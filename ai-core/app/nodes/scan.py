import re
import json
import asyncio
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from app.schemas.state import AgentState
from app.schemas.models import ScanResult
from app.prompts.prompts import SCANNER_SYSTEM_PROMPT
import app.config  # ensures API key is loaded
from app.config import LLM_TIMEOUT_SECONDS


def _extract_json_from_text(raw_text: str) -> dict | None:
    """
    Fallback: if the model wraps JSON in prose like 'Sure, here is...',
    extract the first JSON object using regex.
    """
    # Try to find a JSON object {...}
    match = re.search(r'\{[\s\S]*\}', raw_text)
    if match:
        try:
            parsed = json.loads(match.group())
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    return None


async def scan_outfit(state: AgentState) -> dict:
    """
    Node 1: Receives the outfit (image or text) and extracts a factual
    list of garments and colors.
    """
    print("--- [NODE] Scanning Outfit ---")
    
    if state.get("image_base64"):
        model_name = "meta/llama-3.2-90b-vision-instruct"
    else:
        # Fast Parser Agent (70B)
        model_name = "meta/llama-3.1-70b-instruct"
        
    try:
        llm = ChatNVIDIA(model=model_name, temperature=0.1)
        parser = JsonOutputParser(pydantic_object=ScanResult)
        
        # Inject JSON format instructions into the system prompt
        # Also add a strong instruction to output ONLY JSON
        system_content = (
            SCANNER_SYSTEM_PROMPT
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
            + "Do NOT include any text before or after the JSON.\n\n"
            + "{format_instructions}"
        )
        instruction_text = parser.get_format_instructions()
        system_msg = SystemMessage(content=system_content.replace("{format_instructions}", instruction_text))
        
        messages = [system_msg]
        
        if state.get("image_base64"):
            messages.append(HumanMessage(content=[
                {"type": "text", "text": "Analyze this outfit. Respond with ONLY JSON."},
                {"type": "image_url", "image_url": {"url": state["image_base64"]}}
            ]))
        elif state.get("text_description"):
            messages.append(HumanMessage(content=state["text_description"] + "\n\nRespond with ONLY JSON."))
        else:
            raise ValueError("No image or text description provided.")
            
        print(f"Calling NVIDIA NIM Vision Model: {model_name}...")
        
        # Try the standard parser first
        try:
            result_dict = await asyncio.wait_for(
                (llm | parser).ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            # A hung call must not silently become a retry — that would double the budget.
            raise
        except Exception as parse_err:
            print(f"Parser failed, attempting manual JSON extraction: {parse_err}")
            # Fallback: get raw text and extract JSON manually
            raw_response = await asyncio.wait_for(
                llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
            )
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            result_dict = _extract_json_from_text(raw_text)
            if not result_dict:
                raise ValueError(f"Could not extract JSON from model response: {raw_text[:200]}")
        
        # Handle case where parser returns a list instead of dict
        if isinstance(result_dict, list):
            print("Parser returned a list, wrapping in dict...")
            result_dict = {"detected_items": result_dict, "color_palette": []}
        
        # Parse into Pydantic model
        result = ScanResult(**result_dict)
        print("Scan successful!")
        return {"scan_result": result}
        
    except asyncio.TimeoutError:
        # Deliberately not swallowed. An empty scan here would have the critic grade an
        # outfit containing no garments, handing the user a confident-looking score for a
        # call that never actually completed.
        print(f"Error in scan_outfit: timed out after {LLM_TIMEOUT_SECONDS}s")
        raise
    except Exception as e:
        print(f"Error in scan_outfit: {e}")
        # Fallback empty result so the graph doesn't crash
        return {"scan_result": ScanResult(detected_items=[], color_palette=[])}
