
import requests
import json

url = "http://localhost:8000/api/predict"

scenarios = [
    {
        "name": "Tomorrow (Default)",
        "payload": {
            "export_ban": False,
            "volatility_slider": 5.0,
            "reference_date": "tomorrow" 
        }
    },
    {
        "name": "Next Week from Now",
        "payload": {
            "reference_date": "next_week",
            "volatility_slider": 0
        }
    },
    {
        "name": "Next Month from Now",
        "payload": {
            "reference_date": "next_month",
             "volatility_slider": 0
        }
    },
    {
        "name": "Specific Date (2025-01-01)",
        "payload": {
            "reference_date": "2025-01-01",
             "volatility_slider": 0
        }
    },
    {
         "name": "Reference Date Test (Ref: 2023-06-01, Target: Next Week)",
         "payload": {
             "reference_date": "2023-06-01", 
             "volatility_slider": 0
         }
    }
]

for s in scenarios:
    print(f"\n--- Testing Scenario: {s['name']} ---")
    try:
        response = requests.post(url, json=s['payload'])
        if response.status_code == 200:
            data = response.json()
            print(f"Success. Predicted Date: {data.get('prediction_date')}")
            print(f"Price: {data.get('final_adjusted_price')}")
            if data.get('real_value'):
                 print(f"Real Value: {data.get('real_value')}")
        else:
            print(f"Failed. Status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")
