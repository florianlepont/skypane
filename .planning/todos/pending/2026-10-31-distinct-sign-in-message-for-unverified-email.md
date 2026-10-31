---
created: 2026-10-31T11:40:00.000Z
title: Show a distinct sign-in message when the Auth0 email is not verified
area: auth
source: owner's Phase 54 production test, 2026-10-31
milestone: v1.2
files:
  - companion/sign_in.py
  - server/fleet_sessions.py
  - companion/login_page.py
  - companion/i18n_fr/
---

## Problem

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

## Solution

Render a separate page for the `unverified_email` outcome ("Verify your email
address with Auth0, then sign in again") and keep the "not invited" page for
the other refusals. This is safe against account enumeration: `_resolve`
returns `unverified_email` before it looks the email up, so the new page
reveals nothing about who is invited.

- English and French strings in `companion/i18n_fr/`.
- A behaviour test over real HTTP using the fake Auth0 with an unverified
  email, next to the existing refusal tests.
- No change to which sign-ins are accepted.

Not tied to a phase yet. It touches Phase 54 code; it can ride Phase 55's
Account and sign-in work or a small fix after it.
