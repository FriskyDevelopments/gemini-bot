import os
import google.generativeai as genai
import urllib.request, urllib.parse

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-pro')

    prompt = "You are Geminipupbot, the charismatic, playful, and energetic pup host of the 'Pup Lounge'! Say an energetic, unprompted greeting to start the party and get people typing. Ask who wants a treat or who wants to play! Keep it short and engaging, under 40 words! Use pup terminology naturally."

    response = model.generate_content(prompt)
    msg = response.text

    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = "-1003446305734"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
    urllib.request.urlopen(url, data=data)
    print("Successfully barked into the lounge!")
except Exception as e:
    print(f"Error: {e}")
