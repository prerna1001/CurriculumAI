"""Deterministic profile-aware ranking for validated curriculum cards."""

from __future__ import annotations

from typing import Iterable, Protocol, TypeVar

from backend.learning.profile import ProfileContext


class RankableCandidate(Protocol):
    teaching_style: str
    rank_order: int


CandidateType = TypeVar("CandidateType", bound=RankableCandidate)


def rank_candidates(
    candidates: Iterable[CandidateType], profile: ProfileContext
) -> list[CandidateType]:
    """Order cards by saved style preference, preserving original order for ties."""
    return sorted(
        candidates,
        key=lambda candidate: (
            -profile.weights.get(candidate.teaching_style, 0.0),
            candidate.rank_order,
        ),
    )
