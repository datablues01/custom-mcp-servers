# Tableau MCP Server

MCP server for [Tableau Server/Cloud](https://www.tableau.com/) REST API and Metadata GraphQL. Discover workbooks, export views, inspect data sources, and query metadata through your AI assistant.

---

## Tools

| Tool | Description |
|------|-------------|
| `get_auth_info` | Get current authentication status and site ID |
| `list_workbooks` | List workbooks on the site |
| `get_workbook` | Get workbook details including views |
| `find_workbook_by_name` | Search workbooks by name via Metadata GraphQL |
| `list_workbook_views` | List all views (sheets/tabs) in a workbook |
| `download_view_image` | Download a view as a PNG image |
| `download_workbook` | Download a workbook as `.twbx` |
| `get_workbook_connections` | Get data source connections for a workbook |
| `get_workbook_metadata` | Get full metadata (datasources, fields, upstream tables) |
| `get_sheet_fields` | Get fields used by each sheet in a workbook |
| `get_calculated_fields` | Get calculated fields and formulas |
| `run_metadata_graphql` | Execute raw Metadata GraphQL queries |
| `find_workbook_by_url_id` | Resolve a Tableau URL numeric ID to a LUID |

---

## Configuration

| Env Variable | Required | Description |
|---|:---:|---|
| `TABLEAU_BASE_URL` | Yes | Server/Cloud URL (e.g., `https://tableau.mycompany.com`) |
| `TABLEAU_TOKEN_NAME` | Yes | Personal access token name |
| `TABLEAU_TOKEN_SECRET` | Yes | Personal access token secret |
| `TABLEAU_SITE_CONTENT_URL` | No | Site content URL (empty for default site) |
| `TABLEAU_INSTANCE_NAME` | No | MCP instance label (default: `tableau`) |
| `TABLEAU_API_VERSION` | No | REST API version (default: `3.21`) |

---

## Setup

1. In Tableau, go to **My Account Settings** and create a Personal Access Token
2. Set environment variables:
   ```bash
   export TABLEAU_BASE_URL="https://tableau.mycompany.com"
   export TABLEAU_TOKEN_NAME="my_token"
   export TABLEAU_TOKEN_SECRET="your_token_secret"
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "tableau": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tableau", "server.py"],
      "env": {
        "TABLEAU_BASE_URL": "https://tableau.mycompany.com",
        "TABLEAU_TOKEN_NAME": "my_token",
        "TABLEAU_TOKEN_SECRET": "your_token_secret",
        "TABLEAU_SITE_CONTENT_URL": ""
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
