import json
from pathlib import Path

import pytest

from backend.integrations import one_publish
from backend.integrations.one_publish import (
    _build_command,
    _receipt_from,
    publish_artifact,
)
from backend.rendering.artifact import (
    Artifact,
    ConfigurationError,
    PublishError,
)


@pytest.fixture
def artifact() -> Artifact:
    return Artifact(
        title="Diagnosing model failure in practice",
        content_type="text/html",
        content_bytes=b"<!doctype html><p>outline</p>",
    )


@pytest.fixture(autouse=True)
def _isolated_artifact_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(one_publish, "LOCAL_DIR", tmp_path / "artifacts")


# --- key safety ------------------------------------------------------------

@pytest.mark.parametrize(
    "key", ["../escape", "a/b", "", "key with space", "x" * 200, "k;rm -rf /"]
)
def test_unsafe_publication_keys_rejected(key, artifact):
    with pytest.raises(PublishError):
        publish_artifact(key, artifact)


# --- degradation tier 2 ----------------------------------------------------

def test_local_publish_writes_the_artifact(monkeypatch, artifact):
    monkeypatch.setenv("CURRICULUMAI_PUBLISH_LOCAL", "1")
    receipt = publish_artifact("sel_baseline", artifact)

    assert receipt.external_id == "sel_baseline"
    assert receipt.external_url.startswith("file://")
    written = Path(receipt.external_url.replace("file://", ""))
    assert written.read_bytes() == artifact.content_bytes


def test_local_publish_handles_structured_payload(monkeypatch):
    monkeypatch.setenv("CURRICULUMAI_PUBLISH_LOCAL", "1")
    receipt = publish_artifact(
        "sel_x", Artifact(title="t", content_type="application/json", payload={"a": 1})
    )
    written = Path(receipt.external_url.replace("file://", ""))
    assert json.loads(written.read_text()) == {"a": 1}


# --- command construction --------------------------------------------------

def test_command_is_a_list_not_a_shell_string(artifact, tmp_path):
    upload = tmp_path / "a.html"
    upload.write_bytes(b"x")
    cmd = _build_command("drive", "act_1", "conn_1", artifact, upload)

    assert isinstance(cmd, list)
    assert all(isinstance(part, str) for part in cmd)
    assert cmd[:4] == ["one", "--agent", "actions", "execute"]
    assert "--form-data" in cmd


def test_shell_metacharacters_in_title_stay_one_argument(tmp_path):
    upload = tmp_path / "a.html"
    upload.write_bytes(b"x")
    nasty = Artifact(
        title="; rm -rf / #", content_type="text/html", content_bytes=b"x"
    )
    cmd = _build_command("drive", "act_1", "conn_1", nasty, upload)
    assert "name=; rm -rf / #" in cmd


def test_structured_payload_uses_input_not_form_data():
    cmd = _build_command(
        "notion", "act_2", "conn_1",
        Artifact(title="t", content_type="application/json", payload={"blocks": []}),
        None,
    )
    assert "--input" in cmd
    assert "--form-data" not in cmd


# --- receipt parsing -------------------------------------------------------

def test_receipt_read_from_flat_response(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "id")
    monkeypatch.setenv("ONE_RESULT_URL_PATH", "webViewLink")
    receipt = _receipt_from(json.dumps({"id": "abc", "webViewLink": "https://x.test/abc"}))
    assert (receipt.external_id, receipt.external_url) == ("abc", "https://x.test/abc")


def test_receipt_read_through_data_wrapper(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "id")
    monkeypatch.setenv("ONE_RESULT_URL_PATH", "webViewLink")
    receipt = _receipt_from(
        json.dumps({"data": {"id": "abc", "webViewLink": "https://x.test/abc"}})
    )
    assert receipt.external_id == "abc"


def test_unreadable_receipt_names_the_fix(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "nope")
    monkeypatch.setenv("ONE_RESULT_URL_PATH", "alsoNope")
    with pytest.raises(PublishError, match="one_action.md"):
        _receipt_from(json.dumps({"id": "abc"}))


def test_non_json_output_is_reported(monkeypatch):
    with pytest.raises(PublishError, match="non-JSON"):
        _receipt_from("one: command failed")


# --- configuration ---------------------------------------------------------

def test_missing_config_points_at_the_gate(monkeypatch, artifact):
    monkeypatch.delenv("CURRICULUMAI_PUBLISH_LOCAL", raising=False)
    monkeypatch.setattr(one_publish.shutil, "which", lambda _: "/usr/local/bin/one")
    for var in ("ONE_PLATFORM", "ONE_ACTION_ID", "ONE_CONNECTION_KEY", "ONE_SECRET"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ConfigurationError, match="one_action.md"):
        publish_artifact("sel_baseline", artifact)


def test_missing_cli_is_reported(monkeypatch, artifact):
    monkeypatch.delenv("CURRICULUMAI_PUBLISH_LOCAL", raising=False)
    monkeypatch.setattr(one_publish.shutil, "which", lambda _: None)
    with pytest.raises(ConfigurationError, match="@withone/cli"):
        publish_artifact("sel_baseline", artifact)
