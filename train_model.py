import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
import json
import os
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score, accuracy_score

def train_and_save():
    csv_path = 'Agriculture_price_dataset.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    print("Loading real mandi data...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Filter for Onion
    print("Filtering for 'Onion'...")
    df = df[df['Commodity'].str.contains('Onion', case=False, na=False)]
    
    if df.empty:
        print("Error: No 'Onion' data found in dataset.")
        return

    print("Parsing dates...")
    df['ds'] = pd.to_datetime(df['Price Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['ds'])
    
    # Clean and convert Price
    df['y'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    df = df.dropna(subset=['y'])
    
    # Aggregate by date
    print("Aggregating daily prices...")

    # Aggregate data by date, taking the mean of modal prices
    daily_df = df.groupby('ds')['y'].mean().reset_index()
    daily_df.columns = ['ds', 'y']
    daily_df = daily_df.sort_values('ds')
    
    print(f"Total data: {len(daily_df)} days.")

    # Train-test split (80/20) - Chronological Split
    split_idx = int(len(daily_df) * 0.8)
    train_df = daily_df.iloc[:split_idx]
    test_df = daily_df.iloc[split_idx:]

    print(f"Training samples: {len(train_df)}")
    print(f"Testing samples: {len(test_df)}")

    # --- GRID SEARCH FOR HYPERPARAMETERS ---
    param_grid = {
        'seasonality_mode': ['additive', 'multiplicative'],
        'changepoint_prior_scale': [0.001, 0.01, 0.05, 0.1, 0.5], 
        'seasonality_prior_scale': [0.01, 1.0, 10.0]
    }

    best_params = {}
    best_mape = float('inf')

    import itertools

    # Generate all combinations of parameters
    all_params = [
        dict(zip(param_grid.keys(), v))
        for v in itertools.product(*param_grid.values())
    ]

    print(f"Starting Grid Search with {len(all_params)} combinations...")

    for params in all_params:
        # Simple validation split within the training set for tuning
        val_split_idx = int(len(train_df) * 0.8)
        tune_train = train_df.iloc[:val_split_idx]
        tune_val = train_df.iloc[val_split_idx:]
        
        m = Prophet(**params)
        
        # Add Indian holidays
        m.add_country_holidays(country_name='IN')
        
        # Add custom festivals
        indian_festivals = pd.DataFrame({
            'holiday': 'indian_festival',
            'ds': pd.to_datetime([
                '2023-03-08', '2023-10-24', '2023-11-12', # Holi, Dusshera, Diwali 2023
                '2024-03-25', '2024-10-12', '2024-11-01', # Holi, Dusshera, Diwali 2024
                '2025-03-14', '2025-10-02', '2025-10-20', # Holi, Dusshera, Diwali 2025
            ]),
            'lower_window': -1,
            'upper_window': 1,
        })
        
        m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
        
        # Fit model
        m.fit(tune_train)
        
        # Predict on validation set
        future_val = tune_val[['ds']].copy()
        forecast_val = m.predict(future_val)
        
        # Calculate MAPE
        y_true_val = tune_val['y'].values
        y_pred_val = forecast_val['yhat'].values
        # Handle division by zero
        mask = y_true_val != 0
        if np.sum(mask) == 0:
             mape_val = float('inf')
        else:
             mape_val = np.mean(np.abs((y_true_val[mask] - y_pred_val[mask]) / y_true_val[mask])) * 100
        
        if mape_val < best_mape:
            best_mape = mape_val
            best_params = params

    print(f"Best Parameters found: {best_params}")
    print(f"Best Validation MAPE: {best_mape:.2f}%")

    # --- RETRAIN WITH BEST PARAMETERS ---

    final_model = Prophet(**best_params)

    # Add headers/holidays to final model
    final_model.add_country_holidays(country_name='IN')
    final_model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

    # Fit on FULL training set
    final_model.fit(train_df)

    # Evaluate on TEST set
    future = test_df[['ds']].copy()
    forecast = final_model.predict(future)

    # Metrics Calculation
    y_true = test_df['y'].values
    y_pred = forecast['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

    print(f"Test MAE: {mae:.2f}")
    print(f"Test RMSE: {rmse:.2f}")
    print(f"Test MAPE: {mape:.2f}%")

    # Directional Accuracy (Did price go Up/Down correctly?)
    # Compare change from previous day
    # We need the last day of training data to get the change for the first day of test data
    last_train_price = train_df.iloc[-1]['y']
    y_true_with_prev = np.insert(y_true, 0, last_train_price)

    # Calculate actual direction: (Today - Yesterday) > 0
    y_true_dir = (y_true_with_prev[1:] - y_true_with_prev[:-1]) > 0

    # Calculate predicted direction logic
    y_pred_dir = (y_pred - y_true_with_prev[:-1]) > 0
    
    accuracy = accuracy_score(y_true_dir, y_pred_dir)
    f1 = f1_score(y_true_dir, y_pred_dir, average='weighted')

    print(f"Directional Accuracy: {accuracy*100:.2f}%")
    print(f"Directional F1 Score: {f1:.4f}")

    # Save the final model trained on ALL data for deployment
    deployment_model = Prophet(**best_params)
    deployment_model.add_country_holidays(country_name='IN')
    deployment_model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    deployment_model.fit(daily_df) # Fit on ALL data (Train + Test)

    with open('onion_prophet_model.json', 'w') as f:
        from prophet.serialize import model_to_json
        f.write(model_to_json(deployment_model))

    print("Optimized model saved to onion_prophet_model.json")

    # Write results to file
    with open('evaluation_results.txt', 'w') as f:
        f.write("MODEL EVALUATION RESULTS (Optimized - No Diesel/Filtering)\\n")
        f.write(f"Best Params: {best_params}\\n")
        f.write(f"Mean Absolute Error (MAE): {mae:.2f}\\n")
        f.write(f"Root Mean Squared Error (RMSE): {rmse:.2f}\\n")
        f.write(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%\\n")
        f.write(f"Directional Accuracy: {accuracy*100:.2f}%\\n")
        f.write(f"Directional F1 Score: {f1:.4f}\\n")

if __name__ == "__main__":
    train_and_save()
