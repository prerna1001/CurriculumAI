"""Outline -> HTML. Standard library only.

This module is uploaded into the Daytona sandbox and executed there, so it must
not import anything from the rest of the backend package. It is also imported
directly by the tests, which is what makes the escaping behaviour verifiable
without a sandbox round trip.

Run as a script:  python3 template.py <outline.json> <selection_id> <out.html>
"""

from __future__ import annotations

import html
import json
import sys
from urllib.parse import urlparse

SAFE_SCHEMES = {"http", "https"}

STYLESHEET = """
:root { color-scheme: light; }
body { margin: 0; padding: 2.5rem 1.5rem; background: #faf9f7; color: #1a1a1a;
       font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
main { max-width: 46rem; margin: 0 auto; }
h1 { font-size: 1.75rem; line-height: 1.25; margin: 0 0 .25rem; letter-spacing: -.01em; }
.meta { color: #6b6b6b; font-size: .8125rem; margin: 0 0 2.5rem; }
section { padding: 1.5rem 0; border-top: 1px solid #e5e2dd; }
h2 { font-size: 1.0625rem; margin: 0 0 .75rem; }
h2.module { font-size: .6875rem; text-transform: uppercase; letter-spacing: .1em;
            color: #8a857d; margin: 2.5rem 0 0; padding-top: 1.5rem;
            border-top: 2px solid #1a1a1a; }
h2.module:first-of-type { margin-top: 1rem; }
.num { color: #a8a29a; font-variant-numeric: tabular-nums; margin-right: .5rem; }
dl { margin: 0; }
dt { font-size: .6875rem; text-transform: uppercase; letter-spacing: .06em;
     color: #8a857d; margin: 1rem 0 .25rem; }
dd { margin: 0; }
ul { margin: .25rem 0 0; padding-left: 1.1rem; }
li { font-size: .875rem; }
a { color: #1a5c8a; overflow-wrap: anywhere; }
footer { border-top: 1px solid #e5e2dd; margin-top: 1rem; padding-top: 1.25rem;
         color: #8a857d; font-size: .75rem; }
"""


def safe_url(raw: object) -> str | None:
    """Return the URL only if it is an http(s) URL, else None.

    Source URLs reach this renderer from the web via the research agent, so a
    javascript: or data: href is a live vector rather than a hypothetical one.
    """
    if not isinstance(raw, str):
        return None
    try:
        parsed = urlparse(raw.strip())
    except ValueError:
        return None
    if parsed.scheme.lower() not in SAFE_SCHEMES or not parsed.netloc:
        return None
    return raw.strip()


def _reference_item(ref: object) -> str:
    if not isinstance(ref, dict):
        return ""
    url = safe_url(ref.get("url"))
    label = html.escape(str(ref.get("source_id") or url or "source"))
    if url is None:
        return f"<li>{label} <span>(link omitted: unsupported URL scheme)</span></li>"
    return f'<li><a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">{label}</a></li>'


def _session_block(index: int, session: object) -> str:
    if not isinstance(session, dict):
        return ""
    topic = html.escape(str(session.get("topic", "Untitled session")))
    activity = html.escape(str(session.get("activity", "")))
    objective = html.escape(str(session.get("learning_objective", "")))

    refs = session.get("source_references")
    items = "".join(_reference_item(r) for r in refs) if isinstance(refs, list) else ""
    refs_block = (
        f"<dt>Sources</dt><dd><ul>{items}</ul></dd>" if items else
        "<dt>Sources</dt><dd>No supporting source recorded.</dd>"
    )

    return (
        f"<section><h2><span class='num'>{index:02d}</span>{topic}</h2><dl>"
        f"<dt>Activity</dt><dd>{activity}</dd>"
        f"<dt>Learning objective</dt><dd>{objective}</dd>"
        f"{refs_block}</dl></section>"
    )


def render_html(outline: dict, selection_id: str) -> str:
    """Render a saved outline to a standalone HTML document.

    Accepts either shape: a single module with `sessions`, or a curriculum
    assembled from several approved modules with `modules`. Session numbering
    runs continuously across modules so the document reads as one course.

    Pure and deterministic: the same outline always produces the same bytes, so
    the preview the professor approved and the published artifact can be
    compared directly.
    """
    if not isinstance(outline, dict):
        raise ValueError("outline must be a dict")

    title = html.escape(str(outline.get("title") or "Untitled module"))
    modules = outline.get("modules")

    if isinstance(modules, list):
        parts: list[str] = []
        count = 0
        for module in modules:
            if not isinstance(module, dict):
                continue
            sessions = module.get("sessions")
            if not isinstance(sessions, list):
                continue
            module_title = html.escape(str(module.get("title") or "Untitled module"))
            parts.append(f"<h2 class='module'>{module_title}</h2>")
            for session in sessions:
                count += 1
                parts.append(_session_block(count, session))
        blocks = "".join(parts)
    else:
        sessions = outline.get("sessions")
        if not isinstance(sessions, list):
            sessions = []
        blocks = "".join(_session_block(i, s) for i, s in enumerate(sessions, start=1))
        count = len(sessions)

    if not blocks:
        blocks = "<section><p>This outline has no sessions.</p></section>"

    plural = "session" if count == 1 else "sessions"

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>{STYLESHEET}</style></head><body><main>"
        f"<h1>{title}</h1>"
        f"<p class='meta'>{count} {plural} &middot; selection "
        f"{html.escape(str(selection_id))}</p>"
        f"{blocks}"
        "<footer>Generated by CurriculumAI. Activities are drafted from the cited "
        "sources above; verify each source before teaching from it.</footer>"
        "</main></body></html>"
    )


if __name__ == "__main__":
    outline_path, selection_id, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(outline_path, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_html(data, selection_id))
