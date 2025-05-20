import os
import json
from flask import Flask, redirect, request, session, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

# Load .env if local
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-default-secret")

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Load credentials from environment variable
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON")

credentials_dict = json.loads(credentials_json)

@app.route('/')
def index():
    return '<h2>Welcome to Gmail Organizer</h2><a href="/authorize">Connect Gmail</a>'

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_config(
        credentials_dict,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    if not state:
        return "Session state missing", 400

    flow = Flow.from_client_config(
        credentials_dict,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    return redirect(url_for('labels'))

@app.route('/labels')
def labels():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    creds = Credentials(**session['credentials'])
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    label_names = [label['name'] for label in labels]

    return "<h2>Your Gmail Labels:</h2>" + "<br>".join(label_names)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
