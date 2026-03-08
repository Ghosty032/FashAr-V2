import json
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import base64

from app.graph import app as fashr_graph
from app.schemas.models import FinalAnalysis, DetectedItem, ColorPalette, ScoreBreakdown, RecommendedProduct, WeatherInfo
from app.services.weather_service import get_weather

# =========================================================================================
# PHASE 3+5 - FASTAPI ENTRY POINT
# Exposes the /analyze endpoint to the NextJS frontend
# =========================================================================================

app = FastAPI(title="FASHR AI Core", version="0.1.0")

# Allow requests from Next.js (port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "AI Core running with NVIDIA NIM Llama 3.2 Vision"}

@app.post("/analyze", response_model=FinalAnalysis)
async def analyze_outfit(
    image: Optional[UploadFile] = File(None),
    text_description: Optional[str] = Form(None),
    occasion_tier_1: str = Form(...),
    occasion_tier_2: Optional[str] = Form(None),
    style_persona: str = Form(...),
    gender: str = Form("unisex"),
    body_type: str = Form("[]"),
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
        
    try:
        parsed_body_type = json.loads(body_type)
    except:
        parsed_body_type = []

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
        "latitude": latitude,
        "longitude": longitude,
        "weather_context": weather_context,
    }
    
    print("Starting Fashr LangGraph Workflow...")
    try:
        result = await fashr_graph.ainvoke(inputs) 
    except Exception as e:
        print(f"Graph execution failed: {e}")
        raise HTTPException(status_code=500, detail="The AI execution pipeline failed.")
        
    critique = result.get("critique_result")
    scan = result.get("scan_result")
    
    if not critique or not scan:
        raise HTTPException(status_code=500, detail="AI returned empty or invalid results. Check NIM API limits or endpoints.")

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

