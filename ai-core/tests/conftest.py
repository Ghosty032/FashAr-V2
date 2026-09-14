"""
Shared test configuration.

The gateway secret is set before `app` is imported anywhere, because app.config reads the
environment at import time and app.deps binds GATEWAY_SECRET as a module constant.
"""

import os
import sys
from pathlib import Path

# Allow `import app...` when pytest is run from the repo root as well as from ai-core/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_SECRET = "test-gateway-secret"
os.environ.setdefault("GATEWAY_SECRET", TEST_SECRET)
os.environ.setdefault("RATE_LIMIT_REQUESTS", "3")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "3600")

import pytest  # noqa: E402


@pytest.fixture
def client():
    """TestClient with server exceptions surfaced as responses, not raised."""
    from fastapi.testclient import TestClient
    import app.main as main

    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers():
    """Headers a correctly-behaving Next.js gateway would send."""
    return {"x-gateway-secret": TEST_SECRET, "x-user-id": "test_user"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    The limiter is module-level state, so it leaks between tests without this.
    """
    import app.deps as deps

    deps._request_log.clear()
    yield
    deps._request_log.clear()
