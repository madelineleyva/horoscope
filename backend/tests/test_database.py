"""Tests for the SQLite cache layer (database.py)."""

import sqlite3

import database

COMMON = dict(date="2026-09-22", chaos_level=2, mood_color="#52B788", horoscope_text="Text.")


def test_insert_and_get_cached(test_db):
    row, created = database.insert_horoscope(
        sign="leo",
        requested_mood="happy",
        mood="happy",
        **{**COMMON, "horoscope_text": "You will find a great parking spot."},
    )
    assert created is True

    cached = database.get_cached("leo", "2026-09-22", 2, "happy")
    assert cached is not None
    assert cached["id"] == row["id"]
    assert cached["mood"] == "happy"
    assert cached["view_count"] == 1


def test_get_cached_miss_returns_none(test_db):
    assert database.get_cached("leo", "2026-09-22", 2, "happy") is None
    assert database.get_cached("leo", "2026-09-22", 2) is None


def test_increment_view_count(test_db):
    row, _ = database.insert_horoscope(
        sign="pisces", requested_mood="calm", mood="calm", **{**COMMON, "chaos_level": 1}
    )
    assert row["view_count"] == 1
    assert database.increment_view_count(row["id"]) == 2
    assert database.increment_view_count(row["id"]) == 3


def test_auto_lookup_ignores_the_mood_claude_picked(test_db):
    """For auto requests the mood isn't known up front, so the lookup is by
    (sign, date, chaos_level) alone."""
    database.insert_horoscope(
        sign="aries", requested_mood=None, mood="excited", **{**COMMON, "chaos_level": 3}
    )
    cached = database.get_cached("aries", "2026-09-22", 3)
    assert cached is not None
    assert cached["mood"] == "excited"


def test_user_row_does_not_satisfy_auto_lookup(test_db):
    database.insert_horoscope(
        sign="taurus", requested_mood="bored", mood="bored", **{**COMMON, "chaos_level": 1}
    )
    assert database.get_cached("taurus", "2026-09-22", 1) is None


def test_user_and_auto_requests_can_share_a_displayed_mood(test_db):
    """Regression test. A user picks 'happy' on the classic page, then the
    Win98 page asks Claude to choose and Claude also picks 'happy'. This used
    to raise IntegrityError (after the paid LLM call, with nothing cached)."""
    user_row, user_created = database.insert_horoscope(
        sign="aries", requested_mood="happy", mood="happy", **COMMON
    )
    auto_row, auto_created = database.insert_horoscope(
        sign="aries", requested_mood=None, mood="happy", **COMMON
    )

    assert user_created and auto_created
    assert user_row["id"] != auto_row["id"]
    assert database.get_cached("aries", "2026-09-22", 2, "happy")["id"] == user_row["id"]
    assert database.get_cached("aries", "2026-09-22", 2)["id"] == auto_row["id"]


def test_duplicate_insert_returns_existing_row_instead_of_raising(test_db):
    """Two requests can both miss the cache and both call the LLM. The second
    insert must not crash or overwrite the first row."""
    first, first_created = database.insert_horoscope(
        sign="gemini",
        requested_mood="neutral",
        mood="neutral",
        **{**COMMON, "horoscope_text": "first writer wins"},
    )
    second, second_created = database.insert_horoscope(
        sign="gemini",
        requested_mood="neutral",
        mood="neutral",
        **{**COMMON, "horoscope_text": "second writer loses"},
    )

    assert first_created is True
    assert second_created is False
    assert second["id"] == first["id"]
    assert second["horoscope_text"] == "first writer wins"


def test_fresh_database_gets_current_schema_version(test_db):
    conn = sqlite3.connect(test_db)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == database.SCHEMA_VERSION
    conn.close()


def test_init_db_is_idempotent(test_db):
    database.insert_horoscope(sign="leo", requested_mood="calm", mood="calm", **COMMON)
    database.init_db()
    database.init_db()
    assert database.get_cached("leo", "2026-09-22", 2, "calm") is not None


# --- Migrations from the two legacy schemas -------------------------------

V0_TABLE = """
CREATE TABLE horoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sign TEXT NOT NULL,
    date TEXT NOT NULL,
    mood TEXT NOT NULL,
    mood_color TEXT NOT NULL,
    chaos_level INTEGER NOT NULL,
    horoscope_text TEXT NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(sign, date, mood, chaos_level)
)
"""

V1_TABLE = V0_TABLE.replace(
    "UNIQUE(sign",
    "mood_source TEXT NOT NULL DEFAULT 'user',\n    UNIQUE(sign",
)


def _make_legacy_db(path, table_sql, rows):
    conn = sqlite3.connect(path)
    conn.execute(table_sql)
    for row in rows:
        conn.execute(row)
    conn.commit()
    conn.close()


def test_migrates_v0_schema_preserving_rows(tmp_path, monkeypatch):
    """A database from before mood_source existed."""
    db_path = tmp_path / "v0.db"
    _make_legacy_db(
        db_path,
        V0_TABLE,
        [
            """INSERT INTO horoscopes (sign, date, mood, mood_color, chaos_level,
                   horoscope_text, view_count)
               VALUES ('virgo', '2026-09-20', 'calm', '#457B9D', 1, 'Old row.', 3)"""
        ],
    )
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()

    row = database.get_cached("virgo", "2026-09-20", 1, "calm")
    assert row is not None
    assert row["horoscope_text"] == "Old row."
    assert row["view_count"] == 3


def test_migrates_v1_schema_mapping_llm_rows_to_auto(tmp_path, monkeypatch):
    """A database from the mood_source era, including the llm-picked rows."""
    db_path = tmp_path / "v1.db"
    _make_legacy_db(
        db_path,
        V1_TABLE,
        [
            """INSERT INTO horoscopes (sign, date, mood, mood_color, chaos_level,
                   horoscope_text, view_count, mood_source)
               VALUES ('leo', '2026-09-20', 'happy', '#52B788', 2, 'user row', 2, 'user')""",
            """INSERT INTO horoscopes (sign, date, mood, mood_color, chaos_level,
                   horoscope_text, view_count, mood_source)
               VALUES ('leo', '2026-09-20', 'excited', '#FFD60A', 2, 'llm row', 5, 'llm')""",
        ],
    )
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()

    user_row = database.get_cached("leo", "2026-09-20", 2, "happy")
    auto_row = database.get_cached("leo", "2026-09-20", 2)
    assert user_row["horoscope_text"] == "user row"
    assert auto_row["horoscope_text"] == "llm row"
    assert auto_row["mood"] == "excited"  # displayed mood is untouched
    assert auto_row["view_count"] == 5

    # The migrated database no longer has the collision bug.
    _, created = database.insert_horoscope(
        sign="leo",
        date="2026-09-20",
        chaos_level=2,
        requested_mood=None,
        mood="happy",
        mood_color="#52B788",
        horoscope_text="ignored: auto row already exists",
    )
    assert created is False


def test_migration_leaves_no_legacy_table_behind(tmp_path, monkeypatch):
    db_path = tmp_path / "v1.db"
    _make_legacy_db(db_path, V1_TABLE, [])
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "horoscopes_legacy" not in tables
    assert "horoscopes" in tables
