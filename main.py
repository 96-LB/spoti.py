from flask import Flask, redirect, request, session, url_for

from constants import SECRET_KEY, SPOTIFY_AUTH_URL, SPOTIFY_CLIENT_ID, STRAVA_AUTH_URL, STRAVA_CLIENT_ID
from user import User

from typing import cast


app = Flask(__name__)
app.config['SERVER_NAME'] = 'spotipy.lalabuff.com'
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PREFERRED_URL_SCHEME'] = 'https'



@app.route('/login')
def login():
  # Redirects to Strava authorization
  redirect_uri = url_for('strava_callback', _external=True, _scheme='https')
  scopes = 'activity:write,activity:read_all'
  authorization_url = f'{STRAVA_AUTH_URL}?client_id={STRAVA_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
  return redirect(authorization_url)


@app.route('/strava/callback')
def strava_callback():
    if request.args.get('error'):
        return redirect(url_for('index', message='EPIC FAIL! ' + request.args['error']), 303)
    
    if not request.args.get('code'):
        return redirect(url_for('index', message='Invalid authorization code.'), 303)
    
    user = User.strava_authorize(request.args['code'])
    session['user_id'] = user.id
    session.modified = True
    
    redirect_uri = url_for('spotify_callback', _external=True, _scheme='https')
    scopes = 'user-read-recently-played,user-read-private,user-read-email'
    authorization_url = f'{SPOTIFY_AUTH_URL}?client_id={SPOTIFY_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
    return redirect(authorization_url)


@app.route('/spotify/callback')
def spotify_callback():
    if request.args.get('error'):
        return redirect(url_for('index', message='EPIC FAIL! ' + request.args['error']), 303)
    
    if not request.args.get('code'):
        return redirect(url_for('index', message='Invalid authorization code.'), 303)
    
    id = cast(str, session['user_id'])
    User(id).spotify_authorize(request.args['code'], request.base_url.replace('http:', 'https:'))
    
    return redirect(url_for('index', message='Subscribed successfully!'), 303)


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verify_webhook()
        
    print("Webhook event received!", request.args, request.json)
    if request.json and request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
        user = User(request.json['owner_id'])
        if not user.active:
            return 'EVENT_RECEIVED', 200
        user.strava_refresh()
        
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
