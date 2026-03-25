"""
Clockify MCP Server
====================
Exposes Clockify REST API endpoints for time tracking:
  - Current user & workspaces
  - Projects (list, create)
  - Time entries (list, create, update, delete, stop timer)
  - Clients (list, create)
  - Tags (list)
  - Tasks (list)

Env vars:
  CLOCKIFY_API_KEY       - Your Clockify API key (Profile Settings > API)
  CLOCKIFY_WORKSPACE_ID  - Default workspace ID (optional, auto-detected if not set)
  CLOCKIFY_INSTANCE_NAME - Instance label for MCP (default: "clockify")
"""

import os
from datetime import datetime, timezone
import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
CLOCKIFY_API_KEY = os.environ.get("CLOCKIFY_API_KEY", "")
CLOCKIFY_WORKSPACE_ID = os.environ.get("CLOCKIFY_WORKSPACE_ID", "")
INSTANCE_NAME = os.environ.get("CLOCKIFY_INSTANCE_NAME", "clockify")
API_BASE = "https://api.clockify.me/api/v1"

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)

# ── Cached state ────────────────────────────────────────────────────────────
_cached_user_id: str = ""
_cached_workspace_id: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={
            "X-Api-Key": CLOCKIFY_API_KEY,
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


async def _get_user_id() -> str:
    global _cached_user_id
    if not _cached_user_id:
        user = await _api("GET", "/user")
        _cached_user_id = user["id"]
    return _cached_user_id


async def _get_workspace_id() -> str:
    global _cached_workspace_id
    if not _cached_workspace_id:
        if CLOCKIFY_WORKSPACE_ID:
            _cached_workspace_id = CLOCKIFY_WORKSPACE_ID
        else:
            workspaces = await _api("GET", "/workspaces")
            _cached_workspace_id = workspaces[0]["id"]
    return _cached_workspace_id


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── User & Workspaces ─────────────────────────────────────────────────────
@mcp.tool()
async def get_current_user() -> dict:
    """Get the current authenticated user's profile (name, email, active workspace)."""
    return await _api("GET", "/user")


@mcp.tool()
async def list_workspaces() -> list:
    """List all workspaces the current user belongs to."""
    return await _api("GET", "/workspaces")


# ── Projects ──────────────────────────────────────────────────────────────
@mcp.tool()
async def list_projects(archived: bool = False, page: int = 1, page_size: int = 50) -> list:
    """
    List projects in the workspace.

    Args:
        archived: Include archived projects (default False)
        page: Page number (default 1)
        page_size: Results per page (default 50)
    """
    ws = await _get_workspace_id()
    params = {"archived": str(archived).lower(), "page": page, "page-size": page_size}
    return await _api("GET", f"/workspaces/{ws}/projects", params=params)


@mcp.tool()
async def get_project(project_id: str) -> dict:
    """
    Get project details.

    Args:
        project_id: The project ID
    """
    ws = await _get_workspace_id()
    return await _api("GET", f"/workspaces/{ws}/projects/{project_id}")


@mcp.tool()
async def create_project(name: str, client_id: str = "", color: str = "#0B83D9", billable: bool = True) -> dict:
    """
    Create a new project.

    Args:
        name: Project name
        client_id: Optional client ID to associate
        color: Project color hex (default blue)
        billable: Whether the project is billable (default True)
    """
    ws = await _get_workspace_id()
    body = {"name": name, "color": color, "billable": billable}
    if client_id:
        body["clientId"] = client_id
    return await _api("POST", f"/workspaces/{ws}/projects", json=body)


# ── Time Entries ──────────────────────────────────────────────────────────
@mcp.tool()
async def list_time_entries(
    start: str = "",
    end: str = "",
    project_id: str = "",
    page: int = 1,
    page_size: int = 50,
) -> list:
    """
    List time entries for the current user.

    Args:
        start: Filter start date (ISO 8601, e.g. '2025-01-01T00:00:00Z')
        end: Filter end date (ISO 8601)
        project_id: Filter by project ID
        page: Page number (default 1)
        page_size: Results per page (default 50)
    """
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    params = {"page": page, "page-size": page_size}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    if project_id:
        params["project"] = project_id
    return await _api("GET", f"/workspaces/{ws}/user/{uid}/time-entries", params=params)


@mcp.tool()
async def get_running_timer() -> dict | str:
    """Get the currently running time entry, or a message if no timer is running."""
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    entries = await _api("GET", f"/workspaces/{ws}/user/{uid}/time-entries?in-progress=true")
    if entries:
        return entries[0]
    return "No timer currently running."


@mcp.tool()
async def start_timer(
    description: str = "",
    project_id: str = "",
    tag_ids: list[str] | None = None,
    task_id: str = "",
    billable: bool = True,
) -> dict:
    """
    Start a new timer (time entry without an end time).

    Args:
        description: What you're working on
        project_id: Project ID to track time against
        tag_ids: List of tag IDs to apply
        task_id: Task ID within the project
        billable: Whether this entry is billable (default True)
    """
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    body = {
        "start": _now_utc(),
        "description": description,
        "billable": billable,
    }
    if project_id:
        body["projectId"] = project_id
    if tag_ids:
        body["tagIds"] = tag_ids
    if task_id:
        body["taskId"] = task_id
    return await _api("POST", f"/workspaces/{ws}/user/{uid}/time-entries", json=body)


@mcp.tool()
async def stop_timer() -> dict:
    """Stop the currently running timer."""
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    return await _api("PATCH", f"/workspaces/{ws}/user/{uid}/time-entries", json={"end": _now_utc()})


@mcp.tool()
async def create_time_entry(
    start: str,
    end: str,
    description: str = "",
    project_id: str = "",
    tag_ids: list[str] | None = None,
    task_id: str = "",
    billable: bool = True,
) -> dict:
    """
    Create a completed time entry (with both start and end times).

    Args:
        start: Start time (ISO 8601, e.g. '2025-03-20T09:00:00Z')
        end: End time (ISO 8601, e.g. '2025-03-20T10:30:00Z')
        description: What you worked on
        project_id: Project ID
        tag_ids: List of tag IDs
        task_id: Task ID within the project
        billable: Whether this entry is billable (default True)
    """
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    body = {
        "start": start,
        "end": end,
        "description": description,
        "billable": billable,
    }
    if project_id:
        body["projectId"] = project_id
    if tag_ids:
        body["tagIds"] = tag_ids
    if task_id:
        body["taskId"] = task_id
    return await _api("POST", f"/workspaces/{ws}/user/{uid}/time-entries", json=body)


@mcp.tool()
async def update_time_entry(
    entry_id: str,
    start: str = "",
    end: str = "",
    description: str = "",
    project_id: str = "",
    tag_ids: list[str] | None = None,
    task_id: str = "",
    billable: bool | None = None,
) -> dict:
    """
    Update an existing time entry.

    Args:
        entry_id: Time entry ID to update
        start: New start time (ISO 8601)
        end: New end time (ISO 8601)
        description: New description
        project_id: New project ID
        tag_ids: New list of tag IDs
        task_id: New task ID
        billable: New billable status
    """
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    # Fetch current entry to preserve unchanged fields
    entries = await _api("GET", f"/workspaces/{ws}/user/{uid}/time-entries")
    current = next((e for e in entries if e["id"] == entry_id), None)
    if not current:
        raise ValueError(f"Time entry {entry_id} not found.")

    body = {
        "start": start or current["timeInterval"]["start"],
        "end": end or current["timeInterval"].get("end", ""),
        "description": description if description != "" else current.get("description", ""),
        "billable": billable if billable is not None else current.get("billable", True),
    }
    body["projectId"] = project_id or current.get("projectId", "")
    body["taskId"] = task_id or current.get("taskId", "")
    if tag_ids is not None:
        body["tagIds"] = tag_ids
    else:
        body["tagIds"] = current.get("tagIds", [])

    return await _api("PUT", f"/workspaces/{ws}/user/{uid}/time-entries/{entry_id}", json=body)


@mcp.tool()
async def delete_time_entry(entry_id: str) -> str:
    """
    Delete a time entry.

    Args:
        entry_id: Time entry ID to delete
    """
    ws = await _get_workspace_id()
    uid = await _get_user_id()
    await _api("DELETE", f"/workspaces/{ws}/user/{uid}/time-entries/{entry_id}")
    return f"Time entry {entry_id} deleted."


# ── Clients ───────────────────────────────────────────────────────────────
@mcp.tool()
async def list_clients(page: int = 1, page_size: int = 50) -> list:
    """
    List clients in the workspace.

    Args:
        page: Page number (default 1)
        page_size: Results per page (default 50)
    """
    ws = await _get_workspace_id()
    return await _api("GET", f"/workspaces/{ws}/clients", params={"page": page, "page-size": page_size})


@mcp.tool()
async def create_client(name: str) -> dict:
    """
    Create a new client.

    Args:
        name: Client name
    """
    ws = await _get_workspace_id()
    return await _api("POST", f"/workspaces/{ws}/clients", json={"name": name})


# ── Tags ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_tags(page: int = 1, page_size: int = 50) -> list:
    """
    List tags in the workspace.

    Args:
        page: Page number (default 1)
        page_size: Results per page (default 50)
    """
    ws = await _get_workspace_id()
    return await _api("GET", f"/workspaces/{ws}/tags", params={"page": page, "page-size": page_size})


# ── Tasks ─────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_tasks(project_id: str, page: int = 1, page_size: int = 50) -> list:
    """
    List tasks for a project.

    Args:
        project_id: Project ID
        page: Page number (default 1)
        page_size: Results per page (default 50)
    """
    ws = await _get_workspace_id()
    return await _api(
        "GET",
        f"/workspaces/{ws}/projects/{project_id}/tasks",
        params={"page": page, "page-size": page_size},
    )


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
