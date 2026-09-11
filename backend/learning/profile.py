"""Teaching-style preference representation and factual learning messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ProfileContext:
    """A single, immutable preference snapshot for one agent workflow."""

    version: int
    weights: dict[str, float]
    summary: str


def preference_summary(weights: dict[str, float]) -> str:
    """Build a displayable summary from saved counts without an LLM call."""
    ordered = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    if len({round(weight, 8) for _, weight in ordered}) == 1:
        return "Teaching-style preferences are currently balanced."
    formatted = ", then ".join(f"{style} ({weight:.2f})" for style, weight in ordered)
    return f"Prefers {formatted}."


def learned_change(
    before: ProfileContext, after: ProfileContext, selected_styles: Iterable[str]
) -> str:
    """Describe the recorded preference effect honestly and deterministically."""
    style_counts: dict[str, int] = {}
    for style in selected_styles:
        style_counts[style] = style_counts.get(style, 0) + 1
    if not style_counts:
        return "No teaching-style preference changed."

    changed_style = max(
        style_counts,
        key=lambda style: (after.weights[style] - before.weights[style], style_counts[style]),
    )
    increase = after.weights[changed_style] - before.weights[changed_style]
    if increase <= 0:
        return "Selected topics kept teaching-style preferences balanced."

    count = style_counts[changed_style]
    selection_word = "selection" if count == 1 else "selections"
    return (
        f"{changed_style} weight rose from {before.weights[changed_style]:.2f} "
        f"to {after.weights[changed_style]:.2f} after {count} "
        f"{changed_style.replace('_', '-')} {selection_word}."
    )
