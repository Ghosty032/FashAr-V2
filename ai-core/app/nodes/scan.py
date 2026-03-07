from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from app.schemas.state import AgentState
from app.schemas.models import ScanResult
from app.prompts.prompts import SCANNER_SYSTEM_PROMPT
import app.config  # ensures API key is loaded

def scan_outfit(state: AgentState) -> AgentState:
    """
    Node 1: Receives the outfit (image or text) and extracts a factual
    list of garments and colors.
    """
    print("--- [NODE] Scanning Outfit ---")
    
    # We use a reliable multimodal model from NIM for the vision task.
    # E.g., meta/llama-3.2-90b-vision-instruct is excellent for visual QA.
    # If the user only provided text, we can use a standard LLM.
    if state.get("image_base64"):
        model_name = "meta/llama-3.2-90b-vision-instruct"
        # model_name = "nvidia/nemotron-4-340b-instruct" # alternative if vision is offline
    else:
        model_name = "meta/llama-3.1-405b-instruct"
        
    try:
        llm = ChatNVIDIA(model=model_name, temperature=0.1)
        structured_llm = llm.with_structured_output(ScanResult)
        
        messages = [SystemMessage(content=SCANNER_SYSTEM_PROMPT)]
        
        if state.get("image_base64"):
            messages.append(HumanMessage(content=[
                {"type": "text", "text": "Analyze this outfit."},
                {"type": "image_url", "image_url": {"url": state["image_base64"]}}
            ]))
        elif state.get("text_description"):
            messages.append(HumanMessage(content=state["text_description"]))
        else:
            raise ValueError("No image or text description provided.")
            
        result = structured_llm.invoke(messages)
        return {"scan_result": result}
        
    except Exception as e:
        print(f"Error in scan_outfit: {e}")
        # Fallback empty result so the graph doesn't crash
        return {"scan_result": ScanResult(detected_items=[], color_palette=[])}
