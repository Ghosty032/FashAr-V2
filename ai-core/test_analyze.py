import requests

url = "http://localhost:8001/analyze"

data = {
    "text_description": "I am wearing a blue jacket and blue jeans with white sneakers.",
    "occasion_tier_1": "Casual",
    "occasion_tier_2": "Walking",
    "style_persona": "Minimalist",
    "gender": "mens",
    "body_type": '["athletic"]'
}

response = requests.post(url, data=data)
print("Status:", response.status_code)
try:
    print(response.json())
except Exception as e:
    print(response.text)
