---
quick_id: 261028-special-add
slug: special-add-escape-focus
date: 2026-10-28
type: quick
---

# Quick 261028-special-add: summary

## Root cause

A race in the test, not a product defect. `companion/static/theme-preview.js` closes the add
dialog from a `keydown` listener on `.special-add__panel`, so Escape only closes it while focus
is inside the panel. Focus is moved there from the `<details>` `toggle` listener
(`start.focus()`), and the browser fires `toggle` as a queued task after the click, not
synchronously. The test waited for the panel to be visible (which happens at once, the `open`
attribute drives the CSS) and then pressed Escape. If the key event reaches the page before the
queued `toggle` task has run, focus is still on the summary, the panel listener never sees the
key and the dialog stays open. The close itself is synchronous (`add.open = false`, no
animation or deferred close on `.special-add`), so once focus is inside, Escape closes
reliably. A person cannot press a key within that window; the test can.

## Reproduction

- Plain code, 40 consecutive runs of the test with 8 busy loops on 4 cores: 40/40 passed.
  CPU load alone did not reproduce it here.
- CDP `Emulation.setCPUThrottlingRate` 20x, 10 runs: 10/10 passed.
- Deterministic: an init script that delays the `.special-add` `toggle` listener by 300 ms
  (the late-task case) fails 1/1 with the CI message,
  `assert not True ... evaluate('d => d.open')`.
  So the observed flake is a window the CI runner hit once; locally the natural rate is below
  1 in 50.

## Fix

`companion/test_browser_display_looks.py`: before pressing Escape the test waits until
`document.activeElement` is inside `.special-add__panel` (the real precondition of the handler),
and after it waits for `.special-add` to be closed, both with auto-retrying
`page.wait_for_function`. The assertion that the dialog closes is unchanged in meaning; no
sleep, no tolerance, product code untouched.

## Verification

- With the fix and the same 300 ms late `toggle` injection: passes (without the fix: fails).
- Fixed test, 40 consecutive runs under the same 8 busy loops: 40/40 passed. The unfixed
  loop was also 40/40, so the loop alone cannot show the improvement; the late-toggle injection
  is the evidence.
- Display-looks browser file plus `test_suite_guards.py`: 143 passed (`-n4`). ruff and
  `scripts/check_comment_history.py check` clean.
