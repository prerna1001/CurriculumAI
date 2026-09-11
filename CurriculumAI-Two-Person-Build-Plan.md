# CurriculumAI — two-person execution plan (rev. 2)

Revision of the plan previously in this file (preserved as `CurriculumAI-Two-Person-Build-Plan.ORIGINAL.md`). Changes applied: contracts written out literally instead of referencing the absent `CurriculumAI-MVP-Action-Plan.md`; setup moved to pre-work; the first live gate split so publishing cannot block the learning demo; the publication state machine reduced; learning moved into the agent layer.

**Contracts below are reconstructed, not recovered.** The source plan is not available on either machine. Field names were derived from what the original document already fixed (card fields, the outline shape, `preference_version`, `learned_change`). If the source plan resurfaces and disagrees, the source wins — reconcile before minute 20.

Event theme: **self-improving and learning agents.** Every scoping decision below favours the learning loop over everything else, because that is the only thing being judged.

## Decision

Keep the MVP and stack. Make the two implementation lanes independent through fixed contracts, fixtures, and exclusive file ownership. The runtime phases necessarily depend on each other: search → confirmed selection and saved outline → updated preferences → subsequent recommendations; saved outline → rendering → publishing.

"Two people" means two developers. The application has one demo professor, shared preferences, and no login. Separate application users and isolated profiles remain deferred.

**Budget: 160 minutes implementation and verification, then 50 minutes submission.** The clock starts *after* the pre-work below is done. If the real window is 120 minutes rather than 210, the cut set in **Degradation and cuts** is mandatory, not optional — decide which budget is in force at minute 0 and say it out loud.

## Pre-work — before the clock starts

None of this is implementation and none of it may be paid for out of phase 1. Two people, expect 20–35 minutes.

- `git init`, remote created, **both** developers cloned and able to push.
- `create-next-app` scaffolded and running; Python venv created and FastAPI + CrewAI installed; `npm i -g @withone/cli`.
- `.gitignore` (excludes `.env`, `*.db`) and `.env.example` committed.
- Accounts and keys in hand on both machines: You.com, the LLM provider, Daytona, One.
- Both machines run the frontend and backend hello-world locally.

If this is not done, phase 1 is already overdrawn and every gate after it slips.

## Scope to preserve

- Next.js screen; FastAPI backend; SQLite on persistent local storage.
- Four evidence-supported topic cards with teaching-style values `theory`, `case_study`, `project`.
- Explicit **Use these topics**, durable selection history, saved style preferences, profile-aware subsequent search.
- Two CrewAI roles, live You.com search, Daytona rendering, real publishing through One.
- Short outline preview followed by **Approve & publish**.
- Repository, README, video, description, submission deliverables.
- Deferrals unchanged: accounts, student portal, RAG, vector databases, additional agents, extra destinations, conversational editing, full-semester planning, PDF polish.

## Exclusive ownership

| Owner | Files and responsibilities |
| --- | --- |
| **A — interface and artifact delivery** | `frontend/`; its package manifest and lockfile; `backend/rendering/`; `backend/integrations/one_publish.py`; `tests/test_rendering.py`; `tests/test_one_publish.py`; root `README.md`; video, description, final submission. |
| **B — application state and curriculum workflow** | `backend/main.py`; `backend/schemas.py`; `backend/agents/`; `backend/integrations/you_search.py`; `backend/learning/`; `backend/storage/`; backend dependency manifest and lockfile; `.env.example`; `.gitignore`; API/state/learning tests; `backend/SETUP.md`. |
| **B writes; both agree** | `contracts/`, including every shared fixture and error example. B owns merges into the integration branch. |

A supplies backend dependency and environment requirements to B; A does not modify B's shared manifests. Give every additional file one owner before creating it.

Separate clone or worktree per developer, separate branches, both from the same contract commit. Do not switch branches in a shared working directory. At checkpoints B merges into the integration branch, runs the agreed check with A, and both update from that state. Never commit secrets or local databases.

**At the minute-20 contract commit, A commits importable stubs** for `render_outline`, `publish_artifact` and the `Artifact`/`Receipt` types, raising `NotImplementedError`. Without these, B's routes cannot import and B is blocked.

### Shared One account

One's connection lives in an account, not a repo. Pick **one shared One account**, `one init` at **global** scope, both developers `one login` against it. Record the chosen `platform`, `actionId` and `connectionKey` in `contracts/one_action.md` (not secret). Each developer keeps `ONE_SECRET` in their own local `.env`. B needs a working connection locally too — B runs the end-to-end tests.

## Phases

| Phase / minutes | A builds and verifies | B builds and verifies | Exit gate |
| --- | --- | --- | --- |
| **1. Readiness and contracts / 0–20** | Verify One action and Daytona rendering; push one tiny artifact through **both** and open it. Commit adapter stubs. | Verify You.com and CrewAI/LLM execution; write schemas, fixtures, tables. | Same-artifact Daytona → One round trip opens successfully. You.com and CrewAI calls succeed. Subject/level, destination/format, contracts and ownership frozen. |
| **2. Independent foundations / 20–45** | Cards, selection, preview and status placeholders against fixtures. Turn the smoke test into callable adapters. | Three HTTP routes and storage tables. Fixture-backed search/select, transactional selection, deterministic learning. Publish may return a dev fixture. | First merge: UI calls real routes; a fixture selection persists once; A's adapters work from the saved-outline fixture. |
| **3. Real services / 45–75** | Finish renderer/publisher, content fidelity, progress/error states, external link UI. | Replace fixture research with You.com plus both CrewAI roles; `ProfileContext` into both agents; preference snapshot and deterministic ranking. | Each lane works independently: real supported cards and outline from B; saved-outline fixture rendered and published by A. |
| **4a. Learning loop live / 75–85** | Next-search UI preserving the saved outline; before/after rank display. | Profile-aware second search wired end to end. | **Live: search → select → learning → second search with visibly changed ranking. This is the judged path and it is not allowed to slip.** |
| **4b. Publishing live / 85–110** | Connect **Approve & publish**. | Saved-outline lookup and publication state into A's adapters. | Live publish of the original preview; artifact opens externally. **Cuttable — if not working by 110, fall to degradation tier 2 and stop spending time here.** |
| **5. Correctness and recovery / 110–135** | No stale outline, pending controls, error recovery, citations. Draft README and demo material. | Learning correctness, duplicate/conflicting requests, restart persistence, second complete run. | Second live run plus the acceptance checks pass. Merge at 135. |
| **6. Stabilize and freeze / 135–160** | Fix owned blockers, rehearse, capture the backup recording. | Fresh-venv install check, dependency locks, runtime instructions, secret exclusion. | Passing commit identified; run duration recorded. Feature freeze at 160. |
| **7. Submission / 160–210** | Record and upload the final video; finish description and README; submit once and verify links. | Final repository verification and submission-blocking fixes only. | All deliverables complete. |

The first 20 minutes are a readiness gate. If a required connection cannot be demonstrated, say so immediately — the delivery estimate no longer holds. Fixture work may continue in parallel but must never be reported as live integration. Elapsed time alone never satisfies a gate.

## Data model

Seven tables. B owns all writes.

```sql
profile(id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL DEFAULT 0)

preference_count(dimension TEXT, value TEXT, count INTEGER NOT NULL,
                 PRIMARY KEY (dimension, value))
-- seeded: ('teaching_style','theory',1), ('teaching_style','case_study',1),
--         ('teaching_style','project',1)

session(id TEXT PRIMARY KEY, subject TEXT, level TEXT,
        profile_version_at_search INTEGER, created_at TEXT)

candidate(id TEXT PRIMARY KEY, session_id TEXT, rank_order INTEGER,
          title TEXT, description TEXT, teaching_style TEXT,
          source_url TEXT, why_suggested TEXT, evidence_text TEXT)

selection(id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
          outline_json TEXT, response_json TEXT, created_at TEXT)

publication(selection_id TEXT PRIMARY KEY, status TEXT,
            external_id TEXT, external_url TEXT, created_at TEXT)

search_cache(subject TEXT, level TEXT, profile_version INTEGER,
             response_json TEXT, PRIMARY KEY (subject, level, profile_version))
```

`session.id` and `selection.id` are **server-generated**; the client echoes `session_id` back on select. `profile` is a singleton row — there is no login. `candidate.rank_order` preserves the original pre-ranking order and is what makes a controlled before/after comparison provable.

At connection setup: `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`. Without these, the overlapping-request test in the acceptance list fails with `database is locked` — a self-inflicted debugging session.

**`search_cache` is not an optimisation, it is demo infrastructure.** A search costs 30–90 seconds and real credits; you will run the same subject many times during rehearsal and recording. Keying on `profile_version` means v0 and v1 of the same subject both persist, giving you two stored, diffable rows as evidence of learning.

## Contracts frozen at minute 20

Three endpoints. Every example below goes in `contracts/` as a literal file.

### POST /api/search

```json
// request
{ "subject": "Introduction to Machine Learning", "level": "undergraduate" }

// 200 response
{
  "session_id": "sess_7f3a",
  "profile_version": 1,
  "preference_summary": "Prefers case_study (0.60), then theory (0.20) and project (0.20).",
  "cards": [
    {
      "id": "card_1",
      "title": "Bias-variance tradeoff through a hiring-model audit",
      "description": "Students audit a real hiring model and diagnose where error comes from.",
      "teaching_style": "case_study",
      "source_url": "https://example.org/evidence",
      "why_suggested": "Matches your recorded preference for case-study activities."
    }
  ]
}
```

Exactly four cards or an explicit error. Counts and version are read **once together at request start**; that same snapshot drives research, ranking, summary and the saved session.

### POST /api/select

```json
// request
{ "session_id": "sess_7f3a", "card_ids": ["card_2", "card_3"] }

// 200 response
{
  "selection_id": "sel_91c2",
  "profile_version": 2,
  "learned_change": "case_study weight rose from 0.33 to 0.60 after two case-study selections.",
  "preference_summary": "Prefers case_study (0.60), then theory (0.20) and project (0.20).",
  "outline": {
    "title": "Short module title",
    "sessions": [
      {
        "topic": "Selected topic",
        "activity": "Concrete teaching activity",
        "learning_objective": "What the learner should be able to do",
        "source_references": [
          { "source_id": "saved-source-id", "url": "https://example.org/evidence" }
        ]
      }
    ]
  }
}
```

`card_ids` is treated as a sorted unique set for comparison; validate session membership and non-empty selection. Re-submitting the **same** committed set returns the original saved response. A **different** set on that session returns `409 selection_already_committed`.

One outline session per unique selected card, in saved card-display order (normalised ID ordering is for request comparison only). Every `source_references` entry must match stored evidence for the selected cards — the URL above is fixture data. **The outline is immutable after commitment.** Preview, rendering and publishing all read that same stored JSON; publishing never regenerates it.

`preference_summary` and `learned_change` are factual strings derived from saved state. Neither requires another LLM call.

### POST /api/publish

```json
// request
{ "selection_id": "sel_91c2" }

// 200 published
{ "selection_id": "sel_91c2", "status": "published",
  "external_id": "1AbC", "external_url": "https://..." }

// 202 already in progress
{ "selection_id": "sel_91c2", "status": "publishing",
  "external_id": null, "external_url": null }
```

`status` is `publishing`, `published` or `failed`. `502` for a known delivery failure, carrying the error envelope plus `status` and nullable external fields.

### Error envelope

```json
{ "error": { "code": "no_usable_evidence",
             "message": "No candidate had a usable supporting source.",
             "retryable": false } }
```

Freeze concrete examples for: invalid input, no usable evidence, committed-selection conflict, provider failure. HTTP and UI behaviour must match the examples exactly.

Keep handlers and adapters synchronous — B uses synchronous FastAPI handlers so blocking service work runs in the threadpool. During phase 1, record real provider and total timeouts plus one bounded retry policy from measured calls. Pending UI controls prevent accidental repeat actions; database constraints remain responsible for correctness.

### A/B adapter boundary

Internal Python calls, not HTTP endpoints. A implements; B defines the shared types and owns every database write.

```text
A: render_outline(selection_id, saved_outline) -> Artifact
A: publish_artifact(publication_key, artifact)  -> Receipt
```

`Artifact` is a small dataclass carrying `title`, `content_type`, and **either** `content_bytes` **or** a structured `payload`. **Do not narrow this to raw bytes before phase 1 finishes.** One is a passthrough — the real shape is dictated by the destination platform's API, and that is discovered during minute 0–20 via `one actions knowledge <platform> <actionId>`. Freezing a bytes-only signature at minute 20 and then discovering the destination wants structured content breaks the contract freeze the whole plan depends on.

A's adapters never write SQLite and never touch preferences.

**Rendering:** produce **HTML or Markdown using the Python standard library only.** No PDF libraries. Daytona's outbound internet and runtime `pip install` behaviour is not documented, so a stdlib-only renderer removes that unknown entirely and makes `content_type` trivial. Set the Daytona exec timeout explicitly — the default is 10 seconds.

**Honesty note for the README:** the renderer is deterministic code we wrote, so the sandbox is isolation for untrusted *source content*, not for untrusted code. Say that plainly rather than implying more. If the build runs ahead of schedule, the stronger use is to have an agent generate the render or quiz script and execute *that* in the sandbox.

## State rules

1. **Selection.** One committed selection per session, enforced by the `UNIQUE` constraint on `selection.session_id`. Generate and validate the outline *before* opening a short transaction; recheck commitment inside it. Save selection, outline, preference increments, profile version and the original response atomically. Duplicate card IDs cannot inflate counts.
2. **Publishing.** One `publication` row per selection, keyed by `selection_id`. Insert the row with `status='publishing'` before calling One; on success update to `published` with the receipt; on a known failure update to `failed`. A repeat call returns the saved row. **Never hold a SQLite transaction open during a network call.**
3. **Approval.** **Use these topics** commits preferences and generates the saved preview. **Approve & publish** publishes that displayed immutable outline. No editing subsystem.
4. **Screen state.** Current recommendations and the saved selection/outline are separate. A new search does not erase the preview. A later committed selection deliberately replaces it. Preserve useful state on errors.
5. **Refresh.** Refreshing starts a new screen/search; stored preferences persist. Resuming old outlines after refresh is deferred. A backend restart must preserve stored data and allow a new workflow.

Dropped from the previous revision: the `unknown` publication status, `409 publication_unknown`, claim-before-dispatch and reconciliation. Those guard against a duplicate file in a single-user demo, cost 50–80 person-minutes in B's already-overloaded lane, and are worth nothing at judging. If a publish outcome is genuinely ambiguous, look in the destination folder.

## Learning — the judged path

Learning must be visible **inside the agent layer**, not only as a sort applied afterwards. A re-rank alone reads as "we sorted a list."

**Profile representation.** Generic `(dimension, value, count)` rows, not hardcoded columns — this is simpler, and it means a second dimension can be added in minutes if you run ahead. Seed `teaching_style` at `theory=1, case_study=1, project=1`.

**Update rule.** Add one count per unique selected card's style, exactly once per committed selection. Weight = count ÷ total within that dimension. Increment `profile.version` once per commitment.

**`ProfileContext`** — `{version, weights, summary}` — is built from the snapshot and passed into **three** places:

1. The **researcher** agent's task description, shaping how it constructs You.com queries.
2. The **writer** agent's task description, shaping the activities it generates.
3. The deterministic re-rank.

All three must be demonstrable. (1) and (2) are what make this a learning agent rather than a sorted list.

**Deterministic re-rank.** Validate subject relevance, level and evidence first. Order eligible cards by descending style weight, ties broken by stored `candidate.rank_order`.

**Worked example.** Baseline candidates `[theory, project, case_study, case_study]`. Selecting the two case-study cards moves counts to `(1,3,1)` and weights to `(0.2, 0.6, 0.2)`, putting case-study cards first under the fixed rule.

**Be honest about the null case.** Selecting one of each style produces `(2,2,2)` and equal weights — no visible movement. Say so; do not claim every selection changes ranking. Similarly, if case-study cards already rank first, a fresh selection may correctly produce no movement, so the acceptance fixture must make the intended change observable.

Save original candidates and before/after profiles for a controlled comparison. That comparison may be a test report shown in the demo, labelled as reranking — but a fresh **live** search must separately use the updated profile version.

**Show it in the UI.** On the second search, display a per-card before/after rank delta alongside `learned_change`. This is the single cheapest thing that converts "we store counters" into "the judge saw it learn."

## Degradation and cuts

Decide the demo tier at minute 110, not at minute 158:

1. **Full live** — search → select → learning → second search → publish → artifact opens.
2. **Live minus publish** — everything through the second search live; show the Daytona-rendered artifact locally. **This still demonstrates the entire judged criterion.**
3. **Backup recording** — captured during phase 6, used only if live services fail at the venue.

If the real budget is 120 minutes rather than 210, cut in this order: the overlapping-request test; the fresh-venv install check; phase 4b publishing entirely (fall to tier 2); the adversarial-markup fixture **last** — it is five minutes and guards a real XSS vector, since You.com content is untrusted input.

## Demo narrative — required

The video is a deliverable, and the event's only stated theme is self-improving agents. It must show, in this order and on screen:

1. Search #1 and the resulting card order.
2. The professor's selection.
3. Search #2 on a related subject, with the changed card order and `learned_change` visible.

A correct application that does not show this reads as a search wrapper. Publishing is the closing beat, not the story.

## Acceptance checklist

| Check | Owner | Required evidence |
| --- | --- | --- |
| Fixtures match actual types. | A + B | Frontend and adapters consume the agreed shapes without renaming. |
| Live evidence and both CrewAI roles work. | B | Real supported cards and a saved cited outline. |
| `ProfileContext` reaches both agents. | B | Logged researcher query and writer task showing profile influence. |
| Skewed selection changes weights and ranking; balanced selection behaves honestly. | B | Deterministic checks against the fixed candidate set. |
| Duplicate IDs and conflicting selections behave as specified. | B | Exactly one selection and count update; conflict rejected. |
| Preferences survive backend restart. | B | Second workflow uses stored profile; no manual database edits. |
| Daytona-produced artifact is the artifact published through One. | A | Opened external content matches saved preview and citations. |
| Repeat publish returns the saved receipt, never a second file. | B | One `publication` row; destination contains one artifact. |
| Second search preserves the saved preview and publishing target. | A | Full UI journey with distinct session and selection identities. |
| Source content stays data; renderer escapes text; only web citation links accepted. | A + B | One adversarial-markup fixture remains inert. |
| A complete first run and a restart-then-second run pass. | A + B | Real service evidence, recorded durations, no fixture substitution. |
| Submission complete. | A submits; B verifies | Repository, video and description links checked. |

## Freeze rules

At minute 20, freeze scope, shared data shapes, destination and format, and ownership — once the readiness gate passes. At minute 160, identify the passing commit, dependency locks, model configuration, demo subject and acceptance evidence.

Until the working version is complete, add no features and no extra infrastructure. Fix defects that block agreed behaviour within your own files. Coordinate any unavoidable contract correction immediately rather than changing shared fields silently. A plan reduces rework; only passing live integration checks establish that the build works.
