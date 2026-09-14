"""
FASHR — Verify the NVIDIA NIM key and the configured model IDs.

Run this after changing NVIDIA credentials or when scan/critique starts failing:

    python ai-core/scripts/check_models.py

It answers the two questions that actually matter, separately, because they fail the
same way from inside the app but need completely different fixes:

  1. Can this key run inference at all?  A key that lists models fine but returns 403 on
     every completion has no inference entitlement — exhausted credits or a revoked key.
     No code change will help.

  2. Do the configured model IDs still exist?  NVIDIA retires hosted models regularly;
     three of this project's models went end-of-life on a single day.

When a configured model is dead it probes alternatives and prints the exact environment
variable to set.

IMPORTANT: candidates are probed against the live API. Do not trust
`ChatNVIDIA.get_available_models()` — it reads a static table compiled into
langchain-nvidia-ai-endpoints and happily lists models that no longer exist.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import (  # noqa: E402
    CRITIC_MODEL,
    NVIDIA_API_KEY,
    TEXT_SCAN_MODEL,
    VISION_MODEL,
)

BASE = "https://integrate.api.nvidia.com/v1"

# Tried in order when a configured model is dead. Vision-capable ones are marked, since the
# image path needs one and a text model there fails only at request time.
FALLBACK_CANDIDATES = [
    ("meta/llama-3.2-90b-vision-instruct", True),
    ("meta/llama-3.2-11b-vision-instruct", True),
    ("nvidia/llama-3.1-nemotron-70b-instruct", False),
    ("nvidia/llama-3.1-nemotron-ultra-253b-v1", False),
    ("nvidia/nemotron-3-super-120b-a12b", False),
    ("nvidia/nemotron-nano-3-30b-a3b", False),
    ("mistralai/mistral-large-2-instruct", False),
    ("meta/llama-3.2-3b-instruct", False),
]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def list_live_models() -> list[str] | None:
    """Model ids the API itself reports. None if even listing fails."""
    req = urllib.request.Request(f"{BASE}/models", headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return sorted(m["id"] for m in json.load(resp).get("data", []))
    except urllib.error.HTTPError as exc:
        print(f"  listing failed: HTTP {exc.code}")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  listing failed: {exc}")
        return None


def probe(model: str) -> tuple[bool, str]:
    """Send the smallest possible completion. Returns (usable, explanation)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(payload).encode(), headers=_headers()
    )
    try:
        with urllib.request.urlopen(req, timeout=60):
            return True, "usable"
    except urllib.error.HTTPError as exc:
        body = exc.read()[:160].decode("utf-8", "replace").replace("\n", " ")
        reason = {
            403: "forbidden — key has no inference entitlement for this model",
            404: "not found — the id no longer exists",
            410: "gone — retired by NVIDIA",
            429: "rate limited — try again shortly",
        }.get(exc.code, body)
        return False, f"HTTP {exc.code}: {reason}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    if not NVIDIA_API_KEY:
        print("NVIDIA API key is not configured.")
        print("Set NVIDIA_NVIM_KEY in frontend/.env.local (or ai-core/.env) and re-run.")
        return 1

    print(f"Key loaded: {NVIDIA_API_KEY[:6]}… ({len(NVIDIA_API_KEY)} chars)\n")

    print("1. Can the key list models?")
    live = list_live_models()
    if live is None:
        print("\n   The key cannot even list models — it is invalid or revoked.")
        return 1
    print(f"   yes — {len(live)} models listed\n")

    configured = {
        "VISION_MODEL": VISION_MODEL,
        "TEXT_SCAN_MODEL": TEXT_SCAN_MODEL,
        "CRITIC_MODEL": CRITIC_MODEL,
    }

    print("2. Do the configured models work?")
    results = {}
    for var, model in configured.items():
        usable, detail = probe(model)
        results[var] = usable
        mark = "OK  " if usable else "FAIL"
        print(f"   {mark} {var:16} {model}")
        if not usable:
            print(f"        {detail}")

    if all(results.values()):
        print("\nAll configured models are usable. Nothing to change.")
        return 0

    # A 403 on every single model means the key is the problem, not the ids.
    print("\n3. Probing alternatives…")
    working: list[tuple[str, bool]] = []
    for candidate, vision in FALLBACK_CANDIDATES:
        if candidate in configured.values():
            continue
        usable, detail = probe(candidate)
        tag = " (vision)" if vision else ""
        print(f"   {'OK  ' if usable else 'fail'} {candidate}{tag}")
        if usable:
            working.append((candidate, vision))

    if not working:
        print("\n" + "=" * 78)
        print("No model on this account can run inference, including ones the API lists as")
        print("available. That is an ACCOUNT problem, not a code problem — the key has no")
        print("inference entitlement (exhausted credits, or revoked).")
        print("Changing model IDs will not help. Get a key with inference access at")
        print("https://build.nvidia.com/ and re-run this script.")
        print("=" * 78)
        return 1

    vision_options = [m for m, v in working if v]
    text_options = [m for m, _ in working]

    print("\n" + "=" * 78)
    print("Set these and restart the AI Core:\n")
    if not results["VISION_MODEL"] and vision_options:
        print(f"  VISION_MODEL={vision_options[0]}")
    if not results["TEXT_SCAN_MODEL"] and text_options:
        print(f"  TEXT_SCAN_MODEL={text_options[0]}")
    if not results["CRITIC_MODEL"] and text_options:
        # Prefer the largest usable model for the reasoning step.
        print(f"  CRITIC_MODEL={text_options[0]}")
    if not results["VISION_MODEL"] and not vision_options:
        print("  WARNING: no vision-capable model is usable. The image upload path will")
        print("  fail; only the text description path will work.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
