# Upwork MCP Server

MCP server for the [Upwork](https://www.upwork.com/) GraphQL API. Search jobs, manage contracts, find freelancers, track time, send messages, and view financials through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_current_user` | Get authenticated user's basic info |
| `get_freelancer_profile` | Get current user's freelancer profile |
| `get_organization` | Get current organization details |
| `list_organizations` | List all organizations the user can access |
| `search_jobs` | Search for jobs on the marketplace |
| `get_job` | Get details of a specific job posting |
| `get_contract` | Get details of a specific contract |
| `list_contracts` | List contracts by IDs or all accessible |
| `get_offer` | Get details of a specific offer |
| `search_freelancers` | Search the talent marketplace |
| `get_freelancer_by_profile_key` | Get a freelancer's profile by key |
| `get_time_report` | Get time reports for a date range |
| `list_rooms` | List message rooms (conversations) |
| `get_room_messages` | Get messages in a conversation |
| `send_message` | Send a message in a room |
| `get_client_proposals` | Get proposals received for a job posting |
| `get_transaction_history` | Get payment/charge history |
| `get_work_diary` | Get work diary snapshots for a contract |
| `run_graphql` | Execute raw GraphQL queries |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `UPWORK_CLIENT_ID` | Yes | OAuth2 client ID |
| `UPWORK_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `UPWORK_TOKEN_FILE` | No | Path to saved token (default: `token.json` in server dir) |
| `UPWORK_ORG_ID` | No | Organization/tenant ID (auto-detected if not set) |
| `UPWORK_INSTANCE_NAME` | No | MCP instance label (default: `upwork`) |

---

## Setup

1. Create an OAuth2 app at [Upwork Developer Center](https://www.upwork.com/developer/keys/apply)
2. Set environment variables:
   ```bash
   export UPWORK_CLIENT_ID="your_client_id"
   export UPWORK_CLIENT_SECRET="your_client_secret"
   ```
3. Run the OAuth2 flow once:
   ```bash
   python auth.py
   ```
   This opens a browser for Upwork authorization and saves `token.json` locally. The server will auto-refresh tokens on subsequent runs.
4. Run the server:
   ```bash
   python server.py
   ```

### Multi-Account Support

Run multiple Upwork accounts (e.g., business + personal):

```json
{
  "mcpServers": {
    "upwork-business": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/upwork", "server.py"],
      "env": {
        "UPWORK_CLIENT_ID": "business_client_id",
        "UPWORK_CLIENT_SECRET": "business_client_secret",
        "UPWORK_TOKEN_FILE": "/path/to/token_business.json",
        "UPWORK_ORG_ID": "business_org_id",
        "UPWORK_INSTANCE_NAME": "upwork-business"
      }
    },
    "upwork-personal": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/upwork", "server.py"],
      "env": {
        "UPWORK_CLIENT_ID": "personal_client_id",
        "UPWORK_CLIENT_SECRET": "personal_client_secret",
        "UPWORK_TOKEN_FILE": "/path/to/token_personal.json",
        "UPWORK_INSTANCE_NAME": "upwork-personal"
      }
    }
  }
}
```

---

## Dependencies

- `mcp[cli]` >= 1.0.0
- `httpx` >= 0.27.0

---

## Author

**Raghav Sharma** -- [Upwork](https://www.upwork.com/freelancers/~013c695dd60c19c334) | [LinkedIn](https://www.linkedin.com/in/raghav-s-08a9aa76/)
