"""
Lightweight SQLite storage - no ORM needed for this scope, just stdlib
sqlite3. Stores document metadata + a pointer to the JSON result file
on disk (data/results/<document_id>.json).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from app.core.config import DB_PATH, RESULTS_DIR


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_document_record(document_id: str, filename: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO documents (document_id, filename, status) VALUES (?, ?, ?)",
            (document_id, filename, "processing"),
        )


def update_document_status(document_id: str, status: str, error: Optional[str] = None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET status = ?, error = ? WHERE document_id = ?",
            (status, error, document_id),
        )


def get_document_record(document_id: str) -> Optional[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        return dict(row) if row else None


def save_result_json(document_id: str, result: dict) -> Path:
    path = RESULTS_DIR / f"{document_id}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path


def load_result_json(document_id: str) -> Optional[dict]:
    path = RESULTS_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
