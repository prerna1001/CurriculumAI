# CurriculumAI

A curriculum planner whose agents learn a professor's teaching style from the
topics they actually choose, and rank the next set differently because of it.

Built for **Build with YOU: The AI Agent Hackathon** (theme: *self-improving and
learning agents*).

![How CurriculumAI works: a professor describes a course, a Researcher agent searches the live web via You.com, four sourced topics appear, the professor picks the ones they would teach, a Writer agent plans the lessons, the choice is remembered and fed back into the next search, and the approved outline is rendered in a Daytona sandbox and delivered through One.](docs/architecture.png)

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

## Guardrails

The agents are the only part of this system allowed to be creative, and the only
part that isn't trusted. Everything they return is checked against something
already on disk before it is stored or shown. There are **37 guard raises**
across the backend; these are the ones that matter.

> [!IMPORTANT]
> **An agent cannot cite a page that was never searched.** Every `source_url` the
> researcher returns must appear in the set You.com actually returned, and every
> citation the writer returns must match the stored URL of a card the professor
> selected. A fabricated source fails validation and the request returns `502` —
> it is never quietly shown as evidence.

### CrewAI — researcher agent
`backend/agents/workflow.py`

- **Exactly four cards**, or the whole result is rejected.
- **Style must be one of** `theory` / `case_study` / `project` — nothing invented.
- **Fixed mix enforced**: two case studies, one theory, one project, so every
  professor is shown all three approaches rather than an echo chamber.
- **Source must be real**: `source_url` has to be one of the URLs You.com returned.
- **No empty fields**: title, description and `why_suggested` must all be present.

### CrewAI — writer agent
`backend/agents/workflow.py`

- **One session per selected topic** — it cannot silently drop or invent one.
- **Every session needs** a topic, an activity and a learning objective, all
  non-empty after stripping.
- **Citations are pinned**: each `source_id` must be a card the professor chose,
  and its URL must equal that card's stored URL exactly.
- **Nothing goes uncited**: every selected topic must appear in the references.

### You.com — evidence retrieval
`backend/integrations/you_search.py`

- **30-second timeout** on the request.
- **Only `http`/`https` results** with a title and body text are accepted.
- **No evidence, no cards** — an empty result raises rather than letting the
  agent proceed unsourced.

### Daytona — sandboxed rendering
`backend/rendering/`

- **All source text is HTML-escaped** — model output and scraped web text reach
  the renderer as data, never markup. Covered by an adversarial-input test.
- **Only `http`/`https` citation links survive**; `javascript:` and `data:` URLs
  are dropped rather than rendered.
- **Standard library only** inside the sandbox, so nothing is installed at
  runtime and the sandbox needs no outbound network access.
- **Explicit exec timeout** (Daytona's own default is 10s, too tight for a cold
  sandbox) and the **sandbox is deleted in a `finally` block** so a failure
  can't leak one.
- **Non-zero exit or empty output is an error**, not a silently blank document.

### One — delivery
`backend/integrations/one_publish.py`

- **Publication keys are pattern-checked** before being used in a filename.
- **The CLI is invoked as an argument list, never a shell string** — a title
  containing `; rm -rf /` stays a title. Covered by a test.
- **90-second timeout**, and a non-zero exit is surfaced rather than assumed sent.
- **An unreadable receipt fails loudly** instead of reporting a success it can't
  evidence.

### State and API
`backend/storage/`, `backend/schemas.py`

- **One committed selection per search**, enforced by a `UNIQUE` constraint.
  Re-submitting the same set returns the saved response; a different set is
  rejected with `409`.
- **Selection, outline, counts and version commit atomically** inside a single
  `BEGIN IMMEDIATE` transaction, and roll back together on any error.
- **Duplicate card IDs cannot inflate the counts** — IDs are normalised to a
  sorted unique set first.
- **Selected cards must belong to that search session.**
- **The approved outline is frozen** and re-read at publish time, so what was
  approved and what is delivered cannot drift apart.
- **Schema-level limits** on every request and response: subject and level
  length, exactly four cards, enumerated styles and statuses, URLs validated.
- `PRAGMA foreign_keys`, `busy_timeout` and WAL journaling are all set on connect.

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

Copy `.env.example` to `.env` first. Then, in two terminals:

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
set -a; . ./.env; set +a
.venv/bin/uvicorn backend.main:app --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000.

Use **Python 3.11**. CrewAI and the Daytona SDK do not reliably have wheels for
3.14, which is the system default on some machines.

### Modes

Research and delivery are switched independently, because they have separate
credentials — you can publish for real while research runs on deterministic
cards.

| Variable | Values | Effect |
| --- | --- | --- |
| `CURRICULUMAI_MODE` | `fixture` (default) / `live` | `live` uses You.com + CrewAI. `fixture` serves the deterministic cards in `contracts/`. |
| `CURRICULUMAI_PUBLISH_MODE` | `reserve` (default) / `live` | `live` renders in Daytona and delivers through One. `reserve` just records the attempt. |

Two escape hatches cover the demo's degradation ladder:
`CURRICULUMAI_RENDER_LOCAL=1` renders without a sandbox, and
`CURRICULUMAI_PUBLISH_LOCAL=1` writes the artifact to `artifacts/` rather than
sending it.

### Tests

```bash
.venv/bin/python -m pytest tests/ -q --ignore=tests/test_live_workflow.py
```

46 pass. `test_live_workflow.py` is excluded because it calls You.com and the
LLM provider for real; run it once keys are in `.env`.

## Layout

```
contracts/                        frozen request/response shapes, shared
backend/main.py                   the three HTTP routes                    (B)
backend/schemas.py                Pydantic wire contracts                  (B)
backend/agents/workflow.py        CrewAI researcher + writer               (B)
backend/integrations/you_search.py  You.com research                       (B)
backend/learning/                 preference counts and deterministic rank (B)
backend/storage/                  SQLite schema and repository             (B)
backend/rendering/                outline -> HTML, executed in Daytona     (A)
backend/integrations/one_publish.py  delivery through One                  (A)
frontend/                         the single screen                        (A)
tests/                            rendering, publishing, api, learning, storage
```

The two lanes were built independently and merged here.
`CurriculumAI-Two-Person-Build-Plan.md` is the operating document: phases,
gates, the A/B adapter boundary, and the degradation ladder.
`Person-B-Action-Plan.md` and `backend/SETUP.md` cover the backend lane.

## Status

**Both lanes are integrated and the full path runs end to end.** Verified in a
browser against the real backend: search → select two case studies → search
again, with the ranking moving and per-card rank deltas of ↑2/↑2/↓2/↓2 exactly
matching `contracts/mixed-style-ranking.json` → **Approve & publish** → rendered
in a live Daytona sandbox → delivered through One → arrives in the inbox. The
approved outline survives the second search rather than being replaced by it.

46 tests pass and the frontend builds clean.

Measured: ~2.2 s for Daytona to create a sandbox, render and return the HTML,
then ~0.8 s to deliver. The sandbox output is byte-identical to a local render,
which is what proves the renderer is deterministic rather than merely working.

Google Drive was the intended publish destination and was ruled out at the
readiness gate — One exposes only Drive's metadata endpoint, which creates a
named file containing nothing. `contracts/one_action.md` records the evidence,
the working invocation and the measured timings.

Outstanding: live research mode needs `YOUCOM_API_KEY` and `ANTHROPIC_API_KEY`
(everything above ran with `CURRICULUMAI_MODE=fixture` and
`CURRICULUMAI_PUBLISH_MODE=live`), then the video, description and submission.
