---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 07
subsystem: companion
tags: [poll-now-removal, companion, budget]
requires: [52-06]
provides: [single budget consumer (poll process)]
key-files:
  modified: [companion/routes.py, companion/app.py, companion/flash.py, companion/device_scope.py, companion/test_access_matrix.py, companion/testdata/render_baseline.json, ARCHITECTURE.md]
  created: [companion/test_poll_removal.py]
  deleted: [companion/static/poll-cooldown.js, companion/test_device_poll.py, companion/test_poll_now_lock.py]
decisions:
  - poll_lock_for and META_LAST_POLL_TRIGGER kept (calendar sync lock; expand-only meta key)
metrics:
  completed: 2026-10-30
---

# Phase 52 Plan 07: Poll-now removal Summary

Removed "Poll now" end to end: POST /poll-now now answers 404 (admin, user, prefixed and unprefixed), with no cycle run; Home and Device buttons, cooldown script and state, flash keys and EN/FR strings are gone. The poll process is the only budget consumer.

## Commits
- 3efd732: merge of origin/main (Task 1)
- 64e8478: removal of the feature (Task 2)
- docs commit: FLT-02 and Phase 52 criterion 1 reworded (Task 3)

## Tests
`./scripts/run-all-tests.sh`: 5807 passed, 563 skipped. ruff clean, comment-history and function-size gates clean, Phase 47 freeze test passes.

## Not run
- Chromium is not installed (/opt/pw-browsers), so companion Playwright browser tests were skipped locally.
- mypy reports one error (PIL stub missing in server/panel_format.py, environment only).

## Deviations
Stale mentions of /poll-now remain in comments of server/poll_cycle.py, poll_loop.py, state_store.py, detect.py and history_db.py; left untouched because the plan forbids server production changes in this commit.

## Self-Check: PASSED
