---
phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link
plan: 03
subsystem: api
tags: [python, poll-loop, colour-rules, theme-resolution, d-13]

# Dependency graph
requires:
  - phase: 14-01
    provides: "server/plane/colour_rules.py - the rule registry and resolve_effective_theme_id() resolver"
  - phase: 14-02
    provides: "device_config.py's theme_arriving key and CLEAR_THEME_ARRIVING sentinel"
provides:
  - "run_once() wired to colour_rules.resolve_effective_theme_id() at exactly its two flight-displaying build_canvas() call sites"
  - "effective_theme in both of run_once()'s result dicts and in its per-cycle log line"
  - "the D-13 both-branches invariant proven live: a battery-icon repaint of a rule-matched flight can never change its rendered theme"
affects: [14-04, 14-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Default-then-reassign local (effective_theme_id = theme_id at the top, reassigned only at the two call sites that display a flight) - the same UnboundLocalError-avoidance pattern unknown_prefix/event_recorded already use in this function"
    - "Spy on the real render.build_canvas() call (not just the returned result dict) when a test needs to prove two branches render with the identical resolved value, catching a metadata/render divergence a dict-only assertion would miss"

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "The hold early-return's build_canvas() call, which never previously passed theme_id (the parameter is documented as ignored for quiet_hours/display_off states), now passes theme_id=theme_id explicitly - a behaviourally-inert addition made so the acceptance criteria's exact-count check (4 flight-less call sites, all literally theme_id=theme_id) holds and the 'every non-flight call site passes the bare base theme, explicitly' pattern reads uniformly across all four sites."
  - "The both-branches invariant check (14-VALIDATION.md row 8) spies on the real render.build_canvas() call and asserts the captured theme_id kwarg, not just run_once()'s returned effective_theme field - a metadata/render divergence (correct resolver call, but a stray theme_id=theme_id at the actual build_canvas() call) would otherwise pass a dict-only check while still painting the wrong colour."

requirements-completed: []

coverage:
  - id: D1
    description: "run_once() resolves the effective theme via colour_rules.resolve_effective_theme_id() at exactly the two build_canvas() call sites that display a flight (flight-detected and held/re-render), leaving the four flight-less call sites on the bare base theme"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#the both-branches invariant / the three flight-less call site checks (checks 51-54)"
        status: pass
      - kind: unit
        ref: "grep -c acceptance criteria on server/poll_loop.py (theme_id=theme_id==4, theme_id=effective_theme_id==2, resolver calls==2, priming call==1, build_canvas calls==6)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The identical flight, redrawn by the battery-transition path, reports and renders with the identical effective theme it got on the cycle that first displayed it"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a battery-icon repaint of the same flight ... reports the identical effective_theme (check 51)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Direction sensitivity (arrivals override applies only to a detected arriving flight) proved end to end through the real poll loop"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#with no rule but an arrivals override configured ... (check 55)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The colour-rules registry is primed once per cycle from the cycle's own state_dir, so a rule added between two cycles is picked up by the next cycle"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a colour rule added to the state dir AFTER one run_once() cycle ... (check 56)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 03: D-13 Resolver Wiring Summary

**Wired `colour_rules.resolve_effective_theme_id()` into `run_once()`'s two flight-displaying render branches, proving a battery-icon repaint can never flip a displayed flight's colour.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-06T16:58Z (base commit `068ac200`)
- **Completed:** 2026-09-06T17:15:35+02:00
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments

- `run_once()` primes the colour-rules registry cache exactly once per cycle, beside the existing `illustrations`/`manual_resolutions` priming pair
- `effective_theme_id` defaults to the base theme and is reassigned only immediately before the flight-detected branch's confirmed-state `build_canvas()` call and the held/re-render branch's confirmed-state `build_canvas()` call — the two, and only two, call sites that display a flight
- The other four `build_canvas()` call sites (both empty states, both hold screens) are left passing the bare base `theme_id`, verbatim
- Both of `run_once()`'s result dicts and its per-cycle log line now carry `effective_theme`
- `server/test_poll_loop.py` gained 6 checks (64 → 70) proving: the both-branches invariant (spied at the real render call, not just the returned dict), all three flight-less call sites ignore a configured rule and arrivals override, direction sensitivity end to end, and per-cycle registry priming

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire the resolver into run_once()'s two flight-displaying render branches (D-13)** - `052ce6f` (feat)
2. **Task 2: Extend server/test_poll_loop.py with the both-branches invariant and the flight-less-sites check** - `a942432` (test)

_Note: no plan-metadata commit is made in worktree mode — the orchestrator commits shared docs (STATE.md/ROADMAP.md) centrally after merge; this SUMMARY.md is committed by the finishing step below._

## Files Created/Modified

- `server/poll_loop.py` - imports `colour_rules`; primes its registry cache once per cycle; defaults `effective_theme_id = theme_id` immediately after the base theme read (never resolved there, per Pitfall 1); resolves the effective theme at the flight-detected and held/re-render `build_canvas()` call sites only; reports `effective_theme` in both result dicts and the log line
- `server/test_poll_loop.py` - 6 new checks (both-branches invariant, three flight-less call-site checks, direction sensitivity, per-cycle priming); `EXPECTED_CHECK_COUNT` 64 → 70

## Decisions Made

- The hold early-return's `build_canvas()` call previously passed no `theme_id` at all (the parameter is ignored for `quiet_hours`/`display_off` states per `render.build_canvas()`'s own docstring). Added an explicit `theme_id=theme_id` there — behaviourally inert, but it makes the "every flight-less call site passes the bare base theme, explicitly" pattern hold uniformly across all four such sites and satisfies the plan's pinned exact-count acceptance criterion (`grep -c "theme_id=theme_id"` == 4).
- The both-branches invariant test (row 8) spies on the real `render.build_canvas()` call and asserts against the captured `theme_id` keyword argument, in addition to `run_once()`'s returned `effective_theme` field. A dict-only assertion would not have caught the acceptance criteria's own deliberate-break scenario (reverting one `theme_id=effective_theme_id` call site back to `theme_id=theme_id` while the resolver call above it stays in place) — that specific mutation leaves the returned metadata correct while silently painting the wrong colour. The spy-based check catches exactly this class of bug and was verified live: temporarily reverting the held branch's call site to `theme_id=theme_id` made the harness fail 69/70 with only the both-branches check failing (reason: "reported effective_theme='black' but actually called render.build_canvas() with theme_id='white'"); restoring it returned the suite to 70/70.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made the hold early-return's `build_canvas()` call explicitly pass `theme_id=theme_id`**
- **Found during:** Task 1 acceptance-criteria verification
- **Issue:** The plan's read_first/action sections assumed the hold early-return call already passed `theme_id=theme_id` (grouping it with the other three flight-less sites as "left untouched, with theme_id=theme_id exactly as it stands today"). The actual pre-existing code passed no `theme_id` argument at all there — `render.build_canvas()` documents `theme_id` as ignored for `quiet_hours`/`display_off` states, so the original author omitted it. This left the plan's pinned acceptance criterion (`grep -c "theme_id=theme_id" server/poll_loop.py` == 4) unsatisfiable without a small addition.
- **Fix:** Added `theme_id=theme_id` to that one call site. No behavioural change (the parameter is ignored for both hold states this call ever renders), but it makes the four flight-less call sites' code shape genuinely uniform and satisfies the acceptance criterion.
- **Files modified:** server/poll_loop.py
- **Verification:** `server/test_poll_loop.py` and `server/test_render.py` both pass unchanged (64/64 and 134/134 respectively, pre-Task-2); the four acceptance-criteria greps all return their pinned counts.
- **Committed in:** `052ce6f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking - a plan/codebase drafting mismatch, resolved without changing any rendered behaviour)
**Impact on plan:** No scope creep; the fix is purely additive and behaviourally inert, made solely to satisfy a pinned acceptance criterion the plan's own narrative had assumed was already true.

## Issues Encountered

- The plan's own suggested deliberate-break test ("change one of the two `theme_id=effective_theme_id` arguments back to `theme_id=theme_id`, confirm the harness fails") would NOT have been caught by a both-branches check that only inspects `run_once()`'s returned `effective_theme` dict field — that field is assigned by the resolver call immediately above the `build_canvas()` call and stays correct even if the `build_canvas()` argument itself is reverted, since they are, by construction, the same local variable unless the two are deliberately desynchronised. Resolved by rewriting the check to spy on the real `render.build_canvas()` call (mirroring check 5's existing spy pattern in the same file) and assert on the captured `theme_id` kwarg directly, then re-verifying the deliberate-break scenario actually fails the harness as the plan's acceptance criteria require.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The D-13 resolution seam is live in `run_once()`: any rule saved through the (not-yet-built) companion UI, and the `theme_arriving` override delivered by 14-02, now reach the panel for a displayed flight, and only for a displayed flight.
- Plans 14-04 (Settings UI for `theme_arriving`) and 14-05 (Settings UI for the rules registry) can build directly on this wiring - no further `poll_loop.py` changes are needed for either to take visible effect on the next poll cycle.
- `server/test_poll_loop.py`'s `EXPECTED_CHECK_COUNT` is now 70; any future plan extending this harness must re-derive the count by running it, not by arithmetic.
- Full suite verified green: `scripts/run-all-tests.sh` exits 0, 18/18 harnesses, coverage 92% (unchanged from the wave-1 baseline).

---
*Phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link*
*Completed: 2026-09-06*
