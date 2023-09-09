import requests
import os
from user import User

auth_url = 'https://www.strava.com/api/v3/oauth/token'

def update_joke(user: User):
    url = 'https://www.strava.com/api/v3'
    if not user.refresh_token:
        print('User is not found!')
        return
    #Retrieving refresh token
    payload = {
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
        'grant_type': 'refresh_token',
        'refresh_token': user.refresh_token
    }
    response = requests.post(
        auth_url,
        data=payload,
    )
    json = response.json()
    access_token = json['access_token']

    #Getting first (most recent) activity id
    headers = {'Authorization': 'Bearer ' + access_token} # TODO:
    param = {'page': 1, 'per_page': 1}
    response = requests.get(
        url + '/athlete/activities',
        headers=headers,
        params=param
    )
    activity_id = json[0]['id'] # TODO: just get object id from the response
    
    #Get current description
    headers = {'Authorization': 'Bearer ' + access_token}
    response = requests.get(
        url + '/activities/' + str(activity_id),
        headers=headers,
    )
    current_description = json['description']
    if current_description is None:
        current_description = ''
    
    #Updating activity description
    if ('🔒' not in current_description): # TODO: use database to determine if repeat
        headers = {'Authorization': 'Bearer ' + access_token}
        updatableActivity = {
                'description':
                '🔒\n'+
                '\n\n' + current_description
        }
        response = requests.put(
            url + '/activities/' + str(activity_id),
            headers=headers,
            params=updatableActivity
        )
