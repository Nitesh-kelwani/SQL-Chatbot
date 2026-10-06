"""Environment/Streamlit secrets; clients are created only after validation."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1-chat")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_DB_PATH = Path(__file__).parent / "demo.db"
DATABASE_URL = f"sqlite:///{DEMO_DB_PATH.as_posix()}" if DEMO_MODE else os.getenv("DATABASE_URL", "sqlite:///demo.db")


def validate_config():
    if AI_PROVIDER not in {"groq", "azure"}:
        raise EnvironmentError("AI_PROVIDER must be groq or azure.")
    if AI_PROVIDER == "groq" and not GROQ_API_KEY:
        raise EnvironmentError("The demo owner needs to configure the AI service.")
    if AI_PROVIDER == "azure" and not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY):
        raise EnvironmentError("The demo owner needs to configure the Azure AI service.")


def make_client():
    from openai import OpenAI, AzureOpenAI
    validate_config()
    if AI_PROVIDER == "groq":
        return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1",
                      timeout=30, max_retries=0), GROQ_MODEL
    return AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY,
                       api_version=AZURE_OPENAI_API_VERSION, timeout=30, max_retries=0), AZURE_OPENAI_CHAT_DEPLOYMENT
