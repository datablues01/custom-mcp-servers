# Harvest MCP Server

MCP server for the [Harvest](https://www.getharvest.com/) time tracking API v2. Manage time entries, projects, clients, tasks, and users through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_current_user` | Get authenticated user's profile |
| `get_company` | Get company info and settings |
| `list_time_entries` | List time entries with filters (user, project, date range) |
| `get_time_entry` | Get a specific time entry by ID |
| `create_time_entry_duration` | Create a time entry with hours (or start a timer) |
| `create_time_entry_start_end` | Create a time entry with start/end times |
| `update_time_entry` | Update an existing time entry |
| `delete_time_entry` | Delete a time entry |
| `stop_timer` | Stop a running timer |
| `restart_timer` | Restart a stopped timer |
| `list_projects` | List projects (filter by active/client) |
| `get_project` | Get project details (budget, billing, dates) |
| `list_task_assignments` | List tasks available for a project |
| `list_clients` | List clients |
| `get_client` | Get client details |
| `list_tasks` | List all tasks |
| `get_task` | Get task details |
| `list_users` | List all users in the account |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `HARVEST_ACCESS_TOKEN` | Yes | Personal access token |
| `HARVEST_ACCOUNT_ID` | Yes | Harvest account ID |
| `HARVEST_INSTANCE_NAME` | No | MCP instance label (default: `harvest`) |

---

## Setup

1. Go to [Harvest Developer Tools](https://id.getharvest.com/developers) and create a personal access token
2. Note your Account ID from the same page
3. Set environment variables:
   ```bash
   export HARVEST_ACCESS_TOKEN="your_token"
   export HARVEST_ACCOUNT_ID="your_account_id"
   ```
4. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "harvest": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/harvest", "server.py"],
      "env": {
        "HARVEST_ACCESS_TOKEN": "your_token",
        "HARVEST_ACCOUNT_ID": "your_account_id"
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
