import pandas as pd
from prophet.serialize import model_from_json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "onion_prophet_model.json")
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, "commodity_transport_costs.csv")

# Load Resources
with open(MODEL_PATH, "r") as fin:
    model = model_from_json(fin.read())

transport_df = pd.read_csv(TRANSPORT_CSV_PATH)
transport_df['ds'] = pd.to_datetime(transport_df['Date'], dayfirst=True, errors='coerce')
transport_df['transport_cost'] = pd.to_numeric(transport_df['Global_Transport_Cost_Index'], errors='coerce')
transport_df = transport_df[['ds', 'transport_cost']].dropna()
t_lookup = transport_df.set_index('ds')['transport_cost']

def get_lagged_cost(date):
    target_date = date - pd.Timedelta(days=3)
    last_transport_val = transport_df['transport_cost'].iloc[-1]
    try:
        val = t_lookup.asof(target_date)
        return last_transport_val if pd.isna(val) else val
    except Exception:
        return last_transport_val

def predict_for_date(target_date_str):
    print(f"\n--- Testing for date: {target_date_str} ---")
    last_history_date = model.history['ds'].max()
    print(f"Model Last History Date: {last_history_date}")
    
    target_date = pd.to_datetime(target_date_str)
    
    # REPLICATING CURRENT BROKEN LOGIC
    if target_date <= last_history_date:
        print("Date is within history. Triggering fallback (current logic)...")
        days_to_predict = 14
        future = model.make_future_dataframe(periods=days_to_predict)
    else:
        print("Date is in future.")
        days_to_predict = (target_date - last_history_date).days
        future = model.make_future_dataframe(periods=days_to_predict)

    future['transport_lag_3'] = future['ds'].apply(get_lagged_cost)
    if future['transport_lag_3'].isnull().all():
        future['transport_lag_3'] = 0
        
    forecast = model.predict(future)
    
    predicted_date = forecast.iloc[-1]['ds']
    predicted_val = forecast.iloc[-1]['yhat']

    # Write to file
    with open("debug_results.log", "a") as f:
        f.write(f"\n--- Testing for date: {target_date_str} ---\n")
        f.write(f"Requested Date: {target_date}\n")
        f.write(f"Returned Prediction Date: {predicted_date}\n")
        f.write(f"Predicted Value (yhat): {predicted_val}\n")
        
        f.write("\n--- Forecast Components (Last Row) ---\n")
        cols = ['ds', 'trend', 'yhat', 'transport_lag_3', 'multiplicative_terms', 'additive_terms']
        for c in ['yearly', 'weekly']:
            if c in forecast.columns:
                cols.append(c)
        f.write(str(forecast.iloc[-1][cols]) + "\n")
        
        if target_date != predicted_date:
            f.write(">>> MISMATCH DETECTED! <<\n")

# Clear log file first
open("debug_results.log", "w").close()

# Test Cases
predict_for_date("2024-01-01") # History
predict_for_date("2026-06-01") # Future (Likely missing transport data)
predict_for_date("2027-01-01") # Deep Future
