from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
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
    
    if state.get("image_base64"):
        model_name = "meta/llama-3.2-90b-vision-instruct"
    else:
        model_name = "meta/llama-3.1-405b-instruct"
        
    try:
        llm = ChatNVIDIA(model=model_name, temperature=0.1)
        parser = JsonOutputParser(pydantic_object=ScanResult)
        
        # Inject JSON format instructions into the system prompt
        system_content = SCANNER_SYSTEM_PROMPT + "\n\n{format_instructions}"
        instruction_text = parser.get_format_instructions()
        system_msg = SystemMessage(content=system_content.replace("{format_instructions}", instruction_text))
        
        messages = [system_msg]
        
        if state.get("image_base64"):
            messages.append(HumanMessage(content=[
                {"type": "text", "text": "Analyze this outfit."},
                {"type": "image_url", "image_url": {"url": state["image_base64"]}}
            ]))
        elif state.get("text_description"):
            messages.append(HumanMessage(content=state["text_description"]))
        else:
            raise ValueError("No image or text description provided.")
            
        print(f"Calling NVIDIA NIM Vision Model: {model_name}...")
        result_dict = (llm | parser).invoke(messages)
        
        # Parse into Pydantic model
        result = ScanResult(**result_dict)
        print("Scan successful!")
        return {"scan_result": result}
        
    except Exception as e:
        print(f"Error in scan_outfit: {e}")
        # Fallback empty result so the graph doesn't crash
        return {"scan_result": ScanResult(detected_items=[], color_palette=[])}
