---
quick_id: 260923-em4
status: complete
date: 2026-09-23
---

# Quick 260923-em4 — SUMMARY

## Root cause

Clicking the fallback Save while the save bar's `skypane-bar-arrive` entrance
animation is still running stalls Playwright's `stable` actionability check in the
scripts-blocked context.

- In isolation, an immediate click takes ~0.7–1.0 s with the animation and ~0.06 s
  with `reduced_motion="reduce"`.
- Inside the full harness it hangs for the whole 30 000 ms budget. Tracing with
  `framenavigated`/`request`/`response`/`load` listeners showed **no request and no
  navigation at all** during those 30 s, so the click never happened.
  This explains both CI signatures: "element is not stable", and "Timeout ~20ms
  exceeded … domcontentloaded" once the stalled poll has eaten the shared
  `expect_navigation()` clock.

Hypotheses ruled out along the way:
- a meta/HTTP refresh (none exists);
- a late login-submit navigation (0/20 in a targeted repro);
- the infinite `skypane-pulse` animation (opacity only);
- `click(trial=True)` alone (still failed 2/2 full runs).

## Fix

`page.emulate_media(reduced_motion="reduce")` before the check's navigation. The
stylesheet's own `prefers-reduced-motion: reduce` block zeroes the entrance, and the
check's assertions are unchanged. Other checks in the same file already use
`reduced_motion="reduce"`.

## Verification

- Full harness with the fix: the check passed 3/3 runs (2 in a scratch copy of
  `main`, 1 on the branch). Without the fix it failed on every local full-harness run.
- `ruff check .`: clean.
- The two other local failures ("leave-guard stays armed…", "wake_interval_s below
  its floor… got '301800'") are pre-existing and local-only; both pass in CI. The
  second looks like a macOS select-all difference: typed text is appended instead of
  replacing the field. Not in scope here.
