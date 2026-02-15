# 🌾 Agri-Oracle: AI-Powered Price Forecasting & Policy Simulation

![Status](https://img.shields.io/badge/Status-Prototype-green)
![Tech](https://img.shields.io/badge/Stack-FastAPI%20|%20Prophet%20|%20VanillaJS-blue)

**Agri-Oracle** is an advanced agricultural forecasting platform designed to predict commodity prices (specifically Onion) using a hybrid **Prophet + LSTM** ensemble model. It features a "Liquid Glass" dashboard for real-time visualization and a robust **Policy Simulation Engine** to test the impact of government interventions.

## 🚀 Key Features

### 1. 🧠 Hybrid Forecasting Engine
-   **Ensemble Model:** Combines **Facebook Prophet** (for trend/seasonality) with **LSTM** (for short-term directional accuracy).
-   **30-Day Forecast:** Generates a realistic daily price path with confidence intervals.
-   **Price DNA:** Decomposes every prediction into its core drivers:
    -   📉 **Base Trend:** Long-term market direction.
    -   🗓️ **Seasonality:** Monthly/Weekly cyclical patterns.
    -   🚚 **Transport Costs:** Impact of logistics/fuel prices.
    -   🛰️ **Satellite (NDVI):** Crop health signals from Sentinel-2 data.

### 2. 🎛️ Policy Simulation ("What-If" Analysis)
Empowers policymakers to test interventions in real-time:
-   **Diesel Tax:** Adjust fuel tax to see inflationary impact on transport costs.
-   **Export Ban:** Simulate the price crash resulting from border closures.
-   **Subsidy:** Apply direct consumer subsidies to lower retail prices.
-   **Panic Index:** Model market volatility and fear-driven price spikes.

### 3. 🌐 "Liquid Glass" Dashboard
-   **UI Design:** Premium, glassmorphism-based interface using Tailwind CSS.
-   **Interactive Charts:** Dynamic Chart.js visualization that responds to sliders instantly.
-   **Transparency:** Blockchain-inspired "Transaction Hash" logging (Simulated via Polygon) for audit trails.

---

## 🛠️ Tech Stack

### **Backend (Python)**
-   **FastAPI:** High-performance API server.
-   **Prophet:** Additive regression model for time-series forecasting.
-   **PyTorch/LSTM:** Deep learning for residual error correction.
-   **Pandas/NumPy:** Data processing and vectorized operations.

### **Frontend (Web)**
-   **Vanilla JS:** Lightweight, framework-free interaction logic.
-   **Tailwind CSS:** Modern utility-first styling.
-   **Chart.js:** Recursive rendering for forecast series.

---

## 💻 Installation & Setup

### Prerequisites
-   Python 3.9+
-   Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/agri-oracle.git
cd agri-oracle
```

### 2. Backend Setup
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the System

**Terminal 1: Start the Backend API**
```bash
uvicorn forecasting_engine.main:app --reload --port 8001
```
*The API will start at `http://127.0.0.1:8001`*

**Terminal 2: Start the Frontend**
```bash
cd frontend
python -m http.server 8000
```
*Open your browser to `http://localhost:8000`*

---

## 📂 Project Structure

```
├── forecasting_engine/     # Python Backend & ML Models
│   ├── main.py             # FastAPI Application & Logic
│   ├── lstm_engine.py      # LSTM Model Definition
│   ├── train_model.py      # Training Script for Prophet
│   └── *.csv / *.json      # Data and Model Weights
├── frontend/               # Web Interface
│   ├── index.html          # Main Dashboard
│   ├── script.js           # UI Logic & API Integration
│   └── styles.css          # Tailwind Customizations
├── Daily Mandi Prices/     # Historical Price Data
└── NVDI satellite Onion/   # Satellite Imagery Data
```

## 📜 License
MIT License
