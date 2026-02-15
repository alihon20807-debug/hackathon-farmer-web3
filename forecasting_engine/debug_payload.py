import requests
import json

url = "http://localhost:8001/api/predict"

# Payload mirroring what script.js sends
payload = {
    "diesel_tax": 0,
    "subsidy_percent": 0,
    "export_ban": False,
    "volatility_slider": 0,
    "reference_date": "2023-06-15",
    "target_date": None,
    "volatility_slider": 8.0 # Should trigger CRITICAL message
}

try:
    print(f"Sending payload: {payload}")
    r = requests.post(url, json=payload)
    if r.status_code == 200:
        d = r.json()
        print(f"STATUS MESSAGE: {d['status_message']}")
    else:
        print(f"ERROR: {r.status_code}")
        print(r.text)

except Exception as e:
    print(e)
