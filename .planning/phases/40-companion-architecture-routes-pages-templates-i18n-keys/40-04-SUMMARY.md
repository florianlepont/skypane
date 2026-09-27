---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 04
subsystem: ui
tags: [python, stdlib, html-templating, refactor, companion]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "40-01's render-snapshot baseline harness (companion/testdata/render_baseline.json, test_render_baseline.py) used to prove byte-identical output"
provides:
  - "companion/layout.py split by responsibility into ui_base.py, ui_time.py, ui_nav.py, ui_components.py, ui_shell.py, each under the 1500-line ceiling"
  - "layout.py reduced to a re-export facade (__all__-backed explicit imports, no star imports) so every existing layout.X call site still resolves"
  - "page_shell()/login_shell() fill named templates (str.format_map over a descriptive-key dict) instead of positional %s substitution"
  - "page_shell and frame_strip_html each split into helpers under the 80-code-line ceiling"
affects: [companion-pages, companion-tests, sketch-findings-skypane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Facade module (layout.py) re-exporting a package of ui_*.py modules via explicit __all__-backed imports, never star imports"
    - "Named HTML template strings filled with str.format_map(dict) instead of positional %-formatting, for value-order safety"

key-files:
  created:
    - companion/ui_base.py
    - companion/ui_time.py
    - companion/ui_nav.py
    - companion/ui_components.py
    - companion/ui_shell.py
  modified:
    - companion/layout.py
    - companion/test_structure_guards.py

key-decisions:
  - "FLASH_SLOT_MARKER moved into ui_base.py (not co-located with either of its two consumers, page_header in ui_components and page_shell in ui_shell) since it is a dependency-free constant both downstream modules can import without creating a cross-edge"
  - "layout.py keeps a plain `import companion.i18n as i18n` (no longer used internally after the shell code moved out) because companion/test_status_pages_07.py and companion/test_config_page_02.py reach layout.i18n.t()/.t_lang() directly; added to __all__ so ruff's F401 recognises the re-export intent"
  - "test_structure_guards.py's PENDING_OVERSIZED_FILES/PENDING_LONG_FUNCTIONS allowlists updated in-place as each offender was fixed, per the file's own documented convention (trust companion_structure.py, update the sets)"

requirements-completed: [CMP-03, CMP-05, CMP-06]

# Metrics
duration: 24min
completed: 2026-09-27
---

# Phase 40 Plan 04: layout.py split + named templates Summary

**Split the 2597-line companion/layout.py into five ui_*.py modules behind a re-export facade, and converted page_shell()/login_shell() from positional %s templates to named str.format_map() templates while splitting page_shell and frame_strip_html under the 80-code-line ceiling — output byte-identical to the 40-01 render baseline throughout.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-27T09:13:38Z
- **Completed:** 2026-09-27T09:37:19Z
- **Tasks:** 2
- **Files modified:** 7 (5 created, 2 modified)

## Accomplishments
- `companion/layout.py` (2597 lines) split by responsibility: `ui_base.py` (constants, routes, icon sprite, escaping — 733 lines), `ui_time.py` (timestamp/relative-time formatting — 541 lines), `ui_nav.py` (sidebar/tab-bar/preferences renderers — 566 lines), `ui_components.py` (banners, status rows, stat tiles, quick-switch, frame strip, page header, data table — now 622 lines after the frame-strip split), `ui_shell.py` (the two full-document builders — 349 lines)
- `layout.py` reduced to a 444-line facade: every name any caller reaches via `layout.X` re-exported through explicit, alphabetised `from companion.ui_x import (...)` blocks (no star imports) plus a matching `__all__` tuple
- `PAGE_SHELL_TEMPLATE`/`LOGIN_SHELL_TEMPLATE` named templates replace positional `%s` substitution; `SITE_TITLE` now fills one named key (`site_title`) used three times instead of three positional slots
- `page_shell()` split into `_script_tags_html()` (keeps the `ValueError` contract verbatim), `_body_attrs_html()` (the `<body>` attribute concatenation, same order), `_splice_flash()` (`FLASH_SLOT_MARKER` handling) — down from 156 to well under 80 code lines
- `frame_strip_html()` split into `_frame_resolved_state()`, `_frame_delay_caption_html()`, `_frame_display_cell_html()`, `_frame_quiet_cell_html()`, `_frame_update_cell_html()` — down from 98 to well under 80 code lines
- Every served page (both languages, both themes, all `PAGE_REQUESTS`/`UNAUTH_REQUESTS` samples) verified byte-identical against `companion/testdata/render_baseline.json` after each task

## Task Commits

Each task was committed atomically:

1. **Task 1: Split layout.py by responsibility behind a re-export facade** - `910c0a2` (feat)
2. **Task 2: Named templates for page_shell/login_shell and function-size split** - `81243b6` (feat)

_No TDD tasks in this plan (task 2 carries `tdd="true"` at the plan-file level but its "test" was the pre-existing render-baseline/ValueError-contract suite, run before and after the change — no new failing test was authored since the behavior contract already existed)._

## Files Created/Modified
- `companion/ui_base.py` - module constants (site title, local timezone, nav route/label tables, icon sprite, quick-action/frame-strip wording, status-dot/stat-tile class tables), `nav_slug()`, `icon_html()`, `escape_html()`
- `companion/ui_time.py` - `parse_iso`/`age_seconds`/`_age_bucket` ladder, `relative_age_text`/`relative_future_text`/`duration_text`, `relative_time_html`, `absolute_and_relative`, `concise_timestamp_html`, `month_abbr`, `local_clock_text`, `freshness_line_html`
- `companion/ui_nav.py` - `sidebar_nav`, `_tab_bar_html`, `_mobile_nav_html`, `_theme_form_html`/`_lang_form_html`/`_logout_form_html`, `nav_status_html`, the `REFRESH_*`/`REFRESH_SWAP_SELECTORS_BY_PAGE` freshness-swap registry
- `companion/ui_components.py` - `flash_banner`, `anomaly_banner`, `status_dot`, `stat_tile`, `quick_switch_html`/`quick_switch_state_html`, `frame_strip_html` (now five helpers), `card_status_class`, `status_row`, `section_intro_html`, `empty_state`, `page_header`, `data_table`
- `companion/ui_shell.py` - `login_shell`, `page_shell` (now three helpers), `SHELL_SCRIPT_ORDER`, `GLOBAL_PAGE_SCRIPTS`, `PAGE_SHELL_TEMPLATE`/`LOGIN_SHELL_TEMPLATE`
- `companion/layout.py` - reduced to the public re-export facade (`__all__` plus explicit import lists from the five `ui_*.py` modules)
- `companion/test_structure_guards.py` - `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` allowlists updated as each offender moved/shrank (per the file's own "trust the helper, update the sets" convention)

## Decisions Made
- Grouped every layout.py top-level statement into contiguous blocks (splitting on true top-level blank lines, distinguishing them from blank lines inside a function/tuple/dict body by checking whether the following non-blank line is indented) to move code verbatim without losing any attached comment
- Placed `FLASH_SLOT_MARKER` in `ui_base.py` rather than co-locating it with either consumer, since it has no functional dependencies and both `ui_components.py` (page_header) and `ui_shell.py` (page_shell) can import it from the shared base layer without creating a cross-module edge
- Kept `import companion.i18n as i18n` in `layout.py` even though no code inside `layout.py` calls it directly any more, because `companion/test_status_pages_07.py` and `companion/test_config_page_02.py` reach `layout.i18n.t()`/`.t_lang()` as part of the public surface; added `"i18n"` to `__all__` so ruff's F401 unused-import check recognises the re-export as intentional

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated test_structure_guards.py's PENDING_LONG_FUNCTIONS/PENDING_OVERSIZED_FILES after each move**
- **Found during:** Task 1 (moving frame_strip_html to ui_components.py made `test_no_production_function_exceeds_the_code_line_ceiling` fail, since the allowlist still named the old `companion/layout.py::frame_strip_html` path)
- **Issue:** The guard test's allowlist is keyed by qualified path (`file::function`); moving a still-long function to a new file without updating the allowlist is a genuine new "offender" from the guard's point of view
- **Fix:** Task 1 commit repointed the `frame_strip_html` entry to `companion/ui_components.py::frame_strip_html`; Task 2 commit removed the `frame_strip_html` and `page_shell` entries (both now under the ceiling) and removed `companion/layout.py` from `PENDING_OVERSIZED_FILES` (now 444 lines, well under 1500) — exactly the "trust companion_structure.py, update these sets" maintenance the guard's own docstring calls for
- **Files modified:** companion/test_structure_guards.py
- **Verification:** `pytest companion/test_structure_guards.py` passes; `companion_structure.long_functions()`/`oversized_files()` filtered for `page_shell`/`frame_strip_html`/`layout`/`ui_` print `[]` twice
- **Committed in:** `910c0a2` (Task 1), `81243b6` (Task 2)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary bookkeeping for a guard test that tracks offenders by qualified name; no scope creep, no behavior change.

## Issues Encountered
- An early mechanical edit to insert the `__all__` tuple into `layout.py` accidentally deleted the `def login_shell(...)` line while relocating the block; caught immediately by a syntax check (`ast.parse`) before running any tests, and fixed with a follow-up `Edit` restoring the signature line. No test ever ran against the broken intermediate state.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `companion/layout.py` is now a thin facade; later plans in this phase (typed per-page context, shared body-drain helper, CSS token audit, i18n stable IDs) can target the five `ui_*.py` modules directly without re-touching this split
- `companion/pages/config_page.py` and `companion/pages/health_page.py` remain in `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` for a later plan in this phase to address
- No blockers for 40-05 onward

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All created files found on disk (companion/ui_base.py, companion/ui_time.py,
companion/ui_nav.py, companion/ui_components.py, companion/ui_shell.py,
companion/layout.py, companion/test_structure_guards.py). Both task commits
(910c0a2, 81243b6) found in git history.
