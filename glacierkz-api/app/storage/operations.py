"""SQLite Operations Registry with an append-only cryptographic audit chain."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import OPERATIONS_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS basins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_tier TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    basin_id TEXT NOT NULL REFERENCES basins(id),
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    status TEXT NOT NULL,
    evidence_tier TEXT NOT NULL,
    model_version TEXT,
    data_version TEXT,
    allowed_use TEXT NOT NULL,
    forbidden_use TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    observation_type TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    values_json TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    uncertainty REAL NOT NULL,
    artifact_sha256 TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_candidates (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    observation_id TEXT REFERENCES observations(id),
    change_type TEXT NOT NULL,
    magnitude REAL NOT NULL,
    uncertainty REAL NOT NULL,
    data_quality_gap REAL NOT NULL,
    model_disagreement REAL NOT NULL,
    expected_information_gain REAL NOT NULL,
    domain_shift_status TEXT NOT NULL,
    priority_score REAL NOT NULL,
    next_action TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_tier TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inspection_tasks (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    candidate_id TEXT REFERENCES change_candidates(id),
    action_type TEXT NOT NULL,
    priority_score REAL NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL,
    assigned_to TEXT,
    due_at TEXT,
    offline_package_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS field_reports (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES inspection_tasks(id),
    asset_id TEXT NOT NULL REFERENCES assets(id),
    observer TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    measurements_json TEXT NOT NULL,
    checklist_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    attachment_manifest_json TEXT NOT NULL,
    signature TEXT NOT NULL,
    sync_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_cases (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    limitations TEXT NOT NULL,
    allowed_use TEXT NOT NULL,
    forbidden_use TEXT NOT NULL,
    reviewer TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    evidence_case_id TEXT NOT NULL REFERENCES evidence_cases(id),
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    outcome TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    previous_event_sha256 TEXT,
    event_sha256 TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_basin ON assets(basin_id);
CREATE INDEX IF NOT EXISTS idx_observations_asset ON observations(asset_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_candidates_priority
    ON change_candidates(status, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_priority
    ON inspection_tasks(status, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_cases_asset
    ON evidence_cases(asset_id, updated_at DESC);
"""

TABLE_ORDER = {
    "basins": "created_at DESC",
    "assets": "updated_at DESC",
    "observations": "observed_at DESC",
    "change_candidates": "priority_score DESC, detected_at DESC",
    "inspection_tasks": "priority_score DESC, created_at DESC",
    "field_reports": "observed_at DESC",
    "evidence_cases": "updated_at DESC",
    "decisions": "decided_at DESC",
    "audit_events": "sequence DESC",
}
MUTABLE_TABLES = set(TABLE_ORDER) - {"audit_events"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def database(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or OPERATIONS_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.executescript(SCHEMA)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_audit(
    connection: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    payload: Any,
) -> dict[str, Any]:
    created_at = utc_now()
    payload_sha256 = hashlib.sha256(_canonical(payload).encode()).hexdigest()
    previous = connection.execute("SELECT event_sha256 FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
    previous_hash = previous["event_sha256"] if previous else None
    event = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "actor": actor,
        "payload_sha256": payload_sha256,
        "previous_event_sha256": previous_hash,
        "created_at": created_at,
    }
    event_hash = hashlib.sha256(_canonical(event).encode()).hexdigest()
    connection.execute(
        """
        INSERT INTO audit_events
        (entity_type, entity_id, action, actor, payload_sha256,
         previous_event_sha256, event_sha256, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_type,
            entity_id,
            action,
            actor,
            payload_sha256,
            previous_hash,
            event_hash,
            created_at,
        ),
    )
    result = dict(event)
    result["event_sha256"] = event_hash
    return result


def insert_record(
    connection: sqlite3.Connection,
    table: str,
    record: dict[str, Any],
    *,
    actor: str,
) -> dict[str, Any]:
    if table not in MUTABLE_TABLES:
        raise ValueError(f"Unsupported operations table: {table}")
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    # Safe dynamic identifiers: table is allowlisted and columns come from typed records.
    connection.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",  # nosec B608
        [record[column] for column in columns],
    )
    append_audit(
        connection,
        entity_type=table,
        entity_id=str(record["id"]),
        action="created",
        actor=actor,
        payload=record,
    )
    return record


def row_by_id(
    connection: sqlite3.Connection,
    table: str,
    record_id: str,
) -> dict[str, Any] | None:
    if table not in MUTABLE_TABLES:
        raise ValueError(f"Unsupported operations table: {table}")
    # Safe dynamic identifier: table is allowlisted above.
    row = connection.execute(
        f"SELECT * FROM {table} WHERE id = ?",  # nosec B608
        (record_id,),
    ).fetchone()
    return dict(row) if row else None


def list_rows(
    connection: sqlite3.Connection,
    table: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if table not in TABLE_ORDER:
        raise ValueError(f"Unsupported operations table: {table}")
    order_by = TABLE_ORDER[table]
    # Safe dynamic identifiers: table and ordering come from TABLE_ORDER.
    rows = connection.execute(
        f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?",  # nosec B608
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def update_task(
    connection: sqlite3.Connection,
    task_id: str,
    *,
    status: str,
    assigned_to: str | None,
    actor: str,
) -> dict[str, Any] | None:
    updated_at = utc_now()
    cursor = connection.execute(
        """
        UPDATE inspection_tasks
        SET status = ?, assigned_to = COALESCE(?, assigned_to), updated_at = ?
        WHERE id = ?
        """,
        (status, assigned_to, updated_at, task_id),
    )
    if not cursor.rowcount:
        return None
    record = row_by_id(connection, "inspection_tasks", task_id)
    append_audit(
        connection,
        entity_type="inspection_tasks",
        entity_id=task_id,
        action="status_updated",
        actor=actor,
        payload=record,
    )
    return record


def verify_audit_chain(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
    previous: str | None = None
    for row in rows:
        item = dict(row)
        event = {
            "entity_type": item["entity_type"],
            "entity_id": item["entity_id"],
            "action": item["action"],
            "actor": item["actor"],
            "payload_sha256": item["payload_sha256"],
            "previous_event_sha256": item["previous_event_sha256"],
            "created_at": item["created_at"],
        }
        expected = hashlib.sha256(_canonical(event).encode()).hexdigest()
        if item["previous_event_sha256"] != previous or item["event_sha256"] != expected:
            return {
                "valid": False,
                "events": len(rows),
                "failed_sequence": item["sequence"],
            }
        previous = item["event_sha256"]
    return {"valid": True, "events": len(rows), "head_sha256": previous}


def overview(connection: sqlite3.Connection) -> dict[str, Any]:
    counts = {}
    for table in (
        "basins",
        "assets",
        "observations",
        "change_candidates",
        "inspection_tasks",
        "field_reports",
        "evidence_cases",
        "decisions",
    ):
        # Safe dynamic identifier: table comes only from the fixed tuple above.
        query = f"SELECT COUNT(*) FROM {table}"  # nosec B608
        counts[table] = connection.execute(query).fetchone()[0]
    return {
        "counts": counts,
        "observation_queue": list_rows(connection, "change_candidates", limit=50),
        "inspection_tasks": list_rows(connection, "inspection_tasks", limit=50),
        "assets": list_rows(connection, "assets", limit=100),
        "observations": list_rows(connection, "observations", limit=100),
        "field_reports": list_rows(connection, "field_reports", limit=50),
        "evidence_cases": list_rows(connection, "evidence_cases", limit=50),
        "decisions": list_rows(connection, "decisions", limit=50),
        "audit_events": list_rows(connection, "audit_events", limit=100),
        "audit_chain": verify_audit_chain(connection),
        "safety_statement": (
            "Priorities select the next observation; they are not hazard probabilities or official warnings."
        ),
    }
