---
quick_id: 261031-export
slug: read-only-battery-history-export
date: 2026-10-31
type: quick
---

# Quick 261031-export: read-only battery-history export over HTTPS

`GET /api/export/battery-history?since=<UTC time>` on the companion returns the `device_health` rows
(`ts, battery_mv, fw_version, boot_reason, rssi`, oldest first, null battery stays null) as
`application/x-ndjson; charset=utf-8` with `Cache-Control: no-store`. It is protected by a bearer token in
`SKYPANE_EXPORT_TOKEN`, so the owner can store the token in the cloud environment's network-secret form and
Claude can fetch the history without SSH and without ever seeing the token.

## What changed

- `companion/export_api.py` (new): `ExportMixin` on `Handler`, with token check, throttle, `since` parsing,
  and responses. The environment variable is read on every request, like the Auth0 settings.
- `server/history_db.py`: `export_device_health` opens `history.db` with `file:...?mode=ro`, `busy_timeout`
  and `query_only`, binds `since` as a parameter, and raises `TooManyRows` past the cap. The existing
  `open_db` path is read-write and runs the schema, so it was not used.
- `companion/oidc.py`: `StartThrottle.is_blocked` (a non-recording check) so failures can be counted after
  the comparison and the block checked before it. The throttle class and `login_throttle_key` are reused.
- `companion/routes.py`: one `PUBLIC` GET route, the way the sign-in routes are registered. It is not
  device-scoped and does not resolve under `/devices/<id>`.
- Tests: `companion/test_export_battery_history.py` (50 cases), a matrix row plus a public/global check in
  `companion/test_access_matrix.py`, and the public-route lists in `companion/test_route_table.py`.
- Docs: `deploy/README.md` section, `deploy/skypane.env.example`, `hardware/FIELD-VALIDATION-FR.md`
  Partie A bis. `deploy/Caddyfile` is unchanged.

## Behaviour decisions

- Other methods follow the app's convention: only `do_GET` and `do_POST` exist, so POST finds no route (404)
  and PUT, DELETE, PATCH and HEAD get the standard library's 501. None return data.
- `since` is required, exactly one parameter, percent-encoding accepted.
- A bad query is only reachable with a valid token; a bad request with a valid token is not a failed attempt
  for the throttle.
- A throttled client gets 429 even with the right token until its window (60 s) clears, which stops it from
  testing guesses faster. Limit: 10 failures per 60 s per client (IPv6 collapsed to /64).
- Stored `ts` values are `+00:00` ISO text and `since` ends in `Z`; the comparison is the same text compare
  the SSH export does, so a row exactly on the `since` second is left out ('+' sorts before 'Z').

## Security review

| Threat | Handling | Proof |
|---|---|---|
| Token guessing | 32+ char token required to enable; 10 failures per minute per client, checked before comparing, 429 with the right token too | `test_repeated_failures_from_one_client_are_throttled`, `test_throttling_is_per_client_address`, `test_a_32_character_token_turns_the_feature_on`, `test_a_token_shorter_than_32_characters_leaves_the_feature_off` |
| Timing | `hmac.compare_digest` on bytes; only the length can differ. No early return on a prefix | `test_near_miss_credentials_are_refused` (behaviour only; constant time is by construction) |
| Token leakage (logs, errors, redirects) | Token never formatted into any string; the app logs method and path only; errors are fixed bodies; no redirect on this route | `test_the_token_never_reaches_the_server_log`, `test_a_missing_and_a_wrong_token_get_the_same_401`, `test_a_missing_history_database_is_a_503_and_is_not_created` |
| SQL injection via `since` | Strict regex plus `strptime` before any query, then bound as a parameter | `test_a_malformed_since_is_a_short_400` (quote and DROP cases) |
| Path or host confusion | Exact-match route; not device-scoped; absent under `/devices/<id>`; a token in the query string is not accepted | `test_the_export_route_is_the_only_api_route_and_is_public_and_global`, `test_the_token_in_the_query_string_is_not_a_credential` |
| Resource exhaustion | 200000-row cap answered 413 (the query reads cap+1 rows only), 400-day window, bounded throttle table, query-parameter count limited | `test_more_rows_than_the_cap_is_a_413_never_a_truncation`, `test_since_older_than_400_days_is_refused` |
| CSRF or cookie confusion | The Cookie header is never read, no cookie is set, read-only GET, a cookie alone or with a wrong token is a 401 | `test_a_signed_in_admin_cookie_never_grants_access`, `test_a_valid_token_response_sets_no_cookie_and_ignores_a_bad_one` |
| Feature accidentally on | Off when the variable is unset or under 32 characters; answers like an unknown path, also for an admin cookie; the example env line is commented out | `test_without_a_token_variable_the_route_is_an_unknown_path`, `test_an_admin_cookie_does_not_reveal_a_disabled_route` |
| Writes | `mode=ro`, `query_only`; a missing database is not created | `test_a_missing_history_database_is_a_503_and_is_not_created` |
| Other tables | One fixed SELECT on `device_health` | `test_only_device_health_is_exported` |

Residual: the 429 pre-check means anyone sharing the owner's client address can block the owner's fetches
for up to a minute by sending bad tokens.

## Verification run

ruff, `scripts/check_comment_history.py check`, `scripts/check_function_size.py check --max 80 server
stub-server`, mypy (23 files), the new tests, `companion/test_access_matrix.py`,
`companion/test_route_table.py`, `companion/test_suite_guards.py`, the `deploy` tests, and the non-browser
`companion` plus `server` tests with `-n4` (4955 passed, 11 skipped, no Playwright). Not run: Playwright
browser tests and the whole-suite coverage gate.
