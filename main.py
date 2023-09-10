from flask import Flask, redirect, request, url_for

from constants import STRAVA_AUTH_URL, STRAVA_CLIENT_ID, STRAVA_TOKEN_URL
from user import User


app = Flask(__name__)
app.config['SERVER_NAME'] = 'spotipy.lalabuff.com'


@app.route('/login')
def login():
  # Redirects to Strava authorization
  redirect_uri = url_for('strava_callback', _external=True)
  scopes = 'activity:write,activity:read_all'
  authorization_url = f'{STRAVA_AUTH_URL}?client_id={STRAVA_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
  return redirect(authorization_url)


@app.route('/strava/callback')
def strava_callback():
    if request.args.get('error'):
        return redirect(url_for('index', message='EPIC FAIL! ' + request.args['error']), 303)
    
    if not request.args.get('code'):
        return redirect(url_for('index', message='Invalid authorization code.'), 303)
    
    User.strava_authorize(request.args['code'])
    
    return redirect(url_for('index', message='Subscribed successfully!'), 303)


@app.route('/delete')
def delete_subscription():
    # Authenticate to get users tokens again
    redirect_uri = url_for('strava_delete', _external=True)
    scopes = 'activity:write,activity:read_all'
    authorization_url = f'{STRAVA_TOKEN_URL}?client_id={STRAVA_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
    return redirect(authorization_url)


@app.route('/strava/delete')
def strava_delete():
    if request.args.get('error'):
        return redirect(url_for('index', message='EPIC FAIL! ' + request.args['error']), 303)
    
    if not request.args.get('code'):
        return redirect(url_for('index', message='Invalid authorization code.'), 303)
    
    User.strava_authorize(request.args['code']).strava_deauthorize()
    return url_for('index', message='Removed subscription!')


@app.route('/strava/webhook', methods=['POST'])
def webhook():
    print("Webhook event received!", request.args, request.json)
    if request.json and request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
        user = User(request.json['owner_id'])
        if not user.active:
            return 'EVENT_RECEIVED', 200
        user.strava_refresh()
        
        activity_id = request.json['object_id']
        description = user.strava_request('GET', f'activities/{activity_id}').get('description', '')
        
        if activity_id not in user.activities:
            user.strava_request('PUT', f'activities/{activity_id}', {
                'description':
                    '🔒\n'+ '---' +
                    '\n\n' + description
            })
            user.activities.append(activity_id)
        
    return 'EVENT_RECEIVED', 200


@app.route('/strava/webhook', methods=['GET'])
def verify_webhook():
    VERIFY_TOKEN = 'BEELAU'
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print('Webhook has been verified!')
            return {'hub.challenge': challenge}
        else:
            return 'Forbidden', 403
    return 'Bad Request', 400


@app.route('/')
def index():
    return request.args.get('message', 'hiiiiiii')


app.run('0.0.0.0')
