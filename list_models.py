import os
import google.generativeai as genai
with open('.env') as f:
    for line in f:
        if line.startswith('GEMINI_API_KEY='):
            genai.configure(api_key=line.strip().split('=', 1)[1])
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
