import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WhatsAppNotifier")

load_dotenv()

class WhatsAppNotifier:
    """
    Handles WhatsApp message delivery using Twilio SDK.
    """
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_SID")
        self.auth_token = os.getenv("TWILIO_TOKEN")
        self.from_whatsapp_number = os.getenv("TWILIO_PHONE")
        
        # Initialize client only if credentials exist
        if all([self.account_sid, self.auth_token]):
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized.")
        else:
            self.client = None
            logger.warning("Twilio credentials missing. Running in MOCK mode.")

    def send_alert(self, to_phone: str, message_text: str) -> bool:
        """
        Sends a WhatsApp message via Twilio.
        """
        # Sanitize: strip spaces and ensure whatsapp: prefix
        clean_phone = to_phone.replace(" ", "").strip()
        to_number = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
        
        from_phone = (self.from_whatsapp_number or "").replace(" ", "").strip()
        from_number = f"whatsapp:{from_phone}" if from_phone and not from_phone.startswith("whatsapp:") else from_phone
        
        if not self.client:
            logger.info(f"[MOCK SEND] To: {to_number} | Message: {message_text}")
            return True

        try:
            message = self.client.messages.create(
                body=message_text,
                from_=from_number,
                to=to_number
            )
            logger.info(f"Message sent successfully! SID: {message.sid}")
            return True
        except TwilioRestException as e:
            logger.error(f"Failed to send WhatsApp message via Twilio: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return False
