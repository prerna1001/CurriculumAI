"""Live CrewAI researcher and writer workflow."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterable

from backend.integrations.you_search import Evidence, YouSearchClient
from backend.learning.profile import ProfileContext
from backend.storage.repository import Candidate


class AgentWorkflowError(Exception):
    """Raised when a live agent result is invalid or unavailable."""


@dataclass(frozen=True)
class ResearchIdea:
    title: str
    description: str
    teaching_style: str
    source_url: str
    why_suggested: str
    evidence_text: str


VALID_STYLES = {"theory", "case_study", "project"}


def profile_instruction(profile: ProfileContext) -> str:
    """Return the exact saved profile information included in both agent tasks."""
    weights = ", ".join(
        f"{style}={weight:.2f}" for style, weight in sorted(profile.weights.items())
    )
    return (
        f"Professor preference snapshot v{profile.version}: {profile.summary} "
        f"Teaching-style weights: {weights}."
    )


def research_query(subject: str, level: str, profile: ProfileContext) -> str:
    """Make the profile influence the evidence query as well as the agent prompt."""
    preferred_style = max(profile.weights, key=profile.weights.get)
    return (
        f"Evidence-supported {preferred_style.replace('_', ' ')} teaching activities for "
        f"{level} {subject}; pedagogy, real-world examples, and credible sources"
    )


def _crew_output(role: str, goal: str, task_description: str, expected_output: str) -> dict[str, Any]:
    """Run a single CrewAI role and parse its required JSON response."""
    try:
        from crewai import Agent, Crew, LLM, Process, Task
    except ImportError as error:
        raise AgentWorkflowError("CrewAI is not installed. Install backend requirements first.") from error

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    llm = LLM(model=f"anthropic/{model}")
    agent = Agent(role=role, goal=goal, backstory="You produce grounded curriculum material.", llm=llm, verbose=False)
    task = Task(description=task_description, expected_output=expected_output, agent=agent)
    try:
        result = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()
    except Exception as error:
        raise AgentWorkflowError("The configured LLM provider did not complete the agent task.") from error
    raw = getattr(result, "raw", str(result)).strip()
    return _parse_json(raw)


def _parse_json(raw: str) -> dict[str, Any]:
    """Accept an object wrapped in an optional Markdown code fence."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise AgentWorkflowError("The agent did not return a JSON object.")
    try:
        output = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as error:
        raise AgentWorkflowError("The agent returned invalid JSON.") from error
    if not isinstance(output, dict):
        raise AgentWorkflowError("The agent response must be a JSON object.")
    return output


def research_candidates(
    subject: str, level: str, profile: ProfileContext, search_client: YouSearchClient | None = None
) -> list[ResearchIdea]:
    """Use You.com evidence and a researcher role to produce four supported ideas."""
    evidence = (search_client or YouSearchClient()).search(research_query(subject, level, profile))
    evidence_text = "\n".join(f"- {item.title}: {item.url}\n  {item.text}" for item in evidence)
    output = _crew_output(
        role="Curriculum evidence researcher",
        goal="Select source-grounded teaching activities that fit the professor's saved preferences.",
        task_description=(
            f"{profile_instruction(profile)}\n\n"
            f"Create exactly four {level} curriculum topic cards for {subject}. "
            "Return exactly two case_study cards, one theory card, and one project card. "
            "Use only the evidence URLs below. Each card must use one of theory, case_study, or project. "
            "Return JSON only: {\"cards\":[{\"title\":...,\"description\":...,"
            "\"teaching_style\":...,\"source_url\":...,\"why_suggested\":...}]}.\n\n"
            f"Evidence:\n{evidence_text}"
        ),
        expected_output="A JSON object containing exactly four evidence-supported cards.",
    )
    cards = output.get("cards")
    if not isinstance(cards, list) or len(cards) != 4:
        raise AgentWorkflowError("The researcher must return exactly four cards.")
    allowed_urls = {item.url for item in evidence}
    evidence_by_url = {item.url: item.text for item in evidence}
    ideas = []
    for card in cards:
        if not isinstance(card, dict):
            raise AgentWorkflowError("A researcher card was not an object.")
        style = card.get("teaching_style")
        source_url = card.get("source_url")
        required = ("title", "description", "why_suggested")
        if style not in VALID_STYLES or source_url not in allowed_urls or not all(card.get(key) for key in required):
            raise AgentWorkflowError("A researcher card failed style or source validation.")
        ideas.append(
            ResearchIdea(
                title=str(card["title"]),
                description=str(card["description"]),
                teaching_style=style,
                source_url=source_url,
                why_suggested=str(card["why_suggested"]),
                evidence_text=evidence_by_url[source_url],
            )
        )
    style_counts = {style: sum(idea.teaching_style == style for idea in ideas) for style in VALID_STYLES}
    if style_counts != {"theory": 1, "case_study": 2, "project": 1}:
        raise AgentWorkflowError("The researcher must return two case studies, one theory, and one project.")
    return ideas


def candidates_from_research(session_id: str, ideas: Iterable[ResearchIdea]) -> list[Candidate]:
    """Attach safe database IDs and evidence text to agent-created cards."""
    return [
        Candidate(
            id=f"card_{session_id}_{index + 1}",
            title=idea.title,
            description=idea.description,
            teaching_style=idea.teaching_style,
            source_url=idea.source_url,
            why_suggested=idea.why_suggested,
            evidence_text=idea.evidence_text,
            rank_order=index,
        )
        for index, idea in enumerate(ideas)
    ]


def generate_outline(candidates: list[Candidate], profile: ProfileContext) -> dict[str, Any]:
    """Use the writer role to make an immutable outline from selected saved evidence."""
    source_url_by_id = {candidate.id: candidate.source_url for candidate in candidates}
    selected_topics = "\n".join(
        f"- id={candidate.id}; topic={candidate.title}; source={candidate.source_url}; "
        f"evidence={candidate.evidence_text}"
        for candidate in candidates
    )
    output = _crew_output(
        role="Curriculum outline writer",
        goal="Create a concise, cited learning module that reflects saved professor preferences.",
        task_description=(
            f"{profile_instruction(profile)}\n\n"
            "Create exactly one outline session for each selected topic below. Keep the topic and source IDs. "
            "Return JSON only using this exact shape: {\"title\":...,\"sessions\":[{\"topic\":...,"
            "\"activity\":...,\"learning_objective\":...,\"source_references\":[{\"source_id\":...,\"url\":...}]}]}.\n\n"
            f"Selected topics and saved evidence:\n{selected_topics}"
        ),
        expected_output="A JSON outline with one cited session per selected topic.",
    )
    sessions = output.get("sessions")
    if not isinstance(output.get("title"), str) or not isinstance(sessions, list) or len(sessions) != len(candidates):
        raise AgentWorkflowError("The writer must return one titled session per selected topic.")
    selected_ids = {candidate.id for candidate in candidates}
    referenced_ids = set()
    for session in sessions:
        if not isinstance(session, dict) or not all(
            isinstance(session.get(field), str) and session[field].strip()
            for field in ("topic", "activity", "learning_objective")
        ):
            raise AgentWorkflowError("Every outline session needs a topic, activity, and learning objective.")
        references = session.get("source_references") if isinstance(session, dict) else None
        if not isinstance(references, list) or not references:
            raise AgentWorkflowError("Every outline session needs a source reference.")
        for reference in references:
            if (
                not isinstance(reference, dict)
                or reference.get("source_id") not in source_url_by_id
                or reference.get("url") != source_url_by_id[reference.get("source_id")]
            ):
                raise AgentWorkflowError("The writer returned an unapproved source reference.")
            referenced_ids.add(reference["source_id"])
    if referenced_ids != selected_ids:
        raise AgentWorkflowError("The writer must cite evidence for every selected topic.")
    return output
