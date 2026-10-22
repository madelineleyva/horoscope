"""
SQLite cache layer.

Cache key = (sign, date, chaos_level, requested_mood)

`requested_mood` is what the *caller asked for*: a real mood when the user
picked one (classic page), or the sentinel AUTO_MOOD when they let Claude
choose (Win98 page). It is deliberately separate from `mood`, which is what
actually got stored and displayed. For an auto request, `mood` is whatever
Claude picked, so two different requests can legitimately end up showing
the same mood without ever fighting over the same cache slot.

(The first version of this schema keyed the cache on `mood` itself, which
meant an auto request that happened to pick "happy" collided with a user
request for "happy" and crashed with an IntegrityError *after* the paid
LLM call. See tests/test_database.py::test_user_and_auto_requests_can_share_a_displayed_mood.)
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "horoscopes.db"

# Not a member of models.Mood, so it can never collide with a real mood.
AUTO_MOOD = "auto"

# Stored in SQLite's built-in PRAGMA user_version.
SCHEMA_VERSION = 2

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS horoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sign TEXT NOT NULL,
    date TEXT NOT NULL,
    chaos_level INTEGER NOT NULL,
    requested_mood TEXT NOT NULL,
    mood TEXT NOT NULL,
    mood_color TEXT NOT NULL,
    horoscope_text TEXT NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(sign, date, chaos_level, requested_mood)
);
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


def _migrate_legacy_table(conn: sqlite3.Connection) -> None:
    """Upgrades a pre-v2 `horoscopes` table in place, keeping every row.

    Two legacy shapes exist in the wild: v0 (no mood_source column) and v1
    (mood_source 'user' | 'llm'). In both, rows from the old user-mood flow
    keep their mood as the requested_mood, and v1's 'llm' rows become AUTO.

    SQLite can't change a UNIQUE constraint with ALTER TABLE, so this
    rebuilds the table. It all runs in one transaction, so a crash midway
    leaves the old table untouched.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(horoscopes)")}
    if "mood_source" in columns:
        requested = f"CASE WHEN mood_source = 'llm' THEN '{AUTO_MOOD}' ELSE mood END"
    else:
        requested = "mood"

    conn.executescript(
        f"""
        BEGIN;
        ALTER TABLE horoscopes RENAME TO horoscopes_legacy;
        {CREATE_TABLE_SQL}
        INSERT INTO horoscopes
            (id, sign, date, chaos_level, requested_mood, mood, mood_color,
             horoscope_text, view_count, created_at)
        SELECT id, sign, date, chaos_level, {requested}, mood, mood_color,
               horoscope_text, view_count, created_at
        FROM horoscopes_legacy;
        DROP TABLE horoscopes_legacy;
        PRAGMA user_version = {SCHEMA_VERSION};
        COMMIT;
        """
    )


def init_db() -> None:
    """Creates the schema, or migrates an older one. Safe to call repeatedly."""
    with get_conn() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return

        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'horoscopes'"
        ).fetchone()

        if table_exists:
            _migrate_legacy_table(conn)
        else:
            conn.executescript(CREATE_TABLE_SQL + f"PRAGMA user_version = {SCHEMA_VERSION};")


def get_cached(sign: str, date: str, chaos_level: int, requested_mood: str | None = None):
    """Look up today's row for this request. Pass requested_mood=None for
    the LLM-picks-the-mood flow. Returns None on a miss."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM horoscopes
            WHERE sign = ? AND date = ? AND chaos_level = ? AND requested_mood = ?
            """,
            (sign, date, chaos_level, requested_mood or AUTO_MOOD),
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
    chaos_level: int,
    requested_mood: str | None,
    mood: str,
    mood_color: str,
    horoscope_text: str,
) -> tuple[dict, bool]:
    """Stores a freshly-generated horoscope with view_count starting at 1
    (the request that triggered generation counts as the first view).

    Returns (row, created). If another request stored the same cache key
    while we were waiting on the LLM, nothing is overwritten and you get
    that existing row back with created=False, so the caller can serve it
    as a cache hit instead of crashing on a UNIQUE violation.
    """
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO horoscopes
                (sign, date, chaos_level, requested_mood, mood, mood_color,
                 horoscope_text, view_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                sign,
                date,
                chaos_level,
                requested_mood or AUTO_MOOD,
                mood,
                mood_color,
                horoscope_text,
            ),
        )
        created = cursor.rowcount == 1
        row = conn.execute(
            """
            SELECT * FROM horoscopes
            WHERE sign = ? AND date = ? AND chaos_level = ? AND requested_mood = ?
            """,
            (sign, date, chaos_level, requested_mood or AUTO_MOOD),
        ).fetchone()
        return dict(row), created
