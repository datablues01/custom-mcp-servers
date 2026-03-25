# GitHub MCP Server

MCP server for the [GitHub](https://github.com/) REST API. Manage repositories, branches, pull requests, files, and commits through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_repo` | Get repository info (name, description, visibility) |
| `list_branches` | List branches in a repository |
| `get_branch` | Get branch details with latest commit |
| `compare_branches` | Compare two branches (commits, files, diff stats) |
| `get_file` | Get a file's decoded content |
| `list_directory` | List files and directories at a path |
| `list_commits` | List recent commits (filter by branch/path) |
| `get_commit` | Get a specific commit with diff |
| `list_pull_requests` | List pull requests (open/closed/all) |
| `get_pull_request` | Get PR details with diff stats |
| `get_pr_files` | Get files changed in a PR |
| `get_pr_comments` | Get review comments on a PR |
| `create_pull_request` | Create a new pull request |
| `create_file` | Create a new file and commit it |
| `update_file` | Update an existing file and commit it |
| `delete_file` | Delete a file and commit the deletion |
| `create_branch` | Create a new branch from an existing one |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `GITHUB_TOKEN` | Yes | Personal access token |
| `GITHUB_REPO` | No | Default repo URL or `owner/repo` |
| `GITHUB_INSTANCE_NAME` | No | MCP instance label (default: `github`) |

---

## Setup

1. Create a [Personal Access Token](https://github.com/settings/tokens) with `repo` scope
2. Set the environment variable:
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/github", "server.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here",
        "GITHUB_REPO": "owner/repo"
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
