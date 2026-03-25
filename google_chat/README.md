# Google Chat MCP Server

MCP server for the [Google Chat](https://chat.google.com/) API. Manage spaces, send messages, handle threads, members, and reactions through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `list_spaces` | List spaces (rooms, DMs, group conversations) |
| `get_space` | Get details about a specific space |
| `create_space` | Create a new named space |
| `find_direct_message` | Find or create a DM with another user |
| `list_messages` | List messages in a space (with filters & sorting) |
| `get_message` | Get a specific message |
| `send_message` | Send a message to a space |
| `reply_to_thread` | Reply to an existing message thread |
| `update_message` | Update an existing message's text |
| `delete_message` | Delete a message |
| `list_members` | List members of a space |
| `list_reactions` | List reactions on a message |
| `add_reaction` | Add an emoji reaction to a message |
| `delete_reaction` | Remove a reaction from a message |
| `search_spaces` | Search for spaces by display name |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `GOOGLE_CHAT_CREDENTIALS_FILE` | Yes | Path to OAuth client `credentials.json` |
| `GOOGLE_CHAT_TOKEN_FILE` | No | Path to saved token (default: `token.json` in server dir) |
| `GOOGLE_CHAT_INSTANCE_NAME` | No | MCP instance label (default: `google_chat`) |

---

## Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Chat API**
3. Create OAuth 2.0 credentials (Desktop app) and download `credentials.json`
4. Place `credentials.json` in this directory
5. Run the auth flow once:
   ```bash
   python auth.py
   ```
   This opens a browser for Google sign-in and saves `token.json` locally.
6. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "google-chat": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/google_chat", "server.py"],
      "env": {
        "GOOGLE_CHAT_CREDENTIALS_FILE": "/path/to/credentials.json",
        "GOOGLE_CHAT_TOKEN_FILE": "/path/to/token.json"
      }
    }
  }
}
```

---

## Dependencies

- `mcp[cli]` >= 1.0.0
- `httpx` >= 0.27.0
- `google-auth` >= 2.0.0
- `google-auth-oauthlib` >= 1.0.0

---

## Author

**Raghav Sharma** -- [Upwork](https://www.upwork.com/freelancers/~013c695dd60c19c334) | [LinkedIn](https://www.linkedin.com/in/raghav-s-08a9aa76/)
