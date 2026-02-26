# 🚀 Agri-Oracle Sandbox Quickstart

Welcome to the Agri-Oracle Sandbox! Follow these instructions to get the application up and running, and to verify everything works smoothly.

## 🏃‍♀️ How to Run

### **Option 1: Windows (Local)**
1. Open a Command Prompt or PowerShell in the `hackathon-farmer-web3` folder.
2. Run the batch script:
   ```cmd
   .\run_sandbox.bat
   ```
   *This script will automatically install dependencies, start the FastAPI Backend, and launch the Frontend.*

### **Option 2: Linux, macOS, or Cloud Sandbox (Codespaces/Replit)**
1. Open a Terminal in the `hackathon-farmer-web3` folder.
2. Make the script executable and run it:
   ```bash
   chmod +x run_sandbox.sh
   ./run_sandbox.sh
   ```

### **Accessing the App**
Once the scripts are running, you can access:
- **Frontend Dashboard**: [http://localhost:8000](http://localhost:8000)
- **FastAPI Backend Swagger Docs**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

---

## 🧪 How to Test

### **1. Verify the System is Running**
- Open your browser and go to [http://localhost:8000](http://localhost:8000). You should see the Agri-Oracle "Liquid Glass" dashboard load successfully.

### **2. Test the API Connection**
- On the dashboard, try interacting with the "Policy Simulation Engine" sliders (e.g., adjust the "Diesel Tax" or "Panic Index").
- Observe the chart to see if the **prophet-forecast** updates in real-time. This confirms the frontend is successfully talking to the Python backend.

### **3. Test the Forecasting Endpoint (Manual)**
- Navigate to the API Docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- Find the `POST /predict` endpoint and click **"Try it out"**.
- Leave the default Request Body as is (or tweak the policy flags) and click **"Execute"**.
- Check the **Server Response**: You should receive a 200 OK status with a JSON payload containing the `dates`, `prices`, and `components` (Trend, Seasonality, Transport, etc.).

### **4. Verify API Documentation**
- Keep scrolling in the Swagger Docs to review the expected schemas and models used by the `FastAPI` instance.
