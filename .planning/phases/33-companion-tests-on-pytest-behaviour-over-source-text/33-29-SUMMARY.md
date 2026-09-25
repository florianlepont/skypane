---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 29
subsystem: testing
tags: [pytest, css-parsing, js-parsing, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's rows 172-244 build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture, reused here for the served-CSS/JS checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/css_rules()/declarations_for()/rules_with_selector()/keyframes() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "28"
    provides: "companion/test_status_pages_helpers.py's seeding wrappers and strip_js_line_and_block_comments(), and the module-split naming convention (test_status_pages_NN.py/_NNb.py) this plan extends"
provides:
  - "companion/test_status_pages_05.py: 190 native pytest node ids (37 baseline checks, the three 52-vendored-illustration checks parametrized per file so xdist spreads them) porting the original harness's checks #172-#208 — Home/Frame-strip freshness going live from layout.freshness_line_html()'s one definition site, the strip's countdown (formatting only, never deciding) and the picture's src-compared fade, layout.stat_tile()'s caption_title tooltip, Health's plain-language tile/corroboration text, the 52 vendored illustrations' normalized-output contract, page_shell()/login_shell()'s <html lang> and two ordered theme forms, the French nav labels and D-17 always-rendered Advanced group, the nav status reminder, status_row()/section_intro_html(), and relative_age_text()/local_clock_text()'s French forms"
  - "companion/test_status_pages_05b.py: 36 native pytest node ids porting checks #209-#244 — relative_time_html()'s <time data-relative> wrapping of both ladders in both languages, Health's French rendering and English byte-identity, device/pipeline timestamp localisation, the French health catalogue, the Airlines gallery (page header, card count, image-source membership, per-airline chips, the search-filter bar, Safari contact-autofill suppression, hyphen-free ids), the D-13/D-17 non-goal guards, the click-to-enlarge lightbox and its stylesheet contract, the mobile button override's source order, the lightbox's max-width contract, and the illustration-replace form"
  - "the audit's remaining status-pages TST-12 evidence for source-text reads closed for this slice: no check in either new module opens a production .py/.html/.css/.js file as text; the two ast-based Safari-autofill-suppression sweeps and the ast-based import-statement grep are all rewritten to runtime/rendered behaviour"
  - "companion/test_status_pages.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 146 to 73; part 05's 73 checks removed from main(); three small helpers (_home_ctx, _NAV_STATUS_DEVICE_CFG, _card_slice) that used to sit beside their first Section 1/2 use are relocated (not deleted) because later, not-yet-migrated checks still depend on them; now-unused ast/glob/inspect/i18n_fr.health/server.plane.render imports dropped"
  - "the status-pages ledger fragment's rows 172-244 flipped (72 ported — three to a primary parametrized node id each — 1 deleted with an S reason); 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for (242 ported, 2 deleted, 73 pending)"
affects: [33-30, 33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The 52-vendored-illustration checks (dimensions, byte ceiling, centring) are each @pytest.mark.parametrize('filename', sorted(illustrations.target_filenames())) over the production registry's own enumeration — never a companion/static-style filesystem glob — so xdist spreads all 156 instances across workers instead of one long serial loop; the ledger fragment maps each of the three original checks to its primary id ([air-algerie.png], the first sorted filename)"
    - "An ast-based forward guard against a hypothetical future filter bar (rows 230/231's legacy checks) has no clean rewrite under TST-12: guard G2 bans ast/inspect introspection of production source in this suite, so the port narrows scope deliberately to the rendered behaviour on the pages this app actually serves a search input on today (Compagnies, Health, Flights) — a known, smaller guarantee than static analysis provided, recorded as such rather than silently narrowed"
    - "A 'module X never imports Y' check (row 234) cannot always become a subprocess sys.modules membership test (33-25's own precedent): when X is required to import a THIRD module that itself imports Y transitively (here, poll_loop imports sqlite3/server.history_db), sys.modules will carry Y regardless of X's own source. The correct runtime equivalent is inspecting X's own module namespace (vars(X)) for a binding to Y's module object directly — a fact about X's own import statements, not about the transitive closure"
    - "Bulk line-range deletion in this large legacy file dropped three closures/constants (_home_ctx, _NAV_STATUS_DEVICE_CFG, _card_slice) that later, still-legacy checks (parts 06/07) depend on even though their own first-use checks were migrated away; ruff's F821 (undefined name) caught all three immediately on the shrunk file, and they are restored in place, right after the check() closure, with a comment naming why they survive there now"
  key-files:
    created:
      - companion/test_status_pages_05.py
      - companion/test_status_pages_05b.py
    modified:
      - companion/test_status_pages.py
      - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "Row 185 (a companion-wide grep for a second ALPHA_THRESHOLD constant definition) is deleted, not rewritten: the same module's own centred/unclipped-bbox checks already call server.plane.render._opaque_bbox() directly, so a stray unused constant elsewhere in the package would never change what those checks observe — no behaviour exists for the source-text claim to stand in for"
  - "Row 172's freshness-line check keeps its full rendered-equality/ordering assertions and drops only its two source-text sub-clauses (grepping health_page.py/layout.py for a markup literal), which are redundant with the SAME check's own proof that both pages render layout.freshness_line_html()'s output verbatim"
  - "Row 208's inspect.getsource() signature-order check becomes a behaviour proof instead: relative_age_text(30, 'fr') is compared against relative_age_text(age_seconds=30, lang='fr') — a signature that quietly swapped the two positional parameters would satisfy the keyword call but not the positional one"
  - "Rows 230/231 (the Safari contact-autofill forward guards) trade the legacy checks' whole-package ast static analysis for a narrower rendered-behaviour check on the three pages known to render a search input today, since TST-12's guard leaves no source-scanning mechanism available to a pytest module in this suite — documented as a scope reduction, not silently absorbed"
  - "Row 234 (airlines_page.py imports no sqlite3/history_db) is rewritten as vars(airlines_page) namespace inspection rather than a sys.modules subprocess check, after the sys.modules approach was tried first and failed for a real reason: poll_loop (which airlines_page.py is required to import) itself imports both modules transitively"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~55min
completed: 2026-09-25
---

# Phase 33 Plan 29: Status-Pages Part 05 (Home/Frame-Strip Freshness, Illustration Normalize, Nav/Status-Row Primitives, Airlines Gallery, Click-to-Enlarge Lightbox) Summary

**Migrated the fifth of seven status-pages harness slices to native pytest — 73 legacy checks becoming 226 pytest node ids across two new modules — closing the two remaining ast-based source-scan checks in this harness by rewriting one as a runtime module-namespace check and narrowing the other two to rendered-page behaviour on the pages this app actually serves, since guard G2 leaves no production-source-scanning mechanism available to a pytest module in this suite.**

## Performance

- **Duration:** ~55 min (commit-to-commit)
- **Started:** 2026-09-24T23:56:51Z (STATE.md's own last-recorded session timestamp)
- **Completed:** 2026-09-25T00:52:00Z (approx, full-suite verification run)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_status_pages_05.py`: 190 pytest node ids covering all 37 of part 05's first-half checks (#172-#208) — Home's and Health's freshness lines proven byte-identical to `layout.freshness_line_html()`'s own output with the dot/prefix/clock/pill in source order; Home's declared swap regions checked against every literal they name in the rendered page, with the Display scope pinned to exactly the strip and freshness line; the Frame strip's next-update `<time data-relative-countdown>` proven to read `companion/wake.py`'s own resolved instant while the state word stays `frame_state.resolve_state()`'s, with every served `*_SCRIPT_ROUTE` script checked for zero frame-state vocabulary; the refreshed picture's fade rule (keyframes existence, `var(--motion-fast)` spend, no bare duration literal) checked structurally against the served stylesheet, and `freshness.js`'s own `markPictureFade()` checked for the src-comparison/`FADE_CLASS` contract via `served_asset()`; `layout.stat_tile()`'s `caption_title` tooltip (byte-identity when unused, tooltip placement, escaping); Health's plain-language tile/corroboration text and its full-render jargon/requirement-id sweep; all 52 vendored illustrations' normalized-output contract (identical target dimensions, the 65536-byte ceiling, sub-1px centring), each parametrized per vendored filename so xdist spreads all 156 instances, plus the None-opaque-bbox fallback; `page_shell()`/`login_shell()`'s `<html lang>` and the two ordered, aria-labelled theme forms; the French nav labels and the D-17 always-rendered Advanced group; the nav status reminder's markup/position/dot-classes/French text/None-degrade contract; `status_row()`/`section_intro_html()`'s markup and escaping; `_device_timestamp_only()`'s verdict-free fragment; and `relative_age_text()`/`local_clock_text()`'s French forms, including a rewritten positional-signature proof.
- `companion/test_status_pages_05b.py`: 36 pytest node ids covering all 36 of part 05's second-half checks (#209-#244) — `relative_time_html()`'s `<time data-relative>` wrapping of both the past and future ladders in both languages (equal text, matching instant), its degrade-to-plain-text paths, the future ladder sharing the past ladder's own bucket boundaries, and `concise_timestamp_html()`'s relative half becoming an element with its absolute-first ordering and no-raw-ISO rule intact; Health's French rendering, its English byte-identity, its device/pipeline timestamp full localisation, and the French health catalogue's non-empty-string invariant; the Airlines gallery's shared page header, one-card-per-target-airline count, image-source route-membership, the Air Caraïbes/Air France chip contracts, `variant_chip_label()`, the illustration route-prefix constant, card image intrinsic dimensions, the four filter-bar contract markers, the Clear button, the filter label/id pairing, Safari contact-autofill suppression (now checked across all three pages this app renders a search input on), hyphen-free filter ids (now checked against the real `_FILTER_INPUT_ID` constants plus every rendered id), the filter count/empty-state total, and per-card filter text/group; the D-13/D-17 non-goal guards (no duplicated registry/stats headers, Health still carries both header sets, `airlines_page` imports no history-database or sqlite module while still importing `poll_loop`, and exposes none of the deleted diagnostics symbols); the click-to-enlarge lightbox's zoom-button attribute contract, the shared dialog's markup and empty note, its stylesheet contract (structural, against the served stylesheet), the mobile button override's `@media` source order, the lightbox's max-width-matches-illustration-width contract; and the illustration-replace form's trigger-membership and method/enctype/action contract.
- Three checks' `ast`-based module-wide source scans (TST-12 rubric S) are rewritten, not carried forward verbatim: the Safari contact-autofill-suppression sweep and the hyphen-free-filter-id sweep both used to walk every `companion/pages/*.py` and `companion/app.py` module's AST for a `<input type="search" ...>`-shaped string literal, specifically to forward-guard against a hypothetical future filter bar; guard G2 bans `ast`/`inspect` introspection of production source in this suite, so what's ported instead is a direct check of every `*_FILTER_INPUT_ID` constant this harness already imports (never source text) plus a structural, `parse_html()`-parsed check of every currently-rendered `<input type="search">` across the three pages this app renders one on today (Compagnies, Health, Flights) — a documented, narrower scope than the legacy static analysis provided, not a silent absorption. The third, `airlines_page.py` importing no history-database/sqlite module, is rewritten as a runtime check of `vars(airlines_page)` for a name bound to the `sqlite3`/`server.history_db` module objects directly, after a first attempt at a `sys.modules`-membership subprocess check (33-25's own precedent) failed for a real reason: `poll_loop`, which `airlines_page.py` is required to import, itself imports both modules transitively, so `sys.modules` would carry them regardless of what `airlines_page.py`'s own source says.
- One check is deleted outright (TST-12 rubric S): "no module anywhere under `companion/` defines its own alpha-threshold constant" grepped every `.py` file under `companion/` for a second `ALPHA_THRESHOLD` assignment, with no behaviour behind it beyond what this same module's own centred/unclipped-bbox checks already prove by calling `server.plane.render._opaque_bbox()` directly.
- One check's two source-text sub-clauses are dropped in place (rubric S), its structural half kept fully intact: the freshness-line check's own grep of `companion/pages/health_page.py`/`companion/layout.py` for a `class="page-header__freshness` literal is redundant with the SAME check's own rendered-equality proof (`built in rendered`, for both Health and Home).
- Every CSS check in this slice (the picture-fade rule, the zoom stylesheet contract, the mobile button override's source order, the lightbox max-width contract) fetches the stylesheet `companion/app.py` actually serves and asserts on it structurally via `companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`/`keyframes()`, never a regex/substring probe over the raw served text (33-FOLLOWUPS.md F-01). Every check reading a served script (`freshness.js`, and every `*_SCRIPT_ROUTE`) fetches it via `served_asset()` and strips only comments with this chain's `strip_js_line_and_block_comments()`.
- `companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT` dropped from 146 to 73; part 05's 73 checks removed from `main()`. Bulk line-range deletion over this large legacy file dropped three closures/constants (`_home_ctx`, `_NAV_STATUS_DEVICE_CFG`, `_card_slice`) that later, not-yet-migrated checks (parts 06/07) still depend on even though their own first-use checks were migrated away — caught immediately by `ruff`'s F821 on the shrunk file, and restored in place (Rule 1 auto-fix) right after the `check()` closure with a comment explaining why they survive there now. Now-unused `ast`/`glob`/`inspect`/`companion.i18n_fr.health`/`server.plane.render` imports were also dropped (caught by ruff).
- The ledger fragment's rows 172-244 flipped: 72 rows to `ported` (three of them — the 52-illustration checks — to a single primary parametrized node id, `[air-algerie.png]`, each; the SUMMARY here and the ledger note list the other 51 ids per row), 1 row (185) to `deleted` with an S reason. `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (242 ported, 2 deleted, 73 pending).
- Verification beyond the plan's own scoped checks: `companion/test_suite_guards.py test-support` (107 tests) stays green; `ruff check` clean on every file this plan touched; the FULL suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`) runs **2484 passed, 5 skipped, 0 failed** — no new failures, no new `DeprecationWarning`s from any file this plan wrote.

## Task Commits

1. **Task 1: Calls #172-#208 into test_status_pages_05.py (37 checks, 190 pytest node ids)** - `7865347` (test)
2. **Task 2: Calls #209-#244 into test_status_pages_05b.py (36 checks, 36 pytest node ids)** - `04fb925` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `b05c557` (test)

## Files Created/Modified

- `companion/test_status_pages_05.py` - 190 pytest node ids porting part 05's first 37 legacy checks
- `companion/test_status_pages_05b.py` - 36 pytest node ids porting part 05's remaining 36 legacy checks
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 73`; part 05's checks removed; three still-needed helpers relocated; unused imports dropped
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 172-244 flipped, Part 05 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the alpha-threshold check is deleted outright (no behaviour beyond an existing check elsewhere in the same module); the freshness-line check drops two redundant source-text sub-clauses; the positional-signature check becomes a positional-vs-keyword call comparison; the two Safari-autofill forward guards trade whole-package static analysis for a narrower, documented rendered-behaviour check on the three pages known to render a search input today; and the airlines_page import check is rewritten as a module-namespace inspection rather than a `sys.modules` check, after the more obvious `sys.modules` rewrite was tried and found to fail for a real reason (a required transitive import of the very modules being excluded).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored three helpers a bulk line-range deletion dropped that later checks still need**
- **Found during:** Task 3, running `ruff check` on the shrunk `companion/test_status_pages.py`
- **Issue:** Removing part 05's 73 checks from `main()` also removed `_home_ctx()`, `_NAV_STATUS_DEVICE_CFG` and `_card_slice()` — closures/constants that used to sit beside their OWN first use inside part 05's checks, but which several later, not-yet-migrated checks (parts 06/07, still legacy) also reference. `ruff`'s F821 (undefined name) caught all three immediately.
- **Fix:** Re-added all three, verbatim, in a small "shared helpers still used by later checks below" block right after the `check()` closure definition, with a comment explaining why they now live there instead of beside their original first use.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** `ruff check` clean; the shrunk harness re-verified 73/73 green standalone and through `companion/test_legacy_harness_shim.py -k status_pages`.
- **Committed in:** `b05c557` (Task 3 commit)

**2. [Rule 1 - Bug] The `sys.modules`-subprocess rewrite for the airlines_page import check was itself wrong on first attempt**
- **Found during:** Task 2, running the new module standalone
- **Issue:** The first draft of the `airlines_page.py` imports-no-sqlite/history_db check followed 33-25's own `test_wake_module_never_imports_pages_or_app()` precedent (import in a subprocess, check `sys.modules`). It failed: `airlines_page.py` is required to import `server.poll_loop`, which itself imports `sqlite3` and `server.history_db`, so both land in `sys.modules` regardless of what `airlines_page.py`'s own source says — the subprocess check could never pass while poll_loop stayed a required import.
- **Fix:** Rewrote as a runtime check of `vars(airlines_page)` (the module's own namespace) for a binding to the `sqlite3`/`server.history_db` module objects directly — a fact about `airlines_page.py`'s own import statements, immune to what any imported module imports transitively.
- **Files modified:** `companion/test_status_pages_05b.py`
- **Verification:** Full module re-run green; the check now correctly distinguishes `airlines_page.py`'s own `import server.poll_loop as poll_loop` from the modules that statement transitively pulls in.
- **Committed in:** `04fb925` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs caught before their respective commits)
**Impact on plan:** Both were necessary for the plan's own acceptance criteria (a green shrunk harness; a check that actually tests what it claims). No scope creep — no file outside this plan's own `files_modified` list was touched.

## Issues Encountered

None beyond the two auto-fixes above, both caught and fixed before their respective task commits.

## User Setup Required

None.

## Next Phase Readiness

- 33-30/33-31 (the chain's remaining 2 plans) continue shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 73), starting at `_replace_form_file_input_id_is_unique_and_labelled()` — the check right after part 05's own last anchor.
- The three relocated helpers (`_home_ctx`, `_NAV_STATUS_DEVICE_CFG`, `_card_slice`) are ready for 33-30/33-31 to consume as-is; whichever of those plans migrates the checks that still call them should either port the helper alongside its last remaining caller or fold it into `companion/test_status_pages_helpers.py` if a later part also needs it.
- The "ast-based forward guard against a future filter bar" scope reduction (rows 230/231) is a known, recorded gap: any later phase considering a fourth companion filter bar should re-check the three rendered pages this plan's tests cover, since no source-scanning safety net exists under TST-12 to catch one added elsewhere.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk
(`companion/test_status_pages_05.py`, `companion/test_status_pages_05b.py`,
`companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`,
this summary) and all 3 commit hashes (`7865347`, `04fb925`, `b05c557`)
found in `git log --oneline --all`.
