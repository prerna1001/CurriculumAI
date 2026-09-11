# One destination — fill in at the phase-1 readiness gate

**Status: NOT YET RESOLVED.** This is unresolved dependency U3/U4 from the review.
Nothing in lane A's publish path is real until this file is filled in.

## Why this blocks

One is a *passthrough*. It proxies to the destination platform's own API with
managed auth, so "can we upload an artifact" really means "does the destination
platform's API accept this content here." Binary/file input to One actions is
not documented, and there is no Python SDK — the FastAPI backend shells out to
the Node CLI (see `backend/integrations/one_publish.py`).

## Steps

```bash
one init            # global scope, shared team account
one login
one add <platform>  # opens a browser for OAuth
one list            # confirm the connection, note the connectionKey

one actions search <platform> "create document"
one actions knowledge <platform> <actionId>   # READ THIS BEFORE CHOOSING
```

## Record here

| Field | Value |
| --- | --- |
| Platform | _e.g. googledrive_ |
| Action ID | |
| Connection key | |
| Accepts raw bytes? | yes / no — **if no, `Artifact.payload` is used instead of `content_bytes`** |
| Content type sent | _e.g. text/html_ |
| Receipt: id field | _dotted path, goes in `ONE_RESULT_ID_PATH`_ |
| Receipt: url field | _dotted path, goes in `ONE_RESULT_URL_PATH`_ |

## Exact working invocation

Paste the command that actually succeeded, verbatim:

```bash
# one --agent actions execute ...
```

## Raw response

Paste one real success response, so the receipt paths above can be pinned:

```json
```
