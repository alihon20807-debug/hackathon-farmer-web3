from forecasting_engine.main import app, PolicyInput
import asyncio

async def test_prediction():
    print("Testing /api/predict endpoint...")
    
    # Mock Policy
    policy = PolicyInput(
        diesel_tax=0,
        subsidy_percent=0,
        export_ban=False,
        volatility_slider=0,
        reference_date="2024-03-01",
        target_date="2024-03-02"
    )
    
    # Manually invoke startup event to load models
    await app.router.startup()
    
    try:
        response = await app.router.routes[-1].endpoint(policy) # Assuming predict_price is last route? No, fragile.
        # Better: just call the function directly if possible, or use TestClient
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Need to startup properly
        with TestClient(app) as client:
            resp = client.post("/api/predict", json=policy.dict())
            if resp.status_code == 200:
                data = resp.json()
                print("Success!")
                print("LSTM Direction:", data.get("lstm_direction"))
            else:
                print("Failed:", resp.text)
                
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    # Just import and run the function for a quick check
    pass
