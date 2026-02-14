from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

class SignalEnum(str, Enum):
    SELL = "SELL"
    HOLD = "HOLD"
    BUY = "BUY"
    WARNING = "WARNING"

class PredictionData(BaseModel):
    """
    Standard data contract for crop price predictions.
    This adapter decouples the model output from the bot logic.
    """
    crop_name: str = Field(..., description="Name of the agricultural crop")
    signal: SignalEnum = Field(..., description="Actionable signal (SELL, HOLD, BUY, WARNING)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from the model (0.0 to 1.0)")
    raw_reason: str = Field(..., description="Human-readable reason or raw model output summary")
    days_until_change: int = Field(..., description="Estimated days before the market shifts")
    
    # New Prediction Model Details
    predicted_price: Optional[float] = Field(None, description="The predicted price of the crop")
    crash_spike_type: Optional[str] = Field(None, description="Indicates if a 'CRASH' or 'SPIKE' is predicted")
    
    # New Fields for Batch Logic and Trigger
    should_notify: bool = Field(False, description="Explicit trigger flag: If True, send WhatsApp alerts. If False, just ingest data.")
    recipient_phones: List[str] = Field(default_factory=list, description="List of phone numbers to receive the alert")

    class Config:
        schema_extra = {
            "example": {
                "crop_name": "Onion",
                "signal": "SELL",
                "confidence_score": 0.85,
                "raw_reason": "Supply surge detected",
                "days_until_change": 2,
                "predicted_price": 45.50,
                "crash_spike_type": "CRASH",
                "should_notify": True,
                "recipient_phones": ["1234567890", "0987654321"]
            }
        }
