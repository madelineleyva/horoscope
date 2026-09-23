"""
Shared test fixtures. conftest.py is loaded by pytest before any test
module in this directory, so setting the dummy API key here (as top-level
code, not inside a fixture) guarantees it's in place before main.py ever
gets imported and tries to build the real Anthropic client.
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-ci")

import pytest  # noqa: E402 (must come after the env var is set above)

import database  # noqa: E402


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Points database.py at a fresh, isolated SQLite file for this test,
    so tests never touch your real local horoscopes.db."""
    db_path = tmp_path / "test_horoscopes.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    return db_path
