import streamlit as st
import os
from groq import Groq
from dotenv import load_dotenv

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

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "model" not in st.session_state:
    st.session_state.model = "llama-3.3-70b-versatile"

# Sidebar for Settings
with st.sidebar:
    st.title("Settings")
    st.markdown("---")
    
    # Model Selection
    st.session_state.model = st.selectbox(
        "Select Model",
        ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
        index=0
    )
    
    # Clear Chat Button
    if st.button("Clear Conversation", type="primary"):
        st.session_state.messages = []
        st.rerun()

    # Download Chat History
    chat_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
    st.download_button(
        label="Download Chat History",
        data=chat_str,
        file_name="chat_history.txt",
        mime="text/plain"
    )
        
    st.markdown("---")
    st.markdown("### About")
    st.markdown("A compact, user-friendly chatbot powered by Groq and Llama 3.")
    
    st.markdown("---")
    st.markdown("### Developed by")
    st.markdown("**Pruthviraj**")
    st.markdown("📧 pruthvirajpasi42@gmail.com")

# Main Chat Interface
st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="background: linear-gradient(to right, #007aff, #00c6ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem; font-weight: 800;">
            {st.session_state.model}
        </h1>
        <p style="color: #a0a0a0;">Ask me anything!</p>
    </div>
""", unsafe_allow_html=True)

# Display Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sample Prompts (Only show if chat is empty)
user_input = st.chat_input("Type your message here...")
selected_prompt = None

if len(st.session_state.messages) == 0:
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
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately (if it wasn't already displayed by the loop)
    # Note: If we just appended, the loop above won't show it until next rerun, 
    # but st.chat_message below handles the immediate display.
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
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Add assistant response to state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # Rerun to update the UI (remove suggestions if they were clicked)
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
