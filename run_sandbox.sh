#!/bin/bash
echo "Setting up Agri-Oracle Sandbox..."

# Install dependencies if not already installed (checking if pip exists in venv or globally)
pip install -r requirements.txt

echo "Starting Backend API on port 8001..."
uvicorn forecasting_engine.main:app --host 0.0.0.0 --port 8001 &

echo "Starting Frontend on port 8000..."
cd frontend
python -m http.server 8000
