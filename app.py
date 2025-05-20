import os
import json
import sqlite3
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
user_creds = None

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

    conn = sqlite3.connect("labeled_emails.db")
    cursor = conn.cursor()

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

            cursor.execute("""
                INSERT OR IGNORE INTO labeled_emails (user_email, label, sender, subject, thread_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_email, label['name'], msg_from, msg_subject, msg_detail['threadId']))

    conn.commit()
    conn.close()

    return jsonify({'status': 'Fetched labeled emails', 'count': len(messages)})

@app.route('/setup-db')
def setup_db():
    conn = sqlite3.connect("labeled_emails.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labeled_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            label TEXT,
            sender TEXT,
            subject TEXT,
            thread_id TEXT,
            UNIQUE(user_email, thread_id, label)
        )
    """)
    conn.commit()
    conn.close()
    return "Database and table created successfully."

if __name__ == '__main__':
    app.run(debug=True, port=5000)
