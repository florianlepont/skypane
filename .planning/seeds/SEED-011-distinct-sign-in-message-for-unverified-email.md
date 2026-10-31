---
id: SEED-011
status: dormant
planted: 2026-10-31
planted_during: "v1.2 Phase 54 (Auth0 sign-in), owner's production test"
trigger_when: "Milestone v1.2 — earmarked by the owner on 2026-10-31; surface it when Auth0 sign-in, the Account page or the sign-in error pages are next touched."
target_milestone: v1.2
scope: small
---

# SEED-011: Show a distinct sign-in message when the Auth0 email is not verified

## Why This Matters

The first sign-in of an invited user links the Auth0 identity to the local user
by email, and only when Auth0 reports `email_verified` as true
(`server/fleet_sessions.py`, `_resolve`: refusal reason `unverified_email`).
`companion/sign_in.py` answers every refusal with the same "not invited" page.

On 2026-10-31 an invited account with the role `user`, created by hand in the
Auth0 dashboard (so not verified), was shown "Aucune invitation trouvée: ce
compte n'a pas été invité sur SkyPane". The person is invited; the message is
wrong and sends them to the administrator for nothing. The exact reason is
written to the companion journal as `sign-in refused: <reason>`; confirm
`unverified_email` there for the observed case.

## When to Surface

**Trigger:** v1.2, whenever Auth0 sign-in, the Account page or the sign-in
error pages are next touched (Phase 55 is the natural carrier), or when the
admin invite flow (SEED-012) is built, since both concern the same first
sign-in.

## Scope Estimate

**Small.** One new page and its English and French strings, one extra branch in
`companion/sign_in.py`, one behaviour test.

- Render a separate page for the `unverified_email` outcome ("Verify your email
  address with Auth0, then sign in again"); keep the "not invited" page for the
  other refusals.
- Safe against account enumeration: `_resolve` returns `unverified_email` before
  it looks the email up, so the new page reveals nothing about who is invited.
- English and French strings in `companion/i18n_fr/`.
- A behaviour test over real HTTP with the fake Auth0 and an unverified email,
  next to the existing refusal tests.
- No change to which sign-ins are accepted.

## Breadcrumbs

- `companion/sign_in.py` (refusal handling, the "not invited" page)
- `server/fleet_sessions.py` (`_resolve`, the `unverified_email` reason)
- `companion/login_page.py` (`not_invited_page`)
- `companion/i18n_fr/`
- `test-support/fake_auth0.py` (failure knobs)
- `.planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-VERIFICATION.md`

## Notes

Observed by the owner during the Phase 54 production test. Related: SEED-012.
