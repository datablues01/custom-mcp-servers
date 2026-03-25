"""
Jira MCP Server
===============
Exposes Jira Cloud REST API v3 endpoints:
  - Projects & boards
  - Issues (search, create, update, get)
  - Comments
  - Transitions (move issues through workflow)
  - Sprints
  - Users & assignees

Env vars:
  JIRA_BASE_URL       - e.g. https://yoursite.atlassian.net
  JIRA_USER_EMAIL     - Atlassian account email
  JIRA_TOKEN          - API token (from id.atlassian.com/manage-profile/security/api-tokens)
  JIRA_PROJECT_KEY    - Default project key (e.g. 'LK')
  JIRA_INSTANCE_NAME  - Instance label for MCP (default: 'jira')
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "")
INSTANCE_NAME = os.environ.get("JIRA_INSTANCE_NAME", "jira")

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=f"{JIRA_BASE_URL}/rest",
        auth=(JIRA_USER_EMAIL, JIRA_TOKEN),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return {"status": "success"}
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


async def _agile_api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=f"{JIRA_BASE_URL}/rest/agile/1.0",
        auth=(JIRA_USER_EMAIL, JIRA_TOKEN),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


def _project_key(project: str) -> str:
    p = project or JIRA_PROJECT_KEY
    if not p:
        raise ValueError("No project specified. Pass project= or set JIRA_PROJECT_KEY.")
    return p


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Projects ───────────────────────────────────────────────────────────────
@mcp.tool()
async def list_projects() -> list:
    """List all Jira projects accessible to the authenticated user."""
    return await _api("GET", "/api/3/project")


@mcp.tool()
async def get_project(project: str = "") -> dict:
    """
    Get project details.

    Args:
        project: Project key (e.g. 'LK'). Defaults to JIRA_PROJECT_KEY env var.
    """
    return await _api("GET", f"/api/3/project/{_project_key(project)}")


# ── Boards ─────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_boards(project: str = "") -> dict:
    """
    List boards for a project.

    Args:
        project: Project key. Defaults to JIRA_PROJECT_KEY env var.
    """
    key = _project_key(project)
    return await _agile_api("GET", f"/board?projectKeyOrId={key}")


# ── Sprints ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_sprints(board_id: int, state: str = "active") -> dict:
    """
    List sprints for a board.

    Args:
        board_id: Board ID (get from list_boards)
        state: 'active', 'closed', or 'future' (default 'active')
    """
    return await _agile_api("GET", f"/board/{board_id}/sprint?state={state}")


@mcp.tool()
async def get_sprint_issues(sprint_id: int, max_results: int = 50) -> dict:
    """
    Get issues in a sprint.

    Args:
        sprint_id: Sprint ID (get from list_sprints)
        max_results: Max issues to return (default 50)
    """
    return await _agile_api("GET", f"/sprint/{sprint_id}/issue?maxResults={max_results}")


# ── Issues ─────────────────────────────────────────────────────────────────
@mcp.tool()
async def search_issues(jql: str, max_results: int = 20, fields: str = "summary,status,assignee,priority,issuetype,created,updated") -> dict:
    """
    Search for issues using JQL (Jira Query Language).

    Args:
        jql: JQL query string (e.g. 'project = LK AND status = "In Progress"')
        max_results: Max results (default 20)
        fields: Comma-separated field names to return
    """
    return await _api(
        "POST",
        "/api/3/search/jql",
        json={"jql": jql, "maxResults": max_results, "fields": fields.split(",")},
    )


@mcp.tool()
async def get_issue(issue_key: str) -> dict:
    """
    Get full issue details including description, comments, and linked issues.

    Args:
        issue_key: Issue key (e.g. 'LK-123')
    """
    return await _api("GET", f"/api/3/issue/{issue_key}")


@mcp.tool()
async def create_issue(
    summary: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "",
    assignee_account_id: str = "",
    labels: list[str] | None = None,
    project: str = "",
) -> dict:
    """
    Create a new Jira issue.

    Args:
        summary: Issue title
        issue_type: 'Task', 'Bug', 'Story', 'Epic' (default 'Task')
        description: Issue description (plain text)
        priority: Priority name (e.g. 'High', 'Medium', 'Low')
        assignee_account_id: Atlassian account ID to assign to
        labels: List of label strings
        project: Project key. Defaults to JIRA_PROJECT_KEY env var.
    """
    fields = {
        "project": {"key": _project_key(project)},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }
    if priority:
        fields["priority"] = {"name": priority}
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if labels:
        fields["labels"] = labels

    return await _api("POST", "/api/3/issue", json={"fields": fields})


@mcp.tool()
async def update_issue(issue_key: str, summary: str = "", description: str = "", priority: str = "", assignee_account_id: str = "") -> dict:
    """
    Update an existing issue's fields.

    Args:
        issue_key: Issue key (e.g. 'LK-123')
        summary: New summary (leave empty to skip)
        description: New description (leave empty to skip)
        priority: New priority name (leave empty to skip)
        assignee_account_id: New assignee account ID (leave empty to skip)
    """
    fields = {}
    if summary:
        fields["summary"] = summary
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }
    if priority:
        fields["priority"] = {"name": priority}
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}

    if not fields:
        return {"error": "No fields to update"}

    return await _api("PUT", f"/api/3/issue/{issue_key}", json={"fields": fields})


@mcp.tool()
async def add_comment(issue_key: str, body: str) -> dict:
    """
    Add a comment to an issue.

    Args:
        issue_key: Issue key (e.g. 'LK-123')
        body: Comment text
    """
    return await _api(
        "POST",
        f"/api/3/issue/{issue_key}/comment",
        json={
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}],
            }
        },
    )


# ── Transitions ────────────────────────────────────────────────────────────
@mcp.tool()
async def get_transitions(issue_key: str) -> dict:
    """
    Get available workflow transitions for an issue (e.g. 'To Do' → 'In Progress' → 'Done').

    Args:
        issue_key: Issue key (e.g. 'LK-123')
    """
    return await _api("GET", f"/api/3/issue/{issue_key}/transitions")


@mcp.tool()
async def transition_issue(issue_key: str, transition_id: str) -> dict:
    """
    Move an issue through a workflow transition (e.g. mark as Done).
    Use get_transitions first to find the transition ID.

    Args:
        issue_key: Issue key (e.g. 'LK-123')
        transition_id: Transition ID (from get_transitions)
    """
    return await _api(
        "POST",
        f"/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": transition_id}},
    )


# ── Users ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def search_users(query: str, max_results: int = 10) -> list:
    """
    Search for Jira users by name or email. Useful for finding assignee account IDs.

    Args:
        query: Name or email to search for
        max_results: Max results (default 10)
    """
    return await _api("GET", f"/api/3/user/search?query={query}&maxResults={max_results}")


@mcp.tool()
async def get_myself() -> dict:
    """Get the currently authenticated user's info."""
    return await _api("GET", "/api/3/myself")


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
