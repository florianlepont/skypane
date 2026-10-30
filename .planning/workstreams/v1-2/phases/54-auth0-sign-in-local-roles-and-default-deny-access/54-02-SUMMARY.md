---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 02
subsystem: auth
tags: [oidc, auth0, pkce, test-support]
requires: []
provides:
  - companion/oidc.py (config, PKCE, URLs, claim validation, hardened token call, AttemptTable)
  - test-support/fake_auth0.py (loopback Auth0 with failure knobs and call log)
affects: [phase-54 later plans]
tech-stack:
  added: []
  patterns: [injected HTTP callable, environment-only configuration, loopback-only insecure flag]
key-files:
  created: [companion/oidc.py, companion/test_oidc.py, test-support/fake_auth0.py, test-support/test_fake_auth0.py]
  modified: []
key-decisions:
  - "requests_post returns an HttpReply(status, body bytes); exchange_code does the JSON parsing so injected fakes stay trivial"
  - "AttemptTable.create generates state, nonce and PKCE pair itself and returns the attempt"
requirements-completed: [AUTH-01, AUTH-06]
duration: 20min
completed: 2026-10-30
---

# Phase 54 Plan 02: OIDC client and fake Auth0 Summary

Pure OIDC client module (all-or-nothing environment config, PKCE S256, strict ID-token claim checks, hardened token call, bounded attempt table) plus a loopback fake Auth0 that enforces PKCE, redirect_uri, secret, single-use codes and a logout allow-list, with a knob for each misbehaviour.

## Tasks
1. companion/oidc.py and unit tests: commit b96721c
2. test-support/fake_auth0.py, its tests, and requests_post round-trip tests: commit 8c5164c

## Deviations from Plan
None - plan executed as written. The `wrong_redirect_uri` knob makes the fake remember a different redirect_uri for the code, so the token exchange fails with 400.

## Verification
92 tests pass (companion/test_oidc.py, test-support/test_fake_auth0.py); ruff and comment-history gate pass; stub-server/test_phase47_freeze.py green. No `verify=False` or `pinned_request` in oidc.py. byos_server.py, firmware and measured_fields_freeze.json untouched.

## Known Stubs
None.

## Self-Check: PASSED
