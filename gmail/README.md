# Gmail MCP Server

MCP server for the [Gmail](https://mail.google.com/) API. Search, send, reply, manage labels, threads, and drafts through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `list_messages` | List/search messages (Gmail search syntax) |
| `get_message` | Get full message with body content |
| `send_message` | Send a new email |
| `reply_to_message` | Reply to a message (auto-sets threading headers) |
| `trash_message` | Move a message to Trash |
| `modify_message` | Add/remove labels (mark read, archive, star) |
| `list_threads` | List email threads (conversations) |
| `get_thread` | Get a full thread with all messages |
| `list_labels` | List all Gmail labels |
| `list_drafts` | List email drafts |
| `get_draft` | Get a draft's content |
| `create_draft` | Create a new email draft |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `GMAIL_CREDENTIALS_FILE` | Yes | Path to OAuth client `credentials.json` |
| `GMAIL_TOKEN_FILE` | No | Path to saved token (default: `token.json` in server dir) |
| `GMAIL_INSTANCE_NAME` | No | MCP instance label (default: `gmail`) |

---

## Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Gmail API**
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

### Multi-Account Support

Run multiple Gmail accounts by pointing each instance to a different token file:

```json
{
  "mcpServers": {
    "gmail-work": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/gmail", "server.py"],
      "env": {
        "GMAIL_CREDENTIALS_FILE": "/path/to/credentials.json",
        "GMAIL_TOKEN_FILE": "/path/to/token_work.json",
        "GMAIL_INSTANCE_NAME": "gmail-work"
      }
    },
    "gmail-personal": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/gmail", "server.py"],
      "env": {
        "GMAIL_CREDENTIALS_FILE": "/path/to/credentials.json",
        "GMAIL_TOKEN_FILE": "/path/to/token_personal.json",
        "GMAIL_INSTANCE_NAME": "gmail-personal"
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
