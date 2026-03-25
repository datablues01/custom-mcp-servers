"""
GitHub MCP Server
=================
Exposes GitHub REST API endpoints for repo management:
  - Repository info
  - Branch listing & management
  - File reading
  - Commit history
  - Pull requests (list, create, get, merge)
  - Compare branches

Env vars:
  GITHUB_TOKEN    - Personal access token
  GITHUB_REPO     - Default repo URL (e.g. https://github.com/gympass/looker-lookml)
  GITHUB_INSTANCE_NAME - Instance label for MCP (default: "github")
"""

import os
import base64
import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
INSTANCE_NAME = os.environ.get("GITHUB_INSTANCE_NAME", "github")
API_BASE = "https://api.github.com"

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _parse_repo(repo: str) -> tuple[str, str]:
    """Parse owner/repo from a GitHub URL or 'owner/repo' string."""
    r = repo or GITHUB_REPO
    if not r:
        raise ValueError("No repo specified. Pass repo= or set GITHUB_REPO.")
    r = r.rstrip("/").removesuffix(".git")
    if "github.com" in r:
        parts = r.split("github.com/")[-1].split("/")
        return parts[0], parts[1]
    parts = r.split("/")
    return parts[0], parts[1]


async def _api(method: str, path: str, **kwargs) -> dict | list | str:
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=60.0,
    ) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── Repository ─────────────────────────────────────────────────────────────
@mcp.tool()
async def get_repo(repo: str = "") -> dict:
    """
    Get repository info (name, description, default branch, visibility).

    Args:
        repo: GitHub repo URL or 'owner/repo' (defaults to GITHUB_REPO env var)
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}")


# ── Branches ───────────────────────────────────────────────────────────────
@mcp.tool()
async def list_branches(repo: str = "", per_page: int = 30) -> list:
    """
    List branches in a repository.

    Args:
        repo: GitHub repo URL or 'owner/repo'
        per_page: Results per page (default 30)
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/branches?per_page={per_page}")


@mcp.tool()
async def get_branch(branch: str, repo: str = "") -> dict:
    """
    Get branch details including latest commit.

    Args:
        branch: Branch name
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/branches/{branch}")


@mcp.tool()
async def compare_branches(base: str, head: str, repo: str = "") -> dict:
    """
    Compare two branches. Shows commits, files changed, and diff stats.

    Args:
        base: Base branch (e.g. 'master')
        head: Head branch (e.g. 'feature-branch')
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/compare/{base}...{head}")


# ── Files ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def get_file(path: str, ref: str = "", repo: str = "") -> dict:
    """
    Get a file's content from the repository. Returns decoded content.

    Args:
        path: File path (e.g. 'views/my_view.view.lkml')
        ref: Branch or commit SHA (defaults to default branch)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    params = {}
    if ref:
        params["ref"] = ref
    data = await _api("GET", f"/repos/{owner}/{name}/contents/{path}", params=params)
    if isinstance(data, dict) and data.get("encoding") == "base64":
        data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")
        del data["content"]  # Remove base64 blob to save context
    return data


@mcp.tool()
async def list_directory(path: str = "", ref: str = "", repo: str = "") -> list:
    """
    List files and directories at a path in the repository.

    Args:
        path: Directory path (empty for root)
        ref: Branch or commit SHA (defaults to default branch)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    params = {}
    if ref:
        params["ref"] = ref
    data = await _api("GET", f"/repos/{owner}/{name}/contents/{path}", params=params)
    if isinstance(data, list):
        return [{"name": f["name"], "type": f["type"], "path": f["path"], "size": f.get("size", 0)} for f in data]
    return data


# ── Commits ────────────────────────────────────────────────────────────────
@mcp.tool()
async def list_commits(branch: str = "", path: str = "", per_page: int = 10, repo: str = "") -> list:
    """
    List recent commits. Optionally filter by branch and/or file path.

    Args:
        branch: Branch name (defaults to default branch)
        path: File path to filter commits for
        per_page: Number of commits (default 10)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    params = {"per_page": per_page}
    if branch:
        params["sha"] = branch
    if path:
        params["path"] = path
    return await _api("GET", f"/repos/{owner}/{name}/commits", params=params)


@mcp.tool()
async def get_commit(sha: str, repo: str = "") -> dict:
    """
    Get a specific commit with its diff/files changed.

    Args:
        sha: Commit SHA
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/commits/{sha}")


# ── Pull Requests ──────────────────────────────────────────────────────────
@mcp.tool()
async def list_pull_requests(state: str = "open", per_page: int = 10, repo: str = "") -> list:
    """
    List pull requests.

    Args:
        state: 'open', 'closed', or 'all' (default 'open')
        per_page: Results per page (default 10)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/pulls?state={state}&per_page={per_page}")


@mcp.tool()
async def get_pull_request(pr_number: int, repo: str = "") -> dict:
    """
    Get pull request details including diff stats.

    Args:
        pr_number: PR number
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/pulls/{pr_number}")


@mcp.tool()
async def get_pr_files(pr_number: int, repo: str = "") -> list:
    """
    Get the list of files changed in a pull request.

    Args:
        pr_number: PR number
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/pulls/{pr_number}/files")


@mcp.tool()
async def get_pr_comments(pr_number: int, repo: str = "") -> list:
    """
    Get review comments on a pull request.

    Args:
        pr_number: PR number
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api("GET", f"/repos/{owner}/{name}/pulls/{pr_number}/comments")


@mcp.tool()
async def create_pull_request(title: str, head: str, base: str = "master", body: str = "", repo: str = "") -> dict:
    """
    Create a new pull request.

    Args:
        title: PR title
        head: Source branch name
        base: Target branch name (default 'master')
        body: PR description/body
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    return await _api(
        "POST",
        f"/repos/{owner}/{name}/pulls",
        json={"title": title, "head": head, "base": base, "body": body},
    )


# ── Write / Commit ─────────────────────────────────────────────────────────
@mcp.tool()
async def create_file(path: str, content: str, message: str, branch: str = "", repo: str = "") -> dict:
    """
    Create a new file in the repo and commit it.

    Args:
        path: File path (e.g. 'views/new_view.view.lkml')
        content: File content (plain text, will be base64-encoded automatically)
        message: Commit message
        branch: Branch to commit to (defaults to repo's default branch)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if branch:
        body["branch"] = branch
    return await _api("PUT", f"/repos/{owner}/{name}/contents/{path}", json=body)


@mcp.tool()
async def update_file(path: str, content: str, message: str, branch: str = "", repo: str = "") -> dict:
    """
    Update an existing file in the repo and commit it.
    Automatically fetches the current file's SHA (required by GitHub API).

    Args:
        path: File path (e.g. 'views/my_view.view.lkml')
        content: New file content (plain text)
        message: Commit message
        branch: Branch to commit to (defaults to repo's default branch)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    # Get current file SHA
    params = {}
    if branch:
        params["ref"] = branch
    current = await _api("GET", f"/repos/{owner}/{name}/contents/{path}", params=params)
    sha = current["sha"]

    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "sha": sha,
    }
    if branch:
        body["branch"] = branch
    return await _api("PUT", f"/repos/{owner}/{name}/contents/{path}", json=body)


@mcp.tool()
async def delete_file(path: str, message: str, branch: str = "", repo: str = "") -> dict:
    """
    Delete a file from the repo and commit the deletion.

    Args:
        path: File path to delete
        message: Commit message
        branch: Branch to commit to (defaults to repo's default branch)
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    # Get current file SHA
    params = {}
    if branch:
        params["ref"] = branch
    current = await _api("GET", f"/repos/{owner}/{name}/contents/{path}", params=params)
    sha = current["sha"]

    body = {"message": message, "sha": sha}
    if branch:
        body["branch"] = branch
    return await _api("DELETE", f"/repos/{owner}/{name}/contents/{path}", json=body)


# ── Branch Management ──────────────────────────────────────────────────────
@mcp.tool()
async def create_branch(branch_name: str, from_branch: str = "master", repo: str = "") -> dict:
    """
    Create a new branch from an existing branch.

    Args:
        branch_name: Name for the new branch
        from_branch: Source branch to branch from (default 'master')
        repo: GitHub repo URL or 'owner/repo'
    """
    owner, name = _parse_repo(repo)
    # Get the SHA of the source branch
    source = await _api("GET", f"/repos/{owner}/{name}/git/ref/heads/{from_branch}")
    sha = source["object"]["sha"]
    return await _api(
        "POST",
        f"/repos/{owner}/{name}/git/refs",
        json={"ref": f"refs/heads/{branch_name}", "sha": sha},
    )


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
