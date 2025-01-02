__all__ = ['Session', 'SessionError', 'ServerError', 'ClientError']

import difflib
import functools
import requests
import os
from typing import Callable
from pathlib import Path


@functools.cache
def get_query_text(name: str) -> str:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(f'{dir_path}/queries/{name}.txt') as fp:
        return fp.read()


def snake_case_to_camel_case(snake_str: str) -> str:
    if not snake_str:
        return ''

    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_case_to_snake_case(camel_str: str) -> str:
    if not camel_str:
        return ''

    return ''.join(['_' + i.lower() if i.isupper() else i for i in camel_str]).lstrip('_')


class SessionError(Exception):
    pass


class InvalidQueryError(SessionError):
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
    def __init__(self, code: int):
        super().__init__(f'API request failed with status code {code}')


class ClientError(SessionError):
    def __init__(self, message: str):
        super().__init__(f'Error in API request: {message}')


class Session:
    def __init__(self, api_key: str, url: str = 'localhost', *, port: int | None = None):
        if port is None:
            port = 5000 if url == 'localhost' else 443

        self.url = url
        self.api_key = api_key

    def call(self, query_name: str, variables: dict | None = None) -> str:
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
