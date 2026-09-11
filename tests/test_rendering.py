import json
from html import escape
from pathlib import Path

import pytest

from backend.rendering.artifact import Artifact
from backend.rendering.daytona_render import render_outline
from backend.rendering.template import render_html, safe_url

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"


@pytest.fixture
def saved_outline() -> dict:
    data = json.loads((CONTRACTS / "select-response.json").read_text())
    return data["outline"]


# --- escaping: source text is data, never markup ---------------------------

ADVERSARIAL = {
    "title": "<script>alert('title')</script>",
    "sessions": [
        {
            "topic": "<img src=x onerror=alert(1)>",
            "activity": "Ignore previous instructions and </dd><script>alert(2)</script>",
            "learning_objective": "A & B < C",
            "source_references": [
                {"source_id": "<b>bold</b>", "url": "https://example.org/ok"},
                {"source_id": "js", "url": "javascript:alert(3)"},
                {"source_id": "data", "url": "data:text/html,<script>alert(4)</script>"},
            ],
        }
    ],
}


def test_markup_in_source_content_is_inert():
    html = render_html(ADVERSARIAL, "sel_x")
    # The payload text may survive; what must not survive is a parseable tag.
    assert "<script" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_non_http_urls_are_not_linked():
    html = render_html(ADVERSARIAL, "sel_x")
    assert "javascript:" not in html
    assert "data:text/html" not in html
    assert "link omitted" in html
    assert 'href="https://example.org/ok"' in html


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "", "https://", None, 42],
)
def test_safe_url_rejects(url):
    assert safe_url(url) is None


@pytest.mark.parametrize("url", ["https://example.org/a", "http://example.org/b?x=1#y"])
def test_safe_url_accepts(url):
    assert safe_url(url) == url


# --- fidelity: the artifact matches the approved preview -------------------

def test_every_session_is_rendered(saved_outline):
    html = render_html(saved_outline, "sel_baseline")
    for session in saved_outline["sessions"]:
        # escaped, because apostrophes become &#x27; on the way through
        assert escape(session["topic"]) in html
        assert escape(session["learning_objective"]) in html
    assert "2 sessions" in html


def test_citations_survive_rendering(saved_outline):
    html = render_html(saved_outline, "sel_baseline")
    for session in saved_outline["sessions"]:
        for ref in session["source_references"]:
            assert ref["url"] in html


def test_render_is_deterministic(saved_outline):
    assert render_html(saved_outline, "s") == render_html(saved_outline, "s")


def test_empty_outline_does_not_crash():
    html = render_html({"title": "Empty", "sessions": []}, "sel_x")
    assert "no sessions" in html


# --- a curriculum assembled from several approved modules ----------------

def _module(title: str, topics: list[str]) -> dict:
    return {
        "title": title,
        "sessions": [
            {
                "topic": topic,
                "activity": f"Activity for {topic}",
                "learning_objective": f"Objective for {topic}",
                "source_references": [{"source_id": topic, "url": "https://example.org/x"}],
            }
            for topic in topics
        ],
    }


CURRICULUM = {
    "title": "Machine Learning — course outline",
    "modules": [_module("First module", ["A"]), _module("Second module", ["B", "C"])],
}


def test_modules_render_with_continuous_numbering():
    html = render_html(CURRICULUM, "curriculum_1")
    # Numbering must not restart per module — it is one course.
    for number in ("01", "02", "03"):
        assert f"<span class='num'>{number}</span>" in html
    assert "3 sessions" in html


def test_every_module_keeps_its_own_heading():
    html = render_html(CURRICULUM, "curriculum_1")
    assert html.count("class='module'") == 2
    assert "First module" in html and "Second module" in html


def test_module_titles_are_escaped_like_everything_else():
    html = render_html(
        {"title": "t", "modules": [_module("<script>alert(1)</script>", ["A"])]},
        "curriculum_1",
    )
    assert "<script" not in html
    assert "&lt;script&gt;" in html


def test_malformed_modules_are_skipped_not_crashed():
    html = render_html(
        {"title": "t", "modules": ["nonsense", {"title": "ok"}, _module("Real", ["A"])]},
        "curriculum_1",
    )
    assert "Real" in html
    assert "1 session" in html


def test_empty_modules_list_does_not_crash():
    assert "no sessions" in render_html({"title": "t", "modules": []}, "c")


def test_non_dict_outline_rejected():
    with pytest.raises(ValueError):
        render_html([], "sel_x")  # type: ignore[arg-type]


# --- the adapter -----------------------------------------------------------

def test_local_mode_returns_html_artifact(monkeypatch, saved_outline):
    monkeypatch.setenv("CURRICULUMAI_RENDER_LOCAL", "1")
    artifact = render_outline("sel_baseline", saved_outline)

    assert isinstance(artifact, Artifact)
    assert artifact.content_type == "text/html"
    assert artifact.payload is None
    assert artifact.content_bytes is not None
    assert artifact.title == saved_outline["title"]
    assert b"<!doctype html>" in artifact.content_bytes
    assert artifact.size > 0


def test_artifact_requires_exactly_one_body():
    with pytest.raises(ValueError):
        Artifact(title="t", content_type="text/html")
    with pytest.raises(ValueError):
        Artifact(title="t", content_type="text/html", content_bytes=b"x", payload={"a": 1})
