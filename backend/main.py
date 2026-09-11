"""HTTP entry point for the CurriculumAI backend."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import HealthResponse
from backend.storage.database import initialize_database


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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is available."""
    return HealthResponse(status="ok")
