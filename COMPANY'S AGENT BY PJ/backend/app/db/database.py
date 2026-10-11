"""Tiny SQLite layer (stdlib only). Stores chat sessions, messages,
user feedback and ingested-document metadata."""
import sqlite3
import threading
from pathlib import Path

_DB_LOCK = threading.Lock()
_conn: sqlite3.Connection | None = None


def init_db(db_path: Path) -> None:
    global _conn
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            citations_json TEXT,
            trace_json TEXT,
            sources_json TEXT,
            demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL REFERENCES messages(id),
            rating INTEGER NOT NULL CHECK(rating IN (1,-1)),
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            pages INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    _conn.commit()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with _DB_LOCK:
        cur = _conn.execute(sql, params)
        rows = cur.fetchall()
        _conn.commit()
        return rows


def execute(sql: str, params: tuple = ()) -> None:
    with _DB_LOCK:
        _conn.execute(sql, params)
        _conn.commit()
