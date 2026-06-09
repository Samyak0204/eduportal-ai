import os
import sys
from dotenv import load_dotenv

# Try importing dependencies
dependencies = [
    "streamlit",
    "pymongo",
    "google.generativeai",
    "PIL",
    "speech_recognition",
    "pyaudio",
    "pydub",
    "bcrypt",
    "streamlit_mic_recorder"
]

print("=== Dependency Check ===")
missing = []
for dep in dependencies:
    try:
        __import__(dep)
        print(f"[OK] {dep} is installed")
    except ImportError as e:
        print(f"[FAIL] {dep} is missing ({e})")
        missing.append(dep)

# Try connecting to DB
print("\n=== MongoDB Check ===")
try:
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    client.server_info() # trigger connection check
    print("[OK] MongoDB connection successful!")
except Exception as e:
    print(f"[FAIL] MongoDB connection failed: {e}")

# Try calling Gemini
print("\n=== Gemini API Check ===")
try:
    import google.generativeai as genai
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("[FAIL] GEMINI_API_KEY is not set in environment or .env file.")
    else:
        print(f"Found API key: {api_key[:6]}...{api_key[-4:] if len(api_key) > 10 else ''}")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        print("Sending test query to Gemini...")
        response = model.generate_content("Hello! Verify you are online.")
        print(f"[OK] Gemini Response: {response.text.strip()}")
except Exception as e:
    print(f"[FAIL] Gemini API check failed: {e}")
