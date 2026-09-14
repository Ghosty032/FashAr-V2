"""
Gateway authentication and rate limiting.

These guard the fix for an endpoint that was previously unauthenticated on a public URL,
where anyone who found the hostname could drain paid inference quota.

No network access required.
"""

import pytest

from conftest import TEST_SECRET

# A request that clears auth but has no valid body. 422 therefore means "authentication
# passed, validation rejected it" — which lets us exercise the gateway without ever
# reaching the LLM calls.
AUTH_PASSED = 422


def test_health_is_public(client):
    """Render's health check must reach this without credentials."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "FASHR AI Core"


def test_health_never_leaks_secret_values(client):
    """It reports which settings are missing, never what they contain."""
    body = resp = client.get("/").text
    assert TEST_SECRET not in body


def test_analyze_rejects_missing_secret(client):
    assert client.post("/analyze").status_code == 401


def test_analyze_rejects_wrong_secret(client):
    resp = client.post("/analyze", headers={"x-gateway-secret": "wrong"})
    assert resp.status_code == 401


def test_analyze_rejects_near_miss_secret(client):
    """Guards the constant-time comparison against a prefix match."""
    resp = client.post("/analyze", headers={"x-gateway-secret": TEST_SECRET[:-1]})
    assert resp.status_code == 401


def test_analyze_accepts_valid_secret(client, auth_headers):
    resp = client.post("/analyze", headers=auth_headers)
    assert resp.status_code == AUTH_PASSED


def test_missing_gateway_secret_fails_closed(client, auth_headers, monkeypatch):
    """
    An unconfigured secret must deny everything, never allow everything.
    """
    import app.deps as deps

    monkeypatch.setattr(deps, "GATEWAY_SECRET", None)
    resp = client.post("/analyze", headers=auth_headers)
    assert resp.status_code == 500
    assert "GATEWAY_SECRET" in resp.json()["detail"]


def test_rate_limit_blocks_after_cap(client, auth_headers):
    """Cap is 3 per user (set in conftest)."""
    codes = [client.post("/analyze", headers=auth_headers).status_code for _ in range(5)]
    assert codes == [AUTH_PASSED, AUTH_PASSED, AUTH_PASSED, 429, 429]


def test_rate_limit_sets_retry_after(client, auth_headers):
    for _ in range(3):
        client.post("/analyze", headers=auth_headers)
    resp = client.post("/analyze", headers=auth_headers)
    assert resp.status_code == 429
    assert int(resp.headers["retry-after"]) > 0


def test_rate_limit_is_per_user(client, auth_headers):
    """One user exhausting their quota must not affect another."""
    for _ in range(3):
        client.post("/analyze", headers=auth_headers)
    assert client.post("/analyze", headers=auth_headers).status_code == 429

    other = {**auth_headers, "x-user-id": "someone_else"}
    assert client.post("/analyze", headers=other).status_code == AUTH_PASSED


@pytest.mark.parametrize("missing", ["occasion_tier_1", "style_persona"])
def test_required_fields_are_enforced(client, auth_headers, missing):
    fields = {
        "occasion_tier_1": "Casual",
        "style_persona": "Minimalist",
        "text_description": "jeans and a tee",
    }
    fields.pop(missing)
    assert client.post("/analyze", headers=auth_headers, data=fields).status_code == 422
