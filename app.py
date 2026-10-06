from threading import Lock
import streamlit as st
from config import DEMO_MODE, DEMO_DB_PATH, validate_config
from chatbot import SQLChatbot
from database import test_connection
from schema_inspector import get_schema_text
from sample_data import seed_database
from demo_runtime import RateBudget, safe_error

st.set_page_config(page_title="SQL Chatbot | Nitesh Kelwani", page_icon="🗄️", layout="wide")


@st.cache_resource
def prepare_database():
    if DEMO_MODE and not DEMO_DB_PATH.exists():
        temporary = DEMO_DB_PATH.with_suffix(".seed.db")
        seed_database(temporary)
        temporary.replace(DEMO_DB_PATH)
    return test_connection()


@st.cache_resource
def request_lock():
    return Lock()


if "budget" not in st.session_state:
    st.session_state.budget = RateBudget()
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("SQL Chatbot")
st.caption("Ask a sample e-commerce database in plain English. Explore the SQL, results and explanation.")
try:
    ready = prepare_database()
    validate_config()
    if not ready:
        st.warning("The sample database is unavailable. Please try again later.")
except EnvironmentError:
    ready = False
    st.info("This demo's AI service is not configured yet. Please check back soon.")
except Exception:
    ready = False
    st.warning("The demo is temporarily unavailable. Please try again later.")

with st.sidebar:
    st.subheader("Sample e-commerce data")
    st.write("50 customers · 15 products · 200 orders")
    st.caption("Synthetic data. Queries cannot modify the database. Results are limited to 200 rows.")
    st.caption("Questions and sample query results are sent to the configured AI provider. Please avoid personal information.")
    if ready:
        with st.expander("Database schema"):
            st.code(get_schema_text(), language="sql")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("chatbot", None)
        st.rerun()
    st.caption("Free demo · five questions per minute · shared AI quotas apply")

if not st.session_state.messages:
    st.markdown("**Try asking:**\n- Which product category has the highest sales?\n- Who are the top five customers by total spend?\n- What is the average order value by status?")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.warning(message["error"])
        else:
            st.markdown(message.get("content") or "")
        if message.get("sql"):
            with st.expander("Generated SQL"):
                st.code(message["sql"], language="sql")
                st.caption(message.get("explanation") or "")
        if message.get("results") is not None:
            st.dataframe(message["results"], use_container_width=True)

prompt = st.chat_input("Ask about the sample data", disabled=not ready, max_chars=1000)
if prompt:
    gate = request_lock()
    acquired = gate.acquire(blocking=False)
    if not acquired:
        st.warning("The demo is serving another request. Please try again shortly.")
    else:
        try:
            st.session_state.budget.take()
            st.session_state.messages.append({"role": "user", "content": prompt})
            if "chatbot" not in st.session_state:
                st.session_state.chatbot = SQLChatbot()
            with st.spinner("Writing and running a read-only query..."):
                response = st.session_state.chatbot.ask(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response["answer"], **response})
            st.session_state.messages = st.session_state.messages[-12:]
        except Exception as exc:
            st.session_state.messages.append({"role": "assistant", "error": safe_error(exc)})
        finally:
            gate.release()
        st.rerun()
