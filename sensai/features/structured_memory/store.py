import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_fact(conn: sqlite3.Connection, key: str, value: str) -> None:
    now = _now()
    conn.execute(
        "INSERT INTO facts (key, value, created_at, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, now, now),
    )
    conn.commit()


def get_fact(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def list_facts(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM facts ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def delete_fact(conn: sqlite3.Connection, key: str) -> bool:
    cur = conn.execute("DELETE FROM facts WHERE key = ?", (key,))
    conn.commit()
    return cur.rowcount > 0
