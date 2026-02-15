import requests
import json
import datetime
import os

# Tomorrow's date
tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

try:
    response = requests.post("http://localhost:8000/api/predict", json={
        "diesel_tax": 0,
        "subsidy_percent": 0,
        "export_ban": False,
        "volatility_slider": 0,
        "prediction_date": tomorrow
    })
    
    print(f"Testing Prediction for: {tomorrow}")
    with open("debug_output_future.json", "w") as f:
        json.dump(response.json(), f, indent=2)
    print("Debug output written to debug_output_future.json")

except Exception as e:
    print(f"Error: {e}")
