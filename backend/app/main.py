from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
from io import BytesIO
from typing import Callable, Any
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.watcher import router as watcher_router
from app.api.routes.branches import router as branches_router

# ---------------------------------------------------------------------------
# Input Sanitization: Dangerous Pattern Detection
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS = [
    re.compile(r'\beval\s*\(', re.IGNORECASE),
    re.compile(r'\bexec\s*\(', re.IGNORECASE),
    re.compile(r'\b__import__\b', re.IGNORECASE),
    re.compile(r'\b__builtins__\b', re.IGNORECASE),
    re.compile(r'\b__globals__\b', re.IGNORECASE),
    re.compile(r'\b__locals__\b', re.IGNORECASE),
    re.compile(r'\bcompile\s*\(', re.IGNORECASE),
    re.compile(r'\bimportlib\.import_module\b', re.IGNORECASE),
    re.compile(r'\bsubprocess\b', re.IGNORECASE),
    re.compile(r'\bos\.system\b', re.IGNORECASE),
    re.compile(r'\bos\.popen\b', re.IGNORECASE),
]


def _contains_dangerous_pattern(text: str) -> bool:
    """Check if text contains any dangerous patterns."""
    if not isinstance(text, str):
        return False
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _scan_json_for_dangerous_patterns(obj: Any) -> bool:
    """Recursively scan a JSON object (dict, list, or primitive) for dangerous patterns.
    
    Returns True if any string value contains a dangerous pattern, False otherwise.
    """
    if isinstance(obj, str):
        return _contains_dangerous_pattern(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            if _scan_json_for_dangerous_patterns(value):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _scan_json_for_dangerous_patterns(item):
                return True
    return False


class _BodyReplayRequest(Request):
    """Request wrapper that replays cached body bytes on receive() calls."""
    
    def __init__(self, request: Request, body_bytes: bytes):
        super().__init__(request.scope, request.receive, request.send)
        self._cached_body = body_bytes
        self._body_sent = False
    
    async def receive(self):
        """Override receive to replay the cached body on first call."""
        if not self._body_sent:
            self._body_sent = True
            return {
                "type": "http.request",
                "body": self._cached_body,
                "more_body": False,
            }
        # After body is sent, return empty to signal end of stream
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }


# Content-type prefixes that carry text payloads and must be scanned.
_TEXT_CONTENT_TYPES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
    "text/",
)


def _is_text_content_type(content_type: str) -> bool:
    """Return True when the content-type indicates a text-based body."""
    ct_lower = content_type.lower()
    return any(ct_lower.startswith(prefix) or prefix in ct_lower for prefix in _TEXT_CONTENT_TYPES)


async def input_sanitization_middleware(request: Request, call_next: Callable):
    """Middleware to block requests with dangerous patterns in query, headers, and body."""
    # Check query parameters
    for key, value in request.query_params.items():
        if _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )
    
    # Check headers (skip Authorization and Cookie)
    skip_headers = {"authorization", "cookie"}
    for key, value in request.headers.items():
        if key.lower() not in skip_headers and _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )
    
    # Check body for all text-based content types
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "")
        if _is_text_content_type(content_type):
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8", errors="ignore")
                    # For JSON, parse and recursively scan all string values
                    if "application/json" in content_type:
                        try:
                            parsed_body = json.loads(body_str)
                            if _scan_json_for_dangerous_patterns(parsed_body):
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": "Request contains disallowed content"},
                                )
                        except json.JSONDecodeError:
                            # If JSON parsing fails, fall back to string scan
                            if _contains_dangerous_pattern(body_str):
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": "Request contains disallowed content"},
                                )
                    else:
                        # For form data, multipart, plain text, and other text types,
                        # scan the raw decoded string.
                        if _contains_dangerous_pattern(body_str):
                            return JSONResponse(
                                status_code=400,
                                content={"detail": "Request contains disallowed content"},
                            )
                # Wrap request with body replay capability so downstream handlers can read it
                request = _BodyReplayRequest(request, body)
            except Exception:
                pass
    
    return await call_next(request)


# ---------------------------------------------------------------------------
# CORS origin allowlist
# In production set ALLOWED_ORIGINS to a comma-separated list of origins, e.g.:
#   ALLOWED_ORIGINS=https://app.shipmate.ai
# The wildcard "*" is intentionally NOT supported here because
# allow_credentials=True is incompatible with "*" and would expose
# authenticated endpoints to any third-party site.
# ---------------------------------------------------------------------------

def _validate_origin(origin: str) -> str:
    """Validate a single CORS origin string.

    Rules:
    - Must not be '*' or contain any wildcard character ('*').
    - Must parse to a URL whose scheme is 'http' or 'https'.
    - Must have a non-empty netloc (host).

    Returns the origin unchanged if valid, raises ValueError otherwise.
    """
    if "*" in origin:
        raise ValueError(
            f"CORS origin '{origin}' contains a wildcard character, which is not "
            "allowed when allow_credentials=True. Set ALLOWED_ORIGINS to explicit "
            "origins only."
        )
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"CORS origin '{origin}' has an invalid scheme '{parsed.scheme}'. "
            "Only 'http' and 'https' schemes are permitted."
        )
    if not parsed.netloc:
        raise ValueError(
            f"CORS origin '{origin}' has an empty host/netloc. "
            "Each origin must be a fully-qualified URL such as 'https://example.com'."
        )
    return origin


_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS: list[str] = [
    _validate_origin(origin.strip())
    for origin in _raw_origins.split(",")
    if origin.strip()
]

# Build a frozenset for O(1) strict equality lookups.
_ALLOWED_ORIGINS_SET: frozenset[str] = frozenset(ALLOWED_ORIGINS)


def _is_origin_allowed(origin: str) -> bool:
    """Return True only when *origin* is an exact member of the allowlist.

    Strict equality prevents prefix/substring attacks such as
    'http://localhost:5173.evil.com' matching against 'http://localhost:5173'.
    """
    return origin in _ALLOWED_ORIGINS_SET


async def strict_cors_middleware(request: Request, call_next: Callable):
    """Enforce strict-equality CORS origin validation.

    For preflight (OPTIONS) and simple cross-origin requests the middleware
    checks the Origin header against the exact allowlist.  Only an exact match
    causes the Access-Control-Allow-Origin header to be echoed back; any other
    origin receives a 403 for preflight or a response without CORS headers for
    simple requests, which the browser will block.
    """
    origin = request.headers.get("origin")

    # No Origin header → same-origin or non-browser request; pass through.
    if origin is None:
        return await call_next(request)

    origin_allowed = _is_origin_allowed(origin)

    # Reject preflight immediately when origin is not in the allowlist.
    if request.method == "OPTIONS" and not origin_allowed:
        return JSONResponse(
            status_code=403,
            content={"detail": "CORS origin not allowed"},
        )

    response = await call_next(request)

    if origin_allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"

    return response


app = FastAPI(
    title="ShipMate AI",
    description="AI-native multi-agent release readiness platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# NOTE: CORSMiddleware is kept so that preflight Allow-Methods / Allow-Headers
# headers are generated correctly by the framework.  Its allow_origins list is
# set to the validated allowlist; our strict_cors_middleware (registered below)
# provides the additional exact-match guard that prevents prefix attacks.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(strict_cors_middleware)
app.middleware("http")(input_sanitization_middleware)

app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(actuate_router, prefix="/api")
app.include_router(watcher_router, prefix="/api")
app.include_router(branches_router, prefix="/api")


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
  <title>ShipMate AI \u2013 GitHub Auth</title>
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
    <h1>Completing GitHub authorization\u2026</h1>
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
