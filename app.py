import os
import requests
import time
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq
from gtts import gTTS
from dotenv import load_dotenv
from langdetect import detect

# Load all keys from the .env file
load_dotenv()

# --- THE PATH FIX ---
# This forces Python to find the exact folder where app.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

# Explicitly tell Flask where the static folder is
app = Flask(__name__, static_folder=STATIC_DIR)

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    num_media = int(request.form.get('NumMedia', 0))
    
    if num_media > 0:
        media_url = request.form.get('MediaUrl0')
        local_audio_path = os.path.join(BASE_DIR, "farmer_query.ogg")
        
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        response = requests.get(media_url, auth=(twilio_sid, twilio_token))
        
        with open(local_audio_path, 'wb') as f:
            f.write(response.content)
            
        try:
            with open(local_audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                  file=("farmer_query.ogg", file.read(), "audio/ogg"), 
                  model="whisper-large-v3", 
                )
            farmer_text = transcription.text
            print(f"\n--- AUDIO RECEIVED ---")
            print(f"Farmer asked: {farmer_text}")
            
            try:
                detected_lang = detect(farmer_text)
                print(f"Detected language code: {detected_lang}")
            except Exception as e:
                print(f"Language detection failed. Defaulting to English.")
                detected_lang = 'en'
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful agricultural assistant. Answer the farmer's question based on your knowledge of farming best practices, weather patterns, and market trends. Keep your response actionable and Provide a VERY SHORT and consice/direct solution to the farmer's query. MAXIMUM 2 SENTENCES if not less . IMPORTANT: Reply in the EXACT SAME LANGUAGE as the prompt.",
                    },
                    {
                        "role": "user",
                        "content": farmer_text,
                    }
                ],
                model="llama-3.1-8b-instant", 
            )
            
            bot_reply = chat_completion.choices[0].message.content
            print(f"Bot reply: {bot_reply}\n----------------------\n")
            
            # Generate a completely unique filename using the current time
            unique_filename = f"response_{int(time.time())}.mp3"
            
            # --- THE SAVE PATH FIX ---
            # Force gTTS to save in the absolute STATIC_DIR
            response_audio_path = os.path.join(STATIC_DIR, unique_filename)
            
            tts = gTTS(text=bot_reply, lang=detected_lang) 
            tts.save(response_audio_path)
            
            host = request.host_url.replace("http://", "https://")
            public_audio_url = f"{host}static/{unique_filename}"
            print(f"Sending audio URL to Twilio: {public_audio_url}")

            resp = MessagingResponse()
            msg = resp.message()
            msg.media(public_audio_url)
            return str(resp)

        except Exception as e:
            print(f"Error during AI processing: {e}")
            resp = MessagingResponse()
            resp.message("Sorry, I had trouble processing that. Please try again.")
            return str(resp)
    else:
        resp = MessagingResponse()
        resp.message("Please send a voice note with your agricultural query!")
        return str(resp)

if __name__ == '__main__':
    app.run(port=5000, debug=True)