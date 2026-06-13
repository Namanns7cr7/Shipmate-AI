FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Build context is the backend/ directory (self-contained), so paths are
# relative to backend/. This lets `az containerapp up --source backend` use
# THIS Dockerfile instead of falling back to the Oryx buildpack (which guesses
# a WSGI `application` entrypoint and crash-loops our ASGI app). CI's
# docker-smoke job sets `context: backend` to match.

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check — use stdlib urllib (no `requests` dep) and fail non-zero on a
# non-200 so an unhealthy container is actually reported as such.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
