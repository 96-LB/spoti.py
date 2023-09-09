from os import environ


STRAVA_API_URL = 'https://www.strava.com/api/v3'
STRAVA_AUTH_URL = f'{STRAVA_API_URL}/oauth/authorize'
STRAVA_DEAUTH_URL = f'{STRAVA_API_URL}/oauth/deauthorize'
STRAVA_TOKEN_URL = f'{STRAVA_API_URL}/oauth/token'

STRAVA_CLIENT_ID = environ['STRAVA_CLIENT_ID']
STRAVA_CLIENT_SECRET = environ['STRAVA_CLIENT_SECRET']
