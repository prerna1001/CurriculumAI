"""Focused tests for the durable learning state."""

import tempfile
import unittest
from pathlib import Path

from backend.storage.database import initialize_database
from backend.storage.repository import (
    Candidate,
    Repository,
    SelectionAlreadyCommitted,
)


OUTLINE = {
    "title": "Case-study module",
    "sessions": [
        {
            "topic": "Hiring-model fairness audit",
            "activity": "Audit a model.",
            "learning_objective": "Evaluate unfair outcomes.",
            "source_references": [
                {"source_id": "card_3", "url": "https://example.org/hiring"}
            ],
        }
    ],
}


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "test.db")
        initialize_database(self.database_path)
        self.repository = Repository(self.database_path)
        self.repository.create_session("Machine Learning", "undergraduate", 0, "sess_1")
        self.repository.save_candidates(
            "sess_1",
            [
                Candidate("card_1", "Theory", "d", "theory", "https://example.org/t", "w", "e", 0),
                Candidate("card_2", "Project", "d", "project", "https://example.org/p", "w", "e", 1),
                Candidate("card_3", "Case one", "d", "case_study", "https://example.org/c1", "w", "e", 2),
                Candidate("card_4", "Case two", "d", "case_study", "https://example.org/c2", "w", "e", 3),
            ],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_selection_updates_preference_once_and_replays(self) -> None:
        first = self.repository.commit_selection("sess_1", ["card_4", "card_3", "card_3"], OUTLINE)
        replay = self.repository.commit_selection("sess_1", ["card_3", "card_4"], OUTLINE)

        self.assertTrue(first.created)
        self.assertFalse(replay.created)
        self.assertEqual(first.response, replay.response)
        profile = self.repository.profile_context()
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.weights["case_study"], 0.6)

    def test_different_selection_for_same_session_is_rejected(self) -> None:
        self.repository.commit_selection("sess_1", ["card_3"], OUTLINE)

        with self.assertRaises(SelectionAlreadyCommitted):
            self.repository.commit_selection("sess_1", ["card_4"], OUTLINE)


if __name__ == "__main__":
    unittest.main()
