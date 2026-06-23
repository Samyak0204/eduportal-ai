# EduPortal AI — Full Chat Context Summary

> This document summarises everything discussed in the previous chat session so a new Claude instance can pick up exactly where we left off.

---

## 1. Project Overview

**Project Name:** EduPortal AI  
**GitHub Repo:** https://github.com/Samyak0204/eduportal-ai  
**Developer:** Samyak (intern at a company building this for a commercial client)  
**Stack:** Python, Streamlit, MongoDB, Google Gemini (gemini-2.5-flash)  
**Deployment:** Currently local; cloud access not yet granted by the company  
**Platforms to support:** Windows 10/11 and macOS 13+  
**Timeline:** ~30 working days from manager approval (self-estimated with 25% buffer)

### What it does (existing)
An AI-powered student evaluation portal. Students log in, answer questions (text, image, or audio), and Google Gemini instantly grades their answers with a score, verdict, analysis, correct answer, and suggestions.

---

## 2. Existing Codebase — File by File

### `app.py` (315 lines)
- Streamlit entry point
- Sets page config and injects ~200 lines of inline custom CSS (dark glassmorphism theme, Sora font)
- Manages login screen and `st.session_state`
- Routes to `admin_dashboard()` or `student_dashboard()` based on role
- **No lockdown routing, no query-param handling yet**

### `db.py` (119 lines)
- MongoDB connection via global `_client` singleton (no reconnection logic)
- Collections: `users`, `questions`, `submissions`
- bcrypt password hashing — correctly implemented
- `seed_default_users()` creates admin/student on first run
- Raw image/audio bytes stored directly in MongoDB documents (performance issue)
- `datetime.utcnow()` used in `create_user()` — deprecated in Python 3.12+
- **No ExamSession, upload token, or violation log collections**

### `student_pages.py` (229 lines)
- Shows ALL questions to ALL logged-in students (no scoping)
- Three answer tabs per question: Text, Image (file upload only), Audio (file + mic)
- Calls `gemini_eval.evaluate_answer()` immediately on every submission
- **No exam timer, no lockdown enforcement, no camera capture, no QR code**

### `admin_pages.py` (187 lines)
- Four tabs: Upload Question, Manage Questions, View Submissions, Manage Students
- Can create student accounts, upload questions (MCQ + open-ended + image attachment)
- `datetime.utcnow()` used on question upload — same deprecation issue
- **No exam management, no proctoring dashboard, no manual Gemini trigger**

### `gemini_eval.py` (167 lines)
- Three evaluators: `evaluate_text_answer`, `evaluate_image_answer`, `evaluate_audio_answer`
- Shared `_build_prompt()` for text/image — but audio has its own **duplicated** prompt block
- Retry logic with exponential backoff on 429 quota errors
- Uses `gemini-2.5-flash` model
- Evaluation fires automatically on submission — **no admin trigger gate**

### `requirements.txt`
- Package versions are **unpinned** (e.g. `streamlit` not `streamlit==1.35.0`) — will break on client machines over time

### Repo issues
- Only 2 commits, no meaningful commit history
- `scratch/` folder committed (should be in `.gitignore`)
- No `.env.example` file committed (README references it but it's missing)
- Default credentials (`admin/admin123`, `student1/student123`) shown publicly in README

---

## 3. All Issues Identified

### 🔴 Critical / Security
1. Default credentials are hardcoded and publicly visible in README
2. User-Agent check (`EduPortalSecureBrowser/1.0`) is trivially spoofable — needs signed session tokens
3. No session token / JWT — `st.session_state` resets on browser refresh; students get kicked out mid-exam
4. `datetime.utcnow()` deprecated — inconsistency between `db.py` functions
5. QR upload token was proposed as 6-digit — brute-forceable; must use UUID4 exclusively
6. No rate limiting on `verify_upload_token` — brute-force risk

### 🟡 Architecture
7. No `ExamSession` concept — students can answer any question any time; no time limits
8. Binary blobs (images/audio) stored raw in MongoDB — use GridFS instead
9. `from db import get_db` inside a function in `student_pages.py` — local import smell
10. Global `_client` singleton has no reconnection logic
11. ~200 lines of CSS injected inline in `app.py` — needs to move to `styles.py`
12. `evaluate_answer()` fires automatically on submit — should be admin-triggered
13. No file size validation on uploads — a student could upload a 50MB image
14. `submission_exists()` not scoped to session — allows cross-session resubmission
15. Audio prompt in `gemini_eval.py` is a copy-paste of `_build_prompt()` — duplication

### 🟢 Repo/DevOps
16. Only 2 commits, no commit message convention (`feat:`, `fix:`, `chore:`)
17. `scratch/` folder committed
18. No `.env.example` committed
19. `requirements.txt` has unpinned versions
20. No CI/CD (GitHub Actions) or automated tests

---

## 4. New Features to Build

### 4A. Portal Changes (Streamlit)

#### `db.py` — New functions needed
- `create_exam_session(student_username, question_ids)` → creates `exam_sessions` doc, returns UUID token
- `verify_exam_token(token)` → validates active, non-expired session
- `heartbeat_session(token)` → updates `last_heartbeat`
- `log_violation(token, type, detail)` → appends to `violations[]`
- `create_upload_token(student_username, question_id)` → UUID, 5-min TTL
- `verify_upload_token(token)` → single-use, expiry check
- `save_token_image(token, image_bytes)` → GridFS storage, marks token used
- `check_token_status(token)` → bool: has mobile image arrived yet?
- Fix: all `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Fix: reconnection logic in `get_db()`

#### New MongoDB collections
| Collection | Key Fields |
|---|---|
| `exam_sessions` | token (UUID), student_username, question_ids[], started_at, expires_at, status, violations[], last_heartbeat |
| `exams` | title, question_ids[], duration_minutes, created_by, created_at, is_active |
| `upload_tokens` | token (UUID), student_username, question_id, expires_at (5 min), used, image_gridfs_id |

#### `app.py` — New routing
- Move CSS to `styles.py`
- Query-param router at top of `main()`:
  - `?action=heartbeat&token=...` → update heartbeat, return `{ok: true}`
  - `?action=launch&u=...` → create ExamSession, return token as JSON
  - `?action=violation&token=...&type=...` → log proctoring event
  - `?action=submit&token=...` → mark session submitted
  - `?page=upload&token=...` → render mobile upload page (no auth wall)

#### `student_pages.py` — Exam awareness
- Lockdown gate: verify User-Agent AND session token at top of `student_dashboard()`; show download screen if either fails
- Replace `get_all_questions()` with `get_session_questions(token)`
- Add countdown timer (turns red under 10 minutes)
- Add `st.camera_input()` to Image tab for webcam capture inside lockdown browser
- Add file size validation (reject > 5MB)
- Add QR code panel per question: generate token, show QR, poll `check_token_status()` with `st.rerun()`

#### `admin_pages.py` — New tabs
- **Create Exam tab**: select questions, set duration, activate/deactivate
- **Proctoring Monitor tab**: live view of sessions, violation log, heartbeat status, Terminate Session button
- **Update Submissions tab**: add "Trigger Gemini Evaluation" button (remove auto-eval), show violation count per submission

#### `gemini_eval.py` — Cleanup
- Deduplicate: move audio prompt block into `_build_prompt()`
- Add optional `proctoring_context` parameter: if violations exist during that answer, append note to evaluator prompt

### 4B. Lockdown Browser (`lockdown_browser.py` — PyQt6)

#### Core app
- Frameless fullscreen window with `Qt.WindowType.WindowStaysOnTopHint`
- `QWebEngineView` loading the Streamlit app URL
- Custom User-Agent: `EduPortalSecureBrowser/1.0`
- Auto-accept camera/mic permission requests
- On login success: call `?action=launch`, store session token in memory
- Append `?token=<token>` to all page loads via `urlChanged` signal

#### Security hooks
- **Windows**: `ctypes` `WH_KEYBOARD_LL` hook to suppress LWin, RWin, Alt+Tab, Alt+Esc, Ctrl+Esc
- **macOS**: `NSApplicationPresentationOptions` to hide dock/menu bar, disable Cmd+Tab and Cmd+Option+Esc
- macOS requires Accessibility Permissions — app prompts on first launch

#### Proctoring monitors
- **Screen monitor**: `QApplication.screens()` every 2 seconds → if > 1 screen, show blocking modal, log `multi_screen`
- **Focus monitor**: `focusChanged` signal → log `focus_loss`, show warning banner
- **Process monitor**: whitelist-based background thread every 10s → log `blocked_app` with process name
- **Heartbeat timer**: `QTimer` every 30s → silent GET to `?action=heartbeat&token=...`

#### Crash recovery
- Save token to local temp file on session start
- On relaunch: detect temp file → show "Resume Exam" button
- If token expired: show "Session Expired — contact admin"

#### QR Code Companion flow
1. Portal generates UUID upload token (5-min TTL), renders QR pointing to `http://<server-ip>:8501/?page=upload&token=<uuid>`
2. Student scans with phone; mobile page shows their name + question for confirmation
3. Phone camera forced via `capture="environment"` attribute
4. Image saved to GridFS; desktop polls `check_token_status()` every 3 seconds and auto-updates
5. Token is single-use; "Regenerate QR" button available

#### Build script (`build_lockdown.py`)
- PyInstaller: Windows → `lockdown_browser.exe`, macOS → `lockdown_browser.app`
- macOS Info.plist needs `NSAccessibilityUsageDescription`
- Cross-compilation not supported — must build on each platform natively

---

## 5. Proposed Timeline (from date of approval)

All estimates include a 25% buffer. Labelled as "proposed" — open for manager negotiation.

| Phase | Focus | Buffered Estimate |
|---|---|---|
| Phase 1 | Foundation & security hardening (DB models, datetime fix, CSS refactor) | Days 1–5 |
| Phase 2 | Portal exam & admin features (exam creation, proctoring tab, token gate) | Days 6–12 |
| Phase 3 | Portal upload features (camera, QR, mobile upload page, GridFS) | Days 13–17 |
| Phase 4 | Lockdown browser core build (PyQt6, hooks, monitors, heartbeat) | Days 18–26 |
| Phase 5 | Testing, packaging (.exe/.app), repo cleanup | Days 27–30 |
| **Total** | | **~30 working days** |

Each phase ends with a demo-ready milestone for manager review.

---

## 6. Known Limitations (Documented)

- **Ctrl+Alt+Del** on Windows cannot be blocked at application level — requires kernel driver (out of scope)
- **macOS Accessibility Permissions** must be manually granted by user in System Settings
- **QR Upload** requires phone and server on same local network (or public URL via ngrok) — local-only deployment is an interim constraint
- **Packaging** requires building .exe on Windows and .app on macOS separately — no cross-compilation

---

## 7. Open Questions for Manager (Pending Answers)

1. When will cloud server access be granted? (Needed for QR upload over public URL)
2. Can students re-attempt questions, or is one submission per session final?
3. What violation threshold should trigger an admin alert? What channel (email/Slack)?
4. Is Ctrl+Alt+Del blocking a hard requirement? (Requires kernel driver — significant scope increase)
5. Should the Gemini API key be per-client or shared across deployments?

---

## 8. Deliverables Produced in This Chat

1. **Full code review** of all 5 Python files with specific line-level issues identified
2. **Architecture analysis** comparing current state vs. target state
3. **Implementation plan document** (`EduPortal_AI_Implementation_Plan.docx`) — a professionally formatted Word document with:
   - Cover page with project metadata
   - File-by-file existing code summary
   - Target architecture with end-to-end exam flow (11 steps)
   - Detailed changes per file (db.py, app.py, student_pages.py, admin_pages.py, gemini_eval.py)
   - Lockdown browser spec (security hooks, monitors, QR flow, crash recovery)
   - Proposed Timeline & Milestones table (5 phases, 30 days buffered, milestone callouts)
   - Open questions table for manager review
   - Known limitations section
   - Version: 1.1

---

## 9. Next Steps (What to Do in the Next Chat)

When you start a new chat, paste this document and say which of the following you want to work on:

- **"Start Phase 1"** → Generate updated `db.py` with all new collections and functions
- **"Start Phase 2"** → Generate updated `admin_pages.py` (exam tab + proctoring tab) and `student_pages.py` (lockdown gate + timer)
- **"Build the lockdown browser"** → Generate full `lockdown_browser.py` (Phase 4)
- **"Write the test file"** → Generate `test_lockdown.py`
- **"Fix a specific file"** → e.g. "fix db.py" or "fix gemini_eval.py"
- **"Review the document"** → Make changes to the `.docx` implementation plan
