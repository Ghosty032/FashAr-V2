from app.schemas.state import AgentState
from app.services.pinecone_service import query_products

def retrieve_products(state: AgentState) -> dict:
    """
    Node 3: Given the gap_type from the critique, query Pinecone for
    matching products filtered by user dimensions.
    If style_score >= 90, skip retrieval (outfit is already complete).
    Phase 5: Applies weather suppression rules before retrieval.
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

    # ===== Phase 5 — Weather Suppression =====
    weather = state.get("weather_context", {})
    suppressed = weather.get("suppressed_gap_types", [])
    boosted = weather.get("boosted_gap_types", [])
    
    # If the identified gap is suppressed by weather, try to use a boosted gap instead
    if gap in suppressed:
        if boosted:
            print(f"Weather suppressed gap '{gap}', switching to boosted gap '{boosted[0]}'")
            gap = boosted[0]
        else:
            print(f"Weather suppressed gap '{gap}' and no alternatives. Skipping retrieval.")
            return {"recommended_products": []}

    gender = state.get("gender", "unisex")
    body_types = state.get("body_type", [])
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
        
        # Phase 5: Post-filter — remove products whose gap_type is weather-suppressed
        if suppressed:
            before = len(products)
            products = [p for p in products if not all(gt in suppressed for gt in p.get("gap_type", []))]
            after = len(products)
            if before != after:
                print(f"Weather post-filter: removed {before - after} suppressed products")
        
        print(f"Retrieved {len(products)} products for gap '{gap}'")
        return {"recommended_products": products}
    except Exception as e:
        print(f"Error in retrieve_products: {e}")
        return {"recommended_products": []}

