from typing import TypedDict, Optional, List, Dict, Any
from .models import ScanResult, CritiqueResult

class AgentState(TypedDict):
    """
    The state dictionary that gets passed from node to node in the LangGraph.
    """
    # Inputs
    image_base64: Optional[str]
    text_description: Optional[str]
    occasion: str
    style_persona: str
    
    # User Profile (from Supabase/Clerk context if needed)
    gender: str
    body_type: List[str]
    # Populated once the analyze route looks up the user's saved profile (Tier 2, item 7).
    # Until then it stays empty and the size filter is simply not applied.
    sizes: List[str]
    
    # Phase 5 — Weather context
    latitude: Optional[float]
    longitude: Optional[float]
    weather_context: Optional[Dict[str, Any]]
    
    # Internal AI Pipeline Data
    scan_result: Optional[ScanResult]
    critique_result: Optional[CritiqueResult]

    # Why the pipeline failed, if it did. Without this, a node that swallows an exception
    # and returns a fallback is indistinguishable from one that genuinely succeeded, and
    # every backend failure surfaces to the user as the same generic 500.
    error: Optional[str]
    
    # Phase 4 — Pinecone RAG results
    recommended_products: List[Dict[str, Any]]

