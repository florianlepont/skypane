---
phase: 68-console-and-companion-visual-improvements
plan: 19
subsystem: companion
tags: [auth0, management-api, invitation, security]
requires: ["68-01", "68-05"]
provides:
  - "companion.auth0_management.create_invitation(environ, email, result_url, post)"
affects: ["68-28"]
tech-stack:
  added: []
  patterns: ["injectable transport", "result type, never raises"]
key-files:
  created:
    - companion/auth0_management.py
    - companion/test_auth0_management.py
    - deploy/tests/test_env_example_mgmt.py
  modified:
    - test-support/fake_auth0.py
    - deploy/skypane.env.example
    - deploy/README.md
    - pyproject.toml
decisions:
  - "Connection id comes from optional SKYPANE_AUTH0_DB_CONNECTION_ID; a new user's ticket uses the user_id from the creation response, so the id is needed only for an already-existing account (409). Without it that case fails closed with reason user_exists_connection_id_missing."
  - "A partial or malformed configuration counts as not configured (no raise), so the local invite keeps working."
  - "Module added to the mypy files list and strict override."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 19: Auth0 Management API client Summary

Stdlib-plus-requests client that creates an Auth0 database user with a discarded random password and returns a one-time password-change ticket link, with a loopback fake and tests; no UI change (wiring is plan 28).

## What was built

- `companion/auth0_management.py`: `from_env`, `configured`, `create_invitation`, hardened `requests_post_json` (no proxy/netrc, verify on, no redirects, timeouts, 64 KiB cap, 15 s deadline). Returns `Result(ok, reason, link)`; `link` is excluded from repr. No logging at all; reasons are short codes.
- `test-support/fake_auth0.py`: Management endpoints (client-credentials token, `POST /api/v2/users`, `POST /api/v2/tickets/password-change`) with scope checks and knobs.
- 42 tests including the log-capture test (secret, token, ticket link absent from log records and reprs), no-network-when-unconfigured, 409 path, timeouts, oversize, malformed responses, raising transport.
- `deploy/skypane.env.example` (commented placeholders), `deploy/README.md` section "Auth0 invitations (machine-to-machine)", `deploy/tests/test_env_example_mgmt.py`.

## Auth0 API fields used

Could not be re-confirmed against live docs (ctx7 not installed, no network to Auth0); taken from the Management API as known. Confirm on the real tenant before wiring:
- `POST /oauth/token`: `grant_type=client_credentials`, `client_id`, `client_secret`, `audience=https://{domain}/api/v2/` (sent as JSON).
- `POST /api/v2/users`: `email`, `email_verified=false`, `connection`, `password`, `verify_email=false`; 201 returns `user_id`; 409 when it exists.
- `POST /api/v2/tickets/password-change`: `user_id` (new user) or `email` + `connection_id` (existing), `result_url`, `ttl_sec=432000` (5 days), `mark_email_as_verified=true`; 201 returns `ticket`.
- Tenants with a custom domain may need the audience to stay on the canonical tenant domain (open point).

## Deviations from Plan

None - plan executed as written. The plan says the connection id is "resolved from configuration or from the user-creation response"; both are used as stated above.

## Design-system divergences

None.

## Open owner decisions / manual steps

Written in `deploy/README.md`: create the machine-to-machine application, authorise only `create:users` and `create:user_tickets`, note the database connection name (and optionally id), put the four variables in `/opt/skypane/skypane.env`, restart the companion. Plan 28 decides wording of failures shown to the administrator and how the audit log records the outcome (the reason codes are stable).

## Verification

`pytest companion/test_auth0_management.py` (42), `companion/test_auth0_login.py`, `companion/test_suite_guards.py` (362), `pytest deploy/tests` (308 passed, 1 skipped pre-existing), ruff, mypy (no issues), function-size gate, comment-history guard. `companion/oidc.py`, `companion/sign_in.py`, `server/fleet_sessions.py` unchanged. No render baselines touched.

## Threat Flags

None beyond the plan's threat model.

## Self-Check: PASSED
