"""Centralized GitHub API client factory.

This module provides a single shared GitHubClient factory to eliminate
duplication of header/auth setup logic across service files. All services
should import and use this factory rather than constructing their own
GitHub API clients.
"""

import os
from typing import Dict, Optional

# Single source of truth for the GitHub REST base URL and the per-request auth
# headers. Four services (github_api_service, github_actions_service,
# branch_pruner, github_pr_service) previously each defined a byte-identical
# `_headers(token)` and `_BASE` — they now delegate here so token-rotation or a
# base-URL change is a one-line edit.
GITHUB_API_BASE = "https://api.github.com"


def gh_headers(token: str) -> Dict[str, str]:
    """Standard GitHub REST headers for a per-request user OAuth token.

    Matches what the services send today (token auth + v3 Accept + API-version
    pin), kept identical to avoid behavior drift. `token <t>` is the scheme
    GitHub's REST v3 expects for OAuth user tokens."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class GitHubClient:
    """GitHub API client with centralized auth and header configuration."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with optional token.

        Args:
            token: GitHub personal access token or app token. If not provided,
                   falls back to GITHUB_TOKEN environment variable.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        """Build standard GitHub API headers with auth.

        Returns:
            Dictionary of headers including Authorization if token is available.
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ShipMate-AI/2.0.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def get_headers(self) -> dict[str, str]:
        """Return a copy of the standard headers for this client.

        Returns:
            Dictionary of headers to use in GitHub API requests.
        """
        return self.headers.copy()


def create_github_client(token: Optional[str] = None) -> GitHubClient:
    """Factory function to create a GitHub API client.

    This is the single point of instantiation for GitHub clients across
    the application. All services should use this factory rather than
    constructing GitHubClient directly.

    Args:
        token: Optional GitHub token. If not provided, uses GITHUB_TOKEN env var.

    Returns:
        Configured GitHubClient instance.
    """
    return GitHubClient(token=token)
