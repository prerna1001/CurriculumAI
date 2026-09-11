"""Durable application-state operations for CurriculumAI."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from backend.storage.database import connect


TEACHING_STYLES = ("theory", "case_study", "project")


class StorageError(Exception):
    """Base error for a storage operation."""


class SessionNotFound(StorageError):
    """Raised when a requested search session does not exist."""


class InvalidSelection(StorageError):
    """Raised when selected card IDs are empty or do not belong to a session."""


class SelectionAlreadyCommitted(StorageError):
    """Raised when a session already has a different committed selection."""


@dataclass(frozen=True)
class ProfileContext:
    version: int
    weights: dict[str, float]
    summary: str


@dataclass(frozen=True)
class Candidate:
    id: str
    title: str
    description: str
    teaching_style: str
    source_url: str
    why_suggested: str
    evidence_text: str
    rank_order: int


@dataclass(frozen=True)
class SelectionCommit:
    response: dict[str, Any]
    created: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise_card_ids(card_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(card_ids)))


def _summary(weights: dict[str, float]) -> str:
    ordered = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    if len({round(weight, 8) for _, weight in ordered}) == 1:
        return "Teaching-style preferences are currently balanced."
    formatted = ", then ".join(f"{style} ({weight:.2f})" for style, weight in ordered)
    return f"Prefers {formatted}."


def _profile_context(connection: sqlite3.Connection) -> ProfileContext:
    version_row = connection.execute("SELECT version FROM profile WHERE id = 1").fetchone()
    rows = connection.execute(
        "SELECT value, count FROM preference_count WHERE dimension = 'teaching_style'"
    ).fetchall()
    counts = {row["value"]: row["count"] for row in rows}
    total = sum(counts.values())
    weights = {
        style: (counts.get(style, 0) / total if total else 0.0)
        for style in TEACHING_STYLES
    }
    return ProfileContext(
        version=version_row["version"], weights=weights, summary=_summary(weights)
    )


class Repository:
    """Repository for all Person B-owned SQLite state."""

    def __init__(self, database_path: str):
        self.database_path = database_path

    def profile_context(self) -> ProfileContext:
        with connect(self.database_path) as connection:
            return _profile_context(connection)

    def create_session(
        self, subject: str, level: str, profile_version: int, session_id: str | None = None
    ) -> str:
        session_id = session_id or f"sess_{uuid.uuid4().hex}"
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO session (id, subject, level, profile_version_at_search, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, subject, level, profile_version, _utc_now()),
            )
        return session_id

    def save_candidates(self, session_id: str, candidates: Iterable[Candidate]) -> None:
        candidate_rows = list(candidates)
        with connect(self.database_path) as connection:
            if not connection.execute("SELECT 1 FROM session WHERE id = ?", (session_id,)).fetchone():
                raise SessionNotFound(session_id)
            connection.executemany(
                """
                INSERT INTO candidate (
                    id, session_id, rank_order, title, description, teaching_style,
                    source_url, why_suggested, evidence_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        candidate.id,
                        session_id,
                        candidate.rank_order,
                        candidate.title,
                        candidate.description,
                        candidate.teaching_style,
                        candidate.source_url,
                        candidate.why_suggested,
                        candidate.evidence_text,
                    )
                    for candidate in candidate_rows
                ],
            )

    def candidates_for_session(self, session_id: str) -> list[Candidate]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, rank_order, title, description, teaching_style, source_url,
                       why_suggested, evidence_text
                FROM candidate WHERE session_id = ? ORDER BY rank_order
                """,
                (session_id,),
            ).fetchall()
        return [
            Candidate(
                id=row["id"],
                rank_order=row["rank_order"],
                title=row["title"],
                description=row["description"],
                teaching_style=row["teaching_style"],
                source_url=row["source_url"],
                why_suggested=row["why_suggested"],
                evidence_text=row["evidence_text"],
            )
            for row in rows
        ]

    def cache_search(
        self, subject: str, level: str, profile_version: int, response: dict[str, Any]
    ) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO search_cache
                    (subject, level, profile_version, response_json)
                VALUES (?, ?, ?, ?)
                """,
                (subject, level, profile_version, json.dumps(response)),
            )

    def cached_search(
        self, subject: str, level: str, profile_version: int
    ) -> dict[str, Any] | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT response_json FROM search_cache
                WHERE subject = ? AND level = ? AND profile_version = ?
                """,
                (subject, level, profile_version),
            ).fetchone()
        return json.loads(row["response_json"]) if row else None

    def commit_selection(
        self, session_id: str, card_ids: Iterable[str], outline: dict[str, Any]
    ) -> SelectionCommit:
        """Atomically save a selection, preferences, immutable outline, and response."""
        normalised_ids = _normalise_card_ids(card_ids)
        if not normalised_ids:
            raise InvalidSelection("Select at least one topic.")

        connection = connect(self.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not connection.execute("SELECT 1 FROM session WHERE id = ?", (session_id,)).fetchone():
                raise SessionNotFound(session_id)

            existing = connection.execute(
                "SELECT selected_card_ids_json, response_json FROM selection WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if existing:
                if tuple(json.loads(existing["selected_card_ids_json"])) == normalised_ids:
                    connection.rollback()
                    return SelectionCommit(json.loads(existing["response_json"]), created=False)
                raise SelectionAlreadyCommitted(session_id)

            placeholders = ", ".join("?" for _ in normalised_ids)
            rows = connection.execute(
                f"""
                SELECT id, rank_order, teaching_style FROM candidate
                WHERE session_id = ? AND id IN ({placeholders})
                ORDER BY rank_order
                """,
                (session_id, *normalised_ids),
            ).fetchall()
            if len(rows) != len(normalised_ids):
                raise InvalidSelection("Every selected card must belong to the search session.")

            before = _profile_context(connection)
            for row in rows:
                connection.execute(
                    """
                    UPDATE preference_count SET count = count + 1
                    WHERE dimension = 'teaching_style' AND value = ?
                    """,
                    (row["teaching_style"],),
                )
            connection.execute("UPDATE profile SET version = version + 1 WHERE id = 1")
            after = _profile_context(connection)

            selected_styles = [row["teaching_style"] for row in rows]
            changed_style = max(
                selected_styles,
                key=lambda style: after.weights[style] - before.weights[style],
            )
            selection_id = f"sel_{uuid.uuid4().hex}"
            learned_change = (
                f"{changed_style} weight rose from {before.weights[changed_style]:.2f} "
                f"to {after.weights[changed_style]:.2f} after {len(rows)} "
                f"{changed_style.replace('_', '-')} selections."
            )
            response = {
                "selection_id": selection_id,
                "profile_version": after.version,
                "learned_change": learned_change,
                "preference_summary": after.summary,
                "outline": outline,
            }
            connection.execute(
                """
                INSERT INTO selection (
                    id, session_id, selected_card_ids_json, outline_json, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    selection_id,
                    session_id,
                    json.dumps(normalised_ids),
                    json.dumps(outline),
                    json.dumps(response),
                    _utc_now(),
                ),
            )
            connection.commit()
            return SelectionCommit(response, created=True)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def saved_outline(self, selection_id: str) -> dict[str, Any] | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT outline_json FROM selection WHERE id = ?", (selection_id,)
            ).fetchone()
        return json.loads(row["outline_json"]) if row else None

    def begin_publication(self, selection_id: str) -> dict[str, Any]:
        """Create one publication record or return its current saved state."""
        with connect(self.database_path) as connection:
            existing = connection.execute(
                """
                SELECT selection_id, status, external_id, external_url
                FROM publication WHERE selection_id = ?
                """,
                (selection_id,),
            ).fetchone()
            if existing:
                return dict(existing)
            if not connection.execute("SELECT 1 FROM selection WHERE id = ?", (selection_id,)).fetchone():
                raise InvalidSelection("The selection does not exist.")
            connection.execute(
                """
                INSERT INTO publication (selection_id, status, external_id, external_url, created_at)
                VALUES (?, 'publishing', NULL, NULL, ?)
                """,
                (selection_id, _utc_now()),
            )
        return {
            "selection_id": selection_id,
            "status": "publishing",
            "external_id": None,
            "external_url": None,
        }

    def finish_publication(
        self, selection_id: str, status: str, external_id: str | None = None, external_url: str | None = None
    ) -> dict[str, Any]:
        if status not in {"published", "failed"}:
            raise ValueError("Publication status must be published or failed.")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE publication
                SET status = ?, external_id = ?, external_url = ?
                WHERE selection_id = ?
                """,
                (status, external_id, external_url, selection_id),
            )
        return {
            "selection_id": selection_id,
            "status": status,
            "external_id": external_id,
            "external_url": external_url,
        }
