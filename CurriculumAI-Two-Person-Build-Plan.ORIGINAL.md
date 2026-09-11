# CurriculumAI — two-person execution plan

This is a file-only review and proposed execution revision of `CurriculumAI-MVP-Action-Plan.md`. The original file is unchanged. No service access or application execution was tested. The source plan supplies the requirements; this review does not re-evaluate external event rules.

## Decision

Keep the MVP and stack. Make the two implementation lanes independent through fixed contracts, fixtures, and exclusive file ownership. The runtime phases necessarily depend on each other: search → confirmed selection and saved outline → updated preferences → subsequent recommendations; saved outline → rendering → publishing.

“Two people” means two developers. The application continues to have one demo professor, shared preferences, and no login. Separate application users and isolated profiles remain deferred.

Use the source budget: **160 minutes for implementation and verification, then 50 minutes for submission; 210 minutes total.** The clock starts when implementation begins. This is a conditional target, not demonstrated delivery time. If only 120 minutes of total build time are available, the current file does not establish that the required scope fits.

## Flaws to address in the existing plan

| Source section | Gap | Execution correction |
| --- | --- | --- |
| 3–4 | B owns the API, database, agents, search, learning, Daytona, and final publishing integration. | Move Daytona and the complete rendering/publishing adapter work to A. Keep all database writes and HTTP routes with B. |
| 4 | Learning starts at minute 100; the first complete live flow is only required at 135–160. | Build selection storage and deterministic learning during 20–45. Require the first complete live flow by 100. |
| 3, 5 | Only a search fixture is named. Outline fields, errors, and publication statuses are not fully fixed. | Agree complete search, select/outline, publish, and error examples before the branches diverge. |
| 4–5 | Separate Daytona and One smoke tests do not prove their artifact formats are compatible. | Test the same tiny outline through Daytona and One, then open the returned file. |
| 5–6 | “Commit once” does not define duplicate IDs, conflicting selections, or overlapping requests. | Canonicalize selected IDs; one committed selection per session; save outline and preference update in one transaction. |
| 5 | Successful publish replay is covered, but lost responses and concurrent publishing are not. | Persist one attempt per selection, prevent overlapping calls, and block blind retries when the external result is unknown. |
| 6, 8–9 | Counts are defined, but the ranking rule and a repeatable demonstration of changed ranking are not. | Freeze priors and stable ranking; test mixed-style candidates and both skewed and balanced selections. |
| 5, 9 | A second search occurs before publishing, without explicit preservation of the first outline. | Preserve the selected outline and its selection ID separately from current recommendations. |
| 4, 8 | Clean setup and timing problems can first appear during submission. | Check a clean checkout and measure a complete run before feature freeze. |

These are gaps in the written plan, not findings from running code.

## Scope to preserve

- Next.js screen; FastAPI backend; SQLite on persistent local storage.
- Four evidence-supported topic cards with the original teaching-style values: `theory`, `case_study`, `project`.
- Explicit **Use these topics**, durable selection history, saved style preferences, and profile-aware subsequent search.
- Two CrewAI roles, live You.com search, fixed Daytona rendering, and real publishing through One.
- Short outline preview followed by **Approve & publish**.
- The repository, README, video, description, and submission deliverables already specified in the source.
- All existing deferrals remain: accounts, student portal, RAG, vector databases, additional agents, extra destinations, conversational editing, full-semester planning, and PDF polish.

## Exclusive ownership

| Owner | Files and responsibilities |
| --- | --- |
| **A — interface and artifact delivery** | `frontend/`; its package manifest and lockfile; `backend/rendering/`; `backend/integrations/one_publish.py`; `tests/test_rendering.py`; `tests/test_one_publish.py`; root `README.md`; video, description, final submission. |
| **B — application state and curriculum workflow** | `backend/main.py`; `backend/schemas.py`; `backend/agents/`; `backend/integrations/you_search.py`; `backend/learning/`; `backend/storage/`; backend dependency manifest and lockfile; `.env.example`; `.gitignore`; API/state/learning tests; `backend/SETUP.md`. |
| **B writes; both agree** | `contracts/`, including every shared input/output fixture and error example. B also owns merges into the integration branch. |

A supplies backend dependency and environment-variable requirements to B; A does not independently modify B's shared manifests. A links B's setup instructions from the root README. Give every additional file one owner before creating it.

Each developer uses a separate clone or worktree and a separate branch. Do not switch branches in one shared working directory. Both start from the same contract commit. At checkpoints, B merges the two branches into the integration branch, runs the agreed check with A, and both update from that integrated state. Do not exchange or commit secrets or local databases.

## Phases and independent work

| Phase / minutes | Entry dependency | A builds and verifies | B builds and verifies | Exit gate / handoff |
| --- | --- | --- | --- | --- |
| **1. Readiness and contracts / 0–20** | Existing accounts and the source plan. | Verify One action, Daytona rendering, and one tiny artifact round trip; establish format. | Verify You.com and CrewAI/LLM execution; create schemas, fixtures, dependency setup. | Same-artifact Daytona → One round trip opens successfully; You.com and CrewAI/LLM calls succeed. Agree subject/level, format/destination, contracts, ownership, and fixed identity. Resolve the source plan's stated organizer blocker. |
| **2. Independent foundations / 20–45** | Shared contract commit and fixtures. | Build basic cards/selection with preview and status placeholders against fixtures. Turn the artifact smoke test into callable rendering/publishing adapters. | Scaffold all three HTTP routes and storage tables. Make fixture-backed search/select, transactional selection, and deterministic learning functional; publish may still return a development fixture. | First merge: UI calls real backend routes; a fixture selection persists once. A's delivery adapters work from the saved-outline fixture without the research pipeline. |
| **3. Real services / 45–75** | Stable fixtures, backend foundation, and working artifact route. | Finish renderer/publisher behavior, content fidelity, progress/error states, and external link UI. | Replace fixture research and outline generation with You.com plus both CrewAI roles; validate source support; apply preference snapshot and deterministic ranking. | Each lane works independently: real supported cards/outline from B; saved-outline fixture rendered and published by A. |
| **4. Complete live integration / 75–100** | Both lane contracts pass independently. | Connect **Approve & publish** and next-search UI while preserving the saved outline. | Connect saved-outline lookup and publication state to A's adapters; integrate actual profile-aware next search. | Live search → select → saved learning/outline → next search → publish original preview → open artifact. First complete live run by 100. |
| **5. Correctness and recovery / 100–135** | One complete live run. | Verify no stale outline, pending-action controls, error recovery, citations, and external content. Draft README/demo material. | Verify learning, duplicate/conflicting requests, uncertain publication recovery, database persistence, and second complete run. Start clean-checkout setup verification. | Second live run plus the focused acceptance checks below pass. Merge at 135. |
| **6. Stabilize and freeze / 135–160** | Integrated build and targeted test results. | Fix owned blockers, rehearse, and capture a successful backup recording. | Complete clean setup check, dependency locks, runtime instructions, secret exclusion, and remaining owned fixes. | Passing commit identified; complete-run duration recorded; all required functionality works. Feature freeze at 160. |
| **7. Submission / 160–210** | Frozen working build and backup recording. | Record/upload final video; finish description and README; submit once and verify links. | Final setup/repository verification and submission-blocking fixes only. | All submission deliverables from the source plan complete. |

The first 20 minutes are a readiness gate. If a required connection or compatible artifact action cannot be demonstrated, report that blocker immediately; the unchanged delivery estimate is no longer supported. Fixture development may continue in parallel, but it must not be represented as completed live integration. Keep the final 50 minutes reserved. Minute 100 is a target checkpoint conditional on readiness. Both lanes carry substantial work; elapsed time alone never satisfies a phase gate or makes a build ready to freeze.

## Contracts to freeze during phase 1

Keep the original three endpoints. B supplies valid, invalid, and replay examples; A builds against those examples. Freeze names and types, not merely a list of fields.

### Shared data

- IDs are strings. `preference_version` is a nonnegative integer. Start the demo profile at version 0.
- Topic cards retain `id`, `title`, `description`, `teaching_style`, `source_url`, and `why_suggested` from the original plan.
- Descriptions explicitly describe the proposed activity so that the style label is meaningful.
- Store the evidence text, source IDs/URLs, and original candidate order internally with the session. The UI need not expose the complete evidence record.
- `preference_summary` and `learned_change` are factual strings derived from saved state. Neither requires another LLM call.

Use this exact nested outline shape:

```json
{
  "title": "Short module title",
  "sessions": [
    {
      "topic": "Selected topic",
      "activity": "Concrete teaching activity",
      "learning_objective": "What the learner should be able to do",
      "source_references": [
        {"source_id": "saved-source-id", "url": "https://example.org/evidence"}
      ]
    }
  ]
}
```

The example URL is fixture data, not evidence. Every live source reference must match the stored evidence associated with the selected cards. Use one teaching session per unique selected card, in the saved card-display order; normalized ID ordering is for request comparison only. The generated outline is immutable after commitment. Preview and rendering use that same stored JSON; publishing never regenerates it.

### Endpoint behavior

| Endpoint | Frozen behavior |
| --- | --- |
| `POST /api/search` | Original request and response fields. Read counts and version together at request start; use that same snapshot for research, ranking, summary, and saved session. Return four valid cards or an explicit error. |
| `POST /api/select` | Original request and response fields, with the outline shape above and string `learned_change`. Treat selected IDs as a sorted unique set; validate session membership and nonempty selection. Same committed set returns its original saved response. A different set on that session returns HTTP 409 `selection_already_committed`. |
| `POST /api/publish` | Input remains `selection_id`. `status` is `publishing`, `published`, `failed`, or `unknown`; external ID and URL are nullable until success. Return HTTP 200 for published, 202 for an existing in-progress attempt, HTTP 502 for a known delivery failure, and HTTP 409 `publication_unknown` for an unresolved external outcome. An unknown result must not invite automatic retry. |

Every error includes `error.code`, `error.message`, and `error.retryable`. Preserve that object even if a publication error also includes its `status` and nullable external fields. Freeze concrete examples for invalid input, no usable evidence, committed-selection conflict, provider failure, and publication uncertainty. HTTP and UI behavior must match the examples.

Keep synchronous requests and synchronous adapter functions for this MVP; B uses synchronous FastAPI handlers for blocking service work. During phase 1, record numeric provider/total timeouts and one bounded retry policy based on measured service calls. Pending UI controls prevent accidental repeated actions; database rules remain responsible for correctness. For `publishing` or `unknown`, offer **Check publication status**, which repeats the same POST with the same selection ID. That branch only reads the saved result or attempts reconciliation; it never starts another external creation. No background queue or new endpoint is required.

### A/B backend boundary

Use separate rendering and external-write calls so B can track when the irreversible external step begins:

```text
A: render_outline(selection_id, saved_outline)
   -> {title, content_bytes, content_type}

A: publish_artifact(publication_key, title, content_bytes, content_type)
   -> {external_file_id, external_url}

A: reconcile_publication(publication_key)
   -> published receipt | confirmed absent | unknown
```

These are internal Python calls, not additional HTTP endpoints. B defines their shared types; A implements the adapters. A's adapters do not write SQLite or update preferences. B owns saved-outline lookup, durable publication attempts, response mapping, and the routes.

The reconciliation capability must be established for the chosen One action. If lookup cannot reliably establish whether creation happened, retain `unknown` and document manual destination inspection for the demo; do not invent an unsupported provider API or assume absence from a search proves failure.

Provide these fixtures under `contracts/`: search request/response, select request/response, saved outline, publication success/pending/unknown responses, common errors, and a mixed-style ranking example. Fixture mode is for development/tests only; the accepted demo uses the real services.

## State rules that prevent integration surprises

1. **Selection:** one committed selection per session, enforced by a database constraint. Generate and validate the outline before opening a short transaction; recheck commitment inside it. Save the selection, outline, style-count increments, profile version, and original response atomically. Duplicate IDs cannot inflate counts; overlapping requests cannot commit twice.
2. **Publishing:** one publication record per selection, with a stable key derived from the selection ID. B claims the attempt before work begins and marks external dispatch before calling One. A rendering failure is distinguishable from an external write whose result is unknown. Never hold a SQLite transaction open during network calls.
3. **Uncertainty:** an external timeout, process crash after dispatch, or failure to save a successful receipt requires reconciliation. An old in-progress record is not permission to create another file. A known pre-dispatch failure can be retried; a confirmed success returns the saved receipt.
4. **Approval:** **Use these topics** commits preferences and generates the saved preview. **Approve & publish** approves that displayed immutable outline. No editing or extra approval subsystem is added.
5. **Screen state:** current recommendations and saved selection/outline are separate. New search does not erase the preview. A later committed selection deliberately replaces the selected preview. On errors preserve useful existing state.
6. **Refresh:** for the smallest MVP, refreshing starts a new screen/search while stored preferences persist. Resuming old outlines after browser refresh is deferred; a backend restart must still preserve stored data and allow a new workflow. This avoids silently requiring a fourth endpoint.

## Learning rule and truthful demo

- Start counts at `(theory=1, case_study=1, project=1)`.
- Add one count per unique selected card's style, exactly once per committed selection.
- Weight each style by its count divided by total counts. Increment profile version once per commitment.
- Validate subject relevance, level, and evidence first. Order eligible cards by descending style weight, breaking ties by the saved original candidate order. Apply the same profile snapshot to researcher instructions.
- For the demo, use four supported cards spanning the three styles. If case-study cards are already first, a fresh selection may correctly produce no visible movement; the acceptance fixture must make the intended ordering change observable.
- Example fixture baseline: `[theory, project, case_study, case_study]`. Selecting the two case-study cards changes counts to `(1,3,1)` and weights to `(0.2,0.6,0.2)`, moving the case-study cards first under the fixed ranking rule.
- Selecting one of each style produces `(2,2,2)`, leaving weights equal. Report that honestly; do not claim every selection changes ranking.
- Save original candidates and before/after profiles for a controlled comparison. The same-candidate comparison can be a test report used in the demo; label it as reranking. A fresh live search must separately use the updated profile version.

## Acceptance checklist and owners

| Check | Owner | Required evidence |
| --- | --- | --- |
| All response/adapter fixtures match actual types. | A + B | Frontend and adapters consume the same agreed shapes without renaming. |
| Live evidence and both CrewAI roles work. | B | Actual supported cards and saved cited outline. |
| A skewed selection changes weights and controlled ranking; a balanced selection behaves honestly. | B | Deterministic checks against the fixed candidate set. |
| Duplicate IDs, repeated/overlapping identical requests, and conflicting selections behave as specified. | B | Exactly one selection/count update; conflict is rejected. |
| Saved preferences survive backend restart. | B | Second workflow uses the stored profile; no manual database edits. |
| Daytona-produced artifact is the artifact published through One. | A | Opened external content matches saved preview and citations. |
| Overlapping/repeated publishing does not blindly recreate; a lost external response becomes unknown. | B with A's adapter test | Focused simulated failure check plus real successful publication readback. |
| A second search preserves the correct saved preview and publishing target. | A | Full UI journey with distinct session and selection identities. |
| Source content remains data; renderer escapes text and accepts only suitable web citation links. | A + B | One adversarial-text/markup fixture remains inert; source membership is validated. |
| A complete first run and a restart-followed-by-second run pass. | A + B | Real service evidence, recorded durations, no fixture substitution. |
| Clean setup works before minute 160. | B | Runtime versions, lockfiles, database initialization and connection setup documented. |
| Submission is complete. | A submits; B verifies | Source plan's repository/video/description links checked. |

## Freeze rules

At minute 20, freeze scope, shared data shapes, one destination/format, and ownership once the readiness gate passes. At minute 160, identify the passing commit, dependency locks, model configuration, demo subject, and acceptance evidence.

Until the working version is complete, add no features or extra infrastructure. Fix defects that block the agreed behavior within the assigned files. Coordinate any unavoidable contract correction immediately rather than changing shared fields silently. A review can reduce rework; passing live integration checks are what establish that the build works.
