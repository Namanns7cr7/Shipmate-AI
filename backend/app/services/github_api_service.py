"""
GitHub Service — Real GitHub API Integration

Uses PyGithub library to fetch real data from GitHub API.
Handles repositories, branches, pull requests, and issues.
"""

import os
from typing import List, Dict, Any, Optional
from github import Github
from github.GithubException import GithubException


class GitHubAPIService:
    """
    GitHub API service using PyGithub library.
    Requires GitHub Personal Access Token for authentication.
    """
    
    @staticmethod
    def _get_github_client(access_token: str) -> Github:
        """Get authenticated GitHub client"""
        return Github(access_token)
    
    @staticmethod
    async def get_user_repositories(access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch authenticated user's repositories
        
        Args:
            access_token: GitHub OAuth access token
            
        Returns:
            List of repository objects with metadata
        """
        try:
            g = GitHubAPIService._get_github_client(access_token)
            user = g.get_user()
            
            repos = []
            for repo in user.get_repos(type="owner"):
                repos.append({
                    "id": str(repo.id),
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description or "",
                    "url": repo.html_url,
                    "language": repo.language or "Unknown",
                    "stars": repo.stargazers_count,
                    "watchers": repo.watchers_count,
                    "forks": repo.forks_count,
                    "is_private": repo.private,
                    "default_branch": repo.default_branch,
                    "created_at": repo.created_at.isoformat(),
                    "updated_at": repo.updated_at.isoformat(),
                    "tech_stack": [repo.language] if repo.language else []
                })
            
            return repos
        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch repositories: {str(e)}")
    
    @staticmethod
    async def get_repository_branches(
        access_token: str,
        owner: str,
        repo_name: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all branches for a repository
        
        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo_name: Repository name
            
        Returns:
            List of branch objects with commit info
        """
        try:
            g = GitHubAPIService._get_github_client(access_token)
            repo = g.get_user(owner).get_repo(repo_name)
            
            branches = []
            for branch in repo.get_branches():
                branches.append({
                    "name": branch.name,
                    "commit": {
                        "sha": branch.commit.sha[:7],  # Short SHA
                        "message": branch.commit.commit.message.split("\n")[0],  # First line
                        "author": branch.commit.commit.author.name if branch.commit.commit.author else "Unknown",
                        "date": branch.commit.commit.author.date.isoformat() if branch.commit.commit.author else ""
                    },
                    "protected": branch.protected
                })
            
            return branches
        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch branches: {str(e)}")
    
    @staticmethod
    async def get_repository_pulls(
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        Fetch pull requests for a repository
        
        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo_name: Repository name
            state: "open", "closed", or "all"
            
        Returns:
            List of pull request objects
        """
        try:
            g = GitHubAPIService._get_github_client(access_token)
            repo = g.get_user(owner).get_repo(repo_name)
            
            pulls = []
            for pr in repo.get_pulls(state=state):
                pulls.append({
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body or "",
                    "state": pr.state,
                    "author": pr.user.login if pr.user else "Unknown",
                    "author_avatar": pr.user.avatar_url if pr.user else "",
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat(),
                    "merged": pr.merged,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "head_branch": pr.head.ref,
                    "base_branch": pr.base.ref,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                    "url": pr.html_url
                })
            
            return pulls
        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch pull requests: {str(e)}")
    
    @staticmethod
    async def get_repository_issues(
        access_token: str,
        owner: str,
        repo_name: str,
        state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        Fetch issues for a repository
        
        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo_name: Repository name
            state: "open", "closed", or "all"
            
        Returns:
            List of issue objects
        """
        try:
            g = GitHubAPIService._get_github_client(access_token)
            repo = g.get_user(owner).get_repo(repo_name)
            
            issues = []
            for issue in repo.get_issues(state=state):
                # Skip pull requests (they're also returned as issues)
                if issue.pull_request:
                    continue
                
                issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body or "",
                    "state": issue.state,
                    "author": issue.user.login if issue.user else "Unknown",
                    "author_avatar": issue.user.avatar_url if issue.user else "",
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                    "labels": [label.name for label in issue.labels],
                    "assignees": [assignee.login for assignee in issue.assignees],
                    "comments": issue.comments,
                    "url": issue.html_url
                })
            
            return issues
        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch issues: {str(e)}")
    
    @staticmethod
    async def get_repository_contents(
        access_token: str,
        owner: str,
        repo_name: str,
        path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Fetch file tree for a repository
        
        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo_name: Repository name
            path: Directory path (empty for root)
            
        Returns:
            List of file objects with metadata
        """
        try:
            g = GitHubAPIService._get_github_client(access_token)
            repo = g.get_user(owner).get_repo(repo_name)
            
            contents = []
            try:
                items = repo.get_contents(path if path else "")
                if isinstance(items, list):
                    for item in items:
                        contents.append({
                            "name": item.name,
                            "path": item.path,
                            "type": item.type,  # "file" or "dir"
                            "size": item.size if item.type == "file" else 0,
                            "url": item.html_url
                        })
                else:
                    contents.append({
                        "name": items.name,
                        "path": items.path,
                        "type": items.type,
                        "size": items.size if items.type == "file" else 0,
                        "url": items.html_url
                    })
            except GithubException:
                # Path doesn't exist or empty
                pass
            
            return contents
        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch repository contents: {str(e)}")
