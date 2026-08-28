---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 08
subsystem: ui
tags: [http-server, sqlite, anomaly-detection, svg, read-only-registry]

# Dependency graph
requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s
    provides: "server/history_db.py's recent_device_health()/latest_device_health()/corroboration_counts()/route_source_counts()/get_meta() and the META_* key constants (06-01); companion/layout.py's status_dot()/data_table()/empty_state()/anomaly_banner()/escape_html() (06-04); companion/app.py's route table and page_context() ctx contract, and the health_page.py/airlines_page.py contract-complete stubs (06-05); server.plane.detect.poll_current_aircraft()'s three-state corroboration outcome and server.plane.enrich.resolve_route()'s four-category outcome (Phase 2/2-04)"
provides:
  - "companion/pages/health_page.py — two independently-thresholded freshness signals (device check-in vs. ADS-B pipeline run), a battery trend table plus a dependency-free inline SVG sparkline, three-state corroboration reporting that never mislabels the unknown state as failure, CFG-05's source-fault landing block, and D-14 anomaly-banner flagging that stays silent when everything is healthy"
  - "companion/pages/airlines_page.py — the CFG-04 unresolved-prefix registry rendered read-only (deterministic count-desc/prefix-asc ordering, malformed-entry tolerance, D-16's no-form/no-button constraint) and CFG-08's windowed resolution-rate breakdown across enrich.resolve_route()'s four documented categories"
  - "companion/test_status_pages.py — 25 checks (24 unit/integration + 1 real HTTP round trip) covering both pages' happy paths, empty states, escaping, anomaly detection, and degrade-without-raise behaviour against an unreadable database"
affects: [06-11, 06-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_safe_query(state_dir, fn) / _DB_UNAVAILABLE sentinel: every history_db read on a page goes through a helper that returns a distinguishable sentinel (not None, which is a legitimate 'no rows yet' value) on sqlite3.Error/OSError, so a locked/missing database degrades one section to the health-unavailable copy instead of faulting the whole page"
    - "Threshold constants are never bare numbers — each staleness/anomaly threshold carries a comment naming its real-world anchor (POLL_INTERVAL_S, SKYPANE_SLEEP_S, the flightportrait backoff cap, or an explicit 'provisional, pending Phase 5' note) so a future reader can tell a measured value from an engineering guess"
    - "Hand-picked empty states over layout.data_table()'s generic fallback wherever 'no rows yet' is a legitimately good-news state (battery, corroboration, resolution stats) rather than an error — keeps the page from emitting spurious warn/ok status dots before any data exists"

key-files:
  created:
    - companion/test_status_pages.py
  modified:
    - companion/pages/health_page.py
    - companion/pages/airlines_page.py

key-decisions:
  - "corroboration_status()'s disagreement bucket renders as the warn status, not error, per this plan's own Task 1 action text — even though 06-UI-SPEC.md's general Status-colors table lists a 'corroborated=False streak' under the Error row. A disagreement already triggers D-04's 'leave the panel alone' on the render side; this page surfaces it for visibility without duplicating that as a second hard fault. Documented in corroboration_status()'s docstring so the apparent conflict with the UI-SPEC table doesn't read as an oversight."
  - "CFG-05's landing block names the failed providers via a hand-maintained _ADSB_PROVIDER_NAMES tuple rather than importing server.plane.detect.DEFAULT_PROVIDER_ORDER — the plan's own action text restricts health_page.py's imports to server.history_db/server.poll_loop/companion.layout, and no history_db meta key persists which specific providers failed (only the boolean META_SOURCE_FAULT). Since 06-10's _classify_source_fault() only sets that flag true when every queried provider failed, naming the full default provider set is accurate by construction."
  - "battery_status()/battery_sparkline_svg() both document and require newest-first row ordering (matching battery_trend_rows()'s/history_db.recent_device_health()'s own contract) rather than accepting either order — a single documented convention avoids a silent direction-flip bug, which the harness's first draft actually hit and caught (see Deviations)."

patterns-established:
  - "A page module's docstrings/comments must never spell out the literal name of an internal helper it deliberately avoids re-deriving (e.g. enrich.py's registry-writer) — a grep-based acceptance criterion checking for that name's absence doesn't distinguish prose from code, so naming the avoided function even in an explanatory comment trips the same regression guard as actually calling it."

requirements-completed: [CFG-03, CFG-04, CFG-05, CFG-08]

coverage:
  - id: D1
    description: "The Health page renders two independently-thresholded, separately-labelled freshness signals — 'Device last checked in' (from history_db.latest_device_health()) and 'ADS-B pipeline last ran' (from history_db.get_meta()'s pipeline-run key) — so a stale device and a fresh pipeline show one warning/error row and one healthy row, never a blended verdict."
    requirement: "CFG-03"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#render() shows two distinct, separately-labelled freshness signals"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#staleness_status() returns ok/warn/error at the right boundaries, warn for a never-seen signal"
        status: pass
      - kind: integration
        ref: "companion/test_status_pages.py#a stale device and a fresh pipeline produce one non-healthy row and one healthy row, not a blended verdict"
        status: pass
    human_judgment: false
  - id: D2
    description: "Battery readings render as a trend (a table of recent readings plus a dependency-free inline SVG sparkline), not just the latest value, with the good-news empty state when no reading exists yet; a drop between consecutive readings past BATTERY_DROP_WARN_MV is flagged as an anomaly while a gentle monotonic decline is not."
    requirement: "CFG-03"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#zero battery rows render the good-news empty state and no <svg"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#three battery rows render the full trend (not just the latest value) and exactly one <svg><polyline>"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#battery_sparkline_svg() emits no url(, <image, or <script — no external reference at all"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a large consecutive-reading drop flags the battery anomaly; a gentle monotonic decline does not"
        status: pass
    human_judgment: false
  - id: D3
    description: "The three ADS-B corroboration states (agreement, single-source unknown, disagreement) render distinctly and the unknown state is never presented as a failure; D-14's anomaly banner appears at the top when any tracked signal is non-healthy and is entirely absent when everything is healthy."
    requirement: "CFG-03"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#corroboration counts made only of the unknown state produce no error status class"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a fully-healthy fixture renders no anomaly banner at all"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a stale ADS-B pipeline shows the anomaly banner copy exactly once"
        status: pass
    human_judgment: false
  - id: D4
    description: "When history_db's source-fault meta flag is set, the Health page renders a prominent landing block naming the failed ADS-B providers, closing the loop CFG-05's on-panel badge opens; a locked/missing database degrades to the health-unavailable copy instead of raising."
    requirement: "CFG-05"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#with the source-fault meta key set, the CFG-05 landing explanation appears"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#with the source-fault meta key unset, the CFG-05 landing explanation is absent"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a state directory that cannot hold a database renders the health-unavailable copy without raising"
        status: pass
    human_judgment: false
  - id: D5
    description: "The unresolved-prefix registry (poll_state.json, read only through poll_loop.load_poll_state()) is visible read-only, sorted deterministically, tolerant of hand-edited malformed entries, with hostile values (a script-tag-shaped example callsign) rendered escaped and no in-page action anywhere on the page."
    requirement: "CFG-04"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#an empty unresolved-prefix registry renders the good-news empty state and no <table"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#two entries of unequal count render with the higher count first"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a registry entry that is not a dict, or whose count is not an int, is skipped rather than crashing the page"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#a prefix containing markup characters is rendered escaped"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#an example callsign shaped like a script tag renders escaped, with no unescaped script tag in the output"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#the Airlines page renders no <form and no <button anywhere"
        status: pass
    human_judgment: false
  - id: D6
    description: "Route-resolution performance is visible as a windowed rate: resolution_stats() breaks history_db.route_source_counts() down into enrich.resolve_route()'s four documented categories with a resolved-percentage headline, guarded against a zero-history division."
    requirement: "CFG-08"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#resolution_stats() breaks down the four documented source categories and computes the resolved percentage"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#zero history rows render the statistics empty state rather than dividing by zero"
        status: pass
    human_judgment: false
  - id: D7
    description: "One end-to-end HTTP round trip proves companion/app.py's router and both completed page modules agree: GET /health and GET /airlines both return 200 with their own page heading against a real, seeded, running service."
    requirement: "CFG-03"
    verification:
      - kind: e2e
        ref: "companion/test_status_pages.py#GET /health and GET /airlines both return 200 with their own page heading, against a real running service"
        status: pass
    human_judgment: false

# Metrics
duration: ~45min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 08: Health & Airlines Status Pages Summary

**`companion/pages/health_page.py` and `companion/pages/airlines_page.py` are now real: two independently-thresholded ADS-B freshness signals, a dependency-free SVG battery sparkline with anomaly flagging, three-state corroboration reporting, CFG-05's source-fault landing block, and the read-only unresolved-prefix registry with a windowed CFG-08 resolution-rate breakdown — all degrading gracefully instead of raising when the database is locked or missing.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified:** 2 (`companion/pages/health_page.py`, `companion/pages/airlines_page.py`)
- **Files created:** 1 (`companion/test_status_pages.py`)

## Accomplishments

- `health_page.py`: `staleness_status()` computes independent ok/warn/error verdicts for the device check-in and the ADS-B pipeline run, each threshold pair grounded in a real recorded value (`POLL_INTERVAL_S`'s 30s cadence for the pipeline; `SKYPANE_SLEEP_S`'s current 30s bring-up default plus flightportrait's own documented 6h backoff cap for the device, deliberately generous so lengthening the device's sleep interval doesn't turn the page permanently red).
- `battery_trend_rows()`/`battery_sparkline_svg()`/`battery_status()`: a recent-readings table plus a fixed-viewBox, single-`<polyline>`, dependency-free inline SVG sparkline (no charting library); a consecutive-reading drop past `BATTERY_DROP_WARN_MV` (100mV, explicitly documented as provisional pending Phase 5's still-unmeasured discharge curve) raises the battery anomaly.
- `corroboration_status()`: reports agreement/single-source-unknown/disagreement distinctly, sourced from `detect.poll_current_aircraft()`'s own documented semantics with zero new inference — the unknown state is always `"ok"`, never presented as a failure.
- `collect_anomalies()`/D-14 anomaly banner: renders `layout.anomaly_banner()` with 06-UI-SPEC.md's verbatim copy exactly once when any tracked signal is non-healthy, and not at all when everything is fine — proven both ways, plus a deliberate fault-injection proof (forcing `staleness_status()` to always return `"ok"` made the stale-pipeline check fail, then reverted).
- CFG-05's landing block: when `history_db`'s source-fault meta flag is set, a prominent block names the currently-configured ADS-B providers (adsb.fi, adsb.lol) and explains the on-panel alert badge's redirect.
- `_safe_query()`/`_DB_UNAVAILABLE` sentinel (both pages): every database read is isolated so a locked/missing/corrupt database degrades that one section to the health-unavailable copy instead of raising — proven by pointing a page at a state directory blocked by a plain file.
- `airlines_page.py`: `unresolved_rows()` reads the CFG-04 registry strictly through `poll_loop.load_poll_state()`, sorted count-desc/prefix-asc, tolerant of a hand-edited malformed entry (a string value, a non-int count); the page emits no `<form>` and no `<button>` anywhere (D-16). `resolution_stats()` breaks `route_source_counts()` down into `enrich.resolve_route()`'s four documented categories with a resolved-percentage headline, guarded against a zero-history division.
- `companion/test_status_pages.py`: 25/25 checks, seeding every fixture programmatically via `history_db`'s writers and `poll_loop.save_poll_state()` — never a committed fixture file.

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete the Health page** - `3911554` (feat)
2. **Task 2: Complete the Airlines page** - `06af4a6` (feat)
3. **Task 3: Create companion/test_status_pages.py** - `40f6bc3` (test)

**Plan metadata:** (this commit)

_Note: Tasks 1 and 2 are marked `tdd="true"`, but — matching 06-07's own precedent — `companion/test_status_pages.py` did not exist before Task 3 created it; there was no prior harness for Tasks 1/2 to extend in a literal RED-first commit. Genuine RED/GREEN verification was still performed: the full 25-check harness was written against the completed Task 1 and Task 2 implementations, run to green, and then a real fault-injection pass was performed (temporarily forcing `staleness_status()` to always return `"ok"`, confirming the stale-pipeline check fails at 22/25) before reverting — proving the check's fidelity rather than assuming it. The two page modules and the harness are committed at their own task boundaries per the plan's `<files>` blocks._

## Files Created/Modified

- `companion/pages/health_page.py` — `render()` (completed), `staleness_status()`, `battery_trend_rows()`, `battery_sparkline_svg()`, `battery_status()`, `corroboration_status()`, `collect_anomalies()`, `STALE_DEVICE_WARN_S`/`STALE_DEVICE_ERROR_S`/`STALE_PIPELINE_WARN_S`/`STALE_PIPELINE_ERROR_S`/`BATTERY_DROP_WARN_MV`/`BATTERY_TREND_LIMIT`, plus the CFG-05 landing block and the `_safe_query()`/`_DB_UNAVAILABLE` degrade pattern
- `companion/pages/airlines_page.py` — `render()` (completed), `unresolved_rows()`, `coverage_status()`, `resolution_stats()`, `RESOLUTION_WINDOW_DAYS`
- `companion/test_status_pages.py` — `Harness`, `http_request()`, `_login()`, fixture-seeding helpers, and 25 checks (`EXPECTED_CHECK_COUNT` = 25)

## Decisions Made

See `key-decisions` in the frontmatter above: the corroboration disagreement status deliberately reads as `warn` (not `error`) per this plan's own Task 1 text, despite an apparent tension with 06-UI-SPEC.md's general Status-colors table; the CFG-05 landing block hand-maintains a provider-name list rather than importing `server.plane.detect` (which the plan's import contract excludes); and `battery_status()`/`battery_sparkline_svg()` require newest-first row ordering, matching `history_db.recent_device_health()`'s own contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two grep-based acceptance criteria collided with prose that named the very internals they document as avoided**
- **Found during:** Task 3, while running the full harness for the first time
- **Issue:** `airlines_page.py`'s module docstring and `unresolved_rows()`'s own docstring literally named `enrich.note_unresolved_prefix()` and `_AIRLINE_PREFIX_SHAPE_RE` while explaining that this page never re-derives them — which made the acceptance-criteria grep for those exact strings (`grep -c "note_unresolved_prefix\|_AIRLINE_PREFIX_SHAPE_RE" companion/pages/airlines_page.py == 0`) fail, since the grep can't distinguish prose from code. This is the same class of literal-grep/docstring-prose collision 06-05-SUMMARY.md and 06-07-SUMMARY.md both already documented for `<form>`/`<button>` mentions and `normalise_theme_id`/`normalise_runway_id` mentions respectively.
- **Fix:** Reworded both docstrings to describe the avoided internals without naming them literally ("`server/plane/enrich.py`'s own registry-writer's shape logic").
- **Files modified:** `companion/pages/airlines_page.py`
- **Verification:** `grep -c "note_unresolved_prefix\|_AIRLINE_PREFIX_SHAPE_RE" companion/pages/airlines_page.py` now returns 0; the corresponding harness check passes.
- **Committed in:** `06af4a6` (Task 2 commit)

**2. [Rule 1 - Bug] The harness's first draft of the battery-drop check passed rows in the wrong order for `battery_status()`'s documented contract**
- **Found during:** Task 3, first harness run
- **Issue:** `battery_status()` documents and requires newest-first row ordering (matching `battery_trend_rows()`'s/`history_db.recent_device_health()`'s own contract), but the harness's first draft of the anomaly-vs-gentle-decline check constructed its fixture rows oldest-first — the internal `reversed()` then paired readings in the wrong chronological direction, so the intended large drop was never detected as a drop.
- **Fix:** Reordered both fixtures (the large-drop case and the gentle-decline case) to newest-first, matching the documented contract, with a comment explaining why the order matters.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** The check now passes; re-running the deliberate fault-injection proof (forcing `staleness_status()` to `"ok"`) still correctly fails only the pipeline-staleness check, confirming the fix didn't mask a real defect.
- **Committed in:** `40f6bc3` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs caught and fixed by the harness's own first run, before it was committed)
**Impact on plan:** Both are small, self-contained, and were caught and corrected before the corresponding commit landed — no scope creep, no behavior change beyond what the plan itself specified.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-03, CFG-04, CFG-05, and CFG-08 are now genuinely end-to-end functional: a user can see device/pipeline health, a battery trend with anomaly flagging, ADS-B corroboration status, the source-fault explanation behind the on-panel badge, and the airline-coverage registry with resolution statistics — all without SSH access.
- Neither page yet has real production data flowing into `history_db` — plan 06-10 (Wave 3, parallel to this plan) is what wires `poll_loop.py` to call `record_runway_event()`/`record_device_health()`/`set_meta()` on every real poll cycle. Until 06-10 lands, both pages correctly render their "no data yet" empty states against the live deployment, which this plan's own harness proves is graceful, not broken.
- Full 9-harness suite (`scripts/run-all-tests.sh`) green at 82% coverage; `companion/test_companion_app.py` unchanged at 49/49; `companion/test_status_pages.py` new at 25/25; `ruff check .` clean; `scripts/check-attribution.sh` unaffected (no asset changes); no stray subprocess left behind.
- `git diff --stat` for this plan (against the prior plan's completion commit) touches exactly `companion/pages/health_page.py`, `companion/pages/airlines_page.py`, and the new `companion/test_status_pages.py` — matching the plan's own `<verification>` section exactly.

## Self-Check: PASSED
