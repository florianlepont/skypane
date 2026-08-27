---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 09
subsystem: ui
tags: [python, stdlib-http, sqlite, pillow, html-templating]

requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s
    provides: >-
      06-01's server/history_db.py (runway_events schema/readers), 06-03's
      server/panel_preview.py (panel.bin unpack + PNG encode), 06-05's
      companion/app.py router + gallery_entries()/PREVIEW_IMAGE_ROUTE/
      GALLERY_ROUTE_PREFIX, companion/layout.py's escape_html()/data_table()/
      status_dot()/empty_state(), and the two page-module stubs this plan
      completes
provides:
  - "CFG-06: a browsable, newest-first flight-history log with the same human-readable wording the panel uses (friendly aircraft-type labels, display-airline alias, ROUTE_FALLBACK_TEXT agreement)"
  - "CFG-11: a capped, newest-first render gallery served through the router's own listing-matched file route"
  - "CFG-10 (previously wired by 06-05) now carries the mandatory not-colour-accurate caveat and an honest no-panel-yet fallback instead of a broken image"
  - companion/pages/history_page.py's history_rows()/format_event_row() helpers
  - companion/pages/preview_page.py's preview_section()/gallery_tiles() helpers
  - "ctx[\"gallery_entries\"] as a documented, standing key in companion/pages/__init__.py's page-context contract"
affects: [06-10, 06-11, 06-12]

tech-stack:
  added: []
  patterns:
    - "A page module that needs pre-built markup (layout.status_dot()'s <span>) inside a table cell cannot route it through layout.data_table() — data_table() escapes every cell value it is given, which would print the dot's own tags as visible text. history_page.py builds its own table HTML instead, matching data_table()'s CSS classes for visual consistency."
    - "A page module reaches filesystem/router-owned listings (the gallery directory) only via a ctx key the router populates, never by importing companion.app itself — avoids the router-import cycle CFG-10/CFG-11 would otherwise create."

key-files:
  created:
    - companion/test_view_pages.py
  modified:
    - companion/pages/history_page.py
    - companion/pages/preview_page.py
    - companion/app.py
    - companion/pages/__init__.py

key-decisions:
  - "history_page.py reuses server.plane.render's display_airline_name()/_TYPE_DISPLAY_LABELS/ROUTE_FALLBACK_TEXT directly rather than a second web-only copy, so the History page can never drift from what the panel itself says about the same flight."
  - "history_page.py's Corroboration column bypasses layout.data_table() and builds its own <table> markup, since data_table()'s per-cell escaping cannot host layout.status_dot()'s pre-built HTML without corrupting it."
  - "preview_page.py reads the gallery listing from ctx[\"gallery_entries\"] (added to companion/app.py's page_context()) rather than importing companion.app, preserving the no-router-import-cycle rule the plan's own action text states."
  - "GALLERY_DISPLAY_LIMIT set to 12 — independent of and smaller than companion/app.py's own GALLERY_DEFAULT_LIMIT (30), so the display cap is a real, separately-enforced ceiling, not just relying on the router's own listing size."

requirements-completed: [CFG-06, CFG-10, CFG-11]

coverage:
  - id: D1
    description: "History page lists recent runway_events newest-first with the same human-readable wording (friendly aircraft type, display-airline alias, ROUTE_FALLBACK_TEXT) the panel itself uses, escapes every cell, and degrades to the health-unavailable copy on a locked/missing database"
    requirement: "CFG-06"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#Section 1 (9 checks: empty state, newest-first ordering, known/unknown aircraft-type label, route-fallback agreement, mono columns, hostile-callsign escaping, DB-unavailable degrade, no direct html import, no local _TYPE_DISPLAY_LABELS redefinition)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Preview page shows the live panel image with a mandatory not-colour-accurate caveat, omits a broken <img> when no panel exists, and contains no deferred simulate-a-flight control"
    requirement: "CFG-10"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#Section 2 (panel-present / panel-absent checks, no-<input> and no-companion.app-import source checks)"
        status: pass
      - kind: e2e
        ref: "companion/test_view_pages.py#_tabs_and_preview_image_end_to_end (GET /preview.png over a real subprocess, asserts PNG signature + image/png content type)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Render gallery renders a capped, newest-first grid of tiles built only from names the router's own listing helper returned, via /gallery/<name>"
    requirement: "CFG-11"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_gallery_entries_over_limit_capped_and_newest (fixed 30-entry pool independent of GALLERY_DISPLAY_LIMIT, so an inflated constant is caught by a tile-count mismatch, not masked by a bigger fixture)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 9: History & Preview Pages Summary

**companion/pages/history_page.py (CFG-06 flight log, reusing server.plane.render's presentation mappings) and companion/pages/preview_page.py (CFG-10/CFG-11 live panel + capped render gallery) completed; companion/test_view_pages.py added at 19/19 checks**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3/3 completed
- **Files modified:** 4 (companion/pages/history_page.py, companion/pages/preview_page.py, companion/app.py, companion/pages/__init__.py) + 1 created (companion/test_view_pages.py)

## Accomplishments

- The History page (CFG-06) reads `server.history_db.recent_runway_events()` and renders every event newest-first with the exact wording the panel itself would show for that flight — friendly aircraft-type labels and the display-airline alias come from `server.plane.render`, never a second web-only copy, and a missing airline or route falls back to the same `ROUTE_FALLBACK_TEXT` the panel uses.
- The Preview page (CFG-10/CFG-11) shows the live `panel.bin` image with a mandatory colour caveat (the preview uses nominal render-internal swatches, not colour-accurate Spectra 6 output) and an honest "no panel yet" sentence — never a broken `<img>` — when no panel exists yet; the render gallery below it is a capped, newest-first grid built only from filenames the router's own directory listing returned.
- `companion/app.py`'s `page_context()` now supplies `ctx["gallery_entries"]`, so `preview_page.py` can build gallery tile URLs without importing `companion.app` itself (which would be a router-import cycle) — `companion/pages/__init__.py`'s documented ctx contract was updated to record the new key.
- `companion/test_view_pages.py` (new, 19/19 checks) covers both pages' empty/populated states, per-cell escaping (a script-tag-shaped callsign), the History/panel wording-agreement check (reads `ROUTE_FALLBACK_TEXT` from the render module, never a literal), the gallery's display-limit cap and newest-first ordering (proven against a fixed-size fixture pool so an inflated `GALLERY_DISPLAY_LIMIT` is caught rather than masked), and one end-to-end HTTP round trip fetching a real PNG from `/preview.png` through a genuinely running `companion/app.py` subprocess.

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete the History page** - `d74f644` (feat)
2. **Task 2: Complete the Preview page** - `4da51c8` (feat)
3. **Task 3: Create companion/test_view_pages.py** - `3245051` (test)

**Plan metadata:** (this commit) — `docs: complete 06-09 plan`

## Files Created/Modified

- `companion/pages/history_page.py` - CFG-06's flight log: `history_rows()`, `format_event_row()`, a custom table builder that hosts `layout.status_dot()` markup (data_table() can't), `_safe_query()`-wrapped database access
- `companion/pages/preview_page.py` - CFG-10/CFG-11: `preview_section()` (live image + caveat + no-panel fallback), `gallery_tiles()` (capped, newest-first grid), no simulate-a-flight control (documented in the module docstring)
- `companion/app.py` - `Handler.page_context()` gained a `gallery_entries` key so `preview_page.py` never has to import the router
- `companion/pages/__init__.py` - documented ctx contract updated to record the new `gallery_entries` key
- `companion/test_view_pages.py` (new) - 19/19-check harness for both pages plus one end-to-end HTTP round trip

## Decisions Made

- `history_page.py`'s Corroboration column is rendered through a hand-built `<table>` (`_history_table_html()`), not `layout.data_table()`, because `data_table()` escapes every cell value — including a pre-built `<span>` from `layout.status_dot()` — which would print the dot's own HTML tags as visible text instead of rendering the coloured indicator. The rest of the table's cells are still escaped via `companion.layout.escape_html()`, and the table reuses `data_table()`'s exact CSS classes (`data-table`, `row`/`row-alt`, `mono`) so it is visually indistinguishable from the rest of the site.
- `GALLERY_DISPLAY_LIMIT` set to 12 (independent of, and smaller than, `companion/app.py`'s own `GALLERY_DEFAULT_LIMIT=30`) so the Preview page's cap is a real, separately-enforced ceiling rather than incidentally relying on the router's own listing size.
- The over-limit gallery-cap test seeds a fixed 30-file pool that does not scale with `preview_page.GALLERY_DISPLAY_LIMIT` — this was a deliberate self-correction during authoring (see Deviations below): an earlier draft sized the fixture pool relative to the constant under test, which meant deliberately inflating the constant (the plan's own acceptance criterion) did not make the check fail.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `import server.plane.render as render` collided with the page module's own required `render(ctx)` function name**
- **Found during:** Task 1, first ruff pass (F811 redefinition)
- **Issue:** Every `companion/pages/*.py` module must expose a top-level `render(ctx)` function per `companion/pages/__init__.py`'s documented contract; importing `server.plane.render` under its own module name shadowed that function.
- **Fix:** Imported it as `from server.plane import render as panel_render` instead, and referenced `panel_render.display_airline_name()` / `panel_render._TYPE_DISPLAY_LABELS` / `panel_render.ROUTE_FALLBACK_TEXT` throughout.
- **Files modified:** `companion/pages/history_page.py`
- **Verification:** `ruff check companion/` clean; `companion/test_view_pages.py` still 19/19.
- **Committed in:** `d74f644` (part of the task commit)

**2. [Rule 1 - Bug] Preview page's own docstring literally contained the forbidden `<input` substring**
- **Found during:** Task 2, running the plan's own acceptance-criteria greps by hand
- **Issue:** The module docstring's prose ("no `<input>` element of any kind") accidentally matched the acceptance criterion's own `grep -c "<input" == 0` check, since the docstring is part of the file's text.
- **Fix:** Reworded the docstring to say "no form-input element of any kind" instead, preserving the same documented intent without the literal substring.
- **Files modified:** `companion/pages/preview_page.py`
- **Verification:** `grep -c "<input" companion/pages/preview_page.py` returns 0.
- **Committed in:** `4da51c8` (part of the task commit)

**3. [Rule 1 - Bug] Gallery-cap test's fixture pool scaled with the constant it was meant to guard**
- **Found during:** Task 3, deliberately raising `GALLERY_DISPLAY_LIMIT` to confirm the plan's own acceptance criterion ("deliberately raising GALLERY_DISPLAY_LIMIT makes the cap check fail")
- **Issue:** The first draft generated `preview_page.GALLERY_DISPLAY_LIMIT + 5` gallery fixture files, so inflating the constant just produced a bigger fixture and the check kept passing — the acceptance criterion's own self-test failed.
- **Fix:** Fixed the fixture pool at a constant 30 entries, independent of the module's own constant, so list-slicing can never produce more tiles than the pool has; an inflated `GALLERY_DISPLAY_LIMIT` is now caught the moment `tile_count` stops matching it.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** Manually set `GALLERY_DISPLAY_LIMIT = 999`, confirmed the check failed with a clear message, reverted to `12`, confirmed all 19 checks pass again.
- **Committed in:** `3245051` (the fix was made before the file was ever committed, so no separate commit was needed)

---

**Total deviations:** 3 auto-fixed (3x Rule 1)
**Impact on plan:** All three were correctness fixes caught during authoring/verification, before any commit — no scope creep, no architectural change. `companion/app.py` and `companion/pages/__init__.py` were also touched, beyond the plan's stated `files_modified` list of just the two page modules and the test harness — but both edits were explicitly directed by the plan's own Task 2 action text ("add a `gallery_entries` key to the context `app.Handler.page_context()` builds"), not a deviation from scope, just a gap in the plan's own frontmatter `files_modified` list and the `<verification>` section's `git diff --stat` wording.

## Issues Encountered

None beyond the three auto-fixes documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

CFG-06/CFG-10/CFG-11 are now fully live end-to-end: the History and Preview tabs (already routed by 06-05) show real data instead of contract-complete stubs. Plans 06-10 (wiring `poll_loop.py` to actually write `runway_events` rows and name gallery files) and 06-12 (live host verification) can now exercise these pages against real production output rather than only test fixtures — `history_page.py`/`preview_page.py` make no assumptions about *how* those rows/files are produced, only about the schema/listing contracts `server/history_db.py` and `companion/app.py`'s `gallery_entries()` already define.

---
*Phase: 06-companion-configuration-web-interface-visual-settings-view-s*
*Completed: 2026-08-28*

## Self-Check: PASSED

All created/modified files verified present on disk; all three task commit hashes (d74f644, 4da51c8, 3245051) verified present in git log.
