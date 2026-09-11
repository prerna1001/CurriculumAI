# CurriculumAI

A curriculum planner whose agents learn a professor's teaching style from the
topics they actually choose, and rank the next set differently because of it.

Built for **Build with YOU: The AI Agent Hackathon** (theme: *self-improving and
learning agents*).

## The loop being demonstrated

1. A professor enters a subject and level. A research agent searches the live web
   (You.com) and a writer agent drafts four evidence-backed topic cards, each
   labelled with a teaching style — `theory`, `case_study` or `project`.
2. The professor selects the topics they would actually teach and presses
   **Use these topics**. That selection is the training signal.
3. A module outline is generated from the selected cards, saved, and frozen.
4. On the **next** search the profile has moved: style weights are recomputed,
   the ranking changes, and each card shows how far it moved. The professor sees
   `case_study weight rose from 0.33 to 0.60` and watches case-study topics climb
   to the top.
5. **Approve & publish** renders the saved outline in a Daytona sandbox and
   delivers it through One — the finished curriculum lands in the professor's
   inbox as formatted HTML.

Step 4 is the point of the project. Steps 1–3 exist to produce the signal, and
step 5 is the closing beat.

## How the learning works

Preferences are stored as generic `(dimension, value, count)` rows, seeded at
`theory=1, case_study=1, project=1` (a Laplace prior, so nothing starts at zero).
Each committed selection adds one count per unique selected card's style and
increments the profile version. A style's weight is its count over the total.

That profile snapshot is read once at the start of a request and used in three
places:

1. the research agent's task description, shaping how it constructs queries,
2. the writer agent's task description, shaping the activities it drafts,
3. a deterministic re-rank — order by descending style weight, ties broken by
   the original candidate order.

Only (3) is a sort. (1) and (2) are what make this a learning agent rather than
a sorted list.

**We do not overclaim.** Selecting one topic of each style produces equal weights
and the ranking genuinely does not move; the UI says so rather than inventing a
change. The stored original candidate order is what makes the before/after
comparison verifiable instead of anecdotal.

## Sponsor technology, honestly described

| Tool | How it is used |
| --- | --- |
| **You.com** | Live web search behind the research agent. Every topic card carries the source it came from. |
| **CrewAI** | Two agents — researcher and outline writer — both receiving the learned profile. |
| **Daytona** | Executes the renderer that turns a saved outline into a publishable HTML artifact. |
| **One** | Delivers that artifact to the professor's inbox through Gmail, with managed auth. |

On Daytona specifically: the renderer is deterministic code we wrote, so the
sandbox is isolation for untrusted *source content* — LLM output and scraped web
text flow into the outline — not for untrusted code. The renderer uses the Python
standard library only, so nothing is installed at runtime.

## Running it

Frontend, in fixture mode (no backend or API keys needed):

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. Fixture mode implements the same contracts and the
same ranking rule, so the whole learning loop is demonstrable offline. It is for
development only — the accepted demo uses real services.

Point it at the real backend instead:

```bash
echo 'NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000' > frontend/.env.local
```

Lane A's Python adapters and their tests:

```bash
python3.11 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -q
```

Use Python 3.11 — CrewAI and the Daytona SDK do not reliably have wheels for
3.14, which is the system default on this machine.

Copy `.env.example` to `.env` for live rendering and publishing. Two escape
hatches exist for the demo's degradation ladder: `CURRICULUMAI_RENDER_LOCAL=1`
renders without a sandbox, and `CURRICULUMAI_PUBLISH_LOCAL=1` writes the artifact
to `artifacts/` instead of publishing it.

## Layout

```
contracts/              frozen request/response shapes, shared by both lanes
backend/rendering/      lane A — outline -> HTML, executed in Daytona
backend/integrations/   lane A — publishing through One
backend/agents/         lane B — CrewAI roles
backend/learning/       lane B — preference counts and ranking
backend/main.py         lane B — the three HTTP routes
frontend/               lane A — the single screen, plus a fixture backend
tests/                  lane A — rendering and publishing
```

Two developers work in separate clones on separate branches with exclusive file
ownership. `CurriculumAI-Two-Person-Build-Plan.md` is the operating document:
phases, gates, the A/B adapter boundary, and the degradation ladder.

## Status

**Lane A is complete and the phase-1 readiness gate passes.** A rendered outline
has gone Daytona → One → inbox against the live services: ~2.2 s to create a
sandbox, render and retrieve the HTML, then ~0.8 s to deliver it. The sandbox
output is byte-identical to the local render, which is what proves the renderer
is deterministic rather than merely working.

The frontend is verified in fixture mode end to end: search, selection, the
learning re-rank with visible rank deltas, the approved outline surviving a
subsequent search, publish, and the error state when the backend is unreachable.
38 unit tests pass.

Google Drive was the intended publish destination and was ruled out during the
gate — One exposes only Drive's metadata endpoint, which creates a named file
containing nothing. `contracts/one_action.md` records the evidence, the working
invocation and the measured timings.

Still outstanding for A: integration against B's real backend, and the phase 6–7
deliverables (backup recording, video, description, submission).
