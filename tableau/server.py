"""
Tableau MCP Server
==================
Exposes Tableau Server/Cloud REST API and Metadata GraphQL endpoints:
  - Authentication (Personal Access Tokens)
  - Workbook discovery & details
  - View listing & PNG export
  - Workbook download (.twbx)
  - Data source connections
  - Metadata GraphQL (sheets, fields, calculated fields, upstream tables)

Env vars:
  TABLEAU_BASE_URL       - e.g. https://tableau.mycompany.com
  TABLEAU_TOKEN_NAME     - PAT name
  TABLEAU_TOKEN_SECRET   - PAT secret
  TABLEAU_SITE_CONTENT_URL - Site content URL (empty string for default site)
  TABLEAU_INSTANCE_NAME  - Instance label for MCP (default: "tableau")
  TABLEAU_API_VERSION    - REST API version (default: "3.21")
"""

import os
import xml.etree.ElementTree as ET
import httpx
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
TABLEAU_BASE_URL = os.environ.get("TABLEAU_BASE_URL", "").rstrip("/")
TABLEAU_TOKEN_NAME = os.environ.get("TABLEAU_TOKEN_NAME", "")
TABLEAU_TOKEN_SECRET = os.environ.get("TABLEAU_TOKEN_SECRET", "")
TABLEAU_SITE_CONTENT_URL = os.environ.get("TABLEAU_SITE_CONTENT_URL", "")
INSTANCE_NAME = os.environ.get("TABLEAU_INSTANCE_NAME", "tableau")
API_VERSION = os.environ.get("TABLEAU_API_VERSION", "3.21")
NS = {"t": "http://tableau.com/api"}

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(f"{INSTANCE_NAME}")

# ── Auth state ──────────────────────────────────────────────────────────────
_auth: dict = {"token": None, "site_id": None, "expires_at": 0}


def _rest_url(path: str) -> str:
    return f"{TABLEAU_BASE_URL}/api/{API_VERSION}/{path.lstrip('/')}"


async def _ensure_auth():
    """Authenticate with PAT if token is missing or expired."""
    now = datetime.now(timezone.utc).timestamp()
    if _auth["token"] and now < _auth["expires_at"]:
        return

    async with httpx.AsyncClient(verify=False) as tmp:
        resp = await tmp.post(
            _rest_url("auth/signin"),
            json={
                "credentials": {
                    "personalAccessTokenName": TABLEAU_TOKEN_NAME,
                    "personalAccessTokenSecret": TABLEAU_TOKEN_SECRET,
                    "site": {"contentUrl": TABLEAU_SITE_CONTENT_URL},
                }
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        creds = root.find(".//t:credentials", NS)
        site = root.find(".//t:site", NS)
        _auth["token"] = creds.get("token")
        _auth["site_id"] = site.get("id")
        # Tableau tokens last ~240 minutes; refresh at 200
        _auth["expires_at"] = now + 12000


async def _get_client() -> httpx.AsyncClient:
    """Return an authenticated httpx client."""
    await _ensure_auth()
    return httpx.AsyncClient(
        verify=False,
        headers={"X-Tableau-Auth": _auth["token"]},
        timeout=120.0,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _rest(method: str, path: str, **kwargs) -> str:
    """Make a REST API call and return raw response text (XML)."""
    client = await _get_client()
    try:
        resp = await client.request(method, _rest_url(path), **kwargs)
        resp.raise_for_status()
        return resp.text
    finally:
        await client.aclose()


async def _rest_json(method: str, path: str, **kwargs) -> dict | list:
    """Make a REST API call expecting JSON response."""
    client = await _get_client()
    try:
        resp = await client.request(method, _rest_url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()
    finally:
        await client.aclose()


async def _graphql(query: str) -> dict:
    """Execute a Metadata GraphQL query."""
    client = await _get_client()
    try:
        resp = await client.post(
            f"{TABLEAU_BASE_URL}/api/metadata/graphql",
            json={"query": query},
            headers={
                "X-Tableau-Auth": _auth["token"],
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()
    finally:
        await client.aclose()


def _site_path(path: str) -> str:
    """Prefix a path with sites/{site_id}/."""
    return f"sites/{_auth['site_id']}/{path.lstrip('/')}"


def _parse_xml_list(xml_text: str, element_tag: str, attrs: list[str]) -> list[dict]:
    """Parse Tableau XML response into a list of dicts."""
    root = ET.fromstring(xml_text)
    results = []
    for elem in root.findall(f".//t:{element_tag}", NS):
        row = {}
        for a in attrs:
            row[a] = elem.get(a, "")
        results.append(row)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Auth ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def get_auth_info() -> dict:
    """Get current authentication status and site ID."""
    await _ensure_auth()
    return {
        "authenticated": _auth["token"] is not None,
        "site_id": _auth["site_id"],
        "base_url": TABLEAU_BASE_URL,
    }


# ── Workbooks ──────────────────────────────────────────────────────────────
@mcp.tool()
async def list_workbooks(page_size: int = 100, page_number: int = 1) -> list[dict]:
    """
    List workbooks on the site.

    Args:
        page_size: Number of workbooks per page (default 100)
        page_number: Page number (default 1)
    """
    await _ensure_auth()
    xml = await _rest(
        "GET",
        _site_path(f"workbooks?pageSize={page_size}&pageNumber={page_number}"),
    )
    return _parse_xml_list(xml, "workbook", ["id", "name", "contentUrl", "createdAt", "updatedAt"])


@mcp.tool()
async def get_workbook(workbook_id: str) -> list[dict]:
    """
    Get workbook details including its views.

    Args:
        workbook_id: The LUID of the workbook
    """
    await _ensure_auth()
    xml = await _rest("GET", _site_path(f"workbooks/{workbook_id}"))
    root = ET.fromstring(xml)
    wb = root.find(".//t:workbook", NS)
    result = {
        "id": wb.get("id", ""),
        "name": wb.get("name", ""),
        "contentUrl": wb.get("contentUrl", ""),
    }
    views = []
    for v in root.findall(".//t:view", NS):
        views.append({
            "id": v.get("id", ""),
            "name": v.get("name", ""),
            "contentUrl": v.get("contentUrl", ""),
        })
    result["views"] = views
    return result


@mcp.tool()
async def find_workbook_by_name(name: str) -> list[dict]:
    """
    Search for workbooks by name using the Metadata GraphQL API.

    Args:
        name: Workbook name to search for (exact match)
    """
    query = f'{{ workbooks(filter: {{name: "{name}"}}) {{ luid name vizportalUrlId sheets {{ name id }} }} }}'
    return await _graphql(query)


# ── Views / Sheets ─────────────────────────────────────────────────────────
@mcp.tool()
async def list_workbook_views(workbook_id: str) -> list[dict]:
    """
    List all views (sheets/tabs) in a workbook.

    Args:
        workbook_id: The LUID of the workbook
    """
    await _ensure_auth()
    xml = await _rest("GET", _site_path(f"workbooks/{workbook_id}/views"))
    return _parse_xml_list(xml, "view", ["id", "name", "contentUrl"])


@mcp.tool()
async def download_view_image(view_id: str, output_path: str, resolution: str = "high") -> str:
    """
    Download a view/sheet as a PNG image.

    Args:
        view_id: The LUID of the view
        output_path: Local file path to save the PNG (e.g. '/tmp/dashboard.png')
        resolution: Image resolution - 'high' or 'standard' (default 'high')
    """
    await _ensure_auth()
    client = await _get_client()
    try:
        resp = await client.get(
            _rest_url(_site_path(f"views/{view_id}/image?resolution={resolution}&maxAge=1")),
        )
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return f"Saved to {output_path} ({len(resp.content)} bytes)"
    finally:
        await client.aclose()


# ── Downloads ──────────────────────────────────────────────────────────────
@mcp.tool()
async def download_workbook(workbook_id: str, output_path: str, include_extract: bool = False) -> str:
    """
    Download a workbook as a .twbx file.

    Args:
        workbook_id: The LUID of the workbook
        output_path: Local file path to save the .twbx (e.g. '/tmp/workbook.twbx')
        include_extract: Whether to include data extracts (default False)
    """
    await _ensure_auth()
    extract_param = "true" if include_extract else "false"
    client = await _get_client()
    try:
        resp = await client.get(
            _rest_url(_site_path(f"workbooks/{workbook_id}/content?includeExtract={extract_param}")),
        )
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return f"Saved to {output_path} ({len(resp.content)} bytes)"
    finally:
        await client.aclose()


# ── Data Source Connections ─────────────────────────────────────────────────
@mcp.tool()
async def get_workbook_connections(workbook_id: str) -> list[dict]:
    """
    Get data source connections for a workbook (server, port, database, type).

    Args:
        workbook_id: The LUID of the workbook
    """
    await _ensure_auth()
    xml = await _rest("GET", _site_path(f"workbooks/{workbook_id}/connections"))
    return _parse_xml_list(xml, "connection", ["id", "type", "serverAddress", "serverPort", "userName"])


# ── Metadata GraphQL ───────────────────────────────────────────────────────
@mcp.tool()
async def get_workbook_metadata(workbook_luid: str) -> dict:
    """
    Get full metadata for a workbook: embedded datasources, fields, calculated fields,
    upstream tables, and sheet-to-field mappings via the Metadata GraphQL API.

    Args:
        workbook_luid: The LUID of the workbook
    """
    query = f"""{{
      workbooks(filter: {{luid: "{workbook_luid}"}}) {{
        name
        sheets {{
          name
          sheetFieldInstances {{
            name
            datasource {{ name }}
          }}
        }}
        embeddedDatasources {{
          name
          upstreamTables {{
            name
            fullName
            database {{ name connectionType }}
            schema
          }}
          fields {{
            name
            description
            __typename
            ... on CalculatedField {{ formula }}
          }}
        }}
      }}
    }}"""
    return await _graphql(query)


@mcp.tool()
async def get_sheet_fields(workbook_luid: str, sheet_name: str = "") -> dict:
    """
    Get fields used by each sheet in a workbook. Optionally filter to a specific sheet.

    Args:
        workbook_luid: The LUID of the workbook
        sheet_name: Optional sheet name to filter (returns all sheets if empty)
    """
    query = f"""{{
      workbooks(filter: {{luid: "{workbook_luid}"}}) {{
        sheets {{
          name
          sheetFieldInstances {{
            name
            datasource {{ name }}
          }}
        }}
      }}
    }}"""
    result = await _graphql(query)

    if sheet_name:
        sheets = result.get("data", {}).get("workbooks", [{}])[0].get("sheets", [])
        filtered = [s for s in sheets if sheet_name.lower() in s.get("name", "").lower()]
        return {"sheets": filtered}

    return result


@mcp.tool()
async def get_calculated_fields(workbook_luid: str, datasource_name: str = "") -> dict:
    """
    Get calculated fields and their formulas from a workbook's embedded datasources.

    Args:
        workbook_luid: The LUID of the workbook
        datasource_name: Optional datasource name to filter (returns all if empty)
    """
    query = f"""{{
      workbooks(filter: {{luid: "{workbook_luid}"}}) {{
        embeddedDatasources {{
          name
          fields {{
            name
            __typename
            ... on CalculatedField {{ formula }}
          }}
        }}
      }}
    }}"""
    result = await _graphql(query)

    if datasource_name:
        datasources = result.get("data", {}).get("workbooks", [{}])[0].get("embeddedDatasources", [])
        filtered = [ds for ds in datasources if datasource_name.lower() in ds.get("name", "").lower()]
        # Only return calculated fields
        for ds in filtered:
            ds["fields"] = [f for f in ds.get("fields", []) if f.get("__typename") == "CalculatedField"]
        return {"datasources": filtered}

    return result


@mcp.tool()
async def run_metadata_graphql(query: str) -> dict:
    """
    Execute a raw Metadata GraphQL query against the Tableau instance.

    Args:
        query: The GraphQL query string
    """
    return await _graphql(query)


# ── Vizportal ID Resolution ────────────────────────────────────────────────
@mcp.tool()
async def find_workbook_by_url_id(vizportal_url_id: str) -> dict:
    """
    Resolve a Tableau URL numeric ID (e.g. from /workbooks/1699) to a workbook LUID.
    Tableau URLs use vizportal numeric IDs, but the REST API needs LUIDs.

    Args:
        vizportal_url_id: The numeric ID from the Tableau URL (e.g. '1699')
    """
    query = '{ workbooks { luid name vizportalUrlId } }'
    result = await _graphql(query)
    workbooks = result.get("data", {}).get("workbooks", [])
    match = [wb for wb in workbooks if str(wb.get("vizportalUrlId", "")) == str(vizportal_url_id)]
    if match:
        return match[0]
    return {"error": f"No workbook found with vizportalUrlId={vizportal_url_id}"}


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
