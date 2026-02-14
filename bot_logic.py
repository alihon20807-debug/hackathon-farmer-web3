from intake_adapter import PredictionData, SignalEnum

class MessageGenerator:
    """
    Enhanced MessageGenerator that creates dynamic, context-aware notifications.
    It adjusts tone and urgency based on prediction data.
    """
    
    def __init__(self):
        # Base templates for different signals
        self.base_templates = {
            SignalEnum.SELL: "Market prices for {crop} are expected to drop.",
            SignalEnum.HOLD: "Prices for {crop} are expected to remain stable.",
            SignalEnum.BUY: "Prices for {crop} are low but expected to rise.",
            SignalEnum.WARNING: "Unusual activity detected for {crop}."
        }
        
        # Urgency modifiers based on days
        self.urgency_cues = {
            0: "🚨 CRITICAL: Action required TODAY.",
            1: "⚠️ URGENT: Action recommended by TOMORROW.",
            2: "⏰ NOTICE: Market shift expected in 2 days."
        }

    def _get_prefix(self, data: PredictionData) -> str:
        # Add high confidence prefix
        prefix = ""
        if data.confidence_score > 0.9:
            prefix += "✅ High Confidence | "
        
        # Add urgency cue
        prefix += self.urgency_cues.get(data.days_until_change, f"📅 Alert: Change in {data.days_until_change} days | ")
        return prefix

    def _get_tailored_advice(self, data: PredictionData) -> str:
        # Logic for advice based on signal and days
        if data.signal == SignalEnum.SELL:
            if data.days_until_change <= 1:
                return "Recommend selling your stock immediately to avoid losses."
            return f"Plan to sell your stock within {data.days_until_change} days."
            
        if data.signal == SignalEnum.HOLD:
            return "Keep your stock for now to maximize future value."
            
        if data.signal == SignalEnum.BUY:
            return "Good time to accumulate stock before prices rise."
            
        return f"Be prepared for changes. Reason: {data.raw_reason}."

    def get_message(self, data: PredictionData) -> str:
        """
        Dynamically assembles a natural language message.
        """
        prefix = self._get_prefix(data)
        base = self.base_templates.get(data.signal, f"Update on {data.crop_name}.")
        advice = self._get_tailored_advice(data)
        
        # Build price info if available
        price_info = ""
        if data.predicted_price:
            price_info = f"\n💰 Predicted Price: {data.predicted_price}"
        
        # Build crash/spike alert
        alert_info = ""
        if data.crash_spike_type:
            emoji = "📉" if data.crash_spike_type.upper() == "CRASH" else "📈"
            alert_info = f"\n{emoji} Market Alert: {data.crash_spike_type.upper()} expected!"

        # Final construction
        full_msg = f"{prefix}\n\n{base}{price_info}{alert_info}\n\n👉 Advice: {advice}"
        
        # Always include logic details from the model
        full_msg += f"\n\n🔍 Model Reason: {data.raw_reason}"
            
        return full_msg

# Example validation
if __name__ == "__main__":
    test_data = PredictionData(
        crop_name="Onion",
        signal=SignalEnum.SELL,
        confidence_score=0.95,
        raw_reason="Massive oversupply and market crash predicted",
        days_until_change=1,
        should_notify=True,
        recipient_phones=[]
    )
    generator = MessageGenerator()
    print(generator.get_message(test_data))
