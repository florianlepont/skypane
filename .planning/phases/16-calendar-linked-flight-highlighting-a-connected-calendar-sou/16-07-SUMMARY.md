---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 07
subsystem: infra
tags: [poll-loop, calendar, colour-rules, resolver, d-13, throttle]

requires:
  - phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
    provides: "calendar_rules.py (parser, registry, throttle, SSRF-hardened fetch, refresh_calendar_registry(), match_calendar_theme()) and colour_rules.resolve_effective_theme_id()'s calendar_theme_id keyword, delivered by plans 16-01 through 16-06"
provides:
  - "run_once() wired to the calendar source: one throttled refresh per cycle, one match computed from settled inputs at the flight-detected render, persisted alongside last_route, and reused (never recomputed) by the held/repaint branch"
  - "poll_state.json's new last_calendar_theme_id key, membership-tested against device_config.THEMES on read"
  - "10 new end-to-end checks in server/test_poll_loop.py proving the both-branches invariant, D-02 precedence, the flight-less narrowing, CORRECTION 1, T-16-TAMPER, T-16-DOS and the feature-off regression fence"
affects: ["16-secure-phase (closes the phase's threat register)", "any future plan touching poll_loop.py's flight-detected or held/repaint branches"]

tech-stack:
  added: []
  patterns:
    - "Persist-and-reuse for clock-dependent resolver inputs: compute once at the flight-detected render, persist beside the flight it describes, and have the held/repaint branch read the persisted value rather than recompute — the same idiom current_route already used, now generalised to a time-varying input"

key-files:
  created: []
  modified:
    - "server/poll_loop.py — calendar_rules import, one refresh call per cycle, one match call in the flight-detected branch, persisted last_calendar_theme_id read/write, held branch reuse"
    - "server/test_poll_loop.py — 10 new checks (57-66), EXPECTED_CHECK_COUNT 70 -> 80"

key-decisions:
  - "The calendar match is computed exactly once per cycle, at the same point the resolver call already sits in the flight-detected branch (after enrich.resolve_route(), before the first resolve_effective_theme_id() call) — never at the top-of-cycle default-assignment block, for the identical render_state/current_flight-unsettled reason that block's own comment already gives"
  - "The held/repaint branch reuses the persisted last_calendar_theme_id rather than recomputing a fresh match, because a calendar match is the first resolver input that is a function of the clock — recomputing would let a repaint hours later silently change the panel's colour, breaking Phase 15's D-13 both-branches invariant in a way no same-minute test would catch"
  - "last_calendar_theme_id is written on the same lines as last_flight/last_confirmed_state/last_route so the stored calendar value and the stored route can never drift apart and describe two different aircraft"
  - "The refresh call (calendar_rules.refresh_calendar_registry()) is written as its own distinct step immediately after the three pure cache-priming calls, not folded into that list, because unlike those three it may perform network I/O"
  - "No calendar-specific key was added to either result dict or the log line — the existing effective_theme key already reports the outcome, and a visible trace of a match firing is explicitly on the phase's deferred list"

requirements-completed: []

coverage:
  - id: D1
    description: "run_once() refreshes the calendar registry once per cycle and computes exactly one calendar match, from settled route/render_state inputs, in the flight-detected branch"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_calendar_match_survives_a_battery_repaint_past_its_own_window"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py ordering-verification script (prime < refresh < resolver; route < match < resolver; match not hoisted)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The held/repaint branch reuses the persisted calendar match rather than recomputing it, so the same flight redrawn hours later on a battery-icon repaint reports the identical effective_theme (D-13 both-branches invariant, extended to a clock-dependent input)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_calendar_match_survives_a_battery_repaint_past_its_own_window"
        status: pass
    human_judgment: false
  - id: D3
    description: "A calendar match beats a matching exact-callsign rule end to end (D-02), and never leaks onto any of the four flight-less call sites (nothing-ever-detected, held branch's own empty state, hold early-return)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_calendar_match_beats_an_exact_callsign_rule"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#_nothing_ever_detected_ignores_calendar_match"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#_held_branch_with_no_confirmed_state_ignores_calendar_match"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#_hold_early_return_ignores_calendar_match"
        status: pass
    human_judgment: false
  - id: D4
    description: "The narrowing holds end to end: an airline-only enrichment (no cached route, resolved only via the static ICAO-prefix table) never lets a calendar match fire, even against an otherwise-matching entry (CORRECTION 1)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_airline_only_route_never_matches_the_calendar"
        status: pass
    human_judgment: false
  - id: D5
    description: "A hand-edited poll_state.json whose last_calendar_theme_id is not a registered theme falls back to the base theme on the held branch's repaint, never reaching the panel (T-16-TAMPER)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_tampered_last_calendar_theme_id_falls_back_to_base_theme"
        status: pass
    human_judgment: false
  - id: D6
    description: "The refresh never delays or destabilises a cycle: no registry file is created when unconfigured, and ten consecutive throttled cycles leave the registry file byte-identical (T-16-DOS)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_unconfigured_cycle_never_creates_the_registry_file"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#_throttled_cycles_never_rewrite_the_registry_file"
        status: pass
    human_judgment: false
  - id: D7
    description: "With no calendar configured, every pre-phase behaviour (matching-rule cycle, arrivals-override cycle, plain base-theme cycle) is byte-for-byte unchanged, and server/plane/render.py remains untouched across the whole phase"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#_feature_off_leaves_every_pre_phase_behaviour_unchanged"
        status: pass
      - kind: other
        ref: "git log --oneline 7ca5315..HEAD -- server/plane/render.py (empty)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-08
status: complete
---

# Phase 16 Plan 07: Wire the calendar source into run_once() Summary

**One throttled calendar refresh and one clock-anchored calendar-theme match wired into `run_once()`, computed once at the flight-detected render and reused — never recomputed — by the held/repaint branch, preserving Phase 15's D-13 both-branches invariant against the first resolver input that is a function of time.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-08T00:55:00+02:00 (approx.)
- **Completed:** 2026-09-08T01:41:00+02:00
- **Tasks:** 2
- **Files modified:** 2 (`server/poll_loop.py`, `server/test_poll_loop.py`)

## Accomplishments

- `server/poll_loop.py` now imports `server.plane.calendar_rules` and calls `calendar_rules.refresh_calendar_registry(state_dir, now_s())` once per cycle as its own distinct step (not folded into the three pure cache-priming calls, since it may perform network I/O)
- The flight-detected branch computes the phase's single calendar match site — `calendar_rules.match_calendar_theme(calendar_registry, route, render_state, device_cfg, now_s())` — immediately before the existing `colour_rules.resolve_effective_theme_id()` call, after `enrich.resolve_route()` has settled the route
- The computed match is persisted to `poll_state["last_calendar_theme_id"]` on the same lines that write `last_flight`/`last_confirmed_state`/`last_route`, so the two can never drift apart
- The held/repaint branch reads back `last_calendar_theme_id` (membership-tested against `device_config.THEMES`) and passes it into its own `resolve_effective_theme_id()` call — it never calls `match_calendar_theme()` again, which is what makes the both-branches invariant hold by construction rather than by luck
- The four flight-less `build_canvas()` call sites are untouched — they keep passing the bare base `theme_id`, never `effective_theme_id`
- No calendar-specific key was added to either result dict or the log line
- `server/test_poll_loop.py` gained 10 new end-to-end checks (57-66), raising `EXPECTED_CHECK_COUNT` from 70 to 80, re-derived by running the harness

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire the throttled refresh, the match and the persisted reuse into run_once()** - `7814b37` (feat)
2. **Task 2: Extend server/test_poll_loop.py with the end-to-end calendar checks and the both-branches invariant** - `1af71cb` (test)

_No plan-metadata commit yet — this SUMMARY.md and the STATE.md/ROADMAP.md updates are the orchestrator's responsibility per this plan's execution contract (wave close-out commit made separately, not by this executor)._

## Files Created/Modified

- `server/poll_loop.py` - calendar_rules import; one refresh call per cycle; one match call in the flight-detected branch; persisted `last_calendar_theme_id` read (membership-tested) and write; held branch reuses the persisted value
- `server/test_poll_loop.py` - 10 new checks covering the both-branches invariant, D-02 precedence, the three flight-less call sites, CORRECTION 1's narrowing, T-16-TAMPER, T-16-DOS, and an explicit feature-off regression fence; `EXPECTED_CHECK_COUNT` 70 → 80

## Decisions Made

- The calendar match is computed at the exact point the existing resolver call already sits in the flight-detected branch — never hoisted to the top-of-cycle `effective_theme_id` default-assignment block, whose own comment already explains why (`render_state`/`current_flight` unsettled that early); extended that comment with two sentences naming the calendar match explicitly rather than duplicating the reasoning elsewhere
- The held/repaint branch reuses `current_calendar_theme_id` (read from `poll_state` beside `current_route`) rather than calling `match_calendar_theme()` a second time — a calendar match is the first resolver input that is a function of the clock, so recomputing it here would let a repaint hours after the flight was first displayed fall outside the calendar entry's own time window and silently change the panel's colour, which is exactly the divergence D-13/T-15-10 exist to forbid
- `last_calendar_theme_id` is written on the same lines as `last_flight`/`last_route` (not a separate write elsewhere in the function) so the two values can never describe two different aircraft
- Chose realistic test fixtures (TVF/TO Transavia France, ORY-NCE) matching the exact ICAO/IATA pair and route already cited in `calendar_rules.py`'s own docstring and `16-CONTEXT.md`'s measured findings, rather than inventing a fictitious carrier
- Used `poll_state["enrichment_cache"]` pre-seeding (the same `{"found": True, ...}` shape `enrich.lookup_route()`'s cache-hit path produces) to exercise a real `cache_hit` route with `origin_iata`/`destination_iata`/`callsign_iata` populated, without any live network call

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned a `server/.venv` for this worktree**

- **Found during:** Task 1 verification (running `server/test_poll_loop.py`)
- **Issue:** This worktree had no `server/.venv` — the plan's own verification commands (`server/.venv/bin/python3 ...`) require one, and this sandbox has no network access to `pip install` the pinned `requests`/`Pillow` versions
- **Fix:** Symlinked `server/.venv` to the main checkout's already-built venv at `/Users/florian/Projects/skypane/server/.venv` (exact-version match: `requests==2.34.2`, `Pillow==12.3.0`), following the exact network-free bootstrap route the repo-root `.gitignore` already documents and accounts for (phase 14 plan 14-01 Task 1's own comment: "a worktree that provisions `server/.venv` as a symlink to another checkout's already-built venv")
- **Files modified:** none tracked — `server/.venv` is gitignored by name (`/server/.venv` in the repo-root `.gitignore`) regardless of whether it is a real directory or a symlink
- **Verification:** `server/.venv/bin/python3 -c "import requests, PIL"` succeeds with the exact pinned versions; full suite subsequently runs and passes
- **Committed in:** n/a (untracked, gitignored — no commit)

**2. [Rule 1 - Bug, self-caught during authoring] Two ordering-count-affecting comment phrasings**

- **Found during:** Task 1's own acceptance-criteria self-check (the plan's `grep -c` counted-call-site criteria)
- **Issue:** Two doc comments I wrote (extending the ordering-trap comment, and the held-branch's own comment) happened to spell out `calendar_rules.match_calendar_theme()` and `colour_rules.resolve_effective_theme_id()` with trailing parentheses, which inflated the plan's own `grep -c "...("` counted criteria from the required 1/2 to 3/3
- **Fix:** Reworded both comments to reference the function by name without the call-syntax parentheses (e.g. "calendar_rules's match_calendar_theme function"), preserving the same explanatory content
- **Files modified:** `server/poll_loop.py`
- **Verification:** All of the plan's `grep -c` acceptance criteria (`match_calendar_theme(` == 1, `refresh_calendar_registry(` == 1, `resolve_effective_theme_id(` == 2, `calendar_theme_id=` >= 2) now match exactly
- **Committed in:** `7814b37` (part of Task 1's commit — caught before committing)

---

**Total deviations:** 2 (1 blocking/environment, 1 self-caught authoring correction)
**Impact on plan:** Neither affects the shipped behavior. The venv symlink is a local test-running convenience with a documented precedent in this exact repo; the comment rewording is purely textual.

## Issues Encountered

None beyond the two items above.

## User Setup Required

None - no external service configuration required. (The calendar feature's own `SKYPANE_CALENDAR_ICS_URL` environment variable was already documented by plan 16-04/16-05; this plan wires the already-built pieces together and adds no new operator-facing configuration.)

## Next Phase Readiness

- This is the phase's last code plan. `/gsd-secure-phase 16` is the mandatory next step, consolidating the `T-16-*` threat register across all seven plans (`.planning/ROADMAP.md` § Phase 16, "Closes with").
- Verified phase-wide (not just this plan): `git log --oneline 7ca5315..HEAD -- server/plane/render.py` is empty (D-07 standing gate holds across the whole phase, not only this plan) and `git diff 7ca5315..HEAD -- server/requirements.txt server/requirements-dev.txt` is empty (no new dependency anywhere in the phase). `7ca5315` is phase 16's own start commit ("docs: add Phase 16 ... promoted from SEED-003"); this repo's `main` ref is far behind that point (multiple earlier, still-unmerged phases), so `git merge-base HEAD main` is not a reliable stand-in for "the start of phase 16" in this environment — the phase-start-commit comparison above is the trustworthy one.
- `scripts/run-all-tests.sh` passes all 19 harnesses under coverage at 92% (floor is 83%), and `ruff check` on the touched files is clean.
- No on-glass verification is expected or needed — a calendar match resolves to an already-registered theme id, so nothing new reaches the panel (same D-07 reasoning Phase 15 established, confirmed again in `16-VALIDATION.md`).
- Two manual-only items remain, per `16-VALIDATION.md` § Manual-Only Verifications and this plan's own `<human-check>` block: the Settings surface (already covered by plan 16-05's own verification), and an opportunistic (non-blocking) real end-to-end match — the latter is explicitly not a phase gate given how rarely a match is expected to fire in practice.

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Completed: 2026-09-08*

## Self-Check: PASSED

- FOUND: server/poll_loop.py
- FOUND: server/test_poll_loop.py
- FOUND: commit 7814b37 (Task 1)
- FOUND: commit 1af71cb (Task 2)
