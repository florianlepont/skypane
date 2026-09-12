---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 08
subsystem: ui
tags: [theme-preview, live-render, cache-key, static-script, csp, six-touch-point]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/prefs.py, companion/i18n.py, ctx[\"lang\"]/ctx[\"simple_mode\"] (not consumed directly by this plan's server-side code, but this plan's files sit alongside them)"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-03: layout.status_row()/section_intro_html() (not consumed by this plan; listed as a wave dependency only)"
provides:
  - "theme_preview.preview_png_bytes()/cache_path()/preview_signature()/cached_preview_bytes() — an optional live_event/live_event_id axis (D-23): a runway_events row renders instead of the fixed fictional scene, cache-keyed on the event's own row id"
  - "companion/app.py: GET /theme-preview/{id}.png?live=1 reads the most recent runway_events row (_safe_latest_runway_event(), any exception degrading to the sample scene) and threads it through to the cache"
  - "companion/app.py + companion/layout.py: THEME_PREVIEW_SCRIPT_ROUTE/_THEME_PREVIEW_JS_PATH/_serve_theme_preview_script()/the do_GET() dispatch line/THEME_PREVIEW_SCRIPT_SRC/page_shell()'s tenth script tag — the full six-touch-point contract for theme-preview.js"
  - "companion/static/theme-preview.js — the chip-selection live-preview src swap, event-delegated, ES5-safe, no HTML-writing sink"
affects: [20-11-airlines-live-preview-markup, 20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cache-key discriminator folded from a database row's own autoincrement id, int()-coerced with any coercion failure degrading to a fixed 'sample' literal — never a string field from the row reaching a path component (T-20-14)"
    - "a route-local _safe_*() query helper (mirroring _safe_last_checkin_ts()'s shape) that degrades ANY exception to None rather than the narrower (sqlite3.Error, OSError) catch its sibling uses, because this plan's own instruction requires zero 500s from this one read"
    - "the six-touch-point duplicated-not-imported static-script contract (route+path constants and a thin serve delegate in app.py, a mirrored SRC constant and page_shell() tag in layout.py, a cross-file route==src test) applied to a tenth script"

key-files:
  created:
    - companion/static/theme-preview.js
  modified:
    - companion/theme_preview.py
    - companion/app.py
    - companion/layout.py
    - companion/test_companion_app.py

key-decisions:
  - "cache_path()/preview_signature() always build the 3-part filename/digest shape (\"%s-%s-%s.png\" % (theme_id, event_id or 'sample', signature), digest folding in live_event_id even when None) rather than conditionally staying 2-part for the no-event case — the plan's own <action> text gives this literal template unconditionally, and no existing test (before this plan) hardcoded the old 2-part filename string, so this is fully backward-compatible with every existing call site even though the literal on-disk filename for the no-event/chip-grid case changes shape (a one-time cache-warmup cost, not a correctness issue)."
  - "_safe_latest_runway_event() uses a deliberately broad `except Exception` (not the narrower (sqlite3.Error, OSError) its sibling _safe_last_checkin_ts() uses), because this plan's own action text says ANY exception reading the event must degrade to the sample scene, never a 500."
  - "the GET /static/theme-preview.js public-serving check (named in Task 2's own action text) was deferred to Task 3's commit, since Task 2's own <files> list excludes companion/static/theme-preview.js and the file does not exist until Task 3 creates it — see Deviations below."
  - "theme-preview.js reads data-preview-src from the changed radio input's parentNode (the <label> config_page._theme_chip_grid_html() wraps each radio in), not from the input itself or via .closest() — matching the exact, already-shipped chip markup shape and avoiding a DOM method with a narrower support floor than this codebase's other scripts use."

requirements-completed: [CFG-16, CFG-13]

# Metrics
duration: 55min
completed: 2026-09-11
---

# Phase 20 Plan 08: Live theme preview — render, cache key, and the chip-selection script Summary

**`/theme-preview/{id}.png?live=1` renders the last real runway event with an event-id-keyed cache (never a stale hit after a newer flight), and `theme-preview.js` swaps the live preview's `src` on chip selection through the full six-touch-point static-script contract — the chip grid itself keeps rendering the fixed fictional scene, unchanged.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-11 (approx.)
- **Completed:** 2026-09-11
- **Tasks:** 3
- **Files modified:** 4 (1 created, 4 modified — theme_preview.py, app.py, layout.py, test_companion_app.py)

## Accomplishments
- `theme_preview.py` grew an optional `live_event`/`live_event_id` axis on every one of its four functions, mapping a `runway_events` row onto `build_canvas()`'s `flight`/`route`/`state` args with a fixture fallback for every field the row lacks (D-23) — the no-event path stays behaviourally unchanged (same rendered bytes, same cold/warm-cache contract)
- The cache key now folds in the event's own row id (int()-coerced; any coercion failure or hostile string degrades to the literal `"sample"`, never reaching a path component, T-20-14) — a newer flight is a cache miss, never a stale hit served forever (Pitfall 7), verified end-to-end against a real running service (seed an event, request twice — same cached bytes; seed a newer event — new bytes, new cache file)
- `GET /theme-preview/{id}.png?live=1` reads the single most recent runway event via a new `_safe_latest_runway_event()` helper (any exception degrades to the sample scene, never a 500); the membership test on `theme_id` remains the route's first statement
- `theme-preview.js` (new): guard-clause-first, ES5-safe, event-delegated `change` listener on the chip grid, writing exactly one `<img src>` assignment from a chip's `data-preview-src` attribute — no fetch, no timer, no HTML-writing sink
- The full six-touch-point contract landed for the tenth static script: `THEME_PREVIEW_SCRIPT_ROUTE`/`_THEME_PREVIEW_JS_PATH`/`_serve_theme_preview_script()`/the `do_GET()` dispatch line in `app.py`, and `THEME_PREVIEW_SCRIPT_SRC`/the tenth `page_shell()` script tag in `layout.py`, with a cross-file route==src equality check

## Task Commits

1. **Task 1: the live-event render path and the event-aware cache key** - `8c5f3da` (feat)
2. **Task 2: the ?live=1 route branch and the script's server-side touch points** - `87b3f15` (feat)
3. **Task 3: theme-preview.js and its layout-side touch points** - `16478fa` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/theme_preview.py` - `_live_flight_route_state()` (new, the row-to-`build_canvas()`-args mapper with fixture fallback), `preview_png_bytes(theme_id, live_event=None)`, `preview_signature(theme_id, live_event_id=None)`, `cache_path(state_dir, theme_id, live_event_id=None)` (int()-coercion, "sample" fallback), `cached_preview_bytes(state_dir, theme_id, live_event=None)`; module docstring point 2 rewritten to state the chip grid still renders the fixed scene
- `companion/app.py` - `_safe_latest_runway_event()` (new, broad-exception-degrading query helper); `_serve_theme_preview_image()` now parses `?live=` via `page_context()`'s own `urlsplit`/`parse_qs` idiom and threads the row through to `cached_preview_bytes()`; updated security comment naming D-23; `THEME_PREVIEW_SCRIPT_ROUTE`/`_THEME_PREVIEW_JS_PATH`/`_serve_theme_preview_script()`/`do_GET()` dispatch line
- `companion/layout.py` - `THEME_PREVIEW_SCRIPT_SRC` (duplicated-not-imported, per the standing contract), `page_shell()`'s tenth deferred `<script>` tag
- `companion/static/theme-preview.js` (new) - the chip-selection live-preview `src` swap
- `companion/test_companion_app.py` - Task 1: 6 new checks (no-event path stability, distinct/same event ids, hostile-id degradation, full/partial-row rendering, no-event `cached_preview_bytes()` parity); Task 2: 5 new checks (`?live=1` with/without a seeded event, same-event cache reuse, newer-event cache miss, unknown theme 404, `?live=0`/missing-query sample fallback); Task 3: 4 new checks (public route, ES5-safe/no-HTML-write, route/src agreement, exactly-one-script-tag/no-bare-inline-script) plus the nine-to-ten deferred-scripts retarget; `EXPECTED_CHECK_COUNT` 227 → 233 → 238 → 242

## Decisions Made
See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deferred the "GET /static/theme-preview.js" check from Task 2 to Task 3**
- **Found during:** Task 2
- **Issue:** Task 2's own action text lists "GET /static/theme-preview.js returns 200 with a JavaScript content type" among its new checks, but Task 2's own `<files>` list is `companion/app.py, companion/test_companion_app.py` — it does not include `companion/static/theme-preview.js`, which Task 3 creates. Adding that check at Task 2's commit would fail (the file does not exist yet, so `_serve_theme_preview_script()` 404s), breaking the requirement that every commit's own `<verify>` passes at that commit — the exact tension 20-01-SUMMARY.md's own Rule 3 deviation documents for a materially identical reason.
- **Fix:** Added every OTHER Task 2 check (the `?live=1` route-branch behaviour) at Task 2's commit; moved the static-script-serving check to Task 3's commit, where the file first exists, folded into that task's own three-check family for the new script.
- **Files modified:** `companion/test_companion_app.py` (check placement only; no behaviour change)
- **Verification:** `companion/test_companion_app.py` reports 236/238 (the two documented root-sandbox FAILs) at the Task 2 commit, and 240/242 at the Task 3 commit.
- **Committed in:** `87b3f15` (Task 2 commit, deferred check noted in its own `EXPECTED_CHECK_COUNT` comment) / `16478fa` (Task 3 commit, where the deferred check actually lands)

**2. [Rule 1 - Bug] Removed backticks and re-worded a repeated-token comment in theme-preview.js**
- **Found during:** Task 3, running the file's own new ES5-safe/no-HTML-write check
- **Issue:** The header comment's own prose used backtick-quoting (`` `src` ``) and one occurrence of the literal phrase `addEventListener("change", ...)` to describe the file's behaviour — both accidentally tripped the very banned-token/required-count checks the comment was describing, a self-referential false positive of the same shape 20-01-SUMMARY.md documents for a docstring.
- **Fix:** Re-worded the prose to describe the same facts without repeating the literal banned substring or duplicating the exact call-site text (`"src"` in plain quotes; "change-event-on-the-form idiom" instead of the literal call). No behaviour change.
- **Files modified:** `companion/static/theme-preview.js`
- **Verification:** `grep -c "innerHTML\|document.write\|eval(" companion/static/theme-preview.js` → `0`; `grep -c "addEventListener(\"change\"" companion/static/theme-preview.js` → `1`; the file's own new harness check passes.
- **Committed in:** `16478fa` (Task 3 commit)

**3. [Rule 1 - Bug] Removed an unused local variable flagged by ruff**
- **Found during:** Task 3, running `ruff check .` before committing (per CI lint requirement)
- **Issue:** `_theme_preview_cached_bytes_live_event_keyed_by_id()`'s first `cached_preview_bytes()` call result was assigned to an unused `first` variable.
- **Fix:** Dropped the assignment; the call's side effect (creating the cache file) is what the check actually needs.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `ruff check .` → "All checks passed!"
- **Committed in:** `16478fa` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking check-reordering, 2 bugs — a self-referential grep false positive and a lint warning)
**Impact on plan:** No scope creep and no behaviour change from what the plan specified — all three fixes are check-placement, comment-wording, or dead-code corrections needed for every commit to pass its own verification.

## Issues Encountered

- **Two of the plan's own literal acceptance-criteria greps could not be satisfied exactly as worded, for reasons unrelated to this plan's diff** — noted here rather than silently "passed", following the exact precedent 20-04-SUMMARY.md documents for its own stale greps:
  1. `grep -c "convert(\"RGB\")" companion/theme_preview.py` is expected to output `1`; it outputs `3` both before and after this plan's changes (confirmed via `git show HEAD~3:companion/theme_preview.py`, the pre-plan baseline) — two of the three occurrences are pre-existing docstring prose (`"Ordering is load-bearing: ..."`, `"... canvas.convert(\"RGB\").save(...) ..."`), not new code this plan added. The actual code line (`rgb = canvas.convert("RGB")`) still appears exactly once and still precedes the crop, which is the substantive requirement the criterion exists to protect.
  2. `grep -c "THEME_PREVIEW_SCRIPT_ROUTE" companion/app.py` is expected to output "at least 3 (constant, delegate, dispatch)"; it outputs `2`. Checked every one of the nine pre-existing sibling `*_SCRIPT_ROUTE` constants (`PANEL_LOOKUP_SCRIPT_ROUTE`, `POLL_COOLDOWN_SCRIPT_ROUTE`, `FLASH_CLEANUP_SCRIPT_ROUTE`, `CONFIRM_SUBMIT_SCRIPT_ROUTE`, `DIRTY_STATE_SCRIPT_ROUTE`) — every single one also outputs exactly `2` (the constant definition plus the `do_GET()` dispatch line; the delegate method itself never references the route constant by name, only its own `_*_JS_PATH` constant). `THEME_PREVIEW_SCRIPT_ROUTE` follows the established codebase convention exactly; the criterion's "delegate" clause does not match how any sibling in this codebase is actually written.
- No other issues — every task's own `<verify>` command passed as specified, and the full local suite (`scripts/run-all-tests.sh`) shows exactly the five documented root-sandbox failures (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`), identical to `main`.

## Known Stubs

None — every function and script this plan ships is real, immediately-effective code. The markup that will actually place `.theme-live-preview`/`data-preview-src`/`.theme-chip-grid` on a page is 20-11's, per this plan's own explicit scope boundary; until 20-11 lands, `theme-preview.js`'s guard clause makes it a safe, inert no-op on every existing page (proven by the full test suite passing unchanged on every page module this plan does not touch), and the `?live=1` route is reachable and correct today via direct URL even without that markup.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `/theme-preview/{id}.png?live=1` is fully implemented, cached, and tested end-to-end against a real running service; `theme_preview.cached_preview_bytes(..., live_event=row)` is the exact call shape 20-11's markup plan can rely on.
- `theme-preview.js` is served, loaded by every page via `page_shell()`, and proven equal (`layout.THEME_PREVIEW_SCRIPT_SRC == app.THEME_PREVIEW_SCRIPT_ROUTE`) — 20-11 need only render `.theme-live-preview img` (with an initial server-rendered `src`) and give each chip's `<label>` a `data-preview-src` attribute; no further script-side work is needed.
- `companion/test_view_pages.py` (85/85), `companion/test_config_page.py` (181/181), and `companion/test_i18n.py` (11/11) are confirmed unmoved by this plan.
- No blockers for 20-11 (wave 5) or 20-06/20-07 (this wave's siblings, which own `home_page.py`/`screens.py`/`config_page.py` respectively — none of this plan's files overlap theirs).

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: companion/theme_preview.py
- FOUND: companion/app.py
- FOUND: companion/layout.py
- FOUND: companion/static/theme-preview.js
- FOUND: companion/test_companion_app.py
- FOUND commit: 8c5f3da (Task 1)
- FOUND commit: 87b3f15 (Task 2)
- FOUND commit: 16478fa (Task 3)
