from flask import Flask, redirect, request, url_for

from constants import SECRET_KEY, SPOTIFY_AUTH_URL, SPOTIFY_CLIENT_ID, STRAVA_AUTH_URL, STRAVA_CLIENT_ID
from state import JWT
from user import User


app = Flask(__name__)
app.config['SERVER_NAME'] = 'spotipy.lalabuff.com'
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PREFERRED_URL_SCHEME'] = 'https'


def error(message: str):
    return redirect(url_for('index', message=message), 303)
    

@app.route('/login')
def login():
  # redirects to strava authorization
  redirect_uri = url_for('callback', _external=True, _scheme='https')
  scopes = 'activity:write,activity:read_all'
  state = JWT(src='strava')
  authorization_url = f'{STRAVA_AUTH_URL}?client_id={STRAVA_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}&state={state}'
  return redirect(authorization_url)


@app.route('/callback')
def callback():
    if request.args.get('error'):
        return error('EPIC FAIL! ' + request.args['error'])
    
    if not request.args.get('code'):
        return error('Missing authorization code.')
    
    if not request.args.get('state'):
        return error('Missing state.')
    
    jwt = JWT(request.args['state'])
    match jwt.src:
        case 'strava':
            # redirects to spotify authorization
            user = User.strava_authorize(request.args['code'])
            redirect_uri = url_for('callback', _external=True, _scheme='https')
            scopes = 'user-read-recently-played,user-read-private,user-read-email'
            state = JWT(src='spotify', user_id=user.id)
            authorization_url = f'{SPOTIFY_AUTH_URL}?client_id={SPOTIFY_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}&state={state}'
            return redirect(authorization_url)
        
        case 'spotify':
            if not isinstance(jwt.user_id, int):
                return error(f'Invalid state.<br>Invalid user id "{jwt.user_id}".')
            url = request.base_url.replace('http:', 'https:')
            User(str(jwt.user_id)).spotify_authorize(request.args['code'], url)
            return error('Subscribed successfully!') # :clueless:
        
        case _:
            return error(f'Invalid state.<br>Invalid source "{jwt.src}".')


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verify_webhook()
        
    print("Webhook event received!", request.args, request.json)
    if request.json and request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
        user = User(request.json['owner_id'])
        if not user.active:
            return 'EVENT_RECEIVED', 200
        user.refresh()
        
        activity_id = request.json['object_id']
        old_description = user.strava_request('GET', f'activities/{activity_id}').get('description', '')
        
        if activity_id not in user.activities:
            
            description = '🎵 Music Of The Activity 🎵'
            json = user.spotify_request('GET', 'me/player/recently-played')
            print(json)
            for item in json['items']:
                description += f'\n{item["track"]["name"]} - {item["track"]["artists"][0]["name"]}'
            if not json['items']:
                description += '\nNone :('
            
            user.strava_request('PUT', f'activities/{activity_id}', {
                'description': f'{old_description}\n\n{description}'
            })
            user.activities.append(activity_id)
    
    return 'EVENT_RECEIVED', 200


def verify_webhook():
    VERIFY_TOKEN = 'BEELAU'
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return {'hub.challenge': challenge}
        else:
            return 'Forbidden', 403
    return 'Bad Request', 400


@app.route('/')
def index():
    return request.args.get('message', 'hiiiiiii')


app.run('0.0.0.0')
