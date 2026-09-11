"""Development-only evidence-supported fixture cards."""

from __future__ import annotations

from backend.storage.repository import Candidate


def fixture_candidates(session_id: str) -> list[Candidate]:
    """Return four fixed examples with per-session database IDs."""
    raw_cards = [
        (
            "Bias-variance tradeoff through model diagnostics",
            "Students derive the bias-variance tradeoff and interpret diagnostic plots for a supervised learning model.",
            "theory",
            "https://example.org/evidence/bias-variance",
            "Provides a rigorous conceptual foundation for introductory machine learning.",
        ),
        (
            "Build and evaluate a campus-energy predictor",
            "Students build a small regression model for campus energy use and compare evaluation metrics.",
            "project",
            "https://example.org/evidence/energy-predictor",
            "Connects model evaluation to a concrete, end-to-end project.",
        ),
        (
            "Hiring-model fairness audit",
            "Students audit a hiring-model case, identify disparate outcomes, and recommend mitigations.",
            "case_study",
            "https://example.org/evidence/hiring-audit",
            "Uses a realistic decision-making case to examine model impact.",
        ),
        (
            "Clinical-risk model deployment review",
            "Students review a clinical-risk model case and decide whether evidence supports deployment.",
            "case_study",
            "https://example.org/evidence/clinical-risk",
            "Applies machine-learning evaluation to a high-stakes deployment decision.",
        ),
    ]
    return [
        Candidate(
            id=f"card_{session_id}_{index + 1}",
            title=title,
            description=description,
            teaching_style=style,
            source_url=source_url,
            why_suggested=why_suggested,
            evidence_text=f"Fixture evidence for {title}.",
            rank_order=index,
        )
        for index, (title, description, style, source_url, why_suggested) in enumerate(raw_cards)
    ]
