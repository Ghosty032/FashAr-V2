from app.schemas.state import AgentState
from app.services.pinecone_service import query_products

def retrieve_products(state: AgentState) -> AgentState:
    """
    Node 3: Given the gap_type from the critique, query Pinecone for
    matching products filtered by user dimensions.
    If style_score >= 90, skip retrieval (outfit is already complete).
    """
    print("--- [NODE] Retrieving Completer Products ---")

    critique = state.get("critique_result")

    # High-score bypass (PRD §5.3.3)
    if critique and critique.style_score >= 90:
        print("Style score >= 90. Skipping product retrieval — outfit is complete.")
        return {"recommended_products": []}

    gap = critique.gap_type if critique else "structure"
    if gap == "none":
        print("No gap identified. Skipping retrieval.")
        return {"recommended_products": []}

    gender = state.get("gender", "unisex")
    body_types = state.get("body_type", [])
    # Derive sizes — for now pass empty to get all; the frontend can refine later
    sizes = []

    # Try to get color context from the scan
    scan = state.get("scan_result")
    color_family = []
    if scan and scan.color_palette:
        color_family = [c.name for c in scan.color_palette[:3]]

    try:
        products = query_products(
            gap_type=gap,
            gender=gender,
            body_types=body_types,
            sizes=sizes,
            color_family=color_family,
        )
        print(f"Retrieved {len(products)} products for gap '{gap}'")
        return {"recommended_products": products}
    except Exception as e:
        print(f"Error in retrieve_products: {e}")
        return {"recommended_products": []}
