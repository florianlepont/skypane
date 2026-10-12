---
quick_id: 261012-toast
slug: toast-paused-clock
date: 2026-10-12
type: quick
---

# Quick 261012-toast: summary

## Root cause

`_open(clock=True)` called `page.clock.install()`, which leaves fake time flowing with real
time. `toast.js` arms a `setTimeout` for the dwell and pauses it on hover, focus or a hidden
document. In the test, after the hover phase 4000 ms of the 6000 ms dwell remain; `run_for(3500)`
leaves 500 ms, and the real time that then passes before `page.focus(...)` (the next step)
also counts against the timer. On a slow runner that is enough for the toast to expire and be
removed, so `page.focus` retries against a detached element until its 30 s timeout (the
second-slowest test, about 32 s). The toast script is correct: focus pauses the countdown, but
only if focus lands before expiry.

Reproduced deterministically by adding `page.wait_for_timeout(800)` between `run_for(3500)` and
`page.focus`: 3 of 3 runs failed with the CI message (`Page.focus: Timeout 30000ms exceeded`,
33-38 s). A first run failed earlier at the "countdown resumes" assertion, same cause.

## Fix

`companion/test_browser_toasts.py`: `_open(clock=True)` now installs the clock at a fixed start
time and immediately `pause_at`s one second later, so fake time moves only in `run_for`. The
pause survives the later `page.goto`. All clock tests keep their dwell arithmetic and
assertions.

## Verification

- With the fix reverted and the 800 ms delay: fails 3/3. With the fix and the same delay: passes.
- 8 plain runs and 12 runs with 6 busy loops on 4 cores: 20/20 passed (4 s under load, 2.7 s idle;
  the test now takes about 2 s instead of 30 s on failure).
- Toast file plus `test_suite_guards.py`: 149 passed (`-n4`). ruff and
  `scripts/check_comment_history.py check` clean.
