import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.base import DispatchFunction
from starlette.types import ASGIApp
from app.api.routes.repo import router as repo_router
from app.api.routes.auth import router as auth_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.plan import router as plan_router
from app.api.routes.coder import router as coder_router
from app.api.routes.guardrail import router as guardrail_router
from app.api.routes.lens import router as lens_router

# --- CORS config ---
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://shipmate-ai.vercel.app",
    "https://shipmate-ai-demo.vercel.app",
    "https://shipmate-ai-demo-git-main-namanns7cr7.vercel.app",
    "https://shipmate-ai-demo-git-dev-namanns7cr7.vercel.app",
]

_LOCAL_HOSTS = {"localhost", "127.0.0.1"}
_ENDPOINT_ENV_VARS = ["FRONTEND_URL", "FRONTEND_URL_ALT"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

TRUST_X_FORWARDED_FOR = os.environ.get("TRUST_X_FORWARDED_FOR", "false").lower() == "true"


def _is_origin_allowed(origin: str) -> bool:
    if origin is None:
        return False
    if origin in _ALLOWED_ORIGINS:
        return True
    for var in _ENDPOINT_ENV_VARS:
        env_val = os.environ.get(var)
        if env_val and origin == env_val:
            return True
    return False


def _validate_origin(origin: str) -> str:
    if _is_origin_allowed(origin):
        return origin
    return _ALLOWED_ORIGINS[0]


def _validate_endpoint_urls():
    for var in _ENDPOINT_ENV_VARS:
        env_val = os.environ.get(var)
        if env_val and not _is_origin_allowed(env_val):
            raise RuntimeError(f"Endpoint env var {var}={env_val} is not in allowed origins.")


def _get_client_ip(request: Request) -> str:
    if TRUST_X_FORWARDED_FOR:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the leftmost IP (client's IP)
            return x_forwarded_for.split(",")[0].strip()
    return request.client.host


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.scheme == "http":
            host = request.headers.get("host", "")
            if host.split(":")[0] not in _LOCAL_HOSTS:
                url = request.url.replace(scheme="https")
                return Response(status_code=307, headers={"Location": str(url)})
        return await call_next(request)

app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(repo_router, prefix="/api/repo")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(actuate_router, prefix="/api/actuate")
app.include_router(analyze_router, prefix="/api/analyze")
app.include_router(plan_router, prefix="/api/plan")
app.include_router(coder_router, prefix="/api/coder")
app.include_router(guardrail_router, prefix="/api/guardrail")
app.include_router(lens_router, prefix="/api/lens")
