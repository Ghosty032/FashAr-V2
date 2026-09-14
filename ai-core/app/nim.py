"""
Calling NVIDIA NIM without falling over on transient capacity errors.

The hosted free tier returns 503 "Service temporarily overloaded" fairly regularly — in
testing roughly one call in three during busy periods. Those failures come back almost
immediately, so retrying costs a fraction of a second and turns a failed analysis into a
successful one.

Permanent failures (a retired model, a key without entitlement) are NOT retried: they will
fail identically every time and retrying only burns the request's time budget.
"""

import asyncio
import time

#: Substrings identifying a failure that is worth trying again. NIM surfaces these as
#: generic Exceptions with the status embedded in the message, so there is no exception
#: type or status attribute to match on.
_TRANSIENT_MARKERS = (
    "503",
    "service temporarily overloaded",
    "service unavailable",
    "429",
    "too many requests",
    "rate limit",
    "502",
    "bad gateway",
    "504",
    "gateway timeout",
)


def is_transient(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


async def ainvoke_with_retry(llm, messages, budget_seconds: float, attempts: int = 3):
    """
    Invoke `llm`, retrying transient failures within a total time budget.

    The budget is shared across attempts rather than applied per attempt, so a retry can
    never push the node past the deadline the graph is working to. Each attempt gets
    whatever time is left; once that is gone the last error is raised.
    """
    deadline = time.monotonic() + budget_seconds
    backoff = 0.5
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        try:
            return await asyncio.wait_for(llm.ainvoke(messages), timeout=remaining)
        except asyncio.TimeoutError:
            # Out of budget. Retrying cannot help and would exceed the deadline.
            raise
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not is_transient(exc) or attempt == attempts:
                raise

            # Do not sleep past the deadline just to fail again.
            if time.monotonic() + backoff >= deadline:
                raise
            print(f"  transient NIM error (attempt {attempt}/{attempts}), retrying in {backoff}s")
            await asyncio.sleep(backoff)
            backoff *= 2

    if last_exc:
        raise last_exc
    raise RuntimeError("LLM call exhausted its time budget without a response")
