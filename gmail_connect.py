import os.path
import pickle
import json
import time
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
RULES_FILE = 'rules.json'

# 🔧 Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(levelname)s — %(message)s',
    handlers=[
        logging.FileHandler("organizer.log"),
        logging.StreamHandler()  # Remove this line if you don't want console output
    ]
)

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return []

def apply_label(service, user_id, msg_id, label_name):
    try:
        label_id = None
        label_list = service.users().labels().list(userId=user_id).execute().get('labels', [])
        for label in label_list:
            if label['name'] == label_name:
                label_id = label['id']
                break

        if not label_id:
            label_obj = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            new_label = service.users().labels().create(userId=user_id, body=label_obj).execute()
            label_id = new_label['id']

        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={
                'addLabelIds': [label_id],
                'removeLabelIds': ['INBOX']
            }
        ).execute()

        logging.info(f"Labeled and archived message ID {msg_id} as {label_name}")

    except Exception as e:
        logging.error(f"❌ Failed to apply label to message ID {msg_id}: {e}")

def main():
    logging.info("🟢 Gmail Organizer started...")
    creds = None

    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    rules = load_rules()
    logging.info(f"📖 Loaded {len(rules)} rules from rules.json")

    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX', 'UNREAD'],
        maxResults=2000
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        logging.info("📭 No unread messages in Inbox.")
        return
    else:
        logging.info(f"📬 Found {len(messages)} unread message(s) in Inbox.")

    processed = 0

    for msg in messages:
        try:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From']
            ).execute()

            headers = msg_data['payload'].get('headers', [])
            sender = subject = '(unknown)'
            for header in headers:
                if header['name'] == 'From':
                    sender = header['value']
                elif header['name'] == 'Subject':
                    subject = header['value']

            label_name = '@Later'
            for rule in rules:
                rule_type = rule.get('type')
                match_text = rule.get('contains', '').lower()
                if rule_type == 'from' and match_text in sender.lower():
                    label_name = rule['label']
                    break
                elif rule_type == 'subject' and match_text in subject.lower():
                    label_name = rule['label']
                    break

            apply_label(service, 'me', msg['id'], label_name)
            processed += 1
            time.sleep(0.25)

        except Exception as e:
            logging.error(f"❌ Error processing message ID {msg['id']}: {e}")

    logging.info(f"✅ Labeled and archived {processed} message(s).")

if __name__ == '__main__':
    main()
