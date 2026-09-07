---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 02
subsystem: config
tags: [device_config, python, validation, tamper-defense]

# Dependency graph
requires:
  - phase: 15-arrivals-theme-override-manual-per-flight-colour-rules
    provides: "theme_arriving's two-gate (read/write) normalise contract and CLEAR_THEME_ARRIVING sentinel precedent, copied for calendar_theme_id's read/write gates"
provides:
  - "device_config.json's new optional calendar_theme_id key: None or a THEMES member, validated on both read and write, no migration required"
  - "normalise_calendar_theme_id() - degrade-to-None (never DEFAULT_THEME_ID) contract"
  - "save_device_config(..., calendar_theme_id=None) keyword with a ValueError gate and carry-forward-on-omission semantics"
affects: [16-05-companion-settings-calendar-section, 16-06-calendar-matcher-resolver]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional config key modeled on theme_arriving's contract minus the clear-sentinel: None means both 'not chosen' and 'not supplied, carry forward' since there is no UI checkbox to disambiguate the two."

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py

key-decisions:
  - "No CLEAR_CALENDAR_THEME-style sentinel: the Calendar section's <select> has no enable/disable checkbox (16-UI-SPEC.md), so None keeps its single existing carry-forward meaning, matching wake_interval_s's resolution rather than theme_arriving's three-state one."
  - "Hostile/unrecognised calendar_theme_id degrades to None, never DEFAULT_THEME_ID - an inert 'no calendar theme chosen' state, not a silent repaint in the base theme."

requirements-completed: []

coverage:
  - id: D1
    description: "load_device_config()/save_device_config() gain a validated, optional calendar_theme_id key defaulting to None, with no migration for pre-existing files"
    verification:
      - kind: unit
        ref: "server/test_config_history.py - 6 new calendar_theme_id checks (absent-key-default, round-trip, hostile-degrade x7 shapes, write-gate-rejection, carry-forward-both-directions, independence-from-theme_arriving)"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py - full-dict-equality assertions updated across 9 existing checks to include calendar_theme_id"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-07
status: complete
---

# Phase 16 Plan 02: Add optional calendar_theme_id key to device_config Summary

**Added `calendar_theme_id` to `server/device_config.py`'s validated config registry - a `None`-or-`THEMES`-member key with no clear sentinel, mirroring `theme_arriving`'s two-gate tamper defense but deliberately diverging on write semantics since the Calendar section's `<select>` has no enable/disable checkbox.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-07T16:55:00+02:00
- **Completed:** 2026-09-07T17:15:33+02:00
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- `normalise_calendar_theme_id()` added, degrading any hostile/wrong-typed/unrecognised on-disk value to `None` - provably never to `DEFAULT_THEME_ID` - with a docstring explaining why the degrade-to-default shape would be actively wrong for this key (T-16-TAMPER).
- `load_device_config()` always returns `calendar_theme_id` (third key, after `wake_interval_s` and `theme_arriving`, whose valid value set includes `None`); no migration step, byte-identical for a pre-existing file that never carried the key.
- `save_device_config()` gained a `calendar_theme_id=None` keyword with a `ValueError` gate (checked before anything is written, leaving a rejected file byte-identical) and carry-forward-on-omission semantics, deliberately with no `CLEAR_THEME_ARRIVING`-style sentinel.
- `server/test_config_history.py` extended: 9 pre-existing full-dict-equality assertions honestly updated to include the new key (never loosened to subset/range checks), plus 6 new checks covering absent-key-default, round-trip, 7-shape hostile degradation, write-gate rejection, bidirectional carry-forward, and independence from `theme_arriving`. `EXPECTED_CHECK_COUNT` raised 54 -> 60, re-derived by running the harness.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the optional calendar_theme_id key to server/device_config.py** - `298c98b` (feat)
2. **Task 2: Extend server/test_config_history.py with the calendar_theme_id contract checks** - `b8ecee4` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `server/device_config.py` - `normalise_calendar_theme_id()`, wired into `load_device_config()`'s return dict and `save_device_config()`'s validation/write path and keyword signature; docstrings extended to record the deliberate divergence from `theme_arriving`'s three-state contract.
- `server/test_config_history.py` - full-dict-equality assertions updated; new `calendar_theme_id` test section added (6 checks); ledger comment and `EXPECTED_CHECK_COUNT` updated.

## Decisions Made
- Followed the plan's explicit instruction to check how `theme_arriving`/`CLEAR_THEME_ARRIVING` was implemented before writing this key, and confirmed via `16-UI-SPEC.md` that the Calendar section's `<select>` is `required` and always-rendered with no checkbox - so no clear sentinel was warranted. Documented this reasoning inline in both the new normaliser's docstring and `save_device_config()`'s docstring, exactly as the plan asked.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Acceptance-criteria grep collided with its own negative-existence proof**

- **Found during:** Task 1
- **Issue:** The plan's own action text instructed documenting the "no clear sentinel" divergence, and my first docstring draft used the literal string `CLEAR_CALENDAR_THEME` to name the sentinel kind deliberately not added. This tripped the plan's own acceptance criterion `grep -c 'CLEAR_CALENDAR' server/device_config.py` returning `0` (proving no such sentinel exists) - the comment's use of the term-under-negation was self-defeating.
- **Fix:** Reworded the docstring to reference `CLEAR_THEME_ARRIVING`'s own name generically ("no clear sentinel of `CLEAR_THEME_ARRIVING`'s kind") instead of coining and then negating a `CLEAR_CALENDAR_THEME`-shaped term.
- **Files modified:** `server/device_config.py`
- **Verification:** `grep -c 'CLEAR_CALENDAR' server/device_config.py` returns `0`.
- **Committed in:** `298c98b` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Documentation wording only; no behavioral change. No scope creep.

## Issues Encountered

**Worktree had no provisioned Python venv.** `server/.venv` did not exist in this worktree (a fresh git worktree checkout). Per the project's own documented "phase 14 plan 14-01 Task 1" symlinked-venv bootstrap pattern (recorded in the repo-root `.gitignore`), symlinked `server/.venv` to the main checkout's already-built `server/.venv` rather than reinstalling packages from scratch. This is the project's own sanctioned, network-free bootstrap route for a worktree, not a new pattern introduced by this plan.

**Known, expected `scripts/run-all-tests.sh` regression outside this plan's scope.** Adding `calendar_theme_id` as an always-returned key to `load_device_config()`'s dict changes the shape every full-dict-equality assertion compares against - including one in `companion/test_config_page.py` (`config-page: 108/109 checks pass`, one failure: "a post with a valid theme and runway writes both and returns the saved flash key"). This plan's own verification block explicitly forbids touching `companion/` (`git diff --stat -- companion/ ... must be empty for this plan's commits`, confirmed empty at completion), and `16-05-PLAN.md` (wave 3, `depends_on: [16-02, 16-03]`) explicitly lists `companion/test_config_page.py` in its own `files_modified` - this is the plan the phase's own dependency graph designates to update that assertion. Every harness this plan is scoped to touch or is required to leave unbroken (`server/test_config_history.py` 60/60, `server/test_poll_loop.py` 70/70, `server/test_render.py` 134/134) passes cleanly. `scripts/run-all-tests.sh` will exit 0 again once wave 3's 16-05 lands.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`calendar_theme_id` is live in `device_config.json`'s registry, validated on both read and write, ready for:
- **16-05** (Settings Calendar section, depends on 16-02): can now render a `<select name="calendar_theme_id">` sourced from `device_config.THEME_IDS` and post through `save_device_config(calendar_theme_id=...)`; will also need to update `companion/test_config_page.py`'s full-dict assertions (see Issues Encountered).
- **16-06** (calendar matcher / resolver): can read `device_cfg["calendar_theme_id"]` as an already-validated `None`-or-`THEMES`-member value with no further membership check needed at that tier, though `16-PATTERNS.md`'s resolver-tier gate should still re-apply the membership test as defense-in-depth per T-16-TAMPER's three-gate design.

No blockers.

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Completed: 2026-09-07*

## Self-Check: PASSED

- FOUND: server/device_config.py
- FOUND: server/test_config_history.py
- FOUND: .planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-02-SUMMARY.md
- FOUND: commit 298c98b (feat(16-02): add optional calendar_theme_id key to device_config)
- FOUND: commit b8ecee4 (test(16-02): extend test_config_history.py for calendar_theme_id)
