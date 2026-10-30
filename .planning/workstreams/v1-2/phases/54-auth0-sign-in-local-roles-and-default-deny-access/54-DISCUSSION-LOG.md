# Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access - Discussion Log

> **Audit trail only.** Decisions are in 54-CONTEXT.md.

**Date:** 2026-10-30
**Areas discussed:** legacy removal, session lifetime, user role before Phase 51, sign-out

## Legacy removal
Options: 2027-01-31 (recommended), 2026-12-31, 2027-04-30. **Choice (free text):** "as soon as the Auth0 phase is in production" (event-driven, no calendar date).

## Session lifetime
Options: 30d/7d idle (recommended), 12h, 7d. **Choice:** 30d max, 7d idle.

## User role before Phase 51
Options: account page only (recommended), read-only Home/Flights, nothing. **Choice:** account page only.

## Sign-out
Options: local only (recommended), local + Auth0 logout. **Choice:** local + Auth0 logout.

## Claude's Discretion
Module layout, env names, cookie design, matrix enumeration, plan split.

## Deferred Ideas
Per-device routes (51), pairing/console (55), view-as-user.
