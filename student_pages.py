import streamlit as st
from datetime import datetime
from db import (
    get_all_questions, get_question_by_id,
    insert_submission, get_submissions_by_student, submission_exists
)
from gemini_eval import evaluate_answer


import re
from datetime import datetime, timezone
from db import (
    get_all_questions, get_question_by_id,
    insert_submission, get_submissions_by_student, submission_exists
)
from gemini_eval import evaluate_answer
from salesforce_questions import DUMMY_QUESTIONS


def student_dashboard():
    username = st.session_state.user["username"]

    # Try to load saved active exam state on first session load
    if "test_active" not in st.session_state:
        from db import get_active_exam_state
        saved_state = get_active_exam_state(username)
        if saved_state:
            st.session_state["test_active"] = saved_state.get("test_active", False)
            st.session_state["hardware_verified"] = saved_state.get("hardware_verified", False)
            st.session_state["camera_checked"] = saved_state.get("camera_checked", False)
            st.session_state["mic_checked"] = saved_state.get("mic_checked", False)
            st.session_state["current_question_index"] = saved_state.get("current_question_index", 0)
            st.session_state["student_details"] = saved_state.get("student_details", {})
            st.session_state["answers"] = saved_state.get("answers", {})
            st.session_state["test_questions"] = saved_state.get("test_questions", [])
            st.session_state["prev_student_id"] = saved_state.get("student_details", {}).get("id", "")
            st.session_state["prev_student_email"] = saved_state.get("student_details", {}).get("email", "")
        else:
            st.session_state["test_active"] = False
            st.session_state["hardware_verified"] = False

    # Check if a test has just been submitted to show summary
    if st.session_state.get("test_submitted"):
        _render_submission_summary()
        return

    st.markdown(f"### Welcome, {st.session_state.user['name']}")

    # If test is active, show only a single page without tabs
    if st.session_state.get("test_active"):
        if not st.session_state.get("hardware_verified"):
            _hardware_verification_page()
        else:
            _active_test_page()
            
        # Save state to DB on every rerun while test is active
        from db import save_active_exam_state
        state_doc = {
            "test_active": True,
            "hardware_verified": st.session_state.get("hardware_verified", False),
            "camera_checked": st.session_state.get("camera_checked", False),
            "mic_checked": st.session_state.get("mic_checked", False),
            "current_question_index": st.session_state.get("current_question_index", 0),
            "student_details": st.session_state.get("student_details", {}),
            "answers": st.session_state.get("answers", {}),
            "test_questions": st.session_state.get("test_questions", [])
        }
        save_active_exam_state(username, state_doc)
        
    else:
        # Show tabs only when not actively in an exam
        tab1, tab2 = st.tabs(["Test Room", "Results History"])
        with tab1:
            _landing_page()
        with tab2:
            _results_tab()


def _landing_page():
    st.markdown("""
    <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 24px; margin-bottom: 24px;">
        <h2 style="margin-top: 0; color: #ffffff;"> Salesforce Competency Assessment</h2>
        <p style="color: rgba(255,255,255,0.8);">Welcome to the exam portal. Please enter your details below to unlock and start the assessment.</p>
        <ul style="color: rgba(255,255,255,0.7); line-height: 1.6;">
            <li><strong>Assessment Type:</strong> Combined Salesforce MCQ & Open-Response</li>
            <li><strong>Format:</strong> One question per page. You can navigate back and forth.</li>
            <li><strong>Allowed Input Methods:</strong> Text, Webcam capture, and Voice recording.</li>
            <li><strong>Grading:</strong> MCQs are graded automatically; Open-Response questions are evaluated by Gemini AI upon final submission.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Combine custom questions from database and default Salesforce template questions (avoiding duplicates by title)
    db_questions = get_all_questions()
    db_titles = {q["title"] for q in db_questions}
    unique_dummy = [q for q in DUMMY_QUESTIONS if q["title"] not in db_titles]
    questions = db_questions + unique_dummy
    if not db_questions:
        st.info("Note: No custom questions uploaded yet. You will be taking the default Salesforce sample assessment.")

    st.markdown("### 👤 Enter Candidate Details")
    with st.form("candidate_details_form"):
        col1, col2 = st.columns(2)
        student_id = col1.text_input("Student / Candidate ID", placeholder="e.g. SID-100452", value=st.session_state.get("prev_student_id", ""))
        student_email = col2.text_input("Email Address", placeholder="student@example.com", value=st.session_state.get("prev_student_email", ""))
        
        student_name = st.text_input("Full Name", value=st.session_state.user['name'])
        
        submitted = st.form_submit_button("Start Assessment", use_container_width=True)

    if submitted:
        if not student_id.strip() or not student_email.strip() or not student_name.strip():
            st.error("Please fill in all candidate details to begin the exam.")
        else:
            st.session_state["prev_student_id"] = student_id
            st.session_state["prev_student_email"] = student_email
            
            st.session_state["student_details"] = {
                "id": student_id,
                "name": student_name,
                "email": student_email
            }
            st.session_state["test_active"] = True
            st.session_state["hardware_verified"] = False
            st.session_state["camera_checked"] = False
            st.session_state["mic_checked"] = False
            st.session_state["current_question_index"] = 0
            st.session_state["answers"] = {}
            st.session_state["test_questions"] = questions
            st.rerun()


def _hardware_verification_page():
    st.markdown("### 🛠️ Hardware & Permission Verification")
    st.markdown(
        "Before starting the assessment, we need to verify your webcam and microphone hardware. "
        "Please grant browser permissions to this site when prompted."
    )

    details = st.session_state.get("student_details", {})
    st.info(f"👤 **Candidate Details Registered:**  \n**Name:** {details.get('name')} | **ID:** {details.get('id')} | **Email:** {details.get('email')}")
    st.divider()

    col_chk1, col_chk2 = st.columns(2)
    
    # Camera Check
    with col_chk1:
        st.markdown("##### 📸 Camera Check")
        cam_placeholder = st.empty()
        
        captured_test = st.camera_input("Take a quick snapshot to verify your webcam:", key="check_cam_input")
        if captured_test:
            st.session_state["camera_checked"] = True
            cam_placeholder.success("📸 Camera: Verified Successfully!")
        else:
            st.session_state["camera_checked"] = False
            cam_placeholder.warning("📸 Camera: Pending Verification")

    # Microphone Check
    with col_chk2:
        st.markdown("##### 🎙️ Microphone Check")
        mic_placeholder = st.empty()
        
        try:
            from streamlit_mic_recorder import mic_recorder
            audio_test_data = mic_recorder(
                start_prompt="🎙️ Start Audio Test",
                stop_prompt="⏹️ Stop Audio Test",
                key="check_mic_input"
            )
            if audio_test_data and audio_test_data.get("bytes"):
                st.session_state["mic_checked"] = True
                mic_placeholder.success("🎙️ Microphone: Verified Successfully!")
                st.audio(audio_test_data["bytes"], format="audio/wav")
            else:
                st.session_state["mic_checked"] = False
                mic_placeholder.warning("🎙️ Microphone: Pending Verification")
        except ImportError:
            # Fallback if mic recorder is not installed
            st.session_state["mic_checked"] = True
            mic_placeholder.success("🎙️ Microphone: Verified (Mocked)")

    st.divider()

    camera_ok = st.session_state.get("camera_checked", False)
    mic_ok = st.session_state.get("mic_checked", False)
    hardware_verified = camera_ok and mic_ok

    if not hardware_verified:
        st.warning("⚠️ Both camera and microphone tests must pass to unlock the start button. If you just allowed permissions, click 'Refresh Page' below for browser settings to take effect.")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.button("🔄 Refresh Page", use_container_width=True)
        with col_btn2:
            if st.button("⬅️ Cancel & Back to Landing Page", use_container_width=True):
                from db import delete_active_exam_state
                delete_active_exam_state(username)
                st.session_state["test_active"] = False
                st.session_state["hardware_verified"] = False
                st.rerun()
    else:
        st.success("✅ All systems checked! You are ready to start.")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Proceed to Exam Questions", type="primary", use_container_width=True):
                st.session_state["hardware_verified"] = True
                st.rerun()
        with col_btn2:
            if st.button("⬅️ Cancel & Back to Landing Page", use_container_width=True):
                from db import delete_active_exam_state
                delete_active_exam_state(username)
                st.session_state["test_active"] = False
                st.session_state["hardware_verified"] = False
                st.rerun()


def _active_test_page():
    questions = st.session_state["test_questions"]
    idx = st.session_state["current_question_index"]
    q = questions[idx]
    qid = str(q.get("_id", f"dummy_{idx}"))

    st.markdown(f"#### Question {idx + 1} of {len(questions)}")
    
    # Progress bar
    progress = (idx + 1) / len(questions)
    st.progress(progress)

    # Question Card
    st.markdown(f"### {q['title']}")
    st.caption(f"**Type:** {q['type']} | **Marks:** {q['marks']} | **Difficulty:** {q['difficulty']}")

    col_q1, col_q2 = st.columns([2, 1]) if "image_bytes" in q else (st.container(), None)

    with col_q1:
        st.markdown(f"**Description:**  \n{q['text']}")
        if q["type"] == "Multiple Choice" and "options" in q:
            for k, v in q["options"].items():
                st.markdown(f"**{k}.** {v}")

    if col_q2 is not None and "image_bytes" in q:
        with col_q2:
            st.image(q["image_bytes"], caption="Question Diagram", use_column_width=True)

    st.divider()

    # Initialize answer state for this question if not present
    if qid not in st.session_state["answers"]:
        st.session_state["answers"][qid] = {
            "answer_type": "Text",
            "answer_text": "",
            "image_bytes": None,
            "image_mime": None,
            "audio_bytes": None,
            "audio_mime": None
        }

    ans_state = st.session_state["answers"][qid]

    st.markdown("#### Your Answer")

    if q["type"] == "Multiple Choice":
        is_multi = q.get("is_multi_correct", False)
        correct_opt = q.get("correct_option")
        if not is_multi and isinstance(correct_opt, list) and len(correct_opt) > 1:
            is_multi = True

        if is_multi:
            # Render Checkboxes for Multi-Select MCQ
            current_selection = ans_state.get("answer_text")
            if isinstance(current_selection, str):
                current_list = [opt.strip() for opt in current_selection.split(",") if opt.strip()]
            elif isinstance(current_selection, list):
                current_list = current_selection
            else:
                current_list = []

            st.markdown("Select all correct options:")
            selected_options = []
            for k, v in q["options"].items():
                checked = st.checkbox(
                    f"{k}. {v}",
                    value=(k in current_list),
                    key=f"mcq_cb_{qid}_{k}"
                )
                if checked:
                    selected_options.append(k)
            ans_state["answer_text"] = selected_options
            ans_state["answer_type"] = "Text"
        else:
            # MCQ Single Choice Choice Selection (Radio)
            options_list = list(q["options"].keys())
            default_idx = 0
            current_sel = ans_state.get("answer_text")
            if isinstance(current_sel, list):
                current_sel = current_sel[0] if current_sel else ""
            if current_sel in options_list:
                default_idx = options_list.index(current_sel)

            selected_opt = st.radio(
                "Choose your answer:",
                options_list,
                format_func=lambda x: f"{x}. {q['options'][x]}",
                index=default_idx,
                key=f"active_mcq_{qid}"
            )
            ans_state["answer_text"] = selected_opt
            ans_state["answer_type"] = "Text"

    else:
        # Check allowed formats specified by the admin
        allowed_formats = q.get("allowed_formats", ["Text", "Image", "Audio"])
        if not allowed_formats:
            allowed_formats = ["Text"]

        tabs_list = []
        if "Text" in allowed_formats:
            tabs_list.append("Written Answer")
        if "Image" in allowed_formats:
            tabs_list.append("Webcam & Image")
        if "Audio" in allowed_formats:
            tabs_list.append("Spoken/Audio")

        if not tabs_list:
            tabs_list = ["Written Answer"]
            allowed_formats = ["Text"]

        tabs = st.tabs(tabs_list)
        tab_idx = 0

        if "Text" in allowed_formats:
            with tabs[tab_idx]:
                text_ans = st.text_area(
                    "Type your answer here:",
                    value=ans_state["answer_text"] or "",
                    height=250,
                    placeholder="Enter your detailed solution...",
                    key=f"active_text_{qid}"
                )
                ans_state["answer_text"] = text_ans
                if text_ans.strip():
                    ans_state["answer_type"] = "Text"
            tab_idx += 1

        if "Image" in allowed_formats:
            with tabs[tab_idx]:
                st.markdown("**Webcam Capture**")
                captured_img = st.camera_input("Capture photo of your answer using webcam:", key=f"cam_{qid}")
                
                st.markdown("**OR Upload Image File**")
                uploaded_img = st.file_uploader(
                    "Upload answer image:",
                    type=["png", "jpg", "jpeg"],
                    key=f"file_img_{qid}"
                )

                if captured_img:
                    ans_state["image_bytes"] = captured_img.read()
                    ans_state["image_mime"] = captured_img.type
                    ans_state["answer_type"] = "Image"
                    st.success("Webcam photo captured successfully!")
                elif uploaded_img:
                    ans_state["image_bytes"] = uploaded_img.read()
                    ans_state["image_mime"] = uploaded_img.type
                    ans_state["answer_type"] = "Image"
                    st.image(ans_state["image_bytes"], caption="Uploaded Image Preview", width=300)

                if ans_state["image_bytes"] and ans_state["answer_type"] == "Image":
                    st.info("Selected answer format: Image")
            tab_idx += 1

        if "Audio" in allowed_formats:
            with tabs[tab_idx]:
                st.markdown("**Record Audio**")
                try:
                    from streamlit_mic_recorder import mic_recorder
                    audio_data = mic_recorder(
                        start_prompt="Start Recording",
                        stop_prompt="Stop Recording",
                        key=f"active_mic_{qid}"
                    )
                    if audio_data and audio_data.get("bytes"):
                        ans_state["audio_bytes"] = audio_data["bytes"]
                        ans_state["audio_mime"] = "audio/wav"
                        ans_state["answer_type"] = "Audio"
                except ImportError:
                    st.warning("streamlit-mic-recorder not installed. Use audio file upload below.")

                st.markdown("**OR Upload Audio File**")
                uploaded_audio = st.file_uploader(
                    "Upload audio answer:",
                    type=["wav", "mp3", "ogg", "m4a"],
                    key=f"file_aud_{qid}"
                )

                if uploaded_audio:
                    ans_state["audio_bytes"] = uploaded_audio.read()
                    ans_state["audio_mime"] = uploaded_audio.type or "audio/wav"
                    ans_state["answer_type"] = "Audio"

                if ans_state["audio_bytes"]:
                    st.audio(ans_state["audio_bytes"], format=ans_state.get("audio_mime", "audio/wav"))
                    st.info("Selected answer format: Audio")
            tab_idx += 1

    # Navigation Controls
    st.divider()
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if idx > 0:
            if st.button("Previous Question", use_container_width=True):
                st.session_state["current_question_index"] -= 1
                st.rerun()

    with col_nav3:
        if idx < len(questions) - 1:
            if st.button("Next Question", use_container_width=True):
                st.session_state["current_question_index"] += 1
                st.rerun()
        else:
            if st.button("Submit Assessment", type="primary", use_container_width=True):
                _submit_and_evaluate_exam()


def _submit_and_evaluate_exam():
    questions = st.session_state["test_questions"]
    answers = st.session_state["answers"]
    username = st.session_state.user["username"]
    student_details = st.session_state["student_details"]

    results = []

    progress_bar = st.progress(0.0)
    status_text = st.empty()

    for idx, q in enumerate(questions):
        qid = str(q.get("_id", f"dummy_{idx}"))
        ans = answers.get(qid, {
            "answer_type": "Text",
            "answer_text": "",
            "image_bytes": None,
            "image_mime": None,
            "audio_bytes": None,
            "audio_mime": None
        })

        status_text.text(f"Grading Question {idx + 1} of {len(questions)}: {q['title']}...")
        progress_bar.progress(idx / len(questions))

        # 1. MCQ Auto-Grading Script
        if q["type"] == "Multiple Choice":
            selected = ans["answer_text"]
            correct = q.get("correct_option")
            explanation = q.get("explanation", "No explanation provided.")

            # Normalize selected and correct to sets of options
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
            doc = {
                "student_username": username,
                "student_id": student_details["id"],
                "student_email": student_details["email"],
                "question_id": qid,
                "question_title": q["title"],
                "question_text": q["text"],
                "question_type": q["type"],
                "answer_type": "Text",
                "answer_text": f"Option(s) {selected_str}",
                "evaluation": eval_text,
                "submitted_at": datetime.now(timezone.utc),
            }

            insert_submission(doc)

            results.append({
                "title": q["title"],
                "text": q["text"],
                "type": q["type"],
                "selected": list(selected_set),
                "correct": list(correct_set),
                "explanation": explanation,
                "score": score,
                "max_score": q["marks"],
                "evaluation": eval_text,
                "ans_type": "Text",
                "answer_text": selected_str
            })

        # 2. AI Evaluation
        else:
            ans_type = ans["answer_type"]
            ans_text = ans["answer_text"]
            img_bytes = ans["image_bytes"]
            img_mime = ans["image_mime"]
            aud_bytes = ans["audio_bytes"]
            aud_mime = ans["audio_mime"]

            # Check if candidate provided absolutely no answer
            has_no_answer = (not ans_text or not ans_text.strip()) and not img_bytes and not aud_bytes

            if has_no_answer:
                evaluation = f"""## Verdict
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
                with st.spinner(f"AI is evaluating Question {idx + 1}..."):
                    try:
                        evaluation = evaluate_answer(
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
                        evaluation = f"AI Evaluation Error: {str(e)}"

                # Extract score from Gemini verdict (e.g. ## Score\n8/10)
                score_match = re.search(r"## Score\s*(\d+)", evaluation)
                extracted_score = int(score_match.group(1)) if score_match else 0

            doc = {
                "student_username": username,
                "student_id": student_details["id"],
                "student_email": student_details["email"],
                "question_id": qid,
                "question_title": q["title"],
                "question_text": q["text"],
                "question_type": q["type"],
                "answer_type": ans_type,
                "evaluation": evaluation,
                "submitted_at": datetime.now(timezone.utc),
            }

            if ans_text:
                doc["answer_text"] = ans_text
            if img_bytes:
                doc["answer_image"] = img_bytes
            if aud_bytes:
                doc["answer_audio"] = aud_bytes

            insert_submission(doc)

            results.append({
                "title": q["title"],
                "text": q["text"],
                "type": q["type"],
                "evaluation": evaluation,
                "score": extracted_score,
                "max_score": 10,
                "ans_type": ans_type,
                "answer_text": ans_text,
                "image_bytes": img_bytes,
                "audio_bytes": aud_bytes
            })

    progress_bar.progress(1.0)
    status_text.text("Exam submitted and evaluated successfully!")

    # Clear saved active exam state upon successful submission
    from db import delete_active_exam_state
    delete_active_exam_state(username)

    st.session_state["submission_results"] = results
    st.session_state["test_submitted"] = True
    st.session_state["test_active"] = False
    st.session_state["hardware_verified"] = False
    st.rerun()


def _render_submission_summary():
    st.markdown("## Assessment Submission Summary")
    st.success("Your assessment has been successfully submitted and evaluated!")

    details = st.session_state.get("student_details", {})
    st.markdown(f"**Candidate Name:** {details.get('name')} | **Student ID:** {details.get('id')} | **Email:** {details.get('email')}")

    results = st.session_state.get("submission_results", [])

    mcq_score = sum(r["score"] for r in results if r["type"] == "Multiple Choice")
    mcq_max = sum(r["max_score"] for r in results if r["type"] == "Multiple Choice")

    ai_score = sum(r["score"] for r in results if r["type"] != "Multiple Choice")
    ai_max = sum(r["max_score"] for r in results if r["type"] != "Multiple Choice")

    col1, col2 = st.columns(2)
    if mcq_max > 0:
        col1.metric("Auto-Graded MCQ Score", f"{mcq_score} / {mcq_max}")
    if ai_max > 0:
        col2.metric("AI-Graded Open Answer Score", f"{ai_score} / {ai_max}")

    st.divider()
    st.markdown("### Question-by-Question Evaluation Details")

    for idx, r in enumerate(results):
        with st.expander(f"**Q{idx + 1}: {r['title']}** — Score: {r['score']} / {r['max_score']}"):
            st.markdown(f"**Question:** {r['text']}")
            st.markdown("---")
            st.markdown("**Your Submission:**")
            if r["ans_type"] == "Text":
                st.info(r.get("answer_text") or "No answer provided")
            elif r["ans_type"] == "Image" and r.get("image_bytes"):
                st.image(r["image_bytes"], caption="Your webcam/uploaded image answer", width=400)
            elif r["ans_type"] == "Audio" and r.get("audio_bytes"):
                st.audio(r["audio_bytes"])

            st.markdown("---")
            st.markdown("### Evaluation Details")
            st.markdown(r["evaluation"])

    if st.button("Close & Return to Dashboard", type="primary", use_container_width=True):
        if "submission_results" in st.session_state:
            del st.session_state["submission_results"]
        st.session_state["test_submitted"] = False
        st.rerun()


def _results_tab():
    username = st.session_state.user["username"]
    submissions = get_submissions_by_student(username)

    st.subheader("Submission History")

    if not submissions:
        st.info("You haven't submitted any answers yet.")
        return

    st.metric("Total Submissions", len(submissions))
    st.divider()

    for sub in submissions:
        with st.expander(f"**{sub.get('question_title', 'N/A')}** — {sub['answer_type']} — {sub['submitted_at'].strftime('%Y-%m-%d %H:%M')}"):
            col1, col2 = st.columns(2)
            col1.markdown(f"**Question Type:** {sub.get('question_type', 'N/A')}")
            col2.markdown(f"**Answer Type:** {sub['answer_type']}")

            st.markdown(f"**Question:** {sub.get('question_text', '')}")

            if sub["answer_type"] == "Text":
                st.info(f"**Your Answer:** {sub.get('answer_text', '')}")
            elif sub["answer_type"] == "Image" and "answer_image" in sub:
                st.image(sub["answer_image"], caption="Your submitted image")
            elif sub["answer_type"] == "Audio" and "answer_audio" in sub:
                st.audio(sub["answer_audio"])

            st.divider()
            st.markdown("### Gemini Evaluation")
            st.markdown(sub.get("evaluation", "_Not evaluated_"))
