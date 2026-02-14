from fastapi import FastAPI, HTTPException, BackgroundTasks
from intake_adapter import PredictionData
from bot_logic import MessageGenerator
from notifier import WhatsAppNotifier
import uvicorn
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgriBot")

app = FastAPI(title="Agri-Oracle WhatsApp Chatbot")

# Initialize modules
generator = MessageGenerator()
notifier = WhatsAppNotifier()

@app.get("/")
async def root():
    return {"status": "online", "message": "Agricultural Alert Chatbot API"}

@app.post("/alert")
async def process_alert(data: PredictionData, background_tasks: BackgroundTasks):
    """
    Endpoint to receive crop predictions and send WhatsApp alerts.
    
    Logic:
    1. Always log/ingest the prediction data.
    2. Check the 'should_notify' flag. If False, skip notification.
    3. If 'should_notify' is True, send the message to all 'recipient_phones'.
    """
    logger.info(f"Received prediction for {data.crop_name}: {data.signal} (Confidence: {data.confidence_score})")

    if not data.should_notify:
        return {
            "success": True,
            "status": "Data ingested, but notification was NOT triggered.",
            "should_notify": False
        }

    if not data.recipient_phones:
        return {
            "success": False,
            "status": "Notification triggered but no recipient phones provided.",
            "should_notify": True
        }

    try:
        # 1. Generate the farmer-friendly message
        message = generator.get_message(data)
        
        # 2. Queue notifications for all recipients
        for phone in data.recipient_phones:
            background_tasks.add_task(notifier.send_alert, phone, message)
            
        return {
            "success": True,
            "message_prepared": message,
            "recipients_count": len(data.recipient_phones),
            "action": "Notifications queued in background",
            "confidence": f"{data.confidence_score * 100}%"
        }
        
    except Exception as e:
        logger.error(f"Error processing alert: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
