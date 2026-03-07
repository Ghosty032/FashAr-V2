from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from app.schemas.state import AgentState
from app.schemas.models import CritiqueResult
from app.prompts.prompts import CRITIC_SYSTEM_PROMPT
import app.config  # ensures API key is loaded

def critique_outfit(state: AgentState) -> AgentState:
    """
    Node 2: Takes the factual scan and the user context (occasion, avatar) 
    and returns a brutal but constructive critique + score.
    """
    print("--- [NODE] Critiquing Outfit ---")
    
    # Use Qwen 3.5 122B / Llama 3 for deep reasoning
    llm = ChatNVIDIA(model="meta/llama-3.1-405b-instruct", temperature=0.6)
    structured_llm = llm.with_structured_output(CritiqueResult)
    
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
    
    try:
        # Note: If structured_output fails, langchain handles the retry, but NIM might require specific models.
        result = structured_llm.invoke([
            SystemMessage(content=CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt)
        ])
        
        return {"critique_result": result}
    except Exception as e:
        print(f"Error in critique_outfit: {e}")
        # Fallback wrapper
        return {}
