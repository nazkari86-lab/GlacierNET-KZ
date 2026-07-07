import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import HISTORY_DB_PATH

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    mode TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    response TEXT NOT NULL,
    fallback_used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def _get_db():
    conn = sqlite3.connect(str(HISTORY_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(_INIT_SQL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_analysis(
    prompt: str,
    mode: str,
    provider: str,
    model: str,
    response: str,
    fallback_used: bool = False,
):
    with _get_db() as conn:
        conn.execute(
            """INSERT INTO analysis_history
               (prompt, mode, provider, model, response, fallback_used, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (prompt, mode, provider, model, response, int(fallback_used), datetime.now(timezone.utc).isoformat()),
        )


def get_analysis_history(limit: int = 20, offset: int = 0) -> list[dict]:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_history ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]
