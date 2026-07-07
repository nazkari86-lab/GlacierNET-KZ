import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from app.config import HISTORY_DB_PATH

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    model_name TEXT NOT NULL,
    image_path TEXT,
    mask_path TEXT,
    overlay_path TEXT,
    area_km2 REAL,
    year INTEGER,
    created_at TEXT NOT NULL,
    thumbnail_path TEXT,
    status TEXT NOT NULL DEFAULT 'completed'
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


def save_result(
    task_id: str,
    model_name: str,
    image_path: Optional[str] = None,
    mask_path: Optional[str] = None,
    overlay_path: Optional[str] = None,
    area_km2: Optional[float] = None,
    year: Optional[int] = None,
    thumbnail_path: Optional[str] = None,
):
    with _get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO history
               (task_id, model_name, image_path, mask_path, overlay_path, area_km2, year, created_at, thumbnail_path, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                model_name,
                image_path,
                mask_path,
                overlay_path,
                area_km2,
                year,
                datetime.now(timezone.utc).isoformat(),
                thumbnail_path,
                "completed",
            ),
        )


def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    with _get_db() as conn:
        rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return [dict(r) for r in rows]


def get_result(task_id: str) -> Optional[dict]:
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM history WHERE task_id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def delete_result(task_id: str) -> bool:
    with _get_db() as conn:
        cur = conn.execute("DELETE FROM history WHERE task_id = ?", (task_id,))
        deleted = cur.rowcount > 0
    return deleted
