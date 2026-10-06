from types import SimpleNamespace
import pytest
import database
from chatbot import SQLChatbot
from sample_data import seed_database
from demo_runtime import RateBudget, UsageLimit, safe_error


@pytest.fixture(autouse=True)
def database_fixture(tmp_path, monkeypatch):
    path = tmp_path / 'demo.db'
    seed_database(path)
    monkeypatch.setattr(database, 'DATABASE_URL', f'sqlite:///{path.as_posix()}')


def test_join_and_followup_pipeline():
    responses = iter([
        '{"sql":"SELECT COUNT(*) AS customers FROM customers", "explanation":"Count customers"}',
        'There are 50 customers.',
        '{"sql":"SELECT COUNT(*) AS customers FROM customers WHERE city = \'New York\'", "explanation":"Filter customers"}',
        'These are the customers in New York.',
    ])
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(responses)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    bot = SQLChatbot(client, 'test-model')
    assert bot.ask('How many customers?')['results'].iloc[0, 0] == 50
    assert bot.ask('How many of them are in New York?')['error'] is None
    assert any('There are 50' in msg['content'] for msg in calls[2]['messages'])
    assert all(call['max_completion_tokens'] == 700 for call in calls)
    result = database.run_query('SELECT p.category, SUM(i.quantity) FROM products p JOIN order_items i ON p.id=i.product_id GROUP BY p.category')
    assert len(result) > 0


@pytest.mark.parametrize('sql', [
    'DELETE FROM customers', 'DROP TABLE customers', 'PRAGMA writable_schema=ON',
    "ATTACH DATABASE ':memory:' AS other", 'SELECT 1; DELETE FROM customers',
    'WITH x AS (SELECT 1) DELETE FROM customers', "SELECT load_extension('nope')",
    'SELECT randomblob(1000000000)',
])
def test_unsafe_sql_is_rejected(sql):
    with pytest.raises(ValueError):
        database.run_query(sql)
    assert database.run_query('SELECT COUNT(*) AS n FROM customers').iloc[0, 0] == 50


def test_limits():
    with pytest.raises(ValueError, match='200 rows'):
        database.run_query('SELECT * FROM order_items')
    with pytest.raises(ValueError, match='expensive'):
        database.run_query('WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x WHERE n<1000000000) SELECT SUM(n) FROM x')


def test_rate_limit_and_redaction():
    now = [0]
    budget = RateBudget(lambda: now[0])
    for _ in range(5):
        budget.take()
    with pytest.raises(UsageLimit):
        budget.take()
    now[0] = 60
    budget.take()
    assert 'secret-key' not in safe_error(RuntimeError('secret-key endpoint internal-trace'))
    assert 'too long' in safe_error(TimeoutError('secret-key'))
    error = RuntimeError('secret-key')
    error.status_code = 429
    assert 'quota' in safe_error(error)


def test_missing_secrets_ui(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    import config
    monkeypatch.setattr(config, 'GROQ_API_KEY', '')
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=20)
    assert not app.exception
    assert app.chat_input[0].disabled
    assert any('not configured' in item.value for item in app.info)
