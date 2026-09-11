# CurriculumAI shared contracts

These fixtures are the frozen wire contracts between the frontend, the backend
and the publishing adapters. They use deterministic demo data only — source URLs
here are placeholders, and live runs must replace them with real,
evidence-supported URLs.

The server generates `session_id` and `selection_id`. The client sends the
returned `session_id` to `/api/select`, then the returned `selection_id` to
`/api/publish`.

Every error response uses the envelope in `errors/`. **Person B owns updates to
this directory; both developers must agree before a contract changes.**

| File | What it fixes |
| --- | --- |
| `search-request.json` / `search-response.json` | `POST /api/search`. The response is also the demo baseline: candidate order `[theory, project, case_study, case_study]`. |
| `select-request.json` / `select-response.json` | `POST /api/select`, including the immutable outline shape. |
| `publish-response-*.json` | `POST /api/publish` for `published`, `publishing` and `failed`. |
| `errors/*.json` | One concrete example per frozen error code. |
| `mixed-style-ranking.json` | Expected card order before and after the worked example. This is the deterministic learning check. |
| `one_action.md` | The resolved One destination, with the evidence and working invocation from the readiness gate. |

Card `id` values are stable across fixtures on purpose: `card_1` … `card_4`.

Lane A originally kept a parallel set of these files under dotted names
(`search.response.json`) while the backend did not yet exist. Those were removed
at integration — this hyphenated set is canonical.
