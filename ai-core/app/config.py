"""
Single source of truth for AI Core configuration.

Importing this module loads the environment exactly once and exposes every setting as a
typed constant. Nothing else in the codebase should call `load_dotenv` or reach for
`os.getenv` directly — three modules used to do both, each with its own path arithmetic,
and two of them pointed at a directory that does not exist.

RESOLUTION ORDER (first match wins):
  1. Real environment variables — how Render and Vercel inject config in production
  2. ai-core/.env             — the conventional place for backend-only local settings
  3. frontend/.env.local      — historical location; still supported so existing local
                                setups keep working

Key names are accepted in several spellings because the project has accumulated variants
(`NVIDIA_NVIM_KEY` in .env.local, `NVIDIA_NIM_API_KEY` in an older template, and
`NVIDIA_API_KEY` which is what LangChain itself looks for). Rather than force a rename
across every deployment target at once, each setting lists its accepted aliases.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_AI_CORE_ROOT = Path(__file__).resolve().parents[1]   # .../ai-core
_REPO_ROOT = _AI_CORE_ROOT.parent                     # repo root

# override=False throughout, so real environment variables always beat file contents and
# the first file found wins over later ones.
for _candidate in (_AI_CORE_ROOT / ".env", _REPO_ROOT / "frontend" / ".env.local"):
    if _candidate.is_file():
        load_dotenv(_candidate, override=False)


def _first(*names: str, default: str | None = None) -> str | None:
    """Return the first alias that is set and non-empty."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


# ==========================================================================================
# Credentials
# ==========================================================================================
NVIDIA_API_KEY = _first("NVIDIA_NVIM_KEY", "NVIDIA_NIM_API_KEY", "NVIDIA_API_KEY")
if NVIDIA_API_KEY:
    # LangChain's ChatNVIDIA reads this specific name from the environment.
    os.environ["NVIDIA_API_KEY"] = NVIDIA_API_KEY

PINECONE_KEY = _first("PINECONE_KEY", "PINECONE_API_KEY")
OPENWEATHER_KEY = _first("OPENWEATHER_KEY", "OPENWEATHER_API_KEY", "OPENWEATHERMAP_API_KEY")

# Shared secret proving a request came from the Next.js gateway. No default: a missing
# value must fail closed rather than silently allow everything.
GATEWAY_SECRET = _first("GATEWAY_SECRET")


# ==========================================================================================
# Pinecone
# ==========================================================================================
PINECONE_INDEX = _first("PINECONE_INDEX", "PINECONE_INDEX_NAME", default="fashr-products-v2")
PINECONE_NAMESPACE = _first("PINECONE_NAMESPACE", default="__default__")


# ==========================================================================================
# Models
#
# NVIDIA retires hosted models regularly — several this project used reached end of life on
# 2026-08-25. Keeping the IDs here means repointing them is a config change, not a code
# change. Verify candidates against `GET https://integrate.api.nvidia.com/v1/models`;
# `ChatNVIDIA.get_available_models()` reads a stale table baked into the library and will
# happily list models that no longer exist.
# ==========================================================================================
VISION_MODEL = _first("VISION_MODEL", default="meta/llama-3.2-90b-vision-instruct")
TEXT_SCAN_MODEL = _first("TEXT_SCAN_MODEL", default="meta/llama-3.1-70b-instruct")
CRITIC_MODEL = _first("CRITIC_MODEL", default="meta/llama-3.1-405b-instruct")


# ==========================================================================================
# Limits
#
# ChatNVIDIA has no timeout parameter of its own, and because its model_config sets
# extra="ignore", passing `timeout=...` to the constructor is silently dropped rather than
# raising. The nodes enforce timeouts with asyncio.wait_for instead; its async path runs on
# aiohttp, so cancellation does reach the in-flight request.
#
# The layers nest, tightest first:
#   LLM_TIMEOUT (40s per call) < ANALYSIS_TIMEOUT (55s whole graph)
#     < the gateway's fetch abort (58s) < Vercel's maxDuration (60s)
# ==========================================================================================
LLM_TIMEOUT_SECONDS = float(_first("LLM_TIMEOUT_SECONDS", default="40"))
ANALYSIS_TIMEOUT_SECONDS = float(_first("ANALYSIS_TIMEOUT_SECONDS", default="55"))

RATE_LIMIT_REQUESTS = int(_first("RATE_LIMIT_REQUESTS", default="20"))
RATE_LIMIT_WINDOW_SECONDS = int(_first("RATE_LIMIT_WINDOW_SECONDS", default="3600"))


# ==========================================================================================
# Startup diagnostics
# ==========================================================================================
#: Settings the service cannot usefully run without, and what breaks when each is absent.
REQUIRED = {
    "GATEWAY_SECRET": "every /analyze request will be rejected with 500",
    "NVIDIA_API_KEY": "scan and critique will fail",
    "PINECONE_KEY": "product recommendations will be empty",
}

#: Optional settings that degrade a feature rather than break the service.
OPTIONAL = {
    "OPENWEATHER_KEY": "weather context will be skipped",
}


def missing_settings() -> list[str]:
    """Names of required settings that are not configured."""
    return [name for name in REQUIRED if not globals().get(name)]


def log_config_status() -> None:
    """
    Print what is and is not configured, once, at startup.

    Worth the noise: the failure mode this replaces was a 500 from deep inside the graph
    with no indication that a key was simply absent.
    """
    print("--- [CONFIG] AI Core settings ---")
    print(f"  index={PINECONE_INDEX} namespace={PINECONE_NAMESPACE}")
    print(f"  models: vision={VISION_MODEL} text={TEXT_SCAN_MODEL} critic={CRITIC_MODEL}")
    print(f"  limits: llm={LLM_TIMEOUT_SECONDS}s graph={ANALYSIS_TIMEOUT_SECONDS}s "
          f"rate={RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW_SECONDS}s")

    for name, consequence in REQUIRED.items():
        if not globals().get(name):
            print(f"  MISSING {name} — {consequence}")
    for name, consequence in OPTIONAL.items():
        if not globals().get(name):
            print(f"  absent  {name} — {consequence}")

    if not missing_settings():
        print("  all required settings present")
