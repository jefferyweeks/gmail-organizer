from flask import Flask, redirect, request, session, url_for
from google_auth_oauthlib.flow import Flow
import os
import json

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")  # Replace for production

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Load credentials from environment variable
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable")

credentials_dict = json.loads(credentials_json)

# Set up OAuth flow with correct redirect URI
flow = Flow.from_client_config(
    credentials_dict,
    scopes=SCOPES,
    redirect_uri="https://gmail-organizer-l1xj.onrender.com/oauth2callback"
)

@app.route("/")
def index():
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow.fetch_token(authorization_response=request.url)

    if not flow.credentials:
        return "Authentication failed.", 400

    credentials = flow.credentials
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    return "Authorization successful! You can now use the Gmail API."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
