---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 03
subsystem: api
tags: [python, stdlib, json, threading, calendar, registry, throttle]

# Dependency graph
requires:
  - phase: 16-01
    provides: "the RFC 5545 subset parser (parse_ics_events()), the shared constants/allowlists, and the redacted fixture"
provides:
  - "calendar_rules.json registry file contract: calendar_rules_path(), load_calendar_registry(), write_calendar_registry()"
  - "the calendar URL's two accessors: calendar_is_configured() (bool, presence only) and configured_calendar_url() (the value, sole accessor)"
  - "D-03's rolling-window filter: select_window_entries(entries, now)"
  - "the durable fetch throttle: calendar_fetch_is_due(last_attempt_at, now, min_interval_s=None)"
  - "31/31 test_calendar_rules.py harness, up from 20/20"
affects: [16-04-calendar-fetch, 16-05-settings-status-line, 16-06-calendar-matcher]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Never-raising load + tmp-write-then-os.replace(), copied from colour_rules.py's exact shape, applied to a second, D-01-separate registry file"
    - "Two-timestamp split (last_attempt_at epoch-float for throttle arithmetic vs last_synced_at ISO-string for UI copy) as two independently-normalised, independently-tested fields"
    - "Whole-file rewrite (never merge) as the mechanism that makes D-03's retention window a property of the write, not a cleanup pass"

key-files:
  created: []
  modified:
    - server/plane/calendar_rules.py
    - server/test_calendar_rules.py

key-decisions:
  - "D-01 enforced structurally (no colour_rules import, zero literal 'colour_rules.json' occurrences in the file - including rephrasing plan 16-01's own docstring text that had the literal string) and behaviourally (a colour_rules.json sha256 is provably unchanged by any calendar registry write)"
  - "Both load_calendar_registry() and write_calendar_registry() share one private rebuild-and-cap helper (_rebuild_capped_entries / _normalise_calendar_entry), so a caller can never persist an entry shape the loader would only drop again on the next read"
  - "calendar_fetch_is_due() reads only last_attempt_at, never last_synced_at, matching poll_loop.advance_is_due()'s exact shape including its negative-elapsed clock-step guard"

requirements-completed: []

coverage:
  - id: D1
    description: "calendar_rules.json is a separate, never-raising, allowlist-revalidating, capped, atomically-written registry file, provably distinct from colour_rules.json (D-01)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#D-01: writing and re-writing the calendar registry never touches colour_rules.json's content or bytes, and the two registries are distinct files"
        status: pass
      - kind: unit
        ref: "server/test_calendar_rules.py#load_calendar_registry() drops every one of eight hostile entry shapes ... and raises nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "write_calendar_registry() replaces the registry WHOLE on every call - a shorter write leaves only the shorter list, an empty write empties the window (D-03)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#write_calendar_registry() replaces the whole file - a shorter second write leaves only that list, never a merge with the earlier one"
        status: pass
      - kind: unit
        ref: "server/test_calendar_rules.py#write_calendar_registry([]) empties the registry rather than leaving the previous entries behind, with both timestamps still readable"
        status: pass
    human_judgment: false
  - id: D3
    description: "select_window_entries() reduces entries to the current-UTC-day-through-48h window, sorted, capped, non-mutating, with a back edge strictly wider than the matcher's own tolerance"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#select_window_entries() keeps an already-landed-earlier-today entry, a later-today entry and a 47h-ahead entry, drops one ended yesterday and one 49h ahead, sorted ascending, without mutating its input"
        status: pass
      - kind: unit
        ref: "server/test_calendar_rules.py#select_window_entries() excludes an entry carrying a 19th-century timestamp for a present-day now"
        status: pass
    human_judgment: false
  - id: D4
    description: "calendar_fetch_is_due() gates the 30s poll oneshot's calendar fetch from a durable timestamp, tolerating a backwards clock and non-numeric/boolean input, and reads only last_attempt_at (never last_synced_at)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#calendar_fetch_is_due() returns the exact expected verdict for never-fetched, just-fetched, one-second-before/-after the interval, a future timestamp, a string, and a boolean"
        status: pass
      - kind: unit
        ref: "server/test_calendar_rules.py#the two persisted timestamps survive a round trip with distinct types (a number and an ISO string), and calendar_fetch_is_due() consults only last_attempt_at"
        status: pass
    human_judgment: false
  - id: D5
    description: "the calendar URL has exactly one value accessor (configured_calendar_url()) and one boolean presence accessor (calendar_is_configured()), both reading the environment per call, and a URL token never reaches the persisted file, the loaded dict's serialisation, or stderr"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#a distinctive token set in the calendar URL environment variable appears in neither calendar_rules.json's bytes, the loaded dict's serialisation, nor anything printed to stderr during a round trip"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-09-08
status: complete
---

# Phase 16 Plan 03: Calendar registry, rolling window and fetch throttle Summary

**`calendar_rules.py` gained a D-01-separate, D-03-whole-file-rewrite registry (`{state_dir}/calendar_rules.json`), a 48h rolling-window filter, and a durable fetch throttle reading only `last_attempt_at` — 31/31 in the extended harness, 19/19 harnesses green suite-wide.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-09-07T23:52 (first task commit)
- **Completed:** 2026-09-08T00:00 (final task commit)
- **Tasks:** 3/3 completed
- **Files modified:** 2 (`server/plane/calendar_rules.py`, `server/test_calendar_rules.py`)

## Accomplishments
- Gave the calendar URL exactly one value accessor (`configured_calendar_url()`) and one boolean presence accessor (`calendar_is_configured()`), both reading `SKYPANE_CALENDAR_ICS_URL` on every call with no module-level cache
- Built `calendar_rules.json`'s full file contract — `calendar_rules_path()`, `load_calendar_registry()`, `write_calendar_registry()` — copying `colour_rules.py`'s never-raising-load and tmp-write-then-`os.replace()` shapes verbatim, while proving (both structurally via AST/grep and behaviourally via a sha256 round trip) that it never touches `colour_rules.json`
- Implemented D-03's rolling window (`select_window_entries()`, current UTC day through 48h forward, sorted, capped, non-mutating) and the durable fetch throttle (`calendar_fetch_is_due()`, `poll_loop.advance_is_due()`'s exact shape including its negative-elapsed clock-step guard)
- Extended `server/test_calendar_rules.py` from 20 to 31 checks, adding the D-01 separation proof, the D-03 whole-file-rewrite proof, the rolling-window keep/drop boundary check, the 19th-century-junk exclusion, the entry cap and eight-hostile-shapes checks, the throttle's exact seven-case verdict table, the two-timestamps-differ-by-role proof, and the URL-token containment check across file bytes, serialised dict and stderr

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the env-var accessors and the calendar_rules.json file contract (D-01)** - `1695952` (feat)
2. **Task 2: Add D-03's rolling-window filter and the durable throttle gate** - `68f1ae3` (feat)
3. **Task 3: Extend server/test_calendar_rules.py with the D-01, D-03, throttle and two-timestamp checks** - `8e2b65f` (test)

_Note: Task 1 and Task 2 both modify `server/plane/calendar_rules.py`; each was isolated to its own commit by reconstructing the pre-Task-2 file state, verifying it independently, committing it, then restoring and committing Task 2's addition on top — so both commits are independently checkable against the plan's own per-task verification blocks._

## Files Created/Modified
- `server/plane/calendar_rules.py` - added the registry file contract (Task 1) and the rolling-window/throttle functions (Task 2)
- `server/test_calendar_rules.py` - extended with 11 new checks (Task 3), `EXPECTED_CHECK_COUNT` raised 20 -> 31

## Decisions Made
- Shared a single private helper (`_rebuild_capped_entries()` / `_normalise_calendar_entry()`) between `load_calendar_registry()` and `write_calendar_registry()`, so the write path truncates/rejects with the identical per-field gates and cap the read path applies — a caller cannot persist what the next read would only drop again, and the drop-count warning fires from whichever call site actually did the capping.
- Rephrased three pre-existing plan-16-01 docstring lines that spelled out the literal substring `colour_rules.json` (a redeploy note and two lock-scope comments), because the plan's own acceptance gate (`grep -c 'colour_rules.json' calendar_rules.py` == 0) is whole-file, not diff-scoped. No behavior change — wording only.
- `calendar_fetch_is_due()` and `select_window_entries()` both accept a malformed/hostile input (non-numeric, boolean, non-list) and degrade rather than raise, matching every other function in this module's never-raising discipline, even though the plan's own behavior spec only mandated this explicitly for the timestamp argument.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed the D-01 grep gate by rephrasing pre-existing docstring text**
- **Found during:** Task 1, running the plan's own acceptance criteria
- **Issue:** `grep -c 'colour_rules.json' server/plane/calendar_rules.py` must return `0`, but plan 16-01's own module docstring already contained three literal occurrences of that filename in prose (a redeploy note and lock-scope comments) before this plan touched the file
- **Fix:** Rephrased those three pre-existing lines (and two new ones this plan's own docstrings would otherwise have added) to describe "phase 15's colour-rule registry" / "phase 15's rule store" instead of spelling out the literal filename, with no change in meaning
- **Files modified:** `server/plane/calendar_rules.py`
- **Verification:** `grep -c 'colour_rules.json' server/plane/calendar_rules.py` returns `0`; full harness and `ruff check` still pass
- **Commit:** `1695952`

**2. [Rule 1 - Bug] Fixed a duplicate `os.replace()` grep match from a comment**
- **Found during:** Task 1, running the plan's own acceptance criteria
- **Issue:** `grep -c 'os.replace' server/plane/calendar_rules.py` must return `1`, but a `_WRITE_LOCK` comment describing the lock's scope also contained the literal substring `os.replace()`, making the count `2`
- **Fix:** Reworded the comment to say "the final atomic replace" instead of naming the function literally
- **Files modified:** `server/plane/calendar_rules.py`
- **Verification:** `grep -c 'os.replace' server/plane/calendar_rules.py` returns `1`
- **Commit:** `1695952`

**3. [Rule 1 - Bug] Fixed an invalid theme id in the new D-01 separation test**
- **Found during:** Task 3, first harness run
- **Issue:** The new D-01 separation check called `colour_rules.add_rule(tmp, "prefix", "AFR", "amber_glow")` with a theme id that is not a member of `device_config.THEMES`; `add_rule()` correctly rejected it and never wrote `colour_rules.json`, causing a `FileNotFoundError` when the check tried to hash the (non-existent) file
- **Fix:** Used the real theme id `"white"` instead
- **Files modified:** `server/test_calendar_rules.py`
- **Verification:** `server/test_calendar_rules.py` reports `31/31 checks pass`
- **Commit:** `8e2b65f`

---

**Total deviations:** 3 auto-fixed (all Rule 1 - bugs surfaced by the plan's own acceptance criteria while implementing it)
**Impact on plan:** All three fixes were required to satisfy this plan's own stated gates; no scope creep, no behavior beyond what the plan specified.

## Issues Encountered
- This worktree checkout had no `server/.venv` (the venv is gitignored and not carried into a fresh worktree). Symlinked `server/.venv -> /Users/florian/Projects/skypane/server/.venv`, the documented network-free bootstrap route from phase 14 plan 14-01 Task 1 (see the repo-root `.gitignore`'s own comment on this exact pattern). The symlink is itself gitignored (`/server/.venv`) and was not committed.
- Verified the D-03 whole-file-rewrite check and the throttle check are both "live" (not vacuous) per the plan's own acceptance criteria: temporarily patched `write_calendar_registry()` to merge with existing entries (harness dropped to 29/31, with the whole-file-rewrite check specifically failing) and temporarily made `calendar_fetch_is_due()` return `True` unconditionally (harness dropped to 29/31, with the throttle check specifically failing), then reverted both patches before committing anything (`git status --short` confirmed a clean, matching-HEAD working tree after each revert).

## User Setup Required
None - no external service configuration required. `SKYPANE_CALENDAR_ICS_URL` is read by `calendar_is_configured()`/`configured_calendar_url()` but is not required to be set for this plan's tests (they set/unset it themselves in temporary environment mutations, always restored in a `finally`).

## Next Phase Readiness
- Plan 16-04 (the throttled, hardened fetch) can call `calendar_fetch_is_due()`, `write_calendar_registry()` and the `FETCH_*` result constants directly; nothing else needs to change in this module for that plan to begin.
- Plan 16-05 (Settings status line) can call `calendar_is_configured()` and read `last_synced_at` from `load_calendar_registry()`'s return without ever touching `configured_calendar_url()`.
- Plan 16-06 (the matcher) can call `select_window_entries()` on `load_calendar_registry()`'s `entries` to get the bounded candidate list its match function compares against.
- No blockers. `server/plane/render.py`, `server/plane/colour_rules.py`, `server/poll_loop.py`, `server/device_config.py`, `companion/`, and both requirements files are all untouched by this plan's commits (verified via `git diff --stat`).

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Completed: 2026-09-08*

## Self-Check: PASSED

- FOUND: `server/plane/calendar_rules.py`
- FOUND: `server/test_calendar_rules.py`
- FOUND commit: `1695952` (Task 1)
- FOUND commit: `68f1ae3` (Task 2)
- FOUND commit: `8e2b65f` (Task 3)
