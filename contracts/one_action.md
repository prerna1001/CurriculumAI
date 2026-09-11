# One destination — RESOLVED at the phase-1 readiness gate

**Status: PASSING.** A rendered artifact has gone Daytona → One → inbox, and the
receipt was read back correctly. Unresolved dependencies U3 and U4 are closed.

## Destination: Gmail, not Google Drive

Drive was the intended destination and was ruled out during the gate.

One's Drive catalogue exposes `POST /drive/v3/files` ("Create a Drive File"),
which is **metadata-only**. Its own action knowledge says:

> Do not send uploaded binary file content to
> `https://www.googleapis.com/drive/v3/files`; use an upload URI for file content.

Google's upload URIs (`/upload/drive/v3/files`, `/resumable/upload/drive/v3/files`)
are **not exposed as One actions** — searched under "create file", "upload",
"simple upload media", "resumable upload". So publishing through Drive would
produce a correctly named file containing nothing.

Gmail's Send Email action accepts `isHtml: true` and sends HTML as written. Our
artifact is already a standalone HTML document, so it arrives intact with no
multipart upload involved. `google-drive` is still connected and can be used
later if One adds an upload action.

## Values (copy into .env)

| Field | Value |
| --- | --- |
| Platform | `gmail` |
| Action ID | `conn_mod_def::GGXAjWkZO8U::uMc1LQIHTTKzeMm3rLL5gQ` |
| Action | Send Email — `POST /v1/gmail/send-email` |
| Connection key | Account-specific — **not committed.** Run `one list` and copy your own into `.env`. Format: `live::gmail::default::<32 hex>` |
| Accepts raw bytes? | **No.** JSON body via `-d`. The HTML goes in `body` with `isHtml: true`. |
| Content type sent | `text/html`, inline in the message body |
| Receipt: id path | `response.email.messageId` |
| Receipt: url | No URL returned. Built from `ONE_RESULT_URL_TEMPLATE`. |

`ONE_RECIPIENT` sets the destination address — it is not part of the action id.

## Working invocation

One's CLI guidance is explicit that path and query parameters must **not** go in
the `-d` body. This action has neither, so everything is body:

```bash
one --agent actions execute gmail \
  conn_mod_def::GGXAjWkZO8U::uMc1LQIHTTKzeMm3rLL5gQ \
  "$ONE_CONNECTION_KEY" \
  -d '{"connectionKey":"'"$ONE_CONNECTION_KEY"'",
       "to":"professor@example.org",
       "subject":"Diagnosing model failure in practice",
       "body":"<!doctype html>…",
       "isHtml":true}'
```

`backend/integrations/one_publish.py` builds exactly this, as an argument list
rather than a shell string.

## Real success response (trimmed)

The shape that pinned `ONE_RESULT_ID_PATH`. Note the id is nested two levels
deep — a flat `id` lookup fails, which is how the first gate run failed.

```json
{
  "dryRun": false,
  "request": {
    "method": "POST",
    "url": "https://api.withone.ai/v1/passthrough/v1/gmail/send-email"
  },
  "response": {
    "email": {
      "labelIds": ["SENT"],
      "messageId": "1a091a5ef71b4730",
      "threadId": "1a091a5ef71b4730",
      "recipients": { "to": ["professor@example.org"] },
      "sent": true,
      "subject": "Diagnosing model failure in practice"
    },
    "message": "Successfully sent email … to 1 recipient"
  }
}
```

## Measured timings

| Step | Time |
| --- | --- |
| Daytona: create sandbox, upload, render, download, delete | ~2.2 s |
| One → Gmail send | ~0.8 s |

Well inside the 90 s CLI timeout and the 60 s Daytona exec timeout.

## Note for B

The Gmail connection lives in one personal One account. To run the publish path
from your own machine you need either your own `one add gmail`, or access to the
same account. Either way, run `one list` and put your own `ONE_CONNECTION_KEY`
in your local `.env` — connection keys are account-specific and deliberately
kept out of the repository.
