# config.py — loads Azure OpenAI settings from the .env file

import os
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()

# --- Azure OpenAI settings ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1-chat")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# --- Database settings ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///demo.db")


def validate_config():
    """Check that required environment variables are set before starting."""
    missing = []

    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please copy .env.example to .env and fill in your values."
        )
