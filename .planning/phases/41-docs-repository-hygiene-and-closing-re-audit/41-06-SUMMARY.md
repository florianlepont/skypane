---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 06
subsystem: testing
tags: [security, state-integrity, ssrf, systemd-hardening, audit, re-verification]

# Dependency graph
requires:
  - phase: 36-state-integrity-and-device-protocol
    provides: INT-01..INT-14 remediations (poll.lock flock, one atomic_write helper, content-addressed img/, byos input hardening, TimeoutStartSec, adsbdb TTL/LRU cache, Caddy tailer hardening, provider type checks, full traceback on failure, calendar clock/lock, queued-detection bookkeeping, pinned outbound connections)
  - phase: 37-security-and-operations-hardening
    provides: SEC-01..SEC-08 remediations (per-IP login throttle, HSTS, POST origin check, nightly off-box backup, atomic deploy with rollback, systemd unit hardening + byos loopback bind, secret-via-env, SSH hardening)
provides:
  - Independent, current-code re-audit of all 14 INT and 8 SEC findings (41-REAUDIT-INT-SEC.md)
  - Confirmation that none of the Phase 38-40 refactors (poll_cycle split, history_db rewrite, calendar_rules package split, companion route table) dropped a Phase 36/37 fix
  - A cross-checked, non-repo-provable artefact list for every runtime-only claim (VPS TimeoutStartUSec, live HSTS header, off-box backup arrival, byos loopback listen, no secret in ps, live sshd -T) pointing at its 37-SEC-BASELINE.md/36-VERIFICATION.md checkpoint
affects: [41-08-closing-plan]

# Tech tracking
tech-stack:
  added: []
  patterns: ["read-only re-verification against current file:line and targeted test runs rather than trusting SUMMARY/VERIFICATION checkboxes", "cross-environment test re-run (Docker/Linux) when the native re-audit sandbox itself cannot exercise a check (BSD mv, missing systemd-analyze)"]

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-INT-SEC.md
  modified: []

key-decisions:
  - "All 14 INT findings and all 8 SEC findings verify VERIFIED-CLOSED against the current server/, stub-server/, companion/, and deploy/ trees — none regressed across the Phase 38-40 refactors"
  - "INT-14 confirmed the ledger's primary remediation option (pin the resolved IP for the connection) is what actually shipped in server/http_fetch.py::pinned_request, not merely a corrected docstring; server/net/safe_fetch.py (added in Phase 39) is documented as an additive early-refusal layer on top of it, not a replacement"
  - "SEC-03's origin check was re-verified against the current, larger companion/routes.py POST route table (17 routes, up from Phase 37's set) by tracing the single pre-routing dispatch gate in companion/app.py::_dispatch(), rather than trusting the Phase 37 route list"
  - "Two deploy/tests files (test_activate.py, test_install_backup_key.py) fail natively on this macOS re-audit sandbox because its BSD mv lacks the -T flag the scripts use; rather than leave that unproven, both were re-run inside a Linux container (Docker) to get a real pass/fail result matching what CI's ubuntu-latest runner would see"
  - "systemd-analyze security --offline=true was re-run in a systemd-installed Ubuntu container (this host has no systemd-analyze) and reproduced 37-SEC-BASELINE.md's exact scores (poll 1.5, companion 1.5, byos 1.3, backup 0.8) byte-for-byte, confirming no unit hardening regression"
  - "INT-07's VPS runtime confirmation (TimeoutStartUSec=1min 30s) was already recorded in 36-VERIFICATION.md's own Human Verification Required section (2026-09-26, post Phase 37-11 deploy) — cited directly rather than re-flagged as 'never confirmed'"

patterns-established: []

requirements-completed: []  # DOC-03 spans 4 re-audit slices (41-04..41-07) plus the 41-08 closing merge; not complete until 41-08

# Metrics
duration: 70min
completed: 2026-09-28T07:03:24Z
status: complete
---

# Phase 41 Plan 06: Closing re-audit of Phases 36-37 (INT-01..14, SEC-01..08) Summary

**Independently re-verified all 14 state-integrity/device-protocol findings and all 8 security/operations findings against the current codebase — all 22 VERIFIED-CLOSED, with the Phase 38-40 refactors (poll_cycle split, history_db rewrite, calendar_rules package split, companion route table) confirmed to have carried every fix forward intact.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-28T05:53:00Z (approx.)
- **Completed:** 2026-09-28T07:03:24Z
- **Tasks:** 2 (combined into one report/one commit — see Deviations)
- **Files modified:** 1 (`41-REAUDIT-INT-SEC.md`, new)

## Accomplishments

- Ran the plan's full targeted test set: `server/test_atomic_io.py`, `server/test_caddy_tail.py`,
  `companion/test_poll_now_lock.py`, `companion/test_preview_cache.py`, `stub-server` (94 passed,
  3 skipped — `/proc` reads unavailable in this non-root sandbox), plus `server/test_enrich.py`,
  `server/test_plane_detection.py`, `server/test_calendar_rules.py`, `server/test_safe_fetch.py`,
  `server/test_poll_cycle_steps.py`, `server/test_poll_loop.py`, `server/test_http_fetch.py`,
  `server/test_poll_lock.py` (442 passed) covering every INT finding's own regression test.
- Ran the SEC test set: `companion/test_login_throttle.py`, `companion/test_post_origin.py`,
  `companion/test_route_table.py`, `companion/test_health_offbox.py`,
  `companion/test_browser_origin.py` (124 passed, including the two Playwright cases — Chromium
  launched successfully in this sandbox, unlike `37-VERIFICATION.md`'s own environment).
- Ran `deploy/tests` natively (100 passed, 4 skipped for missing `systemd-analyze`), then
  re-ran the two files that fail on this macOS sandbox's BSD `mv` (`test_activate.py`,
  `test_install_backup_key.py`) inside a Linux Docker container: 70 passed, 4 skipped —
  proving those failures are a sandbox limitation, not a code regression.
- Ran `systemd-analyze security --offline=true --threshold=20` against all four
  `deploy/*.service` units inside a systemd-installed Ubuntu container (this host has no
  `systemd-analyze`): `skypane-backup.service` 0.8 SAFE, `skypane-byos.service` 1.3 OK,
  `skypane-companion.service` 1.5 OK, `skypane-poll.service` 1.5 OK — byte-identical to the
  scores `37-SEC-BASELINE.md`/`37-VERIFICATION.md` recorded, confirming no hardening
  regression across Phases 38-40.
- Wrote 22 report rows (INT-01..14, SEC-01..08), each with a verdict, the closing commit(s)
  `git log --oneline --follow` reports (this repo's history is per-plan/per-phase granular —
  `f4d97097` "Phase 36...", `34bc0384` "Phase 37-11...", etc. — not squashed the way the
  41-05 firmware slice's own history search found for `firmware/`), current file:line
  evidence, and the covering test module.
- Confirmed `server/net/safe_fetch.py` (a Phase 39 addition) layers an additional early SSRF
  refusal on top of INT-14's `pinned_request()` fix rather than replacing it, by reading its
  own docstring's explicit statement that the real DNS-rebinding protection is still
  `pinned_request()`.
- Enumerated all 17 current POST routes in `companion/routes.py` and traced
  `companion/app.py::_dispatch()` to confirm the Origin/Sec-Fetch-Site check
  (`auth.post_origin_ok()`) runs once, before routing, so every route — including ones added
  by Phase 40's route-table refactor — is covered structurally rather than by a per-route
  repeat.
- Built a unit × directive matrix for SEC-06 across all four systemd units, confirming
  `CapabilityBoundingSet=`, `PrivateDevices=true`, the three `ProtectKernel*` directives,
  `RestrictAddressFamilies=`, `SystemCallFilter=@system-service`, and `UMask=0027` are present
  on every one, plus byos's additional `IPAddressDeny=any`/`IPAddressAllow=localhost` and
  `--bind 127.0.0.1`.

## Task Commits

Both plan tasks (Task 1: INT-01..INT-14, Task 2: SEC-01..SEC-08 + `## Flags`) target the same
single output file (`41-REAUDIT-INT-SEC.md`); the work was done as one continuous read-only
investigation and committed as one commit, matching the precedent both `41-04-SUMMARY.md` and
`41-05-SUMMARY.md` recorded for the same structural reason — an atomic markdown-file write
cannot be meaningfully split into two partial, individually-valid commits.

1. **Tasks 1+2: Re-audit INT-01..14 and SEC-01..08, read-only** - `e5daa5a2` (docs)

**Plan metadata:** (this SUMMARY.md and the final metadata commit, see below)

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-INT-SEC.md` -
  22-row re-audit report (INT-01..14, SEC-01..08), a "Gate runs" table recording every test
  suite and container run used as evidence, a unit × directive matrix for SEC-06, and a
  `## Flags` section.

## Decisions Made

- Combined the plan's two tasks into a single commit (see Task Commits above) because they
  write to the same file and an intermediate partial-table commit would not be a valid
  standalone artefact — the same reasoning `41-05-SUMMARY.md` recorded.
- Where a native check in this macOS, non-root sandbox could not run at all (BSD `mv` lacking
  `-T`, no `systemd-analyze` binary, no `/proc` filesystem semantics matching Linux), the gap
  was closed with a Docker container rather than left unproven or silently accepted — each
  such row in the report names exactly which command ran where.
- INT-09 and SEC-05's evidence leans partly on a passing regression test against a
  since-rewritten module (`server/history_db.py`, rewritten by Phase 38's EFF-01..06 work;
  `deploy/activate.sh`, verified via the Linux container) rather than a fresh line-by-line
  reading of every rewritten internal, since a full re-derivation of Phase 38's own EFF-*
  rewrite is out of this slice's scope (a different re-audit slice covers Phase 38). Both rows
  are still recorded VERIFIED-CLOSED because the specific regression test the ledger and the
  Phase 36/37 verification reports relied on passes unmodified against the current code — this
  is flagged in the report's own Notes, not silently accepted.

## Deviations from Plan

None - plan executed exactly as written. The only adaptations were procedural (one commit
instead of two; using Docker to get real evidence for two macOS-incompatible test files and
one missing binary), documented above under Decisions Made, not deviations under Rules 1-4 -
no bug was fixed, no missing functionality was added to the codebase, nothing blocking this
plan's own progress was resolved by touching `server/`/`stub-server/`/`companion/`/`deploy/`,
and no architectural change was made. This plan is read-only on the codebase throughout.

## Issues Encountered

- This macOS re-audit sandbox's `mv` (BSD) does not support the `-T` flag
  `deploy/activate.sh` and `deploy/backup/install-backup-key.sh` use; two test files fail
  natively for that reason alone (`deploy/tests/test_activate.py`,
  `deploy/tests/test_install_backup_key.py`). Resolved by re-running both inside a Linux
  Docker container (`python:3.12-slim` with `pytest`/`requests`/`pillow`/`pytest-socket`
  installed), which passed all 70 tests (4 skipped for the same missing-`systemd-analyze`
  reason as the native run) — confirming this is a sandbox limitation, not a code defect,
  since the production VPS and CI's `ubuntu-latest` runner both have GNU `mv`.
- `systemd-analyze` is not on this host's `PATH` at all (unlike the 41-05 sandbox, which
  presumably had it, or unlike `ci.yml`'s `ubuntu-latest` runner). Resolved the same way: an
  `ubuntu:24.04` Docker container with `systemd` installed reproduced the exact security
  scores `37-SEC-BASELINE.md` recorded.
- This sandbox runs as a normal macOS user (uid 501), not root, unlike the `41-04`/`41-05`
  root-Linux sandboxes those slices ran in — 3 `stub-server/test_byos_bind_secret.py` tests
  that read `/proc` skip here for that reason. Recorded honestly in the report header rather
  than silently ignored.

## User Setup Required

None - no external service configuration required. This plan is read-only verification; no
code was written, and the only external tool used was Docker, already available in this
sandbox, to run existing tests/scripts against the already-committed code — no new service was
provisioned or configured.

## Next Phase Readiness

- All 14 INT and all 8 SEC findings are provably closed on the current codebase, across the
  Phase 38-40 refactors — Phase 42 (OTA) can proceed on the assumption that the state-integrity
  and security foundations from Phases 36-37 are real, not just documented as real.
- No code under `server/`, `stub-server/`, `companion/`, or `deploy/` was modified by this
  plan; the only new artefact is this slice's own re-audit report and SUMMARY.
- No blockers for 41-08 (the closing plan that merges all four re-audit slices): this slice's
  report format matches `41-04`'s and `41-05`'s (same columns, same three verdicts, `## Flags`
  section, header with audited commit/uid/tools), so it can be merged directly. This slice's
  header additionally documents the sandbox differences (non-root, no `systemd-analyze`, BSD
  `mv`) it hit that the other two slices' sandboxes apparently did not, and how each was
  closed with real evidence rather than left unproven — 41-08 should carry that pattern
  forward if the same gaps recur.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*
