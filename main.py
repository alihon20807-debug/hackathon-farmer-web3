from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prophet.serialize import model_from_json
import pandas as pd
import json
import os
import random
import datetime

# Initialize FastAPI
app = FastAPI(title="Agri-Oracle Backend")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variable
model = None

# Load model on startup
@app.on_event("startup")
async def load_model():
    global model
    try:
        if os.path.exists("onion_prophet_model.json"):
            with open("onion_prophet_model.json", "r") as fin:
                model = model_from_json(json.load(fin))
            print("Model loaded successfully.")
        else:
            print("Warning: Model file not found. Please run train_model.py first.")
    except Exception as e:
        print(f"Error loading model: {e}")

# Skip Root UI, only API endpoints

# Pydantic Schema
class PolicyInput(BaseModel):
    diesel_tax: float = 0.0
    subsidy_percent: float = 0.0
    export_ban: bool = False

# Mock Blockchain Logger
def log_to_polygon(price: float, inputs_dict: dict) -> str:
    # Simulate a transaction hash
    # In production, this would use web3.py to call the smart contract
    tx_hash = f"0x{random.getrandbits(256):064x}"
    print(f"Logged to Polygon: Price={price}, Inputs={inputs_dict}, Tx={tx_hash}")
    return tx_hash

# Prediction Endpoint
@app.post("/api/predict")
async def predict_price(policy: PolicyInput):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded. Run train_model.py first.")
    
    try:
        # 1. Forecast next 14 days
        future = model.make_future_dataframe(periods=14)
        forecast = model.predict(future)
        
        # Extract 14th day prediction (yhat)
        # The last row of forecast corresponds to the last date in future
        # future has (history + 14) rows.
        baseline_price = forecast.iloc[-1]['yhat']
        
        # 2. Apply Policy Modifiers
        final_price = baseline_price
        
        # Diesel Tax Impact
        diesel_impact = policy.diesel_tax * 15
        final_price += diesel_impact
        
        # Export Ban Impact (Market Crash)
        status_msg = "Normal Market Conditions"
        if policy.export_ban:
            final_price *= 0.70
            status_msg = "Warning: Export Ban Triggered - Market Crash Imminent"
            
        # Subsidy Impact (Price Reduction)
        subsidy_amount = final_price * (policy.subsidy_percent / 100)
        final_price -= subsidy_amount
        
        # Ensure price is logical (not negative)
        final_price = max(0.0, final_price)
        
        # 3. Log to Blockchain
        tx_hash = log_to_polygon(final_price, policy.dict())
        
        return {
            "commodity": "Onion",
            "baseline_prediction": round(baseline_price, 2),
            "final_adjusted_price": round(final_price, 2),
            "status_message": status_msg,
            "polygon_tx_hash": tx_hash,
            "prediction_date": forecast.iloc[-1]['ds'].strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
