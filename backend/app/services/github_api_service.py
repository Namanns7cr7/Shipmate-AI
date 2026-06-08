"""
GitHub REST API service — uses httpx for async calls.
Access tokens are never logged or stored beyond the request lifetime.
"""

import base64
import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

_BASE = "https://api.github.com"
_TIMEOUT = httpx.Timeout(20.0)

# ── File-tree TTL cache (OPP-003) ────────────────────────────────────────────
# The recursive git-tree call is the single heaviest GitHub request in the
# analyze path and it's re-issued on every analyze / build-plan run for the same
# repo+branch. A short-TTL in-process cache cuts repeat latency and keeps us well
# under the 5000 req/hr authenticated rate limit on re-runs. Keyed by
# (owner, repo, branch) — the path list doesn't depend on which authorized token
# fetched it, and it holds only file PATHS (no file contents/secrets). TTL is
# short so a freshly-pushed file shows up within the window. Disable with
# GITHUB_TREE_CACHE_TTL=0.
_TREE_CACHE_TTL_S = int(os.getenv("GITHUB_TREE_CACHE_TTL", "300"))
_tree_cache: Dict[Tuple[str, str, str], Tuple[float, List[str]]] = {}


def _tree_cache_get(key: Tuple[str, str, str]) -> Optional[List[str]]:
    if _TREE_CACHE_TTL_S <= 0:
        return None
    hit = _tree_cache.get(key)
    if hit is None:
        return None
    ts, paths = hit
    if (time.time() - ts) > _TREE_CACHE_TTL_S:
        _tree_cache.pop(key, None)
        return None
    return list(paths)


def _tree_cache_put(key: Tuple[str, str, str], paths: List[str]) -> None:
    if _TREE_CACHE_TTL_S <= 0:
        return
    _tree_cache[key] = (time.time(), list(paths))


def clear_tree_cache() -> None:
    """Drop all cached trees. For tests and explicit re-analyze invalidation."""
    _tree_cache.clear()


def _headers(token: str) -> Dict[str, str]:
    # Delegates to the single shared definition (see github_client.gh_headers).
    from app.services.github_client import gh_headers
    return gh_headers(token)


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
        """Returns a flat list of all file paths in the repo (recursive tree walk).

        Cached per (owner, repo, branch) for a short TTL — see _tree_cache. The
        cache holds only paths, so it's safe to share across authorized callers
        of the same repo."""
        cache_key = (owner, repo, branch)
        cached = _tree_cache_get(cache_key)
        if cached is not None:
            return cached

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
            paths = [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]

        _tree_cache_put(cache_key, paths)
        return paths

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
