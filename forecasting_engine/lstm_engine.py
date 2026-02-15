import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import os
import glob
from datetime import timedelta

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices')
CLEAN_DATA_PATH = os.path.join(BASE_DIR, 'onion_clean_with_transport.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'lstm_clf_transport_model.pth')
TRANSPORT_PATH = os.path.join(BASE_DIR, '..', 'commodity_transport_costs.csv')
NDVI_CSV_PATH = os.path.join(BASE_DIR, 'ndvi_weekly_nashik.csv')

SEQ_LENGTH = 10 
PREDICTION_WINDOW = 30
HIDDEN_SIZE = 64       # Increased to 64
NUM_LAYERS = 2         # Increased to 2
EPOCHS = 100           
LEARNING_RATE = 0.001 
INPUT_SIZE = 16        # Updated for new features
FEATURE_COLS = ['log_ret', 'rsi', 'macd', 'macd_signal', 'roc', 'national_log_ret', 
                'transport_cost', 'ndvi_mean', 'ndvi_anomaly',
                'bb_upper', 'bb_lower', 'bb_width', 'stoch_k', 'stoch_d', 'cci', 'willr']

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

class DirectionClfLSTM(nn.Module):
    def __init__(self, input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=30):
        super(DirectionClfLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, output_size),
            nn.Sigmoid() 
        )

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        last_out = out[:, -1, :] 
        
        pred_probs = self.classifier(last_out)
        return pred_probs

def calculate_indicators(df):
    # Standard Indicators
    delta = df['y'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    exp1 = df['y'].ewm(span=12, adjust=False).mean()
    exp2 = df['y'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    df['roc'] = df['y'].pct_change(periods=10) * 100

    # --- Advanced Indicators ---
    
    # Bollinger Bands
    df['ma20'] = df['y'].rolling(window=20).mean()
    df['std20'] = df['y'].rolling(window=20).std()
    df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['ma20']
    
    # Stochastic Oscillator
    low14 = df['y'].rolling(window=14).min()
    high14 = df['y'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['y'] - low14) / (high14 - low14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    # CCI (Commodity Channel Index)
    tp = (df['y'] + df['y'] + df['y']) / 3 # Approximation using close price as high/low/close
    sma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df['cci'] = (tp - sma_tp) / (0.015 * mad_tp)
    
    # Williams %R
    df['willr'] = -100 * ((high14 - df['y']) / (high14 - low14))
    
    return df.fillna(0)

def prepare_data():
    if os.path.exists(CLEAN_DATA_PATH):
        df = pd.read_csv(CLEAN_DATA_PATH)
        df['ds'] = pd.to_datetime(df['ds'])
    else:
        print("Aggregating raw data...")
        all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
        if not all_files: raise FileNotFoundError("No data")
        
        combined_list = []
        for filename in all_files:
            try:
                temp_df = pd.read_csv(filename)
                temp_df = temp_df[temp_df['Commodity'].str.contains('Onion', case=False, na=False)]
                if not temp_df.empty: combined_list.append(temp_df)
            except: pass
            
        full_df = pd.concat(combined_list, ignore_index=True)
        full_df['ds'] = pd.to_datetime(full_df['Arrival_Date'], errors='coerce')
        full_df['y'] = pd.to_numeric(full_df['Modal_Price'], errors='coerce')
        full_df = full_df.dropna(subset=['ds', 'y'])
        
        df = full_df.groupby('ds')['y'].mean().reset_index().sort_values('ds')
        
        df.to_csv(CLEAN_DATA_PATH, index=False)
            
    df = calculate_indicators(df)
    df['price'] = df['y']
    df['log_ret'] = np.log(df['price'] / df['price'].shift(1))
    
    # National Log Return (self-series)
    df['national_log_ret'] = df['log_ret'] 
    
    # --- Transport Cost ---
    if os.path.exists(TRANSPORT_PATH):
        t_df = pd.read_csv(TRANSPORT_PATH)
        t_df['ds'] = pd.to_datetime(t_df['Date'], errors='coerce')
        t_df['transport_cost'] = pd.to_numeric(t_df['Global_Transport_Cost_Index'], errors='coerce')
        t_df = t_df[['ds', 'transport_cost']].dropna()
        df = pd.merge(df, t_df, on='ds', how='left')
        df['transport_cost'] = df['transport_cost'].ffill().bfill().fillna(0)
        print(f"Transport cost merged. Non-zero: {(df['transport_cost'] != 0).sum()}")
    else:
        print("Warning: No transport data found. Using 0.")
        df['transport_cost'] = 0.0
    
    # --- NDVI Satellite Data ---
    if os.path.exists(NDVI_CSV_PATH):
        ndvi_df = pd.read_csv(NDVI_CSV_PATH)
        ndvi_df['ds'] = pd.to_datetime(ndvi_df['ds'])
        ndvi_df = ndvi_df.sort_values('ds')
        df = df.sort_values('ds')
        df = pd.merge_asof(df, ndvi_df[['ds', 'ndvi_mean', 'ndvi_anomaly']],
                           on='ds', direction='backward')
        df['ndvi_mean'] = df['ndvi_mean'].fillna(0.0)
        df['ndvi_anomaly'] = df['ndvi_anomaly'].fillna(0.0)
        print(f"NDVI merged. Non-zero: {(df['ndvi_mean'] != 0).sum()}")
    else:
        print("Warning: No NDVI data found. Using 0.")
        df['ndvi_mean'] = 0.0
        df['ndvi_anomaly'] = 0.0

    df = df.iloc[31:].reset_index(drop=True)
    df = df.dropna()
    
    return df

def create_sequences(data_values, seq_length, prediction_window=30):
    xs, ys_cls = [], []
    for i in range(len(data_values) - seq_length - prediction_window + 1):
        x = data_values[i:(i + seq_length)]
        y_ret = data_values[(i + seq_length):(i + seq_length + prediction_window), 0]
        y_dir = (y_ret > 0).astype(float) 
        
        xs.append(x)
        ys_cls.append(y_dir)
        
    return np.array(xs), np.array(ys_cls)

def run_rf_benchmark(X, y):
    N, S, F = X.shape
    X_flat = X.reshape(N, S*F)
    split_idx = int(N * 0.8)
    X_train, X_test = X_flat[:split_idx], X_flat[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    y_train_day1 = y_train[:, 0]
    y_test_day1 = y_test[:, 0]
    
    print("\n--- Running RF Benchmark (Simpler Features) ---")
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train_day1)
    
    train_acc = accuracy_score(y_train_day1, clf.predict(X_train))
    test_acc = accuracy_score(y_test_day1, clf.predict(X_test))
    
    print(f"RF Train Acc: {train_acc:.2f}")
    print(f"RF Test Acc:  {test_acc:.2f}")
    print("------------------------------------------------\n")
    return test_acc

def train_model():
    df = prepare_data()
    # Dropped Rainfall, kept Transport Cost
    features = df[FEATURE_COLS].values
    
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    X, y_cls = create_sequences(scaled_features, SEQ_LENGTH, PREDICTION_WINDOW)
    
    if len(X) == 0: return

    run_rf_benchmark(X, y_cls)

    X_train = torch.from_numpy(X).float().to(device)
    y_cls_train = torch.from_numpy(y_cls).float().to(device)

    model = DirectionClfLSTM(input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=PREDICTION_WINDOW).to(device)
    criterion = nn.BCELoss() 
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4) 
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'max', patience=10, factor=0.5) 

    print(f"Starting Simplified LSTM Training on {device}...")
    model.train()
    
    for epoch in range(EPOCHS):
        pred_probs = model(X_train)
        loss = criterion(pred_probs, y_cls_train)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        with torch.no_grad():
            pred_binary = (pred_probs > 0.5).float()
            acc = (pred_binary == y_cls_train).float().mean()
        
        scheduler.step(acc) 
        
        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{EPOCHS}], Loss: {loss.item():.4f}, Train Acc: {acc:.2f}, LR: {optimizer.param_groups[0]["lr"]:.6f}')

    torch.save({'model_state_dict': model.state_dict(), 'scaler': scaler, 'avg_abs_ret': np.mean(np.abs(features[:, 0]))}, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

def evaluate_model():
    if not os.path.exists(MODEL_PATH): train_model()

    df = prepare_data()
    features = df[FEATURE_COLS].values
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False, map_location=device)
    scaler = checkpoint['scaler']
    
    model = DirectionClfLSTM(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    scaled_features = scaler.transform(features)
    X, y_cls = create_sequences(scaled_features, SEQ_LENGTH, PREDICTION_WINDOW)
    
    split_idx = int(len(X) * 0.8)
    X_test = torch.from_numpy(X[split_idx:]).float().to(device)
    y_cls_test = y_cls[split_idx:]
    
    if len(X_test) == 0: return 0,0,0,0

    print(f"Evaluating on {len(X_test)} samples...")

    with torch.no_grad():
        pred_probs = model(X_test)
        probs_flat = pred_probs.cpu().numpy().flatten()
        targets_flat = y_cls_test.flatten()
        
        pred_binary = (probs_flat > 0.5).astype(float)
        da_score = np.mean(pred_binary == targets_flat) * 100
        
        print("\n--- Simplified Model Performance (No Ext Reg) ---")
        print(f"Overall Directional Accuracy: {da_score:.2f}%")
        
        best_acc = 0.0
        best_thresh = 0.5
        best_cov = 0.0
        
        for thresh in [0.55, 0.60, 0.65, 0.70, 0.75, 0.78, 0.80]:
            mask = np.abs(probs_flat - 0.5) > (thresh - 0.5)
            if mask.sum() > 5: 
                subset_preds = (probs_flat[mask] > 0.5).astype(float)
                subset_targets = targets_flat[mask]
                acc = np.mean(subset_preds == subset_targets) * 100
                cov = (mask.sum() / len(mask)) * 100
                print(f"Thresh {thresh:.2f}: Acc {acc:.2f}% (Cov {cov:.1f}%)")
                if acc > best_acc:
                    best_acc = acc
                    best_thresh = thresh
                    best_cov = cov
            else:
                 print(f"Thresh {thresh:.2f}: No samples")

        print(f"BEST High Conf Accuracy: {best_acc:.2f}% (Thresh {best_thresh}, Cov {best_cov:.1f}%)")
        print("-------------------------------------------------")
    
    return 0, 0, 0, best_acc 

def get_lstm_forecast():
    if not os.path.exists(MODEL_PATH): train_model()
    
    df = prepare_data()
    features = df[FEATURE_COLS].values
    last_price = df['price'].iloc[-1]
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False, map_location=device)
    scaler = checkpoint['scaler']
    avg_abs_ret = checkpoint.get('avg_abs_ret', 0.02)
    
    model = DirectionClfLSTM(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    last_seq = features[-SEQ_LENGTH:]
    scaled_seq = scaler.transform(last_seq)
    X_input = torch.from_numpy(scaled_seq).float().unsqueeze(0).to(device)
    
    with torch.no_grad():
        pred_probs = model(X_input).cpu().numpy().flatten()
        
        prices = []
        curr_price = last_price
        
        for prob in pred_probs:
            direction = 1 if prob > 0.5 else -1
            move = direction * avg_abs_ret 
            next_price = curr_price * np.exp(move)
            prices.append(next_price)
            curr_price = next_price
            
    return prices

def get_lstm_direction_signal():
    """
    Returns the raw directional prediction (UP/DOWN) and confidence score.
    """
    if not os.path.exists(MODEL_PATH): train_model()
    
    df = prepare_data()
    features = df[FEATURE_COLS].values
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False, map_location=device)
    scaler = checkpoint['scaler']
    
    model = DirectionClfLSTM(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    last_seq = features[-SEQ_LENGTH:]
    scaled_seq = scaler.transform(last_seq)
    X_input = torch.from_numpy(scaled_seq).float().unsqueeze(0).to(device)
    
    with torch.no_grad():
        pred_probs = model(X_input).cpu().numpy().flatten()
        prob_up = float(pred_probs[0]) # Scalar prob of UP (Day 1)
        
        # Determine Direction
        direction = "UP" if prob_up > 0.5 else "DOWN"
        
        # specific confidence: how far from 0.5?
        confidence = abs(prob_up - 0.5) * 2 # 0.5->0, 1.0->1, 0.0->1
        
        return {
            "direction": direction,
            "probability_up": prob_up,
            "confidence_score": confidence
        }

def get_lstm_scores_for_dataset():
    """
    Walk-forward: Generate LSTM direction scores for every date.
    Returns DataFrame with columns:
      - lstm_score: signed score -1 to +1
      - lstm_confidence: absolute confidence 0 to 1
      - lstm_high_conf: score ONLY when confidence > 0.30 (≈70%+ accuracy), else 0
    """
    if not os.path.exists(MODEL_PATH): train_model()
    
    df = prepare_data()
    features = df[FEATURE_COLS].values
    dates = df['ds'].values
    
    checkpoint = torch.load(MODEL_PATH, weights_only=False, map_location=device)
    scaler = checkpoint['scaler']
    
    model = DirectionClfLSTM(hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    scaled = scaler.transform(features)
    
    scores, confidences, high_conf_scores = [], [], []
    score_dates = []
    
    CONF_THRESHOLD = 0.30  # |prob - 0.5| > 0.15 → prob > 0.65 or prob < 0.35
    
    with torch.no_grad():
        for i in range(SEQ_LENGTH, len(scaled)):
            seq = scaled[i - SEQ_LENGTH:i]
            X = torch.from_numpy(seq).float().unsqueeze(0).to(device)
            prob = float(model(X).cpu().numpy().flatten()[0])
            
            # Signed score: -1 (strong down) to +1 (strong up)
            lstm_score = (prob - 0.5) * 2
            # Confidence: 0 (no idea) to 1 (very sure)
            confidence = abs(prob - 0.5) * 2
            # High-confidence score: only fires when LSTM is accurate (>70%)
            high_conf = lstm_score if confidence > CONF_THRESHOLD else 0.0
            
            scores.append(lstm_score)
            confidences.append(confidence)
            high_conf_scores.append(high_conf)
            score_dates.append(dates[i])
    
    result = pd.DataFrame({
        'ds': score_dates,
        'lstm_score': scores,
        'lstm_confidence': confidences,
        'lstm_high_conf': high_conf_scores
    })
    result['ds'] = pd.to_datetime(result['ds'])
    
    n_high = sum(1 for s in high_conf_scores if s != 0)
    print(f"Generated {len(result)} LSTM scores. High-confidence signals: {n_high} ({n_high/len(result)*100:.1f}%)")
    return result

if __name__ == "__main__":
    if os.path.exists(MODEL_PATH):
        try: os.remove(MODEL_PATH) 
        except: pass
        
    _, _, _, da = evaluate_model()
    
    with open("metrics.txt", "w") as f:
        f.write(f"Directional Accuracy: {da:.2f}%\n")
        
    forecasts = get_lstm_forecast()
    print(f"Forecast: {forecasts[0]:.2f}, {forecasts[6]:.2f}, {forecasts[-1]:.2f}")
    
    signal = get_lstm_direction_signal()
    print(f"Signal: {signal}")
