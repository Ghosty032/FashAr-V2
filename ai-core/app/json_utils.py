"""
Pulling structured output out of models that will not stay on script.

`JsonOutputParser` assumes the response *is* JSON. Several models this project can use do
not cooperate:

  - reasoning models (nvidia/nemotron-3-*) narrate their working first and put the JSON at
    the end
  - some wrap the object in ```json fences
  - some add a sentence of preamble before it

All three parse fine once the object is isolated, so nodes fall back to this rather than
failing the whole request.
"""

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _balanced_spans(text: str):
    """
    Yield (start, end) for every balanced {...} span at any nesting depth.

    A greedy regex like r'\\{[\\s\\S]*\\}' spans from the first brace to the last, which
    swallows reasoning text containing braces and produces nothing parseable. This tracks
    depth and string state instead, so braces inside string literals do not confuse it.
    """
    depth = 0
    start = -1
    in_string = False
    escaped = False

    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    yield start, i + 1
                    start = -1


def extract_json_object(raw_text: str) -> dict | None:
    """
    Return the most likely JSON answer in `raw_text`, or None.

    Prefers the LAST parseable object: a reasoning model works through the problem first
    and states its answer at the end, so the final object is the conclusion rather than an
    intermediate sketch.
    """
    if not raw_text:
        return None

    # A fenced block, when present, is the intended answer — check those first.
    candidates: list[str] = [m.group(1) for m in _FENCE.finditer(raw_text)]
    candidates.extend(raw_text[s:e] for s, e in _balanced_spans(raw_text))

    best: dict | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed:
            best = parsed  # keep going; later objects win
    return best


def coerce_to_dict(parsed, list_key: str, extra: dict | None = None) -> dict | None:
    """
    Normalise a parsed response into a dict.

    Models sometimes return just the array when a schema's only interesting field is a
    list, so wrap that under `list_key` rather than discarding a valid answer.
    """
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {list_key: parsed, **(extra or {})}
    return None
