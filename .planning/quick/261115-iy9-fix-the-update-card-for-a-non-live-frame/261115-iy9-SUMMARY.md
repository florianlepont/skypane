---
quick_id: 261115-iy9
status: complete
---

# Quick task 261115-iy9: Update card reads the root state dir for a non-live frame

## What changed

- `companion/pages/update_page.py::_loaded_parts` now loads the device report, resolves the
  type choice and loads the registry from `ctx.root_state_dir` (falling back to `ctx.state_dir`
  when it is None). `compute_next_wake_text(ctx)` still uses the frame's own context.
- New `companion/test_update_page_non_live.py`: a non-live second-type frame (registry and
  device report in the root dir, empty frame dir) shows its releases and reported version; a
  live-frame case is identical whichever directory is named.

## Commits

- f13ad154 test: failing tests (the non-live test failed before the fix, the live test passed)
- 7079c494 fix: the state dir change

## Verification

- 110 passed: test_update_page.py, test_update_page_non_live.py, test_update_actions.py,
  test_console_fleet_view*.py. Goldens untouched.
- function-size gate, ruff, mypy, comment-history guard: clean.

## Other readers

`companion/app.py` POST install/cancel handlers already use `self.args.state_dir` (root) for
the registry, device report and `post_choice`; no change needed. No other module under
`companion/` (console_fleet_view, home, health) reads the registry or device report.

## Part 2: the per-frame page shows only the frame's own hardware type

Observed after Part 1: with registries for two types in the root state dir, the Fleet page of a
frame showed a type chooser (EE02 and EE04 tabs).

- `update_page.render_parts` (the Fleet view's entry) now pins the frame's own hardware type
  (`_loaded_parts(..., pinned=True)`): the choice is that type alone, no chooser; a type with no
  releases shows the empty state for itself. The standalone `update_page.render` keeps the
  chooser. A single relevant type renders byte for byte as before (goldens untouched).
- `GET /update` redirects to a frame's Fleet view whenever a frame of the type exists, so the
  chooser is reachable only on the standalone render; the two server tests that expected the
  chooser on the Fleet view were replaced by a Fleet test asserting no chooser, plus a render
  test of the standalone chooser (English and French).

### device_report.json

One document keyed by device id; every entry carries `hardware_type` (an entry without the field
reads as the legacy type), and `update_view` already reads only the entry of the registry's own
type (`_most_recent_device_entry`). So frames of different types share the file but never each
other's entries on a page; no display rule was needed. The "fw-v1.2.0, installed 3 min ago" on the
live frame was a real install (confirmed by the owner), not a leak. Residual note: an entry written
before the stamp existed counts as legacy; none was seen in tests.

### Commits and verification

- Tests (failing first): the new test commit; fix commit follows it.
- 114 passed: test_update_page.py, test_update_page_non_live.py, test_update_actions.py,
  test_console_fleet_view*.py. Function-size gate, ruff, mypy, comment-history guard clean.
- companion/test_browser_update.py: 49 skipped, Chromium not installed here (not run).

## Part 3: browser chooser tests after the chooser left the Fleet page

CI failed 8 tests in companion/test_browser_update.py that looked for the chooser on /fleet.

- Case (a) applied: the chooser is still reachable in a real browser. GET /update serves the
  standalone render (with chooser) when the requested type has no frame of the viewer's; with a
  frame of that type it redirects to that frame's Fleet page. The tests now load
  /update?type=<second type> (no frame of that type in the fixture) with the same assertions
  (keyboard operation; no horizontal overflow at 360/375/1280, EN and FR). The switching test
  now ends by choosing the legacy type, which lands on that frame's Fleet page with no chooser
  and without the other type's schedule, keeping the "scheduling is independent" intent.
- Added test_frame_fleet_page_is_pinned_to_its_type_even_with_two_types_released.
- Dead-UI flag: the chooser is now reachable only for a type with a registry but no frame.
  Once every released type has a frame it is effectively dead UI. No product code removed.
- Commit: 470d18a1. Chromium was available (/opt/pw-browsers): all 50 tests of the module passed
  locally; ruff and the comment-history guard are clean.
