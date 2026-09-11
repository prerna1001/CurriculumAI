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

def test_command_is_a_list_not_a_shell_string(artifact, monkeypatch):
    monkeypatch.setenv("ONE_RECIPIENT", "prof@example.org")
    cmd = _build_command("gmail", "act_1", "conn_1", artifact)

    assert isinstance(cmd, list)
    assert all(isinstance(part, str) for part in cmd)
    assert cmd[:4] == ["one", "--agent", "actions", "execute"]
    # One's CLI guidance: body fields go through -d, never as path/query params.
    assert cmd[-2] == "-d"


def test_rendered_html_becomes_the_email_body(artifact, monkeypatch):
    monkeypatch.setenv("ONE_RECIPIENT", "prof@example.org")
    body = json.loads(_build_command("gmail", "act_1", "conn_1", artifact)[-1])

    assert body["to"] == "prof@example.org"
    assert body["subject"] == artifact.title
    assert body["isHtml"] is True
    assert body["body"] == artifact.content_bytes.decode()
    assert body["connectionKey"] == "conn_1"


def test_shell_metacharacters_stay_inside_one_argument(monkeypatch):
    monkeypatch.setenv("ONE_RECIPIENT", "prof@example.org")
    nasty = Artifact(title="; rm -rf / #", content_type="text/html", content_bytes=b"x")
    cmd = _build_command("gmail", "act_1", "conn_1", nasty)

    assert json.loads(cmd[-1])["subject"] == "; rm -rf / #"
    assert "; rm -rf / #" not in cmd  # only ever inside the JSON payload


def test_structured_payload_passes_through_untouched():
    cmd = _build_command(
        "notion", "act_2", "conn_1",
        Artifact(title="t", content_type="application/json", payload={"blocks": []}),
    )
    assert json.loads(cmd[-1]) == {"connectionKey": "conn_1", "blocks": []}


def test_missing_recipient_is_reported(artifact, monkeypatch):
    monkeypatch.delenv("ONE_RECIPIENT", raising=False)
    with pytest.raises(ConfigurationError, match="ONE_RECIPIENT"):
        _build_command("gmail", "act_1", "conn_1", artifact)


# --- receipt parsing -------------------------------------------------------

def test_receipt_read_from_flat_response(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "id")
    monkeypatch.delenv("ONE_RESULT_URL_PATH", raising=False)
    monkeypatch.setenv("ONE_RESULT_URL_TEMPLATE", "https://mail.test/#all/{id}")
    receipt = _receipt_from(json.dumps({"id": "abc", "threadId": "t1"}))
    assert (receipt.external_id, receipt.external_url) == ("abc", "https://mail.test/#all/abc")


def test_receipt_read_through_data_wrapper(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "id")
    receipt = _receipt_from(json.dumps({"data": {"id": "abc"}}))
    assert receipt.external_id == "abc"


def test_explicit_url_path_wins_over_template(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "id")
    monkeypatch.setenv("ONE_RESULT_URL_PATH", "webViewLink")
    receipt = _receipt_from(json.dumps({"id": "abc", "webViewLink": "https://x.test/abc"}))
    assert receipt.external_url == "https://x.test/abc"


def test_unreadable_receipt_names_the_fix(monkeypatch):
    monkeypatch.setenv("ONE_RESULT_ID_PATH", "nope")
    with pytest.raises(PublishError, match="one_action.md"):
        _receipt_from(json.dumps({"messageId": "abc"}))


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
