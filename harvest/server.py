"""
Harvest MCP Server
==================
Exposes Harvest API v2 endpoints for time tracking:
  - Current user & company info
  - Time entries (list, create, update, delete, stop/restart timer)
  - Projects (list, get details, task assignments)
  - Clients (list)
  - Tasks (list)
  - Users (list)

Multi-instance: set HARVEST_INSTANCE_NAME per instance (e.g. "company-a", "company-b").

Env vars:
  HARVEST_ACCESS_TOKEN   - Personal access token
  HARVEST_ACCOUNT_ID     - Harvest account ID
  HARVEST_INSTANCE_NAME  - Instance label for MCP (default: "harvest")
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
HARVEST_ACCESS_TOKEN = os.environ.get("HARVEST_ACCESS_TOKEN", "")
HARVEST_ACCOUNT_ID = os.environ.get("HARVEST_ACCOUNT_ID", "")
INSTANCE_NAME = os.environ.get("HARVEST_INSTANCE_NAME", "harvest")
API_BASE = "https://api.harvestapp.com/api/v2"

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={
            "Authorization": f"Bearer {HARVEST_ACCESS_TOKEN}",
            "Harvest-Account-Id": HARVEST_ACCOUNT_ID,
            "User-Agent": "Harvest MCP Server",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 200 and not resp.text:
            return {"status": "success"}
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── User & Company ────────────────────────────────────────────────────────
@mcp.tool()
async def get_current_user() -> dict:
    """Get the currently authenticated user's profile (name, email, timezone, roles)."""
    return await _api("GET", "/users/me")


@mcp.tool()
async def get_company() -> dict:
    """Get company info (name, capacity, time format, enabled features)."""
    return await _api("GET", "/company")


# ── Time Entries ──────────────────────────────────────────────────────────
@mcp.tool()
async def list_time_entries(
    user_id: int = 0,
    project_id: int = 0,
    client_id: int = 0,
    is_billed: bool | None = None,
    is_running: bool | None = None,
    from_date: str = "",
    to_date: str = "",
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List time entries with optional filters.

    Args:
        user_id: Filter by user ID (0 = all users)
        project_id: Filter by project ID (0 = all projects)
        client_id: Filter by client ID (0 = all clients)
        is_billed: Filter by billing status
        is_running: Filter by running status (True = only running timers)
        from_date: Return entries on or after this date (YYYY-MM-DD)
        to_date: Return entries on or before this date (YYYY-MM-DD)
        page: Page number (default 1)
        per_page: Results per page, max 100 (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if user_id:
        params["user_id"] = user_id
    if project_id:
        params["project_id"] = project_id
    if client_id:
        params["client_id"] = client_id
    if is_billed is not None:
        params["is_billed"] = str(is_billed).lower()
    if is_running is not None:
        params["is_running"] = str(is_running).lower()
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return await _api("GET", "/time_entries", params=params)


@mcp.tool()
async def get_time_entry(entry_id: int) -> dict:
    """
    Get a specific time entry by ID.

    Args:
        entry_id: Time entry ID
    """
    return await _api("GET", f"/time_entries/{entry_id}")


@mcp.tool()
async def create_time_entry_duration(
    project_id: int,
    task_id: int,
    spent_date: str,
    hours: float = 0.0,
    notes: str = "",
    user_id: int = 0,
) -> dict:
    """
    Create a time entry with a duration (hours). Omit hours or set to 0 to start a running timer.

    Args:
        project_id: Project ID
        task_id: Task ID
        spent_date: Date for the entry (YYYY-MM-DD)
        hours: Hours spent (0 = start a running timer)
        notes: Optional notes
        user_id: User ID (0 = current user)
    """
    body: dict = {
        "project_id": project_id,
        "task_id": task_id,
        "spent_date": spent_date,
    }
    if hours:
        body["hours"] = hours
    if notes:
        body["notes"] = notes
    if user_id:
        body["user_id"] = user_id
    return await _api("POST", "/time_entries", json=body)


@mcp.tool()
async def create_time_entry_start_end(
    project_id: int,
    task_id: int,
    spent_date: str,
    started_time: str,
    ended_time: str = "",
    notes: str = "",
    user_id: int = 0,
) -> dict:
    """
    Create a time entry with start/end times. Omit ended_time to start a running timer.

    Args:
        project_id: Project ID
        task_id: Task ID
        spent_date: Date for the entry (YYYY-MM-DD)
        started_time: Start time (e.g. '8:00am' or '14:30')
        ended_time: End time (e.g. '5:00pm'; omit to start a running timer)
        notes: Optional notes
        user_id: User ID (0 = current user)
    """
    body: dict = {
        "project_id": project_id,
        "task_id": task_id,
        "spent_date": spent_date,
        "started_time": started_time,
    }
    if ended_time:
        body["ended_time"] = ended_time
    if notes:
        body["notes"] = notes
    if user_id:
        body["user_id"] = user_id
    return await _api("POST", "/time_entries", json=body)


@mcp.tool()
async def update_time_entry(
    entry_id: int,
    spent_date: str = "",
    hours: float | None = None,
    started_time: str = "",
    ended_time: str = "",
    notes: str | None = None,
    project_id: int = 0,
    task_id: int = 0,
) -> dict:
    """
    Update an existing time entry. Only provided fields are changed.

    Args:
        entry_id: Time entry ID
        spent_date: New date (YYYY-MM-DD)
        hours: New hours
        started_time: New start time
        ended_time: New end time
        notes: New notes
        project_id: New project ID
        task_id: New task ID
    """
    body: dict = {}
    if spent_date:
        body["spent_date"] = spent_date
    if hours is not None:
        body["hours"] = hours
    if started_time:
        body["started_time"] = started_time
    if ended_time:
        body["ended_time"] = ended_time
    if notes is not None:
        body["notes"] = notes
    if project_id:
        body["project_id"] = project_id
    if task_id:
        body["task_id"] = task_id
    if not body:
        return {"error": "No fields to update"}
    return await _api("PATCH", f"/time_entries/{entry_id}", json=body)


@mcp.tool()
async def delete_time_entry(entry_id: int) -> str:
    """
    Delete a time entry.

    Args:
        entry_id: Time entry ID to delete
    """
    await _api("DELETE", f"/time_entries/{entry_id}")
    return f"Time entry {entry_id} deleted."


@mcp.tool()
async def stop_timer(entry_id: int) -> dict:
    """
    Stop a running timer.

    Args:
        entry_id: Time entry ID of the running timer
    """
    return await _api("PATCH", f"/time_entries/{entry_id}/stop")


@mcp.tool()
async def restart_timer(entry_id: int) -> dict:
    """
    Restart a stopped timer.

    Args:
        entry_id: Time entry ID to restart
    """
    return await _api("PATCH", f"/time_entries/{entry_id}/restart")


# ── Projects ─────────────────────────────────────────────────────────────
@mcp.tool()
async def list_projects(
    is_active: bool | None = None,
    client_id: int = 0,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List projects.

    Args:
        is_active: Filter by active status (None = all)
        client_id: Filter by client ID (0 = all)
        page: Page number (default 1)
        per_page: Results per page (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    if client_id:
        params["client_id"] = client_id
    return await _api("GET", "/projects", params=params)


@mcp.tool()
async def get_project(project_id: int) -> dict:
    """
    Get project details (budget, billing, dates, client).

    Args:
        project_id: Project ID
    """
    return await _api("GET", f"/projects/{project_id}")


@mcp.tool()
async def list_task_assignments(
    project_id: int,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List task assignments for a project (which tasks are available to log time against).

    Args:
        project_id: Project ID
        is_active: Filter by active status (None = all)
        page: Page number (default 1)
        per_page: Results per page (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    return await _api("GET", f"/projects/{project_id}/task_assignments", params=params)


# ── Clients ──────────────────────────────────────────────────────────────
@mcp.tool()
async def list_clients(
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List clients.

    Args:
        is_active: Filter by active status (None = all)
        page: Page number (default 1)
        per_page: Results per page (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    return await _api("GET", "/clients", params=params)


@mcp.tool()
async def get_client(client_id: int) -> dict:
    """
    Get client details.

    Args:
        client_id: Client ID
    """
    return await _api("GET", f"/clients/{client_id}")


# ── Tasks ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_tasks(
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List all tasks.

    Args:
        is_active: Filter by active status (None = all)
        page: Page number (default 1)
        per_page: Results per page (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    return await _api("GET", "/tasks", params=params)


@mcp.tool()
async def get_task(task_id: int) -> dict:
    """
    Get task details.

    Args:
        task_id: Task ID
    """
    return await _api("GET", f"/tasks/{task_id}")


# ── Users ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_users(
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """
    List all users in the account.

    Args:
        is_active: Filter by active status (None = all)
        page: Page number (default 1)
        per_page: Results per page, max 100 (default 100)
    """
    params: dict = {"page": page, "per_page": per_page}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    return await _api("GET", "/users", params=params)


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
