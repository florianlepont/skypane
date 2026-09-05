---
phase: 12-remote-display-on-off-toggle
plan: 03
subsystem: infra
tags: [byos, vendored-server, sleep-s, quiet-hours, display-toggle, poll-protocol]

# Dependency graph
requires:
  - phase: 12-remote-display-on-off-toggle/12-01
    provides: "server/device_config.py's DEFAULT_DISPLAY_ENABLED, DISPLAY_OFF_SLEEP_S = 300, and normalise_display_enabled()"
provides:
  - "DISPLAY_OFF_SLEEP_S, read_display_enabled() and display_off_sleep_s() in stub-server/byos_server.py"
  - "GET /device/v1/display's sleep_s composed as quiet_hours_sleep_s(display_off_sleep_s(read_wake_interval_s(...), state_dir), state_dir) - the off-state pin nested INSIDE the quiet-hours extension"
  - "stub-server/VENDOR.md local-modification entry 7 documenting the change"
  - "6 new test_poll_cycle.py checks (34 -> 40) covering the fail-open contract, the flat pin, the D-05 overlap in both directions (unit + HTTP integration), the on-state regression guard, and constant parity"
affects: [12-04, 12-05, future-phases-touching-stub-server-byos-server]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vendored-file composition order as a correctness contract: display_off_sleep_s() must be the INNER call, quiet_hours_sleep_s() the OUTER call, so quiet_hours_sleep_s()'s existing max(base, remaining) absorbs the 300s pin as its base rather than the pin flattening an active quiet-hours window"
    - "Lightweight text-based constant parity check (sibling of the existing def-block drift guard) for a bare integer constant duplicated across the vendor boundary"

key-files:
  created: []
  modified:
    - stub-server/byos_server.py
    - stub-server/VENDOR.md
    - stub-server/test_poll_cycle.py

key-decisions:
  - "Nesting order confirmed the correctness-critical detail (D-05): quiet_hours_sleep_s(display_off_sleep_s(base, d), d) - not the reverse - verified with an executed negative control, not just read"
  - "display_off_sleep_s() is a flat replacement (not max()/min()) against the base - the whole content of D-01, since a naive max() would defeat the point of the fixed off-state cadence for long configured intervals"
  - "The D-05 overlap check needed BOTH a unit-level test (using quiet_hours_sleep_s()'s injectable now= seam for deterministic epoch-level assertions) and an HTTP integration-level test (exercising the real inlined do_GET response expression) - the unit test alone would not have caught an inverted composition order in byos_server.py, since it composes the functions directly rather than going through the server's response construction"

requirements-completed: []

coverage:
  - id: D1
    description: "With display_enabled false, GET /device/v1/display serves sleep_s == 300 regardless of the configured wake_interval_s (D-01)"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#with display_enabled false and no quiet-hours window..."
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#a device_config.json with a below-floor wake_interval_s:30..."
        status: pass
    human_judgment: false
  - id: D2
    description: "With display_enabled false AND an active quiet-hours window, served sleep_s is max(300, quiet_hours_remaining) in both directions (D-05, sleep axis)"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#with the display off and quiet hours active, the served sleep_s is max(300, quiet_hours_remaining)..."
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#with display_enabled false and quiet hours enabled for a window still ~1h from ending..."
        status: pass
    human_judgment: false
  - id: D3
    description: "With display_enabled true, served sleep_s is byte-for-byte the pre-existing Phase 10/11 chain in all four combinations of window/wake-interval"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#with display_enabled true, the composed sleep_s chain (including display_off_sleep_s())..."
        status: pass
    human_judgment: false
  - id: D4
    description: "A missing, unreadable, malformed, non-dict, or non-bool display_enabled degrades to enabled and never raises"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#read_display_enabled() returns True and never raises for a missing, truncated..."
        status: pass
    human_judgment: false
  - id: D5
    description: "byos_server.py imports nothing from server.* (vendor boundary), and VENDOR.md carries the fourth (seventh, numbered per existing entries) local-modification entry in the same commit as the code"
    verification:
      - kind: other
        ref: "AST-walk confirming no real server.* Import/ImportFrom node exists (run manually, see Deviations); git show --stat eb7a413 lists both stub-server/byos_server.py and stub-server/VENDOR.md"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-09-05
status: complete
---

# Phase 12 Plan 03: Display-off sleep_s pin composed inside quiet hours Summary

**`display_off_sleep_s()` pins GET /device/v1/display's sleep_s to a flat 300s while the display is off, nested inside the existing `quiet_hours_sleep_s()` extension so `max(300, quiet_hours_remaining)` falls out for free — proven correct by an executed negative control that inverts the nesting and confirms it breaks.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-05
- **Tasks:** 2 (both auto)
- **Files modified:** 3 (`stub-server/byos_server.py`, `stub-server/VENDOR.md`, `stub-server/test_poll_cycle.py`)

## Accomplishments

- Added `DISPLAY_OFF_SLEEP_S = 300`, `read_display_enabled()` (fail-open, never-raising, mirrors `read_led_enabled()`), and `display_off_sleep_s()` (flat replacement, not `max()`/`min()`) to the vendored `stub-server/byos_server.py`.
- Rewired `GET /device/v1/display`'s `sleep_s` expression to `quiet_hours_sleep_s(display_off_sleep_s(read_wake_interval_s(...), state_dir), state_dir)` — the off-state pin becomes `quiet_hours_sleep_s()`'s own base, so its unmodified `max(base_sleep_s, remaining)` produces `max(300, quiet_hours_remaining)` with zero change to the Phase 10 function.
- Recorded the change as `VENDOR.md` local-modification entry 7, in the same commit as the code (`git show --stat eb7a413` names both files), and bumped the re-pinning count from six to seven local modifications.
- Extended `stub-server/test_poll_cycle.py` from 34 to 40 checks: `read_display_enabled()`'s fail-open contract (7 malformed/wrong-typed cases + a real `false` surviving), the flat 300s pin across four base values including one longer than 300, the D-05 overlap in both directions (unit-level via the injected `now=` seam, plus an HTTP-integration check against the real `do_GET` composition), an on-state regression guard across all four window/wake-interval combinations, and a lightweight text-based parity check pinning `DISPLAY_OFF_SLEEP_S` equal between `byos_server.py` and `server/device_config.py`.
- Executed the composition-order negative control for real: temporarily inverted the nesting so `display_off_sleep_s()` wrapped `quiet_hours_sleep_s()` instead of the reverse, re-ran the harness, and confirmed the new integration overlap check failed with `sleep_s=300` against an expected `>300` remaining (39/40, with the exact failure message recorded below). Reverted; harness returned to 40/40 green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the off-state sleep pin to byos_server.py and record it in VENDOR.md** - `eb7a413` (feat)
2. **Task 2: Extend stub-server/test_poll_cycle.py** - `24400ad` (test)

## Files Created/Modified

- `stub-server/byos_server.py` - Added `DISPLAY_OFF_SLEEP_S`, `read_display_enabled()`, `display_off_sleep_s()`, rewired the `sleep_s` response expression, extended the module docstring's local-modifications list
- `stub-server/VENDOR.md` - Added local-modification entry 7 (display-off `sleep_s` pin, composition order, rationale); updated the re-pinning count and instructions to seven local modifications
- `stub-server/test_poll_cycle.py` - Added 6 checks (34 → 40), bumped `EXPECTED_CHECK_COUNT`, extended the module docstring and tally comment

## Decisions Made

- **Composition order is the whole correctness of this plan (D-05).** `display_off_sleep_s()` must be the inner call, `quiet_hours_sleep_s()` the outer call. Verified live, not just asserted from reading: temporarily inverting the nesting in `byos_server.py` made the new HTTP-integration overlap check fail exactly as predicted (served `300` instead of the expected `>300` remaining), then reverting restored green. Recorded verbatim below per the plan's requirement.
- **The unit-level overlap check alone would not have caught an inverted composition order.** It calls `quiet_hours_sleep_s(display_off_sleep_s(...), ...)` directly with an explicit, hardcoded-correct order, so it can pin the arithmetic (`max(300, 28000) == 28000`, `max(300, 200) == 300`) but is blind to how `byos_server.py`'s own inlined `do_GET` response expression is actually wired. Added a second, HTTP-integration-level check that exercises the real response construction — this is the check the negative control targets, and it is the one that actually failed under inversion.
- **`display_off_sleep_s()` is a flat replacement, not `max()`/`min()`.** Confirmed via the flat-pin check across `base` values 60, 300, 900, and 3600 — the 3600 case is the one that would silently pass under a wrong `max()` implementation (since `max(300, 3600) == 3600` looks plausible) but fails correctly here because the pin must *replace* rather than bound the base.

## Deviations from Plan

### Auto-fixed / Adjusted

**1. [Verification-script false positive, not a code issue] `verify` block's naive `'from server' not in src` substring check**
- **Found during:** Task 1's `<verify>` automated command
- **Issue:** The plan's provided verification script asserts `'import server' not in src and 'from server' not in src` against the raw file text to prove the vendor boundary holds. This substring check has a pre-existing false positive: prose comments already present in `byos_server.py` before this plan touched it (added in Phase 10/11, e.g. `"...character-for-character from server/device_config.py's own _HHMM_RE"` and `"...rather than imported from server/device_config.py"`) contain the literal substring `"from server"` despite never being a Python `import` statement. Confirmed via `git stash` that these lines existed unchanged before Task 1's edits — this is not something introduced by this plan.
- **Fix:** Did not alter the pre-existing prose (removing it would degrade documentation that follows an established precedent). Instead verified the real intent — no actual `server.*` import statement exists — using an AST walk over `ast.Import`/`ast.ImportFrom` nodes, which confirmed zero real imports. Ran every other assertion in the verify block (the `DISPLAY_OFF_SLEEP_S == 300` check and all `display_off_sleep_s()` behavior assertions) unmodified; all passed.
- **Files modified:** None (no code change was warranted; documented here for auditability).
- **Verification:** `server/.venv/bin/python3 -c "import ast; ..."` confirmed no `server`/`server.*` `Import`/`ImportFrom` node exists anywhere in `stub-server/byos_server.py`.
- **Committed in:** N/A (verification-only finding, not a commit).

---

**Total deviations:** 1 (verification-script limitation, not a functional or correctness issue)
**Impact on plan:** None on delivered functionality. The vendor-boundary contract (no real `server.*` import) holds and was proven by AST inspection rather than the plan's naive substring check.

## Negative Control — Executed Result

Per the plan's requirement, the composition-order negative control was run for real, not asserted from reading:

1. Temporarily edited `stub-server/byos_server.py`'s `do_GET` response construction to invert the nesting:
   ```python
   "sleep_s": display_off_sleep_s(
       quiet_hours_sleep_s(
           read_wake_interval_s(self.args.state_dir, self.args.sleep),
           self.args.state_dir),
       self.args.state_dir),
   ```
2. Re-ran `server/.venv/bin/python3 stub-server/test_poll_cycle.py`. Result: **39/40 checks pass**, with the new integration overlap check failing verbatim:
   ```
   FAIL with display_enabled false and quiet hours enabled for a window still ~1h from ending, a live GET /device/v1/display response's sleep_s is strictly greater than 300 (the remaining window time wins over the flat off-state pin, D-05's sleep axis) - this is the check the composition-order negative control targets - expected sleep_s in (300, 7200] (the remaining window time, not the flat 300s off-state pin), got 300 - display_off_sleep_s() may be nested outside quiet_hours_sleep_s() instead of inside it
   poll-cycle: 39/40 checks pass
   ```
3. Reverted the temporary edit. Re-ran the harness: **40/40 checks pass**, and `git diff --stat stub-server/byos_server.py` showed no residual diff (the revert exactly restored the committed Task 1 state).

This confirms the inverted order silently collapses an active quiet-hours window's remaining sleep down to the flat 300s pin — exactly the failure mode D-05 exists to prevent (the device would wake all night with the display off instead of sleeping through the quiet-hours window).

## Issues Encountered

None beyond the verify-script false positive documented above.

## User Setup Required

None - no external service configuration required. No deployment or environment change is needed (`git diff --quiet deploy/` confirmed clean; `SKYPANE_SLEEP_S` remains the unchanged base value).

## Next Phase Readiness

- `stub-server/byos_server.py`'s served `sleep_s` now correctly composes the display-off pin with quiet hours; ready for 12-04 (`server/poll_loop.py`'s gate/render-skip logic) and 12-05 (companion Settings toggle) to complete the phase once their parallel wave-2 work lands.
- No blockers. `server/test_config_history.py` (49/49) and `stub-server/test_poll_cycle.py` (40/40) both green; `ruff check` clean on both modified files in this plan's scope.

---
*Phase: 12-remote-display-on-off-toggle*
*Completed: 2026-09-05*

## Self-Check: PASSED

All 3 created/modified files confirmed present on disk; both task commit hashes (`eb7a413`, `24400ad`) confirmed present in `git log --oneline --all`. No missing items.
