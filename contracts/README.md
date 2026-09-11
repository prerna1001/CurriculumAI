# CurriculumAI shared contracts

These fixtures are the frozen wire contracts between the frontend, backend, and publishing adapters. They use deterministic demo data only; source URLs are placeholders and must be replaced by live, evidence-supported URLs at runtime.

The server generates `session_id` and `selection_id`. The client sends the returned `session_id` to `/api/select`, then sends the returned `selection_id` to `/api/publish`.

Every error response uses the envelope in `errors/`. Person B owns updates to this directory; both developers must agree before a contract changes.
