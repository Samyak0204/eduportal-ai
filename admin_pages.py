import streamlit as st
from datetime import datetime
from db import (
    insert_question, get_all_questions, delete_question,
    get_all_submissions, get_all_students, create_user
)


QUESTION_TYPES = ["Multiple Choice", "Free Text / Essay", "Math / Equations", "Code Problem", "Image-Based"]


def admin_dashboard():
    st.markdown(f"### 👋 Welcome, {st.session_state.user['name']}")

    col1, col2, col3 = st.columns(3)
    questions = get_all_questions()
    submissions = get_all_submissions()
    students = get_all_students()

    col1.metric("📋 Total Questions", len(questions))
    col2.metric("📥 Total Submissions", len(submissions))
    col3.metric("🎓 Total Students", len(students))

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["➕ Upload Question", "📋 Manage Questions", "📊 View Submissions", "👤 Manage Students"])

    with tab1:
        _upload_question_tab()

    with tab2:
        _manage_questions_tab(questions)

    with tab3:
        _view_submissions_tab(submissions)

    with tab4:
        _manage_students_tab(students)


def _upload_question_tab():
    st.subheader("Upload a New Question")

    q_type = st.selectbox("Question Type", QUESTION_TYPES)

    # Inline tips for the selected question type
    if q_type == "Math / Equations":
        st.info(r"💡 **Tip:** You can write LaTeX equations. Wrap inline math in `$` (e.g., `$E = mc^2$`) and block equations in `$$` (e.g., `$$\int x dx$$`).")
    elif q_type == "Code Problem":
        st.info("💡 **Tip:** Write python or other code blocks using triple backticks: \n```python\n# your code here\n```")
    elif q_type == "Multiple Choice":
        st.info("💡 **Tip:** Provide Option A, B, C, and D details below. The student will select their choice.")

    with st.form("upload_question_form", clear_on_submit=True):
        title = st.text_input("Question Title / Label", placeholder="e.g. Q1 - Python Basics")
        question_text = st.text_area("Question Text", height=150,
                                     placeholder="Enter the full question here...")

        st.markdown("**Optional: Attach an image to the question**")
        q_image = st.file_uploader("Question Image (optional)", type=["png", "jpg", "jpeg", "gif"])

        opt_a = opt_b = opt_c = opt_d = correct_option = None
        ideal_answer = None

        if q_type == "Multiple Choice":
            st.markdown("**MCQ Options**")
            opt_a = st.text_input("Option A")
            opt_b = st.text_input("Option B")
            opt_c = st.text_input("Option C")
            opt_d = st.text_input("Option D")
            correct_option = st.selectbox("Correct Answer", ["A", "B", "C", "D"])
        else:
            ideal_answer = st.text_area(
                "Ideal Correct Answer / Solution / Grading Rubric (optional)",
                height=120,
                placeholder="Provide the complete ideal answer or key grading guidelines for Gemini..."
            )

        marks = st.number_input("Marks", min_value=1, max_value=100, value=10)
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        submitted = st.form_submit_button("📤 Upload Question", use_container_width=True)

    if submitted:
        if not title or not question_text:
            st.error("Title and Question Text are required.")
            return

        doc = {
            "title": title,
            "type": q_type,
            "text": question_text,
            "marks": marks,
            "difficulty": difficulty,
            "created_by": st.session_state.user["username"],
            "created_at": datetime.utcnow(),
        }

        if q_image:
            doc["image_bytes"] = q_image.read()
            doc["image_mime"] = q_image.type

        if q_type == "Multiple Choice" and opt_a:
            doc["options"] = {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d}
            doc["correct_option"] = correct_option
        elif ideal_answer and ideal_answer.strip():
            doc["ideal_answer"] = ideal_answer.strip()

        insert_question(doc)
        st.success(f"✅ Question '{title}' uploaded successfully!")


def _manage_questions_tab(questions):
    st.subheader("All Questions")
    if not questions:
        st.info("No questions uploaded yet.")
        return

    for q in questions:
        with st.expander(f"**{q['title']}** — {q['type']} | {q['difficulty']} | {q['marks']} marks"):
            st.markdown(f"**Question:** {q['text']}")
            if "image_bytes" in q:
                st.image(q["image_bytes"], caption="Attached Image", use_column_width=True)
            if "options" in q:
                for k, v in q["options"].items():
                    marker = "✅" if k == q.get("correct_option") else "  "
                    st.markdown(f"{marker} **{k}.** {v}")
            if "ideal_answer" in q:
                st.info(f"💡 **Ideal Answer / Rubric:**\n\n{q['ideal_answer']}")
            st.caption(f"Uploaded: {q['created_at'].strftime('%Y-%m-%d %H:%M')} by {q['created_by']}")
            if st.button(f"🗑️ Delete", key=f"del_{q['_id']}"):
                delete_question(str(q["_id"]))
                st.warning("Question deleted.")
                st.rerun()


def _view_submissions_tab(submissions):
    st.subheader("All Student Submissions")
    if not submissions:
        st.info("No submissions yet.")
        return

    for sub in submissions:
        with st.expander(f"👤 {sub['student_username']} — {sub.get('question_title', 'N/A')} — {sub['submitted_at'].strftime('%Y-%m-%d %H:%M')}"):
            st.markdown(f"**Answer Type:** {sub['answer_type']}")

            if sub["answer_type"] == "Text":
                st.markdown(f"**Answer:** {sub.get('answer_text', '')}")
            elif sub["answer_type"] == "Image":
                if "answer_image" in sub:
                    st.image(sub["answer_image"], caption="Student's Image Answer")
            elif sub["answer_type"] == "Audio":
                if "answer_audio" in sub:
                    st.audio(sub["answer_audio"])

            st.divider()
            st.markdown("### 🤖 Gemini Evaluation")
            st.markdown(sub.get("evaluation", "_Not evaluated yet_"))


def _manage_students_tab(students):
    st.subheader("Registered Students")

    if students:
        for s in students:
            st.markdown(f"- **{s['name']}** (`{s['username']}`) — joined {s['created_at'].strftime('%Y-%m-%d')}")
    else:
        st.info("No students registered yet.")

    st.divider()
    st.subheader("➕ Add New Student")

    with st.form("add_student_form", clear_on_submit=True):
        name = st.text_input("Full Name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Create Student Account", use_container_width=True)

    if submitted:
        if not name or not username or not password:
            st.error("All fields required.")
        else:
            ok, msg = create_user(username, password, "student", name)
            if ok:
                st.success(f"✅ Student '{name}' created.")
                st.rerun()
            else:
                st.error(msg)
