import requests
import json

url = "http://localhost:8001/api/predict"

# Scenario: Explicit Target Date (Ref + 7 Days)
# Ref: 2023-06-15
# Target: 2023-06-22
payload = {
    "reference_date": "2023-06-15",
    "target_date": "2023-06-22",
    "diesel_tax": 0,
    "subsidy_percent": 0,
    "export_ban": False,
    "volatility_slider": 0
}

try:
    print("--- Test: Explicit Target Date (2023-06-22) ---")
    r = requests.post(url, json=payload)
    if r.status_code == 200:
        d = r.json()
        print(f"Ref Date: {payload['reference_date']}")
        print(f"Target Date: {payload['target_date']}")
        print(f"Backend Returned Date: {d['prediction_date']}")
        
        if d['prediction_date'] == "2023-06-22":
            print("SUCCESS: Backend correctly handled target date.")
        else:
            print(f"FAILURE: Backend returned {d['prediction_date']} instead of 2023-06-22.")
            print(f"DEBUG TARGET: {d.get('debug_target_date')}")
            print(f"DEBUG FUTURE: {d.get('debug_future_tail')}")

    else:
        print(f"Error: {r.status_code} - {r.text}")

except Exception as e:
    print(f"Exception: {e}")
