import os
import json
import sqlite3
import openai
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
DB_PATH = "labeled_emails.db"

credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
redirect_uri = os.getenv("REDIRECT_URI")
openai.api_key = os.getenv("OPENAI_API_KEY")

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

@app.route('/setup-db')
def setup_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS labeled_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            sender TEXT,
            subject TEXT,
            label TEXT
        )
    ''')
    conn.commit()
    conn.close()
    return "Database and table created successfully."

@app.route('/fetch-labeled-emails')
def fetch_labeled_emails():
    if not user_creds:
        return "User not authenticated", 401

    service = build('gmail', 'v1', credentials=user_creds)
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS labeled_emails (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, sender TEXT, subject TEXT, label TEXT)")

    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    custom_labels = [label for label in labels if label['type'] != 'system']

    total_added = 0
    for label in custom_labels:
        results = service.users().messages().list(userId='me', labelIds=[label['id']], maxResults=10).execute()
        messages = results.get('messages', [])

        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            msg_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
            msg_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

            c.execute("SELECT 1 FROM labeled_emails WHERE user_email=? AND sender=? AND subject=? AND label=?",
                      (user_email, msg_from, msg_subject, label['name']))
            if not c.fetchone():
                c.execute("INSERT INTO labeled_emails (user_email, sender, subject, label) VALUES (?, ?, ?, ?)",
                          (user_email, msg_from, msg_subject, label['name']))
                total_added += 1

    conn.commit()
    conn.close()
    return jsonify({'status': 'Fetched labeled emails', 'count': total_added})

@app.route('/suggest-labels')
def suggest_labels():
    if not user_creds:
        return "User not authenticated", 401

    service = build('gmail', 'v1', credentials=user_creds)
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sender, subject, label FROM labeled_emails WHERE user_email=? LIMIT 20", (user_email,))
    training_examples = c.fetchall()

    system_labels = ['INBOX']
    results = service.users().messages().list(userId='me', labelIds=system_labels, maxResults=5).execute()
    messages = results.get('messages', [])

    suggestions = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
        headers = msg_detail.get('payload', {}).get('headers', [])
        msg_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        msg_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

        example_lines = [f'Sender: {s}\nSubject: {subj}\nLabel: {lbl}' for s, subj, lbl in training_examples]
        prompt = "You are an email labeling assistant. Based on the following examples, suggest a label:\n\n"
        prompt += "\n\n".join(example_lines)
        prompt += f"\n\nSender: {msg_from}\nSubject: {msg_subject}\nLabel:"

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an email categorizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        label_suggestion = response['choices'][0]['message']['content'].strip()
        suggestions.append({
            "from": msg_from,
            "subject": msg_subject,
            "suggested_label": label_suggestion
        })

    return jsonify({"suggestions": suggestions})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
