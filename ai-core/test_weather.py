"""Quick test: hit /analyze with lat/lon to verify Phase 5 weather integration."""
import requests

url = "http://127.0.0.1:8001/analyze"
data = {
    "text_description": "I am wearing a blue jacket and blue jeans with white sneakers.",
    "occasion_tier_1": "Casual",
    "style_persona": "Minimalist",
    "gender": "mens",
    "body_type": "[]",
    "latitude": "25.2",   # Dubai (hot city ~35°C)
    "longitude": "55.27",
}

print("Sending test request with Dubai coordinates...")
response = requests.post(url, data=data, timeout=120)
print(f"Status: {response.status_code}")
if response.ok:
    result = response.json()
    print(f"Weather: {result.get('weather')}")
    print(f"Gap: {result.get('gap_type')}")
    print(f"Products: {len(result.get('recommended_products', []))}")
else:
    print(f"Error: {response.text}")
