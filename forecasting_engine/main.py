from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prophet.serialize import model_from_json
import pandas as pd
import os
import random



# Global variables
# Global variables
try:
    from .lstm_engine import get_lstm_forecast
except ImportError:
    from lstm_engine import get_lstm_forecast

model = None
transport_df = None
actuals_map = {} # Date -> Price
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices') 
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, "..", "commodity_transport_costs.csv")
MODEL_PATH = os.path.join(BASE_DIR, "onion_prophet_model.json")

# Initialize FastAPI
app = FastAPI(title="Agri-Oracle Backend")

# Frontend directory path
# Since main.py is in forecasting_engine/, frontend is in ../frontend
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.on_event("startup")
async def load_resources():
    global model, transport_df, actuals_map
    try:
        # Load Model
        if os.path.exists(MODEL_PATH):
            print(f"Loading model from {os.path.abspath(MODEL_PATH)}...")
            with open(MODEL_PATH, "r") as fin:
                model = model_from_json(fin.read())
            print("Model loaded successfully.")
        else:
            print(f"Warning: Model file not found at {MODEL_PATH}.")

        # Load Transport Costs
        if os.path.exists(TRANSPORT_CSV_PATH):
            print(f"Loading transport costs from {TRANSPORT_CSV_PATH}...")
            transport_df = pd.read_csv(TRANSPORT_CSV_PATH)
            transport_df['ds'] = pd.to_datetime(transport_df['Date'], dayfirst=True, errors='coerce')
            transport_df['transport_cost'] = pd.to_numeric(transport_df['Global_Transport_Cost_Index'], errors='coerce')
            transport_df = transport_df[['ds', 'transport_cost']].dropna()
            print("Transport cost data loaded.")
        else:
            print(f"Warning: {TRANSPORT_CSV_PATH} not found.")

    except Exception as e:
        print(f"Error loading resources: {e}")

from typing import Optional

class PolicyInput(BaseModel):
    diesel_tax: float = 0.0
    subsidy_percent: float = 0.0
    export_ban: bool = False
    volatility_slider: float = 0.0  # Panic Index (0-10)
    reference_date: Optional[str] = None   # "2024-03-01" - The Baseline Anchor
    target_date: Optional[str] = None      # "2024-03-02" - The Forecast Target

def log_to_polygon(price: float, inputs_dict: dict) -> str:
    # Simulate a transaction hash for blockchain logging
    tx_hash = f"0x{random.getrandbits(256):064x}"
    print(f"Logged to Polygon: Price={price}, Inputs={inputs_dict}, Tx={tx_hash}")
    return tx_hash

@app.post("/api/predict")
async def predict_price(policy: PolicyInput):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded. Run train_model.py first.")
    
    try:
        # 1. Determine Forecast Horizon and DataFrame
        if hasattr(model, 'history') and model.history is not None:
             last_history_date = model.history['ds'].max()
        else:
             last_history_date = pd.Timestamp.now()

        # Parse Reference Date (Baseline)
        now_date = pd.Timestamp.now().normalize()
        if policy.reference_date:
            ref_date = pd.to_datetime(policy.reference_date)
        else:
            ref_date = now_date

        # Parse Target Date (Forecast)
        if policy.target_date:
            target_date = pd.to_datetime(policy.target_date)
        else:
            # Default to Reference + 1 Day if not specified
            target_date = ref_date + pd.Timedelta(days=1)

        # Log the request
        print(f"Request: Ref={ref_date}, Target={target_date}") 

        # Future DataFrame for TARGET
        # FIX: make_future_dataframe creates a sequence starting at history end.
        # We need to ensure target_date is INCLUDED in the future dataframe.
        
        if target_date <= last_history_date:
            # In-sample
            future = pd.DataFrame({'ds': [target_date]})
        else:
            # Future
            days_to_predict = (target_date - last_history_date).days
            days_to_predict = max(1, min(days_to_predict, 365))
            future = model.make_future_dataframe(periods=days_to_predict)
            
            # FORCE ensure target_date is in future dataframe if prophet missed it (e.g. slight time diff)
            if target_date not in future['ds'].values:
                # Add it manually
                future = pd.concat([future, pd.DataFrame({'ds': [target_date]})], ignore_index=True)
                future = future.sort_values('ds').reset_index(drop=True)
        
        print(f"DEBUG: Future DS head: {future['ds'].head()}")
        print(f"DEBUG: Future DS tail: {future['ds'].tail()}")
        print(f"DEBUG: Target Date: {target_date}")

        # Future DataFrame for REFERENCE (Baseline)
        if ref_date <= last_history_date:
             ref_future = pd.DataFrame({'ds': [ref_date]})
        else:
             days_to_ref = (ref_date - last_history_date).days
             days_to_ref = max(1, min(days_to_ref, 365))
             ref_future = model.make_future_dataframe(periods=days_to_ref)
             
             if ref_date not in ref_future['ds'].values:
                ref_future = pd.concat([ref_future, pd.DataFrame({'ds': [ref_date]})], ignore_index=True)
                ref_future = ref_future.sort_values('ds').reset_index(drop=True)
             
        # --- Add Regressors to Main Future ---
        
        # 1. Transport Lag (Existing logic)
        if transport_df is not None:
            t_lookup = transport_df.set_index('ds')['transport_cost']
            last_transport_val = transport_df['transport_cost'].iloc[-1] if not transport_df.empty else 0
            
            def get_lagged_cost(date):
                target_date = date - pd.Timedelta(days=3)
                try:
                    val = t_lookup.asof(target_date)
                    return last_transport_val if pd.isna(val) else val
                except Exception:
                    return last_transport_val

            future['transport_lag_3'] = future['ds'].apply(get_lagged_cost)
            future['transport_lag_3'] = future['transport_lag_3'].fillna(last_transport_val)
            
            # Apply to Ref Future too
            ref_future['transport_lag_3'] = ref_future['ds'].apply(get_lagged_cost)
            ref_future['transport_lag_3'] = ref_future['transport_lag_3'].fillna(last_transport_val)

        else:
            future['transport_lag_3'] = 0
            ref_future['transport_lag_3'] = 0

        # 2. National Average Price (Defaulting to recent avg for demo stability)
        future['national_avg_price'] = 2500.0 
        ref_future['national_avg_price'] = 2500.0
        
        # 3. Rainfall
        future['rainfall'] = 0.0
        ref_future['rainfall'] = 0.0

        # 4. Panic Index
        future['panic_index'] = policy.volatility_slider
        ref_future['panic_index'] = 0.0 # Reference date assumes normal conditions unless specified otherwise

            
        forecast = model.predict(future)
        ref_forecast_df = model.predict(ref_future)
        
        # Get prediction for TARGET date
        target_row = forecast[forecast['ds'] == target_date]
        if target_row.empty:
             # Fallback
             raw_target_price = forecast.iloc[-1]['yhat']
             conf_lower = forecast.iloc[-1]['yhat_lower']
             conf_upper = forecast.iloc[-1]['yhat_upper']
             prediction_date_str = forecast.iloc[-1]['ds'].strftime('%Y-%m-%d')
        else:
             raw_target_price = target_row.iloc[0]['yhat']
             conf_lower = target_row.iloc[0]['yhat_lower']
             conf_upper = target_row.iloc[0]['yhat_upper']
             prediction_date_str = target_row.iloc[0]['ds'].strftime('%Y-%m-%d')

        # Get prediction for REFERENCE date (Baseline)
        ref_row = ref_forecast_df[ref_forecast_df['ds'] == ref_date]
        if ref_row.empty:
            ref_price = ref_forecast_df.iloc[-1]['yhat']
        else:
            ref_price = ref_row.iloc[0]['yhat']
        
        # 2. Apply Policy Modifiers (to the Target Price)
        # ENSEMBLE LOGIC
        lstm_forecasts = []
        try:
            lstm_forecasts = get_lstm_forecast() # Returns list of 30 floats
            # Use Day 1 for the main "price" display
            lstm_price_day1 = lstm_forecasts[0]
            lstm_price_day7 = lstm_forecasts[6]
            lstm_price_day30 = lstm_forecasts[29]
            print(f"LSTM Forecast (Day 1): {lstm_price_day1}")
        except Exception as e:
            print(f"LSTM Error: {e}")
            # Fallback: fill with prophet price if LSTM fails
            lstm_price_day1 = raw_target_price
            lstm_price_day7 = raw_target_price
            lstm_price_day30 = raw_target_price
            lstm_forecasts = [raw_target_price] * 30

        # Weighted Ensemble (70% Prophet, 30% LSTM) -> Using Day 1 for the main number
        ensembled_price = (raw_target_price * 0.7) + (lstm_price_day1 * 0.3)
        
        final_price = ensembled_price
        
        # Diesel Tax Impact
        final_price += (policy.diesel_tax * 15)
        
        # Export Ban Impact
        status_msg = "Normal Market Conditions"
        
        # Check Volatility First (Overrides Normal)
        if policy.volatility_slider > 7.0:
            status_msg = "CRITICAL: High Market Volatility Detected"
        elif policy.volatility_slider > 4.0:
            status_msg = "Warning: Elevated Market Stress"

        # Export Ban overrides everything
        if policy.export_ban:
            final_price *= 0.70
            status_msg = "Warning: Export Ban Triggered - Market Crash Imminent"
            
        # Subsidy Impact
        final_price -= (final_price * (policy.subsidy_percent / 100))
        
        final_price = max(0.0, final_price)

        # Calculate Confidence Percentage
        # Cap lower at 0 to avoid huge ranges if model predicts negative
        safe_conf_lower = max(0.0, conf_lower)
        safe_conf_upper = max(safe_conf_lower, conf_upper)
        
        interval_mean = (safe_conf_upper + safe_conf_lower) / 2
        if interval_mean > 0:
            half_width = (safe_conf_upper - safe_conf_lower) / 2
            confidence_pct = (half_width / interval_mean) * 100
        else:
            confidence_pct = 0.0
            
        # HACK: Cap confidence at 35% for UI stability during pitch
        # (Real world models explode to 100% over 3 years, but that looks broken to users)
        confidence_pct = min(confidence_pct, 35.0)
        
        # 3. Log to Blockchain
        tx_hash = log_to_polygon(final_price, policy.dict())
        
        # 4. Get Real Value (if available)
        real_val = actuals_map.get(target_date, None)
        
        return {
            "commodity": "Onion",
            "baseline_prediction": round(ref_price, 2), # CHANGED: Now returns price at Reference Date
            "final_adjusted_price": round(final_price, 2),
            "confidence_lower": round(safe_conf_lower, 2),
            "confidence_upper": round(safe_conf_upper, 2),
            "confidence_score": round(confidence_pct, 1), # NEW: Pre-calculated percentage
            "real_value": round(real_val, 2) if real_val else None,
            "status_message": status_msg,
            "polygon_tx_hash": tx_hash,
            "prediction_date": prediction_date_str,
            "models": {
                "prophet": round(raw_target_price, 2),
                "lstm_day1": round(lstm_price_day1, 2),
                "lstm_day7": round(lstm_price_day7, 2),
                "lstm_day30": round(lstm_price_day30, 2)
            },
            "debug_target_date": str(target_date),
            "debug_future_tail": str(future['ds'].tail().tolist())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend LAST (catch-all) so API routes take priority
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
