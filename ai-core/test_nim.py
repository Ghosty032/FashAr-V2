import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import app.config
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.schemas.models import ScanResult
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatNVIDIA(model="meta/llama-3.1-405b-instruct", temperature=0.1)
structured_llm = llm.with_structured_output(ScanResult)

messages = [
    SystemMessage(content="You are an expert fashion AI."),
    HumanMessage(content="I am wearing a blue jacket and blue jeans with white sneakers.")
]

print("Calling NVIDIA NIM...")
try:
    result = structured_llm.invoke(messages)
    print("Result:")
    print(result)
except Exception as e:
    print("Exception thrown:")
    print(e)
