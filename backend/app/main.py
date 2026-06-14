import logging
import os
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import JSONResponse
from app.api.routes.auth import router as auth_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.branch import router as branch_router
from app.api.routes.coder import router as coder_router
from app.api.routes.guardrail import router as guardrail_router
from app.api.routes.plan import router as plan_router
from app.api.routes.repo import router as repo_router
from app.api.routes.orchestrate import router as orchestrate_router

logger = logging.getLogger("uvicorn.error")

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_ENDPOINT_ENV_VARS = [
    "API_ENDPOINT",
    "FRONTEND_ENDPOINT",
    "BACKEND_ENDPOINT",
    "SHIPMATE_ENDPOINT",
    "SHIPMATE_FRONTEND_ENDPOINT",
    "SHIPMATE_BACKEND_ENDPOINT",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "changeme"))
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(actuate_router, prefix="/api/actuate", tags=["actuate"])
app.include_router(analyze_router, prefix="/api/analyze", tags=["analyze"])
app.include_router(branch_router, prefix="/api/branch", tags=["branch"])
app.include_router(coder_router, prefix="/api/coder", tags=["coder"])
app.include_router(guardrail_router, prefix="/api/guardrail", tags=["guardrail"])
app.include_router(plan_router, prefix="/api/plan", tags=["plan"])
app.include_router(repo_router, prefix="/api/repo", tags=["repo"])
app.include_router(orchestrate_router, prefix="/api/orchestrate", tags=["orchestrate"])

def _is_origin_allowed(origin: str) -> bool:
    """Check if the origin is allowed based on environment variables and local hosts."""
    if not origin:
        return False
    for env_var in _ENDPOINT_ENV_VARS:
        endpoint = os.environ.get(env_var)
        if endpoint and origin.startswith(endpoint):
            return True
    host = origin.split(":")[0]
    return host in _LOCAL_HOSTS


def _validate_origin(origin: str) -> str:
    """Validate and return the origin if allowed, else return an empty string."""
    return origin if _is_origin_allowed(origin) else ""


def _validate_endpoint_urls() -> None:
    """Validate endpoint URLs from environment variables."""
    for env_var in _ENDPOINT_ENV_VARS:
        endpoint = os.environ.get(env_var)
        if endpoint and not endpoint.startswith("http"):
            logger.warning(f"Endpoint {env_var} does not start with http: {endpoint}")


def _get_client_ip(request: Request) -> str:
    """
    Securely extract the client IP address from the request.
    If TRUST_X_FORWARDED_FOR is enabled in config, use X-Forwarded-For header (with caution).
    Otherwise, use request.client.host.
    Logs a warning if multiple IPs are present in X-Forwarded-For.
    Note: Trusting X-Forwarded-For is risky unless behind a trusted proxy.
    """
    trust_xff = os.environ.get("TRUST_X_FORWARDED_FOR", "false").lower() == "true"
    if trust_xff:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if len(ips) > 1:
                logger.warning("Multiple IPs in X-Forwarded-For header: %s", ips)
            return ips[0]
    # Fallback: use request.client.host
    return request.client.host
