import sys
import os
import pytest

# Ensure the backend/ directory is on sys.path so `from app.xxx import ...`
# works regardless of how pytest is invoked (locally or in CI).
sys.path.insert(0, os.path.dirname(__file__))

# Run tests in development mode so docs endpoints are available and rate
# limiters use their default dev-friendly configuration.
os.environ.setdefault("ENVIRONMENT", "development")


# Restrict anyio tests to asyncio only — trio is not in the project's
# dependencies and would cause test failures when the package isn't installed.
@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param
