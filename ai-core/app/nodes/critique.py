import asyncio
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from app.schemas.state import AgentState
from app.schemas.models import CritiqueResult
from app.prompts.prompts import CRITIC_SYSTEM_PROMPT
from app.config import LLM_TIMEOUT_SECONDS, CRITIC_MODEL
from app.json_utils import extract_json_object
from app.nim import ainvoke_with_retry

async def critique_outfit(state: AgentState) -> dict:
    """
    Node 2: Takes the factual scan and the user context (occasion, avatar) 
    and returns a brutal but constructive critique + score.
    """
    print("--- [NODE] Critiquing Outfit ---")
    
    try:
     
        # Generous token budget: reasoning models spend most of it narrating, and a cap
        # that truncates mid-JSON produces an unparseable response from a good answer.
        llm = ChatNVIDIA(model=CRITIC_MODEL, temperature=0.66, max_completion_tokens=4096)
        parser = JsonOutputParser(pydantic_object=CritiqueResult)
        
        scan = state.get("scan_result")
        
        # Format the context for the critic
        human_prompt = f"""
        USER CONTEXT:
        Occasion: {state.get('occasion', 'everyday wear')}
        Style Persona: {state.get('style_persona', 'neutral')}
        Physical attributes: Gender: {state.get('gender', 'unspecified')}, Body Type: {", ".join(state.get('body_type', []))}
        
        OBJECTIVE FACTS ABOUT OUTFIT:
        Garments Detected: {scan.model_dump_json() if scan else 'None detected.'}
        
        Please provide your expert, constructed critique formatted strictly as requested.
        """
        
        # Inject JSON format instructions into the system prompt
        system_content = CRITIC_SYSTEM_PROMPT + "\n\n{format_instructions}"
        instruction_text = parser.get_format_instructions()
        system_msg = SystemMessage(content=system_content.replace("{format_instructions}", instruction_text))
        
        messages = [
            system_msg,
            HumanMessage(content=human_prompt)
        ]
        
        print("Calling NVIDIA NIM Critique Model...")
        # One call, then extract — deliberately not `llm | parser`.
        #
        # JsonOutputParser rejects any preamble, and reasoning models always narrate before
        # answering. Retrying on that failure meant a second call that could come back
        # truncated mid-JSON, discarding a first response that was perfectly good. The raw
        # text is all we need, so ask once and pull the object out of it.
        raw_response = await ainvoke_with_retry(llm, messages, LLM_TIMEOUT_SECONDS)
        raw_text = getattr(raw_response, "content", str(raw_response))

        result_dict = extract_json_object(raw_text)
        if not result_dict:
            raise ValueError(
                f"Could not extract JSON from critique response: {raw_text[-400:]}"
            )

        # Parse into Pydantic model
        result = CritiqueResult(**result_dict)
        print("Critique successful!")

        return {"critique_result": result}

    except asyncio.TimeoutError:
        # Let this propagate so main.py can return a 504 that says what actually happened,
        # rather than the generic "AI returned empty or invalid results".
        print(f"Error in critique_outfit: timed out after {LLM_TIMEOUT_SECONDS}s")
        raise
    except Exception as e:
        # The critique is not optional — without it there is no score and no gap, so there
        # is nothing to show the user. Record why rather than returning a bare {} and
        # letting main.py guess.
        print(f"Error in critique_outfit: {type(e).__name__}: {e}")
        return {"error": f"Critique step failed ({type(e).__name__}): {e}"}
