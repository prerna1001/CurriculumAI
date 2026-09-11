"""Pydantic schemas shared by CurriculumAI API routes."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
