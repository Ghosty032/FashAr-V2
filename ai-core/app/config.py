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
