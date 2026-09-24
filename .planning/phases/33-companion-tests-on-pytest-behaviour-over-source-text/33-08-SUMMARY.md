---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 08
subsystem: testing
tags: [pytest, css-parser, day-band, hero-composition, companion, view-pages, migration, chain-closed]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "07"
    provides: "companion/test_view_pages_helpers.py's seed_runway_events()/seed_gallery()/write_panel_file()/history_ctx() and the served_stylesheet()/served_asset() + declarations_for()/css_rules()/rules_with_selector() conventions the whole view-pages chain shares"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/css_rules()/declarations_for()/rules_with_selector() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
provides:
  - "companion/test_view_pages_04.py: 33 native pytest node ids porting part 04 of companion/test_view_pages.py (original check() calls #135-#169, the chain's LAST slice) - Home's fully-seeded French render, the status card's localised health-state timestamps, the Frame/Flight-data tile verdict contracts, four CSS-only checks (one consolidated) rewritten over the served stylesheet's parsed rules, Home's quick-action/headline/health-link/degrade/battery-move contracts, companion/draw.py's day-band time-scale/night-window/crowding/class contracts, Home's own day-band integration (Paris-day bucketing, quiet-hours shading, one extra history.db read), the hero composition proving the ring/band are calls into the shared emitter rather than a forked copy, companion.wake/companion.frame_state's own resolution contracts, and two real HTTP round trips (the retired /preview page, the Airlines dialog forms) plus the shared @starting-style lightbox entrance"
  - "companion/test_view_pages.py deleted outright (git rm) - the view-pages chain is CLOSED: all 169 baseline checks are accounted for across companion/test_view_pages_01.py..04.py (167 new node ids) plus 2 consolidated into companion/test_companion_app_03.py's pre-existing identical coverage, 0 pending"
  - "the view-pages ledger fragment's remaining 35 rows flipped to ported (33 to new companion/test_view_pages_04.py node ids, 2 consolidated to companion/test_companion_app_03.py), a Part 04 closing note added, 33-ledger-check.py WITHOUT --allow-pending confirms 169/169, 0 pending"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A check that walks a page module's own source with inspect.getsource()/ast.parse() to prove 'no forked drawing markup' (banned outright by guard G2) is trimmed to its surviving structural/vocabulary assertions when a SEPARATE check in the same slice already proves the identical property by mutation instead of static analysis: test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from mutates companion/draw.py's own class constant at runtime and observes both consumer pages move together, which a page carrying its own copy of the markup could not do - strictly stronger evidence than a source-literal scan, so the scan clause is a partial S-rubric deletion rather than a guard-violating literal port"
    - "A 'module X never imports Y' source check whose CSS-literal half has no subprocess equivalent splits into two proof mechanisms in the SAME rewritten test: the import-boundary half becomes a subprocess-import + sys.modules check (companion/test_companion_app_03.py's own battery/draw import-boundary precedent), and the 'never names a CSS class literal' half becomes a scan of the module's OWN already-imported public string constants (vars(module) filtered to isupper()+str) - the module's actual returned copy, never inspect/ast over its source text (guard G2 bans both modules outright, not just their use against a specific target)"
    - "Two checks whose behavioural claim is IDENTICAL to a check a different harness's own migration already ported (companion/test_companion_app_03.py's @supports selector(:has(*)) feature-query-block count and its companion.battery import-boundary check) are consolidated by pointing the ledger row's target at the EXISTING node id rather than duplicating the assertion in a second module - 33-MIGRATION-RULES.md section 3's 'several old checks may map to one node id' applies symmetrically across harnesses, not only within one harness's own chain"
    - "The 33-ledger-check.py tool matches a 'ported' row's target against pytest --collect-only's own node-id strings with an EXACT equality test (not a prefix/contains match) - a target cell carrying a node id PLUS a parenthetical explanation fails validation even though the node id substring is correct; the explanation belongs in the fragment's prose note below the table, never inside the target cell itself"

key-files:
  created:
    - companion/test_view_pages_04.py
  modified:
    - companion/test_view_pages.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md

key-decisions:
  - "row 146 (the @supports selector(:has(*)) block count) and row 166 (companion/battery.py's import-boundary check) are consolidated to companion/test_companion_app_03.py's pre-existing, byte-identical coverage rather than ported to a second copy in this module - both checks assert EXACTLY the same behaviour with the EXACT same technique (F-01's sanctioned served-text regex exception for the CSS check; the subprocess+sys.modules technique for the import-boundary check) a prior 33-16 plan already established for a different harness's own migration slice"
  - "row 160's inspect.getsource() forbidden-literal/required-call scan and row 161's ast.parse() restated-literal scan are dropped as partial S-rubric deletions rather than fully deleted checks or guard-violating literal ports - both properties are proven MORE strongly by row 162's mutation-based test (test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from), which is already in the same slice and already fully ported"
  - "every hardcoded '/tmp/skypane-no-such-state-dir'-style literal state_dir the legacy checks used is replaced with a real tmp_path fixture (a plain string sentinel for checks that never touch history_db, tmp_path / 'absent' / 'nested' for checks that do) - the legacy literal actually created a stray directory under the CWD when this plan first ran the ported tests standalone (not under /tmp, since the harness runs from the repo root), caught and fixed before the first commit (see Deviations)"

requirements-completed: [TST-10, TST-12, TST-13, TST-14, TST-15]

# Metrics
duration: ~35min
completed: 2026-09-24
---

# Phase 33 Plan 08: View-Pages Migration Chain Part 04 (Chain Closed) Summary

**Migrated the view-pages chain's final 35 check() calls (Home's French render, the day-band/hero composition contracts, wake/frame_state's own resolution contracts, and two HTTP round trips) into `companion/test_view_pages_04.py`'s 33 native pytest node ids, deleted the legacy `companion/test_view_pages.py` outright, and closed its ledger fragment at 169/169 with 0 pending — the chain that started at 33-05 is now fully migrated.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 1 deleted, 1 ledger fragment updated)

## Accomplishments

- `companion/test_view_pages_04.py`: 33 pytest node ids porting the chain's final 35 baseline checks in full — Home's fully-seeded French end-to-end render and its status card's localised REAL `health_page.compute_health_state()` timestamps, the Frame/Flight-data tile verdict contracts (the nightly quiet-hours regression, the late-frame flip, the single-verdict Flight-data tile, the display-airline alias, the X4 'Frame' naming collision, the one-line time cell), four CSS-only checks rewritten over `served_stylesheet()` + `companion_markup.declarations_for()`/`rules_with_selector()` (one — the `@supports selector(:has(*))` block count — consolidated into `test_companion_app_03.py`'s identical, pre-existing coverage rather than duplicated), the merged i18n catalogue check, Home's quick-action/headline/health-link/degrade-with-nothing/battery-percent-moved contracts, `companion/draw.py`'s four day-band unit contracts (time-scale-not-index-scale, the wrapping night-window shading, crowded-mark collapsing with an exact count, class/colour registration), Home's three day-band integration checks (Paris-clock placement and captioning, quiet-hours shading, the Paris-day-boundary bucketing plus a measured one-extra-`history.db`-read cost), the hero composition's three checks (single-composition containment, the ring/band class-vocabulary-shared-with-Health proof, and the mutation-based "breaking a shared emitter breaks both consumers together" proof), `companion.wake`/`companion.frame_state`'s own resolution contracts (the quiet-hours-aware `next_wake_at_iso()`/`next_wake_status()` fixtures A-E, `resolve_state()`'s due/held/late/unknown ladder including the nightly regression end to end), `companion/frame_state.py`'s view-free boundary (rewritten per rubric S), and two real HTTP round trips (`/preview`'s redirect and the retired `/preview.png`'s 404, the Airlines dialog forms rendering unconditionally) plus the shared `@starting-style` lightbox entrance rewritten from a raw-CSS-text scan into structural `rules_with_selector()`/`declarations_for()` lookups.
- Two checks that used to `open()` `companion/frame_state.py`/`companion/battery.py` from disk are rewritten per rubric S: `test_frame_state_is_view_free_and_localises_its_own_copy` proves the "never imports layout" half with a subprocess import + `sys.modules` check (the same technique `companion/test_companion_app_03.py`'s own `battery`/`draw` import-boundary checks already established) and the "never names a CSS dot class" half against `frame_state`'s own already-imported public string constants; the identical `companion/battery.py` check is fully consolidated to `test_companion_app_03.py`'s pre-existing node id rather than duplicated.
- Two checks that used a banned `inspect.getsource()`/`ast.parse()` syntax-tree walk over `companion/pages/home_page.py` (guard G2) to prove "no forked ring/band markup" are trimmed to their surviving structural/vocabulary assertions — the identical property is proven MORE strongly by `test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from`'s runtime mutation (both pages move together when the shared emitter's own class constant changes, which a forked copy could not do).
- The `@starting-style` lightbox-entrance check (`test_both_dialogs_arrive_through_one_starting_style_entrance`) is rewritten from the legacy harness's own raw-CSS-text regex scan (flagged by 33-FOLLOWUPS.md F-01 as the anti-pattern this closing plan must not repeat) into fully structural `companion_markup.rules_with_selector()`/`declarations_for()` lookups keyed on parsed `Rule.at_rules`/`Rule.declarations` — no regex/substring test over served CSS text anywhere in this new module.
- `companion/test_view_pages.py` deleted outright (`git rm`): its `EXPECTED_CHECK_COUNT`/`check()`/`main()`, `Harness`, `http_request`, `_NoRedirectHandler` and every remaining seeding helper leave the tree with it. `skypane_test_support.legacy_companion_harnesses()`'s disk-derived set and `companion/test_legacy_harness_shim.py`'s parametrize list both drop the file automatically — confirmed by a direct Python check and by `test_legacy_harness_shim.py`'s own consistency test staying green.
- The ledger fragment's rows 135-169 flipped to `ported` (33 to new `companion/test_view_pages_04.py::test_*` node ids, 2 consolidated to `companion/test_companion_app_03.py`'s pre-existing identical coverage), a `### Part 04 (plan 33-08) — chain closed` note added. `33-ledger-check.py companion/test_view_pages.py` **WITHOUT** `--allow-pending` confirms **169/169 baseline checks mapped (169 ported, 0 deleted, 0 pending)**.
- Full-suite verification beyond this plan's own scoped checks: `pytest -n auto companion test-support server stub-server deploy` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **1862 passed, 5 skipped, 0 failed** (up from the prior baseline's 1829 passed by exactly the 33 new node ids this plan adds). A single flaky failure in `companion/test_app_server_fixture.py::test_stop_kills_the_whole_process_group_including_a_grandchild` (a process-group-timing test owned by 33-02, never touched by this plan) appeared on the first full-suite run under `-n auto` load and passed standalone and on a full clean re-run; not a regression from this plan (see Issues Encountered). `ruff check .` clean across the whole tree.

## Task Commits

1. **Task 1: first half of part 04 (17 tests) ported to `companion/test_view_pages_04.py`** - `978180f` (test)
2. **Task 2: second half of part 04 (16 more tests) ported to `companion/test_view_pages_04.py`** - `93290bc` (test)
3. **Task 3: legacy harness deleted, ledger closed, full chain verified** - `9b88ac1` (test)

## Files Created/Modified

- `companion/test_view_pages_04.py` - 33 native pytest node ids (part 04, the chain's closing module)
- `companion/test_view_pages.py` - deleted outright (`git rm`)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md` - rows 135-169 ported, Part 04 closing note added, 0 pending

## Decisions Made

See `key-decisions` in the frontmatter above: the two cross-harness consolidations (the `@supports selector(:has(*))` count and the `battery.py` import-boundary check, both already ported byte-identically by `companion/test_companion_app_03.py`); the two partial S-rubric deletions inside the hero-composition checks (dropped in favour of the already-present, strictly-stronger mutation proof); and every hardcoded host-path literal replaced with a `tmp_path`-derived one.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality / TST-13] Hardcoded literal state-dir paths would have written outside `tmp_path`**
- **Found during:** Task 1, first standalone run of the newly-written module
- **Issue:** The legacy checks this slice ports used a hardcoded `"/tmp/skypane-no-such-state-dir"` literal wherever a check needed a `state_dir` value it never expected to be read. Ported as a bare string literal (`"no-state-dir-needed"`) instead, this became a RELATIVE path — and `companion.pages.home_page`'s render path resolves it against the process's current working directory rather than treating it as inert, so running the new tests from the repo root created a real `no-state-dir-needed/` directory in the working tree (confirmed via `git status --short` immediately after the first test run).
- **Fix:** Every such literal is replaced with `str(tmp_path / "absent" / "nested")` (the migration rules' own sanctioned pattern for "a missing path", already established by `test_view_pages_03.py`), so any accidental write lands inside pytest's own `tmp_path` and is cleaned up automatically.
- **Files modified:** `companion/test_view_pages_04.py`
- **Verification:** Re-ran the whole module standalone; `git status --short` confirmed no stray directory anywhere in the working tree afterward.
- **Committed in:** `978180f` (Task 1 commit) — caught and fixed before the first commit, so no fix-up commit was needed.

**2. [Rule 3 - Blocking] The ledger checker rejects a target cell that carries a node id plus a parenthetical explanation**
- **Found during:** Task 3, first `33-ledger-check.py` run after flipping the two consolidated rows
- **Issue:** `33-ledger-check.py` matches a `ported` row's target against `pytest --collect-only`'s own node-id strings with an exact equality test. The two consolidated rows' target cells initially carried the real node id followed by a parenthetical explanation of the consolidation (e.g. `"...::test_x (identical, pre-existing coverage...)"`), which the exact-match check correctly rejected as "not found in `pytest --collect-only` output".
- **Fix:** Trimmed both target cells to the bare node id; the consolidation rationale moved into the fragment's `### Part 04` prose note below the table, where every other part's own consolidation/deletion reasoning already lives.
- **Files modified:** `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md`
- **Verification:** `33-ledger-check.py companion/test_view_pages.py` (without `--allow-pending`) now exits 0: 169/169, 0 pending.
- **Committed in:** `9b88ac1` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 missing-critical-functionality/TST-13, 1 blocking)
**Impact on plan:** Both narrow, caught by this plan's own verification steps before the affected commit landed — no scope creep, no file touched beyond this plan's own `files_modified` list.

## Issues Encountered

One transient failure on the first full-suite `pytest -n auto` run: `companion/test_app_server_fixture.py::test_stop_kills_the_whole_process_group_including_a_grandchild` failed under `-n auto` parallel load. That test is owned by 33-02 (`companion/test_app_server_fixture.py` is not in this plan's `files_modified` list and was never touched), asserts a process-group-kill race (a grandchild process's death is polled immediately after `stop()` returns), and passed both standalone and on an immediate full clean re-run (1862 passed, 5 skipped, 0 failed) — a pre-existing timing flake under heavy parallel CPU contention, not a regression introduced by this plan's changes, and out of this plan's scope per the Scope Boundary rule.

## User Setup Required

None.

## Next Phase Readiness

- The view-pages migration chain (33-05 through this plan) is CLOSED: `companion/test_view_pages.py` no longer exists, all 169 of its baseline checks are accounted for (167 ported to new node ids across `companion/test_view_pages_01.py`..`_04.py`, 2 consolidated into `companion/test_companion_app_03.py`'s pre-existing coverage), and its ledger fragment reports 0 pending.
- This was the last harness-migration plan whose own summary was still pending in the phase; the closing plans (33-32 guard tightening, 33-33 closing parity/verification) can now treat the view-pages chain as fully done when computing the phase-wide 2018-check parity total.
- No blockers. The full suite (`pytest -n auto companion test-support server stub-server deploy`, `SKYPANE_REQUIRE_BROWSER=1`) is green at 1862 passed / 5 skipped / 0 failed, and `ruff check .` is clean across the whole tree.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

`companion/test_view_pages_04.py` and the ledger fragment found on disk;
`companion/test_view_pages.py` confirmed deleted; this summary found on
disk; all three commit hashes (`978180f`, `93290bc`, `9b88ac1`) found in
`git log --oneline --all`.
