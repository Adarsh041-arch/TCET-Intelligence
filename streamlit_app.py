import streamlit as st
import requests


API_BASE_URL = "http://localhost:8000/api"
APP_NAME = "Knowledge Assistant"


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


def check_health():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


@st.cache_data(ttl=60)
def cached_get_sessions():
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            return response.json().get("sessions", [])
    except:
        pass
    return []


@st.cache_data(ttl=60)
def cached_get_documents():
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/documents", headers=get_headers(), timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"documents": [], "total_chunks": 0}


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
            cached_get_sessions.clear()
            cached_get_documents.clear()
            return True
    except Exception as e:
        st.error(f"Connection error: {e}")
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
            cached_get_sessions.clear()
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


def api_send_message(session_id, message):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"session_id": session_id, "message": message},
            headers=get_headers(),
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
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
            timeout=60,
        )
        cached_get_documents.clear()
        return response.json()
    except:
        return {"success": False, "message": "Connection error"}


def api_delete_document(doc_id):
    try:
        response = requests.delete(
            f"{API_BASE_URL}/admin/documents/{doc_id}",
            headers=get_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            cached_get_documents.clear()
            return True
    except:
        pass
    return False


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.current_session_id = None
    st.session_state.messages = []
    st.session_state.page = "chat"
    cached_get_sessions.clear()
    cached_get_documents.clear()


def render_login_page():
    st.set_page_config(
        page_title=f"Login - {APP_NAME}", page_icon="🤖", layout="centered"
    )

    st.markdown(
        f"<h1 style='text-align: center; color: #1E293B;'>🤖 {APP_NAME}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align: center; color: #64748B;'>Your organizational AI assistant powered by RAG</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register"])

        with tab1:
            with st.form("login_form", clear_on_submit=True):
                st.text_input("Username", key="login_user")
                st.text_input("Password", type="password", key="login_pass")
                if st.form_submit_button("Sign In"):
                    if st.session_state.login_user and st.session_state.login_pass:
                        if api_login(
                            st.session_state.login_user, st.session_state.login_pass
                        ):
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.warning("Please fill in all fields")
            st.markdown(
                "<p style='text-align: center; color: #64748B;'>Default: admin / admin123</p>",
                unsafe_allow_html=True,
            )

        with tab2:
            with st.form("register_form", clear_on_submit=True):
                st.text_input("Username", key="reg_user")
                st.text_input("Password", type="password", key="reg_pass")
                st.selectbox("Role", ["user", "admin"], key="reg_role")
                if st.form_submit_button("Register"):
                    if st.session_state.reg_user and st.session_state.reg_pass:
                        if api_register(
                            st.session_state.reg_user,
                            st.session_state.reg_pass,
                            st.session_state.reg_role,
                        ):
                            st.success("Registration successful! Please sign in.")
                        else:
                            st.error("Username already exists")
                    else:
                        st.warning("Please fill in all fields")


def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 🤖 {APP_NAME}")
        st.markdown(f"👤 **{st.session_state.user['username']}**")
        st.markdown("---")

        if st.button("➕ New Chat", type="primary", use_container_width=True):
            session_id = api_create_session()
            if session_id:
                st.session_state.current_session_id = session_id
                st.session_state.messages = []
                cached_get_sessions.clear()

        st.markdown("**Session History**")
        sessions = cached_get_sessions()

        for session in sessions:
            session_name = session.get("session_name", "Untitled") or "Untitled"
            is_active = st.session_state.current_session_id == session["session_id"]
            btn_type = "primary" if is_active else "secondary"
            label = (
                session_name[:28] + "..." if len(session_name) > 28 else session_name
            )
            if st.button(
                f"💬 {label}",
                key=f"session_{session['session_id']}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state.current_session_id = session["session_id"]
                st.session_state.messages = []

        st.markdown("---")

        if st.session_state.user["role"] == "admin":
            st.markdown("**Admin**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Upload", use_container_width=True):
                    st.session_state.page = "upload"
            with col2:
                if st.button("📚 Docs", use_container_width=True):
                    st.session_state.page = "documents"
            st.markdown("---")

        st.markdown(f"**Role:** {st.session_state.user['role']}")
        if st.button("🚪 Logout", use_container_width=True):
            logout()


def render_chat():
    st.header("💬 Chat")

    if not st.session_state.current_session_id:
        st.info("👈 Create a new chat or select a session from the sidebar")
        return

    messages = api_get_history(st.session_state.current_session_id)

    for msg in messages:
        avatar = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask me anything..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        response_container = st.container()
        with response_container:
            with st.spinner("Thinking..."):
                response = api_send_message(st.session_state.current_session_id, prompt)

        if response:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(response["response"])
                if response.get("retrieved_docs"):
                    with st.expander("📚 Retrieved Context"):
                        for i, doc in enumerate(response["retrieved_docs"], 1):
                            st.markdown(
                                f"**Document {i}** ({doc['filename']}) - {doc['similarity'] * 100:.0f}%"
                            )
                            st.text(
                                doc["content"][:300] + "..."
                                if len(doc["content"]) > 300
                                else doc["content"]
                            )
                st.caption(
                    f"📍 Source: **{response.get('source', 'unknown').upper()}**"
                )
        else:
            st.error("Failed to get response. Please try again.")


def render_upload():
    st.header("📤 Upload Documents")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "docx", "xlsx", "xls", "csv", "json", "html"],
    )

    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(
                f"📎 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)"
            )

        if st.button("⬆️ Upload & Index", type="primary"):
            with st.spinner("Processing..."):
                result = api_upload_document(uploaded_file)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result.get("message", "Upload failed"))


def render_documents():
    st.header("📚 Document Library")

    docs_data = cached_get_documents()
    col1, col2 = st.columns(2)
    col1.metric("Chunks", docs_data["total_chunks"])
    col2.metric("Documents", len(docs_data["documents"]))

    st.divider()

    if docs_data["documents"]:
        for doc in docs_data["documents"]:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"📄 **{doc['filename']}**")
                st.caption(f"Type: {doc['file_type']} · {doc['uploaded_at'][:10]}")
            with col2:
                if st.button("🗑️", key=f"del_{doc['doc_id']}"):
                    if api_delete_document(doc["doc_id"]):
                        st.success("Deleted")
                        st.rerun()
    else:
        st.info("No documents uploaded yet.")


def main():
    init_session_state()

    if not check_health():
        st.error("⚠️ Cannot connect to backend server on port 8000.")
        st.stop()
        return

    if not st.session_state.token:
        render_login_page()
    else:
        page_title = (
            f"Admin - {APP_NAME}"
            if st.session_state.user["role"] == "admin"
            else APP_NAME
        )
        st.set_page_config(
            page_title=page_title,
            page_icon="⚙️" if st.session_state.user["role"] == "admin" else "🤖",
            layout="wide",
        )

        render_sidebar()

        if st.session_state.page == "chat" or st.session_state.user["role"] != "admin":
            render_chat()
        elif st.session_state.page == "upload":
            render_upload()
        elif st.session_state.page == "documents":
            render_documents()


if __name__ == "__main__":
    main()
