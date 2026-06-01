"""
GitHub Authentication Routes

Implements the OAuth 2.0 flow:
1. GET /auth/github/login - Redirect to GitHub
2. GET /auth/github/callback - Handle OAuth callback
3. GET /auth/github/me - Get authenticated user
4. GET /auth/github/repos - Get user repositories
5. POST /auth/github/logout - Logout
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.github_auth_service import GitHubAuthService
import os

router = APIRouter(prefix="/auth/github", tags=["github-auth"])


@router.get("/login")
async def github_login():
    """
    Initiate GitHub OAuth login flow
    
    Returns the GitHub authorization URL that frontend should redirect to.
    """
    try:
        redirect_uri = os.getenv(
            "GITHUB_REDIRECT_URI",
            "http://localhost:5173/github/callback"
        )
        auth_url = GitHubAuthService.get_auth_url(redirect_uri)
        
        return {
            "auth_url": auth_url,
            "message": "Redirect user to this URL to authenticate with GitHub"
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def github_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle GitHub OAuth callback
    
    GitHub redirects here after user authorizes the application.
    Exchanges the authorization code for an access token.
    
    Args:
        code: Authorization code from GitHub
        state: State parameter for CSRF validation
        
    Returns:
        User info and authentication status
    """
    try:
        # Exchange code for access token
        token_data = await GitHubAuthService.exchange_code_for_token(code, state)
        
        # Fetch user profile
        access_token = token_data.get("access_token")
        user_profile = await GitHubAuthService.get_user_profile(access_token)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": token_data.get("token_type", "bearer"),
            "scope": token_data.get("scope"),
            "user": user_profile,
            "message": "GitHub authentication successful"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"GitHub callback failed: {str(e)}"
        )


@router.get("/me")
async def get_authenticated_user(access_token: str = Query(...)):
    """
    Get authenticated GitHub user profile
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        User profile information
    """
    try:
        user_profile = await GitHubAuthService.get_user_profile(access_token)
        
        return {
            "authenticated": True,
            "user": user_profile
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos")
async def get_user_repositories(access_token: str = Query(...)):
    """
    Get authenticated user's repositories from GitHub
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        List of repositories owned by the authenticated user
    """
    try:
        repos = await GitHubAuthService.get_user_repositories(access_token)
        
        return {
            "repos": repos,
            "count": len(repos)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/{owner}/{repo_name}/branches")
async def get_repo_branches(
    owner: str,
    repo_name: str,
    access_token: str = Query(...)
):
    """
    Get branches for a GitHub repository
    
    Args:
        owner: Repository owner username
        repo_name: Repository name
        access_token: GitHub OAuth access token
        
    Returns:
        List of branches
    """
    try:
        branches = await GitHubAuthService.get_repository_branches(
            access_token,
            owner,
            repo_name
        )
        
        return {
            "owner": owner,
            "repo": repo_name,
            "branches": branches,
            "count": len(branches)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/{owner}/{repo_name}/pulls")
async def get_repo_pulls(
    owner: str,
    repo_name: str,
    access_token: str = Query(...),
    state: str = Query("open")
):
    """
    Get pull requests for a GitHub repository
    
    Args:
        owner: Repository owner username
        repo_name: Repository name
        access_token: GitHub OAuth access token
        state: PR state ("open", "closed", "all")
        
    Returns:
        List of pull requests
    """
    try:
        pulls = await GitHubAuthService.get_repository_pulls(
            access_token,
            owner,
            repo_name,
            state
        )
        
        return {
            "owner": owner,
            "repo": repo_name,
            "state": state,
            "pulls": pulls,
            "count": len(pulls)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/{owner}/{repo_name}/issues")
async def get_repo_issues(
    owner: str,
    repo_name: str,
    access_token: str = Query(...),
    state: str = Query("open")
):
    """
    Get issues for a GitHub repository
    
    Args:
        owner: Repository owner username
        repo_name: Repository name
        access_token: GitHub OAuth access token
        state: Issue state ("open", "closed", "all")
        
    Returns:
        List of issues
    """
    try:
        issues = await GitHubAuthService.get_repository_issues(
            access_token,
            owner,
            repo_name,
            state
        )
        
        return {
            "owner": owner,
            "repo": repo_name,
            "state": state,
            "issues": issues,
            "count": len(issues)
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(access_token: str = Query(...)):
    """
    Logout/clear GitHub session
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        Confirmation message
    """
    try:
        GitHubAuthService.clear_token(access_token)
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
