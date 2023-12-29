import requests, functools

@functools.cache
def get_query_text(name: str) -> str:
	with open(f'queries/{name}.txt') as fp:
		return fp.read()

class SessionError(Exception):
	def __init__(self, code: int, message: str|None = None):
		if message is None:
			message = f'API request failed with status code {code}'
		else:
			message = f'Error in API request: {message}'

		super().__init__(message)

class Session:
	def __init__(self, api_key: str, url: str = 'localhost', *, port: int|None = None):
		if port is None:
			port = 5000 if url == 'localhost' else 443

		self.url = url
		self.api_key = api_key

	def call(self, query_name: str, variables: dict|None = None)-> str:
		res = requests.post(
			f'{self.url}/api',
			json = {
				'query': get_query_text(query_name),
				'variables': variables,
			},
			headers = {
				'Content-Type': 'application/json',
				'Authorization': f'Bearer {self.api_key}',
			},
		)

		if res.status_code == 500:
			raise SessionError(res.status_code, res.json().get('errors')[0].get('message'))
		if res.status_code >= 300 or res.status_code < 200:
			raise SessionError(res.status_code)

		data = res.json().get('data')
		for i in data:
			return data[i]
