---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 06
subsystem: ui
tags: [companion, health-page, copywriting, accessibility, corroboration]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "19-01 (wave 1): the stat-tile text-verdict idiom and DEVICE_STATE_TEXT/PIPELINE_STATE_TEXT/CORROBORATION_STATE_TEXT dicts this plan's caption_title tooltips sit beside; 19-05 (wave 2): companion/wake.py and the widened overall_severity()/collect_anomalies() signatures this plan's constant renames do not touch"
provides:
  - "layout.stat_tile()'s optional caption_title parameter — byte-identical output when unused, an escaped title=\"...\" tooltip on the caption <p> element when supplied"
  - "Health's three tile labels (Pipeline/Corroboration/Resolution-rate) and three corroboration rows read in plain language, with each retired technical term reachable one hover away via caption_title"
  - "Health's registry/statistics card headings and prose (UNRESOLVED_SECTION_HEADING, STATS_SECTION_HEADING, _NO_GAPS_BODY, _READ_ONLY_NOTE, _SOURCE_ROWS) carry no 'adsbdb' and no CFG-\\d requirement id in visible text"
  - "history_page.py's own _CORROBORATION_LABELS/_CORROBORATION_TITLES retargeted to match Health's new copy, keeping the two pages' cross-file agreement guard green"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "caption_title tooltip idiom on layout.stat_tile(), modelled on status_dot()'s own pre-existing title parameter: a fully-defaulted, escaped attribute value that keeps a technical term one hover away instead of deleting it"
    - "constants at the top, never literals at a render site — CORROBORATION_TILE_LABEL/CORROBORATION_TILE_TITLE replace the literal \"Corroboration\" that used to be inlined directly at render()'s stat_tile() call"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/pages/history_page.py
    - companion/test_status_pages.py

key-decisions:
  - "D-06: stat_tile()'s new caption_title is an ATTRIBUTE VALUE, not markup — escaped through the same escape_html() call every other attribute value in this module goes through, so it does not violate stat_tile()'s own documented 'never grow a second free-form raw-markup parameter' rule (that rule is about markup, not attribute values)"
  - "D-06: the Device tile's label was already plain language ('Device last checked in') — no caption_title was invented for it; the comment at its stat_tile() call records that choice explicitly rather than leaving it unexplained"
  - "D-06: the corroboration row explanations avoid apostrophes deliberately (e.g. 'Both flight-data sources on the frame picked...' not 'the frame's flight-data sources') so a pinned harness check comparing the raw Python string against escape_html()'s quote=True output stays exact — apostrophes are fine elsewhere on the page, just not inside a string a check compares byte-for-byte unescaped"
  - "history_page.py (not in this plan's own files_modified list) was fixed as a Rule-1 deviation: test_view_pages.py's _corroboration_copy_agrees_with_health_page() cross-file guard exists specifically to catch a drift like this one, and it fired the moment health_page.py's True/False corroboration labels changed. History's own _CORROBORATION_TITLES['None'] tooltip was updated to Health's new 'Only one saw it' (replacing the retired 'Single-source (uncorroborated)') for the same reason"
  - "the 'miss' row in _SOURCE_ROWS points at the registry card by its own on-screen heading (UNRESOLVED_SECTION_HEADING, interpolated by reference, not retyped) instead of naming CFG-04's registry by requirement id"

requirements-completed: [CFG-03, CFG-04, CFG-08]

# Metrics
duration: 9min
completed: 2026-09-11
---

# Phase 19 Plan 06: Health copy de-jargoning (D-06/A-24) Summary

**Health's stat-tile labels, corroboration rows, and registry/statistics prose now read in plain household language, with every retired technical term (adsbdb, CFG-04's registry, "Corroboration", "ADS-B pipeline last ran") demoted to a `title` tooltip via a new `layout.stat_tile(caption_title=...)` parameter rather than deleted.**

## Performance

- **Duration:** 9 min (2026-09-11T08:01:57Z first task commit → 2026-09-11T08:10:45Z last task commit)
- **Started:** 2026-09-11T08:01:57Z
- **Completed:** 2026-09-11T08:10:45Z
- **Tasks:** 3/3 complete
- **Files modified:** 4 (companion/layout.py, companion/pages/health_page.py, companion/pages/history_page.py, companion/test_status_pages.py)

## Accomplishments
- Closed A-24 (D-06): every piece of jargon on Health — "Corroboration", "Single-source (uncorroborated)", "ADS-B pipeline last ran", "adsbdb", "Resolution rate", and the visible "CFG-04's registry" sentence — now reads in plain language, with the technical term surviving as a `title` tooltip on the relevant label rather than being deleted outright.
- `layout.stat_tile()` gained a `caption_title` parameter that is provably byte-identical to today's output when not supplied (both the icon and no-icon branches), so every one of `test_companion_app.py`'s pinned `stat_tile()` checks — a file this plan does not own — stayed green untouched.
- Caught and fixed a real cross-file regression this plan's own copy change caused: `history_page.py`'s `_CORROBORATION_LABELS`/`_CORROBORATION_TITLES` were retargeted to match Health's new "Both agree"/"They disagree"/"Only one saw it" copy, keeping `test_view_pages.py`'s cross-page drift guard green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Give stat_tile an optional caption tooltip, byte-identical when unused** - `403d9be` (feat)
2. **Task 2: Rewrite Health's tile labels and corroboration rows in plain language (D-06)** - `1a23948` (feat)
3. **Task 3: De-jargon the registry and statistics prose (D-06, CFG-04/CFG-08 surfaces)** - `182740b` (feat)

_No plan-metadata commit yet — SUMMARY.md and this plan's metadata commit follow this file's own creation, per worktree-mode instructions._

## Files Created/Modified
- `companion/layout.py` - `stat_tile()` widened with a fully-defaulted `caption_title=None` parameter; escaped through `escape_html()` and emitted as a `title="..."` attribute on the caption `<p>` element only when truthy; docstring extended to record why this is compatible with the function's "no second raw-markup parameter" rule
- `companion/pages/health_page.py` - `_CORROBORATION_ROWS`' three labels/explanations rewritten in plain language (stored keys unchanged); `PIPELINE_FRESHNESS_LABEL`/`RESOLUTION_RATE_LABEL` reworded with sibling `*_TITLE` tooltip constants; new `CORROBORATION_TILE_LABEL`/`CORROBORATION_TILE_TITLE` replacing the inlined `"Corroboration"` literal; `UNRESOLVED_SECTION_HEADING`/`STATS_SECTION_HEADING` renamed (constant names unchanged); `_NO_GAPS_BODY`/`_READ_ONLY_NOTE` reworded to drop "prefix"; `_SOURCE_ROWS`' glosses reworded off "adsbdb"/"CFG-04's registry"; `render()`'s tile call sites wired with `caption_title=`
- `companion/pages/history_page.py` - `_CORROBORATION_LABELS`'s True/False labels and `_CORROBORATION_TITLES["None"]` retargeted to match Health's new copy (Rule 1 deviation, not in this plan's original file list)
- `companion/test_status_pages.py` - three new checks for `stat_tile()`'s `caption_title` contract (Task 1), one combined plain-language/tooltip check (Task 2, plus the pre-existing Corroboration-tile-lookup check retargeted in place), one combined no-`adsbdb`/no-requirement-id full-render check (Task 3, plus the pre-existing read-only-note literal check retargeted in place); `EXPECTED_CHECK_COUNT` 185 → 188 → 189 → 190 across the three task-scoped appends

## Decisions Made
- `caption_title` is documented as an attribute value, not markup, so it does not reopen `stat_tile()`'s standing "never grow a second free-form raw-markup parameter" rule — that rule concerns `icon`'s raw-HTML injection path, not an escaped attribute string.
- The Device tile's `stat_tile()` call passes no `caption_title` and a comment records why: `DEVICE_FRESHNESS_LABEL` ("Device last checked in") has no genuine technical term to demote.
- The corroboration rows' explanations were phrased to avoid apostrophes, since a pinned harness check compares the raw Python string against `escape_html()`'s `quote=True` output — an apostrophe there would silently break the substring match (caught and fixed during Task 2's own verification pass).
- `_SOURCE_ROWS`' "miss" gloss references `UNRESOLVED_SECTION_HEADING` by variable, not by retyped string literal, so a future rename of that heading cannot silently leave the gloss pointing at a stale name.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a cross-file corroboration-copy regression in `companion/pages/history_page.py`**
- **Found during:** Task 2 (rewriting Health's `_CORROBORATION_ROWS` labels)
- **Issue:** `companion/test_view_pages.py`'s `_corroboration_copy_agrees_with_health_page()` check exists specifically to keep `history_page.py`'s `_CORROBORATION_LABELS` in sync with `health_page.py`'s `_CORROBORATION_ROWS` for the True/False keys, and its `_CORROBORATION_TITLES["None"]` tooltip in sync with Health's own "None" visible label. Renaming Health's labels from "Agreement"/"Disagreement" to "Both agree"/"They disagree" (and the corroboration explanation's "None" label to "Only one saw it") immediately tripped that guard.
- **Fix:** Retargeted `history_page.py`'s `_CORROBORATION_LABELS["True"]`/`["False"]` to `"Both agree"`/`"They disagree"`, and `_CORROBORATION_TITLES["None"]` to `"Only one saw it"` (replacing the retired `"Single-source (uncorroborated)"`), matching the plan's own D-06 mapping.
- **Files modified:** companion/pages/history_page.py
- **Verification:** `python3 -m companion.test_view_pages` — 76/76 pass.
- **Committed in:** `1a23948` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - cross-file copy-drift bug, directly caused by Task 2's own change and caught by an existing, purpose-built harness guard)
**Impact on plan:** Necessary to keep an existing, documented cross-page test green; no change to this plan's own scope or intent — `history_page.py`'s own comment already stated the two pages' copy is allowed to diverge in general, but the True/False labels specifically are pinned to agree by name.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- A-24/D-06 is closed: no visible sentence on Health names "adsbdb", "Single-source (uncorroborated)", or a `CFG-\d` requirement id; every renamed label's technical term is reachable via a `title` tooltip; `#server-data` is unchanged.
- `layout.stat_tile()`'s `caption_title` parameter is available for any future page that wants the same plain-label/technical-tooltip split.
- `scripts/run-all-tests.sh` run in full: only the three documented pre-existing failures appear (`server/test_manual_resolutions.py`'s two WR-11 read-only-directory-as-root cases, `companion/test_companion_app.py`'s same two WR-11 cases, and `companion/test_status_pages.py`'s one `anomaly_active()` non-existent-directory case) — all unrelated to this plan and identical to an untouched checkout under this sandbox's root-user constraint. Zero new failures.
- No blockers for the other wave-3 plan (19-07, which owns `config_page.py`/`app.py`/`style.css`/`test_config_page.py`/`test_companion_app.py` and was not touched here).

## Self-Check: PASSED

- FOUND: companion/layout.py
- FOUND: companion/pages/health_page.py
- FOUND: companion/pages/history_page.py
- FOUND: companion/test_status_pages.py
- FOUND commit 403d9be
- FOUND commit 1a23948
- FOUND commit 182740b

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 06*
*Completed: 2026-09-11*
