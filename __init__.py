__all__ = ['Session', 'SessionError', 'ServerError', 'ClientError']

import difflib
import functools
import requests
import os
from typing import Callable
from pathlib import Path


@functools.cache
def get_query_text(name: str) -> str:
    """
    Reads the content of a text file located in the 'queries' directory and returns it as a string.

    Args:
        name (str): The name of the text file (without the .txt extension) to read.

    Returns:
        str: The content of the specified text file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IOError: If there is an error reading the file.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(f'{dir_path}/queries/{name}.txt') as fp:
        return fp.read()


def snake_case_to_camel_case(snake_str: str) -> str:
    """
    Convert a snake_case string to camelCase.

    Args:
        snake_str (str): The snake_case string to be converted.

    Returns:
        str: The converted camelCase string.
    """
    if not snake_str:
        return ''

    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_case_to_snake_case(camel_str: str) -> str:
    """
    Converts a camelCase string to snake_case.

    Args:
        camel_str (str): The camelCase string to be converted.

    Returns:
        str: The converted snake_case string.
    """
    if not camel_str:
        return ''

    return ''.join(['_' + i.lower() if i.isupper() else i for i in camel_str]).lstrip('_')


class SessionError(Exception):
    """
    Exception raised for errors related to session handling.
    """
    pass


class InvalidQueryError(SessionError):
    """
    Exception raised for invalid query names.

    This error is raised when a query name provided by the user does not match
    any of the available query names. It suggests the closest matches to the
    invalid query name.

    Methods:
        __init__(name: str): Initializes the InvalidQueryError with the invalid
                             query name and suggests the closest matches.
    """

    def __init__(self, name: str):
        # Get the closest matches to the query name,
        # and suggest them to the user.
        query_names = [i.stem for i in Path('queries').glob('*.txt')]
        query = snake_case_to_camel_case(name)
        closest_matches = difflib.get_close_matches(query, query_names)
        # Convert closest matches to snake case if the query was also snake case.
        if query != name:
            closest_matches = [
                camel_case_to_snake_case(i) for i in closest_matches
            ]

        msg = f'Invalid query name: {name}'
        if closest_matches:

            msg += f'\nDid you mean: {", ".join(closest_matches)}?'

        super().__init__(msg)


class ServerError(SessionError):
    """
    Exception raised for server errors during API requests.
    This error means that something went wrong on the server side,
    or the server could not fulfill the request (due to insufficient permissions, etc.).

    Methods:
        __init__(code: int): Initializes the ServerError with the status code
                             of the failed API request
    """

    def __init__(self, code: int):
        super().__init__(f'API request failed with status code {code}')


class ClientError(SessionError):
    """
    Exception raised for client errors during API requests.
    This error means that the client's request is invalid, and the server cannot process it.

    Methods:
        __init__(message: str): Initializes the ClientError with the error message.
    """

    def __init__(self, message: str):
        super().__init__(f'Error in API request: {message}')


class Session:
    """
    A class to manage Skrunk API sessions and make API calls.

    Attributes:
        api_key (str): The API key used for authentication.
        url (str): The base URL of the API. Defaults to 'localhost'.
        port (int | None): The port to use for the connection. Defaults to 5000 for 'localhost' and 443 otherwise.

    Methods:
        __init__(api_key: str, url: str = 'localhost', port: int | None = None):
            Initializes the Session with the given API key, URL, and port.

        call(query_name: str, variables: dict | None = None) -> str:
            Makes a POST request to the API with the given query and variables.

        __getattr__(name: str) -> Callable:
            Dynamically handles attribute access to allow API calls by calling a method on the Session object.
    """

    def __init__(self, api_key: str, url: str = 'localhost', *, port: int | None = None):
        """
        Initialize the API client.

        Args:
            api_key (str): The API key for authentication.
            url (str, optional): The base URL of the API. Defaults to 'localhost'.
            port (int, optional): The port to connect to. Defaults to 5000 if url is 'localhost', otherwise 443.
        """

        if port is None:
            port = 5000 if url == 'localhost' else 443

        self.url = url
        self.api_key = api_key

    def call(self, query_name: str, variables: dict | None = None) -> str:
        """
        Executes a GraphQL query by sending a POST request to the API.

        Args:
            query_name (str): The name of the query to be executed.
            variables (dict | None, optional): A dictionary of variables to be passed with the query. Defaults to None.

        Returns:
            str: The data returned from the API for the given query.

        Raises:
            InvalidQueryError: If the query file is not found.
            ClientError: If the server returns a 500 status code.
            ServerError: If the server returns a status code outside the range of 200-299.
        """

        query = snake_case_to_camel_case(query_name)

        try:
            query_text = get_query_text(query)
        except FileNotFoundError:
            raise InvalidQueryError(query_name)

        res = requests.post(
            f'{self.url}/api',
            json={
                'query': query_text,
                'variables': variables,
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            },
        )

        if res.status_code == 500:
            raise ClientError(res.json().get('errors')[0].get('message'))
        if res.status_code >= 300 or res.status_code < 200:
            raise ServerError(res.status_code)

        data = res.json().get('data')
        for i in data:
            return data[i]

    def __getattr__(self, name) -> Callable:
        """
        Dynamically handle attribute access to allow API calls by calling a method on the Session object.

        Args:
            name (str): The name of the attribute being accessed.

        Returns:
            Callable: A wrapper function that takes keyword arguments and returns a dictionary response from the API call.
        """

        def wrapper(**kwargs) -> dict:
            return self.call(name, variables={**kwargs})
        return wrapper
