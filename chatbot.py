"""Natural language -> bounded SQL -> result explanation."""
import json
import re
from config import AI_PROVIDER, make_client
from database import run_query
from schema_inspector import get_schema_text
from demo_runtime import safe_error, trim_history


def extract_json_from_response(text):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        return {"sql": None, "explanation": "I couldn't generate a query. Please rephrase your question."}


class SQLChatbot:
    def __init__(self, client=None, model=None):
        self.client, self.model = (client, model) if client is not None else make_client()
        self.history = []
        self.system_prompt = (
            "Generate SQLite SELECT queries for this synthetic e-commerce database. "
            "Respond as a JSON object with sql and explanation. Use sql=null when unanswerable. "
            "Never modify data. Limit lists to 200 rows. Only use the supplied tables.\n"
            + get_schema_text()
        )

    def reset(self):
        self.history.clear()

    def complete(self, messages, json_mode=False):
        params = dict(model=self.model, messages=messages, temperature=1, max_completion_tokens=700)
        if json_mode:
            params["response_format"] = {"type": "json_object"}
        if AI_PROVIDER == "groq" and self.model.startswith("openai/gpt-oss"):
            params["extra_body"] = {"reasoning_effort": "low"}
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    def ask(self, user_message):
        result = dict(sql=None, explanation=None, results=None, answer=None, error=None)
        if not isinstance(user_message, str) or not 3 <= len(user_message.strip()) <= 1000:
            result["error"] = "Please enter a question between 3 and 1,000 characters."
            return result
        try:
            parsed = extract_json_from_response(self.complete([
                {"role": "system", "content": self.system_prompt},
                *trim_history(self.history), {"role": "user", "content": user_message},
            ], json_mode=True))
            sql = parsed.get("sql")
            if sql is not None and not isinstance(sql, str):
                result["error"] = "I couldn't generate a valid query. Please rephrase your question."
                return result
            explanation = str(parsed.get("explanation") or "")[:1500]
            result.update(sql=sql, explanation=explanation)
            if not sql:
                result["answer"] = explanation
            else:
                try:
                    frame = run_query(sql)
                except ValueError as exc:
                    result["error"] = str(exc)
                    return result
                result["results"] = frame
                try:
                    result["answer"] = self.complete([
                        {"role": "system", "content": "Explain only the supplied query results. Do not invent data."},
                        {"role": "user", "content": f"Question: {user_message}\nSQL: {sql}\nFirst 20 of {len(frame)} returned rows:\n{frame.head(20).to_string(index=False)[:6000]}"},
                    ])
                except Exception as exc:
                    result["answer"] = f"Query succeeded: {len(frame)} rows returned. " + safe_error(exc)
            self.history = trim_history([*self.history, {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"SQL: {sql}\n{result['answer']}"}])
        except Exception as exc:
            result["error"] = safe_error(exc)
        return result
