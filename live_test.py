from intake_adapter import PredictionData, SignalEnum
from bot_logic import MessageGenerator
from notifier import WhatsAppNotifier
from dotenv import load_dotenv
import os

def run_live_test(phone_number: str):
    print(f"--- Initiating Live WhatsApp Test for {phone_number} ---")
    
    # 1. Initialize components
    load_dotenv()
    generator = MessageGenerator()
    notifier = WhatsAppNotifier()
    
    # 2. Create fake prediction data (High urgency, High confidence, Critical keyword)
    fake_prediction = PredictionData(
        crop_name="Tomato",
        signal=SignalEnum.SELL,
        confidence_score=0.98,
        raw_reason="Incoming price crash due to logistics shutdown",
        days_until_change=1,
        predicted_price=15.00,
        crash_spike_type="CRASH",
        should_notify=True,
        recipient_phones=[phone_number]
    )
    
    # 3. Generate message
    message = generator.get_message(fake_prediction)
    print(f"Generated Message: {message}")
    
    # 4. Send live alert
    print("Sending live WhatsApp message via Twilio...")
    success = notifier.send_alert(phone_number, message)
    
    if success:
        print("\n✅ Live test completed successfully!")
    else:
        print("\n❌ Live test failed. Check logs for details.")

if __name__ == "__main__":
    # Using the phone number provided by the user
    target_number = "+91 7357978053"
    run_live_test(target_number)
