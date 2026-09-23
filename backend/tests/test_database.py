"""Tests for the SQLite cache layer (database.py)."""

import sqlite3

import pytest

import database


def test_insert_and_get_cached(test_db):
    database.insert_horoscope(
        sign="leo",
        date="2026-09-22",
        mood="happy",
        mood_color="#52B788",
        chaos_level=2,
        horoscope_text="You will find a great parking spot.",
    )

    row = database.get_cached("leo", "2026-09-22", "happy", 2)
    assert row is not None
    assert row["sign"] == "leo"
    assert row["mood"] == "happy"
    assert row["view_count"] == 1
    assert row["mood_source"] == "user"


def test_get_cached_miss_returns_none(test_db):
    row = database.get_cached("leo", "2026-09-22", "happy", 2)
    assert row is None


def test_increment_view_count(test_db):
    row = database.insert_horoscope(
        sign="pisces",
        date="2026-09-22",
        mood="calm",
        mood_color="#457B9D",
        chaos_level=1,
        horoscope_text="A quiet day awaits.",
    )
    assert row["view_count"] == 1

    new_count = database.increment_view_count(row["id"])
    assert new_count == 2

    new_count = database.increment_view_count(row["id"])
    assert new_count == 3


def test_auto_mood_cache_ignores_mood_in_key(test_db):
    """LLM-chosen-mood rows should be found by (sign, date, chaos_level)
    alone - the whole point is the mood isn't known until after generation."""
    database.insert_horoscope(
        sign="aries",
        date="2026-09-22",
        mood="excited",
        mood_color="#FFD60A",
        chaos_level=3,
        horoscope_text="Chaos awaits!",
        mood_source="llm",
    )

    cached = database.get_cached_auto("aries", "2026-09-22", 3)
    assert cached is not None
    assert cached["mood"] == "excited"

    # A user-mood row for the same sign/date/chaos should NOT satisfy the
    # auto-mood lookup - they're deliberately kept separate.
    database.insert_horoscope(
        sign="taurus",
        date="2026-09-22",
        mood="bored",
        mood_color="#6C757D",
        chaos_level=1,
        horoscope_text="Nothing much happens.",
        mood_source="user",
    )
    assert database.get_cached_auto("taurus", "2026-09-22", 1) is None


def test_user_mood_cache_key_uniqueness_enforced(test_db):
    """The same (sign, date, mood, chaos_level) combo shouldn't be
    insertable twice - that's the whole cache key."""
    kwargs = dict(
        sign="gemini",
        date="2026-09-22",
        mood="neutral",
        mood_color="#ADB5BD",
        chaos_level=2,
        horoscope_text="A day like any other.",
    )
    database.insert_horoscope(**kwargs)

    with pytest.raises(sqlite3.IntegrityError):
        database.insert_horoscope(**kwargs)


def test_init_db_migrates_pre_mood_source_schema(tmp_path, monkeypatch):
    """Simulates a database created before mood_source existed, and
    confirms init_db() adds the column (and the dependent index) without
    losing existing data - this is the exact bug that hit production."""
    db_path = tmp_path / "old_style.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
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
    )
    conn.execute(
        """
        INSERT INTO horoscopes
            (sign, date, mood, mood_color, chaos_level, horoscope_text, view_count)
        VALUES
            ('virgo', '2026-09-20', 'calm', '#457B9D', 1,
             'Old row from before the migration.', 3)
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()

    conn = sqlite3.connect(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(horoscopes)")]
    assert "mood_source" in columns

    old_row = conn.execute("SELECT * FROM horoscopes WHERE sign = 'virgo'").fetchone()
    assert old_row is not None  # existing data survived the migration

    indexes = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")]
    assert "idx_auto_mood_cache" in indexes