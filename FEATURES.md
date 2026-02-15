# Agri-Oracle: Comprehensive Feature Documentation

Agri-Oracle is an advanced agricultural price forecasting platform that combines ensemble machine learning (Prophet + LSTM), satellite data analysis (NDVI), and real-time policy simulation to predict commodity prices with high accuracy and explainability.

## 1. Forecasting Engine (Backend)

The core predictive logic resides in the FastAPI backend, utilizing a sophisticated ensemble approach.

### 1.1 Model Architecture
- **Prophet (Meta):** Handles long-term trends and seasonality.
  - **Seasonality:** Modeled with Fourier order 5 (monthly period).
  - **Regressors:**
    - `transport_lag_3`: Global transport cost index lagged by 3 days.
    - `national_avg_price`: 30-day rolling average of national prices.
    - `panic_index`: User-controlled volatility multiplier.
    - `ndvi_mean`: Weekly vegetation health index from satellite data.
    - `rainfall`: Regional rainfall data (currently set to 0.0 placeholder).
- **LSTM (Long Short-Term Memory):** Predicts short-term directional movement (UP/DOWN) and magnitude.
  - **Input Features (16):**
    - Technical Indicators: `RSI`, `MACD`, `MACD Signal`, `ROC` (Rate of Change), `Bollinger Bands` (Upper, Lower, Width), `Stochastic Oscillator` (%K, %D), `CCI`, `Williams %R`.
    - Fundamental Data: `log_ret` (Log Returns), `transport_cost`, `ndvi_mean`, `ndvi_anomaly`.
  - **Output:** Directional probability (Sigmoid) + Magnitude estimation.

### 1.2 Ensemble Intelligence
The system dynamically weights predictions from both models based on confidence:
- **Confidence Thresholds:**
  - `CONF_FLOOR` (0.30) to `CONF_CEIL` (0.60).
  - Used to determine the weight of the LSTM model in the final price calculation.
- **Directional Agreement:**
  - **Agreement:** If both models predict the same direction, the forecast is boosted by up to 15% (proportional to LSTM confidence).
  - **Disagreement:** The LSTM prediction is blended with the Prophet trend based on weight.
- **Dynamic Confidence Score:**
  - Base Score: 85/100.
  - Penalties: High volatility (Panic Index) reduces confidence by ~1.5 per point.
  - Adjustments: Agreement adds up to +10%, disagreement subtracts up to -20%.

### 1.3 Policy Simulation Logic
Real-time "What-If" analysis allows immediate price impact assessment:
- **Export Ban:** Triggers a **30% price reduction** (`final_price *= 0.70`).
- **Diesel Tax:** Adds inflationary cost: `(diesel_tax * 15) / 100` per unit.
- **Subsidy:** Directly reduces consumer price: `final_price -= (price * subsidy_percent / 100)`.
- **Volatility (Panic Index):** 
  - Increases `panic_index` regressor value for Prophet.
  - Triggers "Warning" or "Critical" market status messages.

### 1.4 Price DNA (Explainability)
Every prediction is decomposed into its constituent drivers for transparency:
- **Base Trend:** The underlying long-term price trajectory.
- **Seasonality:** Cyclical monthly patterns.
- **Transport Impact:** Cost contribution from logistics.
- **Satellite Signal (NDVI):** Price influence from crop health data.
- **Market Panic:** Premium added due to volatility.
- **Policy Effects:** Explicit breakdown of Tax and Subsidy impacts.

## 2. Satellite Intelligence (NDVI Processor)

A specialized pipeline processes raw satellite imagery to extract vegetation health metrics.

- **Data Source:** Multi-band GeoTIFF files (Nashik region).
- **Processing:**
  - **GPU Acceleration:** Uses PyTorch (`torch.cuda`) for fast pixel-level operations.
  - **Cloud Masking:** Filters out invalid pixels (NaN, out-of-bounds, cloud-fill values).
  - **Weekly Aggregation:** Computes Mean and Standard Deviation for each ISO week.
- **Anomaly Detection:** Calculates deviation from the multi-year average for that specific week (Climatology).
- **Interpolation:** Handles missing weeks (e.g., due to heavy monsoon cloud cover) using linear interpolation.

## 3. Frontend Experience ("Liquid Glass")

The user interface is built with HTML5, Tailwind CSS, and Vanilla JavaScript, featuring a premium "Liquid Glass" design system.

### 3.1 Oracle Dashboard (Main View)
- **Interactive Controls:**
  - **Reference Date:** Date picker with "Quick Select" buttons (+1 Day, +1 Week, +1 Month).
  - **Policy Sliders:** Diesel Tax (0-20), Subsidy (0-50%), Volatility (0-10).
  - **Toggle:** Export Ban (On/Off).
- **Real-Time Visualization:**
  - **Price Display:** Large, color-coded price (Green for rising, Red for falling).
  - **Comparisons:** "Lock vs" feature to compare current simulation against a benchmark.
  - **Chart.js Integration:** 30-day forecast line chart with dynamic bounds.
  - **Status Indicators:** "Stable", "Warning", "Critical" based on volatility and price drops.
- **Explainability Panel:** Visual bars showing the contribution of each factor (Trend, Seasonality, etc.) to the final price.

### 3.2 Planner (Concept/Mockup)
- **Rotation Plan:** Logic for selecting previous crop (Onion, Potato, Wheat) and Soil Type (Clay, Sandy, Loamy).
- **Quick Suggest:** Heuristic-based crop recommendation based on "Wait Time" (Short/Medium/Long term).
  - *Example Logic:* Medium Term -> Potato (Hybrid).

### 3.3 Wallet (Concept/Mockup)
- **Farmer Verification:** Drag-and-drop zone for uploading crop images.
- **Blockchain Sync:** Input field for Ethereum wallet address.
- **Polygon Integration:** Simulates logging prediction hashes to the Polygon POS network for auditability.

## 4. API Specification

### Endpoint: `POST /api/predict`
**Input:** `PolicyInput` (JSON)
```json
{
  "diesel_tax": float,
  "subsidy_percent": float,
  "export_ban": bool,
  "volatility_slider": float,
  "reference_date": "YYYY-MM-DD",
  "target_date": "YYYY-MM-DD" (Optional)
}
```

**Output:** JSON
```json
{
  "commodity": "Onion",
  "baseline_prediction": float,
  "final_adjusted_price": float,
  "confidence_lower": float,
  "confidence_upper": float,
  "confidence_score": float,
  "status_message": string,
  "polygon_tx_hash": string,
  "decomposition": {
    "trend": float,
    "seasonality": float,
    "transport_impact": float,
    "ndvi_mean": float,
    ...
  },
  "forecast_trend": [
    { "date": "YYYY-MM-DD", "price": float, "lower": float, "upper": float },
    ...
  ]
}
```
