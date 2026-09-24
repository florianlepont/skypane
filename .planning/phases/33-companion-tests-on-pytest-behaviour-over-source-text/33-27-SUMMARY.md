---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 27
subsystem: testing
tags: [pytest, css-parsing, html-parsing, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's rows 86-139 build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture (reused here, following 33-26's precedent, for the served-CSS/JS checks)"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/css_rules()/declarations_for()/rules_with_selector()/custom_properties() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "26"
    provides: "companion/test_status_pages_helpers.py's seeding/formatting wrappers, the _module_server/css_text/battery_trend_js fixture pattern this plan reuses verbatim, and the module-split naming convention (test_status_pages_NN.py)"
provides:
  - "companion/test_status_pages_03.py: 57 native pytest node ids porting the original harness's check() calls #86-#139 (part 03 of the 7-plan chain) — compute_health_state()'s never-ran-pipeline detail fragment, the D-05/A-23 overall_severity()/collect_anomalies() widened precedence table and device-cadence pinning, the anomaly-banner/source-fault/degrade-not-raise trio, Health's page-header/two-section/section-intro shape, the Server & data grid's tile-count/nesting invariants, the Resolution-rate tile and B3's 'count every row, bucket the unknown as Other' fix, the registry card's filter bar/read-only note/Resolve-link pair, the battery-trend section's post-move heading/caption/readout contract, the card-status-border doubled-form/hover-source-order mechanism, the nested-card-heading-tier/label-voice CSS contracts (06.6.4.1.1 D-09/D-13), and the D-10 two-tier-hierarchy-carried-by-layout closing check"
  - "the plan's named S-rubric hotspot rewritten as a rendered/parsed behaviour test: test_health_still_has_no_form_and_no_button_in_any_state, parametrized over four seeded Health render states (normal, anomaly, source_fault, empty), proving zero <form> and zero <button> elements in every one via companion_markup.parse_html() — replacing a health_page.py source-text grep whose 'exactly one <button' was a docstring mention, never rendered markup"
  - "9 CSS checks in this slice rewritten fully structurally per 33-FOLLOWUPS.md F-01 (never regex/substring over served CSS text): css_rules()/declarations_for()/rules_with_selector()/custom_properties() against the served stylesheet, including a hover/status-border source-order check whose legacy form matched a header COMMENT's text rather than the real selector (parsing from served bytes fixes that latent fragility for free)"
  - "companion/test_status_pages.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 231 to 177; part 03's 54 checks and the closures only they used removed from main()"
  - "the status-pages ledger fragment's rows 86-139 flipped to ported (1 pointing at a parametrized test's primary node id, 3 siblings recorded below); 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for (140 ported, 177 pending)"
affects: [33-28, 33-29, 33-30, 33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every CSS check in this slice goes through companion_markup's structural API even where a prior plan (33-10/33-11, flagged in 33-FOLLOWUPS.md F-01) had precedent for substring/regex probes over served CSS text — declarations_for()'s returned dict is read with .get(prop), and a source-order fact (a status-modifier rule sitting after its component's own :hover rule) is proven by comparing each rule's INDEX in css_rules()'s ordered list, never by comparing string offsets in the raw text"
    - "A source-order comparison over already-structurally-extracted declaration VALUES (never raw stylesheet text) is still 'structural' under F-01: _margin_bottom_token_px() runs one regex against a single declarations_for() dict value to pull out a var(--token) name, then resolves that name via custom_properties(css_text, ':root') — the regex never scans the stylesheet itself, only a value companion_markup.py already parsed out"
    - "A legacy check that greps a page module's own source for a bare 'import X' line is rewritten as not hasattr(module, 'X') when there is no clean sys.modules proof available (here, the stdlib html module is already pulled in transitively by unrelated dependencies, making a subprocess sys.modules probe vacuously true regardless of health_page.py's own import) — a bare import binds the name directly into the importing module's own namespace, so hasattr() is an equally real behavioural proof, scoped to the one module the legacy check actually cared about"
  key-files:
    created:
      - companion/test_status_pages_03.py
    modified:
      - companion/test_status_pages.py
      - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "The plan's own named S-rubric hotspot (row 121, 'health_page.py still contains zero HTML form elements and exactly one <button literal') is rewritten as ported, not deleted: rendering Health in four seeded states and parsing each with companion_markup.parse_html() gives a real behavioural proof, and confirms the true rendered contract is stricter than the legacy check's own text-based one — the legacy check's 'exactly one <button' was counting a docstring mention inside health_page.py's SOURCE, not anything health_page.render() ever emits (verified directly: every one of the four states parses to zero <form> and zero <button>, since render() returns a content fragment only, with no shared nav chrome)"
  - "All 9 raw style.css disk reads in this slice are rewritten fully structurally via companion_markup, per the sequential-executor context's explicit F-01 instruction, rather than following 33-10/33-11's flagged substring-over-served-text precedent — including a card-status/hover source-order check whose ORIGINAL raw-text form (css_source.index('.stat-tile:hover')) actually matched a header COMMENT quoting that selector, not the real (and differently-shaped) '.stat-tile:not(.frame-strip):hover' rule; parsing rule order via css_rules() sidesteps that latent bug for free rather than reproducing it"
  - "Two per-case loops in this slice (_battery_heading_equals_template_times_window_in_both_languages's en/fr loop, _two_tier_hierarchy_carried_by_layout_not_type's seeded=False/True loop) are kept as single test functions with an internal loop, not converted to @pytest.mark.parametrize — following 33-25's own precedent (leaving some loops inside one function body when the plan does not explicitly instruct otherwise), since this plan's own Task 2 instruction named only the S-rubric rewrite, not a parametrize mandate"
  - "Every _mkstate()-style temp directory becomes a tmp_path subdirectory rather than tempfile.mkdtemp() (guard G6); two checks whose only seed call was poll_loop.save_poll_state() (which does not mkdir, unlike history_db.connect()'s auto-mkdir) needed an explicit os.makedirs() first — a small but real behavioural difference from the legacy tempfile.mkdtemp()-created directory that would otherwise raise FileNotFoundError"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 10min
completed: 2026-09-24
---

# Phase 33 Plan 27: Status-Pages Part 03 (Widened Severity Table, Two-Section Shape, Battery-Trend Post-Move Contract, Card-Status CSS) Summary

**Migrated the third of seven status-pages harness slices to native pytest: the D-05/A-23 severity/anomaly precedence table, Health's two-section page shape and Resolution-rate/registry-card contract, the battery-trend section's post-move heading/caption/readout details, and nine card-status/nested-heading/label-voice CSS contracts — 54 legacy checks becoming 57 pytest node ids in a new `companion/test_status_pages_03.py`, with the plan's own named hotspot (the "zero `<form>`/one `<button>`" check) rewritten from a source-text grep into a 4-state rendered/parsed behaviour test, and every CSS check in the slice going through `companion_markup`'s structural parser rather than any substring/regex probe over served text.**

## Performance

- **Duration:** ~10 min (commit-to-commit)
- **Started:** 2026-09-24T17:56:52Z (first commit)
- **Completed:** 2026-09-24T18:06:29Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `companion/test_status_pages_03.py`: 57 native pytest node ids covering all 54 of part 03's original `check()` calls — `compute_health_state()`'s never-ran-pipeline detail fragment (B2); the D-05/A-23 `overall_severity()`/`collect_anomalies()` widened 6-input precedence table and its device-cadence pinning (a device 400s stale at a 30s cadence is warn, the same device at 3600s cadence is ok); the anomaly-banner/source-fault/degrade-not-raise trio (an unreadable database still renders the health-unavailable copy without raising); Health's page-header/two-id-anchored-section/section-intro shape (D-10); the Server & data grid's tile-count/nesting invariants (one tile in Screen's grid, three in Server & data's, two migrated cards nested outside both); the Resolution-rate tile and B3's "count every row, bucket the unknown as Other" fix, including the 36-row audit-reproduction fixture; the registry card's filter bar/read-only note/Resolve-link pair (desktop table + mobile card, hostile-prefix escaping); the battery-trend section's post-move heading/caption/readout contract (the heading carries only its short fixed text, a sibling caption carries `_battery_trend_caption()`'s three branches, the readout precedes the chart and script tag); the card-status-border doubled-form/hover-source-order mechanism across `battery-trend-section`/`page-section`/`stat-tile`; the nested-card-heading-tier and unified-label-voice CSS contracts (06.6.4.1.1 D-09/D-13); and the closing D-10 two-tier-hierarchy-carried-by-layout check (spacing tokens strictly ordered: section-transition 48px > card-to-card 24px > heading-to-content 16px > section-intro rhythm 8px).
- The plan's own named hotspot, rewritten per TST-12 rubric S: `test_health_still_has_no_form_and_no_button_in_any_state`, parametrized over four seeded Health render states (`normal`, `anomaly`, `source_fault`, `empty`). Each state is rendered and parsed with `companion_markup.parse_html()`, asserting zero `<form>` and zero `<button>` elements — verified directly during implementation that all four states produce 0/0, since `health_page.render()` returns a content fragment only (no shared nav chrome that could introduce a legitimate button), so the legacy check's own "exactly one `<button>`" — a docstring mention inside `health_page.py`'s source — carried no real rendered exception at all.
- Nine CSS checks rewritten fully structurally against the served stylesheet (`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`/`custom_properties()`), per the sequential-executor context's explicit F-01 instruction: `.section-caption`'s single 70% muted declaration; `BATTERY_SECTION_CLASS`'s own rule existing at all; the doubled-form status-border declarations for `battery-trend-section`/`page-section` at ok/warn/error; the hover-vs-status-border SOURCE ORDER for all three card components (including `stat-tile`'s four modifiers) — whose legacy raw-text form actually matched a header COMMENT quoting `.stat-tile:hover`, not the real (and differently-shaped) `.stat-tile:not(.frame-strip):hover` rule, a latent fragility parsing from served bytes sidesteps for free; the `.section-intro`/`.stat-tile__value .mono`/`.battery-readout` declaration-plus-source-order guard; `.dashboard-grid`'s stretch-not-start alignment plus the file's one remaining `align-items: start` living in `.dashboard-shell`; `.data-table th`'s symmetric non-zero padding; the nested-card-heading-tier's sans-semibold promotion plus `.text-heading`'s own token-level 22px/regular contract; and `.stat-tile__caption`'s convergence on the unified 12px label voice. One raw JS read (`battery-trend.js`, rubric J) becomes a `served_asset()` fetch.
- One S-rubric source-text grep with no clean `sys.modules` proof available (the stdlib `html` module is already pulled in transitively by unrelated dependencies) is rewritten as `not hasattr(health_page, "html")` — a bare `import html` binds the name directly into the importing module's own namespace, so this is a real, scoped behavioural proof rather than a source-text read.
- `companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT` dropped from 231 to 177; part 03's 54 checks and their own closures removed from `main()`. The shrunk harness re-verified 177/177 green standalone with no orphaned references (module-scope helpers `_battery_section_heading()`/`_tile_slice_by_caption()`/`_stat_tile_slices()` are still called by still-pending sections well past this slice's boundary and were left in place).
- The ledger fragment's rows 86-139 flipped to `ported`: 43 B/D rows, 9 C rows (the CSS checks above), 1 J row (`battery-trend.js`), and 1 row pointing at a parametrized test's primary node id (`[normal]`) with its 3 sibling ids (`[anomaly]`, `[empty]`, `[source_fault]`) recorded in the ledger's own Part 03 note. `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (140 ported, 177 pending).
- Verification beyond the plan's own scoped checks: the shrunk legacy harness runs 177/177 green standalone and through `companion/test_legacy_harness_shim.py -k status_pages`; `companion/test_suite_guards.py test-support` (95 tests) stays green; `ruff check companion/test_status_pages*.py` clean; the FULL suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`) runs 1829 passed, 5 skipped, 0 failed (up from the pre-existing 1771/5/0 baseline, the gain matching this plan's net new pytest node ids).

## Task Commits

1. **Task 1: First half of part 03 (35 pytest nodes)** - `b275ba3` (test)
2. **Task 2: Second half of part 03, including the health_page form-count rewrite (22 more pytest nodes)** - `4e19fac` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `83d2eda` (test)

## Files Created/Modified

- `companion/test_status_pages_03.py` - 57 native pytest node ids porting part 03's 54 legacy checks
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 177`; part 03's checks removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 86-139 flipped, Part 03 note added

## Parametrized checks: primary node id and sibling ids

Per 33-MIGRATION-RULES.md section 3 ("one old check splits into several tests"), this ledger row points at ONE primary node id; the siblings below are the other node ids the same old check now covers:

- Row 121 (`test_health_still_has_no_form_and_no_button_in_any_state`): primary `[normal]`; siblings `[anomaly]`, `[empty]`, `[source_fault]`.

## Decisions Made

See `key-decisions` in the frontmatter above: the S-rubric hotspot is rewritten as `ported` (a real parsed-markup proof, stricter than the legacy text-based check, not a deletion); every CSS check in this slice is rewritten fully structurally per F-01, including one whose legacy raw-text form was matching a comment rather than the real selector; two per-case loops stay inline (33-25 precedent, no explicit parametrize instruction this plan); and two fixtures needed an explicit `os.makedirs()` since their only seed call (`poll_loop.save_poll_state()`) does not create the state directory the way `history_db.connect()` does.

## Deviations from Plan

None beyond the plan's own explicitly-named S-rubric rewrite (not a deviation — it was Task 2's instruction). No Rule 1-4 auto-fixes were needed: the two `os.makedirs()` additions above are direct consequences of moving from `tempfile.mkdtemp()` (which pre-creates the directory) to `tmp_path` subdirectories (which do not), caught immediately by the first `pytest` run and fixed before any commit — not a bug in production code, and not scope creep.

## Issues Encountered

None beyond the `os.makedirs()` fixture adjustment above, caught and fixed before the Task 1 commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-28..33-31 (the chain's remaining 4 plans) continue shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 177), starting from `_nested_card_heading_rhythm_end_to_end` and onward.
- The `_module_server`/`css_text`/`battery_trend_js` module-scoped read-only fixtures (33-26's pattern) are reused verbatim here with zero changes needed — any later part with more served-CSS/JS checks can keep using this exact shape.
- `_battery_section_heading()`/`_tile_slice_by_caption()`/`_stat_tile_slices()` remain module-scope in the legacy harness for still-pending sections; no later part's migration needs to re-discover or re-define them.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk
(`companion/test_status_pages_03.py`, `companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`,
this summary) and all 3 commit hashes (`b275ba3`, `4e19fac`, `83d2eda`)
found in `git log --oneline --all`.
