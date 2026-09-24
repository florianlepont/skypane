---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 07
subsystem: testing
tags: [pytest, css-parser, js-served-asset, companion, view-pages, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "06"
    provides: "companion/test_view_pages_helpers.py's detail_row_block()/table_markup()/seed_gallery()/seed_unresolved_prefixes()/write_panel_file()/strip_js_line_and_block_comments() and companion/test_view_pages_02.py's served_stylesheet()/served_asset() module-fixture conventions"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/css_rules()/declarations_for()/rules_with_selector() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
provides:
  - "companion/test_view_pages_03.py: 57 native pytest node ids (37 tests + a 19-way parametrized clamp test) porting part 03 of companion/test_view_pages.py (original check() calls #97-#134) - panel-lookup.js's date-math ban, the Airlines resolve-dialog action row and manual-count filter chip, the one-hop unresolved-airline link, Flights' day-separator/row-identity/refresh-region/detail-reveal/Show-more contracts, and Home's battery ring, relative-age elements and French render"
  - "a non-hardcoded JS-route-completeness floor (_all_static_script_routes(), enumerating companion/app.py's own *_SCRIPT_ROUTE constants) replacing the legacy check's glob.glob() over companion/static/*.js - TST-12-safe (no production source opened as text) without going stale against a hand-written file-count list"
  - "companion/test_view_pages.py shrunk: one EXPECTED_CHECK_COUNT = 35 line (was 73), 35/35 still pass standalone and through the shim"
  - "the view-pages ledger fragment's rows 97-134 flipped to ported with real node ids, Part 03 note added (25 B, 9 C, 5 J; 0 deleted, 2 partial S-rubric clause deletions inside otherwise-ported checks)"
affects: [33-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A completeness/vacuity check that used to glob.glob() a production static directory (\"scan every companion/static/*.js file\") is rewritten to derive its file set from the production module's own already-imported public constants (companion.app's *_SCRIPT_ROUTE names via dir()/re.match(), never a source-suffixed os.path.join(HERE, ...) glob) - the floor still trips if a route disappears from app.py, but the enumeration itself never opens a production source file as text (TST-12/G3)"
    - "A JS delivery-contract check whose forbidden/required tokens are real API calls (new Date(, toISOString, getAttribute(\"...\")) runs against companion_markup.strip_js_comments_and_strings()'s output; a check whose target token is itself a JS STRING LITERAL (a CSS class name assigned to a JS variable, e.g. var LIVE_CLASS = \"flight-rows-live\") must use test_view_pages_helpers.strip_js_line_and_block_comments() instead - the toolkit stripper erases string content along with comments/strings uniformly, which silently erases the very literal such a check searches for (confirmed by a real standalone failure during this plan, see Deviations)"
    - "A legacy check's ast.parse(inspect.getsource(...)) proof that a render() function calls a validator exactly once and never reads a raw ctx key directly is rewritten as a black-box behavioural equivalence instead: call render() directly with the same hostile input space the validator's own unit test uses, against a fixture large enough that the validator's clamp is the only way the observed output count could match across every hostile value - strictly stronger evidence for the same property than an AST walk over production source, and guard-G2-compliant (inspect/ast/tokenize over production source is banned outright)"

key-files:
  created:
    - companion/test_view_pages_03.py
  modified:
    - companion/test_view_pages.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md

key-decisions:
  - "_all_static_script_routes() (enumerating companion/app.py's *_SCRIPT_ROUTE constants) is added LOCAL to test_view_pages_03.py rather than the shared test_view_pages_helpers.py, because no other part of this chain's remaining slice (33-08) needs a JS-route completeness floor - if a later plan needs the same pattern it can promote it then, per the chain's own established discretion for module-local vs shared helpers"
  - "The two source-text/inspect.getsource clauses (row 109's strftime grep, row 119's AST walk over history_page.render()/app.py) are dropped as partial S-rubric deletions inside otherwise-ported checks, rather than a full-check deletion or a literal source-text port that guard G2 would reject outright - each check's SURVIVING assertions already prove the same property behaviourally (see tech-stack patterns above), so nothing the legacy check actually verified is lost, only the source-text PROOF MECHANISM changes"
  - "row 119's single legacy check splits into two pytest node ids (a 19-way parametrized clamp test over history_page.flights_limit() directly, and one render()-level behavioural-equivalence test) rather than one - the parametrized ids give per-hostile-input granularity the original single PASS/FAIL check() call never had, and the ledger row points at the render()-level test as primary per 33-MIGRATION-RULES.md section 3, with the parametrized family listed here"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~55min
completed: 2026-09-24
---

# Phase 33 Plan 07: View-Pages Migration Chain Part 03 Summary

**Migrated the next 38 of `companion/test_view_pages.py`'s original 169 check() calls (panel-lookup.js's date-math ban, the Airlines resolve-dialog action row, the one-hop unresolved-airline link, Flights' day-separator/row-identity/refresh-region/detail-reveal/Show-more contracts, and Home's battery ring/relative-age/French render) to 57 native pytest node ids in `companion/test_view_pages_03.py`, replacing every JS-source and CSS-source read with a served-asset/served-stylesheet fetch and two AST-introspection proofs with strictly-stronger behavioural equivalences.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `companion/test_view_pages_03.py`: 57 pytest node ids (37 tests + `test_flights_limit_clamps_every_hostile_input_into_bounds`'s 19-way parametrization) porting part 03 in full - panel-lookup.js's date-parsing ban (fetched via `served_asset()`, forbidden API tokens checked against `strip_js_comments_and_strings()`'s output as whole tokens), the resolve dialog's Save/Close action-row layout and its `.lightbox__actions` CSS rule (via `declarations_for()`), Airlines' Editing-badge/per-card-control retirement and full `data-view-panel-*` vocabulary (derived from the module's own `_VIEW_PANEL_*_ATTR` constants, never a hardcoded count), the manual-resolution count's promotion into a real filter-bar chip, the sub-960px two-fixed-column grid (via `declarations_for()`'s `at_rules=` parameter), the one-hop unresolved-airline link across three distinct row shapes (resolved/unresolved/route-only-unresolved), the hex-only row's hex-to-primary promotion, `RESOLVE_LINK_HREF_TEMPLATE`'s cross-module construction, Europe/Paris day separators (including the UTC-vs-Paris boundary case), every Flights row's stable cross-render event identity, the declared refresh-swap regions (and the filter input's deliberate exclusion), the detail row's grid-reveal animation contract (CSS + `flight-rows.js`'s live-script class, via `served_asset()` + `strip_js_line_and_block_comments()`), the chevron's transform-only transition and the stylesheet's fixed reduced-motion-block count, the phone card's disclosure-as-its-own-face structure, the two-track primary-line CSS grid across all three `primary_value_html` branches, the URL-reproducible pagination state plus `freshness.js`'s single `fetch()` target, the Show-more anchor's no-JS/no-script-mention proof (scanned across every one of `companion/app.py`'s own registered static-JS routes rather than a filesystem glob), a real CSS-selector-reachability proof for that same anchor (CR-01), `flights_limit()`'s 19-hostile-input clamp plus a render()-level behavioural equivalence standing in for the legacy AST walk, `list-filter.js`'s count-animation contract, the middle-dot route/state separator, the raw-ISO-behind-copy-control guarantee, the phone card's artwork thumbnail (shared CSS rule membership via `rules_with_selector()`/`css_rules()`), History's registry-table absence, Flights' French rendering (both the headings-only pass and the fully-seeded end-to-end pass), the merged i18n catalogue membership check, and eight distinct Home-page checks (seeded render, the battery ring's shared-emitter geometry proof, both relative-age element checks, the resolved/placeholder thumbnail contract, the hero one-liner and document-order check, and the French render's headings/alt-text pass).
- Every check that used to `open()` `companion/static/style.css`, `panel-lookup.js`, `flight-rows.js`, `list-filter.js` or `freshness.js` from disk now fetches it from a running `companion/app.py` (module-scoped `app`/`served_css`/`panel_lookup_js` fixtures) via `served_stylesheet()`/`served_asset()`, and asserts on `companion_markup.declarations_for()`/`css_rules()`/`rules_with_selector()` (CSS, including two at-rule-scoped lookups) or the served JS text (comment-stripped with either `companion_markup.strip_js_comments_and_strings()` for real-API-token checks or `test_view_pages_helpers.strip_js_line_and_block_comments()` when the target itself is a JS string literal).
- The one completeness-floor check that used to `glob.glob()` `companion/static/*.js` now derives its route set from `companion.app`'s own `*_SCRIPT_ROUTE` constants (`_all_static_script_routes()`) - a floor that still trips if a route disappears, without ever constructing a source-suffixed path off the module's `__file__`.
- Two legacy `ast.parse(inspect.getsource(...))` proofs (row 109's `history_page.py` strftime grep, row 119's `render()`/`app.py` AST walk) are dropped as partial deletions and replaced with behavioural equivalences already covered by each check's surviving assertions (row 109) or a new render()-level hostile-input test (row 119) - see the ledger fragment's Part 03 note for the full reasoning.
- `companion/test_view_pages.py` shrunk: the entire part-03 slice (the Section-1 "history_page.py" comment header through the `_home_page_french_render_translates_headings_and_alt_text_not_data` check() call) deleted from `main()`, plus the now-fully-unused `_row_block()`/`_strip_js_comments()`/`_detail_row_block()`/`_table_markup()`/`_seed_unresolved_prefixes()` helpers and the `glob`/`math`/`server.plane.illustrations`/`server.plane.manual_resolutions`/`server.poll_loop` imports (each confirmed by grep to have zero remaining call sites past this slice). `EXPECTED_CHECK_COUNT` set to `35` (was `73`). The shrunk harness still runs 35/35 standalone and through `companion/test_legacy_harness_shim.py`.
- The ledger fragment's rows 97-134 flipped to `ported` with real `companion/test_view_pages_03.py::test_*` node ids and a `### Part 03 (plan 33-07)` note (25 B, 9 C, 5 J rubric codes; 0 checks fully deleted, 2 partial S-rubric clause deletions inside otherwise-ported checks). `33-ledger-check.py --allow-pending companion/test_view_pages.py` confirms 169/169 baseline checks accounted for (134 ported, 35 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) - **1503 passed, 5 skipped, 0 failed** in 257s. No regression from this plan; `ruff check .` clean across every file this plan touched.

## Task Commits

1. **Task 1+2: part 03 (checks 97-134) ported to `companion/test_view_pages_03.py`** - `1c7b503` (test)
2. **Task 3: shrink the legacy harness, fill the ledger, verify** - `17b4a76` (test)

## Files Created/Modified

- `companion/test_view_pages_03.py` - 57 native pytest node ids (part 03)
- `companion/test_view_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 35`, part-03 checks and their now-unused closures/imports removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md` - rows 97-134 ported, Part 03 note added

## Decisions Made

See `key-decisions` in the frontmatter above: `_all_static_script_routes()` staying module-local to `test_view_pages_03.py` (no other in-flight slice needs it yet); the two partial S-rubric deletions (source-text/AST proofs replaced by already-covered or newly-added behavioural equivalences) rather than full-check deletion or a guard-violating literal port; and row 119 splitting into a parametrized clamp test plus a render()-level behavioural-equivalence test rather than staying one check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `flight-rows.js`'s live-script class check used the wrong JS stripper**
- **Found during:** Task 1, first standalone run of `test_detail_row_height_animates_and_a_closed_row_is_unreachable`
- **Issue:** The check fetched `flight-rows.js` and ran it through `companion_markup.strip_js_comments_and_strings()` before searching for the literal `"flight-rows-live"` - but that class name is itself a JS string literal (`var LIVE_CLASS = "flight-rows-live";`), and the toolkit stripper erases string/template-literal content along with comments, so the search always failed against the stripped text.
- **Fix:** Switched to `test_view_pages_helpers.strip_js_line_and_block_comments()` (strips only `//`/`/* */` comments, preserves string literals) for this one check, matching the exact caveat that helper's own docstring documents.
- **Files modified:** `companion/test_view_pages_03.py`
- **Verification:** Re-ran the test standalone; passes.
- **Committed in:** `1c7b503` (Task 1+2 commit)

**2. [Rule 3 - Blocking] `pytest-xdist` refused to run a hostile-input parametrization over a bare `object()`**
- **Found during:** Task 1, first `pytest -n auto` run of the new module
- **Issue:** `@pytest.mark.parametrize("raw", ..., ids=repr)` produced a test id embedding `object()`'s own memory address (`<object object at 0x...>`), which differs between xdist worker processes and made pytest-xdist abort with "Different tests were collected between gw0 and gwN".
- **Fix:** Replaced the `ids=repr` shorthand with an explicit, worker-stable id list (index-derived for the one opaque-object entry, `repr()` for everything else).
- **Files modified:** `companion/test_view_pages_03.py`
- **Verification:** `pytest -n auto` collects identically across all workers and passes.
- **Committed in:** `1c7b503` (Task 1+2 commit)

**3. [Rule 3 - Blocking] Deleting this slice's own `ast.parse(inspect.getsource(...))` usage exposed a pre-existing `ruff` F811 regression further down the still-legacy file**
- **Found during:** Task 3, `ruff check companion/test_view_pages.py` after the shrink
- **Issue:** Two nested still-legacy functions further down the file (`_home_top_is_one_composition_holding_the_ring_and_the_band`, `_the_heros_ring_is_the_emitter_healths_ring_is`) each carry their own redundant local `import ast`/`import inspect`, shadowing the module-level imports. Before this plan, the module-level `ast`/`inspect` bindings had an earlier, bare (non-shadowed) use inside this slice's own `_flights_limit_is_clamped_and_the_clamp_is_the_only_path` check, which kept `ruff` from flagging the later local shadow-imports as "redefinition of unused" (F811). Deleting that check (replaced by a behavioural equivalence, see key-decisions) removed the only bare use, exposing the F811 warning on the two later local imports.
- **Fix:** Removed the two now-redundant local `import ast`/`import inspect` lines (kept `import textwrap` where still needed) - exactly `ruff`'s own suggested fix. Zero behavioural change: both functions still resolve `ast`/`inspect` from the module-level import.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `ruff check companion/test_view_pages.py` clean; both affected functions still pass through `companion/test_view_pages.py`'s own standalone run (35/35).
- **Committed in:** `17b4a76` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three are narrow, verified fixes discovered while running each new/shrunk file standalone - no scope creep, no file touched beyond this plan's own `files_modified` list.

## Issues Encountered

None beyond the deviations above. The legacy-slice deletion (Task 3) required confirming, by grep, that every helper/import candidate for removal (`_row_block()`, `_strip_js_comments()`, `_detail_row_block()`, `_table_markup()`, `_seed_unresolved_prefixes()`, `glob`, `math`, `server.plane.illustrations`, `server.plane.manual_resolutions`, `server.poll_loop`) truly had zero call sites past this slice's own line range before deleting it, per `33-MIGRATION-RULES.md` section 1's "setup that remaining checks still need stays."

## User Setup Required

None.

## Next Phase Readiness

- 33-08 (part 04, the chain's final plan) can continue shrinking `companion/test_view_pages.py`'s single `EXPECTED_CHECK_COUNT` line from `35`, and reuse the `served_stylesheet()`/`served_asset()` + `declarations_for()`/`css_rules()`/`rules_with_selector()` + `strip_js_line_and_block_comments()` conventions this plan and 33-06 both establish.
- `_all_static_script_routes()`'s pattern (deriving a completeness floor from a production module's own already-imported constants, rather than a filesystem glob) is directly reusable by any later plan that needs to scan every served JS asset without opening a source file as text.
- No blockers. `companion/test_view_pages.py` still has 35 pending checks (the remainder of Home's still-legacy sections: the quiet-hours nightly-regression fixture, `frame_state`/`wake` module checks, `battery.py`'s import-boundary check, and the one remaining end-to-end HTTP round trip) for the chain's closing plan (33-08).

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_view_pages_03.py`,
`companion/test_view_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md`,
this summary), and both commit hashes (`1c7b503`, `17b4a76`) found in
`git log --oneline --all`.
