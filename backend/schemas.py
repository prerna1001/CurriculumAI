"""Pydantic schemas shared by CurriculumAI API routes."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SearchRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    level: str = Field(min_length=1, max_length=100)


class TopicCard(BaseModel):
    id: str
    title: str
    description: str
    teaching_style: Literal["theory", "case_study", "project"]
    source_url: HttpUrl
    why_suggested: str


class SearchResponse(BaseModel):
    session_id: str
    profile_version: int = Field(ge=0)
    preference_summary: str
    cards: list[TopicCard] = Field(min_length=4, max_length=4)


class SelectRequest(BaseModel):
    session_id: str = Field(min_length=1)
    card_ids: list[str] = Field(min_length=1)


class SourceReference(BaseModel):
    source_id: str
    url: HttpUrl


class OutlineSession(BaseModel):
    topic: str
    activity: str
    learning_objective: str
    source_references: list[SourceReference] = Field(min_length=1)


class Outline(BaseModel):
    title: str
    sessions: list[OutlineSession] = Field(min_length=1)


class SelectResponse(BaseModel):
    selection_id: str
    profile_version: int = Field(ge=0)
    learned_change: str
    preference_summary: str
    outline: Outline


class PublishRequest(BaseModel):
    selection_id: str = Field(min_length=1)


class PublicationResponse(BaseModel):
    selection_id: str
    status: Literal["publishing", "published", "failed"]
    external_id: Optional[str] = None
    external_url: Optional[HttpUrl] = None
