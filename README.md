## Public portfolio demo

The public deployment uses Groq (`openai/gpt-oss-20b`) and automatically initializes synthetic e-commerce data.
Python 3.12; Streamlit Community Cloud entrypoint: `app.py`. Configure root secrets `AI_PROVIDER="groq"`,
`GROQ_API_KEY`, `GROQ_MODEL="openai/gpt-oss-20b"`, and `DEMO_MODE="true"` in the hosting dashboard.
Never commit `.env` or `.streamlit/secrets.toml`. Use your personal GitHub and Groq accounts only.

Queries run through read-only SQLite connections and an authorizer, with 200-row, two-second and VM-operation limits.
Each session has a five-question/minute allowance and bounded history. Clear chat does not reset the allowance.
Questions and synthetic results are sent to the AI provider. Quota and configuration failures display safe messages.
Free hosting can sleep. Verify the public URL while signed out before linking it from your portfolio.

Run tests with `pip install pytest==8.4.1` and `python -m pytest -q`.
For local Azure use, set `AI_PROVIDER=azure` and the Azure variables documented below. The demo supports SQLite only.
The old manual reseeding UI is replaced by automatic startup initialization.
# SQL Chatbot with Azure OpenAI

A conversational SQL assistant that accepts natural language questions and returns SQL queries, results, and a human-readable explanation — all powered by Azure OpenAI.

---

## Features

- **Natural Language → SQL**: Ask questions in plain English
- **Auto Schema Detection**: Reads your database schema automatically
- **Result Explanation**: Summarises query results in natural language
- **Multi-turn Memory**: Follow-up questions work in context
- **Safe Execution**: Only SELECT queries allowed
- **Demo Mode**: Seeded e-commerce SQLite database for instant testing

---

## Project Structure

```
SQL Chatbot/
├── app.py               # Streamlit chat UI
├── chatbot.py           # Core NL → SQL → Answer pipeline
├── database.py          # Database connection + query execution
├── schema_inspector.py  # Reads DB schema for the LLM prompt
├── sample_data.py       # Seeds a demo SQLite database
├── config.py            # Loads settings from .env
├── .env                 # Your secrets (never commit this)
├── .env.example         # Template for .env
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
# Copy the template
copy .env.example .env
```

Then open `.env` and fill in your Azure OpenAI values:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.1-chat
AZURE_OPENAI_API_VERSION=2024-12-01-preview
DATABASE_URL=sqlite:///demo.db
```

### 3. Seed the demo database (optional but recommended)

```bash
python sample_data.py
```

This creates `demo.db` with 4 tables:
- **customers** — 50 records
- **products** — 15 records
- **orders** — 200 records
- **order_items** — ~400 records

### 4. Run the app

```bash
streamlit run app.py
```

---

## Example Questions to Try

| Question | What it tests |
|----------|--------------|
| *"Show me all customers from New York"* | Basic filter |
| *"Which product has the highest price?"* | Aggregation |
| *"Top 5 customers by total spend"* | JOIN + GROUP BY + ORDER BY |
| *"How many orders were placed in 2024?"* | Date filtering |
| *"What is the average order value by status?"* | GROUP BY |
| *"Which product category sells the most units?"* | Multi-table JOIN |

---

## Using Your Own Database

Change the `DATABASE_URL` in your `.env`:

| Database | Connection String Format |
|----------|--------------------------|
| SQLite | `sqlite:///path/to/file.db` |
| SQL Server | `mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server` |
| PostgreSQL | `postgresql://user:pass@host/db` |
| MySQL | `mysql+pymysql://user:pass@host/db` |

> Install the matching driver with pip if needed (e.g. `pip install pyodbc` for SQL Server).

---

## Architecture

```
User Question
     │
     ▼
Azure OpenAI (Step 1)
  → Reads schema + question
  → Returns JSON: { "sql": "...", "explanation": "..." }
     │
     ▼
Database Layer
  → Executes SELECT query
  → Returns pandas DataFrame
     │
     ▼
Azure OpenAI (Step 2)
  → Reads question + results
  → Returns natural language answer
     │
     ▼
Streamlit UI (displays answer + SQL + table)
```
