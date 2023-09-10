from typing import Literal
import requests
from dataclasses import field

from constants import STRAVA_API_URL, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_DEAUTH_URL, STRAVA_TOKEN_URL
from jsondata import JSONData


class User(JSONData, folder='data/users'):
    active: bool = True
    
    strava_refresh_token: str = ''
    strava_access_token: str = ''
    activities: list[int] = field(default_factory=list)
    
    
    @classmethod
    def strava_authorize(cls, code: str):
        json = requests.post(
            STRAVA_TOKEN_URL,
            data={
                'client_id': STRAVA_CLIENT_ID,
                'client_secret': STRAVA_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            }
        ).json()
        
        user = cls(json['athlete']['id'])
        user.strava_refresh_token = json['refresh_token']
        user.strava_access_token = json['access_token']
        return user
        
    
    def strava_refresh(self):
        json = requests.post(
            STRAVA_TOKEN_URL,
            data={
                'client_id': STRAVA_CLIENT_ID,
                'client_secret': STRAVA_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': self.strava_refresh_token
            },
        ).json()
        
        self.strava_access_token = json['access_token']
        return self.strava_access_token
    
    
    def strava_request(self, method: Literal['GET', 'POST', 'PATCH', 'PUT', 'DELETE'], url: str, data: dict[str, str] | None = None):
        function = {
            'GET': requests.get,
            'POST': requests.post,
            'PATCH': requests.patch,
            'PUT': requests.put,
            'DELETE': requests.delete
        }[method]
        
        return function(
            f'{STRAVA_API_URL}/{url}',
            data=data,
            headers={'Authorization': f'Bearer {self.strava_access_token}'}
        ).json()
    
    
    def strava_deauthorize(self):
        if self.active:
            requests.post(
                STRAVA_DEAUTH_URL,
                data={
                    'access_token': self.strava_access_token
                }
            )
            self.active = False
