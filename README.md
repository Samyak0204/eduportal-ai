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
- **Flexible Question Upload**: Support MCQ (Single & Multi-Select), Essay, Math, Code, and Image-based questions.
- **Dynamic MCQ Selection**: Dynamic form switches between `st.selectbox` and `st.multiselect` depending on the "Allow Multiple Correct Answers" setting.
- **Inline Question Editor**: Edit existing questions directly in the question manager without losing previously uploaded image assets.
- **Salesforce Template Loader**: Load 5 predefined Salesforce template questions instantly to populate fields and seed the database.
- **Custom Grading Rationale**: Set custom explanation/rationale text to be displayed to students on evaluation.
- **Format Restrictions**: Configure specifically allowed answer formats (Text, Image, and/or Audio) per question.
- **Submission Hub**: Monitor student results, scores, and Gemini AI evaluations.

### Student
- **Secure Landing Screen**: Student ID, Name, and Email entry form to unlock and begin the test.
- **Intermediate Hardware Verification Page**: Dedicated screen to verify webcam (using `st.camera_input`) and microphone permissions before opening the exam. Includes a `🔄 Refresh Page` helper if permissions were blocked.
- **Exam Integrity Layout**: Bypasses Streamlit's tab containers and sidebar (Sign Out button) completely during the exam, providing a focused, full-width workspace.
- **Browser Reload Persistence**: Current question index, student details, hardware checks, and all inputted answers persist in MongoDB across tab reloads and browser crashes.
- **Sequential Exam Sequence**: One question per page navigation (`⬅️ Previous`, `Next ➡️` / `Submit 🚀`) with active progress tracking.
- **Dynamic Format Tabs**: Renders only the input formats allowed by the administrator for each specific question.
- **Instant MCQ Auto-Grading**: Saves Gemini API quota by programmatically auto-grading MCQs upon submission. Supports **proportional subset scoring** for multi-correct MCQs (points awarded for correct subsets, zeroed if any wrong choices are checked).
- **Consolidated AI Evaluations**: Graded all at once at submit-time, with empty answers intercepted locally to output `0/10` instantly.
- **Results History**: Persistent dashboard tab showing full breakdown of past submissions.

---

## 🤖 Gemini Evaluation Output

Each evaluation includes:
- ✅ **Verdict** — Correct / Partially Correct / Incorrect
- 📊 **Score** — out of 10
- 🔍 **Analysis** — detailed breakdown
- 💡 **Correct Answer & Explanation** — custom rationale and answers
- 📝 **Suggestions** — improvement tips

---

## ⚠️ Notes

- **Secure Contexts**: Web browsers require HTTPS (or `localhost` / `127.0.0.1`) to trigger webcam and microphone permission prompts.
- **Reload Restoration**: Persists progress securely via the `db.active_exams` collection in MongoDB.
- **Module Caching**: Automatically calls `importlib.reload` on helper pages on every Streamlit rerun to ensure modifications register without restarting the server.
