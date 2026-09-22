"""
SQLite cache layer

Cache key = (sign, date, mood, chaos_level) — matches the UNIQUE
constraint below, so re-requesting the same combo on the same day
never calls the LLM twice.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "horoscopes.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS horoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sign TEXT NOT NULL,
    date TEXT NOT NULL,
    mood TEXT NOT NULL,
    mood_color TEXT NOT NULL,
    chaos_level INTEGER NOT NULL,
    horoscope_text TEXT NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- 'user': mood was chosen by the caller (original UI).
    -- 'llm': mood was chosen by Claude as part of generation (Win98 page).
    mood_source TEXT NOT NULL DEFAULT 'user',
    UNIQUE(sign, date, mood, chaos_level)
);
"""

# For 'llm' rows the mood isn't known until after generation, so we cache
# one row per (sign, date, chaos_level) regardless of which mood Claude
# picked. A partial unique index lets us enforce that only for these rows,
# without touching the 'user' rows' existing (sign, date, mood, chaos_level)
# uniqueness above. This must run AFTER the mood_source migration below,
# since it references that column.
CREATE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_auto_mood_cache
    ON horoscopes(sign, date, chaos_level)
    WHERE mood_source = 'llm';
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(CREATE_TABLE_SQL)

        # Migration: databases created before mood_source existed won't have
        # the column yet (CREATE TABLE IF NOT EXISTS won't add it). Add it
        # if missing so existing local .db files keep working. This has to
        # run before the index below, since that index references the column.
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(horoscopes)")]
        if "mood_source" not in columns:
            conn.execute(
                "ALTER TABLE horoscopes ADD COLUMN mood_source TEXT NOT NULL DEFAULT 'user'"
            )

        conn.executescript(CREATE_INDEX_SQL)


def get_cached(sign: str, date: str, mood: str, chaos_level: int):
    """Look up today's row for this exact combo. Returns None on a miss."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM horoscopes
            WHERE sign = ? AND date = ? AND mood = ? AND chaos_level = ?
            """,
            (sign, date, mood, chaos_level),
        ).fetchone()
        return dict(row) if row else None


def get_cached_auto(sign: str, date: str, chaos_level: int):
    """Cache lookup for the LLM-picks-the-mood flow. Mood isn't part of the
    key here since it isn't known until Claude generates it."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM horoscopes
            WHERE sign = ? AND date = ? AND chaos_level = ? AND mood_source = 'llm'
            """,
            (sign, date, chaos_level),
        ).fetchone()
        return dict(row) if row else None


def increment_view_count(row_id: int) -> int:
    """Bumps view_count and returns the new value."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE horoscopes SET view_count = view_count + 1 WHERE id = ?",
            (row_id,),
        )
        new_count = conn.execute(
            "SELECT view_count FROM horoscopes WHERE id = ?", (row_id,)
        ).fetchone()["view_count"]
        return new_count


def insert_horoscope(
    sign: str,
    date: str,
    mood: str,
    mood_color: str,
    chaos_level: int,
    horoscope_text: str,
    mood_source: str = "user",
) -> dict:
    """Stores a freshly-generated horoscope with view_count starting at 1
    (the request that triggered generation counts as the first view)."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO horoscopes
                (sign, date, mood, mood_color, chaos_level, horoscope_text, view_count, mood_source)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (sign, date, mood, mood_color, chaos_level, horoscope_text, mood_source),
        )
        row = conn.execute(
            "SELECT * FROM horoscopes WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)