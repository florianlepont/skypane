---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 15
subsystem: testing
tags: [pytest, companion-app, nav, theme-preview, drawing-contract, css-structural-parsing, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "14"
    provides: "companion/test_companion_app_helpers.py's shared test doubles, companion/test_companion_app_01.py's part-01 module and conventions, and the shrunk companion/test_companion_app.py (EXPECTED_CHECK_COUNT=268) this plan continues shrinking"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/module_app_server_factory fixtures and test-support/companion_app_server.py's http_request/served_stylesheet/served_asset — this plan's Section 3 route checks and JS/CSS reads use them instead of the legacy Harness"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for() (the nav/drawing-contract CSS checks) and companion/test_suite_guards.py's TST-10/12/13/14 guard, which now scans this plan's new module"
provides:
  - "companion/test_companion_app_02.py: 70 native pytest tests porting companion/test_companion_app.py's original check() calls across ledger rows 51-122 — the rest of layout.py's nav contract (hamburger dropdown, bottom tab bar, three-file DOM-contract guard), parse_single_uploaded_file()'s multipart parser, env_wake_interval_default()/page_context()'s D-07 threading, the whole of companion/theme_preview.py, _illustration_filenames()'s per-request union, the FLASH_KEY_MANUAL_* deck, the CFG-39/CFG-40 drawing contract (companion/draw.py, the ring gauge), and Section 3's D-02 whole-site auth-gate routes plus the public static-asset routes and two JS ES5 contracts"
  - "companion/test_companion_app_helpers.py gains encode_multipart() (shared with later parts of this chain)"
  - "companion/test_companion_app.py shrunk: EXPECTED_CHECK_COUNT 268 -> 196; part 02's checks and their private closures removed from main(); the main()-level `import companion.app as app_module` and the _unauth_redirects_to_login()/_static_script_public() closure factories kept, since 33-16..33-18's still-legacy checks call them by name"
  - "the companion_app ledger fragment's rows 51-122 flipped (71 ported, 1 deleted), Part 02 note added"
affects: [33-16, 33-17, 33-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A module-scoped app02_server fixture (module_app_server_factory(fake_providers=True)) is shared by every check in the module that needs real HTTP or the served stylesheet/JS assets — none of them mutate server state, matching 33-MIGRATION-RULES.md section 2's read-only-GET guidance; the same fixture backs both the early nav/CSS checks and the late Section 3 auth-gate/static-route checks"
    - "A check that scans production Python source for a structural no-duplication/no-import property (no direct observable HTTP/DOM consequence) is handled per rubric S three different ways depending on what actually covers it: deleted outright when a sibling behaviour test already proves the real failure mode (the battery-constants-exactly-one-home check, superseded by the existing battery-parity test); rewritten as a subprocess import + sys.modules assertion when the check's own subject is exactly \"does importing X pull in Y\" (companion/draw.py's import-graph check); or ported narrowed to a single module's own emitter output, consolidating two old checks into one new test, when the full original scope (every companion/pages/*.py module too) would require calling every page module's render function with fabricated context for no proportionate benefit (the no-colour-literal / every-shape-has-a-fill-route pair, now scoped to companion/draw.py's own samples)"
    - "Shared plumbing that sits textually inside a plan's own check-call range but is called by name from OTHER, still-legacy checks further down main() is identified before shrinking (not assumed absent) by running ruff on the shrunk file and reading every resulting F821 undefined-name error back to its origin — this caught a main()-level `import companion.app as app_module` and two closure factories (_unauth_redirects_to_login, _static_script_public) that 33-16..33-18's own slices still depend on, which were restored verbatim rather than left broken"

key-files:
  created:
    - companion/test_companion_app_02.py
  modified:
    - companion/test_companion_app_helpers.py
    - companion/test_companion_app.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md

key-decisions:
  - "RESEARCH assumption A3 resolved: _resolve_flash_text() never creates a directory for a missing state_dir. Reading companion/app.py's source directly, the function only ever reads state_dir (via poll_cooldown_remaining()'s history_db.open_db() and calendar_rules.load_calendar_registry()), and only for two OTHER flash keys (FLASH_KEY_POLL_COOLDOWN and FLASH_KEY_CALENDAR_CONNECTED/FLASH_KEY_CALENDAR_CONNECT_OK) that the six FLASH_KEY_MANUAL_* deck keys and an unknown key never reach — the per-key branch returns before either is called. test_flash_manual_keys_complete_and_byte_identical proves this by measurement: a tmp_path absent subpath is asserted to still not exist after every _resolve_flash_text() call in the test, not merely by re-reading the source a second time."
  - "_battery_estimate_has_exactly_one_home is deleted (rubric S), not ported: it scanned every companion/server *.py file's tokens (via tokenize, banned by guard G2) for a duplicate battery-constant/function definition — a structural anti-duplication guard whose real failure mode (two homes disagreeing about a percentage for the same reading) is already fully covered behaviourally by test_battery_estimate_parity_between_companion_and_server, ported unchanged in this same plan."
  - "_no_colour_literal_in_emitted_markup and _every_drawn_shape_has_a_fill_route are consolidated into one new test, test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route, narrowed to companion/draw.py's own sample emitters rather than also scanning every companion/pages/*.py module's string literals via tokenize (G2-banned). This is a deliberate scope reduction: the shared geometry layer (companion/draw.py) is what every page module actually calls into, so its own emitter output is the most representative subset, but a page module that hand-wrote its own unstyled SVG shape outside of draw.py's helpers would no longer be caught by this test."
  - "_draw_module_imports_no_page_and_no_server is rewritten per 33-MIGRATION-RULES.md's own prescribed rubric-S technique for import-only checks: a subprocess imports companion.draw fresh (cwd=REPO_ROOT, child_env()) and asserts the banned module names are absent from sys.modules, instead of ast.parse()-ing the file (G2-banned)."
  - "page_context()'s original cross-reference against companion/pages/__init__.py's docstring text (verifying every ctx key is documented) is dropped from test_page_context_supplies_resolve_prefix_and_manual_resolutions — guard G4 bans reading a module's __doc__ at all. The check's own actual subject (resolve_prefix/manual_resolutions correctly present and populated in ctx) is unaffected; a handful of the wider always-present ctx keys are still spot-checked for presence without the docstring comparison."
  - "encode_multipart() (the legacy harness's own _encode_multipart(), used by several still-legacy checks later in companion/test_companion_app.py too) moves into companion/test_companion_app_helpers.py, renamed without its leading underscore, following 33-14's precedent for shared chain plumbing. The ORIGINAL definition stays in the legacy file (it is still called by name from checks outside this plan's slice)."
  - "The main()-level `import companion.app as app_module` and the _unauth_redirects_to_login()/_static_script_public() closure factories, though textually inside this plan's own check-call range, are restored verbatim after the shrink because several still-legacy checks further down main() (33-16..33-18's own slices) call them directly by name — they are shared plumbing, not closures only this plan's checks used, per 33-MIGRATION-RULES.md section 1's own distinction. Caught by running ruff on the shrunk file and tracing every F821 undefined-name error back to its origin before committing."

requirements-completed: []

# Metrics
duration: ~2h10min
completed: 2026-09-24
---

# Phase 33 Plan 15: Companion-App Part 02 — Nav, Theme Preview, Drawing Contract, Auth-Gate Routes Summary

**Migrated 72 more companion_app checks (ledger rows 51-122) to native pytest — the rest of layout.py's nav/tab-bar contract, the whole companion/theme_preview.py module, the CFG-39/CFG-40 drawing contract, and Section 3's whole-site auth gate plus public static-asset routes — resolving RESEARCH A3 (`_resolve_flash_text()` never creates directories) and replacing a tokenize-based source scan with a real behaviour test.**

## Performance

- **Duration:** ~2h10min (commit-to-commit)
- **Started:** 2026-09-24T12:20:00Z (approx, first commit)
- **Completed:** 2026-09-24T14:33:00Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `companion/test_companion_app_02.py`: 70 native pytest tests covering 72 of the original harness's ledger rows (two consolidated into one, several parametrized) — the hamburger dropdown/bottom tab bar contract (nav-dropdown.js and the served stylesheet fetched via `served_asset()`/`served_stylesheet()` instead of disk reads), `parse_single_uploaded_file()`'s multipart parser, `env_wake_interval_default()`/`page_context()`'s D-07 wake-interval threading, all 14 checks of `companion/theme_preview.py` (tempfile.TemporaryDirectory() replaced by `tmp_path` throughout), `_illustration_filenames()`'s per-request union, the FLASH_KEY_MANUAL_* deck (RESEARCH A3 resolved and proven by measurement), the CFG-39/CFG-40 drawing contract over `companion/draw.py` and the ring gauge, and Section 3's D-02 whole-site auth-gate routes plus the public static-asset routes and two JS ES5 contracts (`copy-button.js`/`dirty-state.js`), all driven against a real `companion/app.py` subprocess via `companion_app_server.http_request()`/`served_asset()`.
- Three checks that scanned production `.py` source as text (one via `tokenize`, banned by guard G2) are resolved per rubric S rather than ported as-is: `_battery_estimate_has_exactly_one_home` is **deleted** (its real failure mode is already covered by the parity test this plan also ports); `_no_colour_literal_in_emitted_markup`/`_every_drawn_shape_has_a_fill_route` are **consolidated and narrowed** into one behaviour test over `companion/draw.py`'s own emitter output; `_draw_module_imports_no_page_and_no_server` is **rewritten** as a subprocess-import + `sys.modules` check per the migration rules' own prescribed technique.
- `companion/test_companion_app.py` shrunk: `EXPECTED_CHECK_COUNT` 268 → 196; part 02's checks and their private closures removed from `main()`. A main()-level `import companion.app as app_module` and two closure factories (`_unauth_redirects_to_login`, `_static_script_public`) that sat textually inside this plan's slice but are called by name from several still-legacy checks further down `main()` were identified (via ruff's F821 output on the shrunk file) and restored. The shrunk harness runs 196/196 standalone and through `companion/test_legacy_harness_shim.py -k companion_app`.
- The ledger fragment's rows 51-122 flipped (71 `ported`, 1 `deleted`); a `### Part 02 (plan 33-15)` note added recording the rubric-code split, the A3 finding, and the consolidation/narrowing decisions. `33-ledger-check.py --allow-pending` confirms 320/320 baseline checks accounted for (123 ported total, 1 deleted, 196 pending).
- Full-suite verification beyond the plan's own scoped checks: `pytest -n auto companion test-support server stub-server` as root (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **1277 passed, 5 skipped, 0 failed** (up from 33-14's 1034 passed/1 failed/5 skipped baseline; the one pre-existing `test_status_pages` root-sandbox failure from earlier plans is fixed on `main` since then, outside this plan's own scope).

## Task Commits

1. **Task 1: First half of part 02 (nav/tab-bar/parser/theme_preview/flash-deck)** - `7cbfbc4` (test)
2. **Task 2: Second half of part 02 (drawing contract, auth-gate routes, JS)** - `047f830` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `a15287e` (test)

## Files Created/Modified

- `companion/test_companion_app_02.py` - 70 native pytest tests, part 02 of the companion_app migration chain
- `companion/test_companion_app_helpers.py` - gains `encode_multipart()` (shared with 33-16..33-18)
- `companion/test_companion_app.py` - shrunk to `EXPECTED_CHECK_COUNT = 196`; shared main()-level plumbing (`app_module` import, two closure factories) restored after the shrink
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md` - rows 51-122 flipped, Part 02 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the A3 research finding (no directory creation), the battery-constants deletion, the colour-literal/fill-route consolidation and narrowing, the draw-module-imports subprocess rewrite, dropping the `__doc__`-reading half of the page_context resolve-prefix check (G4), `encode_multipart()`'s move to the shared helpers module, and restoring the shared main()-level plumbing (`app_module` import, `_unauth_redirects_to_login`/`_static_script_public`) that several still-legacy checks further down `main()` still depend on.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored shared main()-level plumbing the shrink had deleted out from under still-legacy checks**
- **Found during:** Task 3, running `ruff check` on the shrunk `companion/test_companion_app.py`
- **Issue:** The plan's own slice boundaries (FIRST/LAST anchor labels) correctly delimited which `check()` *calls* to migrate, but three pieces of plumbing textually sitting inside that same range — a main()-level `import companion.app as app_module`, and the `_unauth_redirects_to_login()`/`_static_script_public()` closure factories — are called BY NAME from several still-legacy checks further down `main()` (the `/quick/led`, `/quick/display` auth-gate checks and the `theme-preview.js`/`flight-rows.js`/`relative-time.js`/`quick-switch.js`/`value-controls.js`/`login-card.js` static-route checks, all owned by 33-16..33-18). Deleting them along with this plan's own migrated calls left the shrunk file with 26 ruff F821 (undefined name) errors.
- **Fix:** Restored the import and both closure factories verbatim, immediately after `base = harness.base_url()`, with a comment explaining why they survive the shrink. Re-ran ruff (clean) and the full shim (196/196, then the full suite) to confirm nothing else was missing.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `ruff check companion/test_companion_app.py` clean; `python3 companion/test_companion_app.py` standalone (196/196); full suite green (1277 passed, 5 skipped, 0 failed)
- **Committed in:** `a15287e` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to keep the suite green for 33-16..33-18, which still depend on this shared plumbing. No scope creep — no other file was touched for this fix, and the restored code is byte-identical to the original.

## Known Stubs

None.

## Threat Flags

None — the new module's HTTP surface (real `companion/app.py` route checks) mirrors exactly what `test-support/companion_app_server.py`'s existing fixtures already exercise; no new endpoint, auth path, or schema is introduced.

## Issues Encountered

Beyond the deviation above, none. The loop-generated Section 3 checks (the six-tab, two-legacy-route and four-static-script loops) turned out to expand the ledger's own row range to 72 rows rather than the plan's stated "63 calls" — the plan's parenthetical counts syntactic `check(...)` call *sites*, while the ledger (and `EXPECTED_CHECK_COUNT`) counts actual runtime check *results*, which is 9 higher because three of those call sites each execute inside a `for` loop. The plan's FIRST/LAST anchor labels (rather than the count) are what 33-MIGRATION-RULES.md makes authoritative for slice boundaries, and both anchors were followed exactly, so this is a documentation note rather than a deviation from the plan's own intent.

## User Setup Required

None.

## Next Phase Readiness

- 33-16 (part 03) continues from ledger row 123 (`dirty-state.js animates the restored bar's own count element...`), immediately after this plan's LAST anchor.
- The shared main()-level plumbing 33-16..33-18 still need (`app_module` import, `_unauth_redirects_to_login`, `_static_script_public`) is confirmed present and correct in the shrunk file.
- `companion/test_companion_app_helpers.py`'s `encode_multipart()` is available for any later part's own multipart-upload checks.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_companion_app_02.py`,
`companion/test_companion_app_helpers.py`, `companion/test_companion_app.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md`)
plus this summary, and all 3 commit hashes (`7cbfbc4`, `047f830`, `a15287e`) found in
`git log --oneline --all`.
