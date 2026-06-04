"""
Repo Analysis Service

Fetches the repo file tree and a curated set of key files from GitHub,
then builds the context dict consumed by the ShipMate orchestrator.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from .github_api_service import GitHubAPIService

# Files we always try to fetch (order = priority)
_KEY_FILE_NAMES = [
    "README.md", "readme.md", "README.rst", "README",
    "package.json",
    "requirements.txt", "requirements-dev.txt",
    "pyproject.toml", "setup.py",
    "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
    "tsconfig.json",
    "go.mod",
    "Cargo.toml",
    ".gitignore",
    "Makefile",
    "nginx.conf",
    "main.py", "app.py", "server.py",
    "index.ts", "index.js", "main.ts",
]

# Max files to fetch (GitHub API rate: 5000 req/hr for authenticated)
_MAX_KEY_FILES = 18


class RepoAnalysisService:

    @classmethod
    async def build_context(
        cls,
        token: str,
        owner: str,
        repo: str,
        branch: str = "main",
        pr_number: Optional[int] = None,
        feature_context: str = "",
    ) -> Dict[str, Any]:
        """
        Fetches repo data from GitHub and returns the context dict
        expected by ShipMateOrchestrator.run().
        """
        # Fetch repo info and file tree in parallel
        repo_info, file_tree = await asyncio.gather(
            GitHubAPIService.get_repo_info(token, owner, repo),
            GitHubAPIService.get_file_tree(token, owner, repo, branch),
        )

        # Determine which files to fetch
        files_to_fetch = cls._select_key_files(file_tree)

        # Fetch key file contents in parallel (bounded concurrency)
        key_files = await cls._fetch_files(token, owner, repo, files_to_fetch)

        # Optional PR context
        pr_info = None
        if pr_number:
            try:
                pr_info = await GitHubAPIService.get_pr_info(token, owner, repo, pr_number)
            except Exception:
                pass

        return {
            "repo_info": repo_info,
            "file_tree": file_tree,
            "key_files": key_files,
            "branch": branch,
            "pr_info": pr_info,
            "feature_context": feature_context,
        }

    @classmethod
    def _select_key_files(cls, tree: List[str]) -> List[str]:
        """Pick files to fetch: prioritized list + first workflow yaml."""
        selected: List[str] = []
        tree_set = set(tree)

        for name in _KEY_FILE_NAMES:
            if name in tree_set:
                selected.append(name)
            if len(selected) >= _MAX_KEY_FILES:
                break

        # Add first GitHub Actions workflow if present
        workflows = [f for f in tree if ".github/workflows" in f and f.endswith((".yml", ".yaml"))]
        if workflows and workflows[0] not in selected:
            selected.append(workflows[0])

        # Add first entry file not yet in list
        ENTRY_NAMES = {"main.py", "app.py", "server.py", "index.ts", "index.js", "main.ts", "main.js"}
        for f in tree:
            if Path(f).name in ENTRY_NAMES and f not in selected:
                selected.append(f)
                break

        return selected[:_MAX_KEY_FILES]

    @classmethod
    async def _fetch_files(
        cls, token: str, owner: str, repo: str, paths: List[str]
    ) -> Dict[str, str]:
        """Fetch files with bounded concurrency (max 6 parallel requests)."""
        sem = asyncio.Semaphore(6)

        async def fetch_one(path: str):
            async with sem:
                content = await GitHubAPIService.get_file_content(token, owner, repo, path)
                return path, content

        results = await asyncio.gather(*[fetch_one(p) for p in paths], return_exceptions=True)

        key_files: Dict[str, str] = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            path, content = result
            if content is not None:
                key_files[Path(path).name] = content  # store by filename for easy agent access
                key_files[path] = content              # also store by full path

        return key_files
