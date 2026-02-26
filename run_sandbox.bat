@echo off
echo Setting up Agri-Oracle Sandbox...

REM Install dependencies
pip install -r requirements.txt

echo Starting Backend API...
start "Agri-Oracle Backend" cmd /c "uvicorn forecasting_engine.main:app --host 127.0.0.1 --port 8001"

echo Starting Frontend...
cd frontend
python -m http.server 8000
