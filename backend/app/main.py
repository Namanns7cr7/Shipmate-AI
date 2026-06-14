import os
import logging
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

app = FastAPI()

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "https://shipmate-ai.vercel.app",
]


def _is_origin_allowed(origin: str) -> bool:
    return origin in ALLOWED_ORIGINS


def _validate_origin(origin: str) -> str:
    if _is_origin_allowed(origin):
        return origin
    return ""


def _get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs, take the first one
        ip = x_forwarded_for.split(",")[0].strip()
        logging.info(f"Extracted client IP from X-Forwarded-For: {ip}")
        return ip
    ip = request.client.host if request.client else ""
    logging.info(f"Extracted client IP from request.client: {ip}")
    return ip


def _validate_endpoint_urls(urls):
    # Dummy implementation for test import
    return True

_LOCAL_HOSTS = ["localhost", "127.0.0.1"]
_ENDPOINT_ENV_VARS = ["API_URL", "FRONTEND_URL"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "secret"))

# Example endpoint
@app.get("/")
def read_root():
    return {"Hello": "World"}
