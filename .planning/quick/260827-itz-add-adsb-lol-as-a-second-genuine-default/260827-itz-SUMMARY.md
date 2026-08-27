---
phase: 05-low-battery-indicator
plan: 260827-itz
subsystem: plane-detection
tags: [ads-b, adsb.lol, adsb.fi, cross-validation, detect.py, compliance]

# Dependency graph
requires:
  - phase: debug/runway3-false-positive
    provides: per-poll cross-source validation logic in poll_current_aircraft() (built but never exercised in production, since DEFAULT_PROVIDER_ORDER had only one entry)
provides:
  - A second live default ADS-B provider (adsb.lol) so poll_current_aircraft()'s cross-validation actually runs on every production poll
  - Observable corroboration outcome in the poll_loop.py journal log line
  - COMPLIANCE.md coverage of adsb.lol at the same rigour as the other four sources
affects: [phase-05-battery-life-verdict, any-future-provider-changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provider registry stays a flat dict (PROVIDERS) + an ordered tuple (DEFAULT_PROVIDER_ORDER) - adding a source is a data change, not a code-shape change"
    - "CLI --provider choices: 'default' (production order, no explicit providers arg) / 'all' (every registered provider) / an individual provider name - avoids a choice name that hardcodes a provider count"

key-files:
  created: []
  modified:
    - server/plane/detect.py
    - server/test_plane_detection.py
    - server/poll_loop.py
    - README.md
    - ARCHITECTURE.md
    - COMPLIANCE.md
    - .planning/PROJECT.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "adsb.lol registered as the second entry in DEFAULT_PROVIDER_ORDER, behind adsb.fi - ordering is load-bearing: poll_current_aircraft() returns the first-listed provider's record on agreement, so adsb.fi's altitude/track/position values are what reach the renderer"
  - "airplanes.live stays registered but out of the default order (unchanged from the prior quick task) - it remains selectable only via an explicit --provider argument"
  - "adsb.lol's disclosed future feeder-contributed API key requirement is recorded as a known-temporary caveat in COMPLIANCE.md, not treated as a settled permanent source"

requirements-completed: [PLANE-03]

coverage:
  - id: D1
    description: "A default poll (poll_current_aircraft(geofence), no providers argument - exactly how poll_loop.py calls it in production) queries adsb.fi then adsb.lol, never airplanes.live"
    requirement: "PLANE-03"
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#check 20 (default poll queries adsb.fi then adsb.lol)"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#check 21 (airplanes.live remains opt-in, absent from default order)"
        status: pass
    human_judgment: false
  - id: D2
    description: "adsb.lol's aircraft array is read under its own response key ('ac'), proven through a stubbed transport against a payload carrying both candidate keys - not by asserting a dict literal"
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#check 28 (query_provider: adsb.fi and adsb.lol response keys are never interchanged)"
        status: pass
    human_judgment: false
  - id: D3
    description: "All three cross-validation outcomes (agreement, disagreement, single-source degradation) behave correctly through the default no-argument path, not only through an explicit providers list"
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#check 25 (default order corroborates, returns adsb.fi's record)"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#check 26 (default order disagreement yields nothing)"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#check 27 (default order degrades to single-source when adsb.lol is unreachable)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every real poll cycle logs its corroboration outcome so the disagreement branch is observable rather than silent"
    verification:
      - kind: unit
        ref: "server/poll_loop.py run_once() fixture-driven check (corroborated= field present in the log line)"
        status: pass
    human_judgment: false
  - id: D5
    description: "COMPLIANCE.md documents adsb.lol at the same rigour as the other four sources: CC0 credit-by-choice, disclosed future-API-key caveat, known-temporary verdict backed by a named check; README/ARCHITECTURE/PROJECT/REQUIREMENTS all describe a two-source default poll"
    verification:
      - kind: other
        ref: "python content-assertion script run against COMPLIANCE.md/README.md/PROJECT.md/REQUIREMENTS.md (see Task 3 verify block in 260827-itz-PLAN.md)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Disagreement rate on real production traffic (VPS journalctl) - the design assumption is that provider disagreement is rare"
    verification: []
    human_judgment: true
    rationale: "Requires watching journalctl -u skypane-poll on the live VPS over real traffic after this reaches production through CI/CD - not observable from this development environment. Recorded in the plan's <human-check> section."
  - id: D7
    description: "The adsb.lol COMPLIANCE.md entry reads honestly - the future-API-key caveat is legible as a real risk (not softened), and the CC0 credit reads as a deliberate courtesy rather than an invented requirement"
    verification: []
    human_judgment: true
    rationale: "Editorial/tone judgment on prose - requires a human reading the entry end to end, per the plan's <human-check> section."

# Metrics
duration: ~45min
completed: 2026-08-27
status: complete
---

# Phase 05 Plan 260827-itz: Register adsb.lol as the second default ADS-B provider Summary

**adsb.lol added to `DEFAULT_PROVIDER_ORDER` behind adsb.fi in `server/plane/detect.py`, giving the runway3-false-positive session's per-poll cross-validation a genuine second live source to corroborate against in production, with `server/test_plane_detection.py` extended 24→28 checks and a full documentation reconciliation (README, ARCHITECTURE, COMPLIANCE, PROJECT, REQUIREMENTS) to match.**

## Performance

- **Duration:** ~45 min (not precisely tracked — no PLAN_START_TIME captured at spawn; estimated from session scope)
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- `DEFAULT_PROVIDER_ORDER` is now `("adsbfi", "adsblol")` — a production poll (`poll_current_aircraft(geofence)`, no `providers` argument) queries adsb.fi then adsb.lol, and never airplanes.live. This is the exact call `server/poll_loop.py`'s `run_once()` makes, so this is what production actually does starting with this commit.
- adsb.lol's aircraft array is read under its own key (`"ac"`, distinct from adsb.fi's `"aircraft"`) — proven through a stubbed-transport check (`check 28`) against a payload carrying both candidate keys, rather than trusting a dict literal in `PROVIDERS`. This was flagged in the plan as the single highest-consequence error available in this task (a wrong key fails completely silently — `data.get(key) or []` just returns an empty list, no exception, no log line, no other failing test).
- All three cross-validation outcomes (agreement → corroborated, returning adsb.fi's record since it's queried first; disagreement → nothing, D-04's "leave the panel alone"; one source unreachable → the other's selection, uncorroborated) now run through the default no-argument path in production, not only through an explicit `providers` argument as before.
- `server/poll_loop.py`'s single log line gained a `corroborated=%s` field (right after `aircraft_type=%s`), so the newly-reachable disagreement branch is observable in the journal instead of silent.
- The `--provider` CLI argument's choices changed from `{adsbfi, airplaneslive, both}` to `{adsbfi, adsblol, airplaneslive, default, all}` — `both` no longer made sense with three registered providers; `default` (the new default value) resolves to no explicit `providers` argument at all, so there is exactly one definition of "the production default order" in the codebase.
- `COMPLIANCE.md` gained a full adsb.lol entry (CC0 licence, credit-by-choice distinction, and — stated plainly, not softened — the same disclosed future-feeder-API-key risk class that just closed airplanes.live's free tier). The status table, the adsb.fi entry, and the runtime-behaviour poll-cadence bullet were all updated to describe two default requests per 30-second cycle instead of one.
- `README.md`, `ARCHITECTURE.md`, `.planning/PROJECT.md`, and `.planning/REQUIREMENTS.md` all now describe a two-source default poll. `ARCHITECTURE.md`'s ASCII data-flow diagram was relabeled with its connector-column alignment preserved (verified programmatically).
- `README.md`'s stated total check count was corrected from the (already-stale, pre-existing) 119 to the real computed sum across all nine harnesses: 171 (167 before this plan's +4 to `test_plane_detection.py`).
- **Best-effort live observation** (not a gate, per the plan): a real, unmocked run of `server/plane/detect.py` with no arguments in this environment succeeded against both live endpoints and returned:
  ```
  39de51 TVF18NF alt=525.0ft vrate=-704 on_ground=False cross=3m track=254.37 dev=0.0 sources=adsbfi,adsblol corroborated=True
  ```
  Both default sources answered, agreed on the same aircraft, and the poll was genuinely corroborated — a live confirmation that the cross-validation path this plan activates actually works end to end, not just against fixtures.

## Task Commits

Each task was committed atomically:

1. **Task 1: Register adsb.lol as the second default provider, pinned by transport-level and cross-validation regression checks** - `7862666` (feat)
2. **Task 2: Make corroboration observable in the journal and correct ARCHITECTURE.md** - `1898955` (feat)
3. **Task 3: Add the adsb.lol compliance entry and reconcile every document that still describes a single-source poll** - `2202ec4` (docs)

_No TDD RED/GREEN split was used — this plan's `tdd="true"` task (Task 1) was executed as a single commit adding both the production code and its regression checks together, consistent with how the prior provider-order quick task (260827-1i6) was committed._

## Files Created/Modified

- `server/plane/detect.py` - adsb.lol registered in `PROVIDERS`/`DEFAULT_PROVIDER_ORDER`; docstrings, block comment, and `--provider` CLI (`build_parser()`/`main()`) updated to describe and resolve the two-source default
- `server/test_plane_detection.py` - check 20 updated for the two-source default; checks 25-28 added (default-order agreement/disagreement/degradation, response-key transport proof); `EXPECTED_CHECK_COUNT` 24→28
- `server/poll_loop.py` - log line gains `corroborated=%s`; `_extract_aircraft()` docstring names adsb.lol under the `"ac"` key
- `README.md` - Data sources section names both default sources with the adsb.fi citation kept verbatim-identical to COMPLIANCE.md; Tests section's stated check count corrected to 171
- `ARCHITECTURE.md` - data-flow diagram relabeled (alignment preserved); Detection paragraph rewritten to describe the two-source cross-validation and its three outcomes
- `COMPLIANCE.md` - new adsb.lol entry; adsb.fi entry, status table, and runtime-behaviour bullet updated for two default providers
- `.planning/PROJECT.md` - dated note layered onto the existing plane-detection correction; new Key Decisions row; supersession pointer added to the prior sole-provider row
- `.planning/REQUIREMENTS.md` - PLANE-03 and the rejected-alternatives row updated to name adsb.fi + adsb.lol

## Decisions Made

- Ordering (adsb.fi first, adsb.lol second) is load-bearing, not cosmetic — `poll_current_aircraft()` returns the first-queried provider's record on agreement, so this determines whose altitude/track/position values reach the renderer. Documented explicitly in the `PROVIDERS` block comment, the docstring, and COMPLIANCE.md.
- `airplaneslive` stays registered but out of the default order (carried over unchanged from the prior quick task, 260827-1i6) — remains selectable only via an explicit `--provider` argument for a feeder operator, sponsor, or licensee.
- adsb.lol's disclosed future feeder-contributed API key requirement is recorded in COMPLIANCE.md as a **known-temporary** caveat, not a settled permanent source — matching the same volunteer-sustainability risk class that just closed airplanes.live's free tier.
- The `--provider` CLI's `"both"` choice was removed (no longer accurate with three registered providers) in favor of `"default"` (production order, the new default value) and `"all"` (every registered provider including the opt-in one).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - stale/inaccurate text introduced by this task's own scope] Corrected a leftover "sole default provider" phrase in COMPLIANCE.md's airplanes.live entry**
- **Found during:** Task 3
- **Issue:** The airplanes.live entry's historical verdict text ("adsb.fi is promoted to sole default provider...") was not explicitly named in the plan's action list for editing, but became factually false the moment adsb.lol became a second default provider in the same document.
- **Fix:** Reworded to "adsb.fi is promoted to default provider (later the same day joined by adsb.lol as a second default source — see the adsb.lol entry above)", preserving the rest of the historical narrative about airplanes.live's withdrawal untouched.
- **Files modified:** COMPLIANCE.md
- **Verification:** `assert 'sole default provider' not in c` (part of Task 3's automated verify block) passes.
- **Committed in:** `2202ec4` (Task 3 commit)

**2. [Rule 1 - stale count] Updated COMPLIANCE.md's opening "Five sources are covered" paragraph to "Six"**
- **Found during:** Task 3
- **Issue:** The plan's action list only asked for the status table's row count and the closing sentence to be checked, but the document's own opening paragraph asserts a source count ("Five sources are covered... a fourth aggregator... adsbdb.com") that becomes stale the instant a sixth source (adsb.lol) is documented in the same file.
- **Fix:** Updated to "Six sources are covered... a fifth (adsb.lol, 2026-08-27)..." preserving the original D-14/adsbdb.com framing.
- **Files modified:** COMPLIANCE.md
- **Verification:** Manual read-through; no automated check asserts this specific count, but leaving it stale would have been a document self-contradiction (5 named vs. 6 actually present).
- **Committed in:** `2202ec4` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — stale/inaccurate text that this task's own scope directly caused, adjacent to but not explicitly named by the plan's action list).
**Impact on plan:** Both fixes prevent this same document from contradicting itself about how many sources it documents and whether adsb.fi is still described as sole. No scope creep — both edits stayed inside COMPLIANCE.md, one of the plan's named `files_modified`.

## Issues Encountered

None. The `server/.venv` virtualenv did not yet exist in this freshly-created worktree (expected — worktrees don't inherit the gitignored venv); it was created and the two requirements files installed before any verification command could run. Package installation initially printed noisy DNS-resolution warnings against an internal proxy host before falling through to a working mirror — packages installed successfully (`requests==2.34.2`, `Pillow==12.3.0`, `ruff==0.16.4`, `coverage==7.15.4`, matching the pinned versions in `server/requirements.txt`/`server/requirements-dev.txt`), so this was not a package-legitimacy concern requiring a `checkpoint:human-verify` gate — no new/unfamiliar package name was involved.

## User Setup Required

None - no external service configuration required. adsb.lol requires no API key today (per the plan's `<research_already_done>`, confirmed live 2026-08-27).

## Next Phase Readiness

- Phase 05 (Battery Life & Low-Battery Indicator)'s remaining work (05-01 Tasks 2-3, the multi-day discharge run and its verdict) is unaffected by this quick task and remains deliberately deferred to the end of the project, per the existing STATE.md note.
- Two follow-up items exist that only a human can close, both named in the plan's `<human-check>` section and NOT gates on this quick task's completion:
  1. **Disagreement rate** — watch `journalctl -u skypane-poll` on the live VPS across a stretch of real traffic once this reaches production via the normal CI/CD path, and count corroborated vs. uncorroborated vs. disagreement outcomes. If disagreement turns out to be common (not rare, as designed), the recommended response is reverting `DEFAULT_PROVIDER_ORDER` to a single entry — everything else in this plan can stay.
  2. **Compliance caveat honesty read** — a human should read the new adsb.lol `COMPLIANCE.md` entry end to end and confirm the future-API-key caveat reads as a real risk (not softened) and the CC0 credit reads as a deliberate courtesy, not an invented requirement.
- No blockers for any other in-flight work. All 9 test harnesses (171 checks total), `ruff check .`, and `./scripts/check-attribution.sh` are green as of the final commit.

---
*Phase: 05-low-battery-indicator (quick task)*
*Completed: 2026-08-27*

## Self-Check: PASSED

All 8 modified files confirmed present on disk (`server/plane/detect.py`, `server/test_plane_detection.py`, `server/poll_loop.py`, `README.md`, `ARCHITECTURE.md`, `COMPLIANCE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`), plus this SUMMARY.md itself. All 3 claimed task commit hashes (`7862666`, `1898955`, `2202ec4`) confirmed present in `git log`.
