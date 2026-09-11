"""render_outline — lane A adapter.

Renders a saved outline into a publishable artifact by executing the renderer
inside a Daytona sandbox.

Honest note for the README: the renderer is deterministic code we wrote, so the
sandbox is isolation for untrusted *source content* (LLM output and scraped web
text flow into the outline), not for untrusted code. Set
CURRICULUMAI_RENDER_LOCAL=1 to bypass the sandbox — that is degradation tier 2,
not the accepted demo path.

Standard library only inside the sandbox: no pip install, so Daytona's outbound
network behaviour never becomes a blocker.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .artifact import Artifact, ConfigurationError, RenderError
from .template import render_html

CONTENT_TYPE = "text/html"
_TEMPLATE_PATH = Path(__file__).with_name("template.py")


def _load_sdk():
    try:
        from daytona import Daytona, DaytonaConfig  # type: ignore
        return Daytona, DaytonaConfig
    except ImportError:
        pass
    try:
        from daytona_sdk import Daytona, DaytonaConfig  # type: ignore
        return Daytona, DaytonaConfig
    except ImportError as exc:
        raise ConfigurationError(
            "Daytona SDK not installed. `pip install daytona`, or set "
            "CURRICULUMAI_RENDER_LOCAL=1 to render without a sandbox."
        ) from exc


def render_outline(selection_id: str, saved_outline: dict) -> Artifact:
    """Render the saved (immutable) outline. Never regenerates content."""
    title = str(saved_outline.get("title") or "Untitled module")

    if os.getenv("CURRICULUMAI_RENDER_LOCAL") == "1":
        html = render_html(saved_outline, selection_id)
        return Artifact(
            title=title,
            content_type=CONTENT_TYPE,
            content_bytes=html.encode("utf-8"),
        )

    return Artifact(
        title=title,
        content_type=CONTENT_TYPE,
        content_bytes=_render_in_sandbox(selection_id, saved_outline),
    )


def _render_in_sandbox(selection_id: str, saved_outline: dict) -> bytes:
    api_key = os.getenv("DAYTONA_API_KEY")
    if not api_key:
        raise ConfigurationError("DAYTONA_API_KEY is not set (see .env.example).")

    Daytona, DaytonaConfig = _load_sdk()

    # Daytona's default exec timeout is 10s, which a cold sandbox can exceed.
    timeout = int(os.getenv("DAYTONA_EXEC_TIMEOUT", "60"))

    template_src = _TEMPLATE_PATH.read_bytes()
    outline_src = json.dumps(saved_outline, ensure_ascii=False).encode("utf-8")

    client = Daytona(DaytonaConfig(api_key=api_key))
    sandbox = None
    try:
        sandbox = client.create()

        # Ask the sandbox where its home is rather than guessing a path that
        # may not exist — upload_file does not create missing directories.
        workdir = os.getenv("DAYTONA_WORKDIR") or sandbox.get_user_root_dir()
        remote_template = f"{workdir}/template.py"
        remote_outline = f"{workdir}/outline.json"
        remote_output = f"{workdir}/artifact.html"

        sandbox.fs.upload_file(template_src, remote_template)
        sandbox.fs.upload_file(outline_src, remote_outline)

        result = sandbox.process.exec(
            f"python3 {remote_template} {remote_outline} {selection_id} {remote_output}",
            timeout=timeout,
        )
        if getattr(result, "exit_code", 0) != 0:
            raise RenderError(
                f"Sandbox renderer exited {result.exit_code}: "
                f"{getattr(result, 'result', '')[:500]}"
            )

        data = sandbox.fs.download_file(remote_output)
        if not data:
            raise RenderError("Sandbox produced an empty artifact.")
        return data if isinstance(data, bytes) else bytes(data)
    except RenderError:
        raise
    except Exception as exc:  # SDK surface varies; never leak a sandbox
        raise RenderError(f"Daytona rendering failed: {exc}") from exc
    finally:
        if sandbox is not None:
            try:
                client.delete(sandbox)
            except Exception:
                pass
