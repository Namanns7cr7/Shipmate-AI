import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.actuate import router as actuate_router
from app.api.routes.repo import router as repo_router
from app.api.routes.branch import router as branch_router
from app.api.routes.coder import router as coder_router
from app.api.routes.plan_forge import router as plan_forge_router
from app.api.routes.guardrail import router as guardrail_router
from app.api.routes.shipmate import router as shipmate_router

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true"


def _get_client_ip(request: Request) -> str:
    if TRUST_X_FORWARDED_FOR:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the left-most IP (client IP)
            return x_forwarded_for.split(",")[0].strip()
    return request.client.host


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        host = request.headers.get("host", "")
        client_ip = _get_client_ip(request)
        if host and not any(h in host for h in _LOCAL_HOSTS):
            if request.url.scheme == "http":
                url = request.url.replace(scheme="https")
                return JSONResponse(
                    status_code=307,
                    content={"detail": "HTTPS required", "redirect": str(url)}
                )
        return await call_next(request)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"]
)

app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(analysis_router, prefix="/api/analyze")
app.include_router(actuate_router, prefix="/api/actuate")
app.include_router(repo_router, prefix="/api/repo")
app.include_router(branch_router, prefix="/api/branch")
app.include_router(coder_router, prefix="/api/coder")
app.include_router(plan_forge_router, prefix="/api/plan-forge")
app.include_router(guardrail_router, prefix="/api/guardrail")
app.include_router(shipmate_router, prefix="/api/shipmate")


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.middleware("http")
async def malformed_json_body_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        if hasattr(exc, "body") and exc.body:
            return JSONResponse(
                status_code=400,
                content={"detail": "Malformed JSON body"}
            )
        raise
