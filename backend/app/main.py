import logging
import os
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ... [other imports and routers as in original, untouched]

# Helper function for config value

def _get_config_value(key: str, default=None):
    return os.environ.get(key, default)

# Example middleware using _get_config_value
class ClientIPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _get_config_value("ENABLE_CLIENT_IP_MIDDLEWARE", False):
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(",")[0].strip()
            else:
                client_ip = request.client.host
            logging.info(f"Client IP: {client_ip}")
        response = await call_next(request)
        return response

app = FastAPI()

# ... [router includes and other setup as in original, untouched]

app.add_middleware(ClientIPMiddleware)

# ... [rest of app code as in original, untouched]
