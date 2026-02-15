
import logging
import warnings
import os
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, accuracy_score
from sklearn.preprocessing import StandardScaler

# Suppress Warnings
logging.getLogger('prophet').setLevel(logging.CRITICAL)
logging.getLogger('prophet.plot').setLevel(logging.CRITICAL)
logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'Daily Mandi Prices')
TRANSPORT_CSV_PATH = os.path.join(BASE_DIR, '..', 'commodity_transport_costs.csv')
NDVI_CSV_PATH = os.path.join(BASE_DIR, 'ndvi_weekly_nashik.csv')
OUTPUT_PLOT_PATH = os.path.join(BASE_DIR, 'predicted_vs_real_plot.png')
LAG_DAYS = 3
HOLIDAY_COUNTRY = 'IN'

# LSTM Config (MUST MATCH lstm_engine.py)
SEQ_LENGTH = 10 
PREDICTION_WINDOW = 30
HIDDEN_SIZE = 64
NUM_LAYERS = 2
EPOCHS = 100
LEARNING_RATE = 0.001
INPUT_SIZE = 16
FEATURE_COLS = ['log_ret', 'rsi', 'macd', 'macd_signal', 'roc', 'national_log_ret', 
                'transport_cost', 'ndvi_mean', 'ndvi_anomaly',
                'bb_upper', 'bb_lower', 'bb_width', 'stoch_k', 'stoch_d', 'cci', 'willr']

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- LSTM Class (Identical) ---
class DirectionClfLSTM(nn.Module):
    def __init__(self, input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=30):
        super(DirectionClfLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 32), nn.BatchNorm1d(32), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(32, output_size), nn.Sigmoid()
        )
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        last_out = out[:, -1, :]
        return self.classifier(last_out)

# --- Data Helpers ---
def load_and_preprocess_data():
    import glob
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not all_files: return None
    combined = []
    for f in all_files:
        try:
            temp = pd.read_csv(f)
            temp = temp[temp['Commodity'].str.contains('Onion', case=False, na=False)]
            if not temp.empty: combined.append(temp)
        except: pass
    if not combined: return None
    
    df = pd.concat(combined, ignore_index=True)
    df['ds'] = pd.to_datetime(df['Arrival_Date'], errors='coerce')
    df['y'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    df = df.dropna(subset=['ds', 'y'])
    daily_df = df.groupby('ds')['y'].mean().reset_index().sort_values('ds')
    
    # Transport
    if os.path.exists(TRANSPORT_CSV_PATH):
        t_df = pd.read_csv(TRANSPORT_CSV_PATH)
        t_df['ds'] = pd.to_datetime(t_df['Date'], dayfirst=True, errors='coerce')
        t_df['transport_cost'] = pd.to_numeric(t_df['Global_Transport_Cost_Index'], errors='coerce')
        t_df = t_df[['ds', 'transport_cost']].dropna()
        daily_df = pd.merge(daily_df, t_df, on='ds', how='left')
        daily_df['transport_cost'] = daily_df['transport_cost'].ffill().bfill().fillna(0)
    else: daily_df['transport_cost'] = 0
    daily_df[f'transport_lag_{LAG_DAYS}'] = daily_df['transport_cost'].shift(LAG_DAYS)
    
    # Placeholders
    daily_df['national_avg_price'] = daily_df['y'].rolling(30, min_periods=1).mean()
    daily_df['rainfall'] = 0.0
    daily_df['panic_index'] = 0.0
    
    # NDVI
    if os.path.exists(NDVI_CSV_PATH):
        ndvi_df = pd.read_csv(NDVI_CSV_PATH)
        ndvi_df['ds'] = pd.to_datetime(ndvi_df['ds'])
        ndvi_df = ndvi_df.sort_values('ds')
        daily_df = daily_df.sort_values('ds')
        daily_df = pd.merge_asof(daily_df, ndvi_df[['ds', 'ndvi_mean', 'ndvi_anomaly']], on='ds', direction='backward')
        daily_df['ndvi_mean'] = daily_df['ndvi_mean'].fillna(0.0)
        daily_df['ndvi_anomaly'] = daily_df['ndvi_anomaly'].fillna(0.0)
    else:
        daily_df['ndvi_mean'] = 0.0
        daily_df['ndvi_anomaly'] = 0.0

    daily_df = daily_df.dropna()
    return daily_df

def calculate_indicators(df):
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
    df['ma20'] = df['y'].rolling(window=20).mean()
    df['std20'] = df['y'].rolling(window=20).std()
    df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['ma20']
    low14 = df['y'].rolling(window=14).min()
    high14 = df['y'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['y'] - low14) / (high14 - low14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    tp = (df['y'] + df['y'] + df['y']) / 3
    sma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df['cci'] = (tp - sma_tp) / (0.015 * mad_tp)
    df['willr'] = -100 * ((high14 - df['y']) / (high14 - low14))
    df['price'] = df['y']
    df['log_ret'] = np.log(df['price'] / df['price'].shift(1))
    df['national_log_ret'] = df['log_ret']
    return df.fillna(0)

def create_sequences(data_values, seq_length, prediction_window=30):
    xs, ys_cls = [], []
    for i in range(len(data_values) - seq_length - prediction_window + 1):
        x = data_values[i:(i + seq_length)]
        y_ret = data_values[(i + seq_length):(i + seq_length + prediction_window), 0] # log_ret is idx 0
        y_dir = (y_ret > 0).astype(float) 
        xs.append(x)
        ys_cls.append(y_dir)
    return np.array(xs), np.array(ys_cls)

def run_evaluation():
    print("Loading data...")
    df = load_and_preprocess_data()
    df = calculate_indicators(df)
    
    # Split
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    print(f"Train samples: {len(train_df)}, Test samples: {len(test_df)}")
    
    # --- 1. Train Prophet ---
    print("Training Prophet on Train Set...")
    m = Prophet(seasonality_mode='multiplicative', changepoint_prior_scale=0.5, seasonality_prior_scale=10.0)
    m.add_country_holidays(country_name=HOLIDAY_COUNTRY)
    m.add_regressor(f'transport_lag_{LAG_DAYS}')
    m.add_regressor('national_avg_price')
    m.add_regressor('rainfall')
    m.add_regressor('panic_index')
    m.add_regressor('ndvi_mean')
    m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    m.fit(train_df)
    
    # Predict with Prophet
    future = test_df[['ds', f'transport_lag_{LAG_DAYS}', 'national_avg_price', 'rainfall', 'panic_index', 'ndvi_mean']].copy()
    forecast = m.predict(future)
    y_pred_prophet = forecast['yhat'].values
    y_true = test_df['y'].values
    dates = test_df['ds'].values
    
    # --- 2. Train LSTM ---
    print("Training LSTM on Train Set...")
    train_features = train_df[FEATURE_COLS].values
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(train_features)
    X_train, y_app = create_sequences(scaled_train, SEQ_LENGTH, PREDICTION_WINDOW)
    
    X_train_t = torch.from_numpy(X_train).float().to(device)
    y_train_t = torch.from_numpy(y_app).float().to(device)
    
    lstm_model = DirectionClfLSTM().to(device)
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(lstm_model.parameters(), lr=LEARNING_RATE)
    lstm_model.train()
    for _ in range(EPOCHS):
        pred_probs = lstm_model(X_train_t)
        loss = criterion(pred_probs, y_train_t)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
    lstm_model.eval()
    
    # Predict with LSTM on Test
    full_features = df[FEATURE_COLS].values
    full_scaled = scaler.transform(full_features)
    
    lstm_conf_aligned = np.zeros(len(test_df))
    lstm_dir_aligned = np.zeros(len(test_df)) # 1 for UP, 0 for DOWN
    
    with torch.no_grad():
        for i in range(len(test_df)):
            abs_idx = split_idx + i
            if abs_idx - SEQ_LENGTH < 0: continue
            
            seq = full_scaled[abs_idx - SEQ_LENGTH : abs_idx]
            X_in = torch.from_numpy(seq).float().unsqueeze(0).to(device)
            prob_vec = lstm_model(X_in).cpu().numpy().flatten()
            
            prob_day1 = prob_vec[0]
            confidence = abs(prob_day1 - 0.5) * 2
            direction = 1 if prob_day1 > 0.5 else 0
            
            lstm_conf_aligned[i] = confidence
            lstm_dir_aligned[i] = direction

    # --- 3. Ensemble (Sniper Mode) ---
    y_pred_combined = []
    
    CONF_FLOOR = 0.30
    CONF_CEIL = 0.60
    
    ref_prices = df['y'].shift(1).iloc[split_idx:].values
    
    for i in range(len(test_df)):
        prophet_price = y_pred_prophet[i]
        ref_price = ref_prices[i]
        
        lstm_conf = lstm_conf_aligned[i]
        lstm_dir_up = (lstm_dir_aligned[i] == 1)
        prophet_change = prophet_price - ref_price
        prophet_dir_up = (prophet_change > 0)
        
        if lstm_conf <= CONF_FLOOR:
            lstm_weight = 0.0
        elif lstm_conf >= CONF_CEIL:
            lstm_weight = 1.0
        else:
            lstm_weight = (lstm_conf - CONF_FLOOR) / (CONF_CEIL - CONF_FLOOR)
            
        prophet_weight = 1.0 - lstm_weight
        magnitude = max(abs(prophet_change), ref_price * 0.005)
        
        if lstm_weight == 0:
            final_price = prophet_price
        elif prophet_dir_up == lstm_dir_up:
            final_price = ref_price + (prophet_change * (1.0 + (lstm_weight * 0.15)))
        else:
            lstm_signed = magnitude if lstm_dir_up else -magnitude
            prophet_signed = prophet_change
            blended_change = (prophet_signed * prophet_weight) + (lstm_signed * lstm_weight)
            final_price = ref_price + blended_change
            
        y_pred_combined.append(final_price)
        
    y_pred_combined = np.array(y_pred_combined)
    
    # --- 4. Plotting & Outlier Removal ---
    print("Preparing plot...")
    # Calculate residuals
    residuals = np.abs(y_true - y_pred_combined)
    threshold = np.percentile(residuals, 98) # Use 98th percentile to filter top 2% outliers
    mask = residuals < threshold
    
    plt.figure(figsize=(14, 7))
    plt.plot(dates[mask], y_true[mask], label='Actual Price', color='black', alpha=0.6, linewidth=1)
    plt.plot(dates[mask], y_pred_combined[mask], label='Ensemble Prediction (Sniper Mode)', color='#00aaff', alpha=0.8, linewidth=1.5)
    
    plt.title('Onion Price Prediction vs Actual (Test Set) - 98% Data Coverage', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (INR/Quintal)', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.savefig(OUTPUT_PLOT_PATH)
    print(f"Plot saved to {OUTPUT_PLOT_PATH}")

if __name__ == "__main__":
    run_evaluation()
