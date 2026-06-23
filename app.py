import os
import io
import re
import json
import base64
from datetime import datetime, timezone
from bson import ObjectId
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response, send_file
import db
import gemini_eval
from salesforce_questions import DUMMY_QUESTIONS
import uuid

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "eduportal_ai_premium_secret_key_98765")

# Seed database with default admin/student user on startup
try:
    db.seed_default_users()
except Exception as e:
    print(f"[EduPortal Startup] Error seeding users: {e}")

@app.before_request
def check_single_session():
    if request.path.startswith('/static') or request.path == '/logout' or request.path == '/login':
        return
    if 'user' in session and session['user']['role'] == 'student':
        flask_session_id = session.get('session_id')
        username = session['user']['username']

        try:
            db_conn = db.get_db()
            user_doc = db_conn.users.find_one({"username": username})
            if user_doc:
                db_session_id = user_doc.get("current_session_id")
                if db_session_id and db_session_id!=flask_session_id:
                    session.clear()
                    flash("Session terminated: You logged in from another device or window", "warning")

                    return redirect(url_for('login'))
        except Exception:
            pass

# ── Utilities ─────────────────────────────────────────────────────────────

def decode_base64_data(base64_str):
    """
    Decodes base64 data URLs (e.g. data:image/png;base64,...) 
    and returns a tuple of (binary_bytes, mime_type).
    """
    if not base64_str:
        return None, None
    match = re.match(r'^data:([^;]+);base64,(.+)$', base64_str)
    if match:
        mime = match.group(1)
        try:
            data = base64.b64decode(match.group(2))
            return data, mime
        except Exception:
            return None, None
    else:
        try:
            data = base64.b64decode(base64_str)
            return data, None
        except Exception:
            return None, None


def get_student_questions():
    """
    Loads unified questions list: Custom questions from DB 
    combined with Salesforce templates not in DB by title.
    """
    try:
        db_questions = db.get_all_questions()
    except Exception:
        db_questions = []
        
    db_titles = {q["title"] for q in db_questions}
    unique_dummy = [q for q in DUMMY_QUESTIONS if q["title"] not in db_titles]
    
    questions = []
    for q in db_questions:
        questions.append({
            "id": str(q["_id"]),
            "title": q["title"],
            "type": q["type"],
            "text": q["text"],
            "marks": q["marks"],
            "difficulty": q["difficulty"],
            "allowed_formats": q.get("allowed_formats", ["Text"]),
            "options": q.get("options"),
            "is_multi_correct": q.get("is_multi_correct", False),
            "correct_option": q.get("correct_option"),
            "ideal_answer": q.get("ideal_answer"),
            "explanation": q.get("explanation"),
            "has_image": "image_bytes" in q and bool(q["image_bytes"])
        })
        
    for idx, q in enumerate(unique_dummy):
        questions.append({
            "id": f"dummy_{idx}",
            "title": q["title"],
            "type": q["type"],
            "text": q["text"],
            "marks": q["marks"],
            "difficulty": q["difficulty"],
            "allowed_formats": q.get("allowed_formats", ["Text", "Image", "Audio"]),
            "options": q.get("options"),
            "is_multi_correct": q.get("is_multi_correct", False),
            "correct_option": q.get("correct_option"),
            "ideal_answer": q.get("ideal_answer"),
            "explanation": q.get("explanation"),
            "has_image": False
        })
    return questions


# ── Page Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session['user']['role']
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        session.clear()
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        payload = request.json or {}
        username = payload.get('username', '').strip()
        password = payload.get('password', '').strip()
        otp_code = payload.get('otp', '').strip()
        fingerprint = payload.get('fingerprint', 'unknown_fingerprint')

        if username and password and not otp_code:
            try:
                user = db.verify_user(username, password)
                if user:
                    db.generate_login_otp(username)
                    return jsonify({"status": "otp_required", "username": username})
                else:
                    return jsonify({"status": "error", "message": "Invalid username or password."}), 401
            except Exception as e:
                return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
            
        elif username and otp_code:
            try:
                if db.verify_login_otp(username, otp_code):
                    db_conn = db.get_db()
                    user_doc = db_conn.users.find_one({"username": username})

                    if not user_doc:
                        return jsonify({"status": "error", "message": "User not found."}), 404
                    
                    session['user'] = {
                        "username": user_doc["username"],
                        "role": user_doc["role"],
                        "name": user_doc["name"]
                    }

                    sess_id = str(uuid.uuid4())
                    session['session_id'] = sess_id

                    db_conn.users.update_one({"username": username}, {"$set": {
                        "current_session_id": sess_id,
                        "device_fingerprint": fingerprint
                    }})

                    if user_doc['role']=='student':
                        saved_state = db.get_active_exam_state(username)
                        if saved_state:
                            session['test_active'] = saved_state.get('test_active', False)
                            session['exam_token'] = saved_state.get('exam_token')

                    return jsonify({"status": "success", "redirect": url_for('index')})
                else:
                    return jsonify({"status": "error", "message": "Invalid OTP code."}), 401
            except Exception as e:
                return jsonify({"status": "error", "message": f"Verification error: {str(e)}"}), 500
        
        else:
            return jsonify({"status": "error", "message": "Missing credentials or OTP code"}), 400
        
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route('/student')
def student_dashboard():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('student.html')


@app.route('/mobile_upload', methods=['GET', 'POST'])
def mobile_upload():
    if request.method == 'POST':
        payload = request.json or {}
        token = payload.get('token')
        image_data = payload.get('image_data')
        
        if not token or not image_data:
            return jsonify({"status": "error", "message": "Missing token or image payload"}), 400
            
        token_doc = db.verify_upload_token(token)
        if not token_doc:
            return jsonify({"status": "error", "message": "Token has expired or is invalid"}), 400
            
        image_bytes, mime = decode_base64_data(image_data)
        if not image_bytes:
            return jsonify({"status": "error", "message": "Failed to decode image data"}), 400
            
        try:
            success = db.save_token_image(token, image_bytes)
            if success:
                return jsonify({"status": "ok"})
            else:
                return jsonify({"status": "error", "message": "Failed to store image in database"}), 500
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    # GET Request
    token = request.args.get('token')
    if not token:
        return render_template('mobile_upload.html', error="Invalid request: Missing secure token")
        
    try:
        token_doc = db.verify_upload_token(token)
        if not token_doc:
            return render_template('mobile_upload.html', error="Link expired or invalid. Please request a new QR code on your exam screen.")
            
        return render_template('mobile_upload.html', token=token, student_username=token_doc['student_username'])
    except Exception as e:
        return render_template('mobile_upload.html', error=f"Database error: {str(e)}")


# ── Proctoring Companion APIs (PyQt6 client backwards compatibility) ───────

@app.route('/api/action', methods=['GET', 'POST'])
def api_action():
    # Read parameters from query string (Streamlit style) or JSON body
    params = {}
    if request.method == 'POST':
        params = request.json or {}
    
    # Merge query string params
    for k, v in request.args.items():
        params[k] = v
        
    action = params.get("action")
    token = params.get("token")
    
    if not token:
        return jsonify({"error": "Missing token"}), 400
        
    try:
        if action == "launch":
            session_doc = db.verify_exam_token(token)
            if session_doc:
                return jsonify({"status": "ok", "student_username": session_doc["student_username"]})
            else:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 403
                
        elif action == "heartbeat":
            ok = db.heartbeat_session(token)
            return jsonify({"status": "ok" if ok else "error"})
            
        elif action == "violation":
            v_type = params.get("type", "unknown")
            v_detail = params.get("detail", "")
            ok = db.log_violation(token, v_type, v_detail)
            return jsonify({"status": "ok" if ok else "error"})
            
        elif action == "submit":
            db_conn = db.get_db()
            result = db_conn.exam_sessions.update_one(
                {"token": token},
                {"$set": {"status": "submitted"}}
            )
            return jsonify({"status": "ok" if result.modified_count > 0 else "error"})
            
        else:
            return jsonify({"error": "Unknown action"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Static Answer Templates API ───────────────────────────────────────────

@app.route('/api/salesforce_templates')
def api_salesforce_templates():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(DUMMY_QUESTIONS)


# ── Stored Binary Media Fetching APIs ─────────────────────────────────────

@app.route('/api/question/image/<qid>')
def get_question_image(qid):
    try:
        q = db.get_question_by_id(qid)
        if q and q.get("image_bytes"):
            mime = q.get("image_mime", "image/png")
            return Response(q["image_bytes"], mimetype=mime)
    except Exception:
        pass
    return "Image not found", 404


@app.route('/api/submission/image/<sid>')
def get_submission_image(sid):
    try:
        db_conn = db.get_db()
        sub = db_conn.submissions.find_one({"_id": ObjectId(sid)})
        if sub and sub.get("answer_image"):
            return Response(sub["answer_image"], mimetype="image/png")
    except Exception:
        pass
    return "Submission image not found", 404


@app.route('/api/submission/audio/<sid>')
def get_submission_audio(sid):
    try:
        db_conn = db.get_db()
        sub = db_conn.submissions.find_one({"_id": ObjectId(sid)})
        if sub and sub.get("answer_audio"):
            return Response(sub["answer_audio"], mimetype="audio/wav")
    except Exception:
        pass
    return "Submission audio not found", 404


# ── REST API: Admin Operations ─────────────────────────────────────────────

@app.route('/api/admin/metrics')
def api_admin_metrics():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    try:
        questions = len(db.get_all_questions())
        submissions = len(db.get_all_submissions())
        students = len(db.get_all_students())
        return jsonify({
            "questions": questions,
            "submissions": submissions,
            "students": students
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/questions')
def api_admin_questions():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        db_questions = db.get_all_questions()
        questions = []
        for q in db_questions:
            questions.append({
                "id": str(q["_id"]),
                "title": q["title"],
                "type": q["type"],
                "text": q["text"],
                "marks": q["marks"],
                "difficulty": q["difficulty"],
                "allowed_formats": q.get("allowed_formats", ["Text"]),
                "options": q.get("options"),
                "is_multi_correct": q.get("is_multi_correct", False),
                "correct_option": q.get("correct_option"),
                "ideal_answer": q.get("ideal_answer"),
                "explanation": q.get("explanation"),
                "has_image": "image_bytes" in q and bool(q["image_bytes"])
            })
        return jsonify(questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/submissions')
def api_admin_submissions():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        db_subs = db.get_all_submissions()
        submissions = []
        for s in db_subs:
            submissions.append({
                "id": str(s["_id"]),
                "student_username": s["student_username"],
                "student_id": s.get("student_id", ""),
                "student_email": s.get("student_email", ""),
                "question_id": s["question_id"],
                "question_title": s.get("question_title", "N/A"),
                "question_text": s.get("question_text", ""),
                "answer_type": s["answer_type"],
                "answer_text": s.get("answer_text") if s["answer_type"] == "Text" else None,
                "evaluation": s.get("evaluation", "_Not evaluated_"),
                "submitted_at": s["submitted_at"].isoformat()
            })
        return jsonify(submissions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/students')
def api_admin_students():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        db_students = db.get_all_students()
        students = []
        for s in db_students:
            students.append({
                "username": s["username"],
                "name": s["name"],
                "created_at": s["created_at"].isoformat()
            })
        return jsonify(students)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/create_student', methods=['POST'])
def api_admin_create_student():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    payload = request.json or {}
    username = payload.get('username', '').strip()
    name = payload.get('name', '').strip()
    password = payload.get('password', '').strip()
    
    if not username or not name or not password:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    try:
        ok, msg = db.create_user(username, password, "student", name)
        if ok:
            return jsonify({"status": "ok"})
        else:
            return jsonify({"status": "error", "message": msg}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/question/add', methods=['POST'])
def api_admin_question_add():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        q_type = request.form.get('type')
        title = request.form.get('title')
        text = request.form.get('text')
        marks = int(request.form.get('marks', 10))
        difficulty = request.form.get('difficulty', 'Medium')
        explanation = request.form.get('explanation', '').strip()
        
        if not title or not text:
            return jsonify({"status": "error", "message": "Title and question text are required"}), 400
            
        doc = {
            "title": title,
            "type": q_type,
            "text": text,
            "marks": marks,
            "difficulty": difficulty,
            "explanation": explanation,
            "created_by": session['user']['username'],
            "created_at": datetime.now(timezone.utc)
        }
        
        # Handle Image File Upload
        img_file = request.files.get('image_file')
        if img_file and img_file.filename != '':
            doc["image_bytes"] = img_file.read()
            doc["image_mime"] = img_file.mimetype
            
        if q_type == "Multiple Choice":
            doc["options"] = {
                "A": request.form.get('opt_a', '').strip(),
                "B": request.form.get('opt_b', '').strip(),
                "C": request.form.get('opt_c', '').strip(),
                "D": request.form.get('opt_d', '').strip()
            }
            # correct_option was appended as a JSON array string in JS
            correct_json = request.form.get('correct_option', '[]')
            correct_list = json.loads(correct_json)
            
            is_multi = request.form.get('is_multi_correct') == 'on'
            doc["is_multi_correct"] = is_multi
            
            if is_multi:
                doc["correct_option"] = correct_list
            else:
                doc["correct_option"] = correct_list[0] if correct_list else "A"
        else:
            doc["ideal_answer"] = request.form.get('ideal_answer', '').strip()
            # allowed formats JSON array string
            formats_json = request.form.get('allowed_formats', '["Text"]')
            doc["allowed_formats"] = json.loads(formats_json)
            
        db.insert_question(doc)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/question/edit/<qid>', methods=['POST'])
def api_admin_question_edit(qid):
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        q_type = request.form.get('type')
        title = request.form.get('title')
        text = request.form.get('text')
        marks = int(request.form.get('marks', 10))
        difficulty = request.form.get('difficulty', 'Medium')
        explanation = request.form.get('explanation', '').strip()
        
        if not title or not text:
            return jsonify({"status": "error", "message": "Title and question text are required"}), 400
            
        # Get existing to retain image if not replaced
        existing = db.get_question_by_id(qid)
        if not existing:
            return jsonify({"status": "error", "message": "Question not found"}), 404
            
        doc = {
            "title": title,
            "type": q_type,
            "text": text,
            "marks": marks,
            "difficulty": difficulty,
            "explanation": explanation,
            "created_by": session['user']['username'],
            "created_at": datetime.now(timezone.utc)
        }
        
        # Handle Image File Upload
        img_file = request.files.get('image_file')
        if img_file and img_file.filename != '':
            doc["image_bytes"] = img_file.read()
            doc["image_mime"] = img_file.mimetype
        else:
            # Retain existing image
            if existing.get("image_bytes"):
                doc["image_bytes"] = existing["image_bytes"]
                doc["image_mime"] = existing.get("image_mime")
                
        if q_type == "Multiple Choice":
            doc["options"] = {
                "A": request.form.get('opt_a', '').strip(),
                "B": request.form.get('opt_b', '').strip(),
                "C": request.form.get('opt_c', '').strip(),
                "D": request.form.get('opt_d', '').strip()
            }
            correct_json = request.form.get('correct_option', '[]')
            correct_list = json.loads(correct_json)
            
            is_multi = request.form.get('is_multi_correct') == 'on'
            doc["is_multi_correct"] = is_multi
            
            if is_multi:
                doc["correct_option"] = correct_list
            else:
                doc["correct_option"] = correct_list[0] if correct_list else "A"
        else:
            doc["ideal_answer"] = request.form.get('ideal_answer', '').strip()
            formats_json = request.form.get('allowed_formats', '["Text"]')
            doc["allowed_formats"] = json.loads(formats_json)
            
        db.update_question(qid, doc)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/question/delete/<qid>', methods=['POST'])
def api_admin_question_delete(qid):
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    try:
        db.delete_question(qid)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── REST API: Student Operations ───────────────────────────────────────────

@app.route('/api/student/questions')
def api_student_questions():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
    try:
        questions = get_student_questions()
        return jsonify(questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/student/submissions')
def api_student_submissions():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        username = session['user']['username']
        db_subs = db.get_submissions_by_student(username)
        submissions = []
        for s in db_subs:
            submissions.append({
                "id": str(s["_id"]),
                "student_username": s["student_username"],
                "question_id": s["question_id"],
                "question_title": s.get("question_title", "N/A"),
                "question_text": s.get("question_text", ""),
                "answer_type": s["answer_type"],
                "answer_text": s.get("answer_text") if s["answer_type"] == "Text" else None,
                "evaluation": s.get("evaluation", "_Not evaluated_"),
                "submitted_at": s["submitted_at"].isoformat()
            })
        return jsonify(submissions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/student/start_exam', methods=['POST'])
def api_student_start_exam():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    payload = request.json or {}
    student_id = payload.get('student_id')
    student_email = payload.get('student_email')
    student_name = payload.get('student_name')
    
    if not student_id or not student_email or not student_name:
        return jsonify({"status": "error", "message": "All candidate fields required"}), 400
        
    try:
        username = session['user']['username']
        questions = get_student_questions()
        
        state_doc = {
            "test_active": True,
            "hardware_verified": False,
            "camera_checked": False,
            "mic_checked": False,
            "current_question_index": 0,
            "student_details": {
                "id": student_id,
                "name": student_name,
                "email": student_email
            },
            "answers": {},
            "test_questions": questions,
            "started_at": datetime.now(timezone.utc),
        }
        
        db.save_active_exam_state(username, state_doc)
        session['test_active'] = True
        
        return jsonify({"status": "ok", "candidate": state_doc["student_details"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/get_state')
def api_student_get_state():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        username = session['user']['username']
        state = db.get_active_exam_state(username)
        if not state:
            return jsonify({"status": "ok", "state": None})
            
        # Convert ObjectId, dates, and convert answer binary fields to base64
        state_serial = {
            "test_active": state.get("test_active", False),
            "hardware_verified": state.get("hardware_verified", False),
            "camera_checked": state.get("camera_checked", False),
            "mic_checked": state.get("mic_checked", False),
            "current_question_index": state.get("current_question_index", 0),
            "student_details": state.get("student_details", {}),
            "started_at": state["started_at"].isoformat() if "started_at" in state else None,
            "answers": {}
        }
        
        answers = state.get("answers", {})
        for qid, ans in answers.items():
            ans_serial = {
                "answer_type": ans.get("answer_type", "Text"),
                "answer_text": ans.get("answer_text", "")
            }
            
            # If image binary, encode to base64 data url
            if ans.get("image_bytes"):
                b64 = base64.b64encode(ans["image_bytes"]).decode()
                mime = ans.get("image_mime", "image/png")
                ans_serial["image_bytes"] = f"data:{mime};base64,{b64}"
            else:
                ans_serial["image_bytes"] = None
                
            # If audio binary, encode to base64 data url
            if ans.get("audio_bytes"):
                b64 = base64.b64encode(ans["audio_bytes"]).decode()
                mime = ans.get("audio_mime", "audio/wav")
                ans_serial["audio_bytes"] = f"data:{mime};base64,{b64}"
            else:
                ans_serial["audio_bytes"] = None
                
            state_serial["answers"][qid] = ans_serial
            
        return jsonify({"status": "ok", "state": state_serial})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/save_state', methods=['POST'])
def api_student_save_state():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    payload = request.json or {}
    try:
        username = session['user']['username']
        existing = db.get_active_exam_state(username) or {}
        
        # Merge payload values into the state doc
        state_doc = {
            "test_active": True,
            "hardware_verified": payload.get("hardware_verified", existing.get("hardware_verified", False)),
            "camera_checked": payload.get("camera_checked", existing.get("camera_checked", False)),
            "mic_checked": payload.get("mic_checked", existing.get("mic_checked", False)),
            "current_question_index": payload.get("current_question_index", existing.get("current_question_index", 0)),
            "student_details": existing.get("student_details", {}),
            "started_at": existing.get("started_at", datetime.now(timezone.utc))
        }
        
        # Deserialize responses dictionary
        answers_payload = payload.get("answers", {})
        answers_doc = {}
        
        for qid, ans in answers_payload.items():
            ans_doc = {
                "answer_type": ans.get("answer_type", "Text"),
                "answer_text": ans.get("answer_text", "")
            }
            
            # Decode image base64 if present
            if ans.get("image_bytes"):
                img_data, mime = decode_base64_data(ans["image_bytes"])
                if img_data:
                    ans_doc["image_bytes"] = img_data
                    ans_doc["image_mime"] = mime or "image/png"
                    
            # Decode audio base64 if present
            if ans.get("audio_bytes"):
                aud_data, mime = decode_base64_data(ans["audio_bytes"])
                if aud_data:
                    ans_doc["audio_bytes"] = aud_data
                    ans_doc["audio_mime"] = mime or "audio/wav"
                    
            answers_doc[qid] = ans_doc
            
        state_doc["answers"] = answers_doc
        
        db.save_active_exam_state(username, state_doc)
        
        # Keep Flask session in sync
        session['test_active'] = True
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/cancel_exam', methods=['POST'])
def api_student_cancel_exam():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
    try:
        username = session['user']['username']
        db.delete_active_exam_state(username)
        session.pop('test_active', None)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/generate_upload_token', methods=['POST'])
def api_student_generate_upload_token():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    payload = request.json or {}
    qid = payload.get('question_id')
    if not qid:
        return jsonify({"status": "error", "message": "Missing question ID"}), 400
        
    try:
        username = session['user']['username']
        token = db.create_upload_token(username, qid)
        return jsonify({"status": "ok", "token": token})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/check_upload_status')
def api_student_check_upload_status():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    token = request.args.get('token')
    if not token:
        return jsonify({"status": "error", "message": "Missing token"}), 400
        
    try:
        status = db.check_token_status(token)
        # If image uploaded, status['image_bytes'] has binary bytes. We base64 encode it for JS.
        uploaded = status.get('uploaded', False)
        img_b64 = None
        if uploaded and status.get('image_bytes'):
            img_b64 = base64.b64encode(status['image_bytes']).decode()
            
        return jsonify({
            "uploaded": uploaded,
            "image_bytes": img_b64
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/submit_exam', methods=['POST'])
def api_student_submit_exam():
    if 'user' not in session or session['user']['role'] != 'student':
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        username = session['user']['username']
        
        # Load registration data and full questions mapping
        state = db.get_active_exam_state(username)
        if not state:
            return jsonify({"status": "error", "message": "No active exam session found"}), 404
            
        student_details = state.get("student_details", {})
        questions = get_student_questions()
        
        payload = request.json or {}
        answers_payload = payload.get("answers", {})
        
        results = []
        
        # Process and evaluate each question
        for idx, q in enumerate(questions):
            qid = q["id"]
            ans = answers_payload.get(qid, {
                "answer_type": "Text",
                "answer_text": "",
                "image_bytes": None,
                "audio_bytes": None
            })
            
            ans_type = ans.get("answer_type", "Text")
            ans_text = ans.get("answer_text", "")
            
            img_bytes, img_mime = decode_base64_data(ans.get("image_bytes"))
            aud_bytes, aud_mime = decode_base64_data(ans.get("audio_bytes"))
            
            # Normalise student answer text representation for storage
            student_raw_ans = ans_text
            if ans_type == "Image":
                student_raw_ans = "(Answer captured via camera)"
            elif ans_type == "Audio":
                student_raw_ans = "(Answer captured via voice recorder)"
                
            # 1. MCQ Auto-Grading Script
            if q["type"] == "Multiple Choice":
                selected = ans_text
                correct = q.get("correct_option")
                explanation = q.get("explanation", "No explanation provided.")
                
                if isinstance(selected, str):
                    selected_set = {selected} if selected else set()
                elif isinstance(selected, list):
                    selected_set = set(selected)
                else:
                    selected_set = set()
                    
                if isinstance(correct, str):
                    correct_set = {correct}
                elif isinstance(correct, list):
                    correct_set = set(correct)
                else:
                    correct_set = set()
                    
                if selected_set == correct_set:
                    verdict = "Correct"
                    score = q["marks"]
                elif selected_set.issubset(correct_set) and len(selected_set) > 0:
                    verdict = "Partially Correct"
                    score = int(q["marks"] * (len(selected_set) / len(correct_set)))
                else:
                    verdict = "Incorrect"
                    score = 0
                    
                selected_str = ", ".join(sorted(list(selected_set))) if selected_set else "None"
                correct_str = ", ".join(sorted(list(correct_set)))
                
                eval_text = f"""## ✅ Verdict
{verdict}

## 📊 Score
{score} / {q['marks']} (Automatically Scored)

## 🔍 Analysis
The student selected option(s): **{selected_str}**. The correct option(s): **{correct_str}**.

## 💡 Correct Answer & Explanation
**Correct Option(s): {correct_str}**

{explanation}

## 📝 Suggestions
{"Excellent! You got the answer fully right." if verdict == "Correct" else "You got some options right but missed others. Review the explanation above to understand this concept better." if verdict == "Partially Correct" else "Review the explanation above to understand this concept better."}
"""
                extracted_score = score
                
            # 2. AI Evaluation via Gemini API
            else:
                has_no_answer = (not ans_text or not ans_text.strip()) and not img_bytes and not aud_bytes
                
                if has_no_answer:
                    eval_text = f"""## Verdict
Incorrect

## Score
0 / 10 (No answer provided)

## Analysis
The student did not submit any response or attachment for this question.

## Correct Answer & Explanation
**Ideal Correct Answer / Rubric:**
{q.get('ideal_answer', 'No ideal answer provided.')}

{q.get('explanation', 'No explanation provided.')}

## Suggestions
Please make sure to attempt all questions by providing text, audio, or image answers.
"""
                    extracted_score = 0
                else:
                    try:
                        eval_text = gemini_eval.evaluate_answer(
                            question_text=q["text"],
                            question_type=q["type"],
                            answer_text=ans_text,
                            image_bytes=img_bytes,
                            image_mime=img_mime or "image/png",
                            audio_bytes=aud_bytes,
                            audio_mime=aud_mime or "audio/wav",
                            options=q.get("options"),
                            correct_option=q.get("correct_option"),
                            ideal_answer=q.get("ideal_answer"),
                            explanation=q.get("explanation")
                        )
                    except Exception as e:
                        eval_text = f"AI Evaluation Error: {str(e)}"
                        
                    # Extract score (e.g. ## Score\n8/10)
                    score_match = re.search(r"## Score\s*(\d+)", eval_text)
                    extracted_score = int(score_match.group(1)) if score_match else 0
            
            # Save submission doc to DB
            sub_doc = {
                "student_username": username,
                "student_id": student_details.get("id"),
                "student_email": student_details.get("email"),
                "question_id": qid,
                "question_title": q["title"],
                "question_text": q["text"],
                "question_type": q["type"],
                "answer_type": ans_type,
                "evaluation": eval_text,
                "submitted_at": datetime.now(timezone.utc)
            }
            
            if ans_text:
                sub_doc["answer_text"] = ans_text
            if img_bytes:
                sub_doc["answer_image"] = img_bytes
            if aud_bytes:
                sub_doc["answer_audio"] = aud_bytes
                
            db.insert_submission(sub_doc)
            
            # Append result
            results.append({
                "title": q["title"],
                "text": q["text"],
                "type": q["type"],
                "score": extracted_score,
                "max_score": q["marks"] if q["type"] == "Multiple Choice" else 10,
                "ans_type": ans_type,
                "answer_text": ans.get("image_bytes") if ans_type == "Image" else (ans.get("audio_bytes") if ans_type == "Audio" else ans_text),
                "evaluation": eval_text
            })
            
        # Clean up active exam state from DB
        db.delete_active_exam_state(username)
        session.pop('test_active', None)
        
        return jsonify({"status": "ok", "results": results})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Run server locally on port 5000 (standard Flask development server)
    app.run(host='0.0.0.0', port=5000, debug=True)
