import streamlit as st
from db import seed_default_users, verify_user, get_db
from admin_pages import admin_dashboard
from student_pages import student_dashboard

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduPortal AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
    color: #f0f0f5 !important;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

/* Standard text elements */
.stApp p, .stApp li, .stApp span, .stApp strong, .stApp em, .stApp label, .stApp code {
    color: #f0f0f5 !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.1);
}
section[data-testid="stSidebar"] * {
    color: #f0f0f5 !important;
}

/* Cards / containers */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
}
div[data-testid="stExpander"] * {
    color: #f0f0f5 !important;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px;
    border: 1px solid rgba(255,255,255,0.12);
}
div[data-testid="metric-container"] div[data-testid="stMetricLabel"] {
    color: rgba(255, 255, 255, 0.7) !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-family: 'Sora', sans-serif;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102,126,234,0.4);
    color: white !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: rgba(255,255,255,0.7) !important;
    font-family: 'Sora', sans-serif;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
}

/* Input widget labels and choices */
.stWidgetFormLabel, label[data-testid="stWidgetLabel"], .stRadio label, .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label, .stFileUploader label {
    color: #ffffff !important;
    font-weight: 600 !important;
}

/* Text inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
    color: white !important;
    font-family: 'Sora', sans-serif !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
}
.stSelectbox div[data-baseweb="select"] * {
    color: white !important;
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    color: white !important;
    font-family: 'Sora', sans-serif !important;
}

/* Divider */
hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* Info/success/warning boxes */
.stAlert {
    border-radius: 10px !important;
}
.stAlert div[data-testid="stMarkdownContainer"] * {
    color: inherit !important;
}

/* Form */
.stForm {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    padding: 20px !important;
}
.stForm label {
    color: white !important;
}

/* Login card */
.login-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 20px;
    padding: 40px;
    backdrop-filter: blur(20px);
    max-width: 460px;
    margin: 60px auto;
}

.login-title {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea, #f093fb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 8px;
}

.login-subtitle {
    color: rgba(255,255,255,0.5) !important;
    text-align: center;
    margin-bottom: 32px;
    font-size: 0.95rem;
}

.role-badge-admin {
    background: linear-gradient(135deg, #f093fb, #f5576c);
    color: white !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}

.role-badge-student {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: #0f0c29 !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}

.stApp small, .stApp .stCaption {
    color: rgba(255, 255, 255, 0.6) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None
if "db_seeded" not in st.session_state:
    st.session_state.db_seeded = False


# ── Seed DB once ───────────────────────────────────────────────────────────
def try_seed():
    if not st.session_state.db_seeded:
        try:
            seed_default_users()
            st.session_state.db_seeded = True
        except Exception:
            pass


# ── Login screen ───────────────────────────────────────────────────────────
def login_screen():
    st.markdown("""
    <div class="login-card">
        <div class="login-title">🎓 EduPortal AI</div>
        <div class="login-subtitle">Powered by Google Gemini</div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Sign In")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user = verify_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

        st.divider()
        st.caption("**Default credentials (change after setup):**")
        st.caption("Admin: `admin` / `admin123`")
        st.caption("Student: `student1` / `student123`")


# ── Sidebar ────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎓 EduPortal AI")
        st.divider()

        user = st.session_state.user
        role_html = f'<span class="role-badge-{user["role"]}">{user["role"].upper()}</span>'
        st.markdown(f"**{user['name']}**  {role_html}", unsafe_allow_html=True)
        st.caption(f"@{user['username']}")
        st.divider()

        # DB connection status
        try:
            db = get_db()
            db.command("ping")
            st.success("🟢 MongoDB Connected")
        except Exception as e:
            st.error(f"🔴 MongoDB Error: {e}")

        st.divider()

        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.divider()
        st.caption("EduPortal AI v1.0")
        st.caption("Gemini 1.5 Flash | MongoDB")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    try_seed()

    if st.session_state.user is None:
        login_screen()
        return

    render_sidebar()

    role = st.session_state.user["role"]

    if role == "admin":
        admin_dashboard()
    elif role == "student":
        student_dashboard()
    else:
        st.error("Unknown role. Please contact admin.")


if __name__ == "__main__":
    main()
