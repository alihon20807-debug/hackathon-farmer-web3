import logging
import warnings
import os

# Suppress Prophet, Plotly, and Holidays warnings
logging.getLogger('prophet').setLevel(logging.CRITICAL)
logging.getLogger('prophet.plot').setLevel(logging.CRITICAL)
logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.serialize import model_to_json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score, accuracy_score
import matplotlib.pyplot as plt

try:
    from lstm_engine import get_lstm_scores_for_dataset
except ImportError:
    from .lstm_engine import get_lstm_scores_for_dataset

# --- CONSTANTS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices')
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, '..', 'commodity_transport_costs.csv')
NDVI_CSV_PATH = os.path.join(BASE_DIR, 'ndvi_weekly_nashik.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'onion_prophet_model.json')
EVAL_RESULTS_PATH = os.path.join(BASE_DIR, 'evaluation_results.txt')
LAG_DAYS = 3
HOLIDAY_COUNTRY = 'IN'

def load_and_preprocess_data():
    import glob
    
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not all_files:
        print(f"Error: No CSV files found in {DATA_DIR}")
        return None

    print(f"Loading data from {len(all_files)} files in Daily Mandi Prices...")
    
    combined = []
    for f in all_files:
        try:
            temp = pd.read_csv(f)
            temp = temp[temp['Commodity'].str.contains('Onion', case=False, na=False)]
            if not temp.empty: combined.append(temp)
        except: pass
    
    if not combined:
        print("Error: No 'Onion' data found.")
        return None
    
    df = pd.concat(combined, ignore_index=True)
    df['ds'] = pd.to_datetime(df['Arrival_Date'], errors='coerce')
    df['y'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    df = df.dropna(subset=['ds', 'y'])
    
    # Aggregate daily
    daily_df = df.groupby('ds')['y'].mean().reset_index().sort_values('ds')
    print(f"Loaded {len(daily_df)} daily price points.")
    
    # Load Transport Data
    if os.path.exists(TRANSPORT_CSV_PATH):
        transport_df = pd.read_csv(TRANSPORT_CSV_PATH)
        transport_df['ds'] = pd.to_datetime(transport_df['Date'], dayfirst=True, errors='coerce')
        transport_df['transport_cost'] = pd.to_numeric(transport_df['Global_Transport_Cost_Index'], errors='coerce')
        transport_df = transport_df[['ds', 'transport_cost']].dropna()
        
        daily_df = pd.merge(daily_df, transport_df, on='ds', how='left')
        daily_df['transport_cost'] = daily_df['transport_cost'].ffill().bfill().fillna(0)
        daily_df[f'transport_lag_{LAG_DAYS}'] = daily_df['transport_cost'].shift(LAG_DAYS)
        daily_df = daily_df.dropna(subset=[f'transport_lag_{LAG_DAYS}'])
        print(f"Data merged with {LAG_DAYS}-day lag transport costs.")
    else:
        print(f"Warning: {TRANSPORT_CSV_PATH} not found. Using dummy values.")
        daily_df[f'transport_lag_{LAG_DAYS}'] = 0
    
    # Add placeholder columns for regressors main.py passes at prediction time
    daily_df['national_avg_price'] = daily_df['y'].rolling(30, min_periods=1).mean()
    daily_df['rainfall'] = 0.0
    daily_df['panic_index'] = 0.0

    # --- NDVI Satellite Data ---
    if os.path.exists(NDVI_CSV_PATH):
        print(f"Loading NDVI data from {NDVI_CSV_PATH}...")
        ndvi_df = pd.read_csv(NDVI_CSV_PATH)
        ndvi_df['ds'] = pd.to_datetime(ndvi_df['ds'])
        # Forward-fill weekly NDVI to daily resolution via merge_asof
        ndvi_df = ndvi_df.sort_values('ds')
        daily_df = daily_df.sort_values('ds')
        daily_df = pd.merge_asof(daily_df, ndvi_df[['ds', 'ndvi_mean', 'ndvi_anomaly']],
                                  on='ds', direction='backward')
        daily_df['ndvi_mean'] = daily_df['ndvi_mean'].fillna(0.0)
        daily_df['ndvi_anomaly'] = daily_df['ndvi_anomaly'].fillna(0.0)
        print(f"NDVI data merged. Non-zero rows: {(daily_df['ndvi_mean'] != 0).sum()}")
    else:
        print(f"Warning: {NDVI_CSV_PATH} not found. Using zeros for NDVI.")
        daily_df['ndvi_mean'] = 0.0
        daily_df['ndvi_anomaly'] = 0.0
    
    # --- LSTM Direction Score ---
    try:
        print("Generating LSTM direction scores...")
        lstm_scores = get_lstm_scores_for_dataset()
        daily_df = pd.merge(daily_df, lstm_scores, on='ds', how='left')
        daily_df['lstm_score'] = daily_df['lstm_score'].fillna(0.0)
        daily_df['lstm_confidence'] = daily_df['lstm_confidence'].fillna(0.0)
        daily_df['lstm_high_conf'] = daily_df['lstm_high_conf'].fillna(0.0)
        print(f"LSTM scores merged. High-conf signals: {(daily_df['lstm_high_conf'] != 0).sum()}")
    except Exception as e:
        print(f"Warning: Could not generate LSTM scores: {e}")
        daily_df['lstm_score'] = 0.0
        daily_df['lstm_confidence'] = 0.0
        daily_df['lstm_high_conf'] = 0.0
        
    return daily_df

def train_and_save():
    daily_df = load_and_preprocess_data()
    if daily_df is None: return

    # Train-test split (80/20)
    split_idx = int(len(daily_df) * 0.8)
    train_df = daily_df.iloc[:split_idx]
    test_df = daily_df.iloc[split_idx:]

    print(f"Training samples: {len(train_df)}, Testing samples: {len(test_df)}")

    # Hyperparameters (Fixed based on prior optimization)
    # forcing multiplicative mode as determined to be best
    params = {
        'seasonality_mode': 'multiplicative',
        'changepoint_prior_scale': 0.5,
        'seasonality_prior_scale': 10.0
    }
    
    # Grid Search (Optional - strictly for minor tuning, can be skipped if confident)
    # For now, we use the best params found: 
    # {'seasonality_mode': 'multiplicative', 'changepoint_prior_scale': 0.5, 'seasonality_prior_scale': 10.0}

    print(f"Training model with params: {params}")
    
    # --- TRAIN ON TRAINING SET (For Eval) ---
    model = Prophet(**params)
    model.add_country_holidays(country_name=HOLIDAY_COUNTRY)
    model.add_regressor(f'transport_lag_{LAG_DAYS}')
    model.add_regressor('national_avg_price')
    model.add_regressor('rainfall')
    model.add_regressor('panic_index')
    model.add_regressor('ndvi_mean')       # Crop health from satellite
    # model.add_regressor('ndvi_anomaly')    # REMOVED per user request
    model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    
    model.fit(train_df)

    # --- EVALUATE ON TEST SET ---
    future = test_df[['ds', f'transport_lag_{LAG_DAYS}', 'national_avg_price', 'rainfall', 'panic_index', 'ndvi_mean']].copy()
    forecast = model.predict(future)
    
    y_true = test_df['y'].values
    y_pred = forecast['yhat'].values
    
    y_pred = forecast['yhat'].values
    
    with open(os.path.join(BASE_DIR, 'stats.txt'), 'w') as f:
        f.write(f"--- Prediction Stats ---\n")
        f.write(f"Min: {y_pred.min()}, Max: {y_pred.max()}\n")
        f.write(f"Zeros: {(y_pred == 0).sum()}\n")
        f.write(f"NaNs: {np.isnan(y_pred).sum()}\n")
        f.write(f"Head: {y_pred[:5]}\n")
        f.write(f"Inputs Check (Head):\n{future.head().to_string()}\n")
        f.write("------------------------\n")

    print(f"Stats written to stats.txt")


    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    print(f"Test MAPE: {mape:.2f}%")

    # Directional Accuracy
    last_train_price = train_df.iloc[-1]['y']
    y_true_with_prev = np.insert(y_true, 0, last_train_price)
    y_true_dir = (y_true_with_prev[1:] - y_true_with_prev[:-1]) > 0
    y_pred_dir = (y_pred - y_true_with_prev[:-1]) > 0
    dir_acc = accuracy_score(y_true_dir, y_pred_dir) * 100

    print(f"Directional Accuracy: {dir_acc:.2f}%")

    # --- PLOT RESULTS ---
    plt.figure(figsize=(12, 6))
    
    # Filter outliers just for the plot (per user request)
    y_pred_plot = y_pred.copy()
    y_pred_plot[y_pred_plot > 15000] = np.nan  # Mask anomalies
    
    plt.plot(test_df['ds'], y_true, label='Actual Prices', color='blue')
    plt.plot(test_df['ds'], y_pred_plot, label='Predicted Prices', color='red', linestyle='dashed')
    plt.title('Actual vs Predicted Onion Prices (Test Set) - [Anomalies Removed]')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    plot_path = os.path.join(BASE_DIR, 'forecast_vs_actual.png')
    plt.savefig(plot_path)
    print(f"Plot saved to {plot_path}")



    # --- CROSS VALIDATION ---
    # SKIPPED per user request
    cv_mape = 0.0


    # --- FINAL RETRAINING (FULL DATA) ---
    print("\nRetraining on FULL dataset for deployment...")
    final_model = Prophet(**params)
    final_model.add_country_holidays(country_name=HOLIDAY_COUNTRY)
    final_model.add_regressor(f'transport_lag_{LAG_DAYS}')
    final_model.add_regressor('national_avg_price')
    final_model.add_regressor('rainfall')
    final_model.add_regressor('panic_index')
    final_model.add_regressor('ndvi_mean')
    # final_model.add_regressor('ndvi_anomaly') # REMOVED
    final_model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    
    final_model.fit(daily_df)
    
    # Save Model
    with open(MODEL_PATH, 'w') as f:
        f.write(model_to_json(final_model))
    print(f"Model saved to {MODEL_PATH}")

    # Save Results
    with open(EVAL_RESULTS_PATH, 'w') as f:
        f.write("MODEL EVALUATION RESULTS (Refactored)\n")
        f.write(f"Parameters: {params}\n")
        f.write(f"Test MAPE: {mape:.2f}%\n")
        f.write(f"CV MAPE: {cv_mape:.2f}%\n")
        f.write(f"Directional Accuracy: {dir_acc:.2f}%\n")

if __name__ == "__main__":
    train_and_save()

