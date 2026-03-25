"""
Gmail MCP Server
================
Exposes Gmail API endpoints:
  - Messages (list, search, get, send, reply, trash, modify labels)
  - Threads (list, get)
  - Labels (list)
  - Drafts (list, get, create)

Env vars:
  GMAIL_CREDENTIALS_FILE  - Path to OAuth client credentials JSON (default: credentials.json in this dir)
  GMAIL_TOKEN_FILE        - Path to saved token JSON (default: token.json in this dir)
  GMAIL_INSTANCE_NAME     - Instance label for MCP (default: "gmail")

First run will open a browser for OAuth consent. Subsequent runs use the saved token.
"""

import os
import json
import base64
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", str(SCRIPT_DIR / "credentials.json"))
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", str(SCRIPT_DIR / "token.json"))
INSTANCE_NAME = os.environ.get("GMAIL_INSTANCE_NAME", "gmail")
API_BASE = "https://gmail.googleapis.com/gmail/v1"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)


# ── Auth ────────────────────────────────────────────────────────────────────
def _get_credentials() -> Credentials:
    """Load or create OAuth2 credentials."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"OAuth credentials file not found at {CREDENTIALS_FILE}. "
                    "Download it from Google Cloud Console > APIs & Services > Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def _auth_headers() -> dict:
    creds = _get_credentials()
    return {"Authorization": f"Bearer {creds.token}"}


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers=_auth_headers(),
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


def _decode_body(payload: dict) -> str:
    """Extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result
    return ""


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _summarize_message(msg: dict) -> dict:
    """Extract key fields from a full message."""
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "snippet": msg.get("snippet", ""),
        "from": _get_header(headers, "From"),
        "to": _get_header(headers, "To"),
        "subject": _get_header(headers, "Subject"),
        "date": _get_header(headers, "Date"),
        "labelIds": msg.get("labelIds", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Messages ──────────────────────────────────────────────────────────────
@mcp.tool()
async def list_messages(query: str = "", max_results: int = 10, label_ids: str = "") -> dict:
    """
    List messages matching a search query (same syntax as Gmail search bar).

    Args:
        query: Gmail search query (e.g. 'from:alice@example.com', 'is:unread', 'subject:meeting')
        max_results: Max messages to return (default 10)
        label_ids: Comma-separated label IDs to filter by (e.g. 'INBOX', 'UNREAD')
    """
    params = {"maxResults": max_results}
    if query:
        params["q"] = query
    if label_ids:
        params["labelIds"] = label_ids
    result = await _api("GET", "/users/me/messages", params=params)
    messages = result.get("messages", [])

    # Fetch summaries for each message
    summaries = []
    for m in messages:
        full = await _api("GET", f"/users/me/messages/{m['id']}", params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]})
        summaries.append(_summarize_message(full))
    return {"messages": summaries, "resultSizeEstimate": result.get("resultSizeEstimate", 0)}


@mcp.tool()
async def get_message(message_id: str) -> dict:
    """
    Get a full message including body content.

    Args:
        message_id: Message ID (from list_messages)
    """
    msg = await _api("GET", f"/users/me/messages/{message_id}", params={"format": "full"})
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "from": _get_header(headers, "From"),
        "to": _get_header(headers, "To"),
        "cc": _get_header(headers, "Cc"),
        "subject": _get_header(headers, "Subject"),
        "date": _get_header(headers, "Date"),
        "body": _decode_body(msg.get("payload", {})),
        "labelIds": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
    }


@mcp.tool()
async def send_message(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """
    Send a new email.

    Args:
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients, comma-separated
        bcc: BCC recipients, comma-separated
    """
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return await _api("POST", "/users/me/messages/send", json={"raw": raw})


@mcp.tool()
async def reply_to_message(message_id: str, body: str) -> dict:
    """
    Reply to an existing message. Automatically sets In-Reply-To, References, and thread ID.

    Args:
        message_id: Message ID to reply to
        body: Reply body (plain text)
    """
    original = await _api("GET", f"/users/me/messages/{message_id}", params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Message-ID"]})
    headers = original.get("payload", {}).get("headers", [])
    from_addr = _get_header(headers, "From")
    subject = _get_header(headers, "Subject")
    message_id_header = _get_header(headers, "Message-ID")
    thread_id = original.get("threadId")

    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = MIMEText(body)
    msg["To"] = from_addr
    msg["Subject"] = subject
    msg["In-Reply-To"] = message_id_header
    msg["References"] = message_id_header

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return await _api("POST", "/users/me/messages/send", json={"raw": raw, "threadId": thread_id})


@mcp.tool()
async def trash_message(message_id: str) -> dict:
    """
    Move a message to Trash.

    Args:
        message_id: Message ID to trash
    """
    return await _api("POST", f"/users/me/messages/{message_id}/trash")


@mcp.tool()
async def modify_message(message_id: str, add_labels: str = "", remove_labels: str = "") -> dict:
    """
    Modify labels on a message (e.g. mark as read, archive, add labels).

    Common label operations:
      - Mark as read: remove_labels='UNREAD'
      - Mark as unread: add_labels='UNREAD'
      - Archive: remove_labels='INBOX'
      - Move to inbox: add_labels='INBOX'
      - Star: add_labels='STARRED'

    Args:
        message_id: Message ID
        add_labels: Comma-separated label IDs to add
        remove_labels: Comma-separated label IDs to remove
    """
    body = {}
    if add_labels:
        body["addLabelIds"] = [l.strip() for l in add_labels.split(",")]
    if remove_labels:
        body["removeLabelIds"] = [l.strip() for l in remove_labels.split(",")]
    return await _api("POST", f"/users/me/messages/{message_id}/modify", json=body)


# ── Threads ───────────────────────────────────────────────────────────────
@mcp.tool()
async def list_threads(query: str = "", max_results: int = 10) -> dict:
    """
    List email threads (conversations).

    Args:
        query: Gmail search query
        max_results: Max threads to return (default 10)
    """
    params = {"maxResults": max_results}
    if query:
        params["q"] = query
    return await _api("GET", "/users/me/threads", params=params)


@mcp.tool()
async def get_thread(thread_id: str) -> dict:
    """
    Get a full thread with all messages.

    Args:
        thread_id: Thread ID (from list_threads or a message's threadId)
    """
    thread = await _api("GET", f"/users/me/threads/{thread_id}", params={"format": "full"})
    messages = []
    for msg in thread.get("messages", []):
        headers = msg.get("payload", {}).get("headers", [])
        messages.append({
            "id": msg["id"],
            "from": _get_header(headers, "From"),
            "to": _get_header(headers, "To"),
            "subject": _get_header(headers, "Subject"),
            "date": _get_header(headers, "Date"),
            "body": _decode_body(msg.get("payload", {})),
            "snippet": msg.get("snippet", ""),
        })
    return {"id": thread["id"], "messages": messages}


# ── Labels ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_labels() -> list:
    """List all Gmail labels (system and user-created)."""
    result = await _api("GET", "/users/me/labels")
    return result.get("labels", [])


# ── Drafts ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_drafts(max_results: int = 10) -> dict:
    """
    List email drafts.

    Args:
        max_results: Max drafts to return (default 10)
    """
    return await _api("GET", "/users/me/drafts", params={"maxResults": max_results})


@mcp.tool()
async def get_draft(draft_id: str) -> dict:
    """
    Get a draft's content.

    Args:
        draft_id: Draft ID (from list_drafts)
    """
    draft = await _api("GET", f"/users/me/drafts/{draft_id}", params={"format": "full"})
    msg = draft.get("message", {})
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": draft["id"],
        "to": _get_header(headers, "To"),
        "subject": _get_header(headers, "Subject"),
        "body": _decode_body(msg.get("payload", {})),
    }


@mcp.tool()
async def create_draft(to: str, subject: str, body: str, cc: str = "") -> dict:
    """
    Create a new email draft.

    Args:
        to: Recipient email address(es)
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients, comma-separated
    """
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return await _api("POST", "/users/me/drafts", json={"message": {"raw": raw}})


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
