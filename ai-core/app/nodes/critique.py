from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from app.schemas.state import AgentState
from app.schemas.models import CritiqueResult
from app.prompts.prompts import CRITIC_SYSTEM_PROMPT
import app.config  # ensures API key is loaded

async def critique_outfit(state: AgentState) -> dict:
    """
    Node 2: Takes the factual scan and the user context (occasion, avatar) 
    and returns a brutal but constructive critique + score.
    """
    print("--- [NODE] Critiquing Outfit ---")
    
    try:
        # Use Llama 3.1 405B for deep reasoning
        llm = ChatNVIDIA(model="meta/llama-3.1-405b-instruct", temperature=0.6)
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
        result_dict = await (llm | parser).ainvoke(messages)
        
        # Parse into Pydantic model
        result = CritiqueResult(**result_dict)
        print("Critique successful!")
        
        return {"critique_result": result}
        
    except Exception as e:
        print(f"Error in critique_outfit: {e}")
        # Try to return fallback, though error propagation is sometimes better for debugging
        return {}
