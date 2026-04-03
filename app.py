# app.py — Streamlit frontend for the SQL Chatbot
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd

from config import validate_config, AZURE_OPENAI_CHAT_DEPLOYMENT, DATABASE_URL
from chatbot import SQLChatbot
from database import test_connection
from schema_inspector import get_schema_text, get_table_names
from sample_data import seed_database
import os

# --- Page config (must be the first Streamlit call) ---
st.set_page_config(
    page_title="SQL Chatbot",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for a clean, modern look ---
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        min-height: 100vh;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.04);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Chat message bubbles */
    .user-bubble {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 14px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
        font-size: 0.95rem;
        line-height: 1.5;
    }

    .bot-bubble {
        background: rgba(255, 255, 255, 0.07);
        color: #e2e8f0;
        padding: 14px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 85%;
        border: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Status badges */
    .badge-green {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-red {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* Input area */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 12px !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);
    }

    /* Title gradient */
    .title-gradient {
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 800;
    }

    /* Code block in expander */
    code {
        background: rgba(0,0,0,0.3) !important;
        color: #a5f3fc !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 8px !important;
        color: #94a3b8 !important;
    }

    /* DataFrames */
    .dataframe {
        background: rgba(0,0,0,0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Initialise session state on first load
# ─────────────────────────────────────────────

def init_session():
    """Set up all Streamlit session state variables."""
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None        # SQLChatbot instance
    if "messages" not in st.session_state:
        st.session_state.messages = []         # list of chat messages for display
    if "config_ok" not in st.session_state:
        st.session_state.config_ok = False     # True once .env is validated
    if "db_ok" not in st.session_state:
        st.session_state.db_ok = False         # True once DB connection works

init_session()


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🗄️ SQL Chatbot")
    st.markdown("*Powered by Azure OpenAI*")
    st.divider()

    # --- Status indicators ---
    st.markdown("### System Status")

    # Validate Azure OpenAI config
    try:
        validate_config()
        st.session_state.config_ok = True
        st.markdown('<span class="badge-green">✓ Azure OpenAI connected</span>', unsafe_allow_html=True)
    except EnvironmentError as e:
        st.session_state.config_ok = False
        st.markdown('<span class="badge-red">✗ Azure OpenAI not configured</span>', unsafe_allow_html=True)
        st.caption(str(e))

    st.caption(f"Model: `{AZURE_OPENAI_CHAT_DEPLOYMENT}`")

    # Check database connection
    if test_connection():
        st.session_state.db_ok = True
        st.markdown('<span class="badge-green">✓ Database connected</span>', unsafe_allow_html=True)
    else:
        st.session_state.db_ok = False
        st.markdown('<span class="badge-red">✗ Database not connected</span>', unsafe_allow_html=True)

    st.caption(f"DB: `{DATABASE_URL}`")
    st.divider()

    # --- Demo database seeder ---
    st.markdown("### 🧪 Demo Database")
    st.caption("Seed a demo e-commerce database to try the chatbot immediately.")
    if st.button("🌱 Seed Demo Data", use_container_width=True):
        with st.spinner("Creating demo database..."):
            seed_database()
        st.success("Demo database ready!")
        st.rerun()

    st.divider()

    # --- Schema viewer ---
    st.markdown("### 📋 Database Schema")
    if st.session_state.db_ok:
        tables = get_table_names()
        if tables:
            with st.expander(f"{len(tables)} table(s) found", expanded=False):
                st.code(get_schema_text(), language="sql")
        else:
            st.caption("No tables found. Seed demo data first.")
    else:
        st.caption("Connect to a database to view schema.")

    st.divider()

    # --- Reset button ---
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        if st.session_state.chatbot:
            st.session_state.chatbot.reset()
        st.rerun()


# ─────────────────────────────────────────────
# Main chat area
# ─────────────────────────────────────────────

# Header
st.markdown('<div class="title-gradient">SQL Chatbot</div>', unsafe_allow_html=True)
st.markdown("Ask questions in plain English — I'll write and run the SQL for you.")
st.divider()

# Show a welcome message if chat is empty
if not st.session_state.messages:
    st.markdown("""
    **💡 Try asking:**
    - *"Show me all customers from New York"*
    - *"Which product category has the highest total sales?"*
    - *"How many orders were placed in 2024?"*
    - *"List the top 5 customers by total spend"*
    - *"What is the average order value by status?"*
    """)

# --- Render existing chat messages ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-bubble">👤 {msg["content"]}</div>', unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        st.markdown(f'<div class="bot-bubble">🤖 {msg["answer"]}</div>', unsafe_allow_html=True)

        # Show SQL query in a collapsible block
        if msg.get("sql"):
            with st.expander("📝 View Generated SQL", expanded=False):
                st.code(msg["sql"], language="sql")
                if msg.get("explanation"):
                    st.caption(f"ℹ️ {msg['explanation']}")

        # Show query results as a table
        if msg.get("results") is not None and not msg["results"].empty:
            with st.expander(f"📊 View Results ({len(msg['results'])} rows)", expanded=False):
                st.dataframe(msg["results"], use_container_width=True)

    elif msg["role"] == "error":
        st.error(f"⚠️ {msg['content']}")


# ─────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────

# Disable input if config or DB is not ready
input_disabled = not (st.session_state.config_ok and st.session_state.db_ok)
placeholder    = "Ask a question about your data..." if not input_disabled else "⚠️ Configure .env and connect a database first"

user_input = st.chat_input(placeholder, disabled=input_disabled)

if user_input:
    # Add user message to display history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Initialise chatbot if this is the first message
    if st.session_state.chatbot is None:
        st.session_state.chatbot = SQLChatbot()

    # Call the chatbot pipeline
    with st.spinner("Thinking..."):
        result = st.session_state.chatbot.ask(user_input)

    if result["error"]:
        # Show error message
        st.session_state.messages.append({"role": "error", "content": result["error"]})
    else:
        # Add assistant response to display history
        st.session_state.messages.append({
            "role":        "assistant",
            "answer":      result["answer"],
            "sql":         result["sql"],
            "explanation": result["explanation"],
            "results":     result["results"],
        })

    # Rerun to display the new messages
    st.rerun()
