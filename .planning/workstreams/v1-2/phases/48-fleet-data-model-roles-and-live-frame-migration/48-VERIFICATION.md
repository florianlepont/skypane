---
phase: 48-fleet-data-model-roles-and-live-frame-migration
verified: 2026-10-29T00:00:00Z
status: passed
score: 4/4 roadmap truths verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "CR-01: orphan legacy token aborted fleet_migrate and survived devices_cli remove"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run fleet_migrate --dry-run against a copy of the real production state (byos_state.json, devices.json)"
    expected: "Exit 0; the frame's next poll returns the same image hash and sleep_s. Shows whether production holds orphan tokens (reported as skipped)."
    why_human: "Production state is not available in the sandbox; replay tests use a synthetic fixture."
  - test: "Run the companion Chromium browser tests for the Health fleet-fallback signal"
    expected: "Pass in an environment with a Playwright browser"
    why_human: "No browser in the sandbox."
---

# Phase 48 Verification (re-verification after plan 48-08)

**Goal:** Owner can record users, devices, hardware types and locations in one fleet database; the live frame is migrated with no observable change.
**Status:** passed. It was `human_needed` on 2026-10-29 with two environment-bound checks open; both are closed below (2026-10-31). Re-verification: Yes, after gap closure.

## Observable truths

| # | Roadmap success criterion | Status | Evidence |
|---|---|---|---|
| 1 | Same image hash and wake interval, credentials kept | VERIFIED | Freeze and replay tests pass (synthetic fixture; real-state replay is a human check). |
| 2 | Previous release runs on migrated state; re-run changes nothing | VERIFIED | Migration is expand-only and idempotent. CR-01 closed (below). |
| 3 | Users admin/user, one owner per device, hardware profiles incl. simulated, role local | VERIFIED | No regression; fleet_db, fleet_cli and fleet_auth tests pass. |
| 4 | fleet.db in backup with tested restore; Phase 47 freeze test | VERIFIED | Backup and freeze tests pass. |

## CR-01 closure (independent)

- `stub-server/devices_cli.py` `cmd_remove` now loads state, deletes `tokens[mac]` if present and saves.
- `server/fleet_migrate.py` `_read_tokens` returns (kept, skipped). It still rejects malformed MACs and tokens but counts tokens for unregistered MACs instead of raising. `_with_skipped` adds a count-only report line on the nothing-to-do, dry-run and applied paths.
- Repro in a scratch state dir: two devices and two tokens, then `devices_cli remove` of the second. `byos_state.json` now holds only token 1. Dry-run and the real migration both exit 0 and migrate 1 device.
- Regression tests exist: orphan skipped and counted, second run a no-op, malformed token on an orphan MAC still aborts, and an auth test with orphan tokens returning 401.

## Tests and gates

- `server/.venv/bin/python3 -m pytest server stub-server deploy/tests -n 4 --no-cov`: 1606 passed, 5 environmental skips.
- Function-size gate (max 80, server and stub-server): clean.
- Comment-history check: exit 0.

## Accepted residual

A pre-existing orphan token stays valid only while byos runs in the legacy fallback (fleet.db corrupt or too new). `bearer_ok` is deliberately unchanged, and `devices_cli revoke-token` clears it. The 48-08 plan records this as accepted.

## Warnings (non-blocking, unchanged from review)

WR-01 through WR-07 in 48-REVIEW.md (dry-run does not exercise apply, token write ordering, empty new fleet.db reported as a fault, backup retention sharing, archive file mode and umask, bootstrap owner not checked for admin).

## Human verification (closed 2026-10-31)

1. **Dry-run of the migration against real production state.** Run by the owner on the production host on 2026-10-31, directly on the live state directory (a dry run writes nothing):

   ```
   python3 -m server.fleet_migrate --state-dir /opt/skypane/state --dry-run
   nothing to do
   skipped 1 token(s) for unregistered device(s)
   ```

   The state is already migrated (production deploys since 2026-10-30 ran the migration before the release swap, and the frame kept waking on its cadence, see `skypane-byos` journal of 2026-10-31: regular `GET /device/v1/display` then `GET /img/<hash>.bin`, no 401, 403 or 5xx). The run also shows the thing the check looked for: production holds **one orphan token** for an unregistered device, counted and skipped, not an error. That token stays valid only while byos runs in the legacy fallback (accepted residual above); `devices_cli revoke-token` clears it if the owner wants it gone. The exit code was not recorded.
2. **Browser tests for the Health fleet-fallback signal.** The CI check "Lint, test, coverage, attribution" succeeded on PR #240 (2026-10-29), where a missing Playwright browser fails the run by project policy instead of skipping. The CI result is the evidence; the specific test was not individually confirmed in the run output.

## Gaps summary

No code gaps remain. Both environment-bound checks are closed (see above). One production observation stays open and is not a gap: the orphan token of check 1, which the owner may revoke at will.

_Verifier: Claude (gsd-verifier)_
