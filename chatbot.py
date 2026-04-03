# chatbot.py — core logic: converts natural language to SQL, runs it, and explains results

import re
import json
import pandas as pd
from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_CHAT_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)
from schema_inspector import get_schema_text
from database import run_query


# --- Azure OpenAI client (created once at import time) ---
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)


def build_system_prompt(schema: str) -> str:
    """
    Build the system prompt that tells the LLM:
    - Its role
    - The database schema
    - How to format its response (JSON with sql + explanation fields)
    """
    return f"""You are a helpful SQL assistant. You help users query a database using natural language.

DATABASE SCHEMA:
{schema}

INSTRUCTIONS:
1. When the user asks a question, generate a valid SQL SELECT query for the above schema.
2. Always respond in this exact JSON format:
   {{
     "sql": "<your SQL query here>",
     "explanation": "<brief explanation of what the query does>"
   }}
3. Use only SELECT statements — never INSERT, UPDATE, DELETE, DROP, etc.
4. If the question cannot be answered with the given schema, set "sql" to null and explain why in "explanation".
5. Use proper SQL syntax compatible with SQLite.
6. For date comparisons, use SQLite date functions like date(), strftime().
7. Always alias aggregated columns for clarity (e.g., COUNT(*) AS total_orders).
"""


def extract_json_from_response(text: str) -> dict:
    """
    Parse the LLM response text to extract the JSON object.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    # Remove markdown code fences if present (```json ... ```)
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If JSON parsing fails, return a fallback structure
        return {"sql": None, "explanation": text}


class SQLChatbot:
    """
    Main chatbot class.
    Maintains conversation history and handles the NL → SQL → Answer pipeline.
    """

    def __init__(self):
        # Load DB schema once when the chatbot starts
        self.schema = get_schema_text()
        self.system_prompt = build_system_prompt(self.schema)

        # Conversation history: list of {"role": ..., "content": ...} dicts
        self.history: list[dict] = []

    def reset(self):
        """Clear the conversation history to start a fresh session."""
        self.history = []

    def ask(self, user_message: str) -> dict:
        """
        Full pipeline for one user turn:
          1. Send the question to Azure OpenAI → get SQL + explanation
          2. Execute the SQL against the database
          3. Send results back to Azure OpenAI → get a human-readable answer
          4. Return everything to the UI layer

        Returns a dict with keys:
          - sql         : the generated SQL string (or None)
          - explanation : what the query does
          - results     : pandas DataFrame (or None)
          - answer      : natural language answer summarising the results
          - error       : error message string (or None)
        """
        # Add user message to conversation history
        self.history.append({"role": "user", "content": user_message})

        # --- Step 1: Generate SQL ---
        try:
            sql_response = client.chat.completions.create(
                model=AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.history,
                ],
                temperature=1,              # gpt-5.1 requires temperature=1
                max_completion_tokens=800,  # gpt-5.1+ uses max_completion_tokens
            )
        except Exception as e:
            return {"sql": None, "explanation": None, "results": None,
                    "answer": None, "error": f"Azure OpenAI error: {e}"}

        raw_text = sql_response.choices[0].message.content
        parsed   = extract_json_from_response(raw_text)
        sql      = parsed.get("sql")
        explanation = parsed.get("explanation", "")

        # Add assistant's SQL response to history
        self.history.append({"role": "assistant", "content": raw_text})

        # If no SQL was generated, return the explanation as the answer
        if not sql:
            return {"sql": None, "explanation": explanation,
                    "results": None, "answer": explanation, "error": None}

        # --- Step 2: Execute SQL ---
        try:
            df = run_query(sql)
        except Exception as e:
            return {"sql": sql, "explanation": explanation,
                    "results": None, "answer": None, "error": str(e)}

        # --- Step 3: Generate a natural language answer from the results ---
        # Convert DataFrame to a small text summary for the LLM
        if df.empty:
            results_text = "The query returned no rows."
        else:
            # Limit to first 20 rows to keep prompt size manageable
            results_text = df.head(20).to_string(index=False)

        answer_prompt = (
            f"The user asked: \"{user_message}\"\n\n"
            f"SQL executed:\n{sql}\n\n"
            f"Query results:\n{results_text}\n\n"
            "Please provide a clear, concise natural language answer based on the results. "
            "If there are numbers, highlight the most important insights."
        )

        try:
            answer_response = client.chat.completions.create(
                model=AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst. Summarise database query results in plain English."},
                    {"role": "user",   "content": answer_prompt},
                ],
                temperature=1,              # gpt-5.1 requires temperature=1
                max_completion_tokens=500,  # gpt-5.1+ uses max_completion_tokens
            )
            answer = answer_response.choices[0].message.content
        except Exception as e:
            # Fall back to raw results if summarisation fails
            answer = f"Query succeeded. {len(df)} row(s) returned.\n\n(Summary unavailable: {e})"

        # Add the final answer to history so follow-up questions have context
        self.history.append({"role": "assistant", "content": answer})

        return {
            "sql":         sql,
            "explanation": explanation,
            "results":     df,
            "answer":      answer,
            "error":       None,
        }
