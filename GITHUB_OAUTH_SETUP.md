# ShipMate AI - GitHub OAuth Setup Guide

## Overview

ShipMate AI integrates with GitHub via OAuth 2.0 to provide real-time analysis of your repositories. This guide walks you through setting up GitHub OAuth credentials for local development and deployment.

## Prerequisites

- GitHub account (free or paid)
- ShipMate AI repository cloned locally
- Node.js and Python installed

## Step 1: Create a GitHub OAuth Application

1. Go to https://github.com/settings/developers/oauth-apps
2. Click "New OAuth App" button
3. Fill in the application details:
   - **Application name**: `ShipMate AI` (or your custom name)
   - **Homepage URL**: `http://localhost:8000` (for development)
   - **Application description**: `Production readiness analysis tool for GitHub repositories`
   - **Authorization callback URL**: `http://localhost:8000/github-callback.html`

   **For Production/Deployment**:
   - Homepage URL: `https://yourdomain.com`
   - Authorization callback URL: `https://yourdomain.com/github-callback.html`

4. Click "Register application"

## Step 2: Copy OAuth Credentials

After creating the OAuth app, you'll see:
- **Client ID**: A long alphanumeric string
- **Client Secret**: A sensitive secret string (shown only once)

⚠️ **Important**: Keep your Client Secret private. Never commit it to version control.

## Step 3: Configure Environment Variables

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and update the GitHub OAuth fields:
   ```
   GITHUB_CLIENT_ID=your_client_id_here
   GITHUB_CLIENT_SECRET=your_client_secret_here
   GITHUB_REDIRECT_URI=http://localhost:8000/github-callback.html
   ```

4. Add other required environment variables if needed:
   ```
   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
   ```

## Step 4: Install Dependencies

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

## Step 5: Start the Application

### Terminal 1 - Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Output should show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

Output should show:
```
VITE v8.0.14  ready in XXX ms

➜  Local:   http://localhost:5174/
```

## Step 6: Test GitHub Integration

1. Open http://localhost:5174 in your browser
2. Click "Connect Your GitHub Account"
3. You'll be redirected to GitHub to authorize ShipMate AI
4. After authorization, you'll be redirected back and see your repositories
5. Select a repository and run the analysis

## GitHub OAuth Scopes

ShipMate AI requests the following GitHub API scopes:

- **repo** (full control of private repositories)
  - Read repository contents
  - Access pull requests and issues
  - View code and commit history

These are read-only operations. ShipMate AI does NOT write to your repositories.

## GitHub API Rate Limits

- **Unauthenticated requests**: 60 requests per hour per IP
- **Authenticated requests**: 5,000 requests per hour per user

ShipMate AI uses authenticated requests, so you get 5,000 requests per hour. For most use cases, this is more than sufficient.

## Troubleshooting

### "Invalid client_id" error
- Verify your Client ID is correct in `.env`
- Ensure you've restarted the backend after updating `.env`

### "Redirect URI mismatch" error
- The Authorization callback URL in GitHub settings must match `GITHUB_REDIRECT_URI` in `.env`
- For development: use `http://localhost:8000/github-callback.html`
- For production: use your domain's callback URL

### "Connection refused" on GitHub Authorization
- Ensure the backend is running (`python -m uvicorn app.main:app --reload`)
- Check that the Vite proxy is configured correctly in `frontend/vite.config.ts`

### "Repositories not loading" after successful auth
- Check browser console for errors (press F12)
- Check backend terminal for error logs
- Ensure your GitHub token has access to the repositories you're trying to analyze

## Environment Variables Reference

```bash
# GitHub OAuth Credentials (REQUIRED)
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>
GITHUB_REDIRECT_URI=http://localhost:8000/github-callback.html

# Optional - GitHub App Authentication (for advanced usage)
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000
```

## Production Deployment

For production deployment:

1. **Update Authorization Callback URL**:
   - In GitHub OAuth app settings: set to `https://yourdomain.com/github-callback.html`
   - In `.env`: set `GITHUB_REDIRECT_URI=https://yourdomain.com/github-callback.html`

2. **Secure Environment Variables**:
   - Use Azure Key Vault (recommended for Azure deployment)
   - Use GitHub Secrets for CI/CD deployments
   - Never commit `.env` file to version control

3. **Enable HTTPS**:
   - GitHub requires HTTPS for production OAuth
   - Use Azure Front Door or similar for SSL/TLS

4. **Session Storage** (production):
   - Replace in-memory session storage with:
     - Redis for distributed caching
     - Azure Cache for Redis
     - SQL database

## Architecture Overview

```
GitHub OAuth Flow:
1. Frontend: User clicks "Connect GitHub Account"
2. Frontend: Opens popup to GitHub authorization URL
3. GitHub: User approves permissions
4. GitHub: Redirects to http://localhost:8000/github-callback.html with authorization code
5. Backend: /github-callback.html receives code, exchanges it for access token
6. Backend: Fetches user profile and repositories via GitHub API
7. Frontend: Receives token via postMessage, stores in memory for session
8. Frontend: Uses token to fetch repository data via ShipMate AI API
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review GitHub OAuth documentation: https://docs.github.com/en/developers/apps/building-oauth-apps
3. Check backend logs for detailed error messages

## Security Notes

- **Client Secret**: Only transmitted server-to-server, never exposed to frontend
- **Access Token**: Stored in memory only (cleared on browser refresh)
- **No Token Storage**: Tokens are not persisted to disk or database
- **CSRF Protection**: State parameter used to validate OAuth callbacks

For production, implement:
- Secure token storage (e.g., encrypted sessions)
- Token refresh logic
- Rate limiting on API endpoints
- Request signing and validation
