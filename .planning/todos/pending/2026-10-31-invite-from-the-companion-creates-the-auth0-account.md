---
created: 2026-10-31T11:40:00.000Z
title: Make the admin invite create the Auth0 account and send the invitation
area: auth
source: owner's Phase 54 production test, 2026-10-31
milestone: v1.2
files:
  - companion/console_users.py
  - deploy/skypane.env.example
  - deploy/README.md
  - test-support/fake_auth0.py
---

## Problem

Phase 55 plan 55-12 adds an Invite card to the admin Users page (email and
role). It creates only the local user. The invited person still has no Auth0
account, because sign-ups are disabled in the tenant, so today the owner must
by hand: create the user in the Auth0 dashboard, make sure the email is
verified (see the unverified-email todo), then tell the person. The owner asked
for the invitation to be sent from the admin companion without these manual
steps.

## Solution

TBD, needs an owner decision. Candidate: the companion calls the Auth0
Management API with `requests` (no new dependency) using a dedicated
machine-to-machine application, creates the user on the `skypane-users`
connection, and sends the invitation email (a password-change or verification
ticket). Points to settle:

- A second Auth0 secret in `skypane.env`, with the narrowest scopes (user
  creation and tickets only). A compromised companion could then create Auth0
  users; sign-in still requires the local invite, so this widens the blast
  radius rather than opening a door.
- Whether the account can be created already email-verified (to check in the
  Auth0 documentation) so the first sign-in links without a separate step.
- Rate limits and failure handling: the local invite must not be left half
  created if the Auth0 call fails, and the audit log should record the outcome.
- Tests against an extended fake Auth0; the test network guard allows
  loopback only.
- Cheaper alternative: keep it manual and add a checklist to the Invite card
  and `deploy/README.md`.

Relates to Phase 55 (Users page) and Phase 54 (Auth0 setup); not part of either
phase's current plans.
