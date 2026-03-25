"""
Google Chat MCP Server
======================
Exposes Google Chat API endpoints:
  - Spaces (list, get, create)
  - Messages (list, get, send, update, delete)
  - Members (list)
  - Reactions (list, create, delete)

Env vars:
  GOOGLE_CHAT_CREDENTIALS_FILE  - Path to OAuth client credentials JSON (default: credentials.json in this dir)
  GOOGLE_CHAT_TOKEN_FILE        - Path to saved token JSON (default: token.json in this dir)
  GOOGLE_CHAT_INSTANCE_NAME     - Instance label for MCP (default: "google_chat")

First run will open a browser for OAuth consent. Subsequent runs use the saved token.
"""

import os
import json
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = os.environ.get("GOOGLE_CHAT_CREDENTIALS_FILE", str(SCRIPT_DIR / "credentials.json"))
TOKEN_FILE = os.environ.get("GOOGLE_CHAT_TOKEN_FILE", str(SCRIPT_DIR / "token.json"))
INSTANCE_NAME = os.environ.get("GOOGLE_CHAT_INSTANCE_NAME", "google_chat")
API_BASE = "https://chat.googleapis.com/v1"
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


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Spaces ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_spaces(page_size: int = 20, filter_str: str = "") -> dict:
    """
    List Google Chat spaces (rooms, DMs, group conversations) the user is a member of.

    Args:
        page_size: Max spaces to return (default 20)
        filter_str: Optional filter (e.g. 'spaceType = "SPACE"' for only named spaces)
    """
    params = {"pageSize": page_size}
    if filter_str:
        params["filter"] = filter_str
    return await _api("GET", "/spaces", params=params)


@mcp.tool()
async def get_space(space_name: str) -> dict:
    """
    Get details about a specific space.

    Args:
        space_name: Space resource name (e.g. 'spaces/AAAA1234')
    """
    return await _api("GET", f"/{space_name}")


@mcp.tool()
async def create_space(display_name: str, space_type: str = "SPACE") -> dict:
    """
    Create a new named space.

    Args:
        display_name: Human-readable name for the space
        space_type: 'SPACE' for a named space (default)
    """
    return await _api(
        "POST",
        "/spaces",
        json={
            "displayName": display_name,
            "spaceType": space_type,
        },
    )


@mcp.tool()
async def find_direct_message(user_name: str) -> dict:
    """
    Find or create a direct message space with another user.

    Args:
        user_name: User resource name (e.g. 'users/123456789' or 'users/user@example.com')
    """
    return await _api(
        "POST",
        "/spaces:findDirectMessage",
        params={"name": user_name},
    )


# ── Messages ──────────────────────────────────────────────────────────────
@mcp.tool()
async def list_messages(space_name: str, page_size: int = 25, filter_str: str = "", order_by: str = "createTime desc", show_deleted: bool = False) -> dict:
    """
    List messages in a space.

    Args:
        space_name: Space resource name (e.g. 'spaces/AAAA1234')
        page_size: Max messages to return (default 25)
        filter_str: Optional filter (e.g. 'createTime > "2024-01-01T00:00:00Z"')
        order_by: Sort order, 'createTime desc' or 'createTime asc' (default desc)
        show_deleted: Whether to include deleted messages (default false)
    """
    params = {
        "pageSize": page_size,
        "orderBy": order_by,
        "showDeleted": show_deleted,
    }
    if filter_str:
        params["filter"] = filter_str
    return await _api("GET", f"/{space_name}/messages", params=params)


@mcp.tool()
async def get_message(message_name: str) -> dict:
    """
    Get a specific message by its resource name.

    Args:
        message_name: Message resource name (e.g. 'spaces/AAAA1234/messages/MSG5678')
    """
    return await _api("GET", f"/{message_name}")


@mcp.tool()
async def send_message(space_name: str, text: str, thread_key: str = "") -> dict:
    """
    Send a message to a space.

    Args:
        space_name: Space resource name (e.g. 'spaces/AAAA1234')
        text: Message text (supports Google Chat formatting)
        thread_key: Optional thread key to reply in a thread
    """
    body = {"text": text}
    params = {}
    if thread_key:
        body["thread"] = {"threadKey": thread_key}
        params["messageReplyOption"] = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
    return await _api("POST", f"/{space_name}/messages", json=body, params=params)


@mcp.tool()
async def reply_to_thread(space_name: str, thread_name: str, text: str) -> dict:
    """
    Reply to an existing message thread.

    Args:
        space_name: Space resource name (e.g. 'spaces/AAAA1234')
        thread_name: Thread resource name (e.g. 'spaces/AAAA1234/threads/THREAD5678')
        text: Reply text
    """
    return await _api(
        "POST",
        f"/{space_name}/messages",
        json={
            "text": text,
            "thread": {"name": thread_name},
        },
        params={"messageReplyOption": "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"},
    )


@mcp.tool()
async def update_message(message_name: str, text: str) -> dict:
    """
    Update an existing message's text.

    Args:
        message_name: Message resource name (e.g. 'spaces/AAAA1234/messages/MSG5678')
        text: New message text
    """
    return await _api(
        "PUT",
        f"/{message_name}",
        json={"text": text},
        params={"updateMask": "text"},
    )


@mcp.tool()
async def delete_message(message_name: str) -> dict:
    """
    Delete a message.

    Args:
        message_name: Message resource name (e.g. 'spaces/AAAA1234/messages/MSG5678')
    """
    result = await _api("DELETE", f"/{message_name}")
    return result if result else {"status": "deleted"}


# ── Members ───────────────────────────────────────────────────────────────
@mcp.tool()
async def list_members(space_name: str, page_size: int = 50, filter_str: str = "") -> dict:
    """
    List members of a space.

    Args:
        space_name: Space resource name (e.g. 'spaces/AAAA1234')
        page_size: Max members to return (default 50)
        filter_str: Optional filter (e.g. 'member.type = "HUMAN"' for only humans)
    """
    params = {"pageSize": page_size}
    if filter_str:
        params["filter"] = filter_str
    return await _api("GET", f"/{space_name}/members", params=params)


# ── Reactions ─────────────────────────────────────────────────────────────
@mcp.tool()
async def list_reactions(message_name: str, page_size: int = 25) -> dict:
    """
    List reactions on a message.

    Args:
        message_name: Message resource name (e.g. 'spaces/AAAA1234/messages/MSG5678')
        page_size: Max reactions to return (default 25)
    """
    return await _api("GET", f"/{message_name}/reactions", params={"pageSize": page_size})


@mcp.tool()
async def add_reaction(message_name: str, emoji: str) -> dict:
    """
    Add a reaction (emoji) to a message.

    Args:
        message_name: Message resource name (e.g. 'spaces/AAAA1234/messages/MSG5678')
        emoji: Unicode emoji string (e.g. '👍', '😊')
    """
    return await _api(
        "POST",
        f"/{message_name}/reactions",
        json={"emoji": {"unicode": emoji}},
    )


@mcp.tool()
async def delete_reaction(reaction_name: str) -> dict:
    """
    Remove a reaction from a message.

    Args:
        reaction_name: Reaction resource name (e.g. 'spaces/AAAA1234/messages/MSG5678/reactions/REACT9')
    """
    result = await _api("DELETE", f"/{reaction_name}")
    return result if result else {"status": "deleted"}


# ── Search ────────────────────────────────────────────────────────────────
@mcp.tool()
async def search_spaces(query: str, page_size: int = 10) -> dict:
    """
    Search for spaces by display name.

    Args:
        query: Search query (matches against space displayName)
        page_size: Max results (default 10)
    """
    result = await _api("GET", "/spaces", params={"pageSize": 100})
    spaces = result.get("spaces", [])
    query_lower = query.lower()
    matched = [s for s in spaces if query_lower in s.get("displayName", "").lower()]
    return {"spaces": matched[:page_size]}


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
