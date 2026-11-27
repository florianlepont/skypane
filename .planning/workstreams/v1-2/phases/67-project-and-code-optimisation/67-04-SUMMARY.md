---
phase: 67-project-and-code-optimisation
plan: 04
status: pending-ci-repetition
requirements: [QUAL-01]
key-files:
  modified: [companion/test_browser_ux_03.py]
---

# Phase 67 Plan 04: Flaky lightbox test fix Summary

Status: code task done, checkpoint pending. The 30-repetition CI proof has not run yet.

## What changed

`test_a_refresh_keeps_every_picture_action_working` read `dialog.open` right
after clicking a swapped-in picture link. The lightbox opens only after the
large picture has loaded (`whenPictureReady`), so the read raced the load.
The test now waits for the dialog to become visible (`wait_for(state="visible")`)
before reading `open`, the same pattern as `test_browser_ux_01.py`. The
assertion message is unchanged. No product code changed; the test is not
skipped, xfailed or quarantined.

Other picture-link clicks in `companion/test_browser*.py` were scanned; each
already waits for the dialog (ux_01, flights_cards) or does not read `open`.

## Verification

- ruff check: passed.
- pytest --collect-only: the test id is still collected (1).
- Browser run: not possible locally (no matching Chromium); left to CI.

## Pending

Checkpoint: 30 consecutive CI passes of the test (orchestrator).

## Deviations from Plan

None.
