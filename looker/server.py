"""
Looker Developer MCP Server
============================
Exposes Looker API endpoints for the developer workflow:
  - Session management (dev/prod mode)
  - Git branch operations
  - LookML validation
  - SQL Runner
  - Explore queries
  - Dashboard introspection
  - Project & file introspection

Multi-instance: set LOOKER_INSTANCE_NAME per instance (e.g. "analytics", "marketing").
The server registers as "{instance}-dev" so tools are namespaced in the MCP client.

Designed to complement existing Looker MCP toolsets that handle
queries, dashboards, Looks, and explore introspection.
"""

import os
import httpx
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
LOOKER_BASE_URL = os.environ.get("LOOKER_BASE_URL", "").rstrip("/")
LOOKER_CLIENT_ID = os.environ.get("LOOKER_CLIENT_ID", "")
LOOKER_CLIENT_SECRET = os.environ.get("LOOKER_CLIENT_SECRET", "")
LOOKER_PROJECT = os.environ.get("LOOKER_PROJECT", "")
LOOKER_CONNECTION = os.environ.get("LOOKER_CONNECTION", "")
INSTANCE_NAME = os.environ.get("LOOKER_INSTANCE_NAME", "looker")
API_VERSION = "4.0"

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(f"{INSTANCE_NAME}-dev")

# ── Auth & HTTP client ──────────────────────────────────────────────────────
_token: dict = {"access_token": None, "expires_at": 0}


def _api_url(path: str) -> str:
    return f"{LOOKER_BASE_URL}/api/{API_VERSION}/{path.lstrip('/')}"


async def _get_client() -> httpx.AsyncClient:
    """Return an authenticated httpx client, refreshing the token if needed."""
    now = datetime.now(timezone.utc).timestamp()
    if _token["access_token"] is None or now >= _token["expires_at"] - 60:
        async with httpx.AsyncClient(verify=False) as tmp:
            resp = await tmp.post(
                _api_url("login"),
                data={
                    "client_id": LOOKER_CLIENT_ID,
                    "client_secret": LOOKER_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            _token["access_token"] = data["access_token"]
            _token["expires_at"] = now + data.get("expires_in", 3600)

    return httpx.AsyncClient(
        verify=False,
        headers={"Authorization": f"Bearer {_token['access_token']}"},
        timeout=120.0,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    client = await _get_client()
    try:
        resp = await client.request(method, _api_url(path), **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text
    finally:
        await client.aclose()


def _project(project: str) -> str:
    """Resolve project: explicit param > env var > error."""
    p = project or LOOKER_PROJECT
    if not p:
        raise ValueError("No project specified. Pass project= or set LOOKER_PROJECT.")
    return p


def _connection(connection: str) -> str:
    """Resolve connection: explicit param > env var > error."""
    c = connection or LOOKER_CONNECTION
    if not c:
        raise ValueError("No connection specified. Pass connection= or set LOOKER_CONNECTION.")
    return c


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Session ─────────────────────────────────────────────────────────────────
@mcp.tool()
async def get_session() -> dict:
    """Get the current API session info, including workspace (dev/production)."""
    return await _api("GET", "session")


@mcp.tool()
async def set_workspace(workspace: str = "dev") -> dict:
    """
    Switch workspace to 'dev' or 'production'.
    Must be in dev mode to make branch/file changes.

    Args:
        workspace: 'dev' or 'production'
    """
    return await _api("PATCH", "session", json={"workspace_id": workspace})


# ── Git / Branch ────────────────────────────────────────────────────────────
@mcp.tool()
async def get_git_branch(project: str = "") -> dict:
    """
    Get the current git branch and its status (ahead/behind remote).

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("GET", f"projects/{_project(project)}/git_branch")


@mcp.tool()
async def switch_git_branch(branch_name: str, project: str = "") -> dict:
    """
    Switch to a different git branch. Creates the branch if it doesn't exist.

    Args:
        branch_name: Name of the branch to switch to
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api(
        "PUT", f"projects/{_project(project)}/git_branch", json={"name": branch_name}
    )


@mcp.tool()
async def list_git_branches(project: str = "") -> list:
    """
    List all git branches for a project.

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("GET", f"projects/{_project(project)}/git_branches")


@mcp.tool()
async def reset_to_remote(project: str = "") -> str:
    """
    Pull remote / sync Looker to GitHub. Resets the current branch to match remote.

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("POST", f"projects/{_project(project)}/reset_to_remote")


@mcp.tool()
async def deploy_to_production(project: str = "") -> str:
    """
    Deploy the current dev branch to production.

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("POST", f"projects/{_project(project)}/deploy_ref_to_production")


# ── Validation ──────────────────────────────────────────────────────────────
@mcp.tool()
async def validate_lookml(project: str = "") -> dict:
    """
    Run the LookML validator. Returns errors and warnings.

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("POST", f"projects/{_project(project)}/validate")


# ── SQL Runner ──────────────────────────────────────────────────────────────
@mcp.tool()
async def run_sql(sql: str, connection: str = "") -> list:
    """
    Execute a raw SQL query via the SQL Runner and return JSON results.

    Args:
        sql: The SQL query to execute
        connection: Database connection name (defaults to LOOKER_CONNECTION env var)
    """
    conn = _connection(connection)
    create_resp = await _api(
        "POST",
        "sql_queries",
        json={"connection_name": conn, "sql": sql},
    )
    slug = create_resp["slug"]
    return await _api("POST", f"sql_queries/{slug}/run/json")


# ── Explore Queries ────────────────────────────────────────────────────────
@mcp.tool()
async def run_explore_query(
    model: str,
    view: str,
    fields: list[str],
    filters: dict[str, str] | None = None,
    sorts: list[str] | None = None,
    limit: int = 500,
) -> list:
    """
    Run a query against a Looker explore and return JSON results.

    Args:
        model: Model name (e.g. 'my_model')
        view: Explore/view name (e.g. 'bic_postal_codes_coverage')
        fields: List of field names (e.g. ['view.dimension', 'view.measure'])
        filters: Dict of filter field -> value (e.g. {'view.country': 'Germany'})
        sorts: List of sort fields (e.g. ['view.count desc'])
        limit: Max rows to return (default 500)
    """
    body = {
        "model": model,
        "view": view,
        "fields": fields,
        "limit": str(limit),
    }
    if filters:
        body["filters"] = filters
    if sorts:
        body["sorts"] = sorts
    return await _api("POST", "queries/run/json", json=body)


@mcp.tool()
async def get_query_by_slug(slug: str) -> dict:
    """
    Get a saved query definition by its slug (qid from explore URLs).

    Args:
        slug: The query slug/qid (e.g. 'UGIoPswzSKX7sIwe1qXxur')
    """
    return await _api("GET", f"queries/slug/{slug}")


# ── Dashboards ─────────────────────────────────────────────────────────────
@mcp.tool()
async def list_dashboards(fields: str = "id,title,slug") -> list:
    """
    List all dashboards.

    Args:
        fields: Comma-separated list of fields to return (default: 'id,title,slug')
    """
    return await _api("GET", f"dashboards?fields={fields}")


@mcp.tool()
async def get_dashboard(dashboard_id: str) -> dict:
    """
    Get full dashboard details including elements, filters, and queries.
    Works with both numeric IDs (UDD) and LookML dashboard IDs (e.g. 'model::dashboard_name').

    Args:
        dashboard_id: Dashboard ID (numeric for UDD, 'model::name' for LookML dashboards)
    """
    return await _api("GET", f"dashboards/{dashboard_id}")


# ── Project / Files ─────────────────────────────────────────────────────────
@mcp.tool()
async def list_projects() -> list:
    """List all LookML projects."""
    return await _api("GET", "projects")


@mcp.tool()
async def list_project_files(project: str = "") -> list:
    """
    List all files in a LookML project.

    Args:
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    return await _api("GET", f"projects/{_project(project)}/files")


@mcp.tool()
async def get_lookml_file(file_id: str, project: str = "") -> str:
    """
    Read a specific LookML file's content.

    Args:
        file_id: The file path/id (e.g., 'views/my_view.view.lkml')
        project: LookML project name (defaults to LOOKER_PROJECT env var)
    """
    encoded = file_id.replace("/", "%2F")
    return await _api("GET", f"projects/{_project(project)}/files/{encoded}")


# ── Connections & Version ───────────────────────────────────────────────────
@mcp.tool()
async def list_connections() -> list:
    """List all database connections configured in Looker."""
    return await _api("GET", "connections")


@mcp.tool()
async def get_looker_version() -> dict:
    """Get the Looker instance version info."""
    return await _api("GET", "versions")


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
