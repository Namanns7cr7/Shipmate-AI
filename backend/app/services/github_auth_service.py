"""
GitHub OAuth 2.0 Authentication Service

Handles the complete GitHub OAuth flow:
1. Generate authorization URL
2. Exchange authorization code for access token
3. Fetch authenticated user profile
4. Manage session tokens
"""

import os
import logging
import httpx
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.services import sqlite_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persistent OAuth state store (SQLite)
# ---------------------------------------------------------------------------
# Connection lifecycle + location are owned by the shared sqlite_store. The
# OAUTH_STATE_DB env var still wins as a legacy override (test fixtures rely on
# it); otherwise the file lives under SHIPMATE_STORE_DIR (default /tmp) — note
# this moved OUT of the source tree, where it used to sit next to this module.
# ---------------------------------------------------------------------------

_STORE = "oauth"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_states (
    state        TEXT PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at   REAL NOT NULL
);
"""

sqlite_store.register(
    _STORE,
    filename="shipmate_oauth.db",
    legacy_env="OAUTH_STATE_DB",
    schema=_SCHEMA,
)


def _get_db_path() -> str:
    """Resolved path for the OAuth-state store (honours OAUTH_STATE_DB)."""
    return sqlite_store.db_path(_STORE)


def _get_conn():
    """Per-(thread, path) cached connection from the shared store manager.
    No longer opened/closed per call — the cache owns the lifecycle."""
    return sqlite_store.connect(_STORE)


def _store_state(state: str, redirect_uri: str) -> None:
    """Persist a new OAuth state token."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO oauth_states (state, redirect_uri, created_at) VALUES (?, ?, ?)",
        (state, redirect_uri, datetime.now().timestamp()),
    )
    conn.commit()


def _consume_state(state: str) -> Optional[str]:
    """
    Atomically validate and delete an OAuth state token.

    Returns the stored redirect_uri if the token exists and has not expired,
    or None if it is missing.  Raises ValueError if the token has expired.
    """
    conn = _get_conn()
    row = conn.execute(
        "SELECT redirect_uri, created_at FROM oauth_states WHERE state = ?",
        (state,),
    ).fetchone()

    if row is None:
        return None

    redirect_uri, created_ts = row[0], row[1]
    age = datetime.now().timestamp() - created_ts
    # Always delete — single-use regardless of outcome
    conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()

    if age > 600:  # 10-minute TTL
        raise ValueError("State parameter expired. Please try again.")

    return redirect_uri


def _purge_expired_states() -> None:
    """Remove state tokens older than 10 minutes (housekeeping)."""
    cutoff = datetime.now().timestamp() - 600
    conn = _get_conn()
    conn.execute("DELETE FROM oauth_states WHERE created_at < ?", (cutoff,))
    conn.commit()


# ---------------------------------------------------------------------------


class GitHubAuthService:
    """GitHub OAuth 2.0 authentication service"""

    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com"

    # NOTE: the in-memory `_tokens` dict was RETIRED. It was a fourth place the
    # raw token lived (alongside localStorage, request bodies, and the
    # ci_watch_state column) — the exact scatter the session vault removed. The
    # vault (session_store) is now the single source of truth for token lifecycle
    # and validity; this class no longer caches raw tokens at all.

    @classmethod
    def get_auth_url(cls, redirect_uri: str) -> str:
        """
        Generate GitHub OAuth authorization URL

        Args:
            redirect_uri: Callback URL where user is redirected after auth

        Returns:
            Authorization URL for user to click

        Raises:
            ValueError: If GITHUB_CLIENT_ID not configured
        """
        client_id = os.getenv("GITHUB_CLIENT_ID")
        if not client_id:
            raise ValueError(
                "GITHUB_CLIENT_ID not configured. "
                "Set GITHUB_CLIENT_ID in .env file."
            )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Persist state in SQLite (survives worker restarts, TTL=10 min)
        _store_state(state, redirect_uri)

        # Opportunistically purge old tokens
        try:
            _purge_expired_states()
        except Exception:  # pragma: no cover
            pass

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            # `workflow` is REQUIRED to create/edit files under .github/workflows/
            # via the Contents API — GitHub returns 404 (not 403!) if missing.
            "scope": "repo workflow read:user user:email",
            "state": state,
            "allow_signup": "true",
        }

        auth_url = f"{cls.GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        return auth_url

    @classmethod
    async def exchange_code_for_token(cls, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange GitHub authorization code for access token.

        Validates the state parameter against the persistent SQLite store.
        Raises ValueError if the state is missing or expired.
        """
        # Validate state — hard reject if not found or expired
        redirect_uri = _consume_state(state)
        if redirect_uri is None:
            raise ValueError(
                "Invalid or unknown OAuth state parameter. "
                "Please restart the login flow."
            )

        # Get OAuth credentials
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError(
                "GitHub OAuth credentials not configured. "
                "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env"
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    cls.GITHUB_TOKEN_URL,
                    json={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                token_data = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to exchange code for token: {str(e)}")

        if "error" in token_data:
            raise ValueError(
                f"GitHub OAuth error: {token_data.get('error_description', token_data.get('error'))}"
            )

        # The raw token is NOT cached here — the callback route vaults it via
        # session_store and hands the client an opaque session id. Returning the
        # token_data (incl. the raw token) to the immediate caller is fine: it's
        # the OAuth-exchange boundary, where the token is minted into the vault.
        return token_data

    @classmethod
    async def get_user_profile(cls, access_token: str) -> Dict[str, Any]:
        """
        Fetch authenticated GitHub user profile

        Args:
            access_token: GitHub OAuth access token

        Returns:
            User profile data: login, name, avatar_url, bio, etc.

        Raises:
            ValueError: If token invalid or API call fails
        """
        if not access_token:
            raise ValueError("Access token required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.GITHUB_API_URL}/user",
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                user_data = response.json()
        except httpx.HTTPError as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                raise ValueError("Invalid or expired GitHub access token")
            raise ValueError(f"Failed to fetch user profile: {str(e)}")

        # Extract and return essential user info
        return {
            "id": user_data.get("id"),
            "login": user_data.get("login"),
            "name": user_data.get("name", user_data.get("login")),
            "avatar_url": user_data.get("avatar_url"),
            "bio": user_data.get("bio"),
            "company": user_data.get("company"),
            "blog": user_data.get("blog"),
            "location": user_data.get("location"),
            "email": user_data.get("email"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "following": user_data.get("following"),
            "html_url": user_data.get("html_url"),
            "created_at": user_data.get("created_at"),
            "updated_at": user_data.get("updated_at"),
        }

    @classmethod
    async def get_user_repositories(cls, access_token: str) -> list:
        """
        Fetch authenticated user's repositories from real GitHub API

        Args:
            access_token: GitHub OAuth access token

        Returns:
            List of user repositories with metadata

        Raises:
            ValueError: If token invalid or API call fails
        """
        if not access_token:
            raise ValueError("Access token required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.GITHUB_API_URL}/user/repos",
                    params={
                        "sort": "updated",
                        "direction": "desc",
                        "per_page": 100,
                        "type": "owner",
                    },
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                repos = response.json()
        except httpx.HTTPError as e:
            if "401" in str(e):
                raise ValueError("Invalid or expired GitHub access token")
            raise ValueError(f"Failed to fetch repositories: {str(e)}")

        # Format repository data
        formatted_repos = []
        for repo in repos:
            formatted_repos.append(
                {
                    "id": repo.get("id"),
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "html_url": repo.get("html_url"),
                    "private": repo.get("private"),
                    "default_branch": repo.get("default_branch", "main"),
                    "language": repo.get("language"),
                    "stargazers_count": repo.get("stargazers_count"),
                    "watchers_count": repo.get("watchers_count"),
                    "forks_count": repo.get("forks_count"),
                    "updated_at": repo.get("updated_at"),
                    "created_at": repo.get("created_at"),
                    "owner": {
                        "login": repo.get("owner", {}).get("login"),
                        "avatar_url": repo.get("owner", {}).get("avatar_url"),
                        "html_url": repo.get("owner", {}).get("html_url"),
                    },
                }
            )

        return formatted_repos

    @classmethod
    async def get_repository_branches(
        cls,
        access_token: str,
        owner: str,
        repo_name: str,
    ) -> list:
        """
        Fetch branches for a GitHub repository

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo_name: Repository name

        Returns:
            List of branch objects with commit info
        """
        if not access_token:
            raise ValueError("Access token required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.GITHUB_API_URL}/repos/{owner}/{repo_name}/branches",
                    params={"per_page": 50},
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                branches = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch branches: {str(e)}")

        # Format branch data
        formatted_branches = []
        for branch in branches:
            formatted_branches.append(
                {
                    "name": branch.get("name"),
                    "commit": {
                        "sha": branch.get("commit", {}).get("sha", "")[:7],
                        "url": branch.get("commit", {}).get("url"),
                    },
                    "protected": branch.get("protected", False),
                }
            )

        return formatted_branches

    @classmethod
    async def get_repository_pulls(
        cls,
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open",
    ) -> list:
        """
        Fetch pull requests for a repository

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner
            repo_name: Repository name
            state: "open", "closed", or "all"

        Returns:
            List of pull requests
        """
        if not access_token:
            raise ValueError("Access token required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.GITHUB_API_URL}/repos/{owner}/{repo_name}/pulls",
                    params={"state": state, "per_page": 50},
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                pulls = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch pull requests: {str(e)}")

        # Format PR data
        formatted_pulls = []
        for pr in pulls:
            formatted_pulls.append(
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "html_url": pr.get("html_url"),
                    "user": {
                        "login": pr.get("user", {}).get("login"),
                        "avatar_url": pr.get("user", {}).get("avatar_url"),
                    },
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                }
            )

        return formatted_pulls

    @classmethod
    async def get_repository_issues(
        cls,
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open",
    ) -> list:
        """
        Fetch issues for a repository

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner
            repo_name: Repository name
            state: "open", "closed", or "all"

        Returns:
            List of issues
        """
        if not access_token:
            raise ValueError("Access token required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.GITHUB_API_URL}/repos/{owner}/{repo_name}/issues",
                    params={"state": state, "per_page": 50},
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                issues = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch issues: {str(e)}")

        # Filter out pull requests (they show up as issues)
        formatted_issues = []
        for issue in issues:
            if "pull_request" not in issue:
                formatted_issues.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "html_url": issue.get("html_url"),
                        "user": {
                            "login": issue.get("user", {}).get("login"),
                            "avatar_url": issue.get("user", {}).get("avatar_url"),
                        },
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                    }
                )

        return formatted_issues

    @classmethod
    def clear_token(cls, access_token: str) -> None:
        """Logout hook. The in-memory token cache is gone — the vault owns token
        lifecycle now, and the logout route already calls
        session_store.revoke_token(). Kept as a no-op so the route's call site
        doesn't need to change and any external caller stays compatible."""
        return None
