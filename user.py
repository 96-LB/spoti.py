from jsondata import JSONData

class User(JSONData, folder='data/users'):
    strava_refresh_token: str = ''