---
id: SEED-012
status: dormant
planted: 2026-10-31
planted_during: "v1.2 Phase 54 (Auth0 sign-in), owner's production test"
trigger_when: "Milestone v1.2 — earmarked by the owner on 2026-10-31; surface it when the admin Users page and its Invite card (Phase 55) are built or revisited."
target_milestone: v1.2
scope: medium
---

# SEED-012: Make the admin invite create the Auth0 account and send the invitation

## Why This Matters

Phase 55 plan 55-12 adds an Invite card to the admin Users page (email and
role). It creates only the local user. The invited person still has no Auth0
account, because sign-ups are disabled in the tenant, so today the owner must,
by hand: create the user in the Auth0 dashboard, make sure the email is
verified (SEED-011), then tell the person. The owner asked on 2026-10-31 to be
able to invite a new user from the admin companion without these manual steps.

## When to Surface

**Trigger:** v1.2, when the admin Users page and its Invite card are built or
revisited, or when a first relative is onboarded for real.

## Scope Estimate

**Medium, and it needs an owner decision first.** Candidate: the companion
calls the Auth0 Management API with `requests` (no new dependency) using a
dedicated machine-to-machine application, creates the user on the
`skypane-users` connection, and sends the invitation email (a password-change
or verification ticket). Points to settle:

- A second Auth0 secret in `skypane.env`, with the narrowest scopes (user
  creation and tickets only). A compromised companion could then create Auth0
  users; sign-in still requires the local invite, so this widens the blast
  radius rather than opening a door.
- Whether the account can be created already email-verified (to check in the
  Auth0 documentation) so the first sign-in links without a separate step.
- Rate limits and failure handling: the local invite must not be left half
  created if the Auth0 call fails, and the audit log should record the outcome.
- Tests against an extended fake Auth0; the test network guard allows loopback
  only.
- Cheaper alternative: keep it manual and add a checklist to the Invite card and
  `deploy/README.md`.

## Breadcrumbs

- `.planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/55-12-PLAN.md` (Users page, Invite card)
- `companion/console_users.py` (on the Phase 55 branch)
- `deploy/skypane.env.example`, `deploy/README.md` (Auth0 section)
- `test-support/fake_auth0.py`
- `.planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-HANDOFF.md` (owner go-live checklist)

## Notes

Related: SEED-011. Not part of Phase 54's or Phase 55's current plans.
