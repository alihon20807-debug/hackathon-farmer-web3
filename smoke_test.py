from fastapi.testclient import TestClient
from app import app
import json

client = TestClient(app)

def test_batch_notifications():
    print("--- Testing Batch Notifications & Trigger Logic ---")
    
    # 1. Test: should_notify=False
    print("\nTest 1: should_notify=False (Data ingestion only)")
    payload_no_trigger = {
        "crop_name": "Rice",
        "signal": "HOLD",
        "confidence_score": 0.70,
        "raw_reason": "Stable weather",
        "days_until_change": 10,
        "should_notify": False,
        "recipient_phones": ["1112223333"]
    }
    response1 = client.post("/alert", json=payload_no_trigger)
    print(f"Response: {response1.json()['status']}")
    assert response1.json()["should_notify"] is False

    # 2. Test: should_notify=True with multiple numbers
    print("\nTest 2: should_notify=True with 2 recipients")
    payload_batch = {
        "crop_name": "Wheat",
        "signal": "WARNING",
        "confidence_score": 0.88,
        "raw_reason": "Sudden frost detected",
        "days_until_change": 1,
        "should_notify": True,
        "recipient_phones": ["1234567890", "0987654321"]
    }
    response2 = client.post("/alert", json=payload_batch)
    print(f"Response: {response2.json()['action']} for {response2.json()['recipients_count']} recipients")
    assert response2.json()["recipients_count"] == 2
    assert "Sudden frost" in response2.json()["message_prepared"]

    # 3. Test: Full payload with predicted price and crash alert
    print("\nTest 3: Full payload with price and crash alert")
    payload_full = {
        "crop_name": "Onion",
        "signal": "SELL",
        "confidence_score": 0.95,
        "raw_reason": "Massive oversupply and market crash predicted",
        "days_until_change": 1,
        "predicted_price": 12.50,
        "crash_spike_type": "CRASH",
        "should_notify": True,
        "recipient_phones": ["1234567890"]
    }
    response3 = client.post("/alert", json=payload_full)
    msg = response3.json()["message_prepared"]
    print(f"Prepared Message:\n{msg}")
    assert "Predicted Price: 12.5" in msg
    assert "Market Alert: CRASH expected!" in msg
    assert "Model Reason:" in msg

    print("\n--- All Batch & Trigger Tests Passed! ---")

if __name__ == "__main__":
    try:
        test_batch_notifications()
    except Exception as e:
        print(f"Batch test failed: {e}")
