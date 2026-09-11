"""Database initialization and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS preference_count (
    dimension TEXT NOT NULL,
    value TEXT NOT NULL,
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (dimension, value)
);

CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    level TEXT NOT NULL,
    profile_version_at_search INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(id),
    rank_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    teaching_style TEXT NOT NULL,
    source_url TEXT NOT NULL,
    why_suggested TEXT NOT NULL,
    evidence_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES session(id),
    selected_card_ids_json TEXT NOT NULL DEFAULT '[]',
    outline_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publication (
    selection_id TEXT PRIMARY KEY REFERENCES selection(id),
    status TEXT NOT NULL CHECK (status IN ('publishing', 'published', 'failed')),
    external_id TEXT,
    external_url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_cache (
    subject TEXT NOT NULL,
    level TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    response_json TEXT NOT NULL,
    PRIMARY KEY (subject, level, profile_version)
);
"""

SEED_COUNTS = (
    ("teaching_style", "theory", 1),
    ("teaching_style", "case_study", 1),
    ("teaching_style", "project", 1),
)


def connect(database_path: str) -> sqlite3.Connection:
    """Open one SQLite connection configured for short concurrent operations."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database(database_path: str) -> None:
    """Create the schema and seed the singleton profile exactly once."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA)
        selection_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(selection)")
        }
        if "selected_card_ids_json" not in selection_columns:
            connection.execute(
                "ALTER TABLE selection ADD COLUMN selected_card_ids_json "
                "TEXT NOT NULL DEFAULT '[]'"
            )
        connection.execute("INSERT OR IGNORE INTO profile (id, version) VALUES (1, 0)")
        connection.executemany(
            """
            INSERT OR IGNORE INTO preference_count (dimension, value, count)
            VALUES (?, ?, ?)
            """,
            SEED_COUNTS,
        )
