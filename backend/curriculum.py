"""Publish several approved modules as one curriculum.

A professor builds a course across several searches, so the deliverable is the
accumulated set, not the most recent module. This assembles the stored outlines
— never regenerating them — and sends the result as a single document.

Deliberately additive: the frozen POST /api/publish contract still means "one
selection", and this endpoint does not touch it. It also keeps no publication
row, because that table is keyed one-per-selection and a merged document has no
single owner; the UI guards against double-sends, consistent with the
reconciliation the build plan already cut.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.integrations.one_publish import publish_artifact
from backend.rendering import (
    ConfigurationError,
    PublishError,
    RenderError,
    render_outline,
)
from backend.storage.database import connect

router = APIRouter()


class CurriculumPublishRequest(BaseModel):
    selection_ids: list[str] = Field(min_length=1)


def _publish_live() -> bool:
    return os.getenv("CURRICULUMAI_PUBLISH_MODE", "reserve").lower() == "live"


def _error(status: int, code: str, message: str, retryable: bool) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "retryable": retryable}},
    )


def _publication_key(selection_ids: list[str]) -> str:
    digest = hashlib.sha256("|".join(selection_ids).encode()).hexdigest()[:24]
    return f"curriculum_{digest}"


def assemble(database_path: str, selection_ids: list[str]) -> dict[str, Any] | None:
    """Merge the stored outlines, in the order the professor approved them."""
    placeholders = ", ".join("?" for _ in selection_ids)
    with connect(database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT s.id, s.outline_json, sess.subject
            FROM selection s JOIN session sess ON sess.id = s.session_id
            WHERE s.id IN ({placeholders})
            """,
            tuple(selection_ids),
        ).fetchall()

    outlines = {row["id"]: (json.loads(row["outline_json"]), row["subject"]) for row in rows}
    if len(outlines) != len(set(selection_ids)):
        return None

    modules = []
    subjects: list[str] = []
    for selection_id in selection_ids:
        outline, subject = outlines[selection_id]
        modules.append(
            {
                "title": outline.get("title") or "Untitled module",
                "sessions": outline.get("sessions") or [],
            }
        )
        if subject and subject not in subjects:
            subjects.append(subject)

    if len(modules) == 1:
        title = modules[0]["title"]
    elif len(subjects) == 1:
        title = f"{subjects[0]} — course outline"
    else:
        title = " · ".join(subjects) if subjects else "Course outline"

    return {"title": title, "modules": modules}


@router.post("/api/publish-curriculum")
def publish_curriculum(request: CurriculumPublishRequest) -> JSONResponse:
    """Render every approved module into one artifact and deliver it."""
    # Order matters and duplicates do not: preserve first appearance.
    selection_ids = list(dict.fromkeys(request.selection_ids))
    database_path = os.getenv("CURRICULUMAI_DATABASE_PATH", "./data/curriculumai.db")

    curriculum = assemble(database_path, selection_ids)
    if curriculum is None:
        return _error(404, "selection_not_found", "An approved module no longer exists.", False)

    sessions = sum(len(module["sessions"]) for module in curriculum["modules"])
    key = _publication_key(selection_ids)

    if not _publish_live():
        return JSONResponse(
            status_code=202,
            content={
                "status": "publishing",
                "external_id": None,
                "external_url": None,
                "modules": len(curriculum["modules"]),
                "sessions": sessions,
            },
        )

    try:
        artifact = render_outline(key, curriculum)
        receipt = publish_artifact(key, artifact)
    except (RenderError, PublishError, ConfigurationError) as error:
        return JSONResponse(
            status_code=502,
            content={
                "status": "failed",
                "external_id": None,
                "external_url": None,
                "modules": len(curriculum["modules"]),
                "sessions": sessions,
                "error": {
                    "code": "publication_failed",
                    "message": str(error),
                    "retryable": True,
                },
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "published",
            "external_id": receipt.external_id,
            "external_url": receipt.external_url,
            "modules": len(curriculum["modules"]),
            "sessions": sessions,
        },
    )
