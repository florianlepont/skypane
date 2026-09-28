---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 09
subsystem: ui
tags: [companion, i18n, ota, nav, python]

# Dependency graph
requires:
  - phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
    provides: "server/firmware_registry.py's update_view(registry, device_report, now) (plan 01) -- the single view model this page renders, never recomputed"
provides:
  - "companion/pages/update_page.py: update_page(ctx, view, next_wake_text) rendering the Status card (running version, five-state row with dot class/timestamp, rollback banner, scheduled sentence, Cancel form) and the Version history card (per-row Install form or 'Not installable' text) from firmware_registry.update_view()"
  - "companion GET /update route (companion/routes.py), the Update entry point, session-required like every other page"
  - "Update as the third Advanced-group nav destination (Health, Device, Update) everywhere NAV_GROUPS is derived: sidebar, tab bar More sheet, header dropdown"
  - "companion/i18n_fr/update.py: the French forms for every new Update-page string, auto-registered through i18n_fr's package-level pkgutil discovery"
affects: [companion-update-install-cancel-actions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only page rendering: update_page() takes the already-computed view dict and never recomputes state -- server/firmware_registry.py's update_view() is the single view model, matching the plan's own contract"
    - "Install/Cancel forms are rendered as static markup (data-confirm, hidden version field) targeting routes a later plan (14) implements, not live yet -- proven by test assertions on the form markup itself, not a POST round-trip"

key-files:
  created:
    - companion/pages/update_page.py
    - companion/i18n_fr/update.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/test_companion_app_01.py
    - companion/test_i18n.py
    - companion/test_update_page.py
    - companion/testdata/render_baseline.json
    - test-support/companion_render_snapshot.py
    - .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/deferred-items.md

key-decisions:
  - "NAV_GROUPS/ICON_IDS/ICON_DEFS_HTML/NAV_ICON_IDS actually live in companion/ui_base.py post-Phase-40 refactor, not layout.py itself (a facade re-exporting them) -- Task 1 edited ui_base.py and re-exported UPDATE_ROUTE through layout.py to match (carried over from the prior executor's Task 1 commit)"
  - "companion/i18n_fr/__init__.py needed no edit despite the plan listing it as files_modified: BY_ID is built by pkgutil.iter_modules() over every sibling module in the package, so adding companion/i18n_fr/update.py alone registers its MESSAGES"
  - "Route table lives in companion/routes.py (Phase 40's route declaration list), not a do_GET dispatch in app.py -- GET /update declared there as session-required (Route(..., True)), matching every other tab route"

requirements-completed: []  # OTA-08 is shared with plan 14 (the Install/Cancel POST handlers and their
                             # confirmation flow); this plan renders only the read side (D-02, D-03, D-05
                             # visibility, D-06/D-11 installability, D-07 notes), so REQUIREMENTS.md is left
                             # Pending here per this phase's established convention (see 42-01/42-03/42-07/
                             # 42-08's precedent) -- only plan 14 or the phase's own close-out plan should
                             # flip OTA-08 to Complete.

coverage:
  - id: D1
    description: "Update is the third Advanced nav destination (after Health, Device) everywhere NAV_GROUPS is derived -- sidebar, tab bar More sheet, header dropdown preferences panel (unchanged) -- with its own icon-nav-update sprite symbol and French label 'Mise à jour'"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_page.py -- Task 1 nav/icon/FR-label tests"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app_01.py::test_nav_tabs_shrunk_to_four_settled_order, ::test_icon_sprite_integrity, ::test_page_shell_emits_sprite_once_no_inline_styles"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /update renders the Status card (running version, five-state row + dot class + timestamp, scheduled sentence, Cancel form, rollback banner) and the Version history card (newest-first rows, per-row Install form or 'Not installable' text, escaped notes, mono version tags) in English and French, behind the existing session gate"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_page.py -- Task 2 (empty state, releases ordering/Install form, below-floor Not-installable, five states with dot classes, scheduled sentence + Cancel, in-progress hides Cancel, rollback banner, escaped notes, French render, unauthenticated redirect, end-to-end scheduled render)"
        status: pass
      - kind: unit
        ref: "companion/test_i18n.py (no new English string lacks a French form)"
        status: pass
      - kind: other
        ref: "grep -cE '#[0-9A-Fa-f]{6}' companion/pages/update_page.py == 0 (no hard-coded colour)"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min (continuation session; Task 1 committed by a prior session that stopped on an API rate limit)
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 09: Companion Update Page (read side) Summary

**Companion `/update` page rendering `firmware_registry.update_view()` as a Status card and a Version history card, in English and French, reached from a new Update nav destination -- Install/Cancel POST handlers are plan 14's own routes.**

## Performance

- **Duration:** ~35 min (this continuation session)
- **Completed:** 2026-09-28
- **Tasks:** 2/2
- **Files modified:** 10 (this session's Task 2 commit) + 6 (Task 1's earlier commit)

## Accomplishments
- Update is the third Advanced-group nav destination (Health, Device, Update) everywhere NAV_GROUPS is derived: sidebar, tab bar More sheet, header dropdown -- one new `icon-nav-update` sprite symbol, French label "Mise à jour"
- `companion/pages/update_page.py` renders the Status card (running version, five-state row with its own dot class and timestamp, scheduled "installs at the next wake" sentence, Cancel form when cancellable, warn-toned rollback banner) and the Version history card (newest-first rows, per-row Install form with `data-confirm` and a hidden version field, or plain "Not installable" text for below-floor releases, escaped notes, monospace version tags)
- `GET /update` is wired into `companion/routes.py`'s route table as session-required, loading the view via `firmware_registry.update_view()` and the next-wake clock text via `server.wake.next_wake_at_iso()`
- `companion/i18n_fr/update.py` supplies every new string's French form, auto-discovered through `i18n_fr`'s existing `pkgutil.iter_modules()` package init (no edit to `__init__.py` needed)
- Full companion suite (`pytest -q companion -m "not browser"`, 1762 tests) and ruff pass; the only 3 failures are pre-existing, out-of-scope, and logged in `deferred-items.md`

## Task Commits

Each task was committed atomically:

1. **Task 1: Navigation entry, icon and FR nav label** - `f9f94619` (feat) -- committed by the prior session before it stopped on an API rate limit; verified present via `git show --stat f9f94619` at the start of this continuation
2. **Task 2: Update page (Status and Version history cards) and GET route** - `88bc5e41` (feat) -- this session: reviewed the prior session's uncommitted working-tree diff against the plan, kept every file (all genuinely required), ran the plan's verify commands plus the full companion suite, then committed

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

## Files Created/Modified
- `companion/pages/update_page.py` - the Status and Version history card renderers, `update_page()` and `render()`
- `companion/i18n_fr/update.py` - French forms for every new Update-page string
- `companion/routes.py` - GET /update route declaration, session-required
- `companion/app.py` - `UPDATE_ROUTE` re-export and the `_PAGE_SCRIPTS` entry for the confirm-submit script the per-row Install forms rely on
- `companion/test_update_page.py` - Task 2's behaviour tests (empty state, ordering, floor, all five states, scheduled/Cancel, in-progress hides Cancel, rollback banner, escaped notes, French, session redirect, end-to-end render)
- `companion/test_companion_app_01.py` - `test_icon_sprite_integrity` / `test_page_shell_emits_sprite_once_no_inline_styles` counts corrected from 23 to 24 symbols (Task 1's `icon-nav-update` addition had grown the sprite without these two pre-existing guards being updated)
- `companion/test_i18n.py` - `_UNCHANGED_IN_FRENCH` cognate allowlist gained `update.version`/`update.date` (identical EN/FR spellings)
- `test-support/companion_render_snapshot.py` - `PAGE_REQUESTS`/`_UNAUTH_GET_REQUESTS` gained `/update` alongside the other six `NAV_TABS` routes
- `companion/testdata/render_baseline.json` - regenerated fixture; diffed against its prior version to confirm every changed page's delta is exactly the new sidebar link, its mobile-nav link and the `icon-nav-update` sprite symbol
- `.planning/phases/42-.../deferred-items.md` - two more pre-existing, out-of-scope failures logged (see Issues Encountered)

## Decisions Made
- Kept the route declaration in `companion/routes.py`'s Phase-40 route table (`Route("GET", Exact(UPDATE_ROUTE), lambda h, m: h._render_tab(UPDATE_ROUTE, update_page.render), True)`) rather than a `do_GET` dispatch, matching every other tab page on main
- `companion/i18n_fr/__init__.py` required no edit: its `BY_ID` catalogue is built by walking every sibling module in the package at import time, so `companion/i18n_fr/update.py` alone was sufficient despite the plan listing `__init__.py` as `files_modified`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected two pre-existing icon-sprite-count guard tests from 23 to 24**
- **Found during:** Task 2's full-suite verification (`pytest -q companion -m "not browser"`)
- **Issue:** Task 1's `icon-nav-update` symbol grew `layout.ICON_IDS`/`ICON_DEFS_HTML` to 24 members, but `test_icon_sprite_integrity` and `test_page_shell_emits_sprite_once_no_inline_styles` in `companion/test_companion_app_01.py` still hard-coded 23. Task 1's own verify command (`test_update_page.py test_suite_guards.py`) didn't exercise these two tests, so the break was silent until the full suite ran.
- **Fix:** Updated both counts (and their explanatory comments) to 24
- **Files modified:** `companion/test_companion_app_01.py`
- **Verification:** `pytest -q companion -m "not browser"` -- both tests pass
- **Committed in:** `88bc5e41` (Task 2 commit)

**2. [Rule 1/3 - Guard extension] Extended three shared cross-page fixtures to the new /update route**
- **Found during:** Task 2's own verify commands and full-suite run
- **Issue:** `companion/test_i18n.py`'s cognate allowlist, `test-support/companion_render_snapshot.py`'s route list and its generated `companion/testdata/render_baseline.json` fixture all enumerate every live page/route; without `/update` added, the i18n cognate test would flag `update.version`/`update.date` as untranslated, and the render-snapshot machinery would simply never exercise the new page
- **Fix:** Added `update.version`/`update.date` to `_UNCHANGED_IN_FRENCH` (identical EN/FR spellings, same pattern as existing entries); added `UPDATE_ROUTE` to `PAGE_REQUESTS`/`_UNAUTH_GET_REQUESTS`; regenerated `render_baseline.json` and diffed it programmatically against its prior committed version to confirm every one of the 40 changed baseline entries differs by exactly the new sidebar link, mobile-nav link and `icon-nav-update` sprite symbol -- nothing else
- **Files modified:** `companion/test_i18n.py`, `test-support/companion_render_snapshot.py`, `companion/testdata/render_baseline.json`
- **Verification:** `pytest -q companion/test_i18n.py` and the render-snapshot test both pass; programmatic diff confirmed no unrelated baseline drift
- **Committed in:** `88bc5e41` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 guard-fixture extension)
**Impact on plan:** Both necessary for the plan's own acceptance criterion (a green full companion suite run) and for the shared fixtures to keep proving what they already claim to prove. No scope creep -- every touched file outside the plan's `files_modified` list was a pre-existing cross-page guard/fixture that needed to learn about the new page, not new functionality.

## Issues Encountered
- `companion/test_suite_guards.py::test_no_legacy_runner_anywhere` fails (pre-existing, caused by `stub-server/test_ota_offer.py`'s trailing `if __name__ == "__main__"` block from plan 42-07, already logged in `deferred-items.md` by the prior Task 1 session)
- `companion/test_app_server_fixture.py::test_stop_kills_the_whole_process_group_including_a_grandchild` and `::test_child_env_carries_no_network_var_and_pythonpath` fail (macOS sandbox limitations -- a killpg-signal-delivery race and a `/proc/<pid>/environ` read that doesn't exist on macOS -- both newly logged to `deferred-items.md` this session; neither test touches any file this plan modified)
- All three are also present, identically, on the unmodified baseline per this project's documented "20 deploy/test-support tests fail identically on origin/main here" environment note

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 14 can now implement the live `/update/install` and `/update/cancel` POST handlers against the form markup this plan already renders (`data-confirm`, hidden `version` field, quiet-button Cancel class)
- OTA-08 stays Pending in REQUIREMENTS.md until plan 14 completes the write side

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*
