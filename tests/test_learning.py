"""Deterministic tests for the visible learning behavior."""

import unittest

from backend.learning.profile import ProfileContext, learned_change
from backend.learning.ranking import rank_candidates
from backend.storage.repository import Candidate


def card(card_id: str, style: str, rank_order: int) -> Candidate:
    return Candidate(
        id=card_id,
        title=card_id,
        description="description",
        teaching_style=style,
        source_url="https://example.org/evidence",
        why_suggested="reason",
        evidence_text="evidence",
        rank_order=rank_order,
    )


class LearningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cards = [
            card("card_1", "theory", 0),
            card("card_2", "project", 1),
            card("card_3", "case_study", 2),
            card("card_4", "case_study", 3),
        ]

    def test_skewed_case_study_profile_changes_rank(self) -> None:
        before = ProfileContext(0, {"theory": 1 / 3, "project": 1 / 3, "case_study": 1 / 3}, "balanced")
        after = ProfileContext(1, {"theory": 0.2, "project": 0.2, "case_study": 0.6}, "case studies")

        self.assertEqual(
            [candidate.id for candidate in rank_candidates(self.cards, before)],
            ["card_1", "card_2", "card_3", "card_4"],
        )
        self.assertEqual(
            [candidate.id for candidate in rank_candidates(self.cards, after)],
            ["card_3", "card_4", "card_1", "card_2"],
        )
        self.assertEqual(
            learned_change(before, after, ["case_study", "case_study"]),
            "case_study weight rose from 0.33 to 0.60 after 2 case-study selections.",
        )

    def test_balanced_selection_reports_no_visible_shift(self) -> None:
        before = ProfileContext(0, {"theory": 1 / 3, "project": 1 / 3, "case_study": 1 / 3}, "balanced")
        after = ProfileContext(1, {"theory": 1 / 3, "project": 1 / 3, "case_study": 1 / 3}, "balanced")

        self.assertEqual(
            [candidate.id for candidate in rank_candidates(self.cards, after)],
            ["card_1", "card_2", "card_3", "card_4"],
        )
        self.assertEqual(
            learned_change(before, after, ["theory", "project", "case_study"]),
            "Selected topics kept teaching-style preferences balanced.",
        )
