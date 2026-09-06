---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 01
subsystem: testing
tags: [python, stdlib-only, test-harness, tdd, reflection]

# Dependency graph
requires: []
provides:
  - "server/.venv/bin/python3 resolvable from this worktree (symlinked to the main checkout's already-provisioned venv), plus a root .gitignore fix so the symlink doesn't show untracked"
  - "companion/test_view_pages.py: _LIGHTBOX_SHARED_TOKENS / _LIGHTBOX_AIRLINES_ONLY_TOKENS / _LIGHTBOX_RENDER_ONLY_TOKENS classified token tuples, replacing the old inline literal"
  - "companion/test_view_pages.py: _view_panel_attr_constants_all_classified() — reflection-driven coverage check over airlines_page._VIEW_PANEL_*_ATTR constants"
  - "companion/test_status_pages.py: _seed_manual_resolutions(state_dir, entries) fixture helper, the one sanctioned manual-registry seeding path"
affects: [14-02, 14-03, 14-04, 14-05, 14-06, 14-07, 14-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-file DOM-contract guards data-driven over classified token tuples (shared / scope-only / render-only-staging) instead of one inline literal tuple, with a reflection-driven coverage check enforcing every source constant is classified exactly once"
    - "Fixture helpers write exclusively through the module's own sanctioned mutation API (manual_resolutions.add_entry()), never a hand-written on-disk literal, and raise loudly (not silently no-op) on an unexpected result code"

key-files:
  created: []
  modified:
    - .gitignore
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "server/.venv is a symlink to the main checkout's already-provisioned venv (network-free bootstrap route), not a freshly built venv — verified identical baseline counts (54/149/159) before any change"
  - "Root .gitignore needed a new no-trailing-slash /server/.venv entry: git's existing `.venv/` pattern only matches a real directory and silently misses a symlink, so without this fix the symlink showed as untracked in git status. Added at repo root, not server/.gitignore, to respect the phase's 'no file under server/ is modified' boundary"
  - "_LIGHTBOX_RENDER_ONLY_TOKENS seeded empty per plan — a deliberate staging tuple for one wave at most, to be emptied again in plan 14-05"
  - "Chose AFR (a real server/plane/enrich.py static-table prefix) and XQZ (a novel one) as the manual-resolutions fixture's superseded/non-superseded pair, matching the existing supersession checks' own convention in the same file"
  - "Renamed the new status-pages check from _seed_manual_resolutions_helper_end_to_end to _manual_section_seed_helper_end_to_end mid-task — the original name's substring collision with _seed_manual_resolutions itself broke the acceptance criteria's `grep -c \"def _seed_manual_resolutions\"` (expected exactly 1, got 2)"

patterns-established:
  - "Token-tuple classification pattern: any future DOM-contract guard extension should add to one of the three classified tuples (or a new tuple with its own explicit present/absent contract), never back to an inline literal"
  - "Reflection-over-dir() coverage checks: enumerate a module's constants by name-shape match rather than hand-copying a list, so a new constant fails the harness by construction until classified"

requirements-completed: []

coverage:
  - id: D1
    description: "All three documented harness commands (view-pages, status-pages, companion-app) run verbatim from this worktree at their measured pre-change baselines (54/149/159), via a symlinked server/.venv with no PYTHON= override needed"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_view_pages.py — baseline 54/54"
        status: pass
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — baseline 149/149"
        status: pass
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_companion_app.py — baseline 159/159"
        status: pass
    human_judgment: false
  - id: D2
    description: "The lightbox DOM-contract guard is restructured onto three classified token tuples, and a new reflection-driven check fails the harness if any airlines_page._VIEW_PANEL_*_ATTR constant is left unclassified or double-classified"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_lightbox_dom_contract_three_file_guard and #_view_panel_attr_constants_all_classified — view-pages 55/55"
        status: pass
    human_judgment: false
  - id: D3
    description: "A single sanctioned manual-resolutions registry seeding helper (_seed_manual_resolutions) exists, seeds exclusively through manual_resolutions.add_entry(), raises loudly on any non-ADD_OK result, and is exercised end-to-end against a real render() call"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_manual_section_seed_helper_end_to_end — status-pages 150/150"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 01: Wave 0 Validation Scaffolding Summary

**Restructured the cross-file lightbox DOM-contract guard onto three classified token tuples plus a reflection-driven coverage check, and added the phase's one sanctioned manual-resolutions seeding fixture — both self-enforcing by construction, not by hand-maintained lists.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-09-06T12:43:30Z
- **Tasks:** 3 completed
- **Files modified:** 3 (`.gitignore`, `companion/test_view_pages.py`, `companion/test_status_pages.py`)

## Accomplishments
- `server/.venv/bin/python3` is resolvable from this worktree (symlinked to the main checkout's provisioned venv), so every VALIDATION.md command in this phase now runs verbatim with no `PYTHON=` prefix
- `_lightbox_dom_contract_three_file_guard()` in `companion/test_view_pages.py` no longer carries an inline literal token tuple — it reads three module-level, explicitly-scoped tuples (`_LIGHTBOX_SHARED_TOKENS`, `_LIGHTBOX_AIRLINES_ONLY_TOKENS`, `_LIGHTBOX_RENDER_ONLY_TOKENS`), and a new `_view_panel_attr_constants_all_classified()` check enforces by `dir()` reflection that every `airlines_page._VIEW_PANEL_*_ATTR` constant is classified in exactly one of them
- `companion/test_status_pages.py` gained `_seed_manual_resolutions(state_dir, entries)`, the one sanctioned write path into the manual-resolutions registry for every later wave, plus an end-to-end check proving it seeds correctly and that `_manual_resolution_rows()`'s `superseded` derivation still holds

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: worktree venv symlink + self-enforcing lightbox guard** - `eb40b4c` (test) — Task 1 produced no committable diff of its own (per plan instruction, its baseline record folded into this commit) beyond the `.gitignore` fix needed to keep the symlink untracked-and-ignored
2. **Task 3: manual-registry fixture helper** - `411e052` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

_Note: both tasks were `tdd="true"`; each was verified test-first (a deliberately unclassified/invalid input was confirmed to fail loudly) and then restored to a green working tree before committing — no separate RED-phase commit exists because the plan's own harness-exact-count gate requires every commit to be green._

## Files Created/Modified
- `.gitignore` - added a root-scoped, no-trailing-slash `/server/.venv` pattern so the symlinked venv (which git's existing `.venv/` directory-only pattern silently misses) shows as ignored, not untracked
- `companion/test_view_pages.py` - three classified lightbox token tuples, restructured guard, new reflection-driven coverage check, `EXPECTED_CHECK_COUNT` 54 → 55
- `companion/test_status_pages.py` - `_seed_manual_resolutions()` fixture helper, one new end-to-end check, `enrich` import added, `EXPECTED_CHECK_COUNT` 149 → 150

## Decisions Made
- Used the plan's preferred network-free route for Task 1 (symlink to the main checkout's venv) rather than the pip-install fallback — no new dependency touched, per the phase's stdlib-only-server / no-new-dependency boundary
- Discovered and fixed (Rule 3 — blocking issue) that git's `.venv/` gitignore pattern does not match a symlink even when it resolves to a directory, since git's ignore matcher checks the working-tree entry's own type (symlink) rather than following it; added a companion no-trailing-slash pattern at repo-root scope rather than touching `server/.gitignore` (out of bounds for this phase)
- Chose `AFR` / `XQZ` as the manual-resolutions fixture's superseded/non-superseded pair to match the file's own existing supersession-check convention
- Mid-task rename (Task 3): `_seed_manual_resolutions_helper_end_to_end` → `_manual_section_seed_helper_end_to_end`, because its name being a superstring of `_seed_manual_resolutions` broke the acceptance criteria's exact-count grep for the fixture helper's own definition

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Symlinked `server/.venv` showed as untracked, not ignored, in `git status`**
- **Found during:** Task 1
- **Issue:** The plan's read-first step cited `.gitignore` line 17 (`.venv/`) as proof "nothing created here is committable," but git's directory-only glob pattern (trailing `/`) does not match a symlink, even one that resolves to a directory — `git check-ignore` returned exit 1 and `git status --short` showed `?? server/.venv`. Left as-is, this both failed the task's own acceptance criterion ("git status --short shows no tracked change under server/.venv") and left a standing risk that a careless `git add` could stage a symlink into the main checkout's private venv.
- **Fix:** Added a second, no-trailing-slash `/server/.venv` pattern to the repo-root `.gitignore` (matches the named entry regardless of type — file, directory, or symlink). Confirmed via `git check-ignore -v server/.venv`.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` now shows only the `.gitignore` diff itself; `git check-ignore -v server/.venv` reports the new rule
- **Committed in:** `eb40b4c` (Task 1+2 commit)

**2. [Rule 1 - Bug] New check's function name collided with the acceptance criteria's own grep**
- **Found during:** Task 3
- **Issue:** `_seed_manual_resolutions_helper_end_to_end` is a superstring of `_seed_manual_resolutions`, so `grep -c "def _seed_manual_resolutions" companion/test_status_pages.py` (the acceptance criterion expecting exactly `1`) matched both definitions and returned `2`.
- **Fix:** Renamed the check function to `_manual_section_seed_helper_end_to_end`, matching the file's existing `_manual_section_*` naming convention for checks in this same section.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** Re-ran the grep (now `1`) and the harness (still `150/150`)
- **Committed in:** `411e052` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking git-ignore gap, 1 bug in a self-authored check name)
**Impact on plan:** Both fixes are process-safety corrections with zero behavioral scope creep — neither touches production code, and both were required to satisfy the plan's own acceptance criteria.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/.venv/bin/python3` is now usable verbatim from this worktree for every remaining plan in this phase
- The dialog contract guard will catch any Wave 1-3 plan that adds a `_VIEW_PANEL_*_ATTR` constant without classifying it in one of the three token tuples — no further guard-maintenance work needed until plan 14-05, which is expected to empty `_LIGHTBOX_RENDER_ONLY_TOKENS`
- `_seed_manual_resolutions()` is ready for Waves 1-3 to reuse as the one sanctioned manual-registry seeding path — no second seeding path should be invented
- Full `scripts/run-all-tests.sh` run (all 17 harnesses, 93% coverage) passes cleanly with only these two test files changed; no file under `companion/pages/`, `companion/static/` or `server/` was touched

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/test_view_pages.py
- FOUND: companion/test_status_pages.py
- FOUND: .gitignore
- FOUND: server/.venv (symlink)
- FOUND commit: eb40b4c
- FOUND commit: 411e052
