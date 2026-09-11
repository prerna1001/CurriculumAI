"""publish_artifact — lane A adapter.

One has no Python SDK. Its documented programmatic surfaces are the Node CLI
(`one actions execute`, with `--agent` for JSON output), a REST passthrough, and
an MCP server. This adapter shells out to the CLI.

DESTINATION: Gmail. Chosen at the phase-1 readiness gate after Google Drive was
ruled out — One exposes only Drive's metadata endpoint (`POST /drive/v3/files`),
which creates a named file with no contents, and does not expose Google's
upload URI. Gmail's Send Email action takes `isHtml: true` and sends our
rendered HTML as the message body, so the artifact arrives intact with no
multipart upload involved. See contracts/one_action.md.

Because the destination takes a JSON body rather than bytes, every parameter
goes through `-d`. One's own CLI guidance is explicit that path and query
parameters must NOT be put in the body flag; this action has neither.

This adapter never writes to SQLite and never touches preferences — B owns all
state (see the A/B boundary in the build plan).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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

    return _publish_via_one(artifact)


# --- degradation tier 2 -----------------------------------------------------

def _publish_local(publication_key: str, artifact: Artifact) -> Receipt:
    """Write the artifact to disk instead of publishing it.

    Tier 2 of the degradation ladder: the professor still sees the real rendered
    artifact, it just is not delivered externally. Say so on camera rather than
    implying a live publish.
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
            f"{name} is not set. See contracts/one_action.md for where each "
            "value comes from, then copy it into .env."
        )
    return value


def _request_body(connection_key: str, artifact: Artifact) -> dict[str, Any]:
    """Map the artifact onto the destination action's request body.

    An artifact carrying a structured payload is passed through as-is; one
    carrying rendered bytes becomes the HTML body of an email.
    """
    if artifact.payload is not None:
        return {"connectionKey": connection_key, **artifact.payload}

    assert artifact.content_bytes is not None
    return {
        "connectionKey": connection_key,
        "to": _require("ONE_RECIPIENT"),
        "subject": artifact.title,
        "body": artifact.content_bytes.decode("utf-8"),
        "isHtml": True,
    }


def _build_command(platform: str, action_id: str, connection_key: str,
                   artifact: Artifact) -> list[str]:
    return [
        "one", "--agent", "actions", "execute",
        platform, action_id, connection_key,
        "-d", json.dumps(_request_body(connection_key, artifact), ensure_ascii=False),
    ]


def _publish_via_one(artifact: Artifact) -> Receipt:
    if shutil.which("one") is None:
        raise ConfigurationError(
            "The One CLI is not on PATH. `npm i -g @withone/cli`, then "
            "`one login`. Or set CURRICULUMAI_PUBLISH_LOCAL=1 for tier 2."
        )

    cmd = _build_command(
        _require("ONE_PLATFORM"),
        _require("ONE_ACTION_ID"),
        _require("ONE_CONNECTION_KEY"),
        artifact,
    )

    # ONE_SECRET is only needed for headless use. If `one login` has already
    # stored credentials on this machine, the CLI authenticates without it.
    env = {**os.environ, "ONE_NO_TELEMETRY": "1"}

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT, env=env
        )
    except subprocess.TimeoutExpired as exc:
        raise PublishError(
            f"One CLI timed out after {CLI_TIMEOUT}s. Check the destination "
            "before retrying — the send may have gone through."
        ) from exc

    if proc.returncode != 0:
        raise PublishError(
            f"One CLI exited {proc.returncode}: {(proc.stderr or proc.stdout)[:500]}"
        )

    return _receipt_from(proc.stdout)


def _receipt_from(stdout: str) -> Receipt:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PublishError(f"One returned non-JSON output: {stdout[:500]}") from exc

    external_id = _dig(data, os.getenv("ONE_RESULT_ID_PATH", "id"))
    if external_id is None:
        raise PublishError(
            "Published, but no message id was found in the response. Set "
            "ONE_RESULT_ID_PATH to match and record it in "
            f"contracts/one_action.md: {json.dumps(data)[:500]}"
        )

    # Gmail returns an id but no link, so the URL is built from a template.
    url_path = os.getenv("ONE_RESULT_URL_PATH", "")
    external_url = _dig(data, url_path) if url_path else None
    if external_url is None:
        template = os.getenv(
            "ONE_RESULT_URL_TEMPLATE", "https://mail.google.com/mail/u/0/#all/{id}"
        )
        external_url = template.format(id=external_id)

    return Receipt(external_id=str(external_id), external_url=str(external_url), raw=data)


def _dig(data: Any, dotted: str) -> Any:
    """Walk a dotted path, descending into the common `data`/`result` wrappers."""
    if not dotted:
        return None
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
