# V2 Support and Troubleshooting

## Run did not start

1. Check the supervisor `/health` response and confirm it is JSON.
2. Check the operator registration with `GET /v2/connectors`; a connector must be registered, enabled, and capability-verified before `POST /v2/runs` succeeds.
3. Confirm the supervisor service binding matches the private connector Worker name. A connector health response must identify the expected connector.
4. Review input validation and the idempotency key; a repeated key with different input is rejected.

## Run is incomplete or failed

- Inspect `GET /v2/runs/{id}`, D1 work-item state, Queue retries/DLQ, K2 events, and the connector's R2 artifact path.
- A health check, HTTP 200, or completed workflow is not proof that distinct source records were captured. Verify record IDs, parser coverage, source artifacts, and known pagination/access limitations.
- A JudyRecords empty search result is not proof that no records exist. Term-based search discovery is unverified; test a concrete results page and direct record separately.
- A one-profile Truth Social sample does not establish timeline pagination or historical completeness.
- Never delete R2 artifacts or reset D1 to roll back. Pause new runs, inspect leases and queued work, then use the documented recovery procedure in [V2 connector operations](V2_CONNECTORS.md).

## Access and local development

- `V2_SUPERVISOR_TOKEN` protects operator routes; `V2_CONNECTOR_TOKEN` protects private supervisor-to-connector calls. Do not paste either value into logs or chat.
- Spider and Webshare values come from the connector's Secrets Store bindings. Binding/permission errors require checking the Worker binding and account permission—not putting the key in a request body.
- Requests to a `workers.dev` endpoint may be blocked when sent with a generic Python client signature. The approved run helper uses a descriptive `HarvyPlatform/2.0` user-agent; do not impersonate a browser.
- Wrangler remote development does not support the production Queue binding. A local preview is not an end-to-end Queue test.

## Reporting an issue

Include the run ID, connector ID, UTC time, request path, response status, and sanitized error/trace identifier. Do not include tokens, provider secrets, private artifact contents, or logged-in account cookies.
