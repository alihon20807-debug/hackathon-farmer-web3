import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os
import glob
from datetime import timedelta

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices')
CLEAN_DATA_PATH = os.path.join(BASE_DIR, 'onion_clean.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'lstm_model.pth')
SEQ_LENGTH = 30
PREDICTION_WINDOW = 30  # Forecast 30 days into the future
HIDDEN_SIZE = 64
NUM_LAYERS = 2  # Increased complexity for multi-step
EPOCHS = 100    # Increased epochs
LEARNING_RATE = 0.001

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=30):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

def prepare_data():
    if os.path.exists(CLEAN_DATA_PATH):
        print(f"Loading existing cleaned data from {CLEAN_DATA_PATH}")
        return pd.read_csv(CLEAN_DATA_PATH)

    print("Aggregating raw data...")
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not all_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

    df_list = []
    for filename in all_files:
        try:
            temp_df = pd.read_csv(filename)
            # Filter for Onion
            temp_df = temp_df[temp_df['Commodity'].str.contains('Onion', case=False, na=False)]
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    if not df_list:
        raise ValueError("No Onion data found in any CSV files.")

    df = pd.concat(df_list, ignore_index=True)
    
    # Standardize columns
    df['ds'] = pd.to_datetime(df['Arrival_Date'], errors='coerce') # Assuming Arrival_Date exists based on inspection
    # Fallback to 'Price Date' if Arrival_Date is missing (based on previous file view observation of 2024.csv having Arrival_Date)
    
    df['y'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    df = df.dropna(subset=['ds', 'y'])
    
    # Aggregate to daily average
    daily_df = df.groupby('ds')['y'].mean().reset_index().sort_values('ds')
    
    print(f"Saving cleaned data to {CLEAN_DATA_PATH}")
    daily_df.to_csv(CLEAN_DATA_PATH, index=False)
    return daily_df

def create_sequences(data, seq_length, prediction_window=30):
    xs, ys = [], []
    for i in range(len(data) - seq_length - prediction_window + 1):
        x = data[i:(i + seq_length)]
        y = data[(i + seq_length):(i + seq_length + prediction_window)]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def train_model():
    df = prepare_data()
    if df is None or df.empty:
        print("No data available for training.")
        return

    data = df['y'].values.reshape(-1, 1)
    
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)

    X, y = create_sequences(scaled_data, SEQ_LENGTH, PREDICTION_WINDOW)
    
    if len(X) == 0:
        print("Not enough data to create sequences.")
        return

    X_train = torch.from_numpy(X).float()
    y_train = torch.from_numpy(y).float().squeeze(-1)

    model = LSTMModel(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=PREDICTION_WINDOW)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("Starting training...")
    model.train()
    for epoch in range(EPOCHS):
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{EPOCHS}], Loss: {loss.item():.4f}')

    print("Training complete.")
    
    # Save model and scaler
    torch.save({
        'model_state_dict': model.state_dict(),
        'scaler': scaler
    }, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    
    return model, scaler

def evaluate_model():
    if not os.path.exists(MODEL_PATH):
        print("Model not found. Training now...")
        train_model()

    df = prepare_data()
    data = df['y'].values.reshape(-1, 1)
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False)
    scaler = checkpoint['scaler']
    
    model = LSTMModel(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Create sequences for the entire dataset
    scaled_data = scaler.transform(data)
    X, y = create_sequences(scaled_data, SEQ_LENGTH)

    if len(X) == 0:
        print("Not enough data for evaluation.")
        return

    # Use last 20% for testing
    split_idx = int(len(X) * 0.8)
    X_test = torch.from_numpy(X[split_idx:]).float()
    y_test = y[split_idx:] # Keep as numpy for comparison
    
    if len(X_test) == 0:
        print("Test set empty.")
        return

    print(f"Evaluating on {len(X_test)} samples...")

    with torch.no_grad():
        test_preds_scaled = model(X_test)
        test_preds = scaler.inverse_transform(test_preds_scaled.numpy())
        y_test_actual = scaler.inverse_transform(y_test.reshape(-1, 1))

    # Metrics
    mse = np.mean((test_preds - y_test_actual) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(test_preds - y_test_actual))
    mape = np.mean(np.abs((y_test_actual - test_preds) / y_test_actual)) * 100

    print("\n--- Model Performance Metrics ---")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"MAPE: {mape:.2f}%")
    print("---------------------------------")
    
    return rmse, mae, mape

def evaluate_model():
    if not os.path.exists(MODEL_PATH):
        print("Model not found. Training now...")
        train_model()

    df = prepare_data()
    data = df['y'].values.reshape(-1, 1)
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False)
    scaler = checkpoint['scaler']
    
    model = LSTMModel(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=PREDICTION_WINDOW)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Create sequences for the entire dataset
    scaled_data = scaler.transform(data)
    X, y = create_sequences(scaled_data, SEQ_LENGTH, PREDICTION_WINDOW)

    if len(X) == 0:
        print("Not enough data for evaluation.")
        return 0,0,0

    # Use last 20% for testing
    split_idx = int(len(X) * 0.8)
    X_test = torch.from_numpy(X[split_idx:]).float()
    y_test = y[split_idx:] # Keep as numpy for comparison
    
    if len(X_test) == 0:
        print("Test set empty.")
        return 0,0,0

    print(f"Evaluating on {len(X_test)} samples...")

    with torch.no_grad():
        test_preds_scaled = model(X_test)
        # Inverse transform shape (Batch, 30)
        # We need to inverse transform each prediction step
        # Since scaler expects (N, 1), we flatten, transform, and reshape
        
        # Actuals
        y_test_flat = y_test.reshape(-1, 1)
        # Reshape to (Batch, 30) instead of (Batch, 30, 1)
        y_test_actual = scaler.inverse_transform(y_test_flat).reshape(y_test.shape[0], y_test.shape[1])
        
        # Preds
        test_preds_flat = test_preds_scaled.numpy().reshape(-1, 1)
        test_preds = scaler.inverse_transform(test_preds_flat).reshape(test_preds_scaled.shape)

    # Metrics (Overall)
    mse = np.mean((test_preds - y_test_actual) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(test_preds - y_test_actual))
    mape = np.mean(np.abs((y_test_actual - test_preds) / y_test_actual)) * 100
    
    # Directional Accuracy (Compare T+1 with T)
    # We'll calculate it for the "Next Day" (Step 0) specifically, as that's most critical
    # Actual direction
    actual_diff = y_test_actual[:, 0] - scaler.inverse_transform(X_test[:, -1, :].numpy().reshape(-1,1)).flatten()
    pred_diff = test_preds[:, 0] - scaler.inverse_transform(X_test[:, -1, :].numpy().reshape(-1,1)).flatten()
    
    correct_direction = np.sign(actual_diff) == np.sign(pred_diff)
    directional_accuracy = np.mean(correct_direction) * 100

    print("\n--- Model Performance Metrics (Multi-Horizon) ---")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"MAPE: {mape:.2f}%")
    print(f"Directional Accuracy (Next Day): {directional_accuracy:.2f}%")
    print("-----------------------------------------------")
    
    return rmse, mae, mape, directional_accuracy

def get_lstm_forecast():
    if not os.path.exists(MODEL_PATH):
        print("Model not found. Training now...")
        train_model()
    
    # Load data for inference (need the last SEQ_LENGTH days)
    df = prepare_data()
    data = df['y'].values.reshape(-1, 1)
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False)
    
    scaler = checkpoint['scaler']

    model = LSTMModel(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=PREDICTION_WINDOW)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Get last sequence
    last_sequence = data[-SEQ_LENGTH:]
    if len(last_sequence) < SEQ_LENGTH:
        raise ValueError("Not enough data for inference")

    scaled_seq = scaler.transform(last_sequence)
    X_input = torch.from_numpy(scaled_seq).float().unsqueeze(0) # Add batch dim

    with torch.no_grad():
        predicted_scaled = model(X_input)
        # Predicted scaled is (1, 30)
        predicted_prices = scaler.inverse_transform(predicted_scaled.numpy().reshape(-1, 1)).flatten()
        
    return predicted_prices.tolist() # Returns list of 30 floats

if __name__ == "__main__":
    # Force retrain to ensure files are created
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
    
    try:
        rmse, mae, mape, da = evaluate_model()
        with open("metrics.txt", "w") as f:
            f.write(f"RMSE: {rmse:.4f}\n")
            f.write(f"MAE:  {mae:.4f}\n")
            f.write(f"MAPE: {mape:.2f}%\n")
            f.write(f"Directional Accuracy: {da:.2f}%\n")
        
        forecasts = get_lstm_forecast()
        print(f"\nPredicted 30-Day Forecast:")
        print(f"Day 1: {forecasts[0]:.2f}")
        print(f"Day 7: {forecasts[6]:.2f}")
        print(f"Day 30: {forecasts[29]:.2f}")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
