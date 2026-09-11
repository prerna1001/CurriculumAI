"""Evidence that the agent improved, computed from stored rows.

Nothing here is instrumented at request time — every number is reconstructed
from the selections and candidates already in the database, so turning this on
costs nothing and works retroactively on history already recorded.

The reconstruction relies on one property of the learning rule: preference
counts start at a fixed Laplace prior and only ever move by +1 per unique
selected card. So replaying the selections in order recovers the exact weights
in force at every past search, and re-ranking a session's stored candidates
with those weights reproduces the order the professor actually saw.
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter

from backend.learning.profile import preference_summary
from backend.storage.database import connect

router = APIRouter()

STYLES = ("theory", "case_study", "project")
TOP_K = 2


def _weights(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    return {style: counts[style] / total for style in counts} if total else dict.fromkeys(counts, 0.0)


def _ranked_ids(rows: list[Any], weights: dict[str, float]) -> list[str]:
    """Reproduce backend.learning.ranking.rank_candidates for stored rows."""
    return [
        row["id"]
        for row in sorted(
            rows,
            key=lambda row: (-weights.get(row["teaching_style"], 0.0), row["rank_order"]),
        )
    ]


def evaluate(database_path: str) -> dict[str, Any]:
    with connect(database_path) as connection:
        selections = connection.execute(
            """
            SELECT id, session_id, selected_card_ids_json, created_at
            FROM selection ORDER BY created_at, id
            """
        ).fetchall()
        candidates = connection.execute(
            "SELECT id, session_id, teaching_style, rank_order FROM candidate"
        ).fetchall()
        seeded = connection.execute(
            "SELECT value, count FROM preference_count WHERE dimension = 'teaching_style'"
        ).fetchall()

    by_session: dict[str, list[Any]] = {}
    for row in candidates:
        by_session.setdefault(row["session_id"], []).append(row)

    # The prior every profile starts from, not whatever the counts are now.
    counts = dict.fromkeys(STYLES, 1)
    points: list[dict[str, Any]] = [
        {
            "n": 0,
            "version": 0,
            "weights": _weights(counts),
            "top2_share": None,
            "mean_rank": None,
            "changed": None,
            "at": None,
        }
    ]
    unchanged = 0

    for index, selection in enumerate(selections, start=1):
        before = _weights(counts)
        rows = by_session.get(selection["session_id"], [])
        picked = set(json.loads(selection["selected_card_ids_json"]))

        top2_share: float | None = None
        mean_rank: float | None = None
        if rows and picked:
            order = _ranked_ids(rows, before)
            position = {card_id: rank for rank, card_id in enumerate(order, start=1)}
            ranks = [position[card_id] for card_id in picked if card_id in position]
            if ranks:
                top2_share = sum(1 for rank in ranks if rank <= TOP_K) / len(ranks)
                mean_rank = sum(ranks) / len(ranks)

        style_of = {row["id"]: row["teaching_style"] for row in rows}
        for card_id in picked:
            style = style_of.get(card_id)
            if style in counts:
                counts[style] += 1

        after = _weights(counts)
        changed = any(abs(after[s] - before[s]) > 1e-9 for s in STYLES)
        if not changed:
            unchanged += 1

        points.append(
            {
                "n": index,
                "version": index,
                "weights": after,
                "top2_share": top2_share,
                "mean_rank": mean_rank,
                "changed": changed,
                "at": selection["created_at"],
            }
        )

    # Reconciles the replay against what is actually stored; a mismatch means
    # something wrote counts outside commit_selection.
    stored = {row["value"]: row["count"] for row in seeded}
    consistent = all(stored.get(style) == counts[style] for style in STYLES) if stored else True

    scored = [p for p in points if p["top2_share"] is not None]
    first = scored[0]["top2_share"] if scored else None
    latest = scored[-1]["top2_share"] if scored else None

    return {
        "selections": len(selections),
        "profile_version": len(selections),
        "current_weights": _weights(counts),
        "preference_summary": preference_summary(_weights(counts)),
        "points": points,
        "top2_share_first": first,
        "top2_share_latest": latest,
        "top2_share_delta": None if first is None or latest is None else latest - first,
        "unchanged_selections": unchanged,
        "replay_consistent": consistent,
    }


@router.get("/api/evals")
def evals() -> dict[str, Any]:
    """Improvement evidence for the current demo professor."""
    return evaluate(os.getenv("CURRICULUMAI_DATABASE_PATH", "./data/curriculumai.db"))
