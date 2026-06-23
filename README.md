# 🎓 EduPortal AI — Setup & Developer Guide

**EduPortal AI** is a premium, AI-powered academic evaluation and proctored examination platform built using **Flask**, **MongoDB**, and **Google Gemini (gemini-2.5-flash)**. It supports multi-format student answers (Text, Audio, Webcam Image, and QR Companion mobile uploads) with automatic grading and AI assessment.

---

## 🎯 Key Features

### 🔐 Security & Anti-Cheating
- **Simulated OTP Login**: Verifies credentials and generates a 6-digit login OTP (printed to console for local simulation).
- **Single Active Session Restriction**: Instantly logs out or invalidates old sessions if a student attempts to log in from a different window or device.
- **Lockdown Browser Integration**: 
  - Dynamic verification of exam session tokens.
  - Heartbeat status checks to ensure the client stays online and focused.
  - Logs proctoring violations (e.g., focus loss, secondary display detection, forbidden processes).
  - Integrates direct webcam verification inside the exam window.

### 📋 Exams & Grading
- **Multi-Format Answers**: Students can submit written text, capture photos via webcam, record audio using their microphone, or upload via their mobile device.
- **QR Code Mobile Upload Companion**: Renders a short-lived tokenized QR code. Students scan this on their phone, take a picture of their handwritten paper, and upload it directly. The desktop exam page polls the DB and auto-updates when received.
- **Instant MCQ Auto-Grading**: Programmatic grading of Single & Multi-Select MCQs with proportional credit subset scoring (no Gemini quota wasted on MCQs).
- **Centralized Gemini AI Evaluator**: Comprehensive evaluation grading (Verdict, Score, Analysis, Suggestions) processed on request by the Admin.

---

## 🗂️ Project Structure

```
login_codex/
├── app.py                   # Main Flask application (routes, session manager, endpoint APIs)
├── db.py                    # MongoDB connectors, schema indexes, security tokens, and queries
├── gemini_eval.py           # Gemini evaluation engine for grading submissions
├── salesforce_questions.py  # Seed questions imported from Salesforce templates
├── requirements.txt         # Python project package dependencies
├── .env.example             # Configuration environment variable template
├── .gitignore               # Excludes virtualenvs, cache folders, and local secrets
├── templates/               # Frontend Jinja2 templates (admin, student, base, mobile_upload, login)
│   ├── base.html            # Main boilerplate layout (SEO metas, fonts, global styles)
│   ├── login.html           # Login screen with OTP input form
│   ├── student.html         # Student Test Room workspace and submission history
│   ├── admin.html           # Admin dashboard: question editor, session monitors, evaluation center
│   └── mobile_upload.html   # Mobile-friendly capture page for QR upload companion
├── static/                  # Shared web assets
│   ├── css/style.css        # Premium dark glassmorphism theme and animations
│   ├── js/                  # Injected scripts for proctoring checks and webcam
│   └── audio/               # Sounds for alerts and countdown timers
└── scratch/                 # Integration test suite and scratch utilities
```

---

## 📋 Prerequisites

- **Python 3.9+**
- **MongoDB** running locally (e.g., through MongoDB Compass or `mongod` service)
- **Google Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note on Windows Audio**: If your python environment fails to compile audio features, make sure `pyaudio` dependencies are satisfied.

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your actual **Gemini API Key**:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
FLASK_SECRET_KEY=eduportal_ai_premium_secret_key_98765
MONGO_URI=mongodb://localhost:27017
MONGO_DB=portal_db
```

### 3. Start MongoDB
Ensure MongoDB is running locally on `localhost:27017`.

### 4. Run the Web Server
Launch the Flask development server:
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🔐 Seed User Credentials

On first run, the database is seeded automatically with the following accounts:

| Username | Password | Role |
| :--- | :--- | :--- |
| **admin** | admin123 | Administrator |
| **student1** | student123 | Student |

*Note: Since Simulated OTP is enabled, after entering the password, check your terminal/console output for the 6-digit OTP code to complete login.*

---

## 🤖 Gemini AI Grading Output

Open-ended answers evaluated by Gemini include:
- **Verdict**: Correct / Partially Correct / Incorrect
- **Score**: Scaled out of 10 points
- **Analysis**: Detailed feedback regarding student explanations, misconceptions, and missing points
- **Correct Answer**: Renders correct answers or custom rubric
- **Suggestions**: Specific advice for improvement
