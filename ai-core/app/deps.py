"""
Gateway authentication and per-user abuse limits for the AI Core.

The AI Core runs on a public URL, but it is only ever called server-to-server by the
Next.js route in `frontend/app/api/analyze/route.ts`, which has already verified the
caller's Clerk session. Two consequences follow:

  1. Every request must present the shared gateway secret. Without it, /analyze is an
     open door to paid NVIDIA NIM inference for anyone who finds the hostname.

  2. The gateway tells us which Clerk user a request belongs to via `X-User-Id`, and we
     rate-limit per user. That header is only trustworthy *because* the gateway secret
     has already proven the caller is our own route — it is never trusted on its own.

The rate limiter lives here rather than in the Next.js route on purpose: Render runs one
long-lived process, so an in-process counter actually holds. On Vercel each invocation
may land on a fresh instance, where the same counter would reset constantly.
"""

import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException

import app.config  # noqa: F401  — ensures the .env file is loaded before we read it

GATEWAY_SECRET = os.getenv("GATEWAY_SECRET")

# Defaults: 20 analyses per user per hour. One analysis is two LLM calls, one of them
# against a 405B model, so this is about cost control rather than traffic shaping.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))

# user id -> timestamps of their recent requests, oldest first
_request_log: dict[str, deque[float]] = defaultdict(deque)

# Above this many tracked users we sweep expired entries so the map cannot grow forever.
_SWEEP_THRESHOLD = 10_000


async def verify_gateway(x_gateway_secret: str | None = Header(default=None)) -> None:
    """Reject anything that is not our own Next.js route."""
    if not GATEWAY_SECRET:
        # Fail closed. A missing secret must never mean "let everyone in".
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: GATEWAY_SECRET is not set.",
        )

    if not x_gateway_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # compare_digest on bytes, so a non-ASCII secret can't raise TypeError here.
    if not hmac.compare_digest(x_gateway_secret.encode(), GATEWAY_SECRET.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _sweep(now: float) -> None:
    """Drop users whose window has fully expired."""
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    stale = [user for user, log in _request_log.items() if not log or log[-1] <= cutoff]
    for user in stale:
        del _request_log[user]


async def enforce_rate_limit(
    _: None = Depends(verify_gateway),
    x_user_id: str | None = Header(default=None),
) -> None:
    """
    Sliding-window limit, per Clerk user.

    Declaring `verify_gateway` as a sub-dependency guarantees the secret is checked
    before we do any bookkeeping, rather than relying on decorator ordering.
    """
    # Our gateway always sends X-User-Id. If it somehow doesn't, share a single bucket
    # rather than creating an unlimited path.
    user = x_user_id or "__anonymous__"
    now = time.monotonic()

    if len(_request_log) > _SWEEP_THRESHOLD:
        _sweep(now)

    log = _request_log[user]

    # Drop anything that has fallen out of the window.
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    while log and log[0] <= cutoff:
        log.popleft()

    if len(log) >= RATE_LIMIT_REQUESTS:
        retry_after = int(log[0] + RATE_LIMIT_WINDOW_SECONDS - now) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached ({RATE_LIMIT_REQUESTS} analyses per hour). Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    # No await between the read above and this write, so the event loop cannot
    # interleave another request in between — no lock needed.
    log.append(now)
