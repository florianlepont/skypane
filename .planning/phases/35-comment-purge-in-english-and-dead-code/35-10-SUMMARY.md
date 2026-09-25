---
phase: 35-comment-purge-in-english-and-dead-code
plan: 10
subsystem: companion-comment-hygiene
tags: [comment-hygiene, companion, health-page, history-page, battery-sparkline, flights-table]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 07
    provides: "stub-server/ purged of history (0 hits); same-code/check/ratio CLI stable"
provides:
  - "companion/pages/health_page.py — 4675 lines, 68.28% comments before this plan — purged of
    plan/ticket/decision/review/phase-ID history: 0 CLI check hits, comment ratio 68.28% -> 37.61%,
    code unchanged (same-code passes with no --allow); health_severity()/anomaly_active() untouched
    in code and still defined (deletion deferred to 35-13)"
  - "companion/pages/history_page.py — 1821 lines, 61.29% comments before this plan — purged of
    the same history-ID patterns: 0 CLI check hits, comment ratio 61.29% -> 38.37%, code unchanged"
  - "threshold/geometry whys (staleness thresholds and their units, the fixed battery-chart Y-axis
    range and its no-viewBox percentage coordinate scheme, the flights_limit()/_show_more_html()
    query-param clamp-not-reject contract) survive as concise comments; all UI string literals
    (EN and FR) untouched"
affects: [35-11, 35-12, 35-13]

tech-stack:
  added: []
  patterns:
    - "for a file with one split point near the middle (health_page.py: def near line 2337 of
      4675), purge the lower half first as one task, then the upper half (including the module
      docstring) as a second task — the lower half's edits never shift the upper half's line
      numbers, so the split stays exact across two separate commits"
    - "same file-wide ratio-after-caps gap 35-09 found recurs on any file with many small helper
      functions: after every per-function docstring was already inside its own 8/15-line cap,
      health_page.py and history_page.py both still sat at ~39-43% until several further
      iterate-ratio-then-tighten passes brought them to ~37-38% — re-running `ratio` after each
      pass remains the reliable stopping signal, not a single pass over the def list"
    - "a purge_bar security/contract exception (≤15 lines) is worth spending deliberately on the
      one genuinely complex function in a file (health_page.battery_sparkline_svg — SVG chart
      geometry with no viewBox, percentage coordinates, an area/mark/threshold overlay) rather
      than trying to force it under the general 8-line cap and losing the non-obvious constraints"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/pages/history_page.py

key-decisions:
  - "health_page.py split at safe_health_state() (line 2337, the top-level def nearest the file's
    exact midpoint of 4675 lines): Task 1 purged everything from there to EOF (the anomaly/tile/
    battery/registry/check-in-grid rendering functions), Task 2 purged the module docstring,
    imports and constants block plus the remaining upper-half functions (thresholds,
    compute_health_state(), the sparkline geometry constants and battery_sparkline_svg() itself)."
  - "history_page.py had no natural split point worth the overhead (1821 lines, one bottom-up
    pass sufficed): Task 3 purged the whole file bottom-up in a single task, then ran the
    status/health/history pytest subset."
  - "battery_sparkline_svg()'s docstring (originally ~62 lines across four paragraphs) was kept at
    the security/contract-adjacent 15-20 line band rather than force-fit to 8: it documents the
    no-external-reference guarantee (asserted by a test), the no-viewBox percentage coordinate
    scheme, and why the trend line is n-1 <line> segments instead of a <polyline> — each fact is
    independently load-bearing for a future edit to the chart. This is the plan's one caps
    exception, logged here per the purge_bar rule."
  - "The 260902-chc D-12 reversal comment block in health_page.py (a ~25-line SUPERSEDED history
    narrative between _stats_section_html() and render(), no code beneath it) was deleted outright
    and replaced with a 4-line statement of the current behaviour (Health self-refreshes on a
    named-interval timer instead of showing a stale-view banner) — nothing in the original block
    described a decision not already visible from freshness.js/render() themselves."
  - "flights_limit() and _show_more_html() in history_page.py (both handle an untrusted ?limit=
    query-string value) were kept at the security-adjacent 12-15 line band: the clamp-not-reject
    contract and the never-reflect-the-raw-value invariant are correctness/security requirements,
    not merely nice-to-know history."

patterns-established: []

requirements-completed: []

duration: ~150min
completed: 2026-09-25
---

# Phase 35 Plan 10: health_page.py + history_page.py comment purge Summary

**Purged health_page.py (4675 lines, 68.28% comments, 554 history-ID hits) to 37.61% comments with 0 hits, and history_page.py (1821 lines, 61.29% comments, 190 hits) to 38.37% with 0 hits, keeping only threshold/geometry/security whys.**

## Performance

- **Duration:** ~150 min
- **Completed:** 2026-09-25
- **Tasks:** 3
- **Files modified:** 2 (`companion/pages/health_page.py`, `companion/pages/history_page.py`)

## Accomplishments

- `companion/pages/health_page.py` has 0 `check` hits (was 554: `d-id`, `plan-artifact`, `bare-plan-id`, `quick-task`, `prefix-id`, `threat-id`, `phase-word` patterns) and `same-code` passes with no `--allow` against base `059774e`.
- `companion/pages/history_page.py` has 0 `check` hits (was 190, same pattern set) and `same-code` passes with no `--allow`.
- Comment ratios: health_page.py **68.28% → 37.61%**, history_page.py **61.29% → 38.37%** — both moved well past halfway to the ≤35% target across several iterate-ratio-then-tighten passes (neither reached exactly 35%; see Deviations).
- Every module docstring, function docstring and inline/block comment in both files was rewritten in English, keeping the why (staleness thresholds and their units and reasons, the fixed battery-chart Y-axis range and its no-viewBox SVG coordinate scheme, WCAG/accessibility invariants, the untrusted-query-param clamp contract, cross-file contracts pinned by `test_status_pages.py`/`test_view_pages.py`) and dropping plan/decision/review/quick-task/phase IDs, "previously/now/superseded/no longer" change narratives, numbered lists that just re-walk the code below them, and the one French quote found in health_page.py's module docstring.
- `health_severity()` and `anomaly_active()` in health_page.py are unchanged in code and still defined — their docstrings were shortened like every other function's, per the plan's explicit instruction that their deletion is 35-13's job.
- All UI string literals (English and French, including anything `companion/i18n_fr/` carries) and both modules' identifiers are untouched — `same-code` proves the AST is identical to base `059774e` once docstrings are stripped.
- `pytest companion -q -n auto -k "status or health or history"` passes: 581 passed, 21 skipped (pre-existing missing-Chromium reason). `ruff check` is clean on both files.

## Task Commits

1. **Task 1: Purge the lower half of health_page.py (safe_health_state() through render(), EOF)** - `fae07e2` (refactor)
2. **Task 2: Purge the upper half of health_page.py (module docstring, imports, constants, compute_health_state() and earlier)** - `fbbb7e2` (refactor)
3. **Task 3: Purge history_page.py bottom-up, then run the status/health/history pytest subset** - `52e0643` (refactor)

_No separate plan-metadata commit was made yet; this SUMMARY and STATE/ROADMAP updates land in the final commit below._

## Files Created/Modified

- `companion/pages/health_page.py` — Health status + trend page (device/pipeline/battery/corroboration tiles, the unresolved-prefix registry, the check-in regularity grid, the battery sparkline SVG chart). Comments purged of history; code byte-identical modulo docstrings. `health_severity()`/`anomaly_active()` retained (dead-code removal is 35-13's scope).
- `companion/pages/history_page.py` — Flights page (the flight-history table/card list, the per-row "View panel near this time" lightbox, the resolve-airline one-hop link, the day-separator grouping). Comments purged of history; code byte-identical modulo docstrings.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: health_page.py was split at `safe_health_state()` (line 2337, the top-level def nearest the file's exact midpoint) so the lower-half purge in Task 1 never shifted Task 2's upper-half line numbers; history_page.py needed no split and was purged bottom-up in one task; `battery_sparkline_svg()`'s docstring was deliberately kept in the ~15-20 line security/contract-adjacent band (the plan's one caps exception) rather than force-compressed, since it documents a test-asserted no-external-reference guarantee and a non-obvious no-viewBox coordinate scheme; a ~25-line dead history-narrative comment block in health_page.py (between `_stats_section_html()` and `render()`, no code under it) was deleted outright rather than compressed; and `flights_limit()`/`_show_more_html()` in history_page.py were kept at the security-adjacent band since they handle an untrusted `?limit=` value.

## Deviations from Plan

**1. [Rule 1 — process correction] Comment ratio settled at ~37-38%, not the ≤35% target, after several tightening passes**
- **Found during:** Task 2 (health_page.py) and Task 3 (history_page.py), after `check` reached 0 hits and every remaining docstring was brought within (or, for the one logged exception, deliberately just outside) its per-item cap.
- **Issue:** `ratio` still read 43.86% (health_page.py) and 43.4-ish% (history_page.py, pre-final-pass) after the first purge pass. Both files are unusually dense with small helper functions (health_page.py has ~60 top-level defs across 4675 lines; history_page.py ~30 across 1821), each carrying a short but real why, so per-function caps alone did not converge the file-wide ratio the way they did for files with fewer, larger functions.
- **Fix:** Ran repeated `ratio`-then-tighten passes (matching 35-09's own documented pattern) targeting the highest comment-density 50-60 line windows and the longest remaining docstrings each time, condensing further while re-verifying `same-code`, `check` and `ast.parse` after every edit. Stopped once further cuts began threatening real non-obvious content (SVG geometry reasoning, accessibility contracts, security invariants) rather than restating.
- **Files modified:** `companion/pages/health_page.py`, `companion/pages/history_page.py` (same files, additional edits within Tasks 1/2/3's own commits).
- **Verification:** `ratio` settled at 37.61% (health_page.py) and 38.37% (history_page.py); `same-code --base 059774e` and `check` still pass with 0 hits on both; `ast.parse` succeeds; `ruff check` clean; `pytest companion -k "status or health or history"` (581 passed, 21 skipped) green.
- **Justification for stopping above 35%:** per this phase's own CONTEXT.md ("A file still above ~35% comment lines after its purge is a review trigger, not a failure. The SUMMARY says why its comments earn their place."), both files are dominated by short helper functions that each need one real why (a threshold's unit, a WCAG rule, an SVG coordinate-system constraint, a query-param security clamp) — further compression at this point would have started deleting the load-bearing content the purge rules require keeping, not more history.

---

**Total deviations:** 1 (process correction/ratio shortfall, not a code/behaviour change).
**Impact on plan:** No scope creep — extra passes only tightened comment text further, per the plan's own "if above, do another pass" instruction. No functional or string-literal change in either file.

## Issues Encountered

None beyond the ratio deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Group 4/5 (companion Python production) now has `health_page.py` and `history_page.py` purged, `check`ed at 0 hits, and `same-code`-clean, alongside the previously-completed `app.py`/`auth.py`/small modules (35-08) and `config_page.py` (35-09).
- Both files' final ratios (37.61%, 38.37%) are ready to fold into `35-COMMENT-RATIO.md` at group close (35-13), alongside this SUMMARY's justification for the >35% figures.
- `health_severity()` and `anomaly_active()` remain defined in `health_page.py`, unchanged in code, ready for 35-13's dead-code pass (per this plan's own scope boundary — the plan explicitly excludes deleting them).
- No blockers.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED
- FOUND: companion/pages/health_page.py
- FOUND: companion/pages/history_page.py
- FOUND: fae07e2
- FOUND: fbbb7e2
- FOUND: 52e0643
