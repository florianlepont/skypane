---
phase: 10-scheduled-quiet-hours
plan: 01
subsystem: config
tags: [python, zoneinfo, device-config, dst, validation]

# Dependency graph
requires: []
provides:
  - "device_config.json quiet-hours registry: quiet_hours_enabled/quiet_hours_start/quiet_hours_end fields"
  - "normalise_quiet_hours_enabled()/normalise_quiet_hours_time() read-path helpers (never-raise, degrade to default)"
  - "save_device_config() strict write-path validation for the three quiet-hours fields"
  - "seconds_until_quiet_hours_end() DST-safe Europe/Paris window arithmetic, the function plan 10-03 vendors byte-for-byte"
  - "quiet_hours_status() epoch-seconds convenience wrapper for plan 10-04's poll_loop.py gate"
affects: [10-02, 10-03, 10-04, 10-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One shared normalise_quiet_hours_time(value, default) function for both start/end fields, never two near-identical ones, so validation strictness can't drift apart between them"
    - "_HHMM_RE anchored with \\Z (not $) so a trailing-newline value can't smuggle a dirty string past the shape gate"
    - "Window-end arithmetic subtracts in UTC after converting both operands, not in local wall-clock time, to stay correct across a DST transition (same-tzinfo aware-datetime subtraction silently ignores the zone)"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py
    - companion/test_config_page.py

key-decisions:
  - "seconds_until_quiet_hours_end() deviates from 10-PATTERNS.md's reference body by converting end_dt to UTC before subtracting now_utc — the reference body's naive same-tzinfo subtraction is off by exactly one hour across a Europe/Paris DST transition"
  - "The 02:00-03:00 DST transition-hour boundary case (PEP 495 fold=0) is accepted as a documented caveat, not engineered around, per D-01's 'never shorter than base sleep' bound on the worst case"
  - "quiet_hours_status() is a separate function from seconds_until_quiet_hours_end(), deliberately NOT vendored into stub-server/byos_server.py (plan 10-03) since it's a poll_loop.py-only convenience wrapper"

patterns-established:
  - "Write-path-is-strict / read-path-is-forgiving asymmetry extended to the three new quiet-hours fields, matching the existing theme/tracked_runway/led_enabled contract"

requirements-completed: []

coverage:
  - id: D1
    description: "load_device_config() returns six keys with documented defaults, and every hostile on-disk quiet-hours value degrades silently instead of reaching a caller"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#load_device_config() replaces hostile quiet_hours_enabled/quiet_hours_start/quiet_hours_end values with their documented defaults"
        status: pass
    human_judgment: false
  - id: D2
    description: "save_device_config() rejects an invalid submitted quiet-hours value with ValueError and leaves any pre-existing file byte-identical"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#save_device_config(quiet_hours_start='24:00') raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py#save_device_config(quiet_hours_enabled='on') raises ValueError"
        status: pass
    human_judgment: false
  - id: D3
    description: "seconds_until_quiet_hours_end() returns the true elapsed seconds to the window's local end time, including across a Europe/Paris DST transition (23400s spring / 30600s autumn)"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#seconds_until_quiet_hours_end() returns the verified wrap-midnight/DST anchors"
        status: pass
    human_judgment: false
  - id: D4
    description: "quiet_hours_status() returns (None, None) for a disabled window, a zero-width window, and any hostile now_epoch, and never raises"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#quiet_hours_status() returns (None, None) when quiet_hours_enabled is False, and (28000, '07:00') for an enabled config"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py#quiet_hours_status() returns (None, None) and never raises for a non-numeric string, None, NaN, or an absurdly large now_epoch"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-03
status: complete
---

# Phase 10 Plan 01: Quiet-Hours Registry Fields + DST-Safe Window Arithmetic Summary

**Three new quiet-hours fields (D-03 one daily recurring window, D-04 separate enabled flag) in `device_config.py`'s registry, plus DST-correct Europe/Paris window arithmetic that every other Wave-2 plan in this phase reads.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-03T21:00Z (approx.)
- **Completed:** 2026-09-03T21:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `load_device_config()` now returns six keys (`theme`, `tracked_runway`, `led_enabled`, `quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`); every hostile or stale on-disk quiet-hours value degrades silently to its documented default
- `save_device_config()` validates all three new quiet-hours arguments before touching the file, raising `ValueError` for a non-bool `quiet_hours_enabled` or a malformed HH:MM string, and never leaves a partial write
- `seconds_until_quiet_hours_end(now_utc, start_hm, end_hm)` — wrap-midnight-aware Europe/Paris window arithmetic, numerically verified against the real Europe/Paris DST transitions (28000s mid-window, 23400s spring-forward, 30600s fall-back)
- `quiet_hours_status(config, now_epoch)` — the never-raising epoch-seconds convenience wrapper `server/poll_loop.py` will call in plan 10-04
- `server/test_config_history.py`'s harness grew from 30 to 39 checks; `companion/test_config_page.py` stays green at its unchanged 64

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the three quiet-hours registry fields to device_config.py** - `05ca4b5` (feat)
2. **Task 2: Add DST-safe Europe/Paris window arithmetic** - `715d8fb` (feat)

_Note: no separate plan-metadata commit exists yet — this SUMMARY.md commit doubles as it, per the final_commit step below._

## Files Created/Modified
- `server/device_config.py` - Three new registry constants, `_HHMM_RE` shape gate, `QUIET_HOURS_TZ`, `normalise_quiet_hours_enabled()`/`normalise_quiet_hours_time()`, extended `load_device_config()`/`save_device_config()`, `seconds_until_quiet_hours_end()`, `quiet_hours_status()`
- `server/test_config_history.py` - Repaired 6 full-document equality assertions broken by the new keys; added 9 new `check(...)` calls (5 for Task 1's registry fields, 4 for Task 2's window arithmetic); `EXPECTED_CHECK_COUNT` 30 → 39
- `companion/test_config_page.py` - Repaired the one equivalent full-dict equality assertion in `_valid_save_writes_both_and_returns_saved_key()`; no other change (plan 10-05 owns the rest of this file)

## Decisions Made
- Subtract in UTC (`end_dt.astimezone(timezone.utc) - now_utc`), not local time, in `seconds_until_quiet_hours_end()` — verified during planning that the reference implementation's same-tzinfo subtraction silently ignores the zone and is off by exactly one hour across a DST transition. This deviation is documented in the function's own docstring so a future reader doesn't "restore" the reference version.
- Accepted the 02:00-03:00 DST transition-hour boundary case as a documented caveat rather than adding a `fold=1` override, per D-01's bound on the worst case (one extra/missing wake, twice a year, only for a boundary configured inside that specific hour).
- `quiet_hours_status()` re-normalises both time strings through `normalise_quiet_hours_time()` before use, so a hand-built `config` dict can't slip an unvalidated string into the arithmetic.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria commands were run verbatim and all passed; `git diff --name-only` after each commit matched the plan's declared file list exactly.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plans 10-02 (render.py quiet-hours canvas), 10-03 (byos_server.py vendored duplicate), and 10-04 (poll_loop.py gate) can now all read the same six-key `load_device_config()` contract and the same `seconds_until_quiet_hours_end()`/`quiet_hours_status()` arithmetic without coordinating with each other.
- `scripts/run-all-tests.sh` run at the end of this plan: 22/22 harnesses pass (the sole non-zero note is the pre-existing, already-accepted macOS Pillow/FreeType `panel.bin` digest mismatch, unrelated to this plan's changes and confirmed present before this plan started).
- `server/requirements.txt` unchanged — `zoneinfo` is stdlib since Python 3.9, no new dependency introduced.

---
*Phase: 10-scheduled-quiet-hours*
*Completed: 2026-09-03*
