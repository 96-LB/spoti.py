import joke
import os
from flask import Flask, redirect, request
from flask import jsonify
import requests
from urllib.parse import quote
from user import User

app = Flask(__name__)
client_id = os.environ.get('CLIENT_ID') # TODO: make a client
client_secret = os.environ.get('CLIENT_SECRET')

@app.route('/login')
def login():
  # Redirects to Strava authorization
  client_id = os.environ.get('CLIENT_ID')
  redirect_uri = 'https://stravajokesv2.beelauuu.repl.co/create_callback' # TODO: use url_for to get correct redirect uri
  scopes = 'activity:write,activity:read_all'
  authorization_url = f'https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
  return redirect(authorization_url)


@app.route('/strava/callback')
def strava_callback():
    code = request.args.get('code')
    # Exchange the authorization code for an access token
    token_url = 'https://www.strava.com/oauth/token'
    payload = {
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload)
    data = response.json()
        
    if 'access_token' in data:
        refresh_token = data['refresh_token']
        user_id = data['athlete']['id']
        User(user_id).refresh_token = refresh_token
        return redirect("https://jokepy.vercel.app/message?message=" + # TODO: url_for
            quote("Subscribed Successfully!"))
    else:
        # Failed to obtain access token
        return redirect("https://jokepy.vercel.app/message?message=" +
                        quote("Unable To Obtain Access Token"))


@app.route('/delete')
def deleteSubscription():
    # Authenticate to get users tokens again
    client_id = os.environ.get('CLIENT_ID')
    redirect_uri = 'https://stravajokesv2.beelauuu.repl.co/delete_callback'
    scopes = 'activity:write,activity:read_all'
    authorization_url = f'https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}'
    return redirect(authorization_url)


@app.route('/delete_callback')
def deleteSubscriptionCallback():
    code = request.args.get('code')
    # Exchange the authorization code for an access token
    token_url = 'https://www.strava.com/oauth/token'
    payload = {
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload)
    data = response.json()
    user_id = data['athlete']['id']
    existing_user = User(user_id)

    # Check if user is in the database
    if existing_user.refresh_token:
        # Doing the deleting
        unsub_url = 'https://www.strava.com/oauth/deauthorize'
        params = {'access_token': data['access_token']}
        response = requests.post(unsub_url, data=params)
        existing_user.refresh_token = ''
        
        if response.status_code == 204 or response.status_code == 200:
            return redirect("https://jokepy.vercel.app/message?message=" + # TODO: url_for
                        quote("Deleted Successfully!"))
        
        else:
            return redirect("https://jokepy.vercel.app/message?message=" +
                        quote("Failed To Delete Subscription"))

    else:
        return redirect("https://jokepy.vercel.app/message?message=" +
                        quote("Failed To Delete Subscription"))


# Creates the endpoint for our webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    print("Webhook event received!", request.args, request.json)
    if request.json and request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
        joke.update_joke(User(request.json['owner_id'])) # TODO: chagne webhook magic
        return 'JOKE_RECEIVED', 200
    return 'EVENT_RECEIVED', 200


# Adds support for GET requests to our webhook
@app.route('/webhook', methods=['GET'])
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
    return 'hiiiiiii'
