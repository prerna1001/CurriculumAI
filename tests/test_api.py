"""Fixture-mode API contract checks."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = str(Path(self.temp_dir.name) / "api-test.db")
        self.environment = patch.dict(
            os.environ,
            {
                "CURRICULUMAI_DATABASE_PATH": database_path,
                "FRONTEND_ORIGIN": "http://localhost:3000",
            },
        )
        self.environment.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        if self.client_context is not None:
            self.client_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_learning_loop_uses_a_saved_profile(self) -> None:
        first_search = self.client.post(
            "/api/search",
            json={"subject": "Introduction to Machine Learning", "level": "undergraduate"},
        )
        self.assertEqual(first_search.status_code, 200)
        first_payload = first_search.json()
        self.assertEqual(first_payload["profile_version"], 0)
        self.assertEqual(len(first_payload["cards"]), 4)

        case_study_ids = [
            card["id"]
            for card in first_payload["cards"]
            if card["teaching_style"] == "case_study"
        ]
        selection_request = {
            "session_id": first_payload["session_id"],
            "card_ids": case_study_ids,
        }
        selected = self.client.post("/api/select", json=selection_request)
        self.assertEqual(selected.status_code, 200)
        selected_payload = selected.json()
        self.assertEqual(selected_payload["profile_version"], 1)
        self.assertIn("case_study weight rose from 0.33 to 0.60", selected_payload["learned_change"])
        self.assertEqual(len(selected_payload["outline"]["sessions"]), 2)

        replay = self.client.post("/api/select", json={**selection_request, "card_ids": list(reversed(case_study_ids))})
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json(), selected_payload)

        conflicting = self.client.post(
            "/api/select",
            json={"session_id": first_payload["session_id"], "card_ids": [first_payload["cards"][0]["id"]]},
        )
        self.assertEqual(conflicting.status_code, 409)
        self.assertEqual(conflicting.json()["error"]["code"], "selection_already_committed")

        second_search = self.client.post(
            "/api/search",
            json={"subject": "Applied Machine Learning", "level": "undergraduate"},
        )
        self.assertEqual(second_search.status_code, 200)
        second_payload = second_search.json()
        self.assertEqual(second_payload["profile_version"], 1)
        self.assertEqual(
            [card["teaching_style"] for card in second_payload["cards"][:2]],
            ["case_study", "case_study"],
        )

    def test_publish_reserves_one_fixture_publication(self) -> None:
        search = self.client.post(
            "/api/search",
            json={"subject": "Machine Learning", "level": "undergraduate"},
        ).json()
        selected = self.client.post(
            "/api/select",
            json={"session_id": search["session_id"], "card_ids": [search["cards"][0]["id"]]},
        ).json()

        first = self.client.post("/api/publish", json={"selection_id": selected["selection_id"]})
        replay = self.client.post("/api/publish", json={"selection_id": selected["selection_id"]})
        self.assertEqual(first.status_code, 202)
        self.assertEqual(replay.status_code, 202)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(first.json()["status"], "publishing")

    def test_preference_persists_across_backend_restart(self) -> None:
        first_search = self.client.post(
            "/api/search",
            json={"subject": "Machine Learning", "level": "undergraduate"},
        ).json()
        case_study_ids = [
            card["id"]
            for card in first_search["cards"]
            if card["teaching_style"] == "case_study"
        ]
        self.client.post(
            "/api/select",
            json={"session_id": first_search["session_id"], "card_ids": case_study_ids},
        )

        self.client_context.__exit__(None, None, None)
        self.client_context = None

        with TestClient(app) as restarted_client:
            second_search = restarted_client.post(
                "/api/search",
                json={"subject": "Applied Machine Learning", "level": "undergraduate"},
            )

        self.assertEqual(second_search.status_code, 200)
        payload = second_search.json()
        self.assertEqual(payload["profile_version"], 1)
        self.assertEqual(
            [card["teaching_style"] for card in payload["cards"][:2]],
            ["case_study", "case_study"],
        )

    def test_invalid_input_uses_the_shared_error_envelope(self) -> None:
        response = self.client.post("/api/search", json={"subject": "", "level": "undergraduate"})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "invalid_input")
        self.assertIn("retryable", response.json()["error"])
