import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.schemas.state import AgentState
from app.graph import app as fashr_graph

state = {
    "text_description": "I am wearing a blue jacket and blue jeans with white sneakers.",
    "occasion": "Casual - Walking",
    "style_persona": "Minimalist",
    "gender": "mens",
    "body_type": ["athletic"],
    "image_base64": None
}

print("Running graph...")
try:
    result = fashr_graph.invoke(state)
    print("\n[SCAN RESULT]\n", result.get("scan_result"))
    print("\n[CRITIQUE RESULT]\n", result.get("critique_result"))
    print("\n[RECOMMENDED PRODUCTS]\n", result.get("recommended_products"))
except Exception as e:
    import traceback
    traceback.print_exc()
