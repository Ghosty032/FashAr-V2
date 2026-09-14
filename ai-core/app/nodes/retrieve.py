import asyncio

from app.schemas.state import AgentState
from app.services.pinecone_service import query_products


def _build_fallback_query(gap: str, scan) -> str:
    """
    Used when the critic gave us no `gap_query` (older cached results, or a model that
    ignored the field). Still prose rather than filter-speak, since that is what the catalog
    descriptions are embedded as.
    """
    colors = ""
    if scan and scan.color_palette:
        colors = " in " + " or ".join(c.name for c in scan.color_palette[:2])

    templates = {
        "structure": f"a tailored structured jacket or blazer{colors}",
        "footwear": f"well-made shoes or boots{colors}",
        "texture": f"a textured knit or suede layer{colors}",
        "accessory": f"a refined accessory such as a belt, bag or scarf{colors}",
        "color": f"a bright accent piece to lift the palette{colors}",
    }
    return templates.get(gap, f"a versatile completer piece{colors}")


async def retrieve_products(state: AgentState) -> dict:
    """
    Node 3: Given the gap identified by the critique, search the catalog for products that
    fill it. Skips retrieval when the outfit is already complete.

    Async because the Pinecone SDK call is blocking — running it inline on the event loop
    would stall every other in-flight request.
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
    weather = state.get("weather_context") or {}
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

    scan = state.get("scan_result")

    # The critic writes this as a product-style phrase; fall back to a generated one if the
    # field is missing or the gap was swapped out by the weather rules above.
    gap_query = getattr(critique, "gap_query", "") if critique else ""
    if not gap_query or (critique and gap != critique.gap_type):
        gap_query = _build_fallback_query(gap, scan)
    print(f"Searching catalog for: {gap_query!r}")

    try:
        products = await asyncio.to_thread(
            query_products,
            gap_query=gap_query,
            gap_type=gap,
            gender=state.get("gender", "unisex"),
            body_types=state.get("body_type", []),
            sizes=state.get("sizes", []),
        )

        # Phase 5: drop products that only fill weather-suppressed gaps. The empty-list
        # guard matters: all([]) is True, so without it a product carrying no gap_type at
        # all would be discarded here.
        if suppressed:
            before = len(products)
            products = [
                p for p in products
                if not p.get("gap_type") or not all(gt in suppressed for gt in p["gap_type"])
            ]
            if before != len(products):
                print(f"Weather post-filter: removed {before - len(products)} suppressed products")

        print(f"Retrieved {len(products)} products for gap '{gap}'")
        return {"recommended_products": products}
    except Exception as e:
        print(f"Error in retrieve_products: {e}")
        return {"recommended_products": []}
