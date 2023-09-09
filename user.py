from jsondata import JSONData

class User(JSONData, folder='data/users'):
    refresh_token: str = ''