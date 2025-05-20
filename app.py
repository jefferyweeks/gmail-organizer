import os
import json
from flask import Flask, redirect, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Load credentials from environment variable
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
redirect_uri = os.getenv("REDIRECT_URI")

if not credentials_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON env variable")
if not redirect_uri:
    raise ValueError("Missing REDIRECT_URI environment variable")

credentials_dict = json.loads(credentials_json)
flow = Flow.from_client_config(credentials_dict, scopes=SCOPES, redirect_uri=redirect_uri)
user_creds = None  # Store in memory for now

@app.route('/')
def index():
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    global user_creds
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    user_creds = creds

    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile['emailAddress']

        return jsonify({'status': 'OAuth success!', 'email': email_address})
    except Exception as e:
        return f"OAuth callback failed:\n{str(e)}", 500

@app.route('/fetch-labeled-emails')
def fetch_labeled_emails():
    if not user_creds:
        return "User not authenticated", 401

    service = build('gmail', 'v1', credentials=user_creds)
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']

    label_history = {}
    try:
        with open("label_history.json", "r") as f:
            label_history = json.load(f)
    except FileNotFoundError:
        label_history = {}

    label_history.setdefault(user_email, [])

    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['type'] != 'system':
            continue

        results = service.users().messages().list(userId='me', labelIds=[label['id']], maxResults=10).execute()
        messages = results.get('messages', [])

        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            msg_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
            msg_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

            entry = {
                'label': label['name'],
                'from': msg_from,
                'subject': msg_subject,
                'threadId': msg_detail['threadId']
            }

            if entry not in label_history[user_email]:
                label_history[user_email].append(entry)

    with open("label_history.json", "w") as f:
        json.dump(label_history, f, indent=2)

    return jsonify({'status': 'Fetched labeled emails', 'count': len(label_history[user_email])})

if __name__ == '__main__':
    app.run(debug=True)
