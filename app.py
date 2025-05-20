import os
import json
from flask import Flask, redirect, request, jsonify
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Load environment variables from .env if present
load_dotenv()

# Flask app setup
app = Flask(__name__)

# Scopes and credentials
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
REDIRECT_URI = os.getenv("REDIRECT_URI")

if not credentials_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable")
if not REDIRECT_URI:
    raise ValueError("Missing REDIRECT_URI environment variable")

credentials_dict = json.loads(credentials_json)

# Start OAuth flow
@app.route("/")
def authorize():
    try:
        flow = Flow.from_client_config(
            credentials_dict,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
        return redirect(auth_url)
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return f"Failed to start OAuth flow: {e}", 500

# OAuth callback
@app.route("/oauth2callback")
def oauth2callback():
    try:
        flow = Flow.from_client_config(
            credentials_dict,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        service = build('gmail', 'v1', credentials=creds)

        # Test: Get user's labels to confirm success
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        return jsonify({
            "status": "OAuth flow completed",
            "labels": labels
        })
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")
        return f"Something went wrong during callback: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
