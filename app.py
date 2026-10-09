import os
import json
import base64
import pandas as pd
import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config import (
    DOCUMENTS_DIR,
    ADMIN_PASSWORD,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    COLLEGE_NAME,
)
import importlib
import config
import faq_agent
import document_search
import admin

importlib.reload(config)
importlib.reload(faq_agent)
importlib.reload(document_search)
importlib.reload(admin)

from faq_agent import CollegeFAQAgent
from document_search import DocumentSearchManager
from admin import AdminManager, CATEGORIES

# Page Configuration
st.set_page_config(
    page_title=f"{COLLEGE_NAME} - Academic Information Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Main container and font styles */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 1.6rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 700;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        font-size: 1.05rem;
        opacity: 0.94;
        color: #e0e7ff !important;
    }
    
    /* Login card styling */
    .login-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        max-width: 520px;
        margin: 0 auto;
    }
    
    /* Source attribution card */
    .source-box {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #16a34a;
        padding: 0.65rem 1rem;
        border-radius: 6px;
        margin-top: 0.6rem;
        font-size: 0.88rem;
        color: #14532d;
    }
    .source-tag {
        display: inline-block;
        background-color: #dcfce7;
        color: #166534;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 6px;
    }
    
    /* Escalation alert box */
    .escalation-box {
        background-color: #fffbeb;
        border: 1px solid #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin-top: 0.6rem;
        font-size: 0.9rem;
        color: #92400e;
    }
    
    /* Portal badge */
    .portal-badge {
        display: inline-block;
        background-color: #eff6ff;
        color: #1d4ed8;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
        border: 1px solid #bfdbfe;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_admin_authenticated" not in st.session_state:
    st.session_state.is_admin_authenticated = False
if "student_user" not in st.session_state:
    st.session_state.student_user = None
if "runtime_api_key" not in st.session_state:
    st.session_state.runtime_api_key = GEMINI_API_KEY
if "selected_view_doc" not in st.session_state:
    st.session_state.selected_view_doc = None

# Query Parameter Routing (?portal=student or ?portal=admin)
url_portal = st.query_params.get("portal", "").lower()
if "active_portal" not in st.session_state:
    if url_portal == "admin":
        st.session_state.active_portal = "Admin Portal"
    else:
        st.session_state.active_portal = "Student Portal"

search_manager = DocumentSearchManager()
admin_manager = AdminManager()
agent = CollegeFAQAgent(
    api_key=st.session_state.runtime_api_key,
    search_manager=search_manager,
    admin_manager=admin_manager,
)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image(
        "https://api.iconify.design/fluent-emoji:graduation-cap.svg",
        width=55,
    )
    # College Branding instead of "Navigation"
    st.markdown(f"### 🏛️ {COLLEGE_NAME}")
    st.caption("Official Institutional Portal")
    st.markdown("---")

    # Portal Switcher
    current_portal_idx = 0 if st.session_state.active_portal == "Student Portal" else 1
    selected_portal = st.radio(
        "Choose Portal",
        ["Student Portal", "Admin Portal"],
        index=current_portal_idx,
    )

    if selected_portal != st.session_state.active_portal:
        st.session_state.active_portal = selected_portal
        st.query_params["portal"] = "admin" if selected_portal == "Admin Portal" else "student"
        st.rerun()

    st.markdown("---")
    st.markdown("##### 🔗 Direct Portal Links")
    st.markdown("• [🎓 Open Student Portal](?portal=student)")
    st.markdown("• [🔐 Open Admin Portal](?portal=admin)")

    st.markdown("---")
    st.markdown("##### 📊 Institutional Knowledge Base")
    doc_count = len(search_manager.get_document_list())
    chunk_count = len(search_manager.chunks)
    st.write(f"📁 **Approved Documents:** {doc_count}")
    st.write(f"🧩 **Indexed Chunks:** {chunk_count}")

    st.markdown("---")
    st.caption(f"{COLLEGE_NAME} • Information System")


# ==========================================
# 1. STUDENT PORTAL
# ==========================================
if st.session_state.active_portal == "Student Portal":

    # --- Student Login Screen (If not logged in) ---
    if st.session_state.student_user is None:
        st.markdown(
            f"""
            <div class="main-header">
                <span class="portal-badge">🎓 STUDENT ACCESS</span>
                <h1>🏛️ {COLLEGE_NAME}</h1>
                <p>Welcome to the Student Portal. Please log in with your institutional credentials to consult the academic assistant.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_space1, col_login_box, col_space2 = st.columns([1, 2, 1])

        with col_login_box:
            login_tab, register_tab = st.tabs(["🔑 Student Sign In", "📝 New Student Registration"])

            with login_tab:
                with st.form("student_login_form"):
                    student_email = st.text_input(
                        "Student Email Address",
                        placeholder="e.g., student@amman.edu",
                    )
                    student_password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="••••••••",
                    )
                    submit_student_login = st.form_submit_button("Sign In to Student Portal", use_container_width=True)

                    if submit_student_login:
                        user_profile = admin_manager.verify_student_login(student_email, student_password)
                        if user_profile:
                            st.session_state.student_user = user_profile
                            st.success(f"Welcome back, {user_profile.get('name', 'Student')}!")
                            st.rerun()
                        else:
                            st.error("Invalid student email or password. Please check your credentials.")

                st.markdown("---")
                st.caption("💡 Quick Demo Student Login:")
                if st.button("⚡ Quick Sign In as Demo Student (student@amman.edu)", use_container_width=True):
                    st.session_state.student_user = {
                        "name": "Demo Student",
                        "email": "student@amman.edu",
                        "department": "CSE",
                    }
                    st.rerun()

            with register_tab:
                with st.form("student_register_form"):
                    reg_name = st.text_input("Full Name", placeholder="e.g., Arun Kumar")
                    reg_email = st.text_input("Email Address", placeholder="e.g., arun@amman.edu")
                    reg_dept = st.selectbox(
                        "Department",
                        ["CSE", "MECH", "IT", "AI&DS", "ECE", "General"],
                    )
                    reg_pass = st.text_input("Create Password", type="password")
                    submit_reg = st.form_submit_button("Create Student Account", use_container_width=True)

                    if submit_reg:
                        if admin_manager.register_student(reg_name, reg_email, reg_pass, reg_dept):
                            st.success("Account created successfully! You can now sign in using the Sign In tab.")
                        else:
                            st.error("Registration failed. Please ensure all fields are filled and email is not already registered.")

    # --- Student Authenticated Dashboard & Chat ---
    else:
        student_info = st.session_state.student_user
        student_display_name = student_info.get("name", "Student")
        student_display_email = student_info.get("email", "")
        student_dept = student_info.get("department", "Student")

        # Header with Log Out & Clear Chat
        header_col1, header_col2, header_col3 = st.columns([5, 1.2, 1.2])
        with header_col1:
            st.markdown(
                f"""
                <div class="main-header" style="margin-bottom: 0.8rem;">
                    <span class="portal-badge">🎓 STUDENT PORTAL</span>
                    <h1>🏛️ {COLLEGE_NAME}</h1>
                    <p>Welcome, <b>{student_display_name}</b> ({student_dept}) • Ask questions in English or தமிழ் regarding rules, timetable, fees, and departments.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with header_col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Clear Chat", use_container_width=True, type="secondary"):
                st.session_state.chat_history = []
                st.rerun()
        with header_col3:
            st.write("")
            st.write("")
            if st.button("🚪 Log Out", use_container_width=True, type="secondary"):
                st.session_state.student_user = None
                st.session_state.chat_history = []
                st.rerun()

        # Frequently Asked Questions Chips
        st.markdown("##### 💡 Frequently Asked Questions (Click to Ask):")
        col1, col2 = st.columns(2)
        sample_queries = [
            "What time does the college start?",
            "What is the college name?",
            "Which departments are available?",
            "What is the minimum attendance requirement?",
        ]

        selected_sample = None
        with col1:
            if st.button(f"📌 {sample_queries[0]}", use_container_width=True):
                selected_sample = sample_queries[0]
            if st.button(f"📌 {sample_queries[1]}", use_container_width=True):
                selected_sample = sample_queries[1]
        with col2:
            if st.button(f"📌 {sample_queries[2]}", use_container_width=True):
                selected_sample = sample_queries[2]
            if st.button(f"📌 {sample_queries[3]}", use_container_width=True):
                selected_sample = sample_queries[3]

        st.markdown("---")

        # Chat history display
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🧑‍🎓"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🏛️"):
                    st.markdown(msg["content"])

                    # Source attribution or escalation badge
                    if msg.get("source"):
                        source_doc = msg["source"].get("document", "Unknown")
                        source_page = msg["source"].get("page")
                        source_sec = msg["source"].get("section", "General")
                        page_str = f" | Page: {source_page}" if source_page else ""

                        st.markdown(
                            f"""
                            <div class="source-box">
                                <span class="source-tag">Verified Source</span>
                                <b>Document:</b> <code>{source_doc}</code>{page_str} &nbsp;|&nbsp; <b>Section:</b> <i>{source_sec}</i>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif msg.get("status") == "unanswered":
                        st.markdown(
                            """
                            <div class="escalation-box">
                                <b>⚠️ Official Verification Required:</b><br/>
                                This question could not be verified from approved college documents.
                                It has been logged and escalated to the college administration for human review.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        # User input bar
        prompt_input = st.chat_input("Ask a question in English or தமிழ் (e.g., What is the library overdue fine?)...")
        active_prompt = selected_sample or prompt_input

        if active_prompt:
            st.session_state.chat_history.append({"role": "user", "content": active_prompt})

            with st.spinner("Searching approved college documents..."):
                response = agent.ask(active_prompt)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response.get("answer", ""),
                "source": response.get("source"),
                "status": response.get("status", "answered"),
                "needs_human_review": response.get("needs_human_review", False),
            })
            st.rerun()


# ==========================================
# 2. ADMINISTRATOR PORTAL
# ==========================================
elif st.session_state.active_portal == "Admin Portal":
    st.markdown(
        f"""
        <div class="main-header" style="background: linear-gradient(135deg, #312e81 0%, #4338ca 100%);">
            <span class="portal-badge" style="background-color: #ede9fe; color: #5b21b6; border-color: #ddd6fe;">🔐 ADMIN PORTAL</span>
            <h1>🏛️ {COLLEGE_NAME}</h1>
            <p>Administrator Portal • Manage approved institutional documents, review escalated student inquiries, and monitor analytics.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Admin Authentication Check
    if not st.session_state.is_admin_authenticated:
        st.subheader("Administrator Login")
        with st.form("admin_login_form"):
            admin_pwd = st.text_input("Enter Admin Password", type="password")
            submit_login = st.form_submit_button("Sign In to Admin Portal", use_container_width=True)

            if submit_login:
                if admin_manager.verify_password(admin_pwd):
                    st.session_state.is_admin_authenticated = True
                    st.success("Authentication successful!")
                    st.rerun()
                else:
                    st.error("Invalid administrator password. Access denied.")
        st.info("Default administrator password is configured in `.env` (ADMIN_PASSWORD).")
    else:
        # Admin Header Bar
        col_admin_info, col_logout = st.columns([4, 1])
        with col_admin_info:
            st.write(f"Logged in as **System Administrator** • {COLLEGE_NAME}")
        with col_logout:
            if st.button("🚪 Log Out", type="secondary"):
                st.session_state.is_admin_authenticated = False
                st.rerun()

        # Tabs for Admin Operations
        tab_analytics, tab_unanswered, tab_documents = st.tabs([
            "📊 Analytics & Metrics",
            "📥 Escalated Questions Review",
            "📂 Approved Documents Manager",
        ])

        # TAB 1: ANALYTICS & METRICS
        with tab_analytics:
            st.subheader("System Performance & Inquiries Overview")
            metrics = admin_manager.get_analytics()

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Queries", metrics["total_questions"])
            with m2:
                st.metric("Answered Queries", metrics["answered_count"])
            with m3:
                st.metric("Unanswered (Escalated)", metrics["unanswered_count"])
            with m4:
                st.metric("Answer Rate", f"{metrics['answer_rate']}%")

            st.markdown("---")
            st.subheader("Inquiries by Academic Category")
            categories_data = metrics.get("categories_distribution", {})
            if categories_data:
                chart_data = [{"Category": k, "Count": v} for k, v in categories_data.items()]
                st.bar_chart(data=chart_data, x="Category", y="Count")
            else:
                st.info("No queries recorded yet.")

        # TAB 2: UNANSWERED QUESTIONS REVIEW
        with tab_unanswered:
            st.subheader("Escalated Student Inquiries Queue")
            st.write(
                "Questions that could not be verified from approved institutional documents are logged here for administrative review."
            )

            filter_col1, filter_col2 = st.columns([2, 2])
            with filter_col1:
                status_choice = st.selectbox(
                    "Filter by Status",
                    ["all", "pending", "reviewed", "resolved"],
                    index=0,
                )

            unanswered_items = admin_manager.get_unanswered_questions(status_filter=status_choice)

            if not unanswered_items:
                st.success("No unanswered questions in this category! 🎉")
            else:
                st.write(f"Showing **{len(unanswered_items)}** inquiry/inquiries:")

                for idx, item in enumerate(unanswered_items):
                    with st.expander(
                        f"[{item.get('status', 'pending').upper()}] {item.get('question')} (Category: {item.get('category')})",
                        expanded=(item.get("status") == "pending" and idx == 0),
                    ):
                        st.write(f"**ID:** `{item.get('id')}`")
                        st.write(f"**Submitted At:** {item.get('timestamp')}")
                        st.write(f"**Category:** {item.get('category')}")
                        st.write(f"**Question:** {item.get('question')}")

                        with st.form(key=f"review_form_{item.get('id')}"):
                            new_status = st.selectbox(
                                "Status",
                                ["pending", "reviewed", "resolved"],
                                index=["pending", "reviewed", "resolved"].index(item.get("status", "pending")),
                            )
                            admin_notes = st.text_area(
                                "Administrative Notes",
                                value=item.get("admin_notes", ""),
                                placeholder="Internal remarks or action taken...",
                            )
                            official_response = st.text_area(
                                "Official Response / Document Update Plan",
                                value=item.get("official_response", ""),
                                placeholder="Answer to add to official handbook...",
                            )
                            update_btn = st.form_submit_button("Update Status & Notes")

                            if update_btn:
                                success = admin_manager.update_unanswered_question(
                                    item_id=item.get("id"),
                                    status=new_status,
                                    admin_notes=admin_notes,
                                    official_response=official_response,
                                )
                                if success:
                                    st.success(f"Updated inquiry `{item.get('id')}`!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update inquiry.")

        # TAB 3: APPROVED DOCUMENTS MANAGER
        with tab_documents:
            st.subheader(f"Manage Approved Documents • {COLLEGE_NAME}")
            st.write(
                "Upload official institutional handbooks, timetables, fee schedules, or circulars. "
                "Supported formats: **PDF, TXT, CSV, JSON**."
            )

            # Upload Document Form
            with st.form("doc_upload_form", clear_on_submit=True):
                uploaded_file = st.file_uploader(
                    "Choose an approved college document to upload",
                    type=["pdf", "txt", "csv", "json"],
                    help=f"Maximum file size: {MAX_FILE_SIZE_MB}MB",
                )
                submit_upload = st.form_submit_button("Upload & Index Document")

                if submit_upload and uploaded_file is not None:
                    file_ext = Path(uploaded_file.name).suffix.lower()
                    if file_ext not in ALLOWED_EXTENSIONS:
                        st.error(f"Unsupported file format: {file_ext}")
                    else:
                        file_bytes = uploaded_file.read()
                        if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
                            st.error(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
                        elif len(file_bytes) == 0:
                            st.error("Uploaded file is empty.")
                        else:
                            safe_name = Path(uploaded_file.name).name
                            save_path = DOCUMENTS_DIR / safe_name
                            with open(save_path, "wb") as f:
                                f.write(file_bytes)

                            total_chunks = search_manager.load_and_index_all()
                            st.success(
                                f"Document '{safe_name}' uploaded successfully! System now has {total_chunks} indexed chunks."
                            )
                            st.rerun()

            st.markdown("---")
            st.subheader("Current Document Repository")

            doc_list = search_manager.get_document_list()
            if not doc_list:
                st.warning("No documents currently indexed in the repository.")
            else:
                for doc in doc_list:
                    col_name, col_type, col_chunks, col_size, col_view, col_del = st.columns([3.5, 1, 1.2, 1.2, 1.3, 1.2])
                    with col_name:
                        st.write(f"📄 **{doc['name']}**")
                    with col_type:
                        st.write(f"`{doc['type']}`")
                    with col_chunks:
                        st.write(f"{doc['chunks']} chunks")
                    with col_size:
                        st.write(f"{doc['size_kb']} KB")
                    with col_view:
                        is_viewing = (st.session_state.selected_view_doc == doc['name'])
                        btn_label = "👁️ Viewing" if is_viewing else "👁️ View"
                        if st.button(btn_label, key=f"view_{doc['name']}", type=("primary" if is_viewing else "secondary")):
                            st.session_state.selected_view_doc = None if is_viewing else doc['name']
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_{doc['name']}", type="secondary"):
                            if st.session_state.selected_view_doc == doc['name']:
                                st.session_state.selected_view_doc = None
                            search_manager.delete_document(doc['name'])
                            st.success(f"Deleted '{doc['name']}' and updated search index.")
                            st.rerun()

            # Dedicated Interactive Document Viewer Section
            if st.session_state.selected_view_doc:
                view_file_name = st.session_state.selected_view_doc
                view_file_path = DOCUMENTS_DIR / view_file_name

                if view_file_path.exists() and view_file_path.is_file():
                    st.markdown("---")
                    v_col_title, v_col_close, v_col_dl = st.columns([4.5, 1.5, 1.5])
                    with v_col_title:
                        st.markdown(f"### 📖 Document Viewer: `{view_file_name}`")
                    with v_col_close:
                        if st.button("❌ Close Viewer", key="btn_close_viewer", use_container_width=True):
                            st.session_state.selected_view_doc = None
                            st.rerun()
                    with v_col_dl:
                        st.download_button(
                            label="⬇️ Download File",
                            data=view_file_path.read_bytes(),
                            file_name=view_file_name,
                            key="btn_dl_viewer",
                            use_container_width=True,
                        )

                    ext = view_file_path.suffix.lower()
                    if ext == ".pdf":
                        tab_embed, tab_text = st.tabs(["📑 Interactive PDF Preview", "📝 Extracted Page Text"])
                        with tab_embed:
                            base64_pdf = base64.b64encode(view_file_path.read_bytes()).decode("utf-8")
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" style="border: 1px solid #cbd5e1; border-radius: 8px;" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        with tab_text:
                            import pypdf
                            reader = pypdf.PdfReader(str(view_file_path))
                            st.write(f"Total Pages: **{len(reader.pages)}**")
                            for p_idx, page in enumerate(reader.pages, start=1):
                                with st.expander(f"📄 Page {p_idx}", expanded=(p_idx == 1)):
                                    p_text = page.extract_text() or "(No readable text on this page)"
                                    st.text_area(f"Page {p_idx} Text Content", p_text, height=250, key=f"pdf_p_{p_idx}")
                    elif ext == ".csv":
                        tab_table, tab_raw = st.tabs(["📊 Interactive Table View", "📝 Raw CSV Content"])
                        with tab_table:
                            try:
                                df = pd.read_csv(view_file_path)
                                st.dataframe(df, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error rendering CSV table: {e}")
                        with tab_raw:
                            st.code(view_file_path.read_text(encoding="utf-8", errors="ignore"), language="csv")
                    elif ext == ".json":
                        tab_tree, tab_json_raw = st.tabs(["🌳 Structured JSON Tree", "📝 Raw JSON Text"])
                        with tab_tree:
                            try:
                                data = json.loads(view_file_path.read_text(encoding="utf-8", errors="ignore"))
                                st.json(data)
                            except Exception as e:
                                st.error(f"Error parsing JSON: {e}")
                        with tab_json_raw:
                            st.code(view_file_path.read_text(encoding="utf-8", errors="ignore"), language="json")
                    elif ext == ".txt":
                        st.text_area(
                            "Document Content",
                            view_file_path.read_text(encoding="utf-8", errors="ignore"),
                            height=450,
                        )

            st.markdown("---")
            col_reindex, _ = st.columns([2, 4])
            with col_reindex:
                if st.button("🔄 Re-index All Documents", type="primary"):
                    total = search_manager.load_and_index_all()
                    st.success(f"Re-indexing complete! {total} total chunks indexed.")
                    st.rerun()
