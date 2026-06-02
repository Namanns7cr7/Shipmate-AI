"""
GitHub Service — Handles GitHub App integration and mock repository data.
This service abstracts GitHub API calls and provides mock data for demo purposes.
Real GitHub App integration can be added later.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class GitHubService:
    """
    GitHub integration service.
    - For now: returns mock repositories and branches
    - Later: Connects to real GitHub App with read-only access
    """

    MOCK_REPOS = [
        {
            "id": "repo-1",
            "name": "shipmate-frontend",
            "full_name": "myorg/shipmate-frontend",
            "description": "React + TypeScript frontend for ShipMate AI",
            "url": "https://github.com/myorg/shipmate-frontend",
            "language": "TypeScript",
            "stars": 42,
            "watchers": 8,
            "forks": 3,
            "tech_stack": ["React", "TypeScript", "Tailwind CSS", "Vite", "Framer Motion"],
        },
        {
            "id": "repo-2",
            "name": "shipmate-backend",
            "full_name": "myorg/shipmate-backend",
            "description": "FastAPI backend for production readiness analysis",
            "url": "https://github.com/myorg/shipmate-backend",
            "language": "Python",
            "stars": 38,
            "watchers": 6,
            "forks": 2,
            "tech_stack": ["FastAPI", "Python 3.11", "Pydantic", "Azure OpenAI"],
        },
        {
            "id": "repo-3",
            "name": "ecommerce-platform",
            "full_name": "myorg/ecommerce-platform",
            "description": "Full-stack e-commerce platform with microservices",
            "url": "https://github.com/myorg/ecommerce-platform",
            "language": "Node.js",
            "stars": 156,
            "watchers": 24,
            "forks": 18,
            "tech_stack": ["Node.js", "Express", "PostgreSQL", "Redis", "Docker"],
        },
        {
            "id": "repo-4",
            "name": "mobile-app",
            "full_name": "myorg/mobile-app",
            "description": "React Native mobile app",
            "url": "https://github.com/myorg/mobile-app",
            "language": "JavaScript",
            "stars": 89,
            "watchers": 12,
            "forks": 7,
            "tech_stack": ["React Native", "Expo", "Firebase"],
        },
    ]

    MOCK_BRANCHES = {
        "repo-1": [
            {"name": "main", "commit": {"sha": "abc123def456", "message": "feat: add dashboard"}},
            {"name": "develop", "commit": {"sha": "def456ghi789", "message": "refactor: sidebar navigation"}},
            {"name": "feature/auth-flow", "commit": {"sha": "ghi789jkl012", "message": "feat: GitHub OAuth integration"}},
            {"name": "feature/azure-integration", "commit": {"sha": "jkl012mno345", "message": "feat: Azure OpenAI connection"}},
        ],
        "repo-2": [
            {"name": "main", "commit": {"sha": "aaa111bbb222", "message": "release: v1.0.0"}},
            {"name": "develop", "commit": {"sha": "bbb222ccc333", "message": "feat: add report export"}},
            {"name": "feature/github-app", "commit": {"sha": "ccc333ddd444", "message": "feat: GitHub App OAuth flow"}},
            {"name": "bugfix/cors-headers", "commit": {"sha": "ddd444eee555", "message": "fix: CORS headers for production"}},
        ],
        "repo-3": [
            {"name": "main", "commit": {"sha": "xxx111yyy222", "message": "release: v2.3.1"}},
            {"name": "develop", "commit": {"sha": "yyy222zzz333", "message": "feat: add payment gateway"}},
            {"name": "feature/inventory-system", "commit": {"sha": "zzz333aaa444", "message": "feat: real-time inventory"}},
        ],
        "repo-4": [
            {"name": "main", "commit": {"sha": "ppp111qqq222", "message": "release: v1.2.0"}},
            {"name": "develop", "commit": {"sha": "qqq222rrr333", "message": "feat: push notifications"}},
        ],
    }

    @staticmethod
    async def get_repositories(github_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of repositories for the authenticated user.
        
        Later: Connect to real GitHub API using OAuth token.
        For now: Returns mock repositories.
        """
        return GitHubService.MOCK_REPOS

    @staticmethod
    async def get_branches(repo_id: str, github_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of branches for a repository.
        
        Later: Connect to real GitHub API.
        For now: Returns mock branches.
        """
        branches = GitHubService.MOCK_BRANCHES.get(repo_id, [])
        return branches if branches else GitHubService.MOCK_BRANCHES["repo-1"]

    @staticmethod
    async def get_repository_details(repo_id: str, github_token: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a repository."""
        for repo in GitHubService.MOCK_REPOS:
            if repo["id"] == repo_id:
                return repo
        return GitHubService.MOCK_REPOS[0]

    @staticmethod
    async def get_repo_content(
        repo_id: str,
        branch: str,
        file_path: str = "",
        github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get repository content and file listing.
        
        Later: Fetch from GitHub API.
        For now: Return mock file structure.
        """
        repo = await GitHubService.get_repository_details(repo_id, github_token)
        
        # Mock file structure based on tech stack
        mock_files = {
            "repo-1": [
                {"name": "src", "type": "dir", "path": "src"},
                {"name": "public", "type": "dir", "path": "public"},
                {"name": "package.json", "type": "file", "path": "package.json"},
                {"name": "tsconfig.json", "type": "file", "path": "tsconfig.json"},
                {"name": "vite.config.ts", "type": "file", "path": "vite.config.ts"},
                {"name": "tailwind.config.ts", "type": "file", "path": "tailwind.config.ts"},
                {"name": "README.md", "type": "file", "path": "README.md"},
            ],
            "repo-2": [
                {"name": "app", "type": "dir", "path": "app"},
                {"name": "tests", "type": "dir", "path": "tests"},
                {"name": "requirements.txt", "type": "file", "path": "requirements.txt"},
                {"name": "main.py", "type": "file", "path": "main.py"},
                {"name": "pytest.ini", "type": "file", "path": "pytest.ini"},
                {"name": "Dockerfile", "type": "file", "path": "Dockerfile"},
                {"name": "README.md", "type": "file", "path": "README.md"},
            ],
        }
        
        files = mock_files.get(repo_id, [])
        return {
            "repository": repo["name"],
            "branch": branch,
            "files": files,
            "last_commit": {
                "date": datetime.now().isoformat(),
                "author": "team@example.com",
                "message": f"Latest commit on {branch}",
            },
        }

    @staticmethod
    async def get_github_app_install_url() -> str:
        """
        Return the GitHub App installation URL.
        
        Later: Generate with real GitHub App ID.
        For now: Return mock URL.
        """
        return "https://github.com/apps/shipmate-ai/installations/new"

    @staticmethod
    async def exchange_github_code(code: str, state: str) -> Dict[str, Any]:
        """
        Exchange GitHub OAuth code for access token.
        
        Later: Call real GitHub OAuth endpoint.
        For now: Return mock token.
        """
        return {
            "access_token": "gho_mock_token_" + code[:8],
            "token_type": "bearer",
            "scope": "repo,user",
            "expires_in": 28800,
            "installed_at": datetime.now().isoformat(),
            "user": {
                "login": "demo-user",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
            },
        }
