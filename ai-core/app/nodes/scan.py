import asyncio
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from app.schemas.state import AgentState
from app.schemas.models import ScanResult
from app.prompts.prompts import SCANNER_SYSTEM_PROMPT
from app.config import LLM_TIMEOUT_SECONDS, VISION_MODEL, TEXT_SCAN_MODEL
from app.json_utils import coerce_to_dict, extract_json_object
from app.nim import ainvoke_with_retry


async def scan_outfit(state: AgentState) -> dict:
    """
    Node 1: Receives the outfit (image or text) and extracts a factual
    list of garments and colors.
    """
    print("--- [NODE] Scanning Outfit ---")
    
    if state.get("image_base64"):
        model_name = VISION_MODEL
    else:
        # Text-only path does not need a vision model.
        model_name = TEXT_SCAN_MODEL
        
    try:
        llm = ChatNVIDIA(model=model_name, temperature=0.1, max_completion_tokens=4096)
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

        # One call, then extract — see the note in critique.py. Chaining `llm | parser`
        # and retrying on failure meant paying for a second call whose output could come
        # back truncated, throwing away a perfectly good first response.
        raw_response = await ainvoke_with_retry(llm, messages, LLM_TIMEOUT_SECONDS)
        raw_text = getattr(raw_response, "content", str(raw_response))

        result_dict = extract_json_object(raw_text)
        if not result_dict:
            raise ValueError(f"Could not extract JSON from model response: {raw_text[-400:]}")

        # Some models return just the garment array when that is the schema's main field.
        result_dict = coerce_to_dict(result_dict, "detected_items", {"color_palette": []})
        if result_dict is None:
            raise ValueError("Model response was neither a JSON object nor an array.")


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
        # The graph continues with an empty scan so the critic can still respond to the
        # user's stated occasion and persona, but the reason is recorded. Without it, a
        # failed vision call is indistinguishable from a photo containing no clothes.
        print(f"Error in scan_outfit: {type(e).__name__}: {e}")
        return {
            "scan_result": ScanResult(detected_items=[], color_palette=[]),
            "error": f"Scan step failed ({type(e).__name__}): {e}",
        }
