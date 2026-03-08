import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import app.config
from langchain_nvidia_ai_endpoints import ChatNVIDIA

try:
    print("Fetching models...")
    models = ChatNVIDIA.get_available_models()
    for m in models:
        # print only llama models to find the 70b version
        if "llama" in m.id.lower():
            print(m.id)
except Exception as e:
    print(e)
