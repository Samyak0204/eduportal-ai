import streamlit as st
from datetime import datetime
from db import (
    get_all_questions, get_question_by_id,
    insert_submission, get_submissions_by_student, submission_exists
)
from gemini_eval import evaluate_answer


def student_dashboard():
    st.markdown(f"### 👋 Welcome, {st.session_state.user['name']}")

    tab1, tab2 = st.tabs(["📋 Questions", "📊 My Results"])

    with tab1:
        _questions_tab()

    with tab2:
        _results_tab()


def _questions_tab():
    questions = get_all_questions()
    if not questions:
        st.info("No questions available yet. Check back later!")
        return

    username = st.session_state.user["username"]
    st.subheader(f"📋 Available Questions ({len(questions)})")

    for q in questions:
        qid = str(q["_id"])
        already_done = submission_exists(username, qid)
        status = "✅ Submitted" if already_done else "⏳ Pending"

        with st.expander(f"**{q['title']}** — {q['type']} | {q['difficulty']} | {q['marks']} marks  |  {status}"):
            _render_question(q)

            if already_done:
                st.success("You have already submitted an answer for this question.")
                if st.button("👁️ View My Evaluation", key=f"view_{qid}"):
                    st.session_state[f"show_eval_{qid}"] = True

                if st.session_state.get(f"show_eval_{qid}"):
                    _show_my_evaluation(username, qid)
            else:
                _answer_form(q, qid, username)


def _render_question(q):
    st.markdown(f"**{q['text']}**")
    if "image_bytes" in q:
        st.image(q["image_bytes"], use_column_width=True)
    if "options" in q:
        for k, v in q["options"].items():
            st.markdown(f"**{k}.** {v}")


def _answer_form(q, qid, username):
    st.divider()
    st.markdown("#### 📝 Submit Your Answer")

    answer_tab1, answer_tab2, answer_tab3 = st.tabs(["✏️ Text", "🖼️ Image", "🎙️ Audio"])

    answer_text = None
    image_bytes = None
    image_mime = None
    audio_bytes = None
    answer_type = None

    with answer_tab1:
        if q["type"] == "Multiple Choice" and "options" in q:
            choices = {f"{k}. {v}": k for k, v in q["options"].items()}
            selected = st.radio("Choose your answer:", list(choices.keys()), key=f"mcq_{qid}")
            answer_text = choices[selected] if selected else None
        else:
            answer_text = st.text_area(
                "Type your answer here:",
                height=200,
                key=f"text_{qid}",
                placeholder="Write your full answer..."
            )

        if st.button("🚀 Submit Text Answer", key=f"sub_text_{qid}", use_container_width=True):
            if not answer_text or not answer_text.strip():
                st.error("Please enter an answer before submitting.")
            else:
                answer_type = "Text"
                _submit_and_evaluate(q, qid, username, answer_type,
                                     answer_text=answer_text)

    with answer_tab2:
        uploaded_img = st.file_uploader(
            "Upload an image of your answer (handwritten, diagram, etc.)",
            type=["png", "jpg", "jpeg"],
            key=f"img_{qid}"
        )
        if uploaded_img:
            st.image(uploaded_img, caption="Your answer image", use_column_width=True)

        if st.button("🚀 Submit Image Answer", key=f"sub_img_{qid}", use_container_width=True):
            if not uploaded_img:
                st.error("Please upload an image before submitting.")
            else:
                image_bytes = uploaded_img.read()
                image_mime = uploaded_img.type
                answer_type = "Image"
                _submit_and_evaluate(q, qid, username, answer_type,
                                     image_bytes=image_bytes, image_mime=image_mime)

    with answer_tab3:
        st.markdown("Record your spoken answer or upload an audio file:")

        audio_method = st.radio("Audio input method:", ["Upload audio file", "Record (browser mic)"], key=f"audio_method_{qid}")

        if audio_method == "Upload audio file":
            uploaded_audio = st.file_uploader(
                "Upload your audio answer",
                type=["wav", "mp3", "ogg", "m4a"],
                key=f"audio_file_{qid}"
            )
            if uploaded_audio:
                st.audio(uploaded_audio)
                if st.button("🚀 Submit Audio Answer", key=f"sub_audio_{qid}", use_container_width=True):
                    audio_bytes = uploaded_audio.read()
                    audio_mime = uploaded_audio.type or "audio/wav"
                    answer_type = "Audio"
                    _submit_and_evaluate(q, qid, username, answer_type,
                                         audio_bytes=audio_bytes, audio_mime=audio_mime)
        else:
            st.info("💡 To record from browser: Use the file upload above with a recorded .wav file, or use a browser extension to record and upload.")
            try:
                from streamlit_mic_recorder import mic_recorder
                audio_data = mic_recorder(
                    start_prompt="🎙️ Start Recording",
                    stop_prompt="⏹️ Stop Recording",
                    key=f"mic_{qid}"
                )
                if audio_data and audio_data.get("bytes"):
                    st.audio(audio_data["bytes"], format="audio/wav")
                    if st.button("🚀 Submit Recorded Answer", key=f"sub_mic_{qid}", use_container_width=True):
                        audio_bytes = audio_data["bytes"]
                        answer_type = "Audio"
                        _submit_and_evaluate(q, qid, username, answer_type,
                                             audio_bytes=audio_bytes, audio_mime="audio/wav")
            except ImportError:
                st.warning("streamlit-mic-recorder not installed. Please use file upload instead.")


def _submit_and_evaluate(q, qid, username, answer_type,
                          answer_text=None, image_bytes=None, image_mime=None,
                          audio_bytes=None, audio_mime=None):
    with st.spinner("🤖 Gemini is evaluating your answer..."):
        evaluation = evaluate_answer(
            question_text=q["text"],
            question_type=q["type"],
            answer_text=answer_text,
            image_bytes=image_bytes,
            image_mime=image_mime or "image/png",
            audio_bytes=audio_bytes,
            audio_mime=audio_mime or "audio/wav",
            options=q.get("options"),
            correct_option=q.get("correct_option"),
            ideal_answer=q.get("ideal_answer")
        )

    doc = {
        "student_username": username,
        "question_id": qid,
        "question_title": q["title"],
        "question_text": q["text"],
        "question_type": q["type"],
        "answer_type": answer_type,
        "evaluation": evaluation,
        "submitted_at": datetime.utcnow(),
    }

    if answer_text:
        doc["answer_text"] = answer_text
    if image_bytes:
        doc["answer_image"] = image_bytes
    if audio_bytes:
        doc["answer_audio"] = audio_bytes

    insert_submission(doc)
    st.session_state[f"show_eval_{qid}"] = True
    st.rerun()


def _show_my_evaluation(username, qid):
    from db import get_db
    db = get_db()
    sub = db.submissions.find_one({"student_username": username, "question_id": qid})
    if sub:
        st.markdown("### 🤖 Gemini Evaluation")
        st.markdown(sub.get("evaluation", "_No evaluation found._"))


def _results_tab():
    username = st.session_state.user["username"]
    submissions = get_submissions_by_student(username)

    st.subheader("📊 My Submission History")

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
            st.markdown("### 🤖 Gemini Evaluation")
            st.markdown(sub.get("evaluation", "_Not evaluated_"))
