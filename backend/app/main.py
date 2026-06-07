from dotenv import load_dotenv
load_dotenv()

import os
import re
import time
import json
import hmac
import hashlib
import logging
from contextlib import asynccontextmanager
from typing import Callable
from urllib.parse import urlparse

logger = logging.getLogger("shipmate.main")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.watcher import router as watcher_router
from app.api.routes.branches import router as branches_router
from app.api.routes.findings import router as findings_router
from app.api.routes.auto_fix import router as auto_fix_router
from app.api.routes.history import router as history_router

# ---------------------------------------------------------------------------
# Rate Limiting: Token Bucket Implementation
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Simple token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def allow_request(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class _RateLimiter:
    """Per-IP rate limiter using token buckets."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, _TokenBucket] = {}

    def is_allowed(self, client_ip: str) -> bool:
        if client_ip not in self.buckets:
            self.buckets[client_ip] = _TokenBucket(self.capacity, self.refill_rate)
        return self.buckets[client_ip].allow_request()


# Auth callback: 10 requests per minute per IP (burst of 2)
_auth_limiter = _RateLimiter(capacity=2, refill_rate=10.0 / 60.0)
# Analysis endpoint: 30 requests per minute per IP (burst of 5)
_analysis_limiter = _RateLimiter(capacity=5, refill_rate=30.0 / 60.0)
# Webhook endpoint: 60 requests per minute per IP (burst of 10)
_webhook_limiter = _RateLimiter(capacity=10, refill_rate=60.0 / 60.0)


def _get_client_ip(request: Request) -> str:
    # X-Forwarded-For is trusted here; ensure a reverse proxy is in place in prod.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def rate_limit_auth_middleware(request: Request, call_next: Callable):
    if request.url.path == "/api/auth/github/callback":
        client_ip = _get_client_ip(request)
        if not _auth_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Too many authentication attempts."},
            )
    return await call_next(request)


async def rate_limit_analysis_middleware(request: Request, call_next: Callable):
    if request.url.path.startswith("/api/analysis"):
        client_ip = _get_client_ip(request)
        if not _analysis_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Too many analysis requests."},
            )
    return await call_next(request)


async def rate_limit_webhook_middleware(request: Request, call_next: Callable):
    if request.url.path == "/webhooks/github":
        client_ip = _get_client_ip(request)
        if not _webhook_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Too many webhook requests."},
            )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Startup: Enforce HTTPS for all configured service endpoint URLs
# ---------------------------------------------------------------------------

_ENDPOINT_ENV_VARS = [
    "BEDROCK_ENDPOINT",
    "API_BASE_URL",
    "INTERNAL_API_URL",
    "GITHUB_API_URL",
    "OPENAI_API_BASE",
    "ANTHROPIC_API_URL",
]

_LOCAL_HOSTS = frozenset([
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
])


def _validate_endpoint_urls() -> None:
    """Refuse to start if any configured endpoint URL uses plain HTTP with a non-local host."""
    for var in _ENDPOINT_ENV_VARS:
        value = os.getenv(var, "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme == "http":
            host = (parsed.hostname or "").lower()
            if host not in _LOCAL_HOSTS:
                raise ValueError(
                    f"Environment variable {var!r} is set to a plain HTTP URL "
                    f"({value!r}). Auth tokens must not be transmitted over "
                    "unencrypted connections. Change the URL scheme to 'https://' "
                    "before starting the application."
                )


_validate_endpoint_urls()

# ---------------------------------------------------------------------------
# Input Sanitization helpers
#
# _TEXT_CONTENT_TYPES and _is_text_content_type are used by
# sanitize_input_middleware below to decide which request bodies to scan.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# CORS origin allowlist
# In production set ALLOWED_ORIGINS to a comma-separated list of origins, e.g.:
#   ALLOWED_ORIGINS=https://app.shipmate.ai
# Wildcards are intentionally not supported (incompatible with allow_credentials=True).
# ---------------------------------------------------------------------------

def _validate_origin(origin: str) -> str:
    if "*" in origin:
        raise ValueError(
            f"CORS origin '{origin}' contains a wildcard character, which is not "
            "allowed when allow_credentials=True."
        )
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"CORS origin '{origin}' has an invalid scheme '{parsed.scheme}'."
        )
    if not parsed.netloc:
        raise ValueError(
            f"CORS origin '{origin}' has an empty host/netloc."
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


def _is_origin_allowed(origin: str) -> bool:
    """Exact-match check: is *origin* on the CORS allowlist? (SEC-004)

    Deliberately strict — no prefix, suffix, or subdomain matching. This is
    the guard that prevents spoofed origins a naive ``startswith``/substring
    check would wrongly accept:

    - ``http://localhost:5173.evil.com``  (prefix attack)  -> False
    - ``http://evil.localhost:5173``      (subdomain)       -> False
    - ``http://localhost:5173/``          (trailing slash)  -> False
    - ``""``                              (empty)           -> False
    - ``"*"``                             (wildcard)        -> False

    A wildcard is never allowed because ``allow_credentials=True`` is
    incompatible with ``*``. Returns True only for a byte-for-byte member of
    ALLOWED_ORIGINS.
    """
    if not origin or "*" in origin:
        return False
    return origin in ALLOWED_ORIGINS


# ---------------------------------------------------------------------------
# Input sanitization — block code-injection patterns before they reach routes
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"eval\s*\(",             re.IGNORECASE),
    re.compile(r"exec\s*\(",             re.IGNORECASE),
    re.compile(r"__import__\s*\(",       re.IGNORECASE),
    re.compile(r"__builtins__",          re.IGNORECASE),
    re.compile(r"__globals__",           re.IGNORECASE),
    re.compile(r"__locals__",            re.IGNORECASE),
    re.compile(r"compile\s*\(",          re.IGNORECASE),
    re.compile(r"importlib\.import_module", re.IGNORECASE),
    re.compile(r"subprocess\.",          re.IGNORECASE),
    re.compile(r"os\.system\s*\(",       re.IGNORECASE),
    re.compile(r"os\.popen\s*\(",        re.IGNORECASE),
]

_SKIP_HEADERS = {"authorization", "cookie"}


def _contains_dangerous_pattern(text: str) -> bool:
    return any(p.search(text) for p in _DANGEROUS_PATTERNS)


# ---------------------------------------------------------------------------
# Application lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: "FastAPI"):
    """Startup: initialize the inflight-registry sqlite (creates tables) and
    re-spawn CIWatcher supervisors for any PR still being watched when the
    backend last stopped (uvicorn --reload restarts on every code change).
    Shutdown: nothing to flush — sqlite commits are synchronous per write."""
    # --- startup ---
    try:
        from app.services import inflight_registry as _ir
        _ir.init_db()
    except Exception as e:  # pragma: no cover - startup best-effort
        logger.warning("inflight_registry init failed: %s", e)
    try:
        from app.services.ci_watcher import CIWatcher
        resumed = CIWatcher.resume_from_db()
        if resumed:
            logger.info("resumed %d CI watcher(s) after restart", resumed)
    except Exception as e:  # pragma: no cover
        logger.warning("CIWatcher resume failed: %s", e)

    yield
    # --- shutdown --- (no-op; sqlite is durable per-commit)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

_is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development"

app = FastAPI(
    title="ShipMate AI",
    description="AI-native multi-agent release readiness platform",
    version="2.0.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiters are registered first so they end up INNER to the sanitize
# middleware. Starlette/FastAPI inserts each @app.middleware at position 0
# of the middleware list and reverses when building the stack — so the LAST
# registered decorator becomes the OUTERMOST layer (runs first for requests).
# Desired request order: security_headers → strict_cors → sanitize → rate-limiters → CORS
@app.middleware("http")
async def _rate_limit_auth(request: Request, call_next: Callable):
    return await rate_limit_auth_middleware(request, call_next)


@app.middleware("http")
async def _rate_limit_analysis(request: Request, call_next: Callable):
    return await rate_limit_analysis_middleware(request, call_next)


@app.middleware("http")
async def _rate_limit_webhook(request: Request, call_next: Callable):
    return await rate_limit_webhook_middleware(request, call_next)


@app.middleware("http")
async def sanitize_input_middleware(request: Request, call_next):
    """Reject requests whose query params, headers, or body contain code-injection patterns."""

    for value in request.query_params.values():
        if _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )

    for key, value in request.headers.items():
        if key.lower() in _SKIP_HEADERS:
            continue
        if _contains_dangerous_pattern(value):
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains disallowed content"},
            )

    # 3. Request body — every text-based content type (JSON, form-urlencoded,
    #    multipart/form-data, text/plain). Multipart uploads carry attacker-
    #    controlled file bytes, so they must be scanned too.
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        if _is_text_content_type(content_type):
            try:
                from urllib.parse import unquote_plus
                body_bytes = await request.body()
                raw_text = body_bytes.decode("utf-8", errors="ignore")
                body_text = unquote_plus(raw_text) if "form-urlencoded" in content_type else raw_text
                if _contains_dangerous_pattern(body_text):
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Request contains disallowed content"},
                    )

                # Re-inject the consumed body so downstream handlers can read it.
                # We rebuild the ASGI receive channel rather than only setting
                # request._body: under an ASGI test transport, the downstream
                # route constructs its OWN Request from the scope and calls
                # receive() to read the body — if the stream is drained and we
                # only stashed _body on THIS Request instance, that receive()
                # blocks forever (observed as a selector.select hang on Linux
                # CI). A receive() that replays the cached bytes is what every
                # consumer (Starlette Request.body, Pydantic binding) honours.
                request._body = body_bytes

                async def _replay_receive() -> dict:
                    return {
                        "type": "http.request",
                        "body": body_bytes,
                        "more_body": False,
                    }
                request = Request(request.scope, receive=_replay_receive)
            except Exception:
                pass

    return await call_next(request)


@app.middleware("http")
async def strict_cors_middleware(request: Request, call_next):
    """Exact-match CORS guard layered on top of CORSMiddleware (SEC-004).

    CORSMiddleware already declines to echo an origin that isn't on the
    allowlist, but for a *preflight* (OPTIONS + Access-Control-Request-Method)
    from a spoofed origin it still returns 200 with no CORS headers. That is
    indistinguishable to a browser from a transient error and leaks no signal
    to defenders. We make the rejection explicit: a preflight from an origin
    that is not a byte-for-byte allowlist member gets a hard 403.

    Non-preflight requests pass straight through — CORSMiddleware owns the
    Access-Control-Allow-Origin reflection for those, and it only reflects
    allowlisted origins, so a spoofed origin is never echoed.
    """
    origin = request.headers.get("origin")
    is_preflight = (
        request.method == "OPTIONS"
        and request.headers.get("access-control-request-method") is not None
    )
    if origin and is_preflight and not _is_origin_allowed(origin):
        return JSONResponse(
            status_code=403,
            content={"detail": "Origin not allowed"},
        )
    return await call_next(request)


@app.middleware("http")
async def _security_headers(request: Request, call_next: Callable):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "X-XSS-Protection": "0",
    })
    return response


app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(actuate_router, prefix="/api")
app.include_router(watcher_router, prefix="/api")
app.include_router(branches_router, prefix="/api")
app.include_router(findings_router, prefix="/api")
app.include_router(auto_fix_router, prefix="/api")
app.include_router(history_router, prefix="/api")


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


def _verify_github_webhook_signature(body: bytes, signature_header: str) -> bool:
    """Verify a GitHub webhook's X-Hub-Signature-256 header (HMAC-SHA256).

    Returns False when:
      - GITHUB_WEBHOOK_SECRET is unset (fail closed),
      - the header is missing or malformed,
      - the digests don't match.
    """
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — rejecting webhook")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


async def _run_webhook_analysis(
    owner: str,
    repo: str,
    branch: str,
    pr_number: int | None,
    installation_token: str,
) -> None:
    """Background task: run the full analysis pipeline and post a PR comment."""
    try:
        from app.services.repo_analysis_service import RepoAnalysisService
        from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator
        from app.services.github_comment_service import post_pr_comment
        from app.services.score_history_service import record_score

        repo_context = await RepoAnalysisService.build_context(
            token=installation_token,
            owner=owner,
            repo=repo,
            branch=branch,
            pr_number=pr_number,
            feature_context="",
        )
        orchestrator = ShipMateOrchestrator()
        report = await orchestrator.run(repo_context)

        record_score(
            owner=owner, repo=repo, branch=branch,
            score=report.readiness_score,
            breakdown={
                "repo": report.score_breakdown.repo_score,
                "delivery": report.score_breakdown.delivery_score,
                "security": report.score_breakdown.security_score,
                "test": report.score_breakdown.test_score,
            },
        )

        if pr_number:
            await post_pr_comment(
                token=installation_token,
                owner=owner, repo=repo,
                pr_number=pr_number,
                report=report,
            )
        logger.info("Webhook analysis complete for %s/%s#%s score=%d",
                    owner, repo, pr_number or branch, report.readiness_score)
    except Exception as e:
        logger.warning("Webhook analysis failed for %s/%s: %s", owner, repo, e)


@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events for push and pull_request.

    Validates webhook signature, extracts repository and branch info,
    and triggers automatic analysis in the background.
    """
    body_bytes = await request.body()

    signature = request.headers.get("x-hub-signature-256", "")
    if not _verify_github_webhook_signature(body_bytes, signature):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid webhook signature"},
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid JSON payload"},
        )

    event_type = request.headers.get("x-github-event", "")

    # The installation token for automated analysis — must be set as env var
    # when running as a GitHub App. Falls back to empty (analysis skipped).
    installation_token = os.getenv("GITHUB_INSTALLATION_TOKEN", "")

    if event_type == "push":
        repo_full = payload.get("repository", {}).get("full_name", "")
        branch = payload.get("ref", "").split("/")[-1]
        owner, _, repo = repo_full.partition("/")

        if not repo_full or not branch:
            return JSONResponse(status_code=400, content={"detail": "Missing repo or branch"})

        if installation_token:
            import asyncio
            asyncio.create_task(_run_webhook_analysis(owner, repo, branch, None, installation_token))

        return JSONResponse(status_code=202, content={
            "status": "accepted",
            "message": f"Analysis queued for {repo_full}:{branch}",
            "event": "push",
        })

    elif event_type == "pull_request":
        repo_full = payload.get("repository", {}).get("full_name", "")
        pr_number = payload.get("pull_request", {}).get("number")
        branch = payload.get("pull_request", {}).get("head", {}).get("ref", "main")
        action = payload.get("action")
        owner, _, repo = repo_full.partition("/")

        if not repo_full or not pr_number:
            return JSONResponse(status_code=400, content={"detail": "Missing repo or PR info"})

        if action not in ["opened", "synchronize", "reopened"]:
            return JSONResponse(status_code=202, content={
                "status": "ignored",
                "message": f"PR action '{action}' does not trigger analysis",
                "event": "pull_request",
            })

        if installation_token:
            import asyncio
            asyncio.create_task(_run_webhook_analysis(owner, repo, branch, pr_number, installation_token))

        return JSONResponse(status_code=202, content={
            "status": "accepted",
            "message": f"Analysis queued for {repo_full} PR #{pr_number}",
            "event": "pull_request",
        })

    else:
        return JSONResponse(status_code=202, content={
            "status": "ignored",
            "message": f"Event type '{event_type}' is not processed",
        })


# HTML template for the backend-served OAuth callback page.
# __PMORIGIN__ is replaced at request time with the configured FRONTEND_URL.
_GITHUB_CALLBACK_HTML_TEMPLATE = """<!DOCTYPE html>
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
              {type:'GITHUB_AUTH_SUCCESS', access_token: d.access_token, user: d.user},
              '__PMORIGIN__');
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
</html>"""


@app.get("/github-callback.html", response_class=HTMLResponse)
async def github_callback_html():
    _origin = os.getenv("FRONTEND_URL", ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:5173")
    return HTMLResponse(content=_GITHUB_CALLBACK_HTML_TEMPLATE.replace("__PMORIGIN__", _origin))


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
