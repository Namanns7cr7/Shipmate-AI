# ShipMate AI - Real GitHub Authentication Setup Guide

## Overview

ShipMate AI now uses real GitHub OAuth 2.0 authentication, allowing any user to connect their GitHub account and analyze their actual repositories.

**Status**: ✅ Full implementation complete
- Real GitHub OAuth flow
- User repositories from GitHub API
- Secure token handling
- No mock data

---

## Prerequisites

- GitHub account
- Node.js 18+ installed
- Python 3.9+ installed
- A terminal or command prompt

---

## Step 1: Create GitHub OAuth Application

### For Development (localhost):

1. Go to **[GitHub Developer Settings](https://github.com/settings/developers/oauth-apps)**
2. Click **"New OAuth App"** button
3. Fill in the form:
   - **Application name**: `ShipMate AI` (or your preferred name)
   - **Homepage URL**: `http://localhost:8000`
   - **Application description**: `Production readiness analysis tool for GitHub repositories`
   - **Authorization callback URL**: `http://localhost:5173/github/callback`
4. Click **"Register application"**
5. You'll be redirected to your app's settings page

### For Production Deployment:

Replace `localhost` URLs with your actual domain:
- **Homepage URL**: `https://yourdomain.com`
- **Authorization callback URL**: `https://yourdomain.com/github/callback`

---

## Step 2: Get Your OAuth Credentials

On your GitHub OAuth app page, you'll see:
- **Client ID**: A string that looks like `abc123xyz...`
- **Client Secret**: A string that looks like `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

⚠️ **IMPORTANT**: Keep your Client Secret private! Never commit it to version control.

---

## Step 3: Configure Environment Variables

### Backend Configuration

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create/update `.env` file with your credentials:
```bash
GITHUB_CLIENT_ID=your_actual_client_id_here
GITHUB_CLIENT_SECRET=your_actual_client_secret_here
GITHUB_REDIRECT_URI=http://localhost:5173/github/callback
```

3. **Do NOT commit `.env` file!** It's already in `.gitignore`

### Verify Your Setup

Check that `.env` is in `.gitignore`:
```bash
cat .gitignore | grep -i "\.env"
```

---

## Step 4: Install Dependencies

### Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- `fastapi` - Web framework
- `httpx` - Async HTTP client (for GitHub API)
- `python-dotenv` - Load environment variables

### Frontend Dependencies

```bash
cd frontend
npm install
```

---

## Step 5: Start the Application

### Terminal 1 - Start Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 [Ctrl+C to quit]
INFO:     Started server process [12345]
```

### Terminal 2 - Start Frontend

```bash
cd frontend
npm run dev
```

Expected output:
```
  VITE v8.0.14  ready in 245 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

---

## Step 6: Test GitHub Authentication

1. Open **http://localhost:5173** in your browser
2. You should see the ShipMate AI dashboard with a **"Connect Your GitHub Account"** button
3. Click the button
4. You'll be redirected to GitHub to authorize the application
5. After clicking "Authorize", you'll be redirected back to the app
6. You should see your real GitHub repositories in a list

### Expected Flow:

```
App (localhost:5173)
  ↓ User clicks "Connect GitHub"
App calls /auth/github/login
  ↓ Backend returns GitHub auth URL
  ↓ Frontend opens popup
GitHub Login Page
  ↓ User authorizes
  ↓ GitHub redirects to callback URL
Frontend receives callback (localhost:5173/github/callback)
  ↓ Frontend exchanges code for token
Backend processes /auth/github/callback?code=...&state=...
  ↓ Backend exchanges code for access token
  ↓ Backend fetches user profile
Frontend saves token & user to localStorage
  ↓ Page redirects to dashboard
Dashboard shows real repositories from GitHub API
```

---

## Backend Endpoints

All endpoints use the `/auth/github` prefix.

### GET /auth/github/login

Returns the GitHub OAuth authorization URL.

**Response**:
```json
{
  "auth_url": "https://github.com/login/oauth/authorize?...",
  "message": "Redirect user to this URL to authenticate with GitHub"
}
```

### GET /auth/github/callback?code=...&state=...

Handles OAuth callback from GitHub.

**Query Parameters**:
- `code`: Authorization code from GitHub
- `state`: State parameter for CSRF validation

**Response**:
```json
{
  "success": true,
  "access_token": "gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "token_type": "bearer",
  "scope": "repo read:user user:email",
  "user": {
    "id": 12345,
    "login": "yourusername",
    "name": "Your Name",
    "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
    "html_url": "https://github.com/yourusername",
    "email": "user@example.com",
    "public_repos": 42,
    "followers": 100,
    "following": 50
  }
}
```

### GET /auth/github/me?access_token=...

Get authenticated user profile.

**Query Parameters**:
- `access_token`: GitHub OAuth access token

**Response**:
```json
{
  "authenticated": true,
  "user": { ...user object... }
}
```

### GET /auth/github/repos?access_token=...

Get authenticated user's repositories.

**Query Parameters**:
- `access_token`: GitHub OAuth access token

**Response**:
```json
{
  "repos": [
    {
      "id": 123,
      "name": "shipmate-ai",
      "full_name": "username/shipmate-ai",
      "description": "Production readiness analysis tool",
      "html_url": "https://github.com/username/shipmate-ai",
      "private": false,
      "default_branch": "main",
      "language": "TypeScript",
      "stargazers_count": 42,
      "watchers_count": 10,
      "forks_count": 5,
      "updated_at": "2026-06-01T10:00:00Z"
    }
  ],
  "count": 1
}
```

### GET /auth/github/repos/{owner}/{repo}/branches?access_token=...

Get branches for a repository.

### GET /auth/github/repos/{owner}/{repo}/pulls?access_token=...

Get pull requests for a repository.

### GET /auth/github/repos/{owner}/{repo}/issues?access_token=...

Get issues for a repository.

### POST /auth/github/logout?access_token=...

Logout and clear session.

---

## Frontend Architecture

### Authentication Hook: `useGithubAuth`

Custom React hook that manages GitHub authentication state.

```typescript
const githubAuth = useGithubAuth();

// Properties:
githubAuth.isAuthenticated  // boolean
githubAuth.user             // GitHubUser | null
githubAuth.accessToken      // string | null
githubAuth.loading          // boolean
githubAuth.error            // string | null

// Methods:
githubAuth.initiateLogin()  // Open GitHub OAuth
githubAuth.logout()         // Clear auth
githubAuth.refreshAuth()    // Reload from localStorage
```

### Authentication Flow:

1. **Page Load**: Check `localStorage` for saved token
2. **User Clicks "Connect"**: `initiateLogin()` opens GitHub OAuth
3. **GitHub Redirects**: Browser navigates to `/github/callback?code=...&state=...`
4. **Callback Page**: Exchanges code for token, saves to `localStorage`
5. **Redirect to Home**: Page reloads, hook detects token in `localStorage`
6. **Authenticated**: App displays user's repositories

### Components:

- **GitHubConnectButton**: Login button with error handling
- **GitHubUserProfile**: User info and logout button
- **GitHubCallback**: Handles OAuth callback

---

## Security Features

✅ **Implemented**:
- Client Secret only used server-side (never exposed to frontend)
- OAuth code exchange happens only in backend
- CSRF protection via `state` parameter
- Access tokens stored in memory only (cleared on page refresh)
- `.env` file with secrets not committed to git
- CORS configured for localhost development

⚠️ **For Production**:
- Use HTTPS only
- Store tokens in secure, httpOnly cookies (instead of localStorage)
- Implement token refresh mechanism
- Use Azure Key Vault for secrets
- Set appropriate CORS origins
- Enable rate limiting on auth endpoints

---

## Environment Variables Reference

```bash
# GitHub OAuth (REQUIRED)
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>
GITHUB_REDIRECT_URI=http://localhost:5173/github/callback

# Azure OpenAI (Optional, for AI agents)
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173
```

---

## Troubleshooting

### "Invalid client_id" Error

**Problem**: GitHub says your Client ID is invalid

**Solution**:
1. Verify your GitHub OAuth app exists: https://github.com/settings/developers/oauth-apps
2. Copy the exact Client ID (no spaces)
3. Paste into `.env`
4. Restart backend: `python -m uvicorn app.main:app --reload --port 8000`

### "Redirect URI Mismatch" Error

**Problem**: Authorization callback URL doesn't match

**Solution**:
1. Go to your GitHub OAuth app settings
2. Check "Authorization callback URL"
3. Make sure it matches `GITHUB_REDIRECT_URI` in `.env`
4. For localhost development: `http://localhost:5173/github/callback`
5. For production: `https://yourdomain.com/github/callback`

### "Repositories Not Loading" After Auth

**Problem**: User sees "Connected as @username" but no repos

**Solution**:
1. Check browser console (F12) for errors
2. Check backend terminal for error logs
3. Verify token has `repo` scope (it should from the OAuth app)
4. Try logging out and back in

### "Connection Refused" on GitHub Authorization

**Problem**: Popup closes or shows network error

**Solution**:
1. Ensure backend is running: `http://localhost:8000` should be accessible
2. Check backend terminal for errors
3. Verify Vite proxy is configured in `frontend/vite.config.ts`:
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true,
     },
   }
   ```

### "Token Invalid or Expired"

**Problem**: After successful login, error appears

**Solution**:
1. GitHub tokens are valid for 8 hours
2. Clear localStorage: Open DevTools → Application → localStorage → Delete all
3. Try logging in again
4. Check that backend is returning valid tokens from `/auth/github/callback`

---

## Files Changed Summary

### Backend

**New Files**:
- `backend/app/services/github_auth_service.py` - OAuth service
- `backend/app/routes/auth_routes.py` - Auth endpoints

**Modified Files**:
- `backend/app/main.py` - Added auth router
- `backend/.env` - Updated with OAuth credentials
- `backend/.env.example` - Documentation

### Frontend

**New Files**:
- `frontend/src/hooks/useGithubAuth.ts` - Auth hook
- `frontend/src/pages/GitHubCallback.tsx` - Callback handler
- `frontend/src/components/GitHubConnectButton.tsx` - Connect button
- `frontend/src/components/GitHubUserProfile.tsx` - User profile display

**Modified Files**:
- `frontend/src/App.tsx` - Integrated real auth
- `frontend/src/lib/api.ts` - Updated API calls
- `frontend/src/main.tsx` - Added callback routing
- `frontend/vite.config.ts` - Updated port and proxy

---

## Next Steps

1. ✅ Test OAuth login/logout
2. ✅ Verify real repositories load
3. ✅ Select a repo and analyze
4. 📋 Deploy to production (Azure App Service)
5. 📋 Set up GitHub Actions CI/CD
6. 📋 Configure custom domain

---

## Production Deployment (Azure)

When deploying to Azure:

1. **Update OAuth URLs**:
   - Callback URL: `https://yourdomain.com/github/callback`
   - Homepage: `https://yourdomain.com`

2. **Use Azure Key Vault**:
   ```python
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient
   ```

3. **Enable HTTPS**: Required by GitHub for production OAuth

4. **Secure Token Storage**: Use httpOnly cookies instead of localStorage

5. **Environment Variables**: Set in Azure App Service Configuration

---

## Support & Issues

For issues:
1. Check troubleshooting section above
2. Review backend logs: Look for error messages in terminal
3. Check browser console: Press F12, go to Console tab
4. Verify environment variables are set correctly
5. Ensure GitHub OAuth app is configured with correct URLs

---

## Architecture Diagram

```
User Browser                 Frontend App              Backend Server         GitHub
    |                            |                          |                    |
    +---Click "Connect"--------->|                          |                    |
    |                            |                          |                    |
    |<-------Auth URL popup------|--/auth/github/login----->|                    |
    |                            |                          |                    |
    +----Popup (auth.github.com)------Open Link-------------------Authorize App--->|
    |                            |                          |                    |
    |<---Redirect callback------|<-----Callback code--------|<---Redirect--------|
    |  (localhost:5173/           |                          |
    |   github/callback?code=...) |                          |
    |                            |                          |
    |---Exchange code for token->|--/auth/github/callback?-->|
    |                            |   code=...&state=...      |
    |                            |                          |--GitHub API Call-->|
    |                            |                          |<---User Profile----|
    |                            |<---Token + User----------|
    |<---Save localStorage------|                          |
    |   (token + user info)      |                          |
    |                            |                          |
    |---Load repositories------->|--/auth/github/repos---->|
    |                            |   ?access_token=...      |
    |                            |                          |--GitHub API Call-->|
    |                            |                          |<---Repository List--|
    |<---Display repos-----------|<---Repo List-----------|
    |                            |                          |
```

---

## GitHub OAuth Scopes

Current scopes requested: `repo read:user user:email`

- **repo**: Full control of private repositories (read-only operations)
- **read:user**: Read user profile info
- **user:email**: Access email address

No write permissions are requested. ShipMate AI is read-only.

---

Congratulations! Your ShipMate AI instance now has real GitHub OAuth authentication. 🎉
