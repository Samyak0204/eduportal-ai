import streamlit as st
from datetime import datetime, timezone
from db import (
    insert_question, get_all_questions, delete_question, update_question,
    get_all_submissions, get_all_students, create_user
)
from salesforce_questions import DUMMY_QUESTIONS

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


def _load_question_into_state(q, edit_mode=False):
    if edit_mode:
        st.session_state["edit_qid"] = str(q["_id"])
    else:
        if "edit_qid" in st.session_state:
            del st.session_state["edit_qid"]
            
    st.session_state["q_template_title"] = q["title"]
    st.session_state["q_template_type"] = q["type"]
    st.session_state["q_template_text"] = q["text"]
    st.session_state["q_template_is_multi_correct"] = q.get("is_multi_correct", False)
    
    if "options" in q:
        st.session_state["q_template_opt_a"] = q["options"].get("A", "")
        st.session_state["q_template_opt_b"] = q["options"].get("B", "")
        st.session_state["q_template_opt_c"] = q["options"].get("C", "")
        st.session_state["q_template_opt_d"] = q["options"].get("D", "")
        
        correct = q.get("correct_option", "A")
        if isinstance(correct, list):
            st.session_state["q_template_correct"] = correct
        else:
            st.session_state["q_template_correct"] = [correct] if correct else ["A"]
    else:
        st.session_state["q_template_opt_a"] = ""
        st.session_state["q_template_opt_b"] = ""
        st.session_state["q_template_opt_c"] = ""
        st.session_state["q_template_opt_d"] = ""
        st.session_state["q_template_correct"] = ["A"]
        
    st.session_state["q_template_explanation"] = q.get("explanation", "")
    st.session_state["q_template_marks"] = q["marks"]
    st.session_state["q_template_difficulty"] = q["difficulty"]
    st.session_state["q_template_ideal_answer"] = q.get("ideal_answer", "")
    st.session_state["q_template_image_bytes"] = q.get("image_bytes")
    st.session_state["q_template_image_mime"] = q.get("image_mime")
    
    formats = q.get("allowed_formats", ["Text"])
    st.session_state["q_template_allow_text"] = "Text" in formats
    st.session_state["q_template_allow_image"] = "Image" in formats
    st.session_state["q_template_allow_audio"] = "Audio" in formats


def _clear_form_state():
    for key in list(st.session_state.keys()):
        if key.startswith("q_template_") or key == "edit_qid":
            del st.session_state[key]


def _render_question_form(edit_qid=None):
    is_editing = edit_qid is not None

    # Find type index for dropdown
    current_type = st.session_state.get("q_template_type", "Multiple Choice")
    try:
        type_idx = QUESTION_TYPES.index(current_type)
    except ValueError:
        type_idx = 0

    q_type = st.selectbox(
        "Question Type", 
        QUESTION_TYPES, 
        index=type_idx, 
        key="q_select_type_edit" if is_editing else "q_select_type"
    )
    st.session_state["q_template_type"] = q_type

    # Inline tips for the selected question type
    if q_type == "Math / Equations":
        st.info(r"💡 **Tip:** You can write LaTeX equations. Wrap inline math in `$` (e.g., `$E = mc^2$`) and block equations in `$$` (e.g., `$$\int x dx$$`).")
    elif q_type == "Code Problem":
        st.info("💡 **Tip:** Write python or other code blocks using triple backticks: \n```python\n# your code here\n```")
    elif q_type == "Multiple Choice":
        st.info("💡 **Tip:** Provide Option A, B, C, and D details below. The student will select their choice.")

    # Render checkbox outside the form to trigger immediate rerun and toggle selectbox/multiselect
    is_multi = False
    if q_type == "Multiple Choice":
        is_multi = st.checkbox("Allow Multiple Correct Answers (Multi-Select)", key="q_template_is_multi_correct")

    with st.form("edit_question_form" if is_editing else "upload_question_form", clear_on_submit=not is_editing):
        title = st.text_input("Question Title / Label", placeholder="e.g. Q1 - Python Basics", key="q_template_title")
        question_text = st.text_area("Question Text", height=150, placeholder="Enter the full question here...", key="q_template_text")

        st.markdown("**Optional: Attach an image to the question**")
        if is_editing and st.session_state.get("q_template_image_bytes"):
            st.info("🖼️ Question currently has an image attached. Uploading a new file will overwrite it.")
        q_image = st.file_uploader("Question Image (optional)", type=["png", "jpg", "jpeg", "gif"], key="q_image_file_edit" if is_editing else "q_image_file_upload")

        opt_a = opt_b = opt_c = opt_d = correct_option = None
        ideal_answer = None

        if q_type == "Multiple Choice":
            st.markdown("**MCQ Options**")
            opt_a = st.text_input("Option A", key="q_template_opt_a")
            opt_b = st.text_input("Option B", key="q_template_opt_b")
            opt_c = st.text_input("Option C", key="q_template_opt_c")
            opt_d = st.text_input("Option D", key="q_template_opt_d")
            
            default_correct = st.session_state.get("q_template_correct", ["A"])
            if isinstance(default_correct, str):
                default_correct = [default_correct]
            elif not isinstance(default_correct, list):
                default_correct = ["A"]
                
            if is_multi:
                correct_option = st.multiselect("Correct Answer(s)", ["A", "B", "C", "D"], default=default_correct, key="q_template_correct_multiselect")
                st.session_state["q_template_correct"] = correct_option
            else:
                single_default = default_correct[0] if default_correct else "A"
                try:
                    correct_idx = ["A", "B", "C", "D"].index(single_default)
                except ValueError:
                    correct_idx = 0
                correct_option = st.selectbox("Correct Answer", ["A", "B", "C", "D"], index=correct_idx, key="q_template_correct_single")
                st.session_state["q_template_correct"] = [correct_option]
                
            allowed_formats = ["Text"]
        else:
            ideal_answer = st.text_area(
                "Ideal Correct Answer / Solution / Grading Rubric (optional)",
                height=120,
                placeholder="Provide the complete ideal answer or key grading guidelines for Gemini...",
                key="q_template_ideal_answer"
            )
            
            st.markdown("**Accepted Answer Formats**")
            col_f1, col_f2, col_f3 = st.columns(3)
            allow_text = col_f1.checkbox("Text Answer", key="q_template_allow_text")
            allow_image = col_f2.checkbox("Image Answer (Webcam/Upload)", key="q_template_allow_image")
            allow_audio = col_f3.checkbox("Audio Answer (Record/Upload)", key="q_template_allow_audio")
            
            allowed_formats = []
            if allow_text:
                allowed_formats.append("Text")
            if allow_image:
                allowed_formats.append("Image")
            if allow_audio:
                allowed_formats.append("Audio")

        explanation = st.text_area(
            "Explanation / Rationale for Correct Answer (optional)",
            height=120,
            placeholder="Provide a detailed explanation of why the correct answer is correct. For MCQs, this is graded/displayed automatically. For other types, this is passed to Gemini...",
            key="q_template_explanation"
        )

        marks = st.number_input("Marks", min_value=1, max_value=100, key="q_template_marks")
        
        try:
            diff_idx = ["Easy", "Medium", "Hard"].index(st.session_state.get("q_template_difficulty", "Easy"))
        except ValueError:
            diff_idx = 0
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=diff_idx, key="q_template_difficulty")
        
        col_submit, col_cancel = st.columns([4, 1]) if is_editing else (st.container(), None)
        
        if is_editing:
            with col_submit:
                submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
            with col_cancel:
                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True, on_click=_clear_form_state)
        else:
            submitted = st.form_submit_button("📤 Upload Question", use_container_width=True)
            cancel_edit = False

    if cancel_edit:
        st.rerun()

    if submitted:
        if not title or not question_text:
            st.error("Title and Question Text are required.")
            return

        if q_type != "Multiple Choice" and not allowed_formats:
            st.error("You must select at least one accepted answer format.")
            return

        doc = {
            "title": title,
            "type": q_type,
            "text": question_text,
            "marks": marks,
            "difficulty": difficulty,
            "allowed_formats": allowed_formats,
            "created_by": st.session_state.user["username"],
            "created_at": datetime.now(timezone.utc),
        }

        # Handle Image
        if q_image:
            doc["image_bytes"] = q_image.read()
            doc["image_mime"] = q_image.type
        elif is_editing:
            # Retain old image
            if st.session_state.get("q_template_image_bytes"):
                doc["image_bytes"] = st.session_state["q_template_image_bytes"]
                doc["image_mime"] = st.session_state.get("q_template_image_mime")

        if q_type == "Multiple Choice" and opt_a:
            doc["options"] = {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d}
            doc["correct_option"] = st.session_state.get("q_template_correct", ["A"])
            doc["is_multi_correct"] = st.session_state.get("q_template_is_multi_correct", False)
        elif ideal_answer and ideal_answer.strip():
            doc["ideal_answer"] = ideal_answer.strip()

        if explanation and explanation.strip():
            doc["explanation"] = explanation.strip()

        if is_editing:
            update_question(edit_qid, doc)
            _clear_form_state()
            st.success("✅ Question updated successfully!")
        else:
            insert_question(doc)
            _clear_form_state()
            st.success("✅ Question uploaded successfully!")
            
        st.rerun()


def _upload_question_tab():
    st.subheader("Upload a New Question")

    # Initialize session state keys for templates if not present
    if "q_template_title" not in st.session_state:
        st.session_state["q_template_title"] = ""
    if "q_template_type" not in st.session_state:
        st.session_state["q_template_type"] = "Multiple Choice"
    if "q_template_text" not in st.session_state:
        st.session_state["q_template_text"] = ""
    if "q_template_opt_a" not in st.session_state:
        st.session_state["q_template_opt_a"] = ""
    if "q_template_opt_b" not in st.session_state:
        st.session_state["q_template_opt_b"] = ""
    if "q_template_opt_c" not in st.session_state:
        st.session_state["q_template_opt_c"] = ""
    if "q_template_opt_d" not in st.session_state:
        st.session_state["q_template_opt_d"] = ""
    if "q_template_correct" not in st.session_state:
        st.session_state["q_template_correct"] = "A"
    if "q_template_explanation" not in st.session_state:
        st.session_state["q_template_explanation"] = ""
    if "q_template_marks" not in st.session_state:
        st.session_state["q_template_marks"] = 10
    if "q_template_difficulty" not in st.session_state:
        st.session_state["q_template_difficulty"] = "Easy"
    if "q_template_ideal_answer" not in st.session_state:
        st.session_state["q_template_ideal_answer"] = ""
    if "q_template_allow_text" not in st.session_state:
        st.session_state["q_template_allow_text"] = True
    if "q_template_allow_image" not in st.session_state:
        st.session_state["q_template_allow_image"] = True
    if "q_template_allow_audio" not in st.session_state:
        st.session_state["q_template_allow_audio"] = True

    # ── Template Loader Expandable ───────────────────────────────────────────
    with st.expander("💡 Load Salesforce Dummy Question Templates"):
        st.caption("You can load these sample questions into the form to quickly review or manually add them to the database.")
        for idx, dq in enumerate(DUMMY_QUESTIONS):
            col_l, col_r = st.columns([4, 1])
            with col_l:
                st.markdown(f"**{idx+1}. {dq['title']}** — *{dq['type']}*")
                st.markdown(f"{dq['text']}")
                if "options" in dq:
                    for k, v in dq["options"].items():
                        st.markdown(f"- **{k}:** {v}")
                st.markdown(f"**Marks:** {dq['marks']} | **Difficulty:** {dq['difficulty']}")
                if "explanation" in dq:
                    st.caption(f"**Explanation:** {dq['explanation']}")
            with col_r:
                st.button(
                    "📋 Load Template", 
                    key=f"load_tpl_{idx}",
                    on_click=_load_question_into_state,
                    args=(dq, False)
                )

    # If currently editing a question, notify user on this tab
    edit_qid = st.session_state.get("edit_qid")
    if edit_qid:
        st.warning(f"⚠️ Form is currently in EDIT MODE on the 'Manage Questions' tab. Uploading a new question is disabled until you cancel or save changes.")
    else:
        _render_question_form(edit_qid=None)


def _manage_questions_tab(questions):
    # If editing, render form at the top of this tab
    edit_qid = st.session_state.get("edit_qid")
    if edit_qid:
        st.markdown(f"### ✏️ Edit Question")
        _render_question_form(edit_qid=edit_qid)
        st.divider()

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
                correct_opts = q.get("correct_option", [])
                correct_list = [correct_opts] if isinstance(correct_opts, str) else correct_opts
                for k, v in q["options"].items():
                    marker = "✅" if k in correct_list else "  "
                    st.markdown(f"{marker} **{k}.** {v}")
            if "ideal_answer" in q:
                st.info(f"💡 **Ideal Answer / Rubric:**\n\n{q['ideal_answer']}")
            if q.get("type") != "Multiple Choice" and "allowed_formats" in q:
                st.markdown(f"**Allowed Student Answer Formats:** {', '.join(q['allowed_formats'])}")
            if q.get("explanation"):
                st.markdown(f"📘 **Explanation / Rationale:**\n\n{q['explanation']}")
            st.caption(f"Uploaded: {q['created_at'].strftime('%Y-%m-%d %H:%M')} by {q['created_by']}")
            
            # Action buttons row
            col_qm1, col_qm2 = st.columns([1, 6])
            with col_qm1:
                st.button(
                    "Edit", 
                    key=f"edit_btn_{q['_id']}", 
                    use_container_width=True,
                    on_click=_load_question_into_state,
                    args=(q, True)
                )
            with col_qm2:
                if st.button(f"Delete", key=f"del_{q['_id']}"):
                    delete_question(str(q["_id"]))
                    st.warning("Question deleted.")
                    st.rerun()


def _view_submissions_tab(submissions):
    st.subheader("All Student Submissions")
    if not submissions:
        st.info("No submissions yet.")
        return

    for sub in submissions:
        with st.expander(f"{sub['student_username']} — {sub.get('question_title', 'N/A')} — {sub['submitted_at'].strftime('%Y-%m-%d %H:%M')}"):
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
            st.markdown("### Gemini Evaluation")
            st.markdown(sub.get("evaluation", "_Not evaluated yet_"))


def _manage_students_tab(students):
    st.subheader("Registered Students")

    if students:
        for s in students:
            st.markdown(f"- **{s['name']}** (`{s['username']}`) — joined {s['created_at'].strftime('%Y-%m-%d')}")
    else:
        st.info("No students registered yet.")

    st.divider()
    st.subheader("Add New Student")

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
                st.success(f"Student '{name}' created.")
                st.rerun()
            else:
                st.error(msg)
