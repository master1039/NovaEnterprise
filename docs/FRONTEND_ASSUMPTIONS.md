# NovaEnterprise Frontend Assumptions

## Status

The frontend is planned for Phases 13 and 14 and does not exist in Phase 1.
This file records the assumptions frontend work may safely use. It is a design
agreement, not evidence that the corresponding backend routes are implemented.

## Runtime assumptions

| Concern | Assumption |
|---|---|
| Local frontend origin | `http://localhost:3001` once the frontend exists |
| Local backend origin | `http://localhost:8001` |
| Business API base | `/api/v1` |
| Current Phase 1 checks | `GET /` and `GET /health/live` |
| Authentication | Bearer token after Phase 3 |
| Polling interval | Approximately 2 seconds while research is running |
| Date/time rendering | Parse ISO 8601; display in the user's locale |
| IDs | Opaque strings; never derive labels or ordering from them |

No process currently listens on port 3001. The backend command starts port
8001 only when a developer runs it.

## Research lifecycle

1. Submit a question to `POST /api/v1/research`.
2. Expect `202`, `session_id`, and `status: running` immediately.
3. Navigate to the session route without waiting for the workflow.
4. Poll `GET /api/v1/research/{id}` about every 2 seconds.
5. Fetch or refresh `/events` to show safe progress details.
6. Stop normal polling on `completed`, `failed`, or `partial`.
7. Offer a manual retry for transient network failures; do not create a second
   research session automatically.

The client must not assume a fixed number of workflow nodes. It renders the
progress object and events returned by the server.

## Status presentation

| API status | Frontend behavior |
|---|---|
| `running` | Show progress and continue polling |
| `completed` | Show answer, evidence, and citations; stop polling |
| `partial` | Show supported results plus missing-evidence warnings |
| `failed` | Show a safe failure message and available diagnostic events |

An unavailable graph store may produce partial research. The UI must not erase
successful SQL or document evidence merely because one retrieval path failed.

## Evidence and citations

- Render citation markers such as `[1]` as links to matching evidence.
- Keep evidence identifiers stable while a session is open.
- Show source type, title or record label, locator, and available metadata.
- Distinguish document, SQL, and graph evidence visually without changing its
  meaning.
- If a citation cannot be resolved, show it as invalid rather than guessing.
- Never render raw untrusted HTML from documents or tool responses.

## Events and observability

The UI may display:

- workflow step names and completion state;
- selected retrieval strategies;
- safe, read-only SQL or Cypher text;
- evidence counts and identifiers;
- durations and timestamps; and
- sanitized failures or degraded dependencies.

The UI must never request or display hidden chain-of-thought, model scratchpad
content, credentials, or internal stack traces.

## Authentication and roles

- The backend is the source of truth for permissions.
- The frontend may hide unavailable actions for usability but must handle `401`
  and `403` responses for every protected request.
- Viewer, analyst, and admin navigation is based on authenticated role data,
  not on locally editable flags.
- Destructive document actions require an approval flow even for an admin.

## Error handling

Parse the shared error envelope from `docs/API_CONTRACT.md`.

- Show the safe `message` to the user.
- Use `code` for conditional UI behavior.
- Display validation `details` next to relevant fields when possible.
- For an unknown or malformed response, show a generic message and preserve the
  `X-Request-ID` for support once Phase 3 introduces it.
- Never show a raw response body that may contain sensitive information.

## API client rules

- Centralize base URL, authentication, JSON parsing, error parsing, and request
  cancellation in one typed client.
- Keep request and response types aligned with the API contract.
- Cancel polling when the user leaves a research session page.
- Do not retry non-idempotent requests unless the contract explicitly permits it.
- Ignore unknown response fields so additive backend changes remain compatible.
- Treat network timeouts as unknown outcome, not automatic proof of failure.

## Accessibility and degraded states

- Do not rely on color alone for status or evidence type.
- Progress updates should be readable by assistive technology without stealing
  focus every two seconds.
- Every interactive control needs a keyboard path and accessible label.
- Loading, empty, partial, failed, and unauthorized states are separate states.
- The frontend must remain navigable when optional stores are degraded.

## Contract-change checklist

Any PR that changes a route or payload updates together:

1. `docs/API_CONTRACT.md`;
2. backend request/response schemas;
3. backend contract tests;
4. frontend client types; and
5. affected frontend tests and fixtures.

Until a route is implemented and covered by tests, label it as planned in code
reviews, demos, and recruiter explanations.
