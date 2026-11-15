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
