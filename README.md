## SKRUNK_API

This Python module allows easy interaction with [data server](https://github.com/ZacharyWesterman/server) instances.

To get started, add this repo as a git submodule under your repo. Then, performing queries is extremely easy:
```python
import skrunk_api

api = skrunk_api.Session(your_api_key, 'https://www.example.com')

#Query for a list of users
user_list = api.call('listUsers', {'restrict': False})
print(user_list)
```

A full list of possible queries/mutations can be found under the `queries/` subdirectory.
