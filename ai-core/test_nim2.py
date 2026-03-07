import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import app.config
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.schemas.models import ScanResult
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatNVIDIA(model="meta/llama-3.1-405b-instruct", temperature=0.1)

# Try with json_schema method or include_raw=True
structured_llm = llm.with_structured_output(ScanResult, method="json_schema", include_raw=True)

messages = [
    SystemMessage(content="You are an expert fashion AI. Extract the clothing and color palette."),
    HumanMessage(content="I am wearing a blue jacket and blue jeans with white sneakers.")
]

print("Calling NVIDIA NIM...")
try:
    result = structured_llm.invoke(messages)
    print("Result Raw:")
    print(result["raw"])
    print("Result Parsed:")
    print(result["parsed"])
except Exception as e:
    print("Exception thrown:")
    print(e)
