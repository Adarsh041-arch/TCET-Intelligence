import streamlit as st
import requests
import json
import time

# -------------------------------------------------------------
# Configuration and Styling Constants
# -------------------------------------------------------------
API_BASE_URL = "http://localhost:8000/api"
APP_NAME = "TCET Intelligence Portal"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark-Muted Premium CSS Theme
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Overrides */
    * {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background-color: #060913;
        color: #f3f4f6;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0c1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #f3f4f6;
    }

    /* Custom Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background-color: #111827 !important;
        color: #f3f4f6 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    /* Custom Buttons */
    .stButton > button {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }

    .stButton > button:hover {
        background-color: #334155 !important;
        border-color: #6366f1 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15) !important;
    }
    
    .stButton > button:active {
        transform: translateY(1px) !important;
    }

    /* Highlight Primary Buttons */
    div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    div.stButton > button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
    }

    /* Selectbox */
    .stSelectbox > div > div > div {
        background-color: #111827 !important;
        color: #f3f4f6 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0c1120 !important;
        border-radius: 8px;
        padding: 4px;
        border: 1px solid #1e293b;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #9ca3af !important;
        border-radius: 6px;
        padding: 8px 16px !important;
        font-weight: 500 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }

    /* Chat Messages */
    div[data-testid="stChatMessage"] {
        background-color: #0c1120 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    div[data-testid="stChatMessage"][data-test-avatar="user"] {
        background-color: #13172c !important;
        border-color: #272e5c !important;
    }

    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #0c1120 !important;
        border: 1px solid #1e293b !important;
        padding: 16px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* File Uploader styling */
    [data-testid="stFileUploader"] {
        background-color: #0c1120 !important;
        border: 2px dashed #334155 !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }
    
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
    }

    /* Custom Glass Container */
    .glass-card {
        background: rgba(12, 17, 32, 0.75);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 32px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
    }
    
    .welcome-card {
        background: linear-gradient(135deg, #0d1222 0%, #151c33 100%);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 40px;
        margin-bottom: 24px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    
    .welcome-card h2 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .suggestion-btn {
        background-color: #0f172a !important;
        border: 1px solid #1e293b !important;
        color: #cbd5e1 !important;
        text-align: left !important;
        padding: 14px 18px !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        display: block !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        height: auto !important;
    }
    
    .suggestion-btn:hover {
        background-color: #1e293b !important;
        border-color: #6366f1 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1) !important;
    }

    .pill-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-right: 8px;
    }
    
    .pill-rag {
        background-color: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    .pill-sql {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border-color: rgba(16, 185, 129, 0.3);
    }

    .pill-filesystem {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.3);
    }

    .pill-general {
        background-color: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border-color: rgba(107, 114, 128, 0.3);
    }
    
    /* Code blocks formatting */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.9em !important;
    }

    .stDivider {
        border-color: #1e293b !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
def init_session_state():
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "page" not in st.session_state:
        st.session_state.page = "chat"
    if "sessions" not in st.session_state:
        st.session_state.sessions = []
    if "documents" not in st.session_state:
        st.session_state.documents = {"documents": [], "total_chunks": 0}
    if "stop_generation" not in st.session_state:
        st.session_state.stop_generation = False
    if "generating" not in st.session_state:
        st.session_state.generating = False
    if "chat_input_trigger" not in st.session_state:
        st.session_state.chat_input_trigger = None

# -------------------------------------------------------------
# API Service Layer
# -------------------------------------------------------------
def check_health():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def load_sessions():
    if not st.session_state.token:
        return []
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            st.session_state.sessions = response.json().get("sessions", [])
    except:
        pass
    return st.session_state.sessions

def load_documents():
    if not st.session_state.token:
        return {"documents": [], "total_chunks": 0}
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/documents", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            st.session_state.documents = response.json()
    except:
        pass
    return st.session_state.documents

def api_login(username, password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user = {
                "user_id": data["user_id"],
                "username": data["username"],
                "role": data["role"],
            }
            load_sessions()
            load_documents()
            return True
    except Exception as e:
        st.error(f"Authentication backend error: {e}")
    return False

def api_register(username, password, role):
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={"username": username, "password": password, "role": role},
            timeout=10,
        )
        return response.status_code == 200
    except:
        return False

def api_create_session():
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions", json={}, headers=get_headers(), timeout=10
        )
        if response.status_code == 200:
            session_id = response.json()["session_id"]
            load_sessions()
            return session_id
    except:
        pass
    return None

def api_get_history(session_id):
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions/{session_id}/history",
            headers=get_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("messages", [])
    except:
        pass
    return []

def api_send_message_stream(session_id, message, attached_files=None):
    try:
        payload = {"session_id": session_id, "message": message}
        if attached_files:
            payload["attached_files"] = attached_files
        response = requests.post(
            f"{API_BASE_URL}/chat/stream",
            json=payload,
            headers=get_headers(),
            stream=True,
            timeout=200,
        )
        if response.status_code == 200:
            return response
    except:
        pass
    return None

def api_upload_document(file):
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(
            f"{API_BASE_URL}/admin/documents/upload",
            files=files,
            headers=get_headers(),
            timeout=120,
        )
        load_documents()
        if response.status_code != 200:
            return {"success": False, "message": response.json().get("detail", "Upload failed")}
        return response.json()
    except:
        return {"success": False, "message": "File processing timeout or connection failure."}

def api_delete_document(doc_id):
    try:
        response = requests.delete(
            f"{API_BASE_URL}/admin/documents/{doc_id}",
            headers=get_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            load_documents()
            return True
    except:
        pass
    return False

def api_sql_status():
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/sql/status", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"connected": False, "db_type": None}

def api_sql_connect(
    db_type, host="localhost", port=3306, user="root", password="", database="", path=""
):
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/sql/connect",
            json={
                "db_type": db_type,
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "database": database,
                "path": path,
            },
            headers=get_headers(),
            timeout=10,
        )
        return response.json()
    except:
        return {"success": False, "error": "Connection error"}

def api_sql_disconnect():
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/sql/disconnect", headers=get_headers(), timeout=5
        )
        return response.json()
    except:
        return {"success": False}

def api_sql_tables():
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/sql/tables", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"success": False, "tables": []}

def api_sql_schema(table_name):
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/sql/schema/{table_name}",
            headers=get_headers(),
            timeout=5,
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"success": False}

def api_tcet_docs():
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/tcet-docs", headers=get_headers(), timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"files": [], "total": 0, "indexed": 0, "unindexed": 0}

def api_index_tcet_docs(file_names):
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/tcet-docs/index",
            json={"file_names": file_names},
            headers=get_headers(),
            timeout=300,
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"results": []}

def api_sql_query(query):
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/sql/query",
            json={"query": query},
            headers=get_headers(),
            timeout=30,
        )
        return response.json()
    except:
        return {"success": False, "error": "Database connection or query syntax error"}

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.current_session_id = None
    st.session_state.messages = []
    st.session_state.page = "chat"
    st.session_state.sessions = []
    st.session_state.documents = {"documents": [], "total_chunks": 0}

# -------------------------------------------------------------
# UI Component Renderers
# -------------------------------------------------------------
def render_login_page():
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.8, 1])

    with col2:
        st.markdown(
            f"""
            <div class='glass-card' style='text-align: center; margin-bottom: 20px;'>
                <div style='font-size: 3.5rem; margin-bottom: 10px;'>⚡</div>
                <h1 style='margin: 0; color: #f3f4f6; font-size: 2.2rem; font-weight: 700;'>{APP_NAME}</h1>
                <p style='color: #9ca3af; margin-top: 8px;'>Institutional RAG & SQL Decision Engine</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["🔒 Secure Login", "✉️ Register Account"])

        with tab1:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter username...", key="login_user")
                password = st.text_input("Password", type="password", placeholder="Enter password...", key="login_pass")
                submit = st.form_submit_button("Authenticate Access", type="primary")
                
                if submit:
                    if username.strip() and password.strip():
                        with st.spinner("Verifying credentials..."):
                            if api_login(username, password):
                                st.rerun()
                            else:
                                st.error("Access Denied: Invalid username or password.")
                    else:
                        st.warning("Please fill in all credential fields.")
                        
            st.markdown(
                """
                <div style='text-align: center; color: #6b7280; font-size: 0.85rem; margin-top: 12px;'>
                    Default Admin Credentials: <code style='color: #a5b4fc;'>admin</code> / <code style='color: #a5b4fc;'>admin123</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab2:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input("Choose Username", placeholder="e.g., student_123", key="reg_user")
                reg_password = st.text_input("Create Password", type="password", placeholder="Password...", key="reg_pass")
                reg_role = st.selectbox("Role Scope", ["user", "admin"], key="reg_role")
                register_submit = st.form_submit_button("Provision Account", type="primary")
                
                if register_submit:
                    if reg_username.strip() and reg_password.strip():
                        with st.spinner("Provisioning account..."):
                            if api_register(reg_username, reg_password, reg_role):
                                st.success("Account provisioned successfully! Proceed to sign in.")
                            else:
                                st.error("Account Creation Failed: Username already exists.")
                    else:
                        st.warning("Please fill in all registration fields.")

def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"""
            <div style='padding: 10px 0 20px 0; border-bottom: 1px solid #1e293b; margin-bottom: 20px;'>
                <h3 style='margin: 0; color: #ffffff; font-weight: 700; font-size: 1.3rem; display: flex; align-items: center;'>
                    <span style='margin-right: 8px;'>⚡</span> TCET Portal
                </h3>
                <span style='display: inline-block; background-color: #1e1b4b; color: #a5b4fc; border: 1px solid #312e81; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; margin-top: 8px; text-transform: uppercase; font-weight: 600;'>
                    {st.session_state.user['role']} Console
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Quick Actions Section
        if st.button("➕ New Chat Session", type="primary", use_container_width=True):
            session_id = api_create_session()
            if session_id:
                st.session_state.current_session_id = session_id
                st.session_state.messages = []
                st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8rem; color: #4b5563; font-weight: 700; text-transform: uppercase;'>Conversation History</div>", unsafe_allow_html=True)

        sessions = st.session_state.sessions if st.session_state.sessions else load_sessions()

        if sessions:
            for session in sessions:
                session_name = session.get("session_name", "Untitled Session") or "Untitled Session"
                is_active = st.session_state.current_session_id == session["session_id"]
                
                # Active vs Inactive Styling
                label = session_name[:24] + "..." if len(session_name) > 24 else session_name
                icon = "💬" if not is_active else "⭐"
                
                if st.button(
                    f"{icon} {label}",
                    key=f"session_{session['session_id']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.current_session_id = session["session_id"]
                    st.session_state.messages = []
                    st.rerun()
        else:
            st.markdown("<div style='color: #6b7280; font-size: 0.85rem; padding: 10px 0;'>No active chat history.</div>", unsafe_allow_html=True)

        # Admin Panel Scopes
        if st.session_state.user["role"] == "admin":
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.8rem; color: #4b5563; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;'>Administrative Scopes</div>", unsafe_allow_html=True)
            
            # Sub-Menu buttons
            pages = {
                "chat": "💬 Chat Interface",
                "upload": "📤 Index Documents",
                "documents": "📚 Knowledge Base",
                "tcet_docs": "📄 TCET Docs",
                "database": "🗄️ Database Hub",
                "sql": "🔗 SQL Console"
            }
            
            for page_key, page_label in pages.items():
                is_current = st.session_state.page == page_key
                if st.button(
                    page_label,
                    key=f"nav_{page_key}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary"
                ):
                    st.session_state.page = page_key
                    st.rerun()

        # User Footer
        st.markdown(
            f"""
            <div style='position: absolute; bottom: 70px; left: 10px; right: 10px; padding: 12px; border-top: 1px solid #1e293b; background-color: #080d1a; border-radius: 8px;'>
                <div style='font-size: 0.85rem; color: #e2e8f0; font-weight: 600;'>{st.session_state.user['username']}</div>
                <div style='font-size: 0.75rem; color: #64748b;'>Scope: {st.session_state.user['role']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Position logout below the user info block
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Terminate Session", use_container_width=True):
            logout()
            st.rerun()

def stop_callback():
    st.session_state.stop_generation = True
    st.session_state.generating = False

def handle_suggestion_click(query_text):
    st.session_state.chat_input_trigger = query_text

def render_chat():
    st.markdown("<h2 style='margin-top: 0;'>💬 Chat Interface</h2>", unsafe_allow_html=True)

    if not st.session_state.current_session_id:
        st.markdown(
            """
            <div class='welcome-card'>
                <div style='font-size: 3rem; margin-bottom: 10px;'>👋</div>
                <h2 style='color: #ffffff; margin-top:0;'>Welcome to TCET Intelligence</h2>
                <p style='color: #94a3b8; max-width: 550px; margin: 10px auto;'>
                    Start a new conversation session to ask questions about college curriculum, 
                    retrieve records using RAG from documentation, or query structural database information.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🚀 Initialize New Chat Session", type="primary"):
            session_id = api_create_session()
            if session_id:
                st.session_state.current_session_id = session_id
                st.session_state.messages = []
                st.rerun()
        return

    # Check for suggested prompt queries clicked
    active_prompt = None
    if st.session_state.chat_input_trigger:
        active_prompt = st.session_state.chat_input_trigger
        st.session_state.chat_input_trigger = None

    messages = api_get_history(st.session_state.current_session_id)

    # Empty State with Suggestion Cards
    if not messages and not active_prompt:
        st.markdown(
            """
            <div class='welcome-card' style='padding: 30px;'>
                <h3 style='color: #ffffff; margin-top:0;'>How can I help you today?</h3>
                <p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;'>
                    Select a curated institutional template query below or type your inquiry in the search bar.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Grid of Suggestion Cards
        col1, col2 = st.columns(2)
        
        suggestions_left = [
            ("📄 Analyze the recent syllabus structure", "Summarize structural changes in the syllabus documents."),
            ("🏫 Tell me about IT courses", "List curricular information regarding Information Technology courses.")
        ]
        suggestions_right = [
            ("📊 SQL: Show student attendance rates", "Check for students with low attendance patterns in the database."),
            ("📁 Create a directory test", "Test filesystem agent capabilities by listing system structure.")
        ]
        
        with col1:
            for title, desc in suggestions_left:
                if st.button(f"💡 {title}\n— {desc}", key=f"sug_{title}", use_container_width=True):
                    handle_suggestion_click(title)
                    st.rerun()
                    
        with col2:
            for title, desc in suggestions_right:
                if st.button(f"💡 {title}\n— {desc}", key=f"sug_{title}", use_container_width=True):
                    handle_suggestion_click(title)
                    st.rerun()

    # Render History
    for msg in messages:
        role = msg["role"]
        avatar = "👤" if role == "user" else "⚡"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # Chat Input Box
    chat_input_val = st.chat_input("Inquire about syllabus, courses, SQL data, or documents...", accept_file="multiple")

    if chat_input_val:
        if isinstance(chat_input_val, dict) or hasattr(chat_input_val, "text"):
            active_prompt = chat_input_val.text if hasattr(chat_input_val, "text") else chat_input_val.get("text", "")
            files = chat_input_val.files if hasattr(chat_input_val, "files") else chat_input_val.get("files", [])
        else:
            active_prompt = chat_input_val
            files = []
    else:
        files = []

    # Processing Inquiries
    if active_prompt:
        # Display user message instantly
        with st.chat_message("user", avatar="👤"):
            if files:
                for file in files:
                    st.write(f"📎 **{file.name}**")
                    with st.spinner(f"Indexing context of {file.name}..."):
                        res = api_upload_document(file)
                        if res.get("success"):
                            st.caption(f"✅ Context parsed and successfully indexed.")
                        else:
                            msg = res.get("message", "Ingestion failed")
                            if "already exists" in msg.lower():
                                st.caption(f"✅ Already present in RAG storage index")
                            else:
                                st.caption(f"❌ {msg}")
            if active_prompt:
                st.markdown(active_prompt)

        # Trigger Backend stream
        if active_prompt:
            st.session_state.stop_generation = False
            st.session_state.generating = True

            # Assistant response card block
            with st.chat_message("assistant", avatar="⚡"):
                response_placeholder = st.empty()
                full_response = ""

                # Stop Button during active stream
                stop_btn_placeholder = st.empty()
                with stop_btn_placeholder:
                    st.button("⏹️ Stop Stream Response", key="stop_btn", on_click=stop_callback)

                attached_filenames = [f.name for f in files] if files else None
                res_obj = api_send_message_stream(st.session_state.current_session_id, active_prompt, attached_filenames)

                metadata = {}
                if res_obj:
                    stream = res_obj.iter_lines(decode_unicode=True)
                    try:
                        for line in stream:
                            if st.session_state.get("stop_generation"):
                                res_obj.close()
                                break
                            if line.startswith("data: "):
                                data = json.loads(line[6:])
                                if not data.get("done"):
                                    token = data.get("token", "")
                                    if token:
                                        full_response += token
                                        response_placeholder.markdown(full_response + "▌")
                                else:
                                    metadata = data
                                    break
                    except Exception as e:
                        st.error(f"Streaming transmission failure: {e}")
                    finally:
                        res_obj.close()
                        st.session_state.generating = False

                    stop_btn_placeholder.empty()

                    if st.session_state.get("stop_generation"):
                        st.session_state.stop_generation = False
                        st.warning("Response generation cancelled by user.")
                        st.rerun()

                    # Render complete clean output
                    response_placeholder.markdown(full_response)

                    # Dynamic metadata footer badge panel
                    source = metadata.get("source", "general").lower()
                    time_val = metadata.get("response_time", 0)
                    time_str = f"{time_val:.2f}s" if time_val >= 1 else f"{time_val * 1000:.0f}ms"
                    
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    
                    # Pill layout
                    badge_class = f"pill-badge pill-{source}"
                    st.markdown(
                        f"""
                        <div>
                            <span class='{badge_class}'>📍 {source}</span>
                            <span class='pill-badge' style='background-color: rgba(255,255,255,0.05); color: #cbd5e1;'>⏱️ Latency: {time_str}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Retrieved Documents Accodion panel
                    if metadata.get("retrieved_docs"):
                        with st.expander("📚 Retrieved Documentation Context Chunks"):
                            for i, doc in enumerate(metadata["retrieved_docs"], 1):
                                st.markdown(
                                    f"""
                                    <div style='background-color: #0f172a; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #1e293b;'>
                                        <div style='font-size: 0.85rem; font-weight: 600; color: #a5b4fc; display:flex; justify-content:space-between;'>
                                            <span>📄 Chunk {i}: {doc['filename']}</span>
                                            <span style='color: #34d399;'>Match Score: {doc['similarity'] * 100:.1f}%</span>
                                        </div>
                                        <div style='font-size: 0.85rem; color: #cbd5e1; margin-top: 6px; font-family: sans-serif;'>
                                            {doc['content']}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                    
                    load_sessions()
                    st.rerun()
                else:
                    response_placeholder.markdown("⚠️ Endpoint connection failed. Please re-run the server backend.")

def render_upload():
    st.markdown("<h2 style='margin-top: 0;'>📤 Index Documents</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;'>
            Upload academic documents, schedules, CSV tables, or text indexes. 
            The system will automatically parse, chunk, and index them into the persistent vector storage.
        </p>
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Select Institutional Documents",
        type=["pdf", "txt", "docx", "xlsx", "xls", "csv", "json", "html"],
    )

    if uploaded_file:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style='background-color: #0c1120; border: 1px solid #1e293b; padding: 15px; border-radius: 8px;'>
                <div style='font-size: 0.9rem; color: #ffffff;'>📄 File: <b>{uploaded_file.name}</b></div>
                <div style='font-size: 0.8rem; color: #64748b; margin-top:4px;'>Size: {uploaded_file.size / 1024:.1f} KB</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        if st.button("🚀 Process & Generate Embeddings", type="primary"):
            with st.spinner("Processing..."):
                result = api_upload_document(uploaded_file)
                if result.get("success"):
                    st.success(f"Successfully processed! {result.get('chunks_created', 0)} embedding chunks added to database.")
                    load_documents()
                else:
                    st.error(result.get("message", "Processing failure"))

def render_documents():
    st.markdown("<h2 style='margin-top: 0;'>📚 Knowledge Base Management</h2>", unsafe_allow_html=True)
    
    docs_data = st.session_state.documents if st.session_state.documents else load_documents()
    
    # Grid of Dashboard stats
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Indexed Chunks", docs_data.get("total_chunks", 0))
    with col2:
        st.metric("Unique Document Index", len(docs_data.get("documents", [])))
        
    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("<h4>Indexed Document Directory</h4>", unsafe_allow_html=True)

    documents = docs_data.get("documents", [])
    if documents:
        for doc in documents:
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"""
                    <div style='background-color: #0c1120; border: 1px solid #1e293b; padding: 16px; border-radius: 8px;'>
                        <div style='font-size: 1rem; font-weight:600; color: #ffffff;'>📄 {doc['filename']}</div>
                        <div style='font-size: 0.8rem; color: #64748b; margin-top: 4px;'>
                            Format Scope: <span style='color:#a5b4fc;'>{doc['file_type']}</span> · Ingested Date: {doc['uploaded_at'][:10]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_del:
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_{doc['doc_id']}", type="secondary"):
                    with st.spinner("Deleting embeddings..."):
                        if api_delete_document(doc["doc_id"]):
                            st.success("Deleted!")
                            st.rerun()
    else:
        st.info("No documents present in RAG vector storage index.")

def render_database():
    st.markdown("<h2 style='margin-top: 0;'>🗄️ Database Hub</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Manage system DB connection parameters and visualize database relations schema.</p>", unsafe_allow_html=True)

    status = api_sql_status()

    if status.get("connected"):
        st.success(f"Connected: Active engine linked to {status.get('db_type', '').upper()} schema.")

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Close Link", type="primary"):
                api_sql_disconnect()
                st.rerun()

        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        st.subheader("Schema Analyzer")

        tables_data = api_sql_tables()
        if tables_data.get("success"):
            for table in tables_data.get("tables", []):
                schema_data = api_sql_schema(table)
                with st.expander(f"📋 Table: {table}"):
                    if schema_data.get("success"):
                        schema = schema_data.get("schema", {})
                        cols = schema.get("columns", [])
                        
                        col_details = ""
                        for col in cols:
                            col_details += f"<li><b>{col['name']}</b> ({col['type']}) {'🔑 Primary Key' if col.get('pk') else ''}</li>"
                            
                        st.markdown(
                            f"""
                            <div style='background-color:#070a13; padding: 15px; border-radius: 8px; border: 1px solid #1e293b;'>
                                <ul style='margin:0; padding-left: 20px; color:#cbd5e1;'>
                                    {col_details}
                                </ul>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    else:
        st.warning("Database Link Offline: Relational features restricted.")
        
        st.markdown("<h4>Connect SQL Database</h4>", unsafe_allow_html=True)
        db_type = st.selectbox("Database Technology", ["sqlite", "mysql", "postgresql"])

        with st.form("db_connect_form"):
            if db_type == "sqlite":
                path = st.text_input("Local Database File Path", value="data/institution.db")
                submit = st.form_submit_button("Initialize Database Link", type="primary")
                if submit:
                    res = api_sql_connect("sqlite", path=path)
                    if res.get("success"):
                        st.success("Successfully connected!")
                        st.rerun()
                    else:
                        st.error(res.get("error", "Link initiation failed."))
            else:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    host = st.text_input("Server Host address", value="localhost")
                    database = st.text_input("Database Schema Name")
                with col_c2:
                    port = st.number_input("Port", value=3306 if db_type == "mysql" else 5432)
                    user = st.text_input("Authentication User ID", value="root")
                password = st.text_input("Access Password Credentials", type="password")
                
                submit = st.form_submit_button("Initialize Link", type="primary")
                if submit:
                    res = api_sql_connect(db_type, host=host, port=port, user=user, password=password, database=database)
                    if res.get("success"):
                        st.success("Successfully connected!")
                        st.rerun()
                    else:
                        st.error(res.get("error", "Access denied or host unreachable."))

def render_sql():
    st.markdown("<h2 style='margin-top: 0;'>🔗 SQL Console</h2>", unsafe_allow_html=True)

    status = api_sql_status()

    if not status.get("connected"):
        st.warning("Database offline. Please setup database credentials in Database Hub page first.")
        if st.button("Go to Database Hub"):
            st.session_state.page = "database"
            st.rerun()
        return

    tables_data = api_sql_tables()
    if tables_data.get("success"):
        tables_list = ", ".join([f"<code>{t}</code>" for t in tables_data.get("tables", [])])
        st.markdown(
            f"""
            <div style='background-color:#0c1120; border: 1px solid #1e293b; padding:12px; border-radius: 8px; font-size:0.9rem;'>
                💡 <b>Relational Tables Found:</b> {tables_list}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    with st.form("sql_query_form"):
        query = st.text_area("Write SQL Statement", placeholder="SELECT * FROM students LIMIT 10;", height=120)
        run = st.form_submit_button("Execute Statement", type="primary")
        
        if run:
            if query.strip():
                with st.spinner("Executing transaction..."):
                    result = api_sql_query(query)
                    if result.get("success"):
                        if result.get("type") == "select":
                            st.success(f"Query completed: {result.get('row_count', 0)} records returned.")
                            if result.get("rows"):
                                import pandas as pd
                                df = pd.DataFrame(result["rows"], columns=result.get("columns", []))
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.info("Zero record matches.")
                        else:
                            st.success(f"Statement executed successfully: {result.get('affected_rows', 0)} rows modified.")
                    else:
                        st.error(result.get("error", "Compilation failure."))

# -------------------------------------------------------------
# TCET Documents Page (Admin-Controlled Indexing)
# -------------------------------------------------------------
def render_tcet_docs():
    st.markdown("<h2 style='margin-top: 0;'>📄 TCET Document Indexing</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;'>"
        "Place files in <code style='color: #a5b4fc;'>data/tcet_docs/</code> on the server. "
        "Scan the directory below, then select unindexed files to process them through "
        "split → chunk → embed → vector storage. These documents are used in <strong>TCET ONLY</strong> mode.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        scan = st.button("🔄 Rescan Directory", type="primary", use_container_width=True)
    with col3:
        refresh = st.button("🔄 Refresh Status", use_container_width=True)

    if scan or refresh or "tcet_files" not in st.session_state:
        with st.spinner("Scanning directory..."):
            data = api_tcet_docs()
            st.session_state.tcet_files = data.get("files", [])
            st.session_state.tcet_total = data.get("total", 0)
            st.session_state.tcet_indexed = data.get("indexed", 0)
            st.session_state.tcet_unindexed = data.get("unindexed", 0)

    total = st.session_state.get("tcet_total", 0)
    indexed = st.session_state.get("tcet_indexed", 0)
    unindexed = st.session_state.get("tcet_unindexed", 0)

    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric("Total Files", total)
    with mcol2:
        st.metric("Indexed", indexed)
    with mcol3:
        st.metric("Unindexed", unindexed)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("<h4>Directory Files</h4>", unsafe_allow_html=True)

    files = st.session_state.get("tcet_files", [])
    if not files:
        st.info("No files found in data/tcet_docs/. Add files to the directory and rescan.")
        return

    selected = []
    for f in files:
        col_a, col_b, col_c, col_d = st.columns([3, 2, 1, 2])
        with col_a:
            st.markdown(f"<span style='color:#e2e8f0;'>{f['file_name']}</span>", unsafe_allow_html=True)
        with col_b:
            size_kb = f.get("file_size", 0) / 1024
            st.markdown(f"<span style='color:#64748b; font-size:0.85rem;'>{size_kb:.1f} KB</span>", unsafe_allow_html=True)
        with col_c:
            if f.get("indexed"):
                st.markdown("<span style='color:#34d399; font-weight:600;'>✅ Indexed</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#fbbf24; font-weight:600;'>⏳ Pending</span>", unsafe_allow_html=True)
        with col_d:
            if not f.get("indexed"):
                if st.checkbox("Index", key=f"cb_{f['file_name']}", label_visibility="collapsed"):
                    selected.append(f["file_name"])

        st.markdown("<div style='border-bottom:1px solid #1e293b; margin:4px 0;'></div>", unsafe_allow_html=True)

    if selected:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button(f"📥 Index Selected ({len(selected)} files)", type="primary"):
            with st.spinner("Processing files... This may take a while."):
                result = api_index_tcet_docs(selected)
                success_count = sum(1 for r in result.get("results", []) if r.get("success"))
                fail_count = len(result.get("results", [])) - success_count
                if success_count:
                    st.success(f"Successfully indexed {success_count} file(s).")
                if fail_count:
                    st.error(f"{fail_count} file(s) failed to index.")
                st.session_state.pop("tcet_files", None)
                st.rerun()

# -------------------------------------------------------------
# Main Application Flow
# -------------------------------------------------------------
def main():
    init_session_state()

    if not check_health():
        st.error("⚠️ Backend Connection Offline: Please ensure uvicorn API server is running on localhost port 8000.")
        st.stop()
        return

    if not st.session_state.token:
        render_login_page()
    else:
        render_sidebar()

        # Route matching based on navbar state or authorization level
        if st.session_state.user["role"] != "admin":
            render_chat()
        else:
            if st.session_state.page == "chat":
                render_chat()
            elif st.session_state.page == "upload":
                render_upload()
            elif st.session_state.page == "documents":
                render_documents()
            elif st.session_state.page == "tcet_docs":
                render_tcet_docs()
            elif st.session_state.page == "database":
                render_database()
            elif st.session_state.page == "sql":
                render_sql()

if __name__ == "__main__":
    main()
