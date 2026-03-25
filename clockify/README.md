# Clockify MCP Server

MCP server for the [Clockify](https://clockify.me/) time tracking API. Track time, manage projects, clients, tags, and tasks through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_current_user` | Get authenticated user's profile |
| `list_workspaces` | List all workspaces |
| `list_projects` | List projects (with pagination & archive filter) |
| `get_project` | Get project details by ID |
| `create_project` | Create a new project |
| `list_time_entries` | List time entries with date/project filters |
| `get_running_timer` | Get the currently running timer |
| `start_timer` | Start a new timer |
| `stop_timer` | Stop the running timer |
| `create_time_entry` | Create a completed time entry |
| `update_time_entry` | Update an existing time entry |
| `delete_time_entry` | Delete a time entry |
| `list_clients` | List clients in the workspace |
| `create_client` | Create a new client |
| `list_tags` | List tags in the workspace |
| `list_tasks` | List tasks for a project |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `CLOCKIFY_API_KEY` | Yes | API key (Profile Settings > API) |
| `CLOCKIFY_WORKSPACE_ID` | No | Default workspace ID (auto-detected if not set) |
| `CLOCKIFY_INSTANCE_NAME` | No | MCP instance label (default: `clockify`) |

---

## Setup

1. Get your API key from [Clockify Profile Settings](https://app.clockify.me/user/settings)
2. Set the environment variable:
   ```bash
   export CLOCKIFY_API_KEY="your_api_key"
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "clockify": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/clockify", "server.py"],
      "env": {
        "CLOCKIFY_API_KEY": "your_api_key"
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
