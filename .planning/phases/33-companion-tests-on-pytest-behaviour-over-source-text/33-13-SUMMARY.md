---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 13
subsystem: testing
tags: [pytest, config-page, migration, chain-closed, http-round-trip, structural-css, monkeypatch, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's make_app_server fixture and test-support/companion_app_server.py's http_request()/login()/get()/served_stylesheet()/served_asset() helpers, this plan's own HTTP round-trip checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "companion/test_suite_guards.py's TST-10/12/13/14 guard (G2's ast/tokenize ban is what forced this plan's two rubric-S rewrites) and test-support/companion_markup.py's css_rules()/declarations_for()"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "12"
    provides: "companion/test_config_page_helpers.py's CALENDAR_BASE_CTX and the config-page chain's tmp_path/no-Harness conventions, part 04's 83 migrated checks, EXPECTED_CHECK_COUNT = 48 (the exact slice this plan closes)"
provides:
  - "companion/test_config_page_05.py: 60 native pytest node ids (48 baseline checks plus one check split into two tests and three checks parametrized with explicit ids) porting part 05 in full - the retired delay-wording guard, the settings-pages editorial floor, seven live authenticated companion/app.py HTTP round trips (save confirmation, PRG redirect + flash cleanup, the empty-body led_enabled no-op, the theme_arriving raw-POST set/clear, the unauthenticated POST, the retired /config-led route, the runway-image route's session/path-traversal guards), the calendar secret never reaching the served HTTP bytes, the aria-describedby/labelledby contract, the Notifications group, the live theme preview, the Aspect card's swatch legend and Current badge, three structural CSS contracts over the served stylesheet, the wake-interval field's B17 layout, the Calendar status detail's singular form, the Display scope's freshness-line refresh loop, D18's two wake-interval gauges and the gated range/readout seam that steers them (one check served over HTTP with comments stripped, never opened from disk), and the closing structural proofs (one radio set per theme field, no duplicate id, the no-JS save floor unconditional on every render() call)"
  - "companion/test_config_page.py deleted outright (git rm) - the config-page migration chain (33-09 through this plan) is CLOSED: all 276 baseline checks are accounted for (274 ported to new node ids across companion/test_config_page_01.py..05.py, 2 deleted with a stated reason), 0 pending"
  - "the config-page ledger fragment's remaining 48 rows flipped to ported, a Part 05 closing note added, 33-ledger-check.py WITHOUT --allow-pending confirms 276/276, 0 pending"
  - "companion/test_companion_app.py's own still-legacy site-wide editorial-floor check repointed off the now-deleted legacy file (see Deviations) - the still-legacy harness stays green"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A check that walks companion/pages/config_page.py's own syntax tree with ast/tokenize (banned outright by guard G2) is rewritten as a monkeypatch proof rather than deleted, when the property it protects has a real behavioural consequence: 'the estimate is called QUALIFIED off companion.battery' becomes not hasattr(config_page, 'battery_life_estimate') (the same not-hasattr technique rubric S recommends for 'retired symbol gone') PLUS monkeypatch.setattr(battery, 'battery_life_estimate', fake) changing what wake_battery_observed_text() reports - which only holds if config_page reads the function off the qualified module object on every call rather than a name bound once at import time by an unqualified from-import"
    - "A second ast-over-source proof ('the no-JS save floor is unconditional') is dropped as a partial S-rubric deletion in favour of a WIDER render-level proof already available: calling render() across every scope AND every extra keyword shape it accepts (errors, submitted, neither) and counting the fallback attribute's occurrence on each is strictly more evidence than proving one particular return statement is unconditional, which says nothing about any other, unexercised code path"
    - "The retired whole-repo source-text scan for three retired delay wordings (originally walking every non-test .py file under companion/ and server/) is rewritten per the plan's own D-rubric guidance as a rendered-page absence check: render() is called for both scopes that can carry an apply-timing sentence, in both languages, and the three literal wordings are asserted absent from the OUTPUT rather than from any file's source"
    - "companion/static/style.css checks in this module use ONLY companion_markup.declarations_for()/css_rules() over the served stylesheet, never a regex/substring/index scan over served CSS text (33-FOLLOWUPS.md F-01's own named anti-pattern, which 33-10/33-11 both introduced as precedent and 33-32 will sweep) - this closing part introduces zero new instances of that anti-pattern"
    - "The one served-JS contract (the value-controls.js readout seam) uses companion/test_config_page_helpers.py's strip_js_line_and_block_comments() rather than companion_markup.strip_js_comments_and_strings(), because the check's own quoted-string-literal searches (document.addEventListener(\"pointerdown\"...) would otherwise be erased by the stricter stripper that also removes string/template literals"
    - "A legacy harness's own cross-file check that pins two implementations of the same helper equal via ast.get_source_segment()-extract-and-exec (rather than import, because the source copy lives inside a legacy main() and is not importable) is a real, functional dependency on a specific file path and function name - deleting the file that check reads from is a genuine breaking change the plan's own pre-flight grep (which only looked for import statements) did not catch, only the full-suite run did"

key-files:
  created:
    - companion/test_config_page_05.py
  modified:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md
    - companion/test_companion_app.py
  # companion/test_config_page.py: deleted (git rm)

key-decisions:
  - "Row 271's own trailing clause (the error block still attaches to the field, with the gauges after it) is split into a SEPARATE test, test_the_gauges_error_block_still_attaches_with_the_gauges_after_it, rather than a seventh parametrize case in the six-shape table, because it exercises a materially different fixture shape (an errors dict, not a current/submitted pair) - 33-MIGRATION-RULES.md section 3's 'one old check may split into several node ids' rule; the ledger row points at the six-shape table's primary id (saved-in-band) and this SUMMARY names the split-off test"
  - "Rows 239, 241 and 243 (three loop-shaped single-check-call sites: three adversarial runway-image paths, three hostile calendar URLs, three scopes' aria-reference resolution) are converted to @pytest.mark.parametrize with explicit ids, following 33-10/33-11/33-12's own established precedent - each row's target points at the primary (first) id"
  - "companion/test_companion_app.py's own still-legacy 29-06-PLAN.md Task 3 check, which pinned a duplicate _caption_word_count_text() equal to the legacy companion/test_config_page.py's copy via ast-extract-and-exec, is repointed at companion/test_config_page_05.py (the same function, same name, now at module level rather than nested inside a retired main()) rather than deleted or left broken - a Rule 3 blocking-issue auto-fix, caught only by the full-suite run, not by the plan's own pre-flight grep for import statements (which this reference pattern does not use)"

requirements-completed: [TST-10, TST-12, TST-13, TST-14, TST-15]

# Metrics
duration: ~14min (commit-to-commit; full-suite verification runs added ~7min more)
completed: 2026-09-24
---

# Phase 33 Plan 13: Config-Page Migration Chain Part 05 (Chain Closed) Summary

**Migrated the config-page chain's final 48 `check()` calls (the retired delay-wording guard, seven live HTTP round trips against a real `companion/app.py`, the Notifications group, the live theme preview, D18's two wake-interval gauges and their gated-range/readout-seam script contract, and the closing structural proofs) into `companion/test_config_page_05.py`'s 60 native pytest node ids, deleted the legacy `companion/test_config_page.py` outright, and closed its ledger fragment at 276/276 with 0 pending — the chain that started at 33-09 is now fully migrated.**

## Performance

- **Duration:** ~14 min (commit-to-commit); full-suite verification (run twice) added roughly 7 more minutes
- **Started:** 2026-09-24T21:42:04Z (first commit)
- **Completed:** 2026-09-24T21:55:48Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 1 deleted, 1 ledger fragment updated) plus 1 deviation fix

## Accomplishments

- `companion/test_config_page_05.py`: 60 pytest node ids porting the chain's final 48 baseline checks in full — the retired-delay-wording guard rewritten from a whole-repo source scan into a rendered-page absence check (D-rubric, per the plan's own explicit instruction) and the settings-pages editorial floor (CFG-79); seven live authenticated `companion/app.py` HTTP round trips using `companion/conftest.py`'s function-scoped `make_app_server` fixture (save confirmation naming D-07's own confirmation copy, the PRG-redirect + flash-cleanup-script pairing, the empty-body `led_enabled` no-op, the raw-POST `theme_arriving` set/clear round trip, the unauthenticated POST writing nothing, the retired `/config-led` route's 404, the runway-image route's session gate and three adversarial path-traversal 404s); the calendar secret never reaching the served HTTP bytes (a seeded `make_app_server`) and a hostile/unparseable stored URL rendering no masked line at all; the aria-describedby/labelledby contract (D-12/A-30) across all three scopes; the Notifications group's status row, checkboxes, no-lang-selector guard and `handle_post()` round trips (D-26/D-28); the live theme preview's exactly-one-figure contract, chip `data-preview-src` contract, and seeded-callsign/sample-flight caption fallback in both languages; the Aspect card's swatch legend (computed from the live registry, never a restated literal) and its server-rendered, translated "Current" badge; the rule-kind segmented control's T12 contract plus confirming `.frame-colours__panel-legend` retired outright (C1); the rules add-form's flex-row geometry (X6/C4); the wake-interval field's B17 label/unit/content-fit-width layout; the Calendar status detail's singular form in both languages; the Display scope's freshness-line refresh loop and its "the settings form is untouched by the swap" guard (D1/CFG-35); D18's two wake-interval gauges (the BOUND freshness sentence, the OBSERVED battery sentence with its three no-figure states, the value-attribute floor across six argument shapes); the gated, nameless wake-interval range (CFG-49/CFG-52) and its readout seam pinned against `value-controls.js`'s served (never disk-read) text; and the two closing structural proofs — exactly `len(THEME_IDS)` `theme` radios, and no duplicate id anywhere on the rendered Display page (CFG-85/CFG-68).
- Three CSS checks (rows 257, 258, 260) fetch the served stylesheet and assert structurally via `companion_markup.declarations_for()`/`css_rules()` — zero regex/substring/index scans over served CSS text anywhere in this new module, per 33-FOLLOWUPS.md F-01's own named anti-pattern (which 33-10/33-11 introduced as precedent and which 33-32 is tasked with sweeping everywhere else). The one served-JS contract (row 273, the `value-controls.js` readout seam) uses `companion/test_config_page_helpers.py`'s `strip_js_line_and_block_comments()` rather than `companion_markup.strip_js_comments_and_strings()`, since several of its assertions search for quoted string literals (`document.addEventListener("pointerdown"...`) that the stricter, string-erasing stripper would remove.
- Two checks (rows 267, 276) that used to `open()` `companion/pages/config_page.py` from disk and walk its syntax tree with `ast.parse()`/`tokenize` — banned outright by guard G2 — are rewritten as behaviour rather than deleted, since both properties have a real observable consequence: row 267 becomes `test_wake_battery_text_reads_the_estimate_through_the_qualified_battery_module`, combining a `not hasattr(config_page, "battery_life_estimate")` check (the same technique rubric S recommends for "retired symbol gone") with a `monkeypatch.setattr(battery, "battery_life_estimate", fake)` proof that `wake_battery_observed_text()`'s output changes to match — provable only if `config_page` reads the estimator off the qualified `companion.battery` module object on every call, never a name bound once by an unqualified import. Row 276 becomes `test_the_native_submit_is_emitted_unconditionally_on_every_render`, calling `render()` across every scope AND every extra keyword shape it accepts and asserting the fallback attribute appears exactly once on each — a WIDER behavioural net than the retired single-return-statement source proof, which said nothing about any other, unexercised code path.
- `companion/test_config_page.py` deleted outright (`git rm`): its `EXPECTED_CHECK_COUNT`/`check()`/`main()`, `Harness`, `http_request`, `_NoRedirectHandler` and every remaining helper leave the tree with it. `skypane_test_support.legacy_companion_harnesses()`'s disk-derived set and `companion/test_legacy_harness_shim.py`'s parametrize list both drop the file automatically — confirmed directly (`legacy_companion_harnesses()` now returns `('companion/test_companion_app.py', 'companion/test_status_pages.py', 'companion/test_browser_ux.py')`, `test_config_page` no longer among them).
- The ledger fragment's rows 229-276 flipped to `ported` (48 to new `companion/test_config_page_05.py::test_*` node ids), a `### Part 05 (plan 33-13) — chain closed` note added. `33-ledger-check.py companion/test_config_page.py` **WITHOUT** `--allow-pending` confirms **276/276 baseline checks mapped (274 ported, 2 deleted, 0 pending)**.
- Full-suite verification (run twice — the first run caught a real cross-file break, see Deviations, and a second clean run confirmed the fix): `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy` (real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **2176 passed, 5 skipped, 0 failed** in 194s on the clean run. The 5 skips are the documented root-sandbox `requires_non_root` skips, not failures. `ruff check .` clean across the whole tree. No new `DeprecationWarning`s from any file this plan touched.

## Task Commits

1. **Task 1: First half of part 05 (26 checks)** - `3e08908` (test)
2. **Task 2: Second half of part 05 (22 checks + 1 split-off test)** - `e0702fa` (test)
3. **Task 3: Delete the legacy harness, close the ledger, verify** - `c6cea08` (test)
4. **Deviation fix: repoint test_companion_app's cross-check off the deleted legacy file** - `37d5b91` (fix)

An unrelated upstream merge commit (`c77a8bf`, merging `origin/main`'s already-landed `01ab214` status-pages part-04 wave) sits between Task 3 and the deviation fix; it carries no changes of this plan's own.

## Files Created/Modified

- `companion/test_config_page_05.py` - 60 native pytest node ids (part 05, the chain's closing module)
- `companion/test_config_page.py` - deleted outright (`git rm`)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md` - rows 229-276 ported, Part 05 closing note added, 0 pending
- `companion/test_companion_app.py` - one still-legacy check's cross-file reference repointed from the deleted `test_config_page.py` to `test_config_page_05.py` (see Deviations)

## Decisions Made

See `key-decisions` in the frontmatter above: the split-off gauges-error-block test (row 271), the three parametrized loop-shaped checks (rows 239/241/243), and the `test_companion_app.py` repoint (a Rule 3 blocking-issue fix, not a scope-creep edit).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deleting the legacy harness broke a DIFFERENT still-legacy harness's own cross-file check**
- **Found during:** Task 3's own required full-suite verification run (not caught by the plan's own pre-flight grep, `grep -rn "companion.test_config_page import\|test_config_page as" companion test-support`, which returned zero matches and gave false confidence)
- **Issue:** `companion/test_companion_app.py` — a wholly different, still-legacy harness this plan's `files_modified` list never named — carries its own 29-06-PLAN.md Task 3 check (`_site_wide_editorial_floor_all_six_routes_both_languages`) that pins a duplicate `_caption_word_count_text()` implementation equal to `companion/test_config_page.py`'s own copy, by opening that file from disk, extracting the function's source via `ast.get_source_segment()`, and `exec()`ing it in isolation (the original copy lived inside `main()` and was never importable). This reference pattern is neither an `import` statement nor a string the pre-flight grep's two literal patterns would match, so Task 3's own confirmation step reported clean while a real break sat one full-suite run away. Deleting `companion/test_config_page.py` in this plan's Task 3 turned the `open()` call into a `FileNotFoundError`, surfacing as `companion/test_legacy_harness_shim.py::test_legacy_companion_harness_exits_zero[test_companion_app]` failing (`companion-app: 51/52 checks pass`) on the first full-suite run.
- **Fix:** Repointed the extraction at `companion/test_config_page_05.py`, which carries the identical function under the identical name — now at module level (a plain top-level `def`, no longer nested inside a retired `main()`) rather than requiring the ast-extract-and-exec workaround for importability reasons, though this fix keeps that exact same technique (not a direct `import`) since `test_companion_app.py` runs as a standalone script outside pytest's own `sys.path` setup, where `test_config_page_05.py`'s own imports (`companion_app_server`, from `test-support/`) are not resolvable.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `pytest companion/test_legacy_harness_shim.py -k test_companion_app` passes (1 passed); a full clean re-run of the entire suite confirms **2176 passed, 5 skipped, 0 failed** with no other regression.
- **Committed in:** `37d5b91` (separate commit, after Task 3's own commit — the break was discovered by Task 3's own verification step, but fixing a file outside this plan's stated scope warranted its own commit rather than amending Task 3's).

---

**Total deviations:** 1 auto-fixed (1 blocking, caught by the mandatory full-suite run before the plan's own completion, not waved off)
**Impact on plan:** The fix is minimal (repoint two string literals and a docstring comment) and touches no behaviour this plan's own migrated tests exercise. No commit ever carried the broken state as this plan's *own* final state — the full-suite verification step is exactly what this session's instructions required it to be for, and it worked.

## Issues Encountered

One transient false start unrelated to this plan's correctness: the first attempt to run the mandatory full-suite verification accidentally launched TWO concurrent `pytest -n auto` invocations against the same working tree (a stray backgrounded process from an earlier command whose foreground `timeout` wrapper had already returned control) before either could exclusively own the shared `-n auto` worker pool and companion `app.py` subprocess ports. The stray process was identified by PID and `SIGTERM`'d before it could corrupt the surviving run's results; the surviving run completed normally and its failure (the `test_companion_app` cross-check) was independently reproduced by a second, clean full-suite run after the fix — so the reported failure was real, not an artefact of the double-run.

## User Setup Required

None.

## Next Phase Readiness

- The config-page migration chain (33-09 through this plan) is CLOSED: `companion/test_config_page.py` no longer exists, all 276 of its baseline checks are accounted for (274 ported to new node ids across `companion/test_config_page_01.py`..`_05.py`, 2 deleted with a stated reason), and its ledger fragment reports 0 pending.
- `companion/test_config_page_helpers.py` is now shared, stable infrastructure for any future companion test module needing `write_device_config()`/`CALENDAR_BASE_CTX`/`strip_js_line_and_block_comments()` — no further plan in this chain will edit it, since the chain it served is closed.
- `companion/test_companion_app.py` (still legacy) now references `companion/test_config_page_05.py` by name in one of its own checks — whichever future plan migrates `test_companion_app.py` itself should be aware this cross-reference exists and needs its own repoint (or deletion, if the property it protects is by then covered another way) at that time.
- No blockers. The full suite (`pytest -n auto companion test-support server stub-server deploy`, `SKYPANE_REQUIRE_BROWSER=1`) is green at 2176 passed / 5 skipped / 0 failed, and `ruff check .` is clean across the whole tree.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

`companion/test_config_page_05.py`, the ledger fragment, `companion/test_companion_app.py`
and this summary all found on disk; `companion/test_config_page.py` confirmed deleted; all
four commit hashes (`3e08908`, `e0702fa`, `c6cea08`, `37d5b91`) found in `git log --oneline --all`.
