# contracts/

Frozen shared shapes. **Owner: B writes, both agree** (see the build plan).

These files were transcribed from the frozen contract section of
`CurriculumAI-Two-Person-Build-Plan.md` so that lane A had something to build
against before B's backend existed. They are **reconstructed, not recovered** —
the original `CurriculumAI-MVP-Action-Plan.md` was not available.

**B: pull this folder rather than recreating it.** If you disagree with a shape,
change it here and tell A immediately — do not change it silently in
`backend/schemas.py`.

| File | What it fixes |
| --- | --- |
| `search.request.json` / `search.response.json` | `POST /api/search`. The response is also the lane-A fixture baseline: candidate order `[theory, project, case_study, case_study]`. |
| `select.request.json` / `select.response.json` | `POST /api/select`, including the immutable outline shape. |
| `publish.request.json` / `publish.response.*.json` | `POST /api/publish` for `published` (200) and `publishing` (202). |
| `errors.json` | The error envelope plus one concrete example per frozen error code. |
| `ranking_after_case_study.json` | Expected card order after the worked example in the plan. This is the deterministic learning check. |
| `one_action.md` | The chosen One destination — fill in at the phase-1 gate. |

Card `id` values are stable across fixtures on purpose: `card_1` … `card_4`.
