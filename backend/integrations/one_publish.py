"""publish_artifact — lane A adapter.

One has no Python SDK. Its documented programmatic surfaces are the Node CLI
(`one actions execute`, with `--agent` for JSON output), a REST passthrough at
api.withone.ai/v1/passthrough, and an MCP server. This adapter shells out to the
CLI, which is the path with `--form-data` support for multipart uploads.

One is a *passthrough*: it proxies to the destination platform's own API, so the
exact invocation and the shape of the receipt are decided by whichever
destination is chosen at the phase-1 readiness gate. Everything that depends on
that is isolated in `_build_command` and the two receipt paths below, and is
recorded in `contracts/one_action.md`.

This adapter never writes to SQLite and never touches preferences — B owns all
state (see the A/B boundary in the build plan).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from backend.rendering.artifact import (
    Artifact,
    ConfigurationError,
    PublishError,
    Receipt,
)

SAFE_KEY = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
LOCAL_DIR = Path(os.getenv("CURRICULUMAI_ARTIFACT_DIR", "artifacts"))
CLI_TIMEOUT = int(os.getenv("ONE_CLI_TIMEOUT", "90"))


def publish_artifact(publication_key: str, artifact: Artifact) -> Receipt:
    """Publish the rendered artifact once. B guarantees one call per selection."""
    if not SAFE_KEY.match(publication_key):
        raise PublishError(f"Unsafe publication key: {publication_key!r}")

    if os.getenv("CURRICULUMAI_PUBLISH_LOCAL") == "1":
        return _publish_local(publication_key, artifact)

    return _publish_via_one(publication_key, artifact)


# --- degradation tier 2 -----------------------------------------------------

def _publish_local(publication_key: str, artifact: Artifact) -> Receipt:
    """Write the artifact to disk instead of publishing it.

    Tier 2 of the degradation ladder: the professor still sees the real rendered
    artifact, it just is not pushed to an external destination. Say so on camera
    rather than implying a live publish.
    """
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".html" if artifact.content_type == "text/html" else ".txt"
    path = (LOCAL_DIR / f"{publication_key}{suffix}").resolve()

    if artifact.content_bytes is not None:
        path.write_bytes(artifact.content_bytes)
    else:
        path.write_text(json.dumps(artifact.payload, indent=2), encoding="utf-8")

    return Receipt(
        external_id=publication_key,
        external_url=path.as_uri(),
        raw={"mode": "local"},
    )


# --- One --------------------------------------------------------------------

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(
            f"{name} is not set. Fill in contracts/one_action.md at the phase-1 "
            "readiness gate, then copy the values into .env."
        )
    return value


def _build_command(platform: str, action_id: str, connection_key: str,
                   artifact: Artifact, upload_path: Path | None) -> list[str]:
    """Construct the One CLI invocation.

    *** PHASE-1 VERIFY POINT ***
    Binary input to One actions is not documented. Run
    `one actions knowledge <platform> <actionId>` first, get one upload to
    succeed by hand, then correct this function to match and paste the working
    command into contracts/one_action.md.
    """
    cmd = ["one", "--agent", "actions", "execute", platform, action_id, connection_key]

    if upload_path is not None:
        field = os.getenv("ONE_FORM_FIELD", "file")
        cmd += ["--form-data", f"{field}=@{upload_path}"]
        cmd += ["--form-data", f"name={artifact.title}"]
    else:
        cmd += ["--input", json.dumps(artifact.payload or {}, ensure_ascii=False)]

    return cmd


def _publish_via_one(publication_key: str, artifact: Artifact) -> Receipt:
    if shutil.which("one") is None:
        raise ConfigurationError(
            "The One CLI is not on PATH. `npm i -g @withone/cli`, then "
            "`one login`. Or set CURRICULUMAI_PUBLISH_LOCAL=1 for tier 2."
        )

    platform = _require("ONE_PLATFORM")
    action_id = _require("ONE_ACTION_ID")
    connection_key = _require("ONE_CONNECTION_KEY")

    env = {**os.environ, "ONE_SECRET": _require("ONE_SECRET")}

    tmp_dir: tempfile.TemporaryDirectory | None = None
    upload_path: Path | None = None
    if artifact.content_bytes is not None:
        tmp_dir = tempfile.TemporaryDirectory()
        suffix = ".html" if artifact.content_type == "text/html" else ".bin"
        upload_path = Path(tmp_dir.name) / f"{publication_key}{suffix}"
        upload_path.write_bytes(artifact.content_bytes)

    try:
        cmd = _build_command(platform, action_id, connection_key, artifact, upload_path)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT, env=env
            )
        except subprocess.TimeoutExpired as exc:
            raise PublishError(
                f"One CLI timed out after {CLI_TIMEOUT}s. Check the destination "
                "folder before retrying — the upload may have landed."
            ) from exc

        if proc.returncode != 0:
            raise PublishError(
                f"One CLI exited {proc.returncode}: {(proc.stderr or proc.stdout)[:500]}"
            )

        return _receipt_from(proc.stdout)
    finally:
        if tmp_dir is not None:
            tmp_dir.cleanup()


def _receipt_from(stdout: str) -> Receipt:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PublishError(f"One returned non-JSON output: {stdout[:500]}") from exc

    id_path = os.getenv("ONE_RESULT_ID_PATH", "id")
    url_path = os.getenv("ONE_RESULT_URL_PATH", "webViewLink")

    external_id = _dig(data, id_path)
    external_url = _dig(data, url_path)

    if external_id is None or external_url is None:
        raise PublishError(
            "Published, but the receipt could not be read. Set "
            f"ONE_RESULT_ID_PATH / ONE_RESULT_URL_PATH to match this response "
            f"and record it in contracts/one_action.md: {json.dumps(data)[:500]}"
        )

    return Receipt(external_id=str(external_id), external_url=str(external_url), raw=data)


def _dig(data: Any, dotted: str) -> Any:
    """Walk a dotted path, descending into the common `data`/`result` wrappers."""
    for root in (data, _child(data, "data"), _child(data, "result"), _child(data, "output")):
        if root is None:
            continue
        node: Any = root
        for part in dotted.split("."):
            node = _child(node, part)
            if node is None:
                break
        if node is not None:
            return node
    return None


def _child(node: Any, key: str) -> Any:
    if isinstance(node, dict):
        return node.get(key)
    if isinstance(node, list) and key.isdigit() and int(key) < len(node):
        return node[int(key)]
    return None
