---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 24
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration, chain-closed]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "23"
    provides: "companion/test_browser_ux.py shrunk to EXPECTED_CHECK_COUNT=13 (rows 63-75), the module-scoped-server-for-read-only / function-scoped-server-for-mutating split precedent, and THEME_PREVIEW_SEL kept alive in the legacy file specifically for this plan's own remaining checks"
provides:
  - "companion/test_browser_ux_04.py: the browser_ux chain's final 13 baseline checks (rows 63-75) rewritten as 13 native pytest-playwright tests — the scripts-blocked accordion's operability/save floor, the Touch Targets measurement sweep over the palette/usage-row/rule-add controls, the no-JS floor's own save-to-disk proof after the .js-gate simplification, the restored dirty bar's settle contract, a server-side validation rejection's inline-error/echo/no-toast floor, the bar's own document-order section naming, a real Annuler click's restore-every-surface proof, the settings-card-title consistency probe (CFG-72), the single-submit-affordance audit (CFG-78), the runway radios' cross-tree form= regression check, and the artwork drop zone's own upload/equivalence/geometry family (CFG-51/D19)"
  - "companion/test_browser_ux.py deleted outright (git rm) — the browser_ux migration chain (33-21 through this plan) is CLOSED: all 75 baseline checks are accounted for (74 ported across companion/test_browser_ux_01.py..04.py, 1 deleted with a stated reason from 33-21, 0 pending)"
  - "the browser_ux migration ledger fragment's remaining 13 rows flipped to ported, a Part 04 closing note added, 33-ledger-check.py WITHOUT --allow-pending confirms 75/75"
  - "the whole browser suite (health_drawings, quiet_wake, browser_ux_01..04, browser_policy) measured under -n auto in a real Chromium: 128 passed, 0 skipped, 0 failed, 101.03s wall time against the 202s serial baseline"
affects: ["33-32"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A second, distinct seed function (_seed_with_needs_artwork_entry, layering manual_resolutions.add_entry() on top of seed_state_dir()) is used where a check's own precondition (a manual-resolution entry with no artwork yet) is not part of the module's default fixture — kept local to this module rather than added to companion/test_browser_ux_helpers.py, since only this module's own 3 artwork checks need it."
    - "The artwork drop-zone family splits its server-scoping by MUTATION, not by membership in one legacy block: the two checks that actually store a file (upload-and-serve, picked-vs-dropped equivalence) each get a fresh function-scoped make_app_server and their own tmp_path fixture files; the one check that only measures the zone at rest (never uploads) shares a second, dedicated module-scoped artwork_server fixture built from the same seed — avoiding the legacy harness's own sequential 'previous check restored the fixture' dependency, which cannot hold under xdist."
    - "Artwork fixture files (a real landscape PNG, a non-image file, an oversized noise PNG) are written fresh under each test's own tmp_path via a shared _write_artwork_fixtures(tmp_path) helper, never tempfile.mkdtemp() — the two uploading checks each get their own copies rather than sharing files across tests."
key-files:
  created:
    - companion/test_browser_ux_04.py
  modified:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md
  # companion/test_browser_ux.py: deleted (git rm)

key-decisions:
  - "None of the 13 checks were parametrized: each drives a single named interaction/procedure (an accordion open/save, a rejected-value floor, a bar settle, a cross-tree save) or an internal loop whose own final assertion compares values across iterations (both languages must read the identical dirty-bar wording; the drop zone must paint differently in both themes) — matching 33-23's own reasoning under 33-MIGRATION-RULES.md section 2."
  - "6 of the 13 checks (the palette Touch Targets sweep, the rejected-value floor, the bar's document-order section naming, the Annuler restore check, the settings-card-title probe, and the submit-shaped-control audit) share one module-scoped, read-only server, because none of them persists a setting: the two edit-then-discard checks (section naming, Annuler) never click Enregistrer, and the rejected-value check's own POST is server-side rejected and never reaches disk. The other 5 mutating checks (accordion save, no-JS tracked_runway floor, bar settle-and-hide save, runway cross-tree save, plus the two artwork uploads) each get their own function-scoped make_app_server."
  - "The artwork family needed a distinct seed (a needs-artwork manual resolution entry) that companion/test_browser_ux_helpers.py's seed_state_dir() never creates — added as a local _seed_with_needs_artwork_entry() wrapper in the new module rather than editing the shared helpers file (33-MIGRATION-RULES.md section 2 reserves that file for capabilities several PARTS of one harness share; this need is local to 3 checks in one part)."
  - "The two artwork checks that upload a file could not safely share the legacy harness's own single artwork_harness instance and its own manual 'previous check restored the fixture' discipline under xdist (33-MIGRATION-RULES.md section 2: no test may depend on another test having run first) — each got its own function-scoped server and its own tmp_path fixture files instead, at the cost of two extra AppServer subprocess starts, which the measured 101.03s full-suite wall time shows is not a real cost."

requirements-completed: []

# Metrics
duration: ~11min (commit-to-commit: this plan's own first commit 81b2665 at 00:44:34Z to its last task commit 9e8d794 at 00:55:12Z; investigation/authoring of the new module preceded the first commit and is not included in this figure)
completed: 2026-09-25
---

# Phase 33 Plan 24: Browser UX Part 04 (Chain Closed) Summary

**Migrated the browser_ux chain's final 13 `check()` calls (the scripts-blocked accordion's operability/save floor, the Touch Targets measurement sweep, the no-JS tracked_runway save floor, the restored dirty bar's settle contract, a validation-rejection floor, document-order section naming, a real Annuler restore proof, the settings-card-title consistency probe, the single-submit-affordance audit, the runway cross-tree save check, and the artwork drop zone's upload/equivalence/geometry family) into `companion/test_browser_ux_04.py`'s 13 native pytest-playwright tests, deleted the legacy `companion/test_browser_ux.py` outright, and closed its ledger fragment at 75/75 with 0 pending — the browser_ux migration chain that started at 33-21 is now fully migrated, and no browser check anywhere in the repository is monolithic.**

## Performance

- **Duration:** ~11 min (commit-to-commit across this plan's own 3 commits)
- **Started:** 2026-09-25T00:44:34Z (first commit)
- **Completed:** 2026-09-25T00:55:12Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 1 deleted, 1 ledger fragment updated)

## Accomplishments

- `companion/test_browser_ux_04.py`: 13 pytest node ids porting the chain's final 13 baseline checks in full — the scripts-blocked accordion's operability/save floor (all 4 usage rows present with full-registry-size radios even closed, a real click opening/closing the grouped `<details>` mutually-exclusive set, a palette selection made inside the just-opened row reaching disk); the Touch Targets measurement sweep (the open row's first/last `.palette-chip`, the row's own `<summary>`, the arrivals leading option, the nested rule-add `<summary>`, all measured — never declared — against the 44px floor, plus grid-overflow and swatch-distinctness checks, in both themes); the no-JS floor's own save-to-disk proof after the `.js`-gate simplification (`tracked_runway` operated natively, submitted, re-read from disk, restored, with the fallback submit asserted visible AFTER the save); the restored dirty bar's settle contract (field/bar/disk agreement through a real Enregistrer navigation, with disk explicitly asserted UNCHANGED while the bar is visible and unsaved); a server-side validation rejection's inline-error/echo/no-toast floor (`aria-describedby`-linked error, the rejected input echoed back, disk untouched, and the explicit negative that no `.quick-toast` appears on this path); the bar's own document-order section naming (both click orders proving `dirtySectionLabels()` walks the DOCUMENT, not the click sequence); a real Annuler click's restore-every-surface proof (theme radio, live preview `src`, and the quiet-hours dial's decoded arc/handle values all read back off the resulting DOM after 28-08's deferred repaint tick); the settings-card-title consistency probe (CFG-72, one combined `(font-size, font-weight, font-family)` set across both settings pages, both themes, with the Poll card's own reach proven specifically); the single-submit-affordance audit (CFG-78, every submit-shaped control's own `.form.id` resolved live in the browser, never a hand-maintained list); the runway radios' cross-tree `form="settings-form"` regression check (a real Enregistrer save through the cross-tree association, re-read off disk and off a reload); and the artwork drop zone's own family (an upload-and-serve check, a picked-vs-dropped byte-identity/floor-measurement check, and an at-rest geometry/paint check).
- 6 read-only checks share one module-scoped, read-only seeded `server` fixture; 5 checks that persist a real setting each get their own function-scoped `make_app_server`. The artwork family needed a SECOND, distinct seed (a `needs-artwork` manual resolution entry `seed_state_dir()` never creates): the two uploading checks each get a fresh function-scoped server plus their own `tmp_path` fixture files (never `tempfile.mkdtemp()`); the one at-rest measurement check shares a second dedicated module-scoped `artwork_server` fixture — deliberately NOT the legacy harness's own single shared `artwork_harness` instance with its manual "previous check restored the fixture" discipline, which cannot hold under xdist (33-MIGRATION-RULES.md section 2).
- `companion/test_browser_ux.py` deleted outright (`git rm`): its `EXPECTED_CHECK_COUNT`, `check()`/`main()`, `Harness` alias and every remaining helper leave the tree with it. Grepped the whole repo first (not only imports — `open(`/`ast`/`Path(`/string mentions across companion, test-support, conftest, the shim, and other tests): every remaining reference to the filename is prose in a comment/docstring (13 hits, listed in the ledger fragment's closing note) or the frozen `ORIGINAL_COMPANION_HARNESSES` history tuple in `test-support/skypane_test_support.py` — `legacy_companion_harnesses()` derives its answer from disk, so no hand-edited list needed updating and `companion/test_browser_ux.py` drops out of the legacy set and the shim's parametrize list automatically.
- The ledger fragment's rows 63-75 flipped to `ported` (13 baseline checks, 13 new node ids), a `### Part 04 (plan 33-24) — CHAIN CLOSED` note added with the rubric-code split (13 B/D-shaped ports, 0 deletions this part) and the pre-deletion grep results. `33-ledger-check.py companion/test_browser_ux.py` **WITHOUT** `--allow-pending` confirms **75/75 baseline checks mapped (74 ported, 1 deleted, 0 pending)**.
- Full browser suite (`health_drawings`, `quiet_wake`, `browser_ux_01` through `_04`, `browser_policy`), `SKYPANE_REQUIRE_BROWSER=1`, real Chromium (`PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`), `-n auto`: **128 passed, 0 skipped, 0 failed, 101.03s wall time** — against the 202s serial baseline this plan's own `must_haves` named, and well under it.
- Full-suite verification: `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy` — **2497 passed, 5 skipped, 0 failed** in 311.60s. The 5 skips are the pre-existing, unrelated `root ignores permission bits; needs a non-root euid` skips — none touch `test_browser_ux*`. `ruff check companion/test_browser_ux*.py` and `ruff check .`: clean. No new `DeprecationWarning`s from any file this plan wrote (the Pillow `getdata()` warnings in the full-suite output are pre-existing, from `server/test_panel_preview.py`/`server/test_render.py`, untouched by this plan).

## Task Commits

1. **Task 1/2: Port part 04 (checks #63-75) into a new module** - `81b2665` (test)
2. **Task 2: Delete the legacy harness, run the full browser set, record wall time** - `b46d6b1` (test)
3. **Task 3: Close the ledger fragment, run the guard/shim/ruff verification, commit** - `9e8d794` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `companion/test_browser_ux_04.py` - new module, 13 pytest-playwright test functions (13 collected node ids, none parametrized)
- `companion/test_browser_ux.py` - deleted outright (`git rm`)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md` - rows 63-75 flipped (13 ported, 0 deleted), `### Part 04 (plan 33-24) — CHAIN CLOSED` note added

## Decisions Made

See `key-decisions` in the frontmatter: why none of the 13 checks were parametrized; the exact 6/5/2 server-scoping split and why (mutation, not slice membership, is the criterion); why the artwork family needed a second, module-local seed rather than a shared-helpers addition; and why the two uploading artwork checks each get a fresh function-scoped server and their own `tmp_path` files rather than reusing the legacy harness's own single shared instance.

## Deviations from Plan

None — the plan's own migration work was executed exactly as written. No production code was touched; no auto-fixes were needed. One mechanical departure from the legacy harness's own shape, anticipated by 33-MIGRATION-RULES.md section 2 itself: the three artwork checks' shared `artwork_harness`/manual-cleanup-between-checks discipline (which relies on tests running in a fixed, single-process order) was replaced with per-test isolation, since "no test may depend on another test having run first" is the rule under xdist and the legacy discipline violated it. This is a test-infrastructure adaptation, not a scope change — the same 3 behaviours are proven, each isolated in its own state.

## Issues Encountered

None. The 13-row slice (rows 63-75, the LAST anchor of the whole browser_ux chain) matched the plan's own anchor labels exactly, and every hand-off item 33-23-SUMMARY.md flagged for this plan (the shrunk legacy file's remaining 13 checks, `THEME_PREVIEW_SEL` kept alive in the legacy file specifically for this slice, the module-scoped/function-scoped server-split precedent) was present and correct at this plan's start. The sandbox's `/opt/pw-browsers` Chromium build was stale for this session (the documented pre-flight case) — resolved by exporting `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers` before any browser command, per 33-MIGRATION-RULES.md section 0's own prescribed fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The browser_ux migration chain (33-21 through this plan) is CLOSED: `companion/test_browser_ux.py` no longer exists, all 75 of its baseline checks are accounted for (74 ported to new node ids across `companion/test_browser_ux_01.py`..`_04.py`, 1 deleted with a stated reason from 33-21), and its ledger fragment reports 0 pending.
- `companion_app_server.LegacyHarness` (the class `test_browser_ux.py` imported as `Harness`) now has exactly ONE remaining consumer in the whole repository: `companion/test_app_server_fixture.py::test_legacy_harness_still_matches_original_behaviour`, a meta-test whose own docstring states its purpose as keeping `LegacyHarness` compatible "while a still-legacy script harness" exists elsewhere. `companion/test_status_pages.py` — the one companion harness still legacy after this plan (`EXPECTED_CHECK_COUNT = 73`, per its own header) — uses its OWN local `Harness` class, never `LegacyHarness` (confirmed by grep: zero `LegacyHarness`/`companion_app_server` references in that file). **For 33-32 (the closing plan named in this plan's own frontmatter `affects`):** once `test_status_pages.py`'s own chain closes too, `LegacyHarness` and its one remaining meta-test consumer can both retire together.
- Both the scoped verification named in the plan and a full unscoped suite run (`companion test-support server stub-server deploy`, 2497 passed / 5 skipped / 0 failed) are green as of this plan's last commit. No blockers for 33-32 or the rest of the companion migration effort.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

`companion/test_browser_ux_04.py` and this summary both found on disk;
`companion/test_browser_ux.py` confirmed deleted; all three commit hashes
(`81b2665`, `b46d6b1`, `9e8d794`) found in `git log --oneline --all`. All
verification commands re-run live in this session: part-04 module 13/13,
legacy file gone, ledger check exit 0 (75/75 mapped, 74 ported / 1 deleted
/ 0 pending), suite guards + shim (browser_ux-scoped) 35/35, suite guards
+ test-support (full, unscoped) 108/108, `ruff check` clean, full browser
suite 128/128 in 101.03s, full unscoped suite 2497 passed / 5 skipped /
0 failed.
