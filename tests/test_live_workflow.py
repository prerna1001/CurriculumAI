"""No-network checks for profile-aware live-workflow helpers."""

import unittest
from unittest.mock import patch

from backend.agents.workflow import (
    AgentWorkflowError,
    ResearchIdea,
    candidates_from_research,
    generate_outline,
    profile_instruction,
    research_query,
)
from backend.learning.profile import ProfileContext
from backend.storage.repository import Candidate


class LiveWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = ProfileContext(
            version=3,
            weights={"theory": 0.2, "project": 0.2, "case_study": 0.6},
            summary="Prefers case_study (0.60), then theory (0.20) and project (0.20).",
        )

    def test_profile_influences_research_prompt_and_query(self) -> None:
        instruction = profile_instruction(self.profile)
        query = research_query("Machine Learning", "undergraduate", self.profile)

        self.assertIn("snapshot v3", instruction)
        self.assertIn("case_study=0.60", instruction)
        self.assertIn("case study teaching activities", query)
        self.assertIn("undergraduate Machine Learning", query)

    def test_persisted_candidate_keeps_validated_evidence(self) -> None:
        idea = ResearchIdea(
            title="Fairness audit",
            description="Audit a model.",
            teaching_style="case_study",
            source_url="https://example.org/evidence",
            why_suggested="Matches preference.",
            evidence_text="Source evidence.",
        )
        candidate = candidates_from_research("sess_1", [idea])[0]

        self.assertEqual(candidate.id, "card_sess_1_1")
        self.assertEqual(candidate.source_url, idea.source_url)
        self.assertEqual(candidate.evidence_text, "Source evidence.")

    def test_writer_rejects_a_source_url_that_does_not_match_its_card(self) -> None:
        candidates = [
            Candidate("card_1", "One", "d", "theory", "https://example.org/one", "w", "e", 0),
            Candidate("card_2", "Two", "d", "project", "https://example.org/two", "w", "e", 1),
        ]
        invalid_output = {
            "title": "Module",
            "sessions": [
                {
                    "topic": "One",
                    "activity": "Do one.",
                    "learning_objective": "Learn one.",
                    "source_references": [{"source_id": "card_1", "url": "https://example.org/two"}],
                },
                {
                    "topic": "Two",
                    "activity": "Do two.",
                    "learning_objective": "Learn two.",
                    "source_references": [{"source_id": "card_2", "url": "https://example.org/two"}],
                },
            ],
        }
        with patch("backend.agents.workflow._crew_output", return_value=invalid_output):
            with self.assertRaises(AgentWorkflowError):
                generate_outline(candidates, self.profile)
