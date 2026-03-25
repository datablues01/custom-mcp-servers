<![CDATA[<div align="center">

# Custom MCP Servers

**Production-ready Model Context Protocol servers for connecting AI assistants to your favorite SaaS tools**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

[Overview](#-overview) | [Quick Start](#-quick-start) | [Connectors](#-connectors) | [Configuration](#%EF%B8%8F-configuration) | [Author](#-author)

</div>

---

## Overview

This repository contains **9 custom MCP (Model Context Protocol) servers** that bridge AI assistants like Claude, Gemini, and others to popular SaaS platforms. Each connector is a standalone Python server that exposes API endpoints as MCP tools, enabling AI assistants to interact with these services natively.

All servers follow a consistent architecture:
- **Environment-based configuration** -- no hardcoded credentials
- **Async HTTP** via `httpx` for high performance
- **Multi-instance support** -- run multiple instances with different credentials
- **Minimal dependencies** -- each server is lightweight and focused

---

## Quick Start

### Prerequisites

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`

### Install & Run Any Server

```bash
# Clone the repo
git clone https://github.com/datablues01/custom-mcp-servers.git
cd custom-mcp-servers/datablues_mcp

# Install a specific server (e.g., github)
cd github
uv pip install -e .

# Set required environment variables
export GITHUB_TOKEN="your_token_here"

# Run the server
python server.py
```

### Add to Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/datablues_mcp/github", "server.py"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

---

## Connectors

| Connector | Service | Tools | Auth Method |
|-----------|---------|:-----:|-------------|
| [**Clockify**](clockify/) | Time Tracking | 16 | API Key |
| [**GitHub**](github/) | Code & Repos | 18 | Personal Access Token |
| [**Gmail**](gmail/) | Email | 14 | Google OAuth2 |
| [**Google Chat**](google_chat/) | Messaging | 16 | Google OAuth2 |
| [**Harvest**](harvest/) | Time Tracking | 20 | Access Token + Account ID |
| [**Jira**](jira/) | Issue Tracking | 16 | Email + API Token |
| [**Looker**](looker/) | BI / Analytics | 18 | Client ID + Secret |
| [**Tableau**](tableau/) | BI / Dashboards | 14 | Personal Access Token |
| [**Upwork**](upwork/) | Freelance Marketplace | 20 | OAuth2 (Client Credentials) |

---

### Clockify

> Time tracking with projects, clients, tags, and running timers.

```
Tools: get_current_user, list_workspaces, list_projects, get_project, create_project,
       list_time_entries, get_running_timer, start_timer, stop_timer, create_time_entry,
       update_time_entry, delete_time_entry, list_clients, create_client, list_tags, list_tasks
```

| Env Variable | Required | Description |
|---|:---:|---|
| `CLOCKIFY_API_KEY` | Yes | API key from Profile Settings |
| `CLOCKIFY_WORKSPACE_ID` | No | Default workspace (auto-detected) |
| `CLOCKIFY_INSTANCE_NAME` | No | MCP instance label (default: `clockify`) |

---

### GitHub

> Repository management, branches, PRs, file operations, and commits.

```
Tools: get_repo, list_branches, get_branch, compare_branches, get_file, list_directory,
       list_commits, get_commit, list_pull_requests, get_pull_request, get_pr_files,
       get_pr_comments, create_pull_request, create_file, update_file, delete_file,
       create_branch
```

| Env Variable | Required | Description |
|---|:---:|---|
| `GITHUB_TOKEN` | Yes | Personal access token |
| `GITHUB_REPO` | No | Default repo (e.g., `owner/repo`) |
| `GITHUB_INSTANCE_NAME` | No | MCP instance label (default: `github`) |

---

### Gmail

> Full email management: search, send, reply, labels, threads, and drafts.

```
Tools: list_messages, get_message, send_message, reply_to_message, trash_message,
       modify_message, list_threads, get_thread, list_labels, list_drafts, get_draft,
       create_draft
```

| Env Variable | Required | Description |
|---|:---:|---|
| `GMAIL_CREDENTIALS_FILE` | Yes | Path to Google OAuth `credentials.json` |
| `GMAIL_TOKEN_FILE` | No | Path to saved token (default: `token.json`) |
| `GMAIL_INSTANCE_NAME` | No | MCP instance label (default: `gmail`) |

**Setup:** Run `python auth.py` once to complete the OAuth flow.

---

### Google Chat

> Spaces, messages, members, reactions, and thread management.

```
Tools: list_spaces, get_space, create_space, find_direct_message, list_messages,
       get_message, send_message, reply_to_thread, update_message, delete_message,
       list_members, list_reactions, add_reaction, delete_reaction, search_spaces
```

| Env Variable | Required | Description |
|---|:---:|---|
| `GOOGLE_CHAT_CREDENTIALS_FILE` | Yes | Path to Google OAuth `credentials.json` |
| `GOOGLE_CHAT_TOKEN_FILE` | No | Path to saved token (default: `token.json`) |
| `GOOGLE_CHAT_INSTANCE_NAME` | No | MCP instance label (default: `google_chat`) |

**Setup:** Run `python auth.py` once to complete the OAuth flow.

---

### Harvest

> Time tracking with projects, clients, tasks, users, and timer management.

```
Tools: get_current_user, get_company, list_time_entries, get_time_entry,
       create_time_entry_duration, create_time_entry_start_end, update_time_entry,
       delete_time_entry, stop_timer, restart_timer, list_projects, get_project,
       list_task_assignments, list_clients, get_client, list_tasks, get_task, list_users
```

| Env Variable | Required | Description |
|---|:---:|---|
| `HARVEST_ACCESS_TOKEN` | Yes | Personal access token |
| `HARVEST_ACCOUNT_ID` | Yes | Harvest account ID |
| `HARVEST_INSTANCE_NAME` | No | MCP instance label (default: `harvest`) |

---

### Jira

> Full issue tracking: projects, boards, sprints, issues, comments, and workflow transitions.

```
Tools: list_projects, get_project, list_boards, list_sprints, get_sprint_issues,
       search_issues, get_issue, create_issue, update_issue, add_comment,
       get_transitions, transition_issue, search_users, get_myself
```

| Env Variable | Required | Description |
|---|:---:|---|
| `JIRA_BASE_URL` | Yes | Jira instance URL (e.g., `https://yoursite.atlassian.net`) |
| `JIRA_USER_EMAIL` | Yes | Atlassian account email |
| `JIRA_TOKEN` | Yes | API token |
| `JIRA_PROJECT_KEY` | No | Default project key (e.g., `PROJ`) |
| `JIRA_INSTANCE_NAME` | No | MCP instance label (default: `jira`) |

---

### Looker

> Developer workflow: git branches, LookML validation, SQL Runner, explores, dashboards.

```
Tools: get_session, set_workspace, get_git_branch, switch_git_branch, list_git_branches,
       reset_to_remote, deploy_to_production, validate_lookml, run_sql, run_explore_query,
       get_query_by_slug, list_dashboards, get_dashboard, list_projects, list_project_files,
       get_lookml_file, list_connections, get_looker_version
```

| Env Variable | Required | Description |
|---|:---:|---|
| `LOOKER_BASE_URL` | Yes | Looker instance URL |
| `LOOKER_CLIENT_ID` | Yes | API3 client ID |
| `LOOKER_CLIENT_SECRET` | Yes | API3 client secret |
| `LOOKER_PROJECT` | No | Default LookML project name |
| `LOOKER_CONNECTION` | No | Default database connection name |
| `LOOKER_INSTANCE_NAME` | No | MCP instance label (default: `looker`) |

---

### Tableau

> Workbook discovery, view exports, data source connections, and Metadata GraphQL.

```
Tools: get_auth_info, list_workbooks, get_workbook, find_workbook_by_name,
       list_workbook_views, download_view_image, download_workbook,
       get_workbook_connections, get_workbook_metadata, get_sheet_fields,
       get_calculated_fields, run_metadata_graphql, find_workbook_by_url_id
```

| Env Variable | Required | Description |
|---|:---:|---|
| `TABLEAU_BASE_URL` | Yes | Server/Cloud URL |
| `TABLEAU_TOKEN_NAME` | Yes | Personal access token name |
| `TABLEAU_TOKEN_SECRET` | Yes | Personal access token secret |
| `TABLEAU_SITE_CONTENT_URL` | No | Site content URL (empty for default) |
| `TABLEAU_INSTANCE_NAME` | No | MCP instance label (default: `tableau`) |
| `TABLEAU_API_VERSION` | No | REST API version (default: `3.21`) |

---

### Upwork

> Marketplace search, contracts, freelancer profiles, time reports, messages, and financials.

```
Tools: get_current_user, get_freelancer_profile, get_organization, list_organizations,
       search_jobs, get_job, get_contract, list_contracts, get_offer, search_freelancers,
       get_freelancer_by_profile_key, get_time_report, list_rooms, get_room_messages,
       send_message, get_client_proposals, get_transaction_history, get_work_diary,
       run_graphql
```

| Env Variable | Required | Description |
|---|:---:|---|
| `UPWORK_CLIENT_ID` | Yes | OAuth2 client ID |
| `UPWORK_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `UPWORK_TOKEN_FILE` | No | Path to saved token (default: `token.json`) |
| `UPWORK_ORG_ID` | No | Organization/tenant ID (auto-detected) |
| `UPWORK_INSTANCE_NAME` | No | MCP instance label (default: `upwork`) |

**Setup:** Run `python auth.py` once to complete the OAuth2 flow.

---

## Configuration

### Multi-Instance Support

All servers support running multiple instances with different credentials. Use the `*_INSTANCE_NAME` environment variable to differentiate them:

```json
{
  "mcpServers": {
    "github-work": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/github", "server.py"],
      "env": {
        "GITHUB_TOKEN": "work_token",
        "GITHUB_REPO": "company/main-repo",
        "GITHUB_INSTANCE_NAME": "github-work"
      }
    },
    "github-personal": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/github", "server.py"],
      "env": {
        "GITHUB_TOKEN": "personal_token",
        "GITHUB_INSTANCE_NAME": "github-personal"
      }
    }
  }
}
```

### Security

- **Never commit credentials.** All secrets are loaded from environment variables.
- Token files (`token.json`, `credentials.json`) are excluded via `.gitignore`.
- For OAuth-based connectors (Gmail, Google Chat, Upwork), run `auth.py` once locally to complete the OAuth flow and generate tokens.

---

## Project Structure

```
datablues_mcp/
├── README.md
├── LICENSE
├── .gitignore
├── clockify/
│   ├── server.py
│   └── pyproject.toml
├── github/
│   ├── server.py
│   └── pyproject.toml
├── gmail/
│   ├── server.py
│   ├── auth.py
│   └── pyproject.toml
├── google_chat/
│   ├── server.py
│   ├── auth.py
│   └── pyproject.toml
├── harvest/
│   ├── server.py
│   └── pyproject.toml
├── jira/
│   ├── server.py
│   └── pyproject.toml
├── looker/
│   ├── server.py
│   └── pyproject.toml
├── tableau/
│   ├── server.py
│   └── pyproject.toml
└── upwork/
    ├── server.py
    ├── auth.py
    └── pyproject.toml
```

---

## Author

**Raghav Sharma**

- [Upwork](https://www.upwork.com/freelancers/~013c695dd60c19c334)
- [LinkedIn](https://www.linkedin.com/in/raghav-s-08a9aa76/)

---

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.
]]>