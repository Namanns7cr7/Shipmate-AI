import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from dotenv import load_dotenv

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.repo import router as repo_router
from app.api.routes.branch import router as branch_router
from app.api.routes.coder import router as coder_router
from app.api.routes.llm import router as llm_router
from app.api.routes.plan import router as plan_router
from app.api.routes.orchestrate import router as orchestrate_router
from app.api.routes.guardrail import router as guardrail_router
from app.api.routes.repo_lens import router as repo_lens_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "default_secret"))

# Security: List of local hosts for trusted IP logic
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

# Security: Should we trust X-Forwarded-For header for client IP?
TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true"


def _get_client_ip(request: Request) -> str:
    """
    Returns the client IP address for a request.
    If TRUST_X_FORWARDED_FOR is enabled, will use X-Forwarded-For header (with warning if multiple IPs).
    Otherwise, falls back to request.client.host.
    WARNING: Trusting X-Forwarded-For is dangerous unless your proxy strips untrusted values.
    """
    if TRUST_X_FORWARDED_FOR:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if len(ips) > 1:
                logging.warning("Multiple IPs in X-Forwarded-For header: %s. Using first.", ips)
            return ips[0]
    return request.client.host


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(analysis_router, prefix="/api/analyze", tags=["analysis"])
app.include_router(actuate_router, prefix="/api/actuate", tags=["actuate"])
app.include_router(repo_router, prefix="/api/repo", tags=["repo"])
app.include_router(branch_router, prefix="/api/branch", tags=["branch"])
app.include_router(coder_router, prefix="/api/coder", tags=["coder"])
app.include_router(llm_router, prefix="/api/llm", tags=["llm"])
app.include_router(plan_router, prefix="/api/plan", tags=["plan"])
app.include_router(orchestrate_router, prefix="/api/orchestrate", tags=["orchestrate"])
app.include_router(guardrail_router, prefix="/api/guardrail", tags=["guardrail"])
app.include_router(repo_lens_router, prefix="/api/repo-lens", tags=["repo-lens"])

# --- TEST HOOKS ---
# For test_main.py route registration tests
ROUTE_PATHS = [route.path for route in app.routes if hasattr(route, 'path')]

