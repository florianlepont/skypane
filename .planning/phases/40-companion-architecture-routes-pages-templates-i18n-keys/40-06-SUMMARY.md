---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 06
subsystem: ui
tags: [svg, drawing-contract, health-page, companion, refactor]

# Dependency graph
requires:
  - phase: 40-01
    provides: the render-baseline snapshot harness (companion_render_snapshot.py, testdata/render_baseline.json) this plan's chart baseline reuses the same freeze/capture conventions from
provides:
  - companion/battery_chart.py, the battery-trend chart built entirely on companion/draw.py's shared primitives (percent_x/percent_y, rect/line/circle/polygon, label_span), byte-identical to the pre-migration chart
  - companion/health_signals.py, the markup-free severity/anomaly/state computation extracted out of companion/pages/health_page.py, importable with no page dependency
  - draw.polygon(), draw.area_canvas() and label_span()'s class_name parameter, three new companion/draw.py primitives
affects: [40-companion-architecture, companion-health-page, companion-draw-module]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SVG drawings are built exclusively from companion/draw.py's primitives; a drawing's own class vocabulary is declared as DRAWING_CHART_* constants in draw.py and folded into DRAWING_CLASSES (except classes deliberately styled only via a higher-specificity selector, which are excluded from that registry with a documented reason)"
    - "Markup-free state/signal computation lives in its own non-page module (companion/health_signals.py) that a page module imports and re-exports under historical names, never the reverse — page modules build markup, signal modules never do"
    - "A monkeypatch must target the module a function is DEFINED in, not a module that merely re-exports it, since Python resolves a bare-name call via the defining module's own globals"

key-files:
  created:
    - companion/battery_chart.py
    - companion/health_signals.py
    - companion/testdata/battery_chart_baseline.json
  modified:
    - companion/draw.py
    - companion/pages/health_page.py
    - companion/test_companion_app_02.py
    - companion/test_health_signals.py
    - companion/test_page_context.py

key-decisions:
  - "CFG-39 MIGRATE: battery_sparkline_svg() rebuilt entirely on draw.py primitives (draw.percent_y/percent_x, draw.rect/line/circle/polygon, draw.area_canvas, draw.label_span), byte-identical for 8 named cases including a hostile timestamp string"
  - "draw.DRAWING_CHART_CANVAS_CLASS (sparkline__canvas) and DRAWING_CHART_AREA_LAYER_CLASS (sparkline__area) are deliberately excluded from draw.DRAWING_CLASSES: style.css sizes both through one higher-specificity selector and carries no bare rule for either by design, so including them would make the class-resolves-in-CSS contract fail two classes that are correct by design"
  - "health_state_from_signals()/compute_health_state()/safe_health_state() stay in health_page.py (not moved to health_signals.py) because they call the page's own _x_section() markup builders; health_signals.py must never import health_page.py, so moving them would require the forbidden import direction"
  - "_battery_trend_caption() and _latest_numeric_battery_reading() also moved to health_signals.py beyond the plan's explicit list: both are pure data/text functions with no HTML, fitting health_signals.py's own charter, and moving them narrows (but does not close) the file-size gap"
  - "health_page.py ends at 1681 lines, still above the plan's 1500-line target (down from 2516 pre-plan) — see Deviations"

requirements-completed: [CFG-39]

# Metrics
duration: 45min
completed: 2026-09-27
---

# Phase 40 Plan 06: Battery chart onto draw.py + Health signal extraction Summary

**Migrated the battery-trend chart onto companion/draw.py's shared SVG primitives (byte-identical, backed by a committed baseline) and extracted Health's markup-free severity computation into companion/health_signals.py, shrinking companion/pages/health_page.py from 2516 to 1681 lines.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-27T12:52Z
- **Completed:** 2026-09-27T13:38Z
- **Tasks:** 2
- **Files modified:** 9 (3 created, 6 modified)

## Accomplishments
- `companion/battery_chart.py`: `battery_sparkline_svg()` and every helper it needs, built entirely on `companion/draw.py`'s scale (`percent_x`/`percent_y`) and shape primitives (`rect`/`line`/`circle`/`polygon`/`label_span`/`percent_canvas`), plus a new `draw.area_canvas()` primitive for the chart's nested private-viewBox area layer. Verified byte-identical to the pre-migration chart across eight named input cases (no rows, one row, two rows, a dense 90-point series, out-of-range readings, a daily series, a threshold-visible series, and a hostile firmware/timestamp string), committed as `companion/testdata/battery_chart_baseline.json`.
- The chart's class vocabulary (`sparkline-hit`, `sparkline-dot`, `sparkline-line`, `sparkline-axis`, `sparkline-area`, `sparkline-mark`, `sparkline-threshold`, `sparkline-legend*`, `sparkline-axis-label`, `sparkline`, `sparkline__y`, `sparkline__x`) is declared in `draw.py`'s `DRAWING_CLASSES` registry, so the existing class-resolves-in-CSS, no-colour-literal, escaping and no-script drawing-contract tests now cover the chart the same way they cover the ring gauge, day band and regularity grid.
- `companion/health_signals.py`: the markup-free half of Health's severity computation (`health_signals()`, `safe_health_signals()`, `_device_state()`/`_pipeline_state()`/`_battery_state()`/`_disagreement_warn()`, `collect_anomalies()`, `overall_severity()`, `staleness_status()`, `offbox_backup_status()`, the battery-query functions, `unresolved_rows()`/`coverage_status()`, `_read_health_inputs()`), built with zero HTML and no dependency on any page module.
- `companion/pages/health_page.py` re-exports every moved name under its historical name, so every existing test and cross-module caller (`companion/app.py`'s lazy context loaders, the nav-dot/banner severity path) kept working unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Chart equivalence baseline, then migrate the chart onto draw.py** - `607c4ac` (feat)
2. **Task 2: Extract the health-signal logic and bring health_page.py under the ceiling** - `60f3b3f` (feat)
3. **Follow-up fix: reword health_page prose references in the two new modules** - `7346d20` (fix)

_No plan-metadata-only commit was made separately; this summary and STATE.md updates land in the closing commit noted below._

## Files Created/Modified
- `companion/draw.py` - Added `DRAWING_CHART_*` class constants (folded into `DRAWING_CLASSES`, except the two classes styled only via a higher-specificity selector), `polygon()`, `area_canvas()`, and an optional `class_name` parameter on `label_span()`
- `companion/battery_chart.py` - New module: `battery_sparkline_svg()` and its helpers, built on `draw.py`
- `companion/testdata/battery_chart_baseline.json` - Committed pre-migration chart markup for 8 named input cases
- `companion/health_signals.py` - New module: the markup-free severity/anomaly/state computation
- `companion/pages/health_page.py` - Chart and signal logic replaced with re-exports; markup builders (`_device_section()`, `_pipeline_section()`, `_battery_section()`, `_corroboration_section()`, `health_state_from_signals()`, `compute_health_state()`, `safe_health_state()`, `render()`, the registry/stats/check-in sections) stay, since they still need the page's own tile-building helpers
- `companion/test_companion_app_02.py` - Added `test_battery_chart_markup_is_unchanged()` and `CHART_CASES`, and appended chart samples to the drawing contract
- `companion/test_health_signals.py` - Retargeted the `_read_health_inputs` monkeypatch onto the `companion.health_signals` module (see Decisions)
- `companion/test_page_context.py` - Retargeted the two `health_signals` monkeypatches onto the `companion.health_signals` module; `health_state_from_signals` patches stay on `health_page` (unaffected, since `companion/app.py` calls it through a `health_page.health_state_from_signals(...)` attribute lookup)

## Decisions Made
- Kept `health_state_from_signals()`/`compute_health_state()`/`safe_health_state()` in `health_page.py` per the plan's own conditional (they call the page's markup builders; `health_signals.py` must never import `health_page.py`).
- Excluded `DRAWING_CHART_CANVAS_CLASS`/`DRAWING_CHART_AREA_LAYER_CLASS` from `draw.DRAWING_CLASSES` (Rule 1 auto-fix — see Deviations).
- Moved two additional pure-data functions (`_battery_trend_caption()`, `_latest_numeric_battery_reading()`) to `health_signals.py` beyond the plan's explicit list, since both fit its "markup-free" charter and further narrow the file-size gap.
- Retargeted two test monkeypatches from `health_page` onto the `health_signals` module per the plan's own instruction (a patch on a re-export does not reach a bare-name call inside the function's defining module).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Excluded two classes from draw.DRAWING_CLASSES that carry no CSS rule by design**
- **Found during:** Task 1 verification (`test_every_drawing_class_resolves_in_the_served_stylesheet`)
- **Issue:** Adding all eleven `DRAWING_CHART_*` constants to `draw.DRAWING_CLASSES` (as the plan's must_haves literally state) failed the existing class-resolves-in-CSS contract test for two of them: `sparkline__canvas` and `sparkline__area` deliberately carry no bare CSS rule — `style.css`'s `.battery-trend-section svg:not(.icon)` rule (specificity 0,2,1) is the ONE place that sizes both `<svg>` elements, by explicit design (see that rule's own comment, and `test_status_pages_02.py`'s pre-existing assertion that `.sparkline__area` carries no rule of its own).
- **Fix:** Kept both constants defined in `draw.py` (used as literal class-attribute values) but excluded them from the `DRAWING_CLASSES` tuple, with a comment explaining why.
- **Files modified:** `companion/draw.py`
- **Verification:** `test_every_drawing_class_resolves_in_the_served_stylesheet` and the rest of the drawing contract pass; `test_sparkline_area_sits_under_the_line_in_its_own_nested_viewbox`'s pre-existing "no `.sparkline__area` rule" assertion still passes unchanged.
- **Committed in:** `607c4ac` (Task 1 commit)

**2. [Rule 1 - Bug] Reworded health_page prose references that tripped the plan's own textual "no page import" check**
- **Found during:** post-Task-2 self-check against the plan's acceptance criteria
- **Issue:** Several docstrings in `health_signals.py`/`battery_chart.py` named `companion/pages/health_page.py` by path/attribute in prose (e.g. "the reads `render()` and `compute_health_state()` (companion/pages/health_page.py) both need"). No actual `import` statement existed (verified structurally: importing either module standalone pulls nothing from `companion.pages` into `sys.modules`), but the plan's acceptance grep (`grep -cE "companion.pages|health_page" ...`) cannot distinguish a comment from a real import.
- **Fix:** Reworded the affected comments to say "the Health page module" instead of the literal path/attribute name.
- **Files modified:** `companion/health_signals.py`, `companion/battery_chart.py`
- **Verification:** `grep -cE "companion.pages|health_page" companion/health_signals.py companion/battery_chart.py` now finds nothing; full test suite re-run clean.
- **Committed in:** `7346d20`

---

**Total deviations:** 2 auto-fixed (both Rule 1)
**Impact on plan:** Both auto-fixes were necessary to make the plan's own acceptance checks pass without weakening any real contract. No scope creep.

## Known Gap (not a deviation — plan acceptance criterion not fully met)

**`companion/pages/health_page.py` is 1681 lines, above the plan's stated "under 1500" target** (down from 2516 before this plan; `companion/health_signals.py` is 595 lines and `companion/battery_chart.py` is 445 lines, both comfortably under the ceiling).

Why the gap remains: after moving everything the plan names (the chart, and the full severity/anomaly/state computation) plus two additional pure-data functions found during execution, everything left in `health_page.py` is either a markup builder that must stay (it calls the page's own tile-building helpers, and `health_signals.py` may never import `health_page.py`) or a page-text constant block those builders need (tile captions, the registry/stats/check-in-regularity sections' headings and templates). Closing the remaining ~180-line gap would require a THIRD extraction — most plausibly the registry ("Airlines we could not name"), stats ("How well we name flights") and check-in-regularity sections, which are markup-heavy and only loosely related to either the chart or the severity signals this plan's Task 2 scoped itself to. That is a larger, distinct structural change than this plan's `files_modified` list (`health_signals.py` + `health_page.py` + two test files) authorized, so it was not attempted here.

This is not silently swept aside: `companion/test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` allowlist already tracks `companion/pages/health_page.py` as a known, intentionally-tolerated oversized file (pre-dating this plan) with the comment "expected to shrink to nothing as this phase's later plans land" — this plan made real, verified progress (2516 → 1681 lines) without closing the ceiling, and the file remains correctly listed in that allowlist (no change was needed there, and none was made). A follow-up plan targeting the registry/stats/check-in sections would be the natural next step if getting under 1500 is required before the phase closes.

## Issues Encountered
None beyond the two auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The chart-onto-draw.py migration (CFG-39) is complete and machine-verified: byte-identical output, full drawing-contract coverage, no `label_grid` reference anywhere.
- `companion/health_signals.py` is ready to be a dependency for anything else in this phase that needs Health's severity/anomaly state without pulling in the page's markup builders.
- `companion/pages/health_page.py` still needs further splitting to get under the phase's file-size ceiling; a follow-up plan should extract the registry/stats/check-in-regularity sections (see Known Gap above) if that is required before Phase 40 closes.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: companion/battery_chart.py
- FOUND: companion/health_signals.py
- FOUND: companion/testdata/battery_chart_baseline.json
- FOUND commit 607c4ac (Task 1)
- FOUND commit 60f3b3f (Task 2)
- FOUND commit 7346d20 (follow-up fix)
