import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.routes.auth import router as auth_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.repo_lens import router as repo_lens_router
from app.api.routes.plan_forge import router as plan_forge_router
from app.api.routes.guardrail import router as guardrail_router
from app.api.routes.coder import router as coder_router
from app.api.routes.branch_pruner import router as branch_pruner_router
from app.api.routes.ci_watcher import router as ci_watcher_router
from app.api.routes.llm import router as llm_router
from app.api.routes.repo import router as repo_router

# Environment variable to control trust of X-Forwarded-For header
TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true"

app = FastAPI()

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://shipmate-ai.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_ENDPOINT_ENV_VARS = ["FRONTEND_URL", "BACKEND_URL", "API_URL"]


def _is_origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    for allowed in ALLOWED_ORIGINS:
        if origin.startswith(allowed):
            return True
    return False


def _validate_origin(origin: str) -> str:
    return origin if _is_origin_allowed(origin) else ""


def _validate_endpoint_urls() -> None:
    for var in _ENDPOINT_ENV_VARS:
        url = os.getenv(var)
        if url and url.startswith("http://") and not any(host in url for host in _LOCAL_HOSTS):
            raise RuntimeError(f"{var} must use HTTPS in production: {url}")


def _get_client_ip(request: Request) -> str:
    if TRUST_X_FORWARDED_FOR:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the first IP in the list
            return x_forwarded_for.split(",")[0].strip()
    return request.client.host


app.include_router(auth_router, prefix="/api/auth")
app.include_router(actuate_router, prefix="/api/actuate")
app.include_router(repo_lens_router, prefix="/api/repo-lens")
app.include_router(plan_forge_router, prefix="/api/plan-forge")
app.include_router(guardrail_router, prefix="/api/guardrail")
app.include_router(coder_router, prefix="/api/coder")
app.include_router(branch_pruner_router, prefix="/api/branch-pruner")
app.include_router(ci_watcher_router, prefix="/api/ci-watcher")
app.include_router(llm_router, prefix="/api/llm")
app.include_router(repo_router, prefix="/api/repo")
