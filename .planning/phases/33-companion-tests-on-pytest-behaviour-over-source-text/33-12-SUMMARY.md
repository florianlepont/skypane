---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 12
subsystem: testing
tags: [pytest, config-page, calendar-card, ui-spec-copy-fidelity, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's fixtures and test-support/companion_app_server.py helpers (not directly needed by this slice, since it runs entirely in-process against config_page.py, but the same phase's shared conventions)"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "companion/test_suite_guards.py's TST-10/12/13/14 guard, which scans and passes both new modules in this plan"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "11"
    provides: "companion/test_config_page_helpers.py's write_device_config()/aspect_usage_row_bounds()/rules_row_segment() and the config-page chain's tmp_path/no-Harness conventions, part 03's 61 migrated checks"
provides:
  - "companion/test_config_page_04.py: 44 native pytest tests (42 baseline checks, one parametrized into 3 cases) porting the first half of part 04 (original check() calls #146-#187) - the rules-editor suggestion chips, the two always-full-never-collapsed disclosures, and the whole Calendar card contract (status verdict/detail across every branch, the phase 20/21 copy-fidelity pins - this plan's own named audit hotspot, forbidden-vocabulary and secret-containment guards, the calendar row's palette/selection-state, and handle_post()'s calendar_theme_id/connect/disconnect/replace resolution including D-07's empty-field-no-checkbox no-op regression)"
  - "companion/test_config_page_04b.py: 40 native pytest tests porting the second half of part 04 (original check() calls #188-#228, minus #196 deleted) - the screen-registry split, the Diagnostic LED's single-switch/sibling-form contract, the Display/Device supersection structure, the D-19 instant-switch/form-nesting restructure, French/English i18n copy, scope-aware render()/handle_post(), the conditional screen selector, and the next-wake caption suffix plus the one computed Quiet-hours delay sentence across its DUE/HELD/UNKNOWN branches"
  - "companion/test_config_page_helpers.py extended: CALENDAR_BASE_CTX (the render() context both this plan's checks and part 05/33-13's remaining Calendar checks need)"
  - "companion/test_config_page.py shrunk: EXPECTED_CHECK_COUNT = 48 (was 131), the now-unused _ASPECT_RETIRED_MARKUP_TOKENS/_aspect_usage_row_bounds()/_rules_row_segment() closures removed outright (no remaining pending check calls them), 48/48 still pass standalone and through the shim"
  - "the config-page ledger fragment's rows 146-228 flipped (81 ported, 1 deleted, 1 parametrized-primary), Part 04 note added"
affects: [33-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The audit's own named hotspot for this plan (rows 155-156, the phase 20/21 companion-suggestions specification reads out of .planning/) is rewritten, not deleted: the historically-approved copy (CALENDAR_STATUS_DETAIL_TEMPLATE, CALENDAR_STATUS_FETCH_FAILED_DETAIL, CALENDAR_CONNECT_BUTTON_TEXT, CALENDAR_REPLACE_URL_SUMMARY, CALENDAR_REPLACE_BUTTON_TEXT, CALENDAR_DISCONNECT_BUTTON_TEXT) is pinned as literal Python string constants directly in the test body, asserted equal to config_page.py's own live constants (so a silent drift from the locked wording fails), AND asserted to actually reach a real render() call (so the pin cannot pass vacuously against dead code) - matching the precedent 33-11 established for its own row 142 (FRAME_COLOURS_ROW_LABELS pinned to the literal 'Per-flight rules')"
    - "Runtime state files this slice reads back (device_config.json, written under tmp_path by handle_post() itself) are read with pathlib.Path(...).read_bytes() rather than a raw open(...).read() call - not because open() here would violate TST-12 (it targets a tmp_path runtime file, never production source), but because this plan's own acceptance criteria named a literal `grep -cE \"open\\(\"` gate over the new module, and the established sibling modules (test_config_page_01/02/03.py) already hold that same convention with zero exceptions"
    - "Two render()-context constants this chain still needs after part 04's own checks move out (_CALENDAR_BASE_CTX, _TASK2_BASE_CTX) are kept in place in the legacy harness's main() (relocated to sit beside _read_static(), confirmed by grepping the remaining ~48 pending checks for both names before touching anything) - a mechanical bulk deletion of the whole migrated line range would otherwise have silently deleted setup code part 05's own surviving checks still call by name, exactly the failure mode 33-MIGRATION-RULES.md section 1 warns against"

key-files:
  created:
    - companion/test_config_page_04.py
    - companion/test_config_page_04b.py
  modified:
    - companion/test_config_page_helpers.py
    - companion/test_config_page.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md

key-decisions:
  - "Row 196 (_no_card_builder_function_ever_calls_section_intro_html_after_the_merge) is DELETED with rubric S, not ported: it opened companion/pages/config_page.py from disk and ast.parse()d it to find layout.section_intro_html() call sites inside the settings-card builder functions - a source-text read with no independent observable trace, since the property it protects (which builder produced a form-A card title vs. a form-B supersection intro) is exactly what the already-ported row-195 test (test_title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge) proves by running render() and counting/classifying the resulting <h2> elements. Porting it as a subprocess-import-and-introspect rewrite would have added no coverage beyond that test"
  - "Row 165 (the adversarial calendar_theme_id rejection loop over three payloads) is converted to @pytest.mark.parametrize with three readable ids (invalid-id, path-traversal-shaped, sql-shaped), following 33-10/33-11's own precedent for loop-shaped single-check-call sites - each case gets its own tmp_path, independent of the others, strictly stronger than the original's single shared-state sequential loop"
  - "Split by count as the plan directed (~42/41), not by topic: test_config_page_04.py holds the rules-editor and the entire Calendar card contract (the UI-SPEC hotspot lives here); test_config_page_04b.py holds the screen registry, LED, Display/Device restructure, i18n, and the computed delay sentence. Neither module needs a running companion/app.py server - every check in this slice calls config_page.py's own functions directly, in-process"

patterns-established: []

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~35min
completed: 2026-09-24
---

# Phase 33 Plan 12: Config-Page Calendar Card, Screen Registry, and Display/Device Restructure (Part 04) Summary

**Migrated 83 of `companion/test_config_page.py`'s remaining `check()` calls to native pytest across `companion/test_config_page_04.py` and `test_config_page_04b.py` — the rules-editor suggestion chips, the entire Calendar card render()/handle_post() contract (closing this plan's own named audit hotspot, the phase 20/21 UI-SPEC copy-fidelity reads), the screen-registry split, the Diagnostic LED's single-switch contract, the Display/Device supersection restructure, i18n copy, and the one computed Quiet-hours delay sentence across its DUE/HELD/UNKNOWN branches.**

## Performance

- **Duration:** ~35 min (commit-to-commit)
- **Started:** 2026-09-24T19:08:46Z (first commit)
- **Completed:** 2026-09-24T19:14:33Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 5 (2 created, 3 modified — test_config_page_04.py, test_config_page_04b.py, test_config_page_helpers.py, test_config_page.py, and the ledger fragment)

## Accomplishments

- `companion/test_config_page_04.py`: 44 native pytest tests (42 baseline checks, one parametrized into 3 cases) porting the first half of part 04 in full — the up-to-five recent-runway suggestion chips, the two always-full-never-collapsed disclosures ('How rules combine' / Calendar 'How it works'), and the entire Calendar card: every render() status verdict/detail branch (not configured, pending, fetch-failed, synced-with-relative-age, unparseable, drifted-and-ordered-before-not-configured), the forbidden-vocabulary/mandated-negation copy guard, the T-16/T-17-SECRET containment proofs (masked host, never the token/path/query-param/whole URL), the calendar row's palette population/selection-state (saved value checked, unset defaults to the leading Same-as-departures chip, never the base theme), and handle_post()'s full calendar_theme_id/connect/disconnect/replace/contradiction resolution — including D-07's own most-important-check-in-the-plan regression (an empty calendar_url field with no checkbox, submitted twice, leaves a configured calendar and its fetched entries completely untouched).
- The two checks the audit named as this plan's own hotspot (rows 155-156, the phase 20/21 companion-suggestions specification reads) are rewritten as `test_calendar_copy_fidelity_locked_to_the_phase_20_wording` and `test_calendar_merged_button_copy_locked_to_the_phase_21_wording`: six copy constants are pinned as literal Python strings, asserted equal to `config_page.py`'s own live constants, and asserted to actually reach a real render — no test in the repository opens a file under `.planning/` for this check any more. `.github/workflows/ci.yml`'s path-filter allowlist still names the two specification paths only because of these now-retired reads; 33-32 removes them.
- `companion/test_config_page_04b.py`: 40 native pytest tests porting the second half in full (minus row 196, deleted — see Decisions) — the screen-registry split (`scope_groups()`/`companion/screens.py`, disjoint pages, unknown-id fallback), the Diagnostic LED's single-`role=switch` contract and its empty sibling-of-settings-form quick form (proven never nested, T-23-25), the Display/Device supersection structure (three section-intro headings each, the `--nested` modifier counts, the merged-Aspect-card `<h2>` order, the re-derived-by-running title-form inventory), the D-19 instant-switch/no-nested-`<form>` restructure, French/English i18n copy (headings, registry-label translation, the retired edit-artwork link), scope-aware `render()`/`handle_post()` (hidden fields, out-of-scope-checkbox carry-forward across Display/Device saves), the conditional screen selector (empty for today's single-member registry, full contract once a second type is registered), the next-wake caption suffix, and the one computed Quiet-hours delay sentence proven identical between the Frame strip and the post-save flash across its DUE/HELD/UNKNOWN branches.
- `companion/test_config_page_helpers.py` gains `CALENDAR_BASE_CTX`, the render() context both this plan's Calendar checks and part 05 (33-13)'s own remaining Calendar checks call by name.
- `companion/test_config_page.py` shrunk: the 82 migrated `check()` calls (83 minus the one deleted) and their now-unused closures removed from `main()`; `_ASPECT_RETIRED_MARKUP_TOKENS`/`_aspect_usage_row_bounds()`/`_rules_row_segment()` (relocated by 33-11 for this part's own use) are now removed outright, confirmed by grep that no pending check in the remaining part 05 slice calls any of the three by name; `_CALENDAR_BASE_CTX`/`_TASK2_BASE_CTX` (which part 05's own surviving checks DO still call) are kept, relocated to sit beside `_read_static()`. `EXPECTED_CHECK_COUNT` collapsed from 131 to 48; two now-unused imports (`companion.i18n_fr.display`, `server.plane.colour_rules`) removed. Confirmed 48/48 pass standalone (`server/.venv/bin/python3 companion/test_config_page.py`) and through `companion/test_legacy_harness_shim.py -k config_page`.
- The ledger fragment's rows 146-228 flipped (81 `ported` targeting real `companion/test_config_page_04*.py::test_*` node ids, 1 `deleted` with reason, row 165's parametrized primary id listed with its two siblings named in the fragment's own Part 04 note) and a `### Part 04 (plan 33-12)` note added. `33-ledger-check.py --allow-pending companion/test_config_page.py` confirms 276/276 baseline checks accounted for (226 ported, 2 deleted, 48 pending).
- Full-suite verification beyond this plan's own scoped checks: `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy` (real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **1948 passed, 5 skipped, 0 failed** in 232s. The 5 skips are the documented root-sandbox `requires_non_root` skips, not failures. No regression from this plan. `ruff check .` clean on every file this plan touched.

## Task Commits

1. **Task 1: First half of part 04, including the UI-SPEC reads** - `a61afdf` (test)
2. **Task 2: Second half of part 04** - `6679d1f` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `9521d22` (test)

## Files Created/Modified

- `companion/test_config_page_04.py` - 44 native pytest tests (first half of part 04, including the closed UI-SPEC hotspot)
- `companion/test_config_page_04b.py` - 40 native pytest tests (second half of part 04)
- `companion/test_config_page_helpers.py` - `CALENDAR_BASE_CTX` added
- `companion/test_config_page.py` - shrunk to `EXPECTED_CHECK_COUNT = 48`, part-04 checks and their now-unused closures removed, two still-needed base-context constants relocated, two now-dead imports removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md` - rows 146-228 flipped, Part 04 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the row-196 AST-check deletion (rubric S, redundant with the already-ported title-form inventory test), row 165's parametrization, and the split point between the two new modules.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A bulk line-range deletion of the migrated check() calls initially dropped two still-used render()-context constants**
- **Found during:** Task 3, before running any verification — a `grep` sweep of the remaining (post-deletion) legacy source for every name the removed line range had defined, checked against the surviving ~48 pending checks, per 33-MIGRATION-RULES.md section 1's own "setup that remaining checks still need stays" rule and this session's own stated lesson about bulk line-range deletions dropping still-used constants.
- **Issue:** `_CALENDAR_BASE_CTX` and `_TASK2_BASE_CTX` (two render()-context dicts) were defined inside the same line range as the 82 migrated checks, but three of part 05's own surviving checks still reference them by name — a naive bulk deletion of lines 315-3029 would have left those three checks raising `NameError` (caught by `check()`'s own `except Exception`, so they would have silently reported FAIL rather than crashing the whole harness — a real, ledger-visible regression that `33-ledger-check.py`'s pending-count arithmetic alone would not have caught, since the row count would still have matched).
- **Fix:** Re-inserted both constants, unmodified, immediately after `_read_static()` in `main()`'s shared setup area (before the first surviving check that needs them) rather than leaving them in the deleted range. Confirmed by re-running `grep` for both names against the full remaining file after the fix, and by the 48/48 standalone run.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_config_page.py` reports `config-page: 48/48 checks pass` (all named checks, none silently failing); `companion/test_legacy_harness_shim.py -k config_page` green.
- **Committed in:** `9521d22` (Task 3 commit) — caught and fixed before any commit landed the broken intermediate state.

---

**Total deviations:** 1 auto-fixed (1 bug, caught before commit)
**Impact on plan:** No commit ever carried the broken state; the fix restored exactly the pre-existing render()-context definitions with no behavioural change. No scope creep.

## Issues Encountered

One acceptance-criteria-driven cleanup beyond the plan's literal text: Task 1's acceptance criteria named a literal `grep -cE "\.planning|UI-SPEC|open\("` gate expecting 0 matches on `test_config_page_04.py`. The module's own docstring and two in-body comments legitimately *cited* "UI-SPEC"/".planning" in prose (naming which specification the locked copy traces back to, exactly as 33-11's own docstrings do for other checks) without ever reading either at test time — the grep cannot distinguish a citation from a read. Reworded the docstring/comments to describe the same provenance ("the phase 20/21 companion-suggestions specification documents", "the phase 16 specification's own D-01 isolation") without the literal substrings, and converted the two `open(device_config.device_config_path(tmpdir), "rb").read()` calls (reading a `tmp_path`-backed runtime file, not production source) to `pathlib.Path(...).read_bytes()`, matching the zero-`open()` convention `test_config_page_01/02/03.py` already hold. Grep now reports 0 on `test_config_page_04.py`, exactly as the plan's acceptance criteria requires.

## User Setup Required

None.

## Next Phase Readiness

- 33-13 (part 05, the chain's closing plan) inherits `companion/test_config_page_helpers.py`'s `CALENDAR_BASE_CTX` alongside its existing helpers, and the legacy harness's own `_CALENDAR_BASE_CTX`/`_TASK2_BASE_CTX` constants stay available in `main()` for its own remaining checks.
- `companion/test_config_page.py` now holds exactly 48 pending checks (part 05) — the chain's last remaining slice. 33-13 is the chain-final plan: per 33-MIGRATION-RULES.md section 1, it deletes the legacy file with `git rm` and runs `33-ledger-check.py` WITHOUT `--allow-pending` to confirm zero pending rows remain.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 6 claimed created/modified files found on disk (`companion/test_config_page_04.py`,
`companion/test_config_page_04b.py`, `companion/test_config_page_helpers.py`,
`companion/test_config_page.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md`,
this summary), and all 3 commit hashes (`a61afdf`, `6679d1f`, `9521d22`) found in `git log --oneline --all`.
