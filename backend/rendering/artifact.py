"""Shared types across the A/B adapter boundary.

The build plan assigns these to B ("B defines their shared types; A implements
the adapters"). They live here so A's stubs are importable from the contract
commit onward; B may relocate them into `backend/schemas.py` as long as the
field names survive.

`Artifact` deliberately carries EITHER raw bytes OR a structured payload. One is
a passthrough, so the destination platform's own API decides which one is
required, and that is not known until the phase-1 readiness gate fills in
`contracts/one_action.md`. Narrowing this to bytes before then would break the
contract freeze the moment the destination turns out to want structured content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RenderError(RuntimeError):
    """Rendering failed. Nothing external happened; safe to retry."""


class PublishError(RuntimeError):
    """The destination rejected the artifact, or the receipt was unreadable."""


class ConfigurationError(RuntimeError):
    """A required environment variable or contract value is missing."""


@dataclass(frozen=True)
class Artifact:
    title: str
    content_type: str
    content_bytes: bytes | None = None
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if (self.content_bytes is None) == (self.payload is None):
            raise ValueError("Artifact needs exactly one of content_bytes or payload")

    @property
    def size(self) -> int:
        return len(self.content_bytes) if self.content_bytes is not None else 0


@dataclass(frozen=True)
class Receipt:
    external_id: str
    external_url: str
    raw: dict[str, Any] = field(default_factory=dict)
