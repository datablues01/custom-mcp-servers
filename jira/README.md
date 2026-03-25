# Jira MCP Server

MCP server for the [Jira Cloud](https://www.atlassian.com/software/jira) REST API v3. Manage projects, issues, sprints, comments, and workflow transitions through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all accessible Jira projects |
| `get_project` | Get project details |
| `list_boards` | List boards for a project |
| `list_sprints` | List sprints for a board (active/closed/future) |
| `get_sprint_issues` | Get issues in a sprint |
| `search_issues` | Search issues using JQL |
| `get_issue` | Get full issue details with description and comments |
| `create_issue` | Create a new issue (Task, Bug, Story, Epic) |
| `update_issue` | Update issue fields (summary, description, priority, assignee) |
| `add_comment` | Add a comment to an issue |
| `get_transitions` | Get available workflow transitions for an issue |
| `transition_issue` | Move an issue through a workflow transition |
| `search_users` | Search for users by name or email |
| `get_myself` | Get the authenticated user's info |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `JIRA_BASE_URL` | Yes | Jira instance URL (e.g., `https://yoursite.atlassian.net`) |
| `JIRA_USER_EMAIL` | Yes | Atlassian account email |
| `JIRA_TOKEN` | Yes | API token |
| `JIRA_PROJECT_KEY` | No | Default project key (e.g., `PROJ`) |
| `JIRA_INSTANCE_NAME` | No | MCP instance label (default: `jira`) |

---

## Setup

1. Create an [Atlassian API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Set environment variables:
   ```bash
   export JIRA_BASE_URL="https://yoursite.atlassian.net"
   export JIRA_USER_EMAIL="you@example.com"
   export JIRA_TOKEN="your_api_token"
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/jira", "server.py"],
      "env": {
        "JIRA_BASE_URL": "https://yoursite.atlassian.net",
        "JIRA_USER_EMAIL": "you@example.com",
        "JIRA_TOKEN": "your_api_token",
        "JIRA_PROJECT_KEY": "PROJ"
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
