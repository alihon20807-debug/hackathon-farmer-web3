import requests
import json

url = "http://localhost:8000/api/predict"

# Scenario 1: Basic (Ref = Target default)
payload1 = {
    "reference_date": "2023-06-15",
    "diesel_tax": 0,
    "subsidy_percent": 0,
    "export_ban": False,
    "volatility_slider": 0
}

# Scenario 2: With Target Date (+1 Day)
payload2 = {
    "reference_date": "2023-06-15",
    "target_date": "2023-06-16",
    "diesel_tax": 0,
    "subsidy_percent": 0,
    "export_ban": False,
    "volatility_slider": 0
}

try:
    print("--- Test 1: Implicit Target ---")
    r1 = requests.post(url, json=payload1)
    if r1.status_code == 200:
        d1 = r1.json()
        print(f"Ref Date: 2023-06-15")
        print(f"Predicted Date: {d1['prediction_date']}")
        print(f"Baseline Price: {d1['baseline_prediction']}")
        print(f"Final Price: {d1['final_adjusted_price']}")
    else:
        print(f"Error: {r1.text}")

    print("\n--- Test 2: Explicit Target (2023-06-16) ---")
    r2 = requests.post(url, json=payload2)
    if r2.status_code == 200:
        d2 = r2.json()
        print(f"Ref Date: 2023-06-15")
        print(f"Target Date: 2023-06-16")
        print(f"Predicted Date: {d2['prediction_date']}")
        print(f"Baseline Price: {d2['baseline_prediction']}")
        print(f"Final Price: {d2['final_adjusted_price']}")
        
        # Validation
        if d2['prediction_date'] == "2023-06-16":
            print("SUCCESS: Target Date update working on backend.")
        else:
            print("FAILURE: Backend returned wrong date.")
            
        if d1['baseline_prediction'] == d2['baseline_prediction']:
             print("SUCCESS: Baseline remained constant.")
        else:
             print(f"FAILURE: Baseline changed! {d1['baseline_prediction']} vs {d2['baseline_prediction']}")

    else:
        print(f"Error: {r2.text}")

except Exception as e:
    print(f"Exception: {e}")
