"""HTTP entry point for the CurriculumAI backend."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.fixtures import fixture_candidates
from backend.learning.ranking import rank_candidates
from backend.schemas import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PublicationResponse,
    PublishRequest,
    SearchRequest,
    SearchResponse,
    SelectRequest,
    SelectResponse,
)
from backend.storage.database import initialize_database
from backend.storage.repository import (
    InvalidSelection,
    Repository,
    SelectionAlreadyCommitted,
    SessionNotFound,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(os.getenv("CURRICULUMAI_DATABASE_PATH", "./data/curriculumai.db"))
    yield


app = FastAPI(title="CurriculumAI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def repository() -> Repository:
    return Repository(os.getenv("CURRICULUMAI_DATABASE_PATH", "./data/curriculumai.db"))


def error_response(status_code: int, code: str, message: str, retryable: bool) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, retryable=retryable))
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def invalid_input_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return error_response(422, "invalid_input", "Request fields are missing or invalid.", False)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is available."""
    return HealthResponse(status="ok")


@app.post("/api/search", response_model=SearchResponse, responses={422: {"model": ErrorResponse}})
def search(request: SearchRequest) -> SearchResponse:
    """Return four fixture cards ranked using one saved profile snapshot."""
    store = repository()
    profile = store.profile_context()
    session_id = store.create_session(request.subject, request.level, profile.version)
    candidates = fixture_candidates(session_id)
    store.save_candidates(session_id, candidates)
    ranked = rank_candidates(candidates, profile)
    response: dict[str, Any] = {
        "session_id": session_id,
        "profile_version": profile.version,
        "preference_summary": profile.summary,
        "cards": [
            {
                "id": candidate.id,
                "title": candidate.title,
                "description": candidate.description,
                "teaching_style": candidate.teaching_style,
                "source_url": candidate.source_url,
                "why_suggested": candidate.why_suggested,
            }
            for candidate in ranked
        ],
    }
    store.cache_search(request.subject, request.level, profile.version, response)
    return SearchResponse.model_validate(response)


def outline_for_selection(session_id: str, card_ids: list[str]) -> dict[str, Any]:
    """Create a deterministic cited outline until the live writer agent replaces it."""
    requested_ids = set(card_ids)
    candidates = [
        candidate
        for candidate in repository().candidates_for_session(session_id)
        if candidate.id in requested_ids
    ]
    if len(candidates) != len(requested_ids):
        raise InvalidSelection("Every selected card must belong to the search session.")
    return {
        "title": "CurriculumAI topic module",
        "sessions": [
            {
                "topic": candidate.title,
                "activity": candidate.description,
                "learning_objective": f"Evaluate the key ideas in {candidate.title}.",
                "source_references": [{"source_id": candidate.id, "url": candidate.source_url}],
            }
            for candidate in candidates
        ],
    }


@app.post(
    "/api/select",
    response_model=SelectResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def select(request: SelectRequest) -> SelectResponse | JSONResponse:
    """Commit one topic selection and its immutable, cited fixture outline."""
    try:
        outline = outline_for_selection(request.session_id, request.card_ids)
        commit = repository().commit_selection(request.session_id, request.card_ids, outline)
        return SelectResponse.model_validate(commit.response)
    except SessionNotFound:
        return error_response(404, "session_not_found", "The search session does not exist.", False)
    except InvalidSelection as error:
        return error_response(422, "invalid_selection", str(error), False)
    except SelectionAlreadyCommitted:
        return error_response(
            409,
            "selection_already_committed",
            "This search session already has a different committed selection.",
            False,
        )


@app.post(
    "/api/publish",
    response_model=PublicationResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    status_code=202,
)
def publish(request: PublishRequest) -> PublicationResponse | JSONResponse:
    """Reserve one publication record; Person A's adapter is integrated in phase 4b."""
    try:
        publication = repository().begin_publication(request.selection_id)
    except InvalidSelection:
        return error_response(404, "selection_not_found", "The selection does not exist.", False)

    status_code = 200 if publication["status"] in {"published", "failed"} else 202
    if status_code == 200:
        return JSONResponse(status_code=status_code, content=publication)
    return PublicationResponse.model_validate(publication)
