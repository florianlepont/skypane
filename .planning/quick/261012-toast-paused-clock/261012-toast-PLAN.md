---
quick_id: 261012-toast
slug: toast-paused-clock
date: 2026-10-12
type: quick
---

# Quick 261012-toast: toast tests run on a paused fake clock

`test_auto_hide_pauses_on_hover_focus_and_hidden_document[chromium]` failed in CI with
`Page.focus: Timeout 30000ms exceeded` ("element was detached from the DOM") and passed on a
re-run.

## Task

Make `_open(..., clock=True)` pause the installed Playwright clock so fake time moves only
through `page.clock.run_for`. Dwell times, assertions and the toast script stay as they are.

## Verification

Repeated runs of the failing test with and without CPU load, an artificial real-time delay
with the fix reverted (must fail) and applied (must pass), the whole toast file, suite
guards, ruff, comment-history guard.
