import html
from datetime import datetime

import streamlit as st

from api_client import (
    APIError,
    create_set,
    delete_set_completely,
    get_documents,
    get_messages,
    get_sets,
    get_status,
    send_chat,
    upload_document,
)
from styles import inject_css


APP_NAME = "MultiPDF Agentic Chat"
TAGLINE = "Agentic RAG Bot with Long-Term Memory For each Chat"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🗂️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

if "active_set_id" not in st.session_state:
    st.session_state.active_set_id = None

if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}

if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = {}

if "pending_delete_set_id" not in st.session_state:
    st.session_state.pending_delete_set_id = None


inject_css(st.session_state.dark_mode)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_chat_history_loaded(set_id):
    """
    Load the persisted chat history from the backend once per set/session.

    The backend returns messages in this format:
        {
            "role": "user" | "assistant",
            "content": "..."
        }

    We convert them to tuples because the rest of the app uses:
        ("user", "...")
        ("assistant", "...")
    """

    if set_id in st.session_state.chat_histories:
        return st.session_state.chat_histories[set_id]

    try:
        messages = get_messages(set_id) or []

        st.session_state.chat_histories[set_id] = [
            (message["role"], message["content"])
            for message in messages
        ]

    except APIError:
        st.session_state.chat_histories[set_id] = []

    return st.session_state.chat_histories[set_id]


def format_timestamp(raw):
    try:
        return datetime.strptime(
            raw,
            "%Y-%m-%d %H:%M:%S"
        ).strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return raw


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

# Callbacks run once, before Streamlit's single automatic rerun for the
# click that triggered them — so by the time the script body below executes,
# session_state (and anything fetched from it) is already up to date.
# No extra st.rerun() needed, which was causing the double fade/"blink"
# on every click before.

def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode


def select_set(set_id):
    st.session_state.active_set_id = set_id


def handle_create_set():
    name = st.session_state.get("new_set_name_input", "").strip()

    if not name:
        st.session_state.new_set_error = "Give the set a name first."
        return

    try:
        created = create_set(name)

        st.session_state.active_set_id = created["id"]
        st.session_state.new_set_error = None

    except APIError as e:
        st.session_state.new_set_error = str(e)


def request_delete_set(set_id):
    # First click just asks for confirmation — no API call yet.
    st.session_state.pending_delete_set_id = set_id


def cancel_delete_set():
    st.session_state.pending_delete_set_id = None


def confirm_delete_set(set_id):
    try:
        delete_set_completely(set_id)

        if st.session_state.active_set_id == set_id:
            st.session_state.active_set_id = None

        st.session_state.chat_histories.pop(set_id, None)
        st.session_state.uploader_nonce.pop(set_id, None)
        st.session_state.pending_delete_set_id = None
        st.session_state.delete_error = None

    except APIError as e:
        st.session_state.delete_error = str(e)
        st.session_state.pending_delete_set_id = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Orchestrated by Tharun")

    top_l, top_r = st.columns([3, 1])

    with top_l:
        st.markdown(
            f'<div class="brand-title">{APP_NAME}</div>',
            unsafe_allow_html=True,
        )

    with top_r:
        st.button(
            "☀️" if st.session_state.dark_mode else "🌙",
            key="theme_toggle",
            on_click=toggle_theme,
            help=(
                "Switch to light mode"
                if st.session_state.dark_mode
                else "Switch to dark mode"
            ),
        )

    st.markdown(
        f'<div class="brand-tagline">{TAGLINE}</div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Load sets
    # -----------------------------------------------------------------------

    try:
        sets = get_sets()
        sidebar_error = None

    except APIError as e:
        sets = []
        sidebar_error = str(e)

    if sidebar_error:
        st.error(sidebar_error)

    # -----------------------------------------------------------------------
    # Set list
    # -----------------------------------------------------------------------

    for s in sets:
        is_active = s["id"] == st.session_state.active_set_id

        if st.session_state.pending_delete_set_id == s["id"]:
            safe_name = html.escape(s["name"])

            st.markdown(
                f'<div class="set-subtitle" style="margin:0.3rem 0;">'
                f'Delete "{safe_name}"? This can\'t be undone.</div>',
                unsafe_allow_html=True,
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                st.button(
                    "Delete",
                    key=f"confirm_delete_{s['id']}",
                    use_container_width=True,
                    type="primary",
                    on_click=confirm_delete_set,
                    args=(s["id"],),
                )

            with cancel_col:
                st.button(
                    "Cancel",
                    key=f"cancel_delete_{s['id']}",
                    use_container_width=True,
                    type="secondary",
                    on_click=cancel_delete_set,
                )

        else:
            name_col, delete_col = st.columns([4, 1])

            with name_col:
                st.button(
                    s["name"],
                    key=f"set_{s['id']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    on_click=select_set,
                    args=(s["id"],),
                )

            with delete_col:
                st.button(
                    "🗑️",
                    key=f"delete_{s['id']}",
                    use_container_width=True,
                    on_click=request_delete_set,
                    args=(s["id"],),
                    help=f'Delete "{s["name"]}"',
                )

    # -----------------------------------------------------------------------
    # Delete error
    # -----------------------------------------------------------------------

    if st.session_state.get("delete_error"):
        st.error(st.session_state.pop("delete_error"))

    st.divider()

    # -----------------------------------------------------------------------
    # Create new set
    # -----------------------------------------------------------------------

    with st.form("new_set_form", clear_on_submit=True):
        st.text_input(
            "New set name",
            label_visibility="collapsed",
            placeholder="Name a new set…",
            key="new_set_name_input",
        )

        st.form_submit_button(
            "+ New set",
            use_container_width=True,
            on_click=handle_create_set,
        )

    if st.session_state.get("new_set_error"):
        st.error(st.session_state.pop("new_set_error"))


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

active_id = st.session_state.active_set_id

st.markdown(
    f'<div class="app-title">{APP_NAME}</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# No active set
# ---------------------------------------------------------------------------

if active_id is None:
    st.markdown(
        '<div class="set-subtitle">'
        'Pick a set from the sidebar, or create one, to get started.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Each set keeps its own documents and its own memory — nothing crosses "
        "over between them."
    )


# ---------------------------------------------------------------------------
# Active set
# ---------------------------------------------------------------------------

else:
    active_set = next(
        (s for s in sets if s["id"] == active_id),
        None,
    )

    set_name = (
        active_set["name"]
        if active_set
        else f"Set {active_id}"
    )

    # Load persisted conversation before rendering the chat.
    ensure_chat_history_loaded(active_id)

    st.markdown(
        f'<div class="set-subtitle">Set: {set_name}</div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    try:
        status = get_status(active_id)
        status_error = None

    except APIError as e:
        status = None
        status_error = str(e)

    # -----------------------------------------------------------------------
    # Documents
    # -----------------------------------------------------------------------

    try:
        documents = get_documents(active_id)
        docs_error = None

    except APIError as e:
        documents = []
        docs_error = str(e)

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    col_chat, col_docs = st.columns(
        [2.3, 1],
        gap="large",
    )

    # -----------------------------------------------------------------------
    # Right panel: capacity, upload, documents
    # -----------------------------------------------------------------------

    with col_docs:
        st.markdown(
            '<div class="set-subtitle" style="margin-top:0;">Documents</div>',
            unsafe_allow_html=True,
        )

        if status_error:
            st.error(status_error)

        chunk_count = (
            status.get("chunk_count", 0)
            if status
            else 0
        )

        chunk_limit = (
            status.get("chunk_limit", 150)
            if status
            else 150
        )

        at_capacity = chunk_count >= chunk_limit

        # -------------------------------------------------------------------
        # Capacity gauge
        # -------------------------------------------------------------------

        if status:
            pct = (
                min(
                    100,
                    int(100 * chunk_count / chunk_limit),
                )
                if chunk_limit
                else 0
            )

            fill_class = (
                "gauge-fill full"
                if at_capacity
                else "gauge-fill"
            )

            st.markdown(
                f"""
                <div class="gauge-label">
                    {chunk_count} / {chunk_limit} chunks used
                </div>
                <div class="gauge-track">
                    <div class="{fill_class}" style="width:{pct}%;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # -------------------------------------------------------------------
        # Upload
        # -------------------------------------------------------------------

        if at_capacity:
            st.warning(
                "This set is at capacity. Start a new set for more material."
            )

        else:
            nonce = st.session_state.uploader_nonce.get(
                active_id,
                0,
            )

            uploaded_file = st.file_uploader(
                "Add a document",
                type=["pdf"],
                key=f"uploader_{active_id}_{nonce}",
            )

            if uploaded_file is not None:
                if not uploaded_file.name.lower().endswith(".pdf"):
                    st.error("Only PDF files are supported.")

                elif st.button(
                    "Upload",
                    key=f"upload_btn_{active_id}_{nonce}",
                ):
                    try:
                        with st.spinner("Uploading and indexing…"):
                            upload_document(
                                active_id,
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                            )

                        st.session_state.uploader_nonce[
                            active_id
                        ] = nonce + 1

                        st.success(
                            f"{uploaded_file.name} added."
                        )

                        # Refresh in place rather than st.rerun() —
                        # this click already triggers Streamlit's one
                        # automatic rerun; adding a second was the
                        # double-fade cause.
                        #
                        # Tradeoff:
                        # the file_uploader widget above won't visibly
                        # clear until the next interaction, since it
                        # already rendered earlier in this same run.

                        try:
                            status = get_status(active_id)

                            chunk_count = status.get(
                                "chunk_count",
                                0,
                            )

                            chunk_limit = status.get(
                                "chunk_limit",
                                150,
                            )

                            at_capacity = (
                                chunk_count >= chunk_limit
                            )

                        except APIError:
                            pass

                        try:
                            documents = get_documents(active_id)
                        except APIError:
                            pass

                    except APIError as e:
                        st.error(str(e))

        st.markdown(
            "<div style='height:0.4rem'></div>",
            unsafe_allow_html=True,
        )

        # -------------------------------------------------------------------
        # Document cards
        # -------------------------------------------------------------------

        if docs_error:
            st.error(docs_error)

        elif documents:
            for doc in documents:
                st.markdown(
                    f"""
                    <div class="doc-card">
                        <div class="doc-name">
                            {doc['filename']}
                        </div>
                        <div class="doc-meta">
                            {doc['chunk_count']} chunks,
                            added {format_timestamp(doc['uploaded_at'])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:
            st.caption(
                "No documents yet — add one above to get started."
            )

    # -----------------------------------------------------------------------
    # Center: chat
    # -----------------------------------------------------------------------

    with col_chat:
        # This now returns the already-loaded history.
        history = ensure_chat_history_loaded(active_id)

        # A fixed-height, bordered container gives the conversation its own
        # scroll region, so appending a message doesn't reflow (and jump)
        # the whole page the way it did before.
        chat_box = st.container(
            height=440,
            border=True,
        )

        with chat_box:
            for role, content in history:
                with st.chat_message(role):
                    st.write(content)

        has_docs = len(documents) > 0

        # -------------------------------------------------------------------
        # No documents
        # -------------------------------------------------------------------

        if not has_docs:
            st.info(
                "Upload a document to this set before you can start chatting."
            )

        # -------------------------------------------------------------------
        # Chat input
        # -------------------------------------------------------------------

        else:
            user_input = st.chat_input(
                "Ask something about this set's documents…"
            )

            if user_input:
                # Show user message immediately.
                history.append(
                    ("user", user_input)
                )

                with chat_box:
                    with st.chat_message("user"):
                        st.write(user_input)

                    with st.chat_message("assistant"):
                        try:
                            with st.spinner("Thinking…"):
                                result = send_chat(
                                    active_id,
                                    user_input,
                                )

                            answer = result["answer"]

                            st.write(answer)

                            # Keep frontend session history in sync.
                            history.append(
                                ("assistant", answer)
                            )

                        except APIError as e:
                            st.error(str(e))