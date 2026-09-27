# Deferred items

Out-of-scope discoveries logged during execution, per the executor's scope
boundary (fix only what the current task's own files touch; log the rest
here instead of expanding scope).

## 39-10, Task 2 — stale `poll_loop.` prose outside the plan's 3-file scope

39-10's Task 2 acceptance criteria include a repo-wide grep for
`server.poll_loop` / `poll_loop.(run_once|PollBusy|poll_cycle_lock|now_s|
_save_to_gallery|write_panel_atomic)` across `companion/`, filtered to
exclude `#`-comment lines. After Task 2's edits (companion/app.py,
companion/test_browser_ux_helpers.py, companion/test_view_pages_helpers.py
— the only three files the plan's own interfaces section names), the grep
still finds descriptive **docstring prose** (not `#` comments, so not
filtered by the criterion's own pattern, and not code) in six files
outside that plan's list, none of which touch the actual module import or
call a moved seam:

- `companion/wake.py:3` — "server/poll_loop.py can ..." (describes where
  the wake-arithmetic caller lives)
- `companion/test_request_connections.py:9` — "`poll_loop.run_once()`
  nests its own ..."
- `companion/test_freshness_token.py:213,238` — "a second, identical
  `poll_loop.run_once()` cycle ..." (x2, in test docstrings)
- `companion/test_companion_app_05.py:1268` — "server/poll_loop.py's own
  `refresh_calendar_registry()` call shape ..."
- `companion/test_companion_app_helpers.py:122` — "calls
  `poll_loop.now_s()` (real ..."
- `companion/test_browser_ux_03.py:137` — "server/poll_loop.py writes
  them with ..."

These files are not in 39-10's Task 2 file list, and Phase 39's own
CONTEXT.md coordination note assigns `companion/` to a parallel Phase 40
session for this phase — touching them here would risk a needless merge
conflict with concurrent Phase 40 work for a purely cosmetic prose fix
(none of them import or call the moved module; every actual import/call
site in `companion/` was verified retargeted). Left as-is; a future
`companion/` pass (Phase 40, or a later 39-13 sweep if still present) can
reword this prose to say `poll_cycle` while it already has files open in
this area.
