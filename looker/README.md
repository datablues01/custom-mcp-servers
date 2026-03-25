# Looker MCP Server

MCP server for the [Looker](https://www.looker.com/) API 4.0. Developer workflow tools for git branches, LookML validation, SQL Runner, explore queries, and dashboard introspection through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_session` | Get current session info (dev/production workspace) |
| `set_workspace` | Switch between dev and production mode |
| `get_git_branch` | Get current git branch and status |
| `switch_git_branch` | Switch to a branch (creates if needed) |
| `list_git_branches` | List all git branches for a project |
| `reset_to_remote` | Sync current branch to match remote |
| `deploy_to_production` | Deploy dev branch to production |
| `validate_lookml` | Run the LookML validator |
| `run_sql` | Execute raw SQL via SQL Runner |
| `run_explore_query` | Run a query against a Looker explore |
| `get_query_by_slug` | Get a saved query definition by slug |
| `list_dashboards` | List all dashboards |
| `get_dashboard` | Get full dashboard details with elements |
| `list_projects` | List all LookML projects |
| `list_project_files` | List all files in a LookML project |
| `get_lookml_file` | Read a specific LookML file's content |
| `list_connections` | List all database connections |
| `get_looker_version` | Get Looker instance version info |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `LOOKER_BASE_URL` | Yes | Looker instance URL (e.g., `https://mycompany.looker.com`) |
| `LOOKER_CLIENT_ID` | Yes | API3 client ID |
| `LOOKER_CLIENT_SECRET` | Yes | API3 client secret |
| `LOOKER_PROJECT` | No | Default LookML project name |
| `LOOKER_CONNECTION` | No | Default database connection name |
| `LOOKER_INSTANCE_NAME` | No | MCP instance label (default: `looker`) |

---

## Setup

1. In Looker, go to **Admin > Users** and create API3 credentials for your user
2. Set environment variables:
   ```bash
   export LOOKER_BASE_URL="https://mycompany.looker.com"
   export LOOKER_CLIENT_ID="your_client_id"
   export LOOKER_CLIENT_SECRET="your_client_secret"
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "looker": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/looker", "server.py"],
      "env": {
        "LOOKER_BASE_URL": "https://mycompany.looker.com",
        "LOOKER_CLIENT_ID": "your_client_id",
        "LOOKER_CLIENT_SECRET": "your_client_secret",
        "LOOKER_PROJECT": "my_project",
        "LOOKER_CONNECTION": "my_database"
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
