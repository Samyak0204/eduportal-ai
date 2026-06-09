# 🎓 EduPortal AI — Setup Guide

AI-powered question evaluation portal using Streamlit, MongoDB, and Google Gemini.

---

## 📋 Prerequisites

- Python 3.9+
- MongoDB installed and running locally (via MongoDB Compass or `mongod`)
- Google Gemini API key from [AI Studio](https://aistudio.google.com/app/apikey)

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> If `pyaudio` fails on Windows, install it via:
> ```bash
> pip install pipwin && pipwin install pyaudio
> ```
> On Linux: `sudo apt-get install portaudio19-dev` first.

---

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
MONGO_URI=mongodb://localhost:27017
MONGO_DB=portal_db
SECRET_KEY=any_random_string_here
```

---

### 3. Start MongoDB

Make sure MongoDB is running locally. Via Compass: just open the app.
Or via terminal:
```bash
mongod --dbpath /data/db
```

---

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔐 Default Login Credentials

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Admin   | admin     | admin123    |
| Student | student1  | student123  |

> ⚠️ Change these after first login via the Manage Students tab.

---

## 🗂️ Project Structure

```
portal_app/
├── app.py              # Main Streamlit entry point
├── db.py               # MongoDB connection & helpers
├── gemini_eval.py      # Google Gemini evaluation engine
├── admin_pages.py      # Admin UI: upload questions, view submissions
├── student_pages.py    # Student UI: answer questions, view results
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # This file
```

---

## 🎯 Features

### Admin
- Upload questions: MCQ, Essay, Math, Code, Image-based
- Attach images to questions
- View all student submissions with Gemini evaluations
- Manage student accounts

### Student
- View all available questions
- Submit answers in 3 formats:
  - ✏️ **Text** — typed or MCQ selection
  - 🖼️ **Image** — upload handwritten/diagram answer
  - 🎙️ **Audio** — upload or record spoken answer
- Get instant Gemini evaluation with score, analysis & correct answer
- View submission history

---

## 🤖 Gemini Evaluation Output

Each evaluation includes:
- ✅ **Verdict** — Correct / Partially Correct / Incorrect
- 📊 **Score** — out of 10
- 🔍 **Analysis** — detailed breakdown
- 💡 **Correct Answer** — ideal response
- 📝 **Suggestions** — improvement tips

---

## ⚠️ Notes

- The free tier Gemini API (AI Studio) supports audio via file upload — make sure audio files are under 20MB.
- MongoDB runs locally — data persists across sessions.
- The `streamlit-mic-recorder` package enables in-browser microphone recording.
