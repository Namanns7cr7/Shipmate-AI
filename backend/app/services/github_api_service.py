"""
GitHub REST API service — uses httpx for async calls.
Access tokens are never logged or stored beyond the request lifetime.
"""

import base64
import asyncio
from typing import Any, Dict, List, Optional

import httpx

_BASE = "https://api.github.com"
_TIMEOUT = httpx.Timeout(20.0)


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class GitHubAPIService:

    # ── User / repos ──────────────────────────────────────────────────────

    @staticmethod
    async def get_user_repos(token: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/user/repos",
                headers=_headers(token),
                params={"sort": "updated", "direction": "desc", "per_page": 100, "type": "owner"},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_repo_info(token: str, owner: str, repo: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_BASE}/repos/{owner}/{repo}", headers=_headers(token))
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_branches(token: str, owner: str, repo: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/branches",
                headers=_headers(token),
                params={"per_page": 50},
            )
            resp.raise_for_status()
            return resp.json()

    # ── File tree ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_file_tree(token: str, owner: str, repo: str, branch: str = "main") -> List[str]:
        """Returns a flat list of all file paths in the repo (recursive tree walk)."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/git/trees/{branch}",
                headers=_headers(token),
                params={"recursive": "1"},
            )
            if resp.status_code == 404:
                # Branch might be "master"
                resp = await client.get(
                    f"{_BASE}/repos/{owner}/{repo}/git/trees/master",
                    headers=_headers(token),
                    params={"recursive": "1"},
                )
            resp.raise_for_status()
            data = resp.json()
            return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]

    @staticmethod
    async def get_file_content(
        token: str, owner: str, repo: str, path: str,
        ref: Optional[str] = None,
    ) -> Optional[str]:
        """Fetch and decode a single file's content from `ref` (branch/sha/tag).
        Returns None on 404 / binary files. If `ref` is None, GitHub serves
        the repo's default branch."""
        params: Dict[str, Any] = {}
        if ref:
            params["ref"] = ref
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers=_headers(token),
                params=params,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                except Exception:
                    return None
            return None

    # ── PRs ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_pr_info(token: str, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_open_pulls(token: str, owner: str, repo: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/pulls",
                headers=_headers(token),
                params={"state": "open", "per_page": 30},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_pr_files(
        token: str, owner: str, repo: str, pr_number: int, max_files: int = 300,
    ) -> List[Dict[str, Any]]:
        """Return a PR's changed files for the PRRiskAgent.

        Each item carries: filename, status (added|modified|removed|renamed),
        additions, deletions, changes, and `patch` (the unified-diff hunks for
        that file — absent for binary or very large files). Paginated at 100/page
        and capped at `max_files` so a giant PR can't blow the request budget;
        the risk heuristic only needs a representative slice."""
        out: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            page = 1
            while len(out) < max_files:
                resp = await client.get(
                    f"{_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                    headers=_headers(token),
                    params={"per_page": 100, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                out.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return out[:max_files]
