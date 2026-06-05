"""Shared GitHub API client for authenticated requests.

This module provides a single authenticated GitHub client that centralizes
token management, rate-limit handling, and HTTP session lifecycle.
"""

import os
from typing import Optional

import httpx


class GitHubClient:
    """Authenticated GitHub API client with centralized token and session management.
    
    Attributes:
        token: GitHub personal access token or OAuth token.
        base_url: GitHub API base URL (default: https://api.github.com).
        timeout: Request timeout in seconds (default: 30).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ):
        """Initialize the GitHub client.
        
        Args:
            token: GitHub token. If None, reads from GITHUB_TOKEN env var.
            base_url: GitHub API base URL.
            timeout: Request timeout in seconds.
        """
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = base_url
        self.timeout = timeout
        self._session: Optional[httpx.Client] = None

    @property
    def session(self) -> httpx.Client:
        """Lazy-initialize and return the httpx session.
        
        Returns:
            An httpx.Client configured with GitHub auth headers.
        """
        if self._session is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            headers["Accept"] = "application/vnd.github.v3+json"
            self._session = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._session

    def close(self) -> None:
        """Close the underlying httpx session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get(self, path: str, **kwargs) -> httpx.Response:
        """Perform a GET request.
        
        Args:
            path: API endpoint path (relative to base_url).
            **kwargs: Additional arguments passed to httpx.Client.get().
        
        Returns:
            httpx.Response object.
        """
        return self.session.get(path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        """Perform a POST request.
        
        Args:
            path: API endpoint path (relative to base_url).
            **kwargs: Additional arguments passed to httpx.Client.post().
        
        Returns:
            httpx.Response object.
        """
        return self.session.post(path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        """Perform a PUT request.
        
        Args:
            path: API endpoint path (relative to base_url).
            **kwargs: Additional arguments passed to httpx.Client.put().
        
        Returns:
            httpx.Response object.
        """
        return self.session.put(path, **kwargs)

    def patch(self, path: str, **kwargs) -> httpx.Response:
        """Perform a PATCH request.
        
        Args:
            path: API endpoint path (relative to base_url).
            **kwargs: Additional arguments passed to httpx.Client.patch().
        
        Returns:
            httpx.Response object.
        """
        return self.session.patch(path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        """Perform a DELETE request.
        
        Args:
            path: API endpoint path (relative to base_url).
            **kwargs: Additional arguments passed to httpx.Client.delete().
        
        Returns:
            httpx.Response object.
        """
        return self.session.delete(path, **kwargs)


# Module-level singleton instance for convenient import and use.
github_client = GitHubClient()
