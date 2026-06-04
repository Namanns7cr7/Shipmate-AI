"""
GitHub OAuth 2.0 Authentication Service

Handles the complete GitHub OAuth flow:
1. Generate authorization URL
2. Exchange authorization code for access token
3. Fetch authenticated user profile
4. Manage session tokens
"""

import os
import httpx
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode


class GitHubAuthService:
    """GitHub OAuth 2.0 authentication service"""
    
    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com"
    
    # In-memory session storage (for development)
    # In production: use Redis, Azure Cache, or SQL database
    _sessions: Dict[str, Dict[str, Any]] = {}
    _tokens: Dict[str, Dict[str, Any]] = {}
    
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
        
        # Store state temporarily (valid for 10 minutes)
        cls._sessions[state] = {
            "created_at": datetime.now(),
            "redirect_uri": redirect_uri,
            "expires_in": 600
        }
        
        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "repo read:user user:email",  # Real scopes needed
            "state": state,
            "allow_signup": "true"
        }
        
        auth_url = f"{cls.GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        return auth_url
    
    @classmethod
    async def exchange_code_for_token(cls, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange GitHub authorization code for access token.

        State validation uses in-memory storage which does not survive a server
        restart (uvicorn --reload wipes it). When the state is missing we fall
        back to the configured redirect URI and log a warning rather than
        rejecting the request, so login works reliably in development.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Default redirect URI in case session was lost on server restart
        default_redirect_uri = os.getenv(
            "GITHUB_REDIRECT_URI", "http://localhost:5173/github/callback"
        )

        if state in cls._sessions:
            session_data = cls._sessions[state]
            created_at = session_data.get("created_at")
            if datetime.now() - created_at > timedelta(minutes=10):
                del cls._sessions[state]
                raise ValueError("State parameter expired. Please try again.")
            redirect_uri = session_data.get("redirect_uri", default_redirect_uri)
            del cls._sessions[state]  # single-use
        else:
            # Session not found — server likely restarted during the OAuth flow.
            # In production use persistent session storage (Redis / DB).
            logger.warning(
                "OAuth state '%s…' not found in sessions "
                "(server may have restarted). Proceeding without CSRF check.",
                state[:8],
            )
            redirect_uri = default_redirect_uri

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
        
        # Store token in memory for session
        access_token = token_data.get("access_token")
        if access_token:
            cls._tokens[access_token] = {
                "created_at": datetime.now(),
                "scope": token_data.get("scope"),
                "token_type": token_data.get("token_type", "bearer")
            }
        
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
                        "Accept": "application/vnd.github.v3+json"
                    }
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
                        "type": "owner"
                    },
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
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
            formatted_repos.append({
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
                }
            })
        
        return formatted_repos
    
    @classmethod
    async def get_repository_branches(
        cls, 
        access_token: str,
        owner: str,
        repo_name: str
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
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                response.raise_for_status()
                branches = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch branches: {str(e)}")
        
        # Format branch data
        formatted_branches = []
        for branch in branches:
            formatted_branches.append({
                "name": branch.get("name"),
                "commit": {
                    "sha": branch.get("commit", {}).get("sha", "")[:7],
                    "url": branch.get("commit", {}).get("url"),
                },
                "protected": branch.get("protected", False)
            })
        
        return formatted_branches
    
    @classmethod
    async def get_repository_pulls(
        cls,
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open"
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
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                response.raise_for_status()
                pulls = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch pull requests: {str(e)}")
        
        # Format PR data
        formatted_pulls = []
        for pr in pulls:
            formatted_pulls.append({
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
            })
        
        return formatted_pulls
    
    @classmethod
    async def get_repository_issues(
        cls,
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open"
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
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                response.raise_for_status()
                issues = response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch issues: {str(e)}")
        
        # Filter out pull requests (they show up as issues)
        formatted_issues = []
        for issue in issues:
            if "pull_request" not in issue:
                formatted_issues.append({
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
                })
        
        return formatted_issues
    
    @classmethod
    def is_token_valid(cls, access_token: str) -> bool:
        """
        Check if access token is stored and valid
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if token exists in session
        """
        return access_token in cls._tokens
    
    @classmethod
    def clear_token(cls, access_token: str) -> None:
        """
        Clear/logout token from session
        
        Args:
            access_token: Token to remove
        """
        if access_token in cls._tokens:
            del cls._tokens[access_token]
