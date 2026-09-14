"""
JSON extraction and transient-error retry.

Both exist because the models this project can reach do not behave like the happy path
LangChain assumes: reasoning models narrate before answering, and the hosted free tier
returns 503 under load.
"""

import asyncio

import pytest

from app.json_utils import coerce_to_dict, extract_json_object
from app.nim import ainvoke_with_retry, is_transient


# ==========================================================================================
# extract_json_object
# ==========================================================================================

def test_plain_object():
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_object_after_reasoning():
    """
    The real failure mode: nvidia/nemotron-3-* works through the problem first and states
    its answer last. JsonOutputParser rejects the whole response.
    """
    raw = (
        "We need to output JSON matching the schema.\n"
        "Color Cohesion: maybe 85. Occasion: maybe 60.\n"
        'Rough sketch: {"style_score": 0}\n'
        "Now output.\n"
        '{"style_score": 68, "gap_type": "structure"}'
    )
    assert extract_json_object(raw) == {"style_score": 68, "gap_type": "structure"}


def test_prefers_the_final_object():
    """Intermediate sketches must lose to the stated conclusion."""
    assert extract_json_object('{"draft": 1} then {"final": 2}') == {"final": 2}


def test_markdown_fence():
    assert extract_json_object('Here:\n```json\n{"a": 1}\n```\nDone.') == {"a": 1}


def test_brace_inside_string_does_not_break_parsing():
    """A naive brace counter would terminate early here."""
    raw = '{"note": "closing } brace in a string", "ok": true}'
    assert extract_json_object(raw) == {"note": "closing } brace in a string", "ok": True}


def test_nested_objects():
    raw = '{"outer": {"inner": {"deep": 1}}, "n": 2}'
    assert extract_json_object(raw) == {"outer": {"inner": {"deep": 1}}, "n": 2}


def test_truncated_json_returns_none():
    """A response cut off mid-object has no balanced span and must not half-parse."""
    assert extract_json_object('{"style_score": 67, "score_') is None


@pytest.mark.parametrize("raw", ["", "I refuse to answer.", "[1, 2, 3]", "null"])
def test_no_object_returns_none(raw):
    assert extract_json_object(raw) is None


def test_empty_object_is_not_an_answer():
    assert extract_json_object("{}") is None


# ==========================================================================================
# coerce_to_dict
# ==========================================================================================

def test_list_is_wrapped_under_the_named_key():
    """Models sometimes return just the array when that is the schema's main field."""
    out = coerce_to_dict([{"garment_type": "tee"}], "detected_items", {"color_palette": []})
    assert out == {"detected_items": [{"garment_type": "tee"}], "color_palette": []}


def test_dict_passes_through():
    assert coerce_to_dict({"a": 1}, "items") == {"a": 1}


def test_scalar_is_rejected():
    assert coerce_to_dict("nope", "items") is None


# ==========================================================================================
# Transient-error retry
# ==========================================================================================

@pytest.mark.parametrize("message", [
    "[###] {'message': 'Service temporarily overloaded', 'code': 503}",
    "HTTP 429 Too Many Requests",
    "502 Bad Gateway",
])
def test_recognises_transient_errors(message):
    assert is_transient(Exception(message))


@pytest.mark.parametrize("message", [
    "404 Not Found",
    "410 Gone: model reached end of life",
    "403 Forbidden: Authorization failed",
])
def test_permanent_errors_are_not_transient(message):
    """Retrying a retired model or a bad key only burns the time budget."""
    assert not is_transient(Exception(message))


class FlakyLLM:
    """Fails with a transient error `fail_times` times, then succeeds."""

    def __init__(self, fail_times, exc=None):
        self.fail_times = fail_times
        self.calls = 0
        self._exc = exc or Exception("Service temporarily overloaded 503")

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self._exc
        return "recovered"


@pytest.mark.asyncio
async def test_retries_until_success():
    llm = FlakyLLM(fail_times=2)
    assert await ainvoke_with_retry(llm, [], budget_seconds=10) == "recovered"
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_gives_up_after_attempts():
    llm = FlakyLLM(fail_times=99)
    with pytest.raises(Exception, match="overloaded"):
        await ainvoke_with_retry(llm, [], budget_seconds=10, attempts=3)
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_permanent_error_is_not_retried():
    llm = FlakyLLM(fail_times=99, exc=Exception("410 Gone: retired"))
    with pytest.raises(Exception, match="Gone"):
        await ainvoke_with_retry(llm, [], budget_seconds=10)
    assert llm.calls == 1, "a permanent failure must not be retried"


@pytest.mark.asyncio
async def test_budget_is_shared_not_per_attempt():
    """
    Retries must never push a node past the deadline the graph is working to. With a tiny
    budget, backoff alone would exceed it, so it must stop rather than sleep past it.
    """
    llm = FlakyLLM(fail_times=99)
    started = asyncio.get_running_loop().time()
    with pytest.raises(Exception):
        await ainvoke_with_retry(llm, [], budget_seconds=0.3, attempts=5)
    assert asyncio.get_running_loop().time() - started < 2.0


@pytest.mark.asyncio
async def test_slow_call_times_out_within_budget():
    class HangingLLM:
        async def ainvoke(self, messages):
            await asyncio.sleep(30)

    with pytest.raises(asyncio.TimeoutError):
        await ainvoke_with_retry(HangingLLM(), [], budget_seconds=0.4)
