import logging
import warnings
import os
import glob
import pandas as pd
from prophet import Prophet
from sklearn.metrics import accuracy_score
import numpy as np

# Suppress warnings
logging.getLogger('prophet').setLevel(logging.CRITICAL)
logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

# --- CONSTANTS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices') 
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, '..', 'commodity_transport_costs.csv')
RAINFALL_CSV_PATH = os.path.join(BASE_DIR, '..', 'Rainfall', 'Nashik_Weekly_Rainfall_2023_2025.csv')
EVAL_RESULTS_PATH = os.path.join(BASE_DIR, 'evaluation_results_monthly.txt')

MARKET_FILTER = 'Pratapgarh'
COMMODITY_FILTER = 'Onion'
VARIETY_FILTER = 'Red'
HOLIDAY_COUNTRY = 'IN'

YEARS_TO_PROCESS = ['2023', '2024', '2025', '2026']

def load_and_aggregate_data():
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    relevant_files = [f for f in all_files if any(y in f for y in YEARS_TO_PROCESS)]
    
    dfs = []
    for f in relevant_files:
        try:
            temp_df = pd.read_csv(f)
            temp_df.columns = temp_df.columns.str.strip()
            
            # Filter for Red Onion
            if 'Commodity' in temp_df.columns and 'Variety' in temp_df.columns:
                mask = (temp_df['Commodity'].str.strip().str.lower() == COMMODITY_FILTER.lower()) & \
                       (temp_df['Variety'].str.strip().str.lower() == VARIETY_FILTER.lower())
                filtered_df = temp_df[mask].copy()
                if not filtered_df.empty:
                    dfs.append(filtered_df)
        except Exception:
            pass
            
    if not dfs: return None
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df['ds'] = pd.to_datetime(full_df['Arrival_Date'], errors='coerce')
    full_df['price'] = pd.to_numeric(full_df['Modal_Price'], errors='coerce')
    full_df = full_df.dropna(subset=['ds', 'price'])
    
    # Target Data
    target_mask = full_df['Market'].str.strip().str.lower() == MARKET_FILTER.lower()
    target_df = full_df[target_mask].copy()
    
    # 1. Resample Target to Monthly ('ME')
    monthly_target = target_df.set_index('ds')[['price']].resample('ME').mean().reset_index()
    monthly_target = monthly_target.rename(columns={'price': 'y'})
    
    # 2. National Average (Aggregated Monthly)
    nat_avg = full_df.set_index('ds')[['price']].resample('ME').mean().reset_index()
    nat_avg.rename(columns={'price': 'national_avg_price'}, inplace=True)
    
    merged = pd.merge(monthly_target, nat_avg, on='ds', how='left')
    
    # 3. Rainfall (Aggregated Monthly)
    if os.path.exists(RAINFALL_CSV_PATH):
        rain_df = pd.read_csv(RAINFALL_CSV_PATH)
        rain_df['ds'] = pd.to_datetime(rain_df['date'], errors='coerce')
        rain_df['rainfall'] = pd.to_numeric(rain_df['rainfall_mm'], errors='coerce')
        rain_monthly = rain_df.set_index('ds').resample('ME')['rainfall'].sum().reset_index() # Sum for rainfall
        merged = pd.merge(merged, rain_monthly, on='ds', how='left')
        merged['rainfall'] = merged['rainfall'].fillna(0)
    else:
        merged['rainfall'] = 0
        
    merged = merged.ffill().bfill()
    return merged

def train_monthly():
    print("Loading and creating Monthly Aggregates...")
    df = load_and_aggregate_data()
    if df is None:
        print("No data found.")
        return

    # Train/Test Split (Leave last 6 months for testing)
    test_months = 6
    if len(df) < 12: test_months = 2 # Adjustment for small datasets
    
    train_df = df.iloc[:-test_months]
    test_df = df.iloc[-test_months:]
    
    print(f"Training on {len(train_df)} months. Testing on {len(test_df)} months.")
    
    # Model Setup
    params = {
        'seasonality_mode': 'multiplicative',
        'changepoint_prior_scale': 0.5,
        'yearly_seasonality': True,
        'weekly_seasonality': False,
        'daily_seasonality': False
    }
    
    model = Prophet(**params)
    model.add_country_holidays(country_name=HOLIDAY_COUNTRY)
    model.add_regressor('national_avg_price')
    model.add_regressor('rainfall')
    
    print("Training Monthly Model...")
    model.fit(train_df)
    
    # Predict
    future = test_df[['ds', 'national_avg_price', 'rainfall']].copy()
    forecast = model.predict(future)
    
    y_true = test_df['y'].values
    y_pred = forecast['yhat'].values
    
    # Evaluaton
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    # Directional Accuracy
    if len(train_df) > 0:
        last_train = train_df.iloc[-1]['y']
        y_true_w_prev = np.insert(y_true, 0, last_train)
        y_true_dir = (y_true_w_prev[1:] - y_true_w_prev[:-1]) > 0
        y_pred_dir = (y_pred - y_true_w_prev[:-1]) > 0
        dir_acc = accuracy_score(y_true_dir, y_pred_dir) * 100
    else:
        dir_acc = 0.0
        
    print(f"Monthly Test MAPE: {mape:.2f}%")
    print(f"Monthly Directional Accuracy: {dir_acc:.2f}%")
    
    with open(EVAL_RESULTS_PATH, 'w') as f:
        f.write("Dedicated Monthly Model Results\n")
        f.write(f"Test Period: Last {test_months} Months\n")
        f.write(f"MAPE: {mape:.2f}%\n")
        f.write(f"Directional Accuracy: {dir_acc:.2f}%\n")

if __name__ == "__main__":
    train_monthly()
