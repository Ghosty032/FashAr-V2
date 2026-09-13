import os
from dotenv import load_dotenv

# Try to load environment variables.
# We explicitly load the frontend/.env.local where the user put the API key.
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
frontend_env_path = os.path.join(parent_dir, "frontend", ".env.local")
load_dotenv(frontend_env_path)

# LangChain's ChatNVIDIA looks for NVIDIA_API_KEY.
# The user specified it as NVIDIA_NVIM_KEY in .env.local
nim_key = os.getenv("NVIDIA_NVIM_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
if nim_key:
    os.environ["NVIDIA_API_KEY"] = nim_key

# ==========================================================================================
# Timeouts
#
# ChatNVIDIA has no timeout parameter of its own, and because its model_config sets
# extra="ignore", passing `timeout=...` to the constructor is silently dropped rather than
# raising. The nodes therefore enforce timeouts with asyncio.wait_for instead. Its async
# path runs on aiohttp, so cancellation does reach the in-flight request.
#
# The layers are meant to nest, tightest first:
#   LLM_TIMEOUT (40s per call) < ANALYSIS_TIMEOUT (55s whole graph)
#     < the gateway's fetch abort (58s) < Vercel's maxDuration (60s)
# ==========================================================================================
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "40"))
ANALYSIS_TIMEOUT_SECONDS = float(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "55"))
