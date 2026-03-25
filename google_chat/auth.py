"""Run this once per account to complete the OAuth flow and save a token."""

import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = os.environ.get("GOOGLE_CHAT_CREDENTIALS_FILE", str(SCRIPT_DIR / "credentials.json"))
TOKEN_FILE = os.environ.get("GOOGLE_CHAT_TOKEN_FILE", str(SCRIPT_DIR / "token.json"))
SCOPES = [
    "https://www.googleapis.com/auth/chat.spaces",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.messages",
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.memberships",
    "https://www.googleapis.com/auth/chat.memberships.readonly",
    "https://www.googleapis.com/auth/chat.messages.reactions",
    "https://www.googleapis.com/auth/chat.messages.reactions.readonly",
]

if not os.path.exists(CREDENTIALS_FILE):
    print(f"ERROR: credentials.json not found at {CREDENTIALS_FILE}")
    sys.exit(1)

print(f"Saving token to: {TOKEN_FILE}")
print("Opening browser for Google sign-in...")
flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
creds = flow.run_local_server(port=0)
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())
print(f"Done! Token saved to {TOKEN_FILE}")
