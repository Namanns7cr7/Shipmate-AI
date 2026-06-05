from dotenv import load_dotenv
load_dotenv()

import os
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router

# ---------------------------------------------------------------------------
# CORS origin allowlist
# In production set ALLOWED_ORIGINS to a comma-separated list of origins, e.g.:
#   ALLOWED_ORIGINS=https://app.shipmate.ai
# The wildcard "*" is intentionally NOT supported here because
# allow_credentials=True is incompatible with "*" and would expose
# authenticated endpoints to any third-party site.
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS: list[str] = [
    origin.strip() for origin in _raw_origins.split(",") if origin.strip()
]

# ---------------------------------------------------------------------------
# Input sanitization — block code injection patterns in query params / headers
# / request body before they reach any route handler.
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"eval\s*\(",            re.IGNORECASE),
    re.compile(r"exec\s*\(",            re.IGNORECASE),
    re.compile(r"__import__\s*\(",      re.IGNORECASE),
    re.compile(r"__builtins__",         re.IGNORECASE),
    re.compile(r"__globals__",          re.IGNORECASE),
    re.compile(r"__locals__",           re.IGNORECASE),
    re.compile(r"compile\s*\(",         re.IGNORECASE),
    re.compile(r"importlib\.import_module", re.IGNORECASE),
    re.compile(r"subprocess\.",         re.IGNORECASE),
    re.compile(r"os\.system\s*\(",      re.IGNORECASE),
    re.compile(r"os\.popen\s*\(",       re.IGNORECASE),
]

_SKIP_HEADERS = {"authorization", "cookie"}


def _contains_dangerous_pattern(text: str) -> bool:
    """Return True if *text* matches any known code-injection pattern."""
    return any(p.search(text) for p in _DANGEROUS_PATTERNS)


app = FastAPI(
    title="ShipMate AI",
    description="AI-native multi-agent release readiness platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def sanitize_input_middleware(request: Request, call_next):
    """Reject requests whose query params, headers, or body contain
    code-injection patterns (eval, exec, subprocess, etc.)."""

    # 1. Query parameters
    for value in request.query_params.values():
        if _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )

    # 2. Headers (skip Authorization and Cookie — they are trust-boundary values)
    for key, value in request.headers.items():
        if key.lower() in _SKIP_HEADERS:
            continue
        if _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )

    # 3. Request body (JSON and form-encoded only)
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type or "application/x-www-form-urlencoded" in content_type:
            try:
                from urllib.parse import unquote_plus
                body_bytes = await request.body()
                raw_text = body_bytes.decode("utf-8", errors="ignore")
                # URL-decode form bodies so percent-encoded patterns (exec%28…) are caught
                body_text = unquote_plus(raw_text) if "form-urlencoded" in content_type else raw_text
                if _contains_dangerous_pattern(body_text):
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Request contains disallowed content"},
                    )
                # Re-inject body bytes so downstream handlers can read them
                async def _receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                request = Request(request.scope, receive=_receive)
            except Exception:
                pass  # Don't crash on body-read errors; let the route handle it

    return await call_next(request)


app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "ShipMate AI",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "agents": ["RepoLens", "PlanForge", "GuardRail", "TestPilot"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agents": 4}


@app.get("/github-callback.html", response_class=HTMLResponse)
async def github_callback_html():
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ShipMate AI – GitHub Auth</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:system-ui,sans-serif;background:#0f172a;display:flex;align-items:center;
         justify-content:center;min-height:100vh;color:#e2e8f0}
    .box{text-align:center;padding:2rem}
    .spinner{width:48px;height:48px;border:4px solid rgba(99,179,237,.2);
             border-top-color:#60a5fa;border-radius:50%;animation:spin 1s linear infinite;
             margin:0 auto 1.5rem}
    @keyframes spin{to{transform:rotate(360deg)}}
    h1{font-size:1.25rem;margin-bottom:.5rem}
    p{color:#94a3b8;font-size:.875rem}
    .error{color:#fca5a5;margin-top:1rem;padding:.75rem 1rem;
           background:rgba(239,68,68,.1);border-radius:.5rem;font-size:.875rem}
  </style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h1>Completing GitHub authorization…</h1>
    <p>This window will close automatically.</p>
    <div id="err"></div>
  </div>
  <script>
    const p = new URLSearchParams(location.search);
    const code  = p.get('code');
    const state = p.get('state');
    const err   = p.get('error');
    if (err) {
      document.getElementById('err').innerHTML =
        '<div class="error">Authorization failed: ' + (p.get('error_description') || err) + '</div>';
      setTimeout(() => window.close(), 3000);
    } else if (code) {
      fetch('/api/auth/github/callback?code=' + encodeURIComponent(code) + '&state=' + encodeURIComponent(state || ''))
        .then(r => r.json())
        .then(d => {
          if (d.success) {
            window.opener && window.opener.postMessage(
              {type:'GITHUB_AUTH_SUCCESS', access_token: d.access_token, user: d.user}, '*');
            window.close();
          } else { throw new Error(d.detail || 'Auth failed'); }
        })
        .catch(e => {
          document.getElementById('err').innerHTML =
            '<div class="error">' + e.message + '</div>';
          setTimeout(() => window.close(), 3000);
        });
    }
  </script>
</body>
</html>""")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
