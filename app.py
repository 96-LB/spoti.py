import requests
from flask import Flask, jsonify, redirect, request, url_for

from constants import STRAVA_API_URL, STRAVA_AUTH_URL, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_DEAUTH_URL, STRAVA_TOKEN_URL
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
    # Exchange the authorization code for an access token
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': request.args.get('code'),
        'grant_type': 'authorization_code'
    })
    data = response.json()
        
    if 'refresh_token' in data:
        refresh_token = data['refresh_token']
        User(data['athlete']['id']).strava_refresh_token = refresh_token
        return redirect(url_for('index', message='Subscribed successfully!'), 303)
    else:
        return redirect(url_for('index', message='EPIC FAIL!'), 303)


@app.route('/delete')
def delete_subscription():
    # Authenticate to get users tokens again
    redirect_uri = url_for('delete_subscription_callback', _external=True)
    scopes = 'activity:write,activity:read_all'
    authorization_url = f'{STRAVA_TOKEN_URL}?client_id={STRAVA_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
    return redirect(authorization_url)


@app.route('/strava/delete')
def delete_subscription_callback():
    code = request.args.get('code')
    
    # Exchange the authorization code for an access token
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    })
    data = response.json()
    user_id = data['athlete']['id']
    existing_user = User(user_id)

    # Check if user is in the database
    if existing_user.strava_refresh_token:
        params = {'access_token': data['access_token']}
        response = requests.post(STRAVA_DEAUTH_URL, data=params)
        deleted = response.status_code in (200, 204)
    else:
        deleted = True
        
    if deleted:
        existing_user.strava_refresh_token = ''
        return url_for('index', message='Removed subscription!')
    else:
        return url_for('index', message=f'EPIC FAIL! {response.status_code} {response.text}')


# Creates the endpoint for our webhook
@app.route('/strava/webhook', methods=['POST'])
def webhook():
    print("Webhook event received!", request.args, request.json)
    if request.json and request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
        activity_id = request.json['object_id']
        user = User(request.json['owner_id'])
        if not user.strava_refresh_token:
            print('User is not found!')
            return 'EVENT_RECEIVED', 200
        
        #Retrieving refresh token
        payload = {
            'client_id': STRAVA_CLIENT_ID,
            'client_secret': STRAVA_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': user.strava_refresh_token
        }
        response = requests.post(
            STRAVA_TOKEN_URL,
            data=payload,
        )
        json = response.json()
        access_token = json['access_token']
        
        #Get current description
        headers = {'Authorization': 'Bearer ' + access_token}
        response = requests.get(
            f'{STRAVA_API_URL}/activities/{activity_id}',
            headers=headers,
        )
        json = response.json()
        current_description = json.get('description', '')
        
        #Updating activity description
        if '🔒' not in current_description: # TODO: use database to determine if repeat
            headers = {'Authorization': 'Bearer ' + access_token}
            updatableActivity = {
                    'description':
                    '🔒\n'+
                    '\n\n' + current_description
            }
            response = requests.put(
                f'{STRAVA_API_URL}/activities/{activity_id}',
                headers=headers,
                params=updatableActivity
            )
        
    return 'EVENT_RECEIVED', 200


# Adds support for GET requests to our webhook
@app.route('/strava/webhook', methods=['GET'])
def verify_webhook():
    # Your verify token. Should be a random string.
    VERIFY_TOKEN = 'BEELAU'
    # Parses the query params
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Checks if a token and mode is in the query string of the request
    if mode and token:
        # Verifies that the mode and token sent are valid
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            # Responds with the challenge token from the request
            print('Webhook has been verified!')
            return jsonify({'hub.challenge': challenge}), 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            return 'Forbidden', 403
    return 'Bad Request', 400


@app.route('/')
def index():
    return request.args.get('message', 'hiiiiiii')
