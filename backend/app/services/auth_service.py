"""
GitHub Authentication Service

Handles GitHub OAuth 2.0 flow for real GitHub integration.
- Generates authorization URLs
- Exchanges auth codes for access tokens  
- Validates and manages authentication state
"""

import os
import httpx
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# GitHub OAuth URLs
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class AuthService:
    """GitHub OAuth authentication service"""
    
    # In-memory session storage (in production, use Redis or database)
    _sessions: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def get_auth_url(redirect_uri: str) -> str:
        """
        Generate GitHub OAuth authorization URL
        
        Args:
            redirect_uri: Callback URL where user is redirected after auth
            
        Returns:
            Authorization URL for user to click
        """
        client_id = os.getenv("GITHUB_CLIENT_ID", "")
        if not client_id:
            raise ValueError("GITHUB_CLIENT_ID not configured")
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state temporarily
        AuthService._sessions[state] = {
            "created_at": datetime.now(),
            "redirect_uri": redirect_uri
        }
        
        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "repo read:user user:email read:repo_hook",
            "state": state,
            "allow_signup": "true"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{GITHUB_AUTHORIZE_URL}?{query_string}"
    
    @staticmethod
    async def exchange_code_for_token(code: str, state: str) -> Dict[str, Any]:
        """
        Exchange GitHub authorization code for access token
        
        Args:
            code: Authorization code from GitHub
            state: State parameter for CSRF validation
            
        Returns:
            Dictionary with access_token, token_type, etc.
        """
        # Validate state
        if state not in AuthService._sessions:
            raise ValueError("Invalid or expired state parameter")
        
        # Clean up old state (older than 10 minutes)
        session_data = AuthService._sessions[state]
        created_at = session_data["created_at"]
        if datetime.now() - created_at > timedelta(minutes=10):
            del AuthService._sessions[state]
            raise ValueError("State parameter expired")
        
        # Exchange code for token
        client_id = os.getenv("GITHUB_CLIENT_ID", "")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
        redirect_uri = session_data.get("redirect_uri", "")
        
        if not client_id or not client_secret:
            raise ValueError("GitHub OAuth credentials not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GITHUB_TOKEN_URL,
                    json={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                token_data = response.json()
        except Exception as e:
            raise ValueError(f"Failed to exchange code for token: {str(e)}")
        
        # Clean up session
        del AuthService._sessions[state]
        
        return token_data
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """
        Fetch authenticated GitHub user information
        
        Args:
            access_token: GitHub OAuth access token
            
        Returns:
            User profile data: login, name, avatar_url, bio, etc.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GITHUB_API_URL}/user",
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                response.raise_for_status()
                user_data = response.json()
                
                # Extract essential user info
                return {
                    "id": user_data.get("id"),
                    "login": user_data.get("login"),
                    "name": user_data.get("name"),
                    "avatar_url": user_data.get("avatar_url"),
                    "bio": user_data.get("bio"),
                    "company": user_data.get("company"),
                    "blog": user_data.get("blog"),
                    "location": user_data.get("location"),
                    "public_repos": user_data.get("public_repos"),
                    "followers": user_data.get("followers"),
                    "following": user_data.get("following"),
                }
        except Exception as e:
            raise ValueError(f"Failed to fetch user info: {str(e)}")
