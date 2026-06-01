from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.models.schemas import (
    AnalyzeRequest, AnalyzeResponse, RepoSummary,
    GitHubRepository, GitHubBranch
)
from app.services.analyzer import run_full_analysis
from app.services.repo_service import process_repo_zip, get_sample_repo
from app.services.github_service import GitHubService
from app.services.auth_service import AuthService
from app.services.github_api_service import GitHubAPIService

app = FastAPI(
    title="ShipMate AI API",
    description="Agentic Engineering Command Center — Production Readiness Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for frontend dev server and Azure deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def root():
    return {
        "service": "ShipMate AI — Agentic Engineering Command Center",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "tagline": "Production Readiness Analysis powered by Azure AI Foundry + Azure OpenAI"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agents": [
            "planner",
            "repo_analyst",
            "test_generator",
            "security_guard",
            "delivery_manager"
        ],
        "message": "All systems operational"
    }


# ============================================================================
# GitHub Callback HTML - Serves the OAuth callback page
# ============================================================================

@app.get("/github-callback.html")
async def github_callback_html():
    """Serve GitHub OAuth callback HTML page"""
    from fastapi.responses import HTMLResponse
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShipMate AI - GitHub Authorization</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: #e2e8f0;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(96, 165, 250, 0.2);
            border-top: 4px solid #60a5fa;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 2rem;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        h1 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        p {
            color: #94a3b8;
        }
        .error {
            color: #fca5a5;
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h1>Authorizing with GitHub...</h1>
        <p>Please wait while we complete your authentication.</p>
        <div id="error"></div>
    </div>

    <script>
        // Get OAuth code and state from URL
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const error = params.get('error');
        const errorDesc = params.get('error_description');

        if (error) {
            document.getElementById('error').innerHTML = 
                `<div class="error"><strong>Authorization Failed:</strong> ${errorDesc || error}</div>`;
            setTimeout(() => {
                window.close();
            }, 3000);
        } else if (code) {
            // Exchange code for access token
            fetch('/api/github/callback?code=' + encodeURIComponent(code) + '&state=' + encodeURIComponent(state))
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Post message to parent window
                        window.opener.postMessage({
                            type: 'GITHUB_AUTH_SUCCESS',
                            access_token: data.access_token,
                            user: data.user
                        }, '*');
                        window.close();
                    } else {
                        throw new Error(data.detail || 'Authentication failed');
                    }
                })
                .catch(err => {
                    document.getElementById('error').innerHTML = 
                        `<div class="error"><strong>Authorization Failed:</strong> ${err.message}</div>`;
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                });
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


# ============================================================================
# Real GitHub OAuth Integration Endpoints
# ============================================================================

@app.get("/api/github/auth-url")
async def get_github_auth_url():
    """
    Get GitHub OAuth authorization URL
    
    Frontend redirects user to this URL to authenticate with GitHub.
    After authorization, GitHub redirects back to /github-callback.html.
    """
    try:
        # Construct callback URL - GitHub will redirect here after user authorizes
        redirect_uri = os.getenv(
            "GITHUB_REDIRECT_URI",
            "http://localhost:8000/github-callback.html"
        )
        
        auth_url = AuthService.get_auth_url(redirect_uri)
        
        return {
            "auth_url": auth_url,
            "message": "Redirect user to this URL to authenticate"
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/callback")
async def github_oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    GitHub OAuth callback endpoint
    
    GitHub redirects here after user authorizes.
    Exchanges authorization code for access token.
    Frontend can then use this token to fetch GitHub data.
    """
    try:
        # Exchange code for access token
        token_data = await AuthService.exchange_code_for_token(code, state)
        
        # Fetch user info
        access_token = token_data.get("access_token")
        user_info = await AuthService.get_user_info(access_token)
        
        # Return auth data to frontend
        # In production: store in secure session, return session ID instead
        return {
            "success": True,
            "access_token": access_token,
            "token_type": token_data.get("token_type", "bearer"),
            "user": user_info,
            "message": "GitHub authentication successful"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub callback failed: {str(e)}")


@app.get("/api/github/me")
async def get_current_user(access_token: str = Query(...)):
    """
    Get authenticated GitHub user profile
    
    Args:
        access_token: GitHub OAuth access token from /api/github/callback
    """
    try:
        user_info = await AuthService.get_user_info(access_token)
        return user_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/github/user-repos")
async def get_user_repositories(access_token: str = Query(...)):
    """
    Get authenticated user's repositories (real GitHub API)
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        List of user's repositories with metadata
    """
    try:
        repos = await GitHubAPIService.get_user_repositories(access_token)
        return repos
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/repos/{owner}/{repo_name}/branches")
async def get_repo_branches(
    owner: str,
    repo_name: str,
    access_token: str = Query(...)
):
    """
    Get branches for a GitHub repository (real GitHub API)
    """
    try:
        branches = await GitHubAPIService.get_repository_branches(
            access_token, owner, repo_name
        )
        return branches
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/repos/{owner}/{repo_name}/pulls")
async def get_repo_pulls(
    owner: str,
    repo_name: str,
    access_token: str = Query(...),
    state: str = Query("open")
):
    """
    Get pull requests for a GitHub repository (real GitHub API)
    """
    try:
        pulls = await GitHubAPIService.get_repository_pulls(
            access_token, owner, repo_name, state
        )
        return pulls
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/repos/{owner}/{repo_name}/issues")
async def get_repo_issues(
    owner: str,
    repo_name: str,
    access_token: str = Query(...),
    state: str = Query("open")
):
    """
    Get issues for a GitHub repository (real GitHub API)
    """
    try:
        issues = await GitHubAPIService.get_repository_issues(
            access_token, owner, repo_name, state
        )
        return issues
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/repos/{owner}/{repo_name}/contents")
async def get_repo_contents(
    owner: str,
    repo_name: str,
    access_token: str = Query(...),
    path: str = Query("")
):
    """
    Get file tree for a GitHub repository (real GitHub API)
    """
    try:
        contents = await GitHubAPIService.get_repository_contents(
            access_token, owner, repo_name, path
        )
        return contents
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Keep old endpoints for backward compatibility (mock data)
@app.get("/api/github/app-install-url")
async def get_github_app_install_url():
    """
    Get the GitHub App installation URL (deprecated).
    
    Use /api/github/auth-url instead for OAuth flow.
    """
    url = await GitHubService.get_github_app_install_url()
    return {
        "install_url": url,
        "message": "Click to authorize ShipMate with your GitHub account",
        "permissions": [
            "Contents: read-only",
            "Metadata: read-only",
            "Pull requests: read-only",
            "Issues: read-only",
            "Actions: read-only"
        ]
    }


@app.post("/api/github/callback-legacy")
async def github_oauth_callback_legacy(code: str = Query(...), state: str = Query(...)):
    """
    GitHub OAuth callback endpoint (legacy mock version)
    """
    try:
        result = await GitHubService.exchange_github_code(code, state)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub authentication failed: {str(e)}")


@app.get("/api/github/repos", response_model=list[GitHubRepository])
async def list_repositories(github_token: str = Query(None)):
    """
    Get list of repositories (mock data for demo fallback)
    """
    try:
        repos = await GitHubService.get_repositories(github_token)
        return repos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")


@app.get("/api/github/repos/{repo_id}/branches", response_model=list[GitHubBranch])
async def list_branches(repo_id: str, github_token: str = Query(None)):
    """
    Get list of branches (mock data for demo fallback)
    """
    try:
        branches = await GitHubService.get_branches(repo_id, github_token)
        return branches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch branches: {str(e)}")


@app.get("/api/github/repos/{repo_id}")
async def get_repository(repo_id: str, github_token: str = Query(None)):
    """
    Get detailed information about a specific repository (mock data)
    """
    try:
        repo = await GitHubService.get_repository_details(repo_id, github_token)
        return repo
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repository: {str(e)}")


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Run the full 5-agent production analysis swarm for a GitHub repository.
    
    Agents:
    1. Planner Agent — Converts feature into engineering tasks
    2. Repo Analyst Agent — Maps impact across the codebase
    3. Test Architect Agent — Creates comprehensive test strategy
    4. Security Guard Agent — Identifies security vulnerabilities
    5. Delivery Manager Agent — Produces release-ready sprint plan
    
    Returns: Production Readiness Score (0-100) + detailed analysis
    """
    if not request.feature_request or len(request.feature_request.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Feature request must be at least 10 characters long."
        )

    try:
        # Fetch repository details
        repo_details = await GitHubService.get_repository_details(request.repo_id, request.github_token)
        
        # Run the analysis
        result = run_full_analysis(request, repo_details)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/upload-repo", response_model=RepoSummary)
async def upload_repo(file: UploadFile = File(...)):
    """
    Upload a ZIP file containing a repository.
    
    [Legacy endpoint — deprecated in favor of GitHub integration]
    
    Extracts file tree, detects tech stack, and reads key files
    (README, package.json, requirements.txt, etc.)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported. Please compress your repository as a ZIP file."
        )

    # 50MB limit
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()

    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 50MB."
        )

    try:
        summary = await process_repo_zip(content)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e)}")


@app.get("/api/sample", response_model=RepoSummary)
async def get_sample():
    """
    Return a sample repository context for demo purposes.
    
    Returns a realistic e-commerce TypeScript project summary.
    """
    return get_sample_repo()


# ============================================================================
# Report Export Endpoint
# ============================================================================

@app.post("/api/reports/export")
async def export_report(analysis_id: str = Query(...)):
    """
    Generate an exportable delivery report.
    
    Later: Connect to Azure Blob Storage for report storage.
    For now: Return report metadata and download URL.
    """
    return {
        "status": "ready",
        "analysis_id": analysis_id,
        "format": "markdown",
        "download_url": f"/api/reports/{analysis_id}/download",
        "expires_in_hours": 24,
        "message": "Report ready for download"
    }


@app.get("/api/reports/{analysis_id}/download")
async def download_report(analysis_id: str):
    """
    Download an exported delivery report.
    
    Later: Stream from Azure Blob Storage.
    """
    return JSONResponse(
        content={
            "message": "Report download feature coming soon",
            "analysis_id": analysis_id
        }
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
