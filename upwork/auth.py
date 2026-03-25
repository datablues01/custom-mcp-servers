"""
Run this once to complete the Upwork OAuth2 flow and save tokens.

Usage:
    UPWORK_CLIENT_ID=xxx UPWORK_CLIENT_SECRET=yyy python auth.py

Optionally set UPWORK_TOKEN_FILE to choose where the token is saved
(default: token.json in this directory).
"""

import os
import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import httpx

SCRIPT_DIR = Path(__file__).parent
CLIENT_ID = os.environ.get("UPWORK_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("UPWORK_CLIENT_SECRET", "")
TOKEN_FILE = os.environ.get("UPWORK_TOKEN_FILE", str(SCRIPT_DIR / "token.json"))
REDIRECT_URI = "http://localhost:8080/callback"

AUTH_URL = "https://www.upwork.com/ab/account-security/oauth2/authorize"
TOKEN_URL = "https://www.upwork.com/api/v3/oauth2/token"

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set UPWORK_CLIENT_ID and UPWORK_CLIENT_SECRET environment variables.")
    sys.exit(1)


class CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth2 callback and captures the authorization code."""

    auth_code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            CallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful!</h2><p>You can close this tab.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error = query.get("error", ["unknown"])[0]
            self.wfile.write(f"<h2>Authorization failed: {error}</h2>".encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


# Step 1: Open browser for authorization
auth_params = f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
full_auth_url = AUTH_URL + auth_params
print(f"Opening browser for Upwork authorization...")
print(f"If the browser doesn't open, visit:\n{full_auth_url}\n")
webbrowser.open(full_auth_url)

# Step 2: Wait for callback
server = HTTPServer(("localhost", 8080), CallbackHandler)
print("Waiting for callback on http://localhost:8080/callback ...")
while CallbackHandler.auth_code is None:
    server.handle_request()
server.server_close()

code = CallbackHandler.auth_code
print(f"Authorization code received.")

# Step 3: Exchange code for tokens
print("Exchanging code for access token...")
resp = httpx.post(
    TOKEN_URL,
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    },
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    },
)
resp.raise_for_status()
token_data = resp.json()

# Step 4: Save tokens
with open(TOKEN_FILE, "w") as f:
    json.dump(token_data, f, indent=2)

print(f"Done! Token saved to {TOKEN_FILE}")
print(f"Access token expires in {token_data.get('expires_in', '?')} seconds.")
print(f"Refresh token saved for automatic renewal.")
