import json
import asyncio
from fastapi import FastAPI, UploadFile, Form, File, HTTPException, Depends
from typing import Optional
import base64

from app.config import ANALYSIS_TIMEOUT_SECONDS
from app.graph import app as fashr_graph
from app.deps import enforce_rate_limit
from app.schemas.models import FinalAnalysis, DetectedItem, ColorPalette, ScoreBreakdown, RecommendedProduct, WeatherInfo
from app.services.weather_service import get_weather

# =========================================================================================
# PHASE 3+5 - FASTAPI ENTRY POINT
# Exposes the /analyze endpoint to the NextJS frontend
# =========================================================================================

app = FastAPI(title="FASHR AI Core", version="0.1.0")

# No CORS middleware on purpose. Nothing in a browser talks to this service directly —
# the Next.js route at /api/analyze proxies every call server-side, and server-to-server
# requests are not subject to CORS. Adding it back would only weaken the gateway check.

@app.get("/")
def health_check():
    """Unauthenticated so Render's health check can reach it."""
    return {"status": "AI Core running with NVIDIA NIM Llama 3.2 Vision"}

@app.post("/analyze", response_model=FinalAnalysis, dependencies=[Depends(enforce_rate_limit)])
async def analyze_outfit(
    image: Optional[UploadFile] = File(None),
    text_description: Optional[str] = Form(None),
    occasion_tier_1: str = Form(...),
    occasion_tier_2: Optional[str] = Form(None),
    style_persona: str = Form(...),
    gender: str = Form("unisex"),
    body_type: str = Form("[]"),
    # JSON-encoded arrays, attached by the Next.js gateway from the user's saved profile.
    sizes: str = Form("[]"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """
    Main endpoint for analyzing an outfit via LangGraph. 
    Accepts Multipart Form Data because it might contain a File object.
    """
    print(f"\n--- INCOMING /analyze REQUEST ---")
    print(f"text_description: {text_description}")
    print(f"occasion: {occasion_tier_1}")
    print(f"coordinates: ({latitude}, {longitude})")
    
    # 1. Validate Input
    if not image and not text_description:
        raise HTTPException(status_code=400, detail="Must provide either an image array buffer or text_description.")

    # 2. Process Image to Base64 (if exists)
    image_base64 = None
    if image:
        contents = await image.read()
        b64_str = base64.b64encode(contents).decode("utf-8")
        mime_type = image.content_type or "image/jpeg"
        image_base64 = f"data:{mime_type};base64,{b64_str}"

    # 3. Format Occasion & Body Type arrays
    full_occasion = occasion_tier_1
    if occasion_tier_2:
        full_occasion += f" - {occasion_tier_2}"
        
    def _parse_str_list(raw: str, field: str) -> list[str]:
        """Tolerate a malformed profile field rather than failing the whole analysis."""
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            print(f"Could not parse {field}={raw!r}; treating as empty.")
            return []
        if not isinstance(parsed, list):
            return []
        return [v for v in parsed if isinstance(v, str)]

    parsed_body_type = _parse_str_list(body_type, "body_type")
    parsed_sizes = _parse_str_list(sizes, "sizes")

    # 4. Phase 5 — Fetch weather data if coordinates provided
    weather_context = {}
    if latitude is not None and longitude is not None:
        weather_context = await get_weather(latitude, longitude)

    # 5. Invoke the LangGraph Pipeline
    inputs = {
        "text_description": text_description,
        "image_base64": image_base64,
        "occasion": full_occasion,
        "style_persona": style_persona,
        "gender": gender,
        "body_type": parsed_body_type,
        "sizes": parsed_sizes,
        "latitude": latitude,
        "longitude": longitude,
        "weather_context": weather_context,
    }
    
    print("Starting Fashr LangGraph Workflow...")
    try:
        result = await asyncio.wait_for(
            fashr_graph.ainvoke(inputs), timeout=ANALYSIS_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        print(f"Graph execution timed out after {ANALYSIS_TIMEOUT_SECONDS}s")
        raise HTTPException(
            status_code=504,
            detail="The AI pipeline took too long to respond. Please try again.",
        )
    except Exception as e:
        print(f"Graph execution failed: {e}")
        raise HTTPException(status_code=500, detail="The AI execution pipeline failed.")
        
    critique = result.get("critique_result")
    scan = result.get("scan_result")
    pipeline_error = result.get("error")

    if not critique or not scan:
        # Prefer the reason a node actually recorded over a guess about NIM limits.
        detail = pipeline_error or (
            "AI returned empty or invalid results. Check NIM API limits or endpoints."
        )
        print(f"Analysis incomplete: {detail}")
        raise HTTPException(status_code=502, detail=detail)

    # The scan can fail softly (empty result) while the critique still succeeds. Say so
    # rather than presenting a score derived from no detected garments as if it were solid.
    if pipeline_error:
        print(f"Analysis completed with a degraded step: {pipeline_error}")

    # 6. Build the recommended products list from RAG results
    raw_products = result.get("recommended_products", [])
    products = [RecommendedProduct(**p) for p in raw_products] if raw_products else []

    # 7. Build weather info for the frontend
    weather_info = None
    if weather_context:
        weather_info = WeatherInfo(
            temp_c=weather_context.get("temp_c", 0),
            condition=weather_context.get("condition", "unknown"),
            description=weather_context.get("description", ""),
            city=weather_context.get("city", "Unknown"),
            weather_note=weather_context.get("weather_note", ""),
        )

    # 8. Assemble the final response
    final_output = FinalAnalysis(
        detected_items=scan.detected_items,
        color_palette=scan.color_palette,
        style_score=critique.style_score,
        score_breakdown=critique.score_breakdown,
        narrative_critique=critique.narrative_critique,
        gap_type=critique.gap_type,
        recommended_products=products,
        weather=weather_info,
    )

    return final_output

