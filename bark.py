import os
import google.generativeai as genai
import urllib.request, urllib.parse

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = "You are Geminipupbot, the friendly and engaging host of the 'Pup Lounge'. Give a warm, concise welcome message to start the conversation. Keep it under 40 words and invite members to introduce themselves or ask a question. Be welcoming but not over the top."

    response = model.generate_content(prompt)
    msg = response.text

    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = "-1003446305734"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
    urllib.request.urlopen(url, data=data, timeout=10)
    print("Successfully sent greeting to the lounge!")
except Exception as e:
    print(f"Error: {e}")
