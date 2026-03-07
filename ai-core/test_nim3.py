import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import app.config
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.schemas.models import ScanResult
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

llm = ChatNVIDIA(model="meta/llama-3.1-405b-instruct", temperature=0.1)
parser = JsonOutputParser(pydantic_object=ScanResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert fashion AI. Extract the clothing and color palette.\n\n{format_instructions}"),
    ("human", "{text}")
])

chain = prompt | llm | parser

print("Calling NVIDIA NIM with JsonOutputParser...")
try:
    result = chain.invoke({
        "text": "I am wearing a blue jacket and blue jeans with white sneakers.",
        "format_instructions": parser.get_format_instructions()
    })
    print("Result Parsed:")
    print(result)
except Exception as e:
    print("Exception thrown:")
    print(e)
