import os
import pandas as pd
from prophet.serialize import model_from_json
import warnings

# Suppress warnings
import logging
logging.getLogger('prophet').setLevel(logging.CRITICAL)
logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'onion_prophet_model.json')
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, '..', 'commodity_transport_costs.csv')

def load_transport_data():
    if os.path.exists(TRANSPORT_CSV_PATH):
        df = pd.read_csv(TRANSPORT_CSV_PATH)
        df['ds'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        # Handle column name variation if necessary
        col = 'Global_Transport_Cost_Index' if 'Global_Transport_Cost_Index' in df.columns else df.columns[1]
        df['transport_cost'] = pd.to_numeric(df[col], errors='coerce')
        return df[['ds', 'transport_cost']].dropna().set_index('ds')['transport_cost']
    return None

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return

    print("Loading model...")
    with open(MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())

    last_date = model.history['ds'].max()
    print(f"Last Training Date: {last_date.date()}")

    # Define prediction horizons
    horizons = [1, 7, 30] # Days ahead
    target_dates = [last_date + pd.Timedelta(days=h) for h in horizons]
    
    # Create Future DataFrame for max horizon
    future = model.make_future_dataframe(periods=30)
    
    # --- Prepare Regressors ---
    
    # 1. Transport Lag (3 days)
    transport_series = load_transport_data()
    last_transport_val = transport_series.iloc[-1] if transport_series is not None else 0
    
    def get_transport_lag(date):
        if transport_series is None: return 0
        target = date - pd.Timedelta(days=3)
        try:
             idx = transport_series.index.get_indexer([target], method='pad')[0]
             if idx == -1: return last_transport_val
             return transport_series.iloc[idx]
        except:
            return last_transport_val
            
    future['transport_lag_3'] = future['ds'].apply(get_transport_lag)

    # 2. National Avg Price (Default 2500)
    future['national_avg_price'] = 2500.0
    
    # 3. Rainfall (Default 0)
    future['rainfall'] = 0.0
    
    # 4. Panic Index (Default 0 - Normal Conditions)
    future['panic_index'] = 0.0
    
    # Predict
    print("\nGenerating Forecasts...")
    forecast = model.predict(future)
    
    print("\n--- FORECAST RESULTS ---")
    labels = ["1 Day Later", "1 Week Later", "1 Month Later"]
    
    for label, target_date in zip(labels, target_dates):
        # Find the row for target_date
        row = forecast[forecast['ds'] == target_date]
        if not row.empty:
            price = row.iloc[0]['yhat']
            lower = row.iloc[0]['yhat_lower']
            upper = row.iloc[0]['yhat_upper']
            print(f"{label:<15} ({target_date.date()}): ₹{price:.2f} (Range: ₹{lower:.2f} - ₹{upper:.2f})")
        else:
            print(f"{label:<15} ({target_date.date()}): Data not found")

if __name__ == "__main__":
    main()
