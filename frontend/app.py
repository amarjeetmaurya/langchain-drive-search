import requests
import streamlit as st
import os
from streamlit_mic_recorder import speech_to_text
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
print(BACKEND_URL)

# Page configuration
st.set_page_config(
    page_title="Google Drive Search Agent",
    page_icon="📁",
)

# Load custom CSS
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# Sidebar for Chat History
with st.sidebar:
    st.markdown("<h3 style='color: #00FFA3;'>System Status</h3>", unsafe_allow_html=True)
    st.success("Connected to Render Cloud")
    
    st.markdown("---")
    
    st.title("💬 Chat History")
    
    if st.button("New Chat", icon=":material/add:", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Fetch sessions from backend
    try:
        response = requests.get(f"{BACKEND_URL}/sessions", timeout=10)
        if response.status_code == 200:
            sessions = response.json()
            if sessions:
                for session in sessions:
                    sid = session['id']
                    
                    if st.session_state.get(f"renaming_{sid}"):
                        new_title = st.text_input("New title", value=session['title'], key=f"title_{sid}")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("Save", key=f"save_{sid}"):
                                requests.put(f"{BACKEND_URL}/sessions/{sid}", json={"title": new_title}, timeout=10)
                                st.session_state[f"renaming_{sid}"] = False
                                st.rerun()
                        with col_cancel:
                            if st.button("Cancel", key=f"cancel_{sid}"):
                                st.session_state[f"renaming_{sid}"] = False
                                st.rerun()
                    else:
                        col1, col2 = st.columns([8.5, 1.5])
                        with col1:
                            if st.button(f"{session['title']}", icon=":material/chat:", key=f"session_{sid}", use_container_width=True):
                                st.session_state.session_id = sid
                                # Fetch messages for this session
                                msg_response = requests.get(f"{BACKEND_URL}/sessions/{sid}/messages", timeout=10)
                                if msg_response.status_code == 200:
                                    history = msg_response.json()
                                    st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in history]
                                else:
                                    st.error("Failed to load chat history.")
                                st.rerun()
                        with col2:
                            with st.popover("⋮", use_container_width=True):
                                if st.button("Rename", icon=":material/edit:", key=f"edit_{sid}", use_container_width=True):
                                    st.session_state[f"renaming_{sid}"] = True
                                    st.rerun()
                                if st.button("Delete", icon=":material/delete:", key=f"del_{sid}", use_container_width=True):
                                    requests.delete(f"{BACKEND_URL}/sessions/{sid}", timeout=10)
                                    if st.session_state.session_id == sid:
                                        st.session_state.session_id = None
                                        st.session_state.messages = []
                                    st.rerun()
            else:
                st.write("No previous chats found.")
        else:
            st.error("Could not load chat sessions.")
    except Exception as e:
        st.error("Backend connection failed.")

# Main Chat Interface
st.title("📁 Google Drive Search Agent")
st.write("Ask questions about the files in your Google Drive.")

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input area
st.markdown("---")
col1, col2, col3 = st.columns([1, 9, 2])

if "user_query" not in st.session_state:
    st.session_state.user_query = ""

with col1:
    text_from_voice = speech_to_text(
        start_prompt="🎙️",
        stop_prompt="🛑",
        language='en',
        use_container_width=True,
        just_once=True,
        key='STT'
    )

if text_from_voice:
    st.session_state.user_query = text_from_voice

def submit_query():
    if st.session_state.user_query.strip():
        st.session_state.submitted_query = st.session_state.user_query
        st.session_state.user_query = ""

with col2:
    st.text_input("Search your Google Drive...", key="user_query", on_change=submit_query, label_visibility="collapsed")

with col3:
    st.button("Send", use_container_width=True, on_click=submit_query)

user_input = st.session_state.get("submitted_query", "")

if user_input:
    st.session_state.submitted_query = ""
    # Show user message
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Send request to FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Searching Google Drive..."):
            payload = {"message": user_input}
            if st.session_state.session_id:
                payload["session_id"] = st.session_state.session_id

            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    json=payload,
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("response", "No response content.")
                    
                    # Update session_id if it's a new session
                    if "session_id" in data and st.session_state.session_id is None:
                        st.session_state.session_id = data["session_id"]
                        # We force a rerun here to update the sidebar with the new session
                        st.session_state.rerun_needed = True 
                else:
                    answer = f"Error: {response.status_code}"
            except Exception as e:
                answer = f"Error: {str(e)}"

            st.markdown(answer)

    # Save assistant response
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
    
    if st.session_state.get("rerun_needed"):
        st.session_state.rerun_needed = False
        st.rerun()