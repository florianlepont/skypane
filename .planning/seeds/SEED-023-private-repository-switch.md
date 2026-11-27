---
id: SEED-023
status: dormant
planted: 2026-11-27
planted_during: "v1.2, Phase 70 closed for criteria 1 to 4; the owner moved the switch out of v1.2 so that it does not block the close of v1.2"
trigger_when: "Close of milestone v1.4 (the last step of that milestone), set by the owner on 2026-11-27; surface it when v1.4 is about to close."
target_milestone: v1.4
scope: small
requirement: PRV-01, PRV-03 (moved from v1.2 Phase 70.1)
---

# SEED-023: Switch the repository to private and verify afterwards

## Why This Matters

The owner decided on 2026-11-24 that the whole repository becomes private (firm,
not to be reopened). Phase 70 (v1.2) prepared everything: the production deploy is
a manual workflow, the firmware is signed on the owner's Mac, the CI was measured
and the choice recorded, the inventory of what has been public was made and
handled, and the documents for the private repository were written. On
2026-11-27 the owner decided that the switch itself happens at the close of v1.4
and is part of v1.4, not of v1.2, so that it does not block the close of v1.2.
Until then the repository stays public and the CI runs on hosted runners.

## Scope

- **The pre-flip gate** in `.planning/workstreams/v1-2/phases/70-*/70-POSTFLIP.md`
  must be fully `pass`: token scope of the sessions' GitHub integration, fork pull
  request settings and approval of outside collaborators, a fresh firmware
  artifact, the self-hosted charge status re-read (it expires 2026-12-24 and will
  need a new check), and the CI variable `CI_RUNS_ON` set to the Mac runner.
  Re-run the inventory scan for what was added to the repository since Phase 70.
- **The switch** is made by the owner himself in GitHub settings, last. Nobody
  else can do it.
- **After the switch**, check: sessions can push branches, open draft pull
  requests and read CI status and logs; CI runs green on the Mac runner and once on
  the hosted fallback (private-repository minutes recorded); the production deploy,
  the nightly backup, the release download in CI and Dependabot work; the owner
  can still run a firmware release (a dry run of the signing on the Mac against
  the private repository).
- **No part of the setup may assume** environments, branch protection, rulesets or
  secret scanning on the free plan, and the documents describe the private
  repository.
- Re-check the GitHub plan limits and prices at that date; they change.

## Breadcrumbs

- `.planning/workstreams/v1-2/phases/70-private-repository-and-ci/` (`70-VERIFICATION.md`, `70-POSTFLIP.md`, `70-10-PLAN.md`, `70-MEASUREMENTS.md`, the inventory summary 70-08)
- `.planning/workstreams/v1-2/phases/70.1-*/` (the empty phase folder)
- `deploy/README.md`, `firmware/SIGNING.md`, `COMPLIANCE.md`, `README.md` (licence section)

## Notes

Phase 70.1 of v1.2 is closed as "moved to v1.4": it is no longer a v1.2 phase.
