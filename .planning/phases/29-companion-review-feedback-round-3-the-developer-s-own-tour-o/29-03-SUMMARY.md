---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 03
subsystem: ui
tags: [companion, history-page, pagination, css-grid, no-js-controls, python-stdlib-http]

requires:
  - phase: 29-02
    provides: "a stable companion/pages/history_page.py and companion/static/style.css baseline to build the reveal on top of, plus the general pattern of asserting section order as index() relationships"
provides:
  - "history_page.render() paginates Vols to FLIGHTS_PAGE_SIZE (15) flights on first load, sliced once into visible_rows before the per-row gallery/thumbnail enrichment loop, feeding both the phone card list and the desktop table"
  - "history_page.flights_limit(ctx) — a never-raising int clamp of the raw '?limit=' query value into [15, HISTORY_ROW_LIMIT], the single validation point every consumer shares"
  - "history_page._show_more_html() — a plain <a class=\"calendar-disconnect-btn\"> Show-more anchor advancing the limit by one page, working with scripts blocked, whose href is a declared REFRESH_SWAP_SELECTORS_BY_PAGE region so it cannot go stale after a background refresh"
  - "companion/app.py's new 'flights_limit' ctx key, threaded raw and unvalidated exactly like 'resolve_prefix'"
  - "a two-track CSS grid on .history-card__primary (minmax(0, 1fr) then auto) with white-space: nowrap on .history-card__time, closing the 2026-09-17 audit's P1 callsign/timestamp collision at 390px"
  - "the filter's empty-state copy discloses when a search only covers the currently-loaded flights (a second _FILTER_EMPTY_BODY_LIMITED_TEMPLATE, English and French)"
affects: [29-06]

tech-stack:
  added: []
  patterns:
    - "No pagination pattern existed anywhere in this codebase before this plan — the query-param '?limit=' re-render is the new, argued-from-scratch mechanism, chosen over a <details> reveal specifically because freshness.js's fetch(window.location.href) survives a query-param-encoded reveal state for free."
    - "A swap-registry region added to layout.py's REFRESH_SWAP_SELECTORS_BY_PAGE must ALSO be added, as the identical plain-selector-array literal, to freshness.js's own SWAP_SELECTORS_BY_PAGE mirror — this is a pre-existing, mechanically-enforced (test_status_pages.py D1/CFG-35) two-file registry, not something a query-param mechanism can avoid touching."
    - "AST-based source-structure checks (ast.parse + ast.walk over inspect.getsource output) prove a 'this function is the only path' invariant without a comment mentioning the function's name in prose producing a false positive — the same discipline test_i18n.py's own D-08 scanners already use, applied here to a single function's call graph rather than a whole-module string catalogue."

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/app.py
    - companion/pages/__init__.py
    - companion/layout.py
    - companion/static/style.css
    - companion/i18n_fr/flights.py
    - companion/static/freshness.js
    - companion/test_view_pages.py

key-decisions:
  - "Query-param '?limit=' re-render over a native <details> reveal (CONTEXT.md left this to the planner) — freshness.js's fetch(window.location.href, ...) re-requests whatever URL the browser is currently on, so once a visitor clicks through to '?limit=30' every later background refresh keeps requesting that same URL automatically, with zero new client-side state-preservation logic. A <details open> reveal would be silently collapsed by the very next background swap (the DOMParser-parsed replacement node's <details> is closed by default) — a visitor who opened it, looked away for 45 seconds, would find it closed with no explanation, which reads as data loss."
  - "The filter's narrowed reach (list-filter.js only ever sees the loaded subset once a limit is in force) is disclosed, not hidden — a second _FILTER_EMPTY_BODY_LIMITED_TEMPLATE fires only when shown < total_available, naming the narrowed coverage instead of letting the existing 'all %d flights' template imply a search that did not happen."
  - "flights_limit() clamps out-of-range values upward/downward rather than rejecting them to a fallback the way wake_gauge_interval_s() does — a hand-edited URL should render a page, not an error, and HISTORY_ROW_LIMIT (50) is already the hard ceiling history_rows() ever fetches from the database, so clamping can never request more rows than the query would have returned anyway."
  - "Deviation (Rule 3, documented below): adding '.flights-more' to layout.py's REFRESH_SWAP_SELECTORS_BY_PAGE required the identical one-line addition to freshness.js's own SWAP_SELECTORS_BY_PAGE mirror, because test_status_pages.py's pre-existing D1/CFG-35 cross-file check pins the two registries byte-equal selector-for-selector. This falsifies the plan's own literal acceptance criterion that this task produces zero freshness.js diff — the plan's premise ('zero script change') was correct about not needing any new swap LOGIC, but did not account for the pre-existing two-file mirror requirement. Documented rather than silently sacrificing the green test suite to satisfy the literal line."

requirements-completed: [CFG-83]

coverage:
  - id: D1
    description: "Vols' default render shows the filter bar plus 15 flights (both the phone card list and the desktop table sliced from one shared visible_rows list), not all 50"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — Task 1 acceptance criteria: a 36-row fixture with no limit renders exactly 15 cards and 15 table rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "A real 'Afficher plus' / 'Show more' plain-anchor link reveals the next page with scripts blocked, and no script anywhere mentions the control beyond the sanctioned swap-registry mirror entry"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_flights_reveal_control_is_a_plain_anchor_no_script_mentions"
        status: pass
    human_judgment: true
    rationale: "No playwright is installed in this sandbox — the 'scripts genuinely disabled in a real browser' half of the no-JS proof cannot be executed here; the check proves the markup and the JS-file scan structurally instead. See Human Follow-ups."
  - id: D3
    description: "The revealed pagination state survives a background auto-refresh — the reveal state IS the URL, so freshness.js's own re-fetch of window.location.href reproduces it with no new script logic"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_flights_reveal_state_reproduces_from_the_url_alone"
        status: pass
    human_judgment: true
    rationale: "No browser executes the actual fetch()/DOMParser swap in this sandbox — this check proves only the structural half (byte-identical re-render at the same URL, the declared swap region, freshness.js's one fetch( targeting window.location.href verbatim). The live 45-second-cycle confirmation is a human follow-up."
  - id: D4
    description: "The filter bar renders above the first card at all times, never pushed below the list or hidden by the reveal"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — Task 1 acceptance criteria: index('filter-bar') < index('history-cards') < index('data-table-wrap') < index('flights-more')"
        status: pass
    human_judgment: false
  - id: D5
    description: "The phone summary card's callsign and timestamp occupy stable, non-competing columns at 390px — the timestamp never wraps"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_history_card_primary_grid_pins_the_timestamp_track"
        status: pass
    human_judgment: true
    rationale: "The check proves the CSS declarations and the markup/grid track-count relationship from source; the actual resolved 390px box (and the page's total height against the audit's 6710px baseline) needs a live browser, not available in this sandbox. See Human Follow-ups."
  - id: D6
    description: "A hostile or malformed ?limit= value cannot make the page raise, and cannot request more rows than the database query ever fetches"
    requirement: CFG-83
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_flights_limit_is_clamped_and_the_clamp_is_the_only_path"
        status: pass
    human_judgment: false

# Metrics
duration: 58min
completed: 2026-09-21
status: complete
---

# Phase 29 Plan 03: Vols Paginated, No-JS Show-More, Stable Phone Grid Summary

**A server-side `?limit=` query-param re-render paginates Vols to 15 flights with a real no-JS "Show more" anchor whose reveal state survives freshness.js's background refresh for free, plus a two-track CSS grid closing the audit's callsign/timestamp collision on the phone card.**

## Performance

- **Duration:** 58 min
- **Started:** 2026-09-21T19:42:00Z
- **Completed:** 2026-09-21T20:39:43Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- `history_page.render()` now slices `formatted_rows` to `flights_limit(ctx)` (clamped into `[FLIGHTS_PAGE_SIZE=15, HISTORY_ROW_LIMIT=50]`) **before** the per-row gallery-lookup/thumbnail-render loop, so that work runs only for rows this render actually shows, and feeds `visible_rows` — one shared list — to both the phone card list and the desktop table
- `flights_limit(ctx)` reuses `wake_gauge_interval_s()`'s exact `try: int(str(raw).strip()) except (TypeError, ValueError)` idiom, clamping (not rejecting) an out-of-range value; 19 hostile inputs (`None`, `""`, `" "`, `"abc"`, `"1.5"`, `"-1"`, `"0"`, `"14"`, `"15"`, `"50"`, `"51"`, `"999999999"`, `"1e9"`, `"0x10"`, `True`, `False`, `[]`, `{}`, `object()`) all resolve to an int inside the band and nothing raises
- `_show_more_html()` renders a plain `<a class="calendar-disconnect-btn" href="/flights?limit=N">` — no button, no form, no script — reusing `.calendar-disconnect-btn`'s small-secondary-action treatment as its third consumer; the `<nav class="flights-more">` container always renders (empty when nothing remains) so it satisfies the swap-registry witness contract and costs zero layout via `.flights-more:empty { display: none; }`
- `layout.REFRESH_SWAP_SELECTORS_BY_PAGE[REFRESH_PAGE_FLIGHTS]` grew a fifth entry, `.flights-more`, so the Show-more href cannot go stale after a background refresh
- `.history-card__primary` became a two-track CSS grid (`minmax(0, 1fr) auto`) with `.history-card__time` gaining `white-space: nowrap` — the flex row that let the two children renegotiate their share of the line at 390px is gone
- The filter's empty-state copy now discloses, in a second body template, when a search only covers the currently-loaded flights rather than "all" of them
- Three new structural checks prove the refresh-survival property's non-browser half, the Show-more control's no-JS/no-script-dependency contract, and the hostile-input clamp plus its "only one path" invariant

## Task Commits

Each task was committed atomically:

1. **Task 1: the limit parameter, the slice, and the Show-more control** - `cd81a6f` (feat)
2. **Task 2: the phone summary card's stable grid at 390 px** - `4ccb8ec` (fix)
3. **Task 3: prove the reveal survives a refresh, works with scripts blocked, and cannot be abused through the URL** - `167041e` (test)

**Plan metadata:** (this commit) — `docs(29-03): complete Vols paginated plan`

## Harness Counts (re-derived by running)

| Harness | Before | After | Delta |
|---|---|---|---|
| `test_view_pages.py` | 164/164 | 168/168 | +4 (Task 1: +0 net, one existing witness check retargeted; Task 2: +1 new grid-relationship check; Task 3: +3 new checks) |
| `test_status_pages.py` | 312/312 | 312/312 | 0 (the freshness.js mirror-registry cross-file check re-passed after the deviation fix; no new check added) |
| `test_config_page.py` | 266/266 | 266/266 | 0 (unchanged, confirmed unaffected) |
| `test_i18n.py` | 24/24 | 24/24 | 0 (same 6 check(...) call sites; the two new templates and their French twins are covered by the existing D-08 completeness scanners, not a new call) |
| `test_companion_app.py` | 316/316 | 316/316 | 0 (unchanged, confirmed unaffected after the CSS edit) |
| `test_browser_ux.py` | SKIP | SKIP | n/a — "SKIP companion/test_browser_ux.py — playwright not installed", never reported as a pass |
| Full suite (`scripts/run-all-tests.sh`) | — | PASS, all 22 harnesses green (`PYTHON=server/.venv/bin/python`) | — |

`test_view_pages.py`'s literal output:
```
view-pages: 168/168 checks pass
```
`test_status_pages.py`:
```
status-pages: 312/312 checks pass
```
`test_i18n.py`:
```
24/24 checks pass
```
`test_companion_app.py`:
```
companion-app: 316/316 checks pass
```
`test_browser_ux.py`:
```
SKIP companion/test_browser_ux.py — playwright not installed (dev-only dependency; run `pip install -r server/requirements-dev.txt` to enable this harness)
```
Full suite tail:
```
==> Result: PASS
```

## Mutation Proofs

Six required by the plan (two per task); all six performed, all six reverted with `git checkout-index -f -- <path>` (staged first), `git status --porcelain` clean after each revert.

**Task 2, Mutation A** — `display: flex` restored on `.history-card__primary`:
```
FAIL the phone summary card's .history-card__primary line is a two-track CSS grid (minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time (white-space: nowrap, no margin-left: auto), and all three primary_value_html branches — callsign, hex-plus-note, empty — produce a child set the grid can place with no third, unclassified top-level child (2026-09-17 audit P1, 29-03-PLAN.md Task 2) - expected .history-card__primary to declare display: grid, got block '\n  display: flex;\n  grid-template-columns: minmax(0, 1fr) auto;\n  align-items: center;\n  gap: var(--space-sm);\n'
```

**Task 2, Mutation B** — `white-space: nowrap` removed from `.history-card__time`:
```
FAIL the phone summary card's .history-card__primary line is a two-track CSS grid (minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time (white-space: nowrap, no margin-left: auto), and all three primary_value_html branches — callsign, hex-plus-note, empty — produce a child set the grid can place with no third, unclassified top-level child (2026-09-17 audit P1, 29-03-PLAN.md Task 2) - expected .history-card__time to declare white-space: nowrap, got '\n  font-size: var(--font-label-size);\n'
```

**Task 3, Mutation A** — `.flights-more` removed from `layout.REFRESH_SWAP_SELECTORS_BY_PAGE[REFRESH_PAGE_FLIGHTS]` (as instructed, this trips TWO checks together):
```
FAIL the rendered Flights page carries exactly one data-loaded-at marker and a witness for every one of its REFRESH_SWAP_SELECTORS_BY_PAGE regions, and no region names the filter input list-filter.js captured at load (D7/CFG-37, 23-08-PLAN.md Task 1) - Flights' registry entry is ['.data-table-wrap', '.page-header__freshness', '[data-filter-count]', 'ul.history-cards'], and this check knows how to witness ['.data-table-wrap', '.flights-more', '.page-header__freshness', '[data-filter-count]', 'ul.history-cards'] — a region added to the registry must be witnessed in the rendered page here too, or it is a list entry that can never fire
```
```
FAIL two renders of a 36-row fixture at the SAME ?limit= value produce byte-identical pagination state (standing in for freshness.js's own re-fetch of the unchanged window.location.href), '.flights-more' is a declared swap region, and freshness.js carries exactly one fetch( call targeting window.location.href verbatim — the structural half of the refresh-survival property this harness can prove without a browser (29-RESEARCH.md, 29-03-PLAN.md Task 3) - expected '.flights-more' to be a declared REFRESH_SWAP_SELECTORS_BY_PAGE region for Flights, got ('.page-header__freshness', 'ul.history-cards', '.data-table-wrap', '[data-filter-count]')
```

**Task 3, Mutation B** — a targeted `document.querySelector(".flights-more")` reference added to `companion/static/list-filter.js`:
```
FAIL the Show-more anchor renders with an href and no onclick/data- attribute and is never a <button> or <form>, and zero companion/static/*.js files mention its 'flights-more' class (scanned-file floor >= 17, printed on failure) — a no-JS control proof, not merely a render (29-03-PLAN.md Task 3) - expected only freshness.js's own generic swap-registry mirror to mention 'flights-more' — found it in ['list-filter.js'] too (scanned 17 files)
```

**Task 3, Mutation C** — `flights_limit()`'s upper clamp changed to return the parsed value unclamped:
```
FAIL history_page.flights_limit() clamps all 19 hostile inputs into [15, 50] without raising, render() calls it exactly once and never reads ctx['flights_limit'] directly, companion/app.py performs no arithmetic or comparison on the raw threaded value, and HISTORY_ROW_LIMIT is the literal ceiling flights_limit()'s own source uses (T-29-03-01, T-29-03-02, 29-03-PLAN.md Task 3) - flights_limit('51') returned 51, outside [15, 50]
```
Note: the plan named `"999999999"` as the input expected to trip this check; the loop fails fast on the FIRST offending value in iteration order, which is `"51"` (it precedes `"999999999"` in the 19-entry hostile-input list). Both are symptoms of the same removed clamp — the check still catches the mutation and prints the offending input and returned value exactly as required, just not the specific literal the plan named first.

## Files Created/Modified
- `companion/pages/history_page.py` — `FLIGHTS_PAGE_SIZE`, `FLIGHTS_LIMIT_QUERY_PARAM`, `flights_limit(ctx)`, `_show_more_html()`, `SHOW_MORE_TEMPLATE`, `_FILTER_EMPTY_BODY_LIMITED_TEMPLATE`; `render()` slices `visible_rows` once before the per-row enrichment loop; `_filter_bar_html()` now takes `(shown, total_available)` and picks between the two empty-state templates
- `companion/app.py` — new `"flights_limit"` ctx key threaded raw and unvalidated, beside `resolve_prefix`
- `companion/pages/__init__.py` — ctx contract gained the `flights_limit` bullet
- `companion/layout.py` — `REFRESH_SWAP_SELECTORS_BY_PAGE[REFRESH_PAGE_FLIGHTS]` gained `.flights-more` as its fifth entry
- `companion/static/style.css` — `.history-card__primary` is now a two-track grid; `.history-card__time` gained `white-space: nowrap` and lost `margin-left: auto`; `.cell-primary`/`.cell-secondary` scoped to `grid-column: 1` under `.history-card__primary`; new `.flights-more`/`.flights-more:empty` rules
- `companion/i18n_fr/flights.py` — French twins for `SHOW_MORE_TEMPLATE` and the new filter-empty-limited sentence
- `companion/static/freshness.js` — `.flights-more` added to `SWAP_SELECTORS_BY_PAGE["flights"]` (the Rule-3 deviation described below)
- `companion/test_view_pages.py` — `_history_ctx()` gained a `flights_limit` kwarg; the registry-witness check's witness dict extended; one new grid-relationship check; three new pagination/security checks; `EXPECTED_CHECK_COUNT` re-derived twice (165, then 168); `ast`, `glob`, `inspect` imports added

## Decisions Made
See `key-decisions` in the frontmatter above: the query-param-over-`<details>` mechanism decision and its `freshness.js` ground, the disclosed filter trade-off, the clamp-not-reject direction for `flights_limit()`, and the freshness.js mirror-registry deviation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] freshness.js's own swap-registry mirror required the identical one-line addition**
- **Found during:** Task 1
- **Issue:** The plan's objective states the query-param mechanism needs "zero script change" to survive the refresh loop, and its acceptance criteria requires `git diff --stat companion/static/freshness.js companion/static/list-filter.js` to be empty. This is true for the swap LOGIC (no new function, no new event listener), but 29-RESEARCH.md and the plan both overlooked that `layout.REFRESH_SWAP_SELECTORS_BY_PAGE` has a second, independent JS-side mirror — `freshness.js`'s own `SWAP_SELECTORS_BY_PAGE` object literal — which `test_status_pages.py`'s pre-existing D1/CFG-35 check (`23-06-PLAN.md Task 1`) pins byte-equal, selector-for-selector, to the Python registry. Adding `.flights-more` to the Python side without the JS mirror fails that pre-existing check, and the plan's own `<verification>` section requires `test_status_pages.py` to pass.
- **Fix:** Added the identical `".flights-more"` string as a fifth array entry to `SWAP_SELECTORS_BY_PAGE["flights"]` in `companion/static/freshness.js` — a one-line, purely additive, mechanical mirror update, introducing no new logic, no new function, and no behavior beyond what the pre-existing mirror contract already demanded.
- **Files modified:** companion/static/freshness.js
- **Verification:** `test_status_pages.py` 312/312 (was failing 2/312 before this fix)
- **Committed in:** cd81a6f (Task 1 commit)
- **Note:** this makes the plan's stated acceptance criterion ("`git diff --stat` on those two files is empty") literally false. Documented here rather than silently sacrificing the green test suite to satisfy that one line — `git diff --stat cd81a6f~1 HEAD -- companion/static/freshness.js companion/static/list-filter.js` shows `companion/static/freshness.js | 3 ++-`.

**2. [Rule 1 - Bug] The pre-existing registry-witness check's witness dict needed a `.flights-more` entry**
- **Found during:** Task 1
- **Issue:** Adding a fifth region to `REFRESH_SWAP_SELECTORS_BY_PAGE[REFRESH_PAGE_FLIGHTS]` broke `test_view_pages.py`'s `_flights_declares_its_refresh_regions_and_never_the_filter_input()`, exactly as the plan's own `read_first` section predicted.
- **Fix:** Added `".flights-more": 'class="flights-more"'` to that check's `witnesses` dict.
- **Files modified:** companion/test_view_pages.py
- **Verification:** `test_view_pages.py` 164/164 (retargeted check, no net new `check(...)` call)
- **Committed in:** cd81a6f (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (Rule 3 — a pre-existing two-file registry contract this plan's own files touch; Rule 1 — a pre-existing check the plan's own read_first section flagged as needing this exact update). Both stayed inside files this plan's tasks already own or (for `freshness.js`) inside the one file the plan's own threat register and mechanism decision are centrally about. No scope creep.

## Issues Encountered
None beyond the two documented deviations above. Two implementation bugs were caught and fixed inline during Task 3 development, before any commit (not deviations — ordinary debugging of code written in this same session): (1) the `fetch(` regex in Check A initially matched an explanatory comment ("fetch( is a single, ...") in `freshness.js`'s own prose; fixed by running the scan through the pre-existing `_strip_js_comments()` helper. (2) Check C's `flights_limit(` call-count regex initially matched this plan's own new comment inside `render()` ("since flights_limit() never clamps below..."); fixed by switching to an `ast`-based call-node count, which cannot be confused by prose.

## Known Stubs
None.

## Threat Flags
None — every new/changed surface is already named and mitigated in the plan's own threat register (T-29-03-01 through T-29-03-05, T-29-03-SC), all disposition `mitigate` except the deliberate `accept` on unchanged session auth and the `accept` (not applicable) on the package-install gate. No new network endpoint beyond the already-covered `/flights?limit=N` query parameter on an already-session-gated route, no new auth path, no new file-access pattern, no schema change.

## Human Follow-ups
Carried from the plan (not blocking — no playwright in this sandbox):
1. On a 390px viewport with the realistic 36-flight fixture, re-measure Vols' page height with the registered instrument and report it against 3,355px (half of the audit's 6,710px). Report the real number; never restate the target to fit it.
2. On the same page, open "Afficher plus", wait out one 45-second refresh cycle, and confirm the list is still expanded and the link now offers the next page (the live half of the refresh-survival property this plan's Check A could only prove structurally).
3. With JavaScript disabled in a real browser, confirm the Show-more link still reveals more flights (the live half of the no-JS proof Check B could only prove structurally).

## Next Phase Readiness
Plan 29-03 is complete. `history_page.py`, `layout.py` and `style.css` are now in the state 29-04/29-05/29-06 (if they touch these same files) should build from. No blockers.

## Self-Check: PASSED

All 8 files in `key-files.modified` confirmed present on disk; all three task commit hashes (`cd81a6f`, `4ccb8ec`, `167041e`) confirmed present in `git log`.

---
*Phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o*
*Plan: 03*
*Completed: 2026-09-21*
