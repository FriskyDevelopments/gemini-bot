import os
import google.generativeai as genai
from telegram.ext import ApplicationBuilder

# --- CLOUD CONFIG ---
# Instead of input(), we pull from Render's Environment Variables
gemini_key = os.getenv("GEMINI_API_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")

if not gemini_key or not telegram_token:
    print("❌ ERROR: Missing GEMINI_API_KEY or TELEGRAM_TOKEN in Render Environment Variables.")
    exit(1)

genai.configure(api_key=gemini_key)

def initialize_pup():
    print("🐾 --- PUP IS LIVE ON RENDER --- 🐾")
    # Add the rest of your bot logic here

if __name__ == "__main__":
    initialize_pup()
    # Your bot starting logic (app.run_polling(), etc.)
