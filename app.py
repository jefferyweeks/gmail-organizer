import os
import json
from flask import Flask, redirect, request, jsonify
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
load_dotenv()

# Set up Flask app and handle HTTPS via ProxyFix
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Scopes and environment variables
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
REDIRECT_URI = os.getenv("REDIRECT_URI")

if not credentials_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable")
if not REDIRECT_URI:
    raise ValueError("Missing REDIRECT_URI environment variable")

# Parse credentials JSON
credentials_dict = json.loads(credentials_json)

@app.route("/")
def authorize():
    try:
        flow = Flow.from_client_config(
            credentials_dict,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )
        return redirect(auth_url)
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return f"OAuth authorization failed: {e}", 500

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
        labels = service.users().labels().list(userId='me').execute()

        return jsonify({
            "status": "OAuth success!",
            "labels": labels.get('labels', [])
        })
    except Exception as e:
        import traceback
        return f"<pre>OAuth callback failed:\n{traceback.format_exc()}</pre>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
