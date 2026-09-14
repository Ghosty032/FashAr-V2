"""
FASHR V2 — Weather Service (Phase 5)
Fetches live weather from OpenWeatherMap and applies PRD §5.5 suppression rules.
"""

import httpx

# All configuration comes from app.config — see the note in pinecone_service.py. The
# load_dotenv call this replaced pointed at `ai-core/frontend/.env.local`, which does not
# exist; it only worked because app.config had already populated os.environ.
from app.config import OPENWEATHER_KEY
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


async def get_weather(lat: float, lon: float) -> dict:
    """
    Fetch current weather for the given coordinates.
    Returns a structured dict with temp, condition, suppression rules, etc.
    """
    if not OPENWEATHER_KEY:
        print("[WEATHER] No OPENWEATHER_KEY found, skipping weather.")
        return {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OPENWEATHER_URL, params={
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_KEY,
                "units": "metric",  # Celsius
            })
            resp.raise_for_status()
            data = resp.json()

        temp_c = data["main"]["temp"]
        # Weather condition group (Rain, Snow, Clear, Clouds, etc.)
        condition = data["weather"][0]["main"].lower() if data.get("weather") else "clear"
        description = data["weather"][0]["description"] if data.get("weather") else ""
        city = data.get("name", "Unknown")

        # ===== PRD §5.5 — Suppression & Boost Rules =====
        suppressed_gap_types = []
        boosted_gap_types = []
        weather_note = ""

        if temp_c > 28:
            # Hot weather: suppress heavy layers
            suppressed_gap_types = ["structure"]
            weather_note = f"It's {temp_c:.0f}°C in {city} — heavy layers like jackets and coats filtered out."
        elif temp_c < 10:
            # Cold weather: boost outerwear, deprioritize light clothing
            boosted_gap_types = ["structure", "texture"]
            weather_note = f"It's {temp_c:.0f}°C in {city} — outerwear and warm layers prioritized."

        if condition in ("rain", "drizzle", "thunderstorm"):
            boosted_gap_types.append("footwear")
            weather_note += f" Rain detected — waterproof footwear elevated."

        result = {
            "temp_c": round(temp_c, 1),
            "condition": condition,
            "description": description,
            "city": city,
            "suppressed_gap_types": suppressed_gap_types,
            "boosted_gap_types": boosted_gap_types,
            "weather_note": weather_note,
        }

        print(f"[WEATHER] {city}: {temp_c:.1f}°C, {condition} — suppressions={suppressed_gap_types}, boosts={boosted_gap_types}")
        return result

    except Exception as e:
        print(f"[WEATHER] Error fetching weather: {e}")
        return {}
