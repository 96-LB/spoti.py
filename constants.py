from base64 import b64encode
from os import environ


SECRET_KEY = b64encode(environ['SECRET_KEY'].encode())

STRAVA_API_URL = 'https://www.strava.com/api/v3'
STRAVA_AUTH_URL = f'{STRAVA_API_URL}/oauth/authorize'
STRAVA_TOKEN_URL = f'{STRAVA_API_URL}/oauth/token'

STRAVA_CLIENT_ID = environ['STRAVA_CLIENT_ID']
STRAVA_CLIENT_SECRET = environ['STRAVA_CLIENT_SECRET']

SPOTIFY_CLIENT_ID = environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = environ['SPOTIFY_CLIENT_SECRET']

SPOTIFY_API_URL = 'https://api.spotify.com/v1'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
