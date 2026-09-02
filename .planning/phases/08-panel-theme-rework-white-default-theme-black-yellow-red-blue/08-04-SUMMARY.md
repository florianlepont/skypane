---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 04
subsystem: rendering
tags: [pillow, content-ladder, callsign-iata, render, cli]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 02
    provides: "callsign_iata threaded through enrich.py's route dict (all three builders agree on the key)"
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 03
    provides: "PT Serif Bold active-state fonts and the removed text-backing-plate, which this plan's text blocks draw onto unchanged"
provides:
  - "server.plane.render._flight_line1_text() as a four-tier content ladder (D-08/D-09/D-10) - the raw ADS-B ICAO callsign is structurally unreachable at any tier"
  - "draw_main_text_block()/draw_previous_text_block() both independently omit line 1 and promote line 2 when the ladder returns the tier-3 sentinel"
  - "PREVIOUS_TEXT_LEFT_OFFSET_PX = 20 (D-12): the previous card's optical alignment correction"
  - "render.py --no-identifier CLI flag, plus real callsign_iata values on both CLI preview routes - all four tiers are one copy-pasteable command for plan 08-06"
affects: [08-05, 08-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sentinel-return content ladder: a private text-derivation function returns \"\" (not None) to signal 'omit this element', and each of the (possibly multiple, independently-positioned) draw call sites checks that sentinel itself rather than sharing a drawing helper - because the call sites are not otherwise interchangeable (different gap constants, different anchor edges)."

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "The optical-offset constant is named PREVIOUS_TEXT_LEFT_OFFSET_PX (contains both PREVIOUS and OFFSET per the plan's discretion clause), placed beside PREVIOUS_TEXT_GAP_PX with a comment recording the zero-delta pixel-instrumentation finding, the raked-tail-fin-tip rationale, and the 15px-to-20px live iteration."
  - "The new CLI flag is named --no-identifier (mirrors --no-route's naming), and strips callsign_iata from whichever preview route is in play rather than adding a separate tier-2-specific route dict."
  - "_PREVIEW_ROUTE gets callsign_iata='AF1006' (Air France's real IATA prefix, synthetic value); _PREVIEW_PREVIOUS_ROUTE gets 'VY1234' (Vueling's real IATA prefix, synthetic value)."
  - "TEST_ROUTE gets callsign_iata='TO16VB' - the REAL value from server/fixtures/adsbdb_hit_TVF16VB.json, not synthetic, so the default test render exercises tier 1 against a genuine adsbdb value. TEST_PREVIOUS_ROUTE gets 'VY8163' and TEST_LONG_ROUTE gets 'AT9051', both synthetic IATA-format values in their airline's real prefix, marked as such in comments."
  - "Three pre-existing checks whose assertions directly contradicted the new D-08 guarantee (the enrichment-miss check, the two airline-only-route checks, and the --no-route CLI check) were corrected as Rule 1 fixes even though they weren't among the plan's literal 'seven' - they tested behavior Task 1's rewrite necessarily changed, and leaving them unfixed would have left the suite red or (worse) still asserting the raw callsign is expected output."

requirements-completed: [D-08, D-09, D-10, D-12]

coverage:
  - id: D1
    description: "_flight_line1_text() evaluates the four-tier content ladder in order (identifier+city, city-only, airline-only, nothing-resolved) and never returns the raw ADS-B callsign at any tier, including every hostile-input degradation path"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "server/test_render.py#_tier1_identifier_and_city_both_known"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_tier2_city_known_no_identifier"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_tier3_airline_only_returns_empty_string"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_tier4_nothing_resolved_returns_title_case_state_word"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_hostile_route_shapes_degrade_a_tier_without_raising"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_d08_no_raw_callsign_or_hex_anywhere_across_all_tiers"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_cli_never_draws_raw_callsign_across_all_four_tiers"
        status: pass
      - kind: other
        ref: "deliberate fifth-tier bare-callsign regression added to _flight_line1_text(), suite run, one failure observed naming the tier-4 check, reverted before commit - see below for the observed message"
        status: pass
    human_judgment: false
  - id: D2
    description: "callsign_iata (D-09, threaded by plan 08-02) is consumed by exactly the tier-1 identifier slot, and enrich.city_for_state() is read through a guarded, never-raising path"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "server/test_render.py#_tier1_identifier_and_city_both_known"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both draw_main_text_block() and draw_previous_text_block() independently omit line 1 and promote line 2 into its slot when the ladder returns the tier-3 sentinel, each using its own gap constant"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "server/test_render.py#_tier3_promotion_on_main_card"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_tier3_promotion_on_previous_card"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_tier3_on_both_cards_simultaneously"
        status: pass
      - kind: other
        ref: "deliberate half-applied fix: omitted-line branch removed from draw_previous_text_block() only, suite run, the previous-card-specific check (and the both-cards check) failed as designed, reverted before commit - see below for the observed message"
        status: pass
    human_judgment: false
  - id: D4
    description: "The previous card's two text lines are right-aligned PREVIOUS_TEXT_LEFT_OFFSET_PX (20px) left of the aircraft's measured opaque right edge; the main card receives no equivalent offset"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "server/test_render.py#_previous_card_and_text_align_to_the_main_aircrafts_visible_right_edge"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_previous_card_both_lines_share_one_anchor_at_the_optical_offset"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_main_card_text_remains_centred_not_offset"
        status: pass
      - kind: manual_procedural
        ref: "server/plane/render.py --state departing --callsign AF1380 --previous-callsign VY1234 --preview /tmp/08-04-tier1.png, compared against .planning/spikes/001-panel-theme-colours/renders/97-prev-text-nudged-left-20px.png"
        status: pass
    human_judgment: false
  - id: D5
    description: "All four content-ladder tiers are reachable as a single command against the production render.py CLI, for plan 08-06's on-glass session"
    verification:
      - kind: integration
        ref: "server/test_render.py#_cli_default_preview_draws_tier1_with_identifier"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_cli_no_identifier_flag_forces_tier2"
        status: pass
      - kind: integration
        ref: "server/test_render.py#_cli_no_identifier_is_a_noop_with_no_route_and_airline_only"
        status: pass
    human_judgment: false

# Metrics
duration: ~7min (commit span; wall time longer - see Issues Encountered)
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 04: The four-tier flight-identifier content ladder Summary

**`_flight_line1_text()` rewritten as a four-tier content ladder (identifier+city, city-only, airline-only-omit-line-1, nothing-resolved) that structurally cannot reach the raw ADS-B callsign, both drawing functions independently promote line 2 when line 1 is omitted, and the previous card's text gets a developer-confirmed 20px optical left-offset (D-12) - all four tiers now reachable as a single `render.py` CLI command.**

## Performance

- **Duration:** ~7min (commit span, three atomic task commits between 12:23 and 12:29 local time); wall time including reads, planning, and mid-session recovery from an accidental `git checkout --` was substantially longer
- **Tasks:** 3
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py` - exactly the plan's stated `files_modified`)

## Accomplishments

- `_flight_line1_text()` deletes the `flight.get("callsign") or hex or "?"` derivation outright - there is no path back to the raw callsign at any tier, including every hostile-input case (non-dict route, non-string/empty/whitespace `callsign_iata`, a route whose `.get()` raises).
- Tier 1 (`"{identifier} to|from {city}"`) reads `route["callsign_iata"]` (D-09) and `enrich.city_for_state()`; tier 2 (`"To|From {city}"`, title-case) fires when only a city is known; tier 3 returns `""` - the sentinel meaning line 1 is omitted entirely - when only the airline is known; tier 4 returns the title-case state word (`"Departing"`/`"Arriving"`) when nothing resolved, deliberately distinct from the all-caps top-left label.
- `draw_main_text_block()` and `draw_previous_text_block()` both independently check the tier-3 sentinel and skip line 1's font/bbox/draw, promoting line 2 into line 1's y-position using each function's own gap expression (`content[3] + {MAIN,PREVIOUS}_TEXT_GAP_PX`) - implemented twice on purpose, since the two functions position line 2 from opposite edges of line 1 (bottom vs. top) and a shared helper would obscure that asymmetry.
- New `PREVIOUS_TEXT_LEFT_OFFSET_PX = 20` constant (D-12): `draw_previous_text_block()`'s `right_x` is now `prev_placement.content[2] - PREVIOUS_TEXT_LEFT_OFFSET_PX`, feeding both lines' anchor and narrowing `fit_text_size()`'s budget as a documented harmless side effect. The main card's `center_x` is untouched.
- `render.py`'s CLI gained `--no-identifier` (strips `callsign_iata` to force tier 2; a documented no-op when combined with `--no-route` or `--preview-airline-only`) and both preview routes gained synthetic `callsign_iata` values, so all four tiers are now one command each - recorded verbatim below for plan 08-06.
- `server/test_render.py` grew 82→97 checks across the three tasks (Task 1: +6, Task 2: +5, Task 3: +4), reconciled all seven pre-existing callsign-interpolated expectations to the tier-1 shape, corrected three pre-existing checks whose assertions directly contradicted D-08 (not in the plan's literal "seven" but genuinely broken by the rewrite), and updated the anchor-alignment check to expect the D-12 offset.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `_flight_line1_text()` as the four-tier content ladder** - `93f3d30` (feat)
2. **Task 2: Omit line 1 on tier 3 in both text blocks, apply the previous card's 20px optical offset** - `8e869be` (feat)
3. **Task 3: Make every ladder tier reachable from the render CLI** - `7af4a95` (feat)

## Files Created/Modified

- `server/plane/render.py` - `_flight_line1_text()` rewritten as the four-tier ladder; `draw_main_text_block()`/`draw_previous_text_block()` gain the omitted-line branch; new `PREVIOUS_TEXT_LEFT_OFFSET_PX` constant and its application in `draw_previous_text_block()`; `_PREVIEW_ROUTE`/`_PREVIEW_PREVIOUS_ROUTE` gain synthetic `callsign_iata` values; new `--no-identifier` CLI flag wired through `main()`; `--preview-airline-only`'s stale "bare callsign" help text corrected
- `server/test_render.py` - `TEST_ROUTE`/`TEST_PREVIOUS_ROUTE`/`TEST_LONG_ROUTE` gain `callsign_iata`; seven pre-existing expectations reconciled to tier 1; three pre-existing checks corrected (enrichment-miss, two airline-only checks, one CLI check) to match D-08; 15 new checks (6 tier-coverage + D-08 guard + hostile-input, 5 tier-3-omission + D-12-offset, 4 CLI-reachability); `EXPECTED_CHECK_COUNT` 82→97

## Decisions Made

- The real on-disk `EXPECTED_CHECK_COUNT` baseline was **82**, matching the value 08-03 actually committed (confirmed by reading the file before editing) - not a stale literal.
- `PREVIOUS_TEXT_LEFT_OFFSET_PX` was chosen as the constant's exact name (must contain both `PREVIOUS` and `OFFSET` per the plan's discretion clause).
- `--no-identifier` was chosen as the new CLI flag's exact name, mirroring `--no-route`'s naming convention.
- `_PREVIEW_ROUTE["callsign_iata"] = "AF1006"` and `_PREVIEW_PREVIOUS_ROUTE["callsign_iata"] = "VY1234"` - both synthetic, in each airline's real IATA prefix.
- `TEST_ROUTE["callsign_iata"] = "TO16VB"` is the REAL value from `server/fixtures/adsbdb_hit_TVF16VB.json` (confirmed via `grep` before use), not synthetic - the default test render now exercises tier 1 against a genuine adsbdb-sourced value. `TEST_PREVIOUS_ROUTE["callsign_iata"] = "VY8163"` and `TEST_LONG_ROUTE["callsign_iata"] = "AT9051"` are synthetic, marked as such in comments.
- Three pre-existing checks that directly asserted raw-callsign presence (the enrichment-miss check, two airline-only-route checks at lines ~1082/1106, and the `--no-route` CLI check) were corrected as Rule 1 fixes. These weren't among the plan's literal "seven line-1 expectations" list, but Task 1's rewrite made their assertions genuinely false (they required the raw callsign to appear, which D-08 now forbids everywhere) - leaving them unfixed would have left the suite red or worse, still pinning the exact behavior this plan exists to remove.

## The four verbatim CLI commands (for plan 08-06's on-glass session)

```
server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 --previous-callsign VY1234 --preview /tmp/tier1.png
server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 --previous-callsign VY1234 --no-identifier --preview /tmp/tier2.png
server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 --previous-callsign VY1234 --preview-airline-only --preview /tmp/tier3.png
server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 --previous-callsign VY1234 --no-route --preview /tmp/tier4.png
```

All four exit 0, and all five themes (`white black yellow red sky`) render alongside them with no parser change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected three pre-existing checks whose assertions directly contradicted D-08**

- **Found during:** Task 1
- **Issue:** The enrichment-miss check, two airline-only-route checks (`EJU84YF`/`TVF12ZW`), and the `--no-route` CLI check all asserted the RAW CALLSIGN must appear among the drawn text - exactly the behavior D-08 forbids after the rewrite. These weren't in the plan's literal "seven" list but were genuinely broken by Task 1's change.
- **Fix:** Inverted each assertion to require the raw callsign's ABSENCE, and to require the correct tier's actual output (title-case state word for tier 4, airline name alone with no line 1 for tier 3).
- **Files modified:** `server/test_render.py`
- **Verification:** All four checks pass; the suite would have failed on this scope's own work if left unfixed.
- **Committed in:** `93f3d30` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test-suite correctness fix, no production code affected)
**Impact on plan:** Necessary to keep the test suite meaningful and green after Task 1's behavioral change. No scope creep - these are the same D-08 guarantee the plan's own new checks assert, just also enforced on three checks the plan's author didn't happen to flag.

## Issues Encountered

**Mid-session recovery from an accidental `git checkout --`.** After completing Task 1's render.py+test_render.py edits (all three tasks' worth of render.py changes had already been applied in one continuous editing pass before any commit), the deliberate D-08 regression demonstration was reverted using `git checkout -- server/plane/render.py` - which, since none of the session's render.py changes were committed yet, silently discarded ALL of them (Task 1 through Task 3), not just the one-line deliberate regression. This was caught immediately via the post-revert test run (many more failures than expected). Recovery: the fully-edited file had been backed up to the scratchpad directory before the revert; render.py was rebuilt task-by-task by re-applying each task's edits via the `Edit` tool (never `git checkout`) and diffed byte-for-byte against the backup to confirm fidelity before each commit. No work was lost; the three per-task commits reflect exactly the same content as the original single edit pass, split correctly by task boundary. Going forward, per this project's own `destructive_git_prohibition` guidance: `git checkout -- <file>` is only safe to discard changes belonging entirely to the CURRENT step being reverted, never used on a file carrying multiple as-yet-uncommitted tasks' worth of work.

**Two deliberate-regression demonstrations, both observed failing as designed, both reverted via `Edit` (not `git checkout`) before committing:**

Task 1 (D-08 guard, temporarily adding a fifth bare-callsign fallback tier):
```
FAIL _flight_line1_text() tier 4 (nothing resolved) returns the title-case state word 'Departing'/'Arriving' for
both route=None and a dict with no airline name, for both states (D-10) - tier 4 departing expected 'Departing'
for route={'airline_name': None, 'origin_iata': None, 'origin_city': None, 'destination_iata': None,
'destination_city': None, 'callsign_iata': None}, got 'XYZ999'
render: 87/88 checks pass
```

Task 2 (half-applied omitted-line fix, removing the branch from `draw_previous_text_block()` only):
```
FAIL an airline-only route on the previous card omits its own line 1, promoting line 2 to line 1's y-position
using the previous card's own gap constant, with no empty-string draw call (D-10 tier 3) - the check that catches
the change implemented in only one of the two functions - an empty-string draw call was made for the previous
card's omitted line 1: [('', (1071, 1333)), ('Vueling Airlines · A320', (1071, 1367))]
FAIL both cards independently omit line 1 and promote line 2 on a simultaneous airline-only render, without
interfering with each other (D-10 tier 3) - an empty-string draw call was made somewhere: ['DEPARTING',
'ORY · RWY 3', 'Air France · 737-800', '', 'Vueling Airlines · A320']
render: 91/93 checks pass
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The panel never shows the raw ADS-B callsign again, at any information tier, on either card - proven both at the library level (`_flight_line1_text()` direct calls, end-to-end `build_canvas()` renders) and at the CLI level (`render.main()` across all four tier-forcing flag combinations).
- Both drawing functions independently and correctly handle the tier-3 omitted-line case, proven by a deliberate half-applied-fix demonstration that only the per-card-specific checks caught.
- The previous card's optical alignment correction is a named, documented constant (`PREVIOUS_TEXT_LEFT_OFFSET_PX = 20`), applied only to the previous card; the main card is provably unshifted.
- Every content-ladder tier is now one copy-pasteable `render.py` command - plan 08-06's blocking on-glass session can reuse the four commands recorded above verbatim, alongside the existing five-theme sweep.
- None of this plan's rendering changes have been seen on real Spectra 6 ink yet - screen-confirmed only via `/tmp/08-04-tier1.png` and `/tmp/08-04-tier3.png` (both visually compared against `.planning/spikes/001-panel-theme-colours/renders/97-prev-text-nudged-left-20px.png` and the tier-3 spike renders, and matched). Plan 08-06's blocking on-glass session is where that check happens.
- Full suite: `scripts/run-all-tests.sh` reports the one pre-existing, pre-flagged failure documented in this plan's own execution context - `server/test_poll_loop.py`'s pinned `panel.bin` digest mismatch (macOS-local render vs. Linux-CI-pinned digest, plan 08-05's job to re-pin) - confirmed unrelated (`git diff --stat` across all three commits touches only `server/plane/render.py`/`server/test_render.py`).

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*

## Self-Check: PASSED

Both modified files (`server/plane/render.py`, `server/test_render.py`) confirmed present on disk; all three task commit hashes (`93f3d30`, `8e869be`, `7af4a95`) confirmed in `git log`.
