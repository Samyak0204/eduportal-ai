import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

models_to_test = [
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash"
]

for model_name in models_to_test:
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! Verify you are online.")
        print(f"✅ Success with {model_name}: {response.text.strip()}")
        break
    except Exception as e:
        print(f"❌ Failed with {model_name}: {e}\n")
