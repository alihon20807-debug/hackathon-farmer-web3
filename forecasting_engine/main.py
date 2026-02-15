from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prophet.serialize import model_from_json
import pandas as pd
import os
import random
import traceback
from typing import Optional

# Global variables
try:
    from .lstm_engine import get_lstm_forecast, get_lstm_direction_signal
except ImportError:
    from lstm_engine import get_lstm_forecast, get_lstm_direction_signal

model = None
transport_df = None
ndvi_df = None  # NDVI satellite data
actuals_map = {} # Date -> Price
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices') 
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, "..", "commodity_transport_costs.csv")
NDVI_CSV_PATH = os.path.join(BASE_DIR, "ndvi_weekly_nashik.csv")
MODEL_PATH = os.path.join(BASE_DIR, "onion_prophet_model.json")

# Initialize FastAPI
app = FastAPI(title="Agri-Oracle Backend")

# Frontend directory path
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
    global model, transport_df, ndvi_df, actuals_map
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

        # Load NDVI satellite data
        if os.path.exists(NDVI_CSV_PATH):
            print(f"Loading NDVI data from {NDVI_CSV_PATH}...")
            ndvi_df = pd.read_csv(NDVI_CSV_PATH)
            ndvi_df['ds'] = pd.to_datetime(ndvi_df['ds'])
            ndvi_df = ndvi_df.sort_values('ds')
            print(f"NDVI data loaded: {len(ndvi_df)} weekly entries.")
        else:
            print(f"Warning: {NDVI_CSV_PATH} not found. NDVI features will be zero.")

    except Exception as e:
        print(f"Error loading resources: {e}")

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

            future['transport_lag_3'] = future['ds'].apply(get_lagged_cost).fillna(last_transport_val)
            ref_future['transport_lag_3'] = ref_future['ds'].apply(get_lagged_cost).fillna(last_transport_val)
        else:
            future['transport_lag_3'] = 0
            ref_future['transport_lag_3'] = 0

        # 2. National Average Price (Dynamic default)
        last_price = 5000.0 # Fallback
        if hasattr(model, 'history') and model.history is not None:
             last_price = model.history['y'].iloc[-1]
             
        future['national_avg_price'] = last_price
        ref_future['national_avg_price'] = last_price
        
        # 3. Rainfall
        future['rainfall'] = 0.0
        ref_future['rainfall'] = 0.0

        # 4. Panic Index
        future['panic_index'] = policy.volatility_slider
        ref_future['panic_index'] = 0.0

        # 5. NDVI Satellite Data
        if ndvi_df is not None and not ndvi_df.empty:
            ndvi_lookup = ndvi_df.set_index('ds')
            last_ndvi_mean = ndvi_df['ndvi_mean'].iloc[-1]
            
            def get_ndvi_val(date, col, default):
                try:
                    val = ndvi_lookup[col].asof(date)
                    return default if pd.isna(val) else float(val)
                except Exception:
                    return default

            future['ndvi_mean'] = future['ds'].apply(lambda d: get_ndvi_val(d, 'ndvi_mean', last_ndvi_mean))
            ref_future['ndvi_mean'] = ref_future['ds'].apply(lambda d: get_ndvi_val(d, 'ndvi_mean', last_ndvi_mean))
        else:
            future['ndvi_mean'] = 0.0
            ref_future['ndvi_mean'] = 0.0

        # Generate 30-day forecast series for the chart
        forecast_horizon = 30
        future_trend = model.make_future_dataframe(periods=forecast_horizon)
        
        # Add regressors to future_trend
        if transport_df is not None:
             future_trend['transport_lag_3'] = future_trend['ds'].apply(get_lagged_cost).fillna(last_transport_val)
        else:
             future_trend['transport_lag_3'] = 0

        future_trend['national_avg_price'] = last_price
        future_trend['rainfall'] = 0.0
        future_trend['panic_index'] = policy.volatility_slider
        
        if ndvi_df is not None and not ndvi_df.empty:
            future_trend['ndvi_mean'] = future_trend['ds'].apply(lambda d: get_ndvi_val(d, 'ndvi_mean', last_ndvi_mean))
        else:
            future_trend['ndvi_mean'] = 0.0

        forecast_trend_df = model.predict(future_trend)
        
        # Filter for "future" only (starting from ref_date)
        # We want the chart to start from the reference date (Day 0) and go 30 days out
        mask = forecast_trend_df['ds'] >= ref_date
        trend_segment = forecast_trend_df.loc[mask].head(31) # Day 0 + 30 days
        
        # Prepare the series data
        # Prepare the series data
        forecast_series = []
        for _, row in trend_segment.iterrows():
            # Base price from model (in kg)
            base_kg = row['yhat'] / 100.0
            
            # Apply Policy Adjustments to Series
            # 1. Diesel Tax Impact (Additive)
            diesel_impact = (policy.diesel_tax * 15) / 100.0
            daily_price = base_kg + diesel_impact
            
            # 2. Export Ban (Multiplicative)
            if policy.export_ban:
                daily_price *= 0.70
                
            # 3. Subsidy (Percentage Reduction)
            subsidy_amt = daily_price * (policy.subsidy_percent / 100.0)
            daily_price -= subsidy_amt
            
            # Clamp to 0
            daily_price = max(0.0, round(daily_price, 2))
            
            # For bounds, we scale them similarly or just center them around the new price?
            # Ideally applying the same transform. Let's approximate by applying the delta.
            # Or better: Apply the same logic to lower/upper.
            
            def apply_policy(val_quintal):
                v = val_quintal / 100.0
                v += diesel_impact
                if policy.export_ban: v *= 0.70
                v -= (v * (policy.subsidy_percent / 100.0))
                return max(0.0, round(v, 2))

            lower_kg = apply_policy(row['yhat_lower'])
            upper_kg = apply_policy(row['yhat_upper'])

            forecast_series.append({
                "date": row['ds'].strftime('%Y-%m-%d'),
                "price": daily_price,
                "lower": lower_kg,
                "upper": upper_kg
            })

        forecast = model.predict(future)
        ref_forecast_df = model.predict(ref_future)
        
        # Get prediction for TARGET date
        target_row = forecast[forecast['ds'] == target_date]
        if target_row.empty:
             raw_target_price = forecast.iloc[-1]['yhat']
             conf_lower = forecast.iloc[-1]['yhat_lower']
             conf_upper = forecast.iloc[-1]['yhat_upper']
             prediction_date_str = forecast.iloc[-1]['ds'].strftime('%Y-%m-%d')
             decomp_row = forecast.iloc[-1]
        else:
             raw_target_price = target_row.iloc[0]['yhat']
             conf_lower = target_row.iloc[0]['yhat_lower']
             conf_upper = target_row.iloc[0]['yhat_upper']
             prediction_date_str = target_row.iloc[0]['ds'].strftime('%Y-%m-%d')
             decomp_row = target_row.iloc[0]

        # Get prediction for REFERENCE date
        ref_row = ref_forecast_df[ref_forecast_df['ds'] == ref_date]
        if ref_row.empty:
            ref_price = ref_forecast_df.iloc[-1]['yhat']
        else:
            ref_price = ref_row.iloc[0]['yhat']
        
        # LSTM Integration
        try:
            lstm_forecasts = get_lstm_forecast()
            lstm_price_day1 = lstm_forecasts[0]
            lstm_price_day7 = lstm_forecasts[6]
            lstm_price_day30 = lstm_forecasts[29]
        except:
            lstm_price_day1 = raw_target_price
            lstm_price_day7 = raw_target_price
            lstm_price_day30 = raw_target_price

        try:
            direction_signal = get_lstm_direction_signal()
            lstm_direction = direction_signal["direction"]
            lstm_confidence = direction_signal["confidence_score"]
        except:
            lstm_direction = "NEUTRAL"
            lstm_confidence = 0.0

        # --- Unit Conversion (Quintal -> kg) ---
        raw_target_price /= 100.0
        ref_price /= 100.0
        conf_lower /= 100.0
        conf_upper /= 100.0
        lstm_price_day1 /= 100.0
        lstm_price_day7 /= 100.0
        lstm_price_day30 /= 100.0

        # Ensemble Logic
        prophet_change = raw_target_price - ref_price
        prophet_direction_up = prophet_change > 0
        lstm_direction_up = (lstm_direction == "UP")
        
        CONF_FLOOR = 0.30
        CONF_CEIL = 0.60
        
        if lstm_confidence <= CONF_FLOOR:
            lstm_weight = 0.0
        elif lstm_confidence >= CONF_CEIL:
            lstm_weight = 1.0
        else:
            lstm_weight = (lstm_confidence - CONF_FLOOR) / (CONF_CEIL - CONF_FLOOR)
        
        prophet_weight = 1.0 - lstm_weight
        magnitude = max(abs(prophet_change), ref_price * 0.005)
        
        if lstm_weight == 0:
            final_price = raw_target_price
        elif prophet_direction_up == lstm_direction_up:
            boost = 1.0 + (lstm_weight * 0.15)
            final_price = ref_price + (prophet_change * boost)
        else:
            lstm_signed = magnitude if lstm_direction_up else -magnitude
            blended_change = (prophet_change * prophet_weight) + (lstm_signed * lstm_weight)
            final_price = ref_price + blended_change
        
        # --- Policy Impacts (in kg) ---
        diesel_impact = (policy.diesel_tax * 15) / 100.0 
        final_price += diesel_impact
        
        status_msg = "Normal Market Conditions"
        if policy.export_ban:
            final_price *= 0.70
            status_msg = "Warning: Export Ban Triggered"
            
        subsidy_amount = final_price * (policy.subsidy_percent / 100.0)
        final_price -= subsidy_amount
        subsidy_impact = -subsidy_amount

        final_price = max(0.0, final_price)

        if policy.volatility_slider > 7.0: status_msg = "CRITICAL: High Market Volatility"
        elif policy.volatility_slider > 4.0: status_msg = "Warning: Elevated Market Stress"

        # --- Confidence Score (Dynamic) ---
        # Base confidence starts high for Prophet (it's generally good at trend)
        base_conf = 85.0
        
        # 1. Penalize for Volatility (Panic Index)
        # Slider 0-10. Each point drops confidence by ~1.5%
        base_conf -= (policy.volatility_slider * 1.5)
        
        # 2. Adjust by LSTM Agreement/Confidence
        # lstm_confidence is 0.0 to 1.0 (or similar scale, checking value)
        # If it's 0-100, we normalize. Assuming 0-1 here effectively.
        
        # Normalize lstm_conf to 0-1 range just in case
        l_conf_norm = max(0.0, min(1.0, float(lstm_confidence)))

        if prophet_direction_up == lstm_direction_up:
             # Agreement: Boost proportional to LSTM strength
             # Max boost: +10%
             base_conf += (l_conf_norm * 10.0)
        else:
             # Disagreement: Penalty proportional to LSTM strength
             # Max penalty: -20% (if LSTM is very sure but wrong vs Prophet)
             base_conf -= (l_conf_norm * 20.0)
             
        # 3. Micro-Jitter for Simulation "Feel"
        # REMOVED: Artificial jitter removes "natural" feeling of correctness
        # base_conf += random.uniform(-1.5, 1.5)

        # Cap confidence
        confidence_score = min(99.0, max(40.0, base_conf))
        
        # Derive bounds from confidence (higher confidence = narrower bounds)
        spread_pct = (100.0 - confidence_score) / 100.0
        
        safe_lower = final_price * (1.0 - (spread_pct * 0.5)) # Tighter lower bound
        conf_upper = final_price * (1.0 + (spread_pct * 0.5)) # Tighter upper bound

        # --- Decomposition (Corrected for Multiplicative Mode) ---
        # Model is multiplicative: yhat = trend * (1 + season + regressors)
        # So Absolute Impact = Trend * Component_Factor
        
        raw_trend = decomp_row['trend'] # Quintal price trend
        
        # Robust Seasonality Calculation
        # Sum all seasonality components that exist in the dataframe
        season_components = ['weekly', 'yearly', 'monthly', 'daily']
        available_components = [c for c in season_components if c in decomp_row]
        
        season_factor = sum(decomp_row[c] for c in available_components)
        
        season_kg = (raw_trend * season_factor) / 100.0
        season_kg = (raw_trend * season_factor) / 100.0
        
        # Regressors
        trans_factor = decomp_row.get('transport_lag_3', 0)
        trans_kg = (raw_trend * trans_factor) / 100.0
        
        ndvi_factor = decomp_row.get('ndvi_mean', 0)
        ndvi_kg = (raw_trend * ndvi_factor) / 100.0
        
        panic_factor = decomp_row.get('panic_index', 0)
        panic_kg = (raw_trend * panic_factor) / 100.0
        
        # Policy: Diesel & Subsidy are applied AFTER Prophet in main.py logic (Lines 289, 297),
        # so they are absolute values already calculated above.
        # diesel_impact, subsidy_impact are already in kg/absolute terms.
        
        # Market Impact (Residual)
        # In multiplicative, the "Market" is the base trend + national avg (if regressor) + rainfall (if regressor)
        # But here we treat "Market Structure" as the Trend itself + uncaptured residuals.
        # Let's define Market Impact as Trend (base price) + whatever is left.
        # Or simpler: Market Impact = Final - (Season + Transport + NDVI + Panic + Diesel + Subsidy)
        # This captures the "Base Price" (Trend) as part of Market.
        
        # Let's present "Trend" purely as the long-term move.
        trend_kg_val = raw_trend / 100.0
        
        # The "Market Impact" in the UI usually represents the 'Base State' or 'External Factors'. 
        # Let's set it to be the Trend value itself plus any unassigned regressors (Rainfall, National Avg).
        
        nat_avg_factor = decomp_row.get('national_avg_price', 0)
        rain_factor = decomp_row.get('rainfall', 0)
        
        other_factors = (nat_avg_factor + rain_factor)
        other_kg = (raw_trend * other_factors) / 100.0
        
        # We will group "Trend" (Base) and "Other" into a "Market Structure" or keep Trend separate?
        # The UI shows "Trend" and "Market Impact". 
        # Let's say Market Impact = Other Regressors (Rain, National Avg) + Residuals.
        
        market_impact = other_kg
        
        decomp = {
            "trend": round(trend_kg_val, 2),
            "seasonality": round(season_kg, 2),
            "transport_impact": round(trans_kg, 2),
            "ndvi_impact": round(ndvi_kg, 2),
            "panic_impact": round(panic_kg, 2),
            "diesel_impact": round(diesel_impact, 2),
            "subsidy_impact": round(subsidy_impact, 2),
            "market_impact": round(market_impact, 2)
        }

        tx_hash = log_to_polygon(final_price, policy.dict())
        real_val = actuals_map.get(target_date, None)
        
        return {
            "commodity": "Onion",
            "baseline_prediction": round(ref_price, 2),
            "final_adjusted_price": round(final_price, 2),
            "confidence_lower": round(safe_lower, 2),
            "confidence_upper": round(conf_upper, 2),
            "confidence_score": round(confidence_score, 1),
            "real_value": round(real_val / 100.0, 2) if real_val else None,
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
            "lstm_direction": get_lstm_direction_signal(),
            "decomposition": decomp,
            "forecast_trend": forecast_series
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend LAST (catch-all) so API routes take priority
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
