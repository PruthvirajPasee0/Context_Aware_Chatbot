import streamlit as st
import os
import uuid
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

# Import authentication and storage modules
from auth import register_user, authenticate_user, get_username
from chroma_storage import save_user_chats, load_user_chats

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Llama 3 Chatbot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Initialize Groq Client
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("GROQ_API_KEY not found in environment variables. Please add it to your .env file.")
    st.stop()

client = Groq(api_key=api_key)

# Helper Functions
def create_new_chat():
    """Create a new chat session and return its ID"""
    chat_id = str(uuid.uuid4())
    st.session_state.chat_sessions[chat_id] = {
        "messages": [],
        "title": "New Chat",
        "created_at": datetime.now().isoformat()
    }
    return chat_id

def get_chat_title(messages):
    """Generate chat title from first user message"""
    if messages and messages[0]["role"] == "user":
        title = messages[0]["content"][:50]
        return title + "..." if len(messages[0]["content"]) > 50 else title
    return "New Chat"

def save_to_chromadb():
    """Save current user's chats to ChromaDB"""
    if st.session_state.authenticated and st.session_state.user_id:
        save_user_chats(
            st.session_state.user_id,
            st.session_state.chat_sessions,
            st.session_state.current_chat_id
        )

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None

if "model" not in st.session_state:
    st.session_state.model = "llama-3.3-70b-versatile"

# Authentication UI
if not st.session_state.authenticated:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 3rem;">
            <h1 style="background: linear-gradient(to right, #007aff, #00c6ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5rem; font-weight: 800;">
                🤖 Llama 3 Chatbot
            </h1>
            <p style="color: #a0a0a0; font-size: 1.2rem;">Sign in to access your personal AI assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Toggle between login and register
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Welcome Back!")
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            submit_login = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submit_login:
                success, user_id, message = authenticate_user(login_username, login_password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.username = login_username
                    
                    # Load user's chats from ChromaDB
                    loaded_sessions, loaded_current_id = load_user_chats(user_id)
                    
                    if loaded_sessions:
                        st.session_state.chat_sessions = loaded_sessions
                        st.session_state.current_chat_id = loaded_current_id or list(loaded_sessions.keys())[0]
                    else:
                        # Create first chat for new user
                        st.session_state.chat_sessions = {}
                        first_chat_id = create_new_chat()
                        st.session_state.current_chat_id = first_chat_id
                        save_to_chromadb()
                    
                    st.success(f"Welcome back, {login_username}!")
                    st.rerun()
                else:
                    st.error(message)
    
    with tab2:
        st.markdown("### Create Account")
        with st.form("register_form"):
            reg_username = st.text_input("Username (min 3 characters)", key="reg_username")
            reg_password = st.text_input("Password (min 6 characters)", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            submit_register = st.form_submit_button("Register", use_container_width=True, type="primary")
            
            if submit_register:
                if reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(reg_username, reg_password)
                    if success:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)
    
    st.stop()  # Stop here if not authenticated

# Main Chat Application (Only shown when authenticated)
# Initialize chat sessions for authenticated user
if "chat_sessions" not in st.session_state:
    # Load from ChromaDB
    loaded_sessions, loaded_current_id = load_user_chats(st.session_state.user_id)
    
    if loaded_sessions:
        st.session_state.chat_sessions = loaded_sessions
        st.session_state.current_chat_id = loaded_current_id or list(loaded_sessions.keys())[0]
    else:
        # Create first chat
        st.session_state.chat_sessions = {}
        first_chat_id = create_new_chat()
        st.session_state.current_chat_id = first_chat_id
        save_to_chromadb()

if "current_chat_id" not in st.session_state:
    first_chat_id = create_new_chat()
    st.session_state.current_chat_id = first_chat_id
    save_to_chromadb()

# Get current chat messages
current_messages = st.session_state.chat_sessions[st.session_state.current_chat_id]["messages"]

# Sidebar for Settings
with st.sidebar:
    # User info and logout
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem; padding: 1rem; background: rgba(137, 180, 250, 0.1); border-radius: 12px;">
            <p style="margin: 0; color: var(--accent-secondary); font-size: 0.9rem;">👤 Logged in as</p>
            <p style="margin: 0; color: var(--text-primary); font-weight: 600; font-size: 1.1rem;">{st.session_state.username}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", use_container_width=True):
        # Save chats before logging out
        save_to_chromadb()
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.chat_sessions = {}
        st.rerun()
    
    st.markdown("---")
    
    st.title("💬 Chats")
    
    # New Chat Button
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        new_chat_id = create_new_chat()
        st.session_state.current_chat_id = new_chat_id
        save_to_chromadb()
        st.rerun()
    
    st.markdown("---")
    
    # Display chat list
    st.markdown("### Chat History")
    
    # Sort chats by creation time (newest first)
    sorted_chats = sorted(
        st.session_state.chat_sessions.items(),
        key=lambda x: x[1]["created_at"],
        reverse=True
    )
    
    for chat_id, chat_data in sorted_chats:
        # Update title if messages exist
        if chat_data["messages"]:
            chat_data["title"] = get_chat_title(chat_data["messages"])
        
        # Show chat with selection indicator
        is_current = chat_id == st.session_state.current_chat_id
        button_label = f"{'🟢 ' if is_current else '⚪ '}{chat_data['title']}"
        
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(button_label, key=f"chat_{chat_id}", use_container_width=True):
                if chat_id != st.session_state.current_chat_id:
                    st.session_state.current_chat_id = chat_id
                    save_to_chromadb()
                    st.rerun()
        
        with col2:
            # Delete button (only if more than one chat exists)
            if len(st.session_state.chat_sessions) > 1:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    del st.session_state.chat_sessions[chat_id]
                    # Switch to another chat if current was deleted
                    if chat_id == st.session_state.current_chat_id:
                        st.session_state.current_chat_id = list(st.session_state.chat_sessions.keys())[0]
                    save_to_chromadb()
                    st.rerun()
    
    st.markdown("---")
    
    # Model Selection
    st.markdown("### Settings")
    st.session_state.model = st.selectbox(
        "Select Model",
        ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
        index=0
    )
    
    # Clear Current Chat Button
    if st.button("Clear Current Chat", use_container_width=True):
        st.session_state.chat_sessions[st.session_state.current_chat_id]["messages"] = []
        save_to_chromadb()
        st.rerun()
        
    st.markdown("---")
    st.markdown("### About")
    st.markdown("A compact, user-friendly chatbot powered by Groq and Llama 3.")
    
    st.markdown("---")
    st.markdown("### Developed by")
    st.markdown("**Pruthviraj**")
    st.markdown("📧 pruthvirajpasi42@gmail.com")

# Main Chat Interface
current_chat_title = st.session_state.chat_sessions[st.session_state.current_chat_id]["title"]

# col1, col2 = st.columns([5, 1])
# with col1:
st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="background: linear-gradient(to right, #007aff, #00c6ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; font-weight: 800;">
            {st.session_state.model}
        </h1>
        <p style="color: #a0a0a0;">💬 {current_chat_title}</p>
    </div>
""", unsafe_allow_html=True)

# Download Current Chat History
chat_str = "\n".join([f"{m['role']}: {m['content']}" for m in current_messages])
if current_messages:
    st.download_button(
        label="📥 Download Chat History",
        data=chat_str,
        file_name=f"chat_{current_chat_title[:20].replace(' ', '_')}.txt",
        mime="text/plain",
        use_container_width=False,
    )

# Display Chat Messages
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sample Prompts (Only show if chat is empty)
user_input = st.chat_input("Type your message here...")
selected_prompt = None

if len(current_messages) == 0:
    st.markdown('<div class="suggestion-row">', unsafe_allow_html=True)
    cols = st.columns(4)
    suggestions = [
        "🚀 Plan a trip to Mars",
        "🐍 Simple Python Script",
        "🎨 Suggest Color Palette",
        "📝 Summarize the Text"
    ]
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, key=f"suggestion_{i}"):
            selected_prompt = suggestion
    st.markdown('</div>', unsafe_allow_html=True)

# Handle Input (Chat Input or Suggestion Click)
if prompt := (user_input or selected_prompt):
    # Add user message to current chat
    current_messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=st.session_state.model,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in current_messages
                ],
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Add assistant response to current chat
            current_messages.append({"role": "assistant", "content": full_response})
            
            # Update chat title if this is the first message
            if len(current_messages) == 2:  # First user + first assistant message
                st.session_state.chat_sessions[st.session_state.current_chat_id]["title"] = get_chat_title(current_messages)
            
            # Save to ChromaDB
            save_to_chromadb()
            
            # Rerun to update the UI
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
