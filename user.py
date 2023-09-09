from dataclasses import field

from jsondata import JSONData


class User(JSONData, folder='data/users'):
    strava_refresh_token: str = ''
    activities: list[int] = field(default_factory=list)