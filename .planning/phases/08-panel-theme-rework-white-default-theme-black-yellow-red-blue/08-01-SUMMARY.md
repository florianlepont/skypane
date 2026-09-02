---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 01
subsystem: config
tags: [device_config, palette, theme-registry, panel-format, companion-config]

# Dependency graph
requires:
  - phase: 07-final-on-glass-verification
    provides: Blue/Green palette real-ink tuning, dithered state background, text backing plate (superseded by 08-03 for the backing plate)
provides:
  - "server.device_config.THEMES with five entries (white/black/yellow/red/sky), DEFAULT_THEME_ID='white'"
  - "server.plane.render.STATE_BACKGROUND/STATE_INK now derive from the White default at import time"
  - "companion CFG-01 picker proven registry-driven with zero companion-side code change"
affects: [08-02, 08-03, 08-04, 08-05, 08-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry-driven CFG-01 picker: adding a theme is a pure data change in device_config.THEMES, no call-site fanout anywhere else in the codebase"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py
    - server/test_render.py
    - companion/test_config_page.py
    - server/test_pipeline_e2e.py

key-decisions:
  - "White is the new DEFAULT_THEME_ID; the retained Sky theme is relabelled 'Sky' (D-01/D-03/D-04)"
  - "Black/Yellow/Red are single-colour themes (departing_index == arriving_index), contrast-correct ink, distinguished from Sky's genuine two-tone by an explicit regression check (D-02)"
  - "The registry's provenance comment now records that White/Black/Yellow/Red are screen-confirmed only, pending plan 08-06's on-glass pass"

patterns-established:
  - "Theme id-to-(background,ink) contrast mapping pinned as an explicit literal dict in test_config_history.py, so a swapped ink index fails loudly by name rather than passing silently"

requirements-completed: [D-01, D-02, D-03, D-04]

coverage:
  - id: D1
    description: "White is the default theme: THEMES['white'] exists, DEFAULT_THEME_ID='white', and a fresh render (no theme_id) is white-background/black-ink in both departing and arriving states"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_default_theme_and_labels_are_correct"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_departing_dominant_is_white / _arriving_dominant_is_white"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_white_theme_canvas_matches_default_and_sky_differs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Black, Yellow and Red are single-colour themes with contrast-correct ink (black on yellow; white on black/red), built only from named panel_format.IDX_* constants"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_theme_registry_shape_is_correct"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py#_single_colour_contract_for_new_themes_and_sky_differs"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py#_ink_contrast_pairing_is_correct"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_per_theme_dominant_background_holds_in_both_states"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_ink_index_matches_theme_registry_for_every_theme"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sky (Blue departing / Green arriving) is retained, behaviourally unchanged, no longer default, relabelled 'Sky'"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_single_colour_contract_for_new_themes_and_sky_differs (sky-still-two-tone half)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_white_theme_canvas_matches_default_and_sky_differs (sky-differs-from-default half)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Companion CFG-01 picker offers all five themes with plain labels and White pre-selected, with zero change to companion/pages/config_page.py or companion/app.py"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_theme_fieldset_five_options_with_own_id_and_label"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_theme_fieldset_default_selects_exactly_the_white_option"
        status: pass
      - kind: other
        ref: "git diff --stat companion/ (only test_config_page.py changed)"
        status: pass
    human_judgment: false

# Metrics
duration: ~10min
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 01: White default theme + Black/Yellow/Red registry entries Summary

**Five-entry `THEMES` registry (White/Black/Yellow/Red/Sky) with White as the new `DEFAULT_THEME_ID`, added as a pure data change to `server/device_config.py` with zero call-site fanout anywhere else — proven by a registry-driven companion picker requiring no code edit and a render harness exercising all five themes in both active states.**

## Performance

- **Duration:** ~10min (commit span; wall time including reads/verification longer)
- **Started:** 2026-08-31T09:32:00Z (approx, first commit 09:32:37Z UTC)
- **Completed:** 2026-08-31T09:40:12Z (last commit, UTC)
- **Tasks:** 3
- **Files modified:** 5 (4 planned + 1 Rule 1 deviation)

## Accomplishments

- `THEMES` grew from a single `"sky"` entry to five: `white` (new default), `black`, `yellow`, `red` (all single-colour, contrast-correct), and the relabelled `sky` (unchanged Blue/Green, no longer default) — built only from `panel_format`'s named `IDX_*` constants, per the registry's own stated discipline.
- `DEFAULT_THEME_ID` flip to `"white"` silently propagated to `server/plane/render.py`'s `STATE_BACKGROUND`/`STATE_INK` module-level constants (evaluated at import time from the registry) with zero edit to `render.py` itself — exactly the extension contract the module's docstring promises.
- `server/test_config_history.py` grew 21→25 checks: five stale default-comparison literals corrected from `"sky"` to `"white"`, four new checks pinning the registry's shape, the four new themes' single-colour contract (with Sky's genuine two-tone difference pinned alongside it as a regression guard), the ink-contrast mapping, and the new default + all five plain labels.
- `server/test_render.py` grew 76→78 checks: the two dominant-nibble checks now expect White instead of Blue/Green; the Sky-equals-default check is rewritten to assert White-matches-default AND Sky-still-differs-from-default (so it can no longer pass if Sky were silently deleted); two new checks assert per-theme background dominance across both states for a real two-flight render, and ink-index agreement with the registry, both looped over `THEME_IDS` so a future sixth theme is exercised automatically.
- `companion/test_config_page.py` grew 37→39 checks proving the CFG-01 picker absorbed all four new themes purely through the registry, with `companion/pages/config_page.py` and `companion/app.py` confirmed byte-untouched via `git diff --stat`.
- Every registered theme, in both active states, was rendered as a real two-flight panel and passed `_assert_legal_palette()`'s legality-plus-dominance guard rail.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the four new THEMES entries, flip DEFAULT_THEME_ID to white, relabel Sky** - `1104656` (feat)
2. **Task 2: Pin the new registry and load-time defaults in test_config_history.py** - `aa79d51` (test)
3. **Task 3: Reconcile test_render.py's theme-default checks, confirm companion picker needs no code change** - `0456a06` (test)

_No plan-metadata docs commit yet — pending state/roadmap update below._

## Files Created/Modified

- `server/device_config.py` - `THEMES` gains white/black/yellow/red entries, `DEFAULT_THEME_ID="white"`, Sky relabelled, provenance comment extended with a dated Phase 8 note
- `server/test_config_history.py` - five stale default literals corrected to White; four new registry-contract checks; `EXPECTED_CHECK_COUNT` 21→25
- `server/test_render.py` - three theme-default checks reconciled to the White default; two new checks (per-theme background dominance, ink-index agreement); `EXPECTED_CHECK_COUNT` 76→78
- `companion/test_config_page.py` - two new checks proving the registry-driven CFG-01 picker; `EXPECTED_CHECK_COUNT` 37→39
- `server/test_pipeline_e2e.py` - (Rule 1 deviation, not in plan's `files_modified`) corrected a hardcoded battery-icon ink-nibble expectation that assumed the retired Sky default's White ink

## Decisions Made

- Insertion order in `THEMES` (white, black, yellow, red, sky) follows the plan's own suggested ordering (Claude's Discretion per D-01) — mirrors the new default's precedence, no functional effect since `THEME_IDS = tuple(THEMES)` derives automatically.
- Left `render.py`'s `STATE_BACKGROUND`/`STATE_INK` block comment ("the default ('sky') theme's colours...") stale rather than editing it — `server/plane/render.py` is outside this plan's file scope (Task 3 explicitly forbids production-code edits, and the file isn't in this plan's `files_modified`). Flagged below as a deferred item.
- Left `companion/pages/config_page.py`'s `THEME_HELPER_TEXT` ("More themes will be added once Phase 7 validates...") unedited for the same reason — Task 3 explicitly forbids touching that file, and CONTEXT.md's own scope confirms the picker needs zero code change. Flagged below as a deferred item.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected a stale hardcoded ink-nibble expectation in `server/test_pipeline_e2e.py`**
- **Found during:** Task 3 verification (running every other server harness per the plan's acceptance criteria)
- **Issue:** `_real_battery_poll_changes_only_the_icon_region()`'s sampled-pixel assertion hardcoded `expected_nibble = 0x0 if state == "empty" else 0x1` — this was only ever true because the retired `"sky"` default's `ink_index` was `IDX_WHITE` (nibble `0x1`) for both active states. With White now the default (`ink_index=IDX_BLACK`, nibble `0x0`), the literal broke: the check failed with `packed nibble ... is 0x0, expected 0x1`. This file is not in plan 08-01's `files_modified` list, but the plan's own verification step explicitly requires this harness to exit 0, and the plan's threat register (T-08-01-02) names exactly this class of default-flip fallout as something Task 3 must catch.
- **Fix:** Derived the expected nibble from `device_config.theme_ink_index(theme_id)` for the theme `run_once()` actually reported (via `result_after["theme"]`), mapped to a wire nibble through `panel_format.INDEX_TO_NIBBLE` — the empty-state case (always Black regardless of theme) is unchanged.
- **Files modified:** `server/test_pipeline_e2e.py`
- **Verification:** `server/.venv/bin/python3 server/test_pipeline_e2e.py` — 6/6 checks pass (was 5/6 before the fix)
- **Committed in:** `0456a06` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Necessary for the plan's own verification step to actually pass; no scope creep — the fix is a test-only literal correction following the exact same registry-driven pattern the plan's own Task 3 already applied to `test_render.py`.

### Deferred items (not fixed — out of this plan's file scope)

- `server/plane/render.py` lines ~164-166: the `STATE_BACKGROUND`/`STATE_INK` block comment states "the default ('sky') theme's colours are exactly the pre-Phase-6 values" — now inaccurate since the default is `"white"`. `render.py` is not in plan 08-01's `files_modified`, and Task 3 explicitly forbids production-code edits in this plan. Comment-only, zero behavioral impact; worth a one-line fix whenever `render.py` is next touched (plan 08-03/08-04 both modify it).
- `companion/pages/config_page.py`'s `THEME_HELPER_TEXT` constant ("More themes will be added once Phase 7 validates additional color options on real hardware.") is now stale copy — Phase 7 has passed and four more themes exist. `config_page.py` is explicitly out of scope for this plan (Task 3: "Do not edit `companion/pages/config_page.py`"), and CONTEXT.md's own boundary confirms the picker's registry-driven behaviour needs no companion-side change. Left for a future plan to update the copy.

## Issues Encountered

- **Task 2 acceptance criterion imprecision (informational only, no code change needed).** The plan's literal acceptance check `grep -c '"theme": "sky", "tracked_runway"' server/test_config_history.py` is 0` does not account for `_save_then_load_round_trips()`'s deliberate, plan-endorsed explicit round-trip assertion (`{"theme": "sky", "tracked_runway": "02-20", ...}`), which the plan's own action text explicitly instructs to leave alone ("those exercise the round-trip of a non-default value and are now more meaningful than before"). The grep pattern is a substring match with no trailing colon, so it also matches that legitimate assertion (`grep -c` returns 1, not 0). Verified the real behavioral intent instead: all five *default*-comparison literals were corrected to `"white"`, and the one remaining match is confirmed to be exactly the intentional Sky round-trip test, not a missed default-comparison site.
- **Task 2's "three checks" undercounted the real default-literal count.** The plan's action text says "three checks compare `load_device_config()`'s result against a literal dict whose theme value is the old default," but the real on-disk file had five such comparisons (the three named plus `_hostile_hand_edit_after_a_real_save_still_yields_defaults` and `_save_led_enabled_false_round_trips`). All five were corrected — the plan's own "read the real on-disk value" principle (already applied to `EXPECTED_CHECK_COUNT`) was extended to this count as well, since leaving any default-comparison literal at `"sky"` would have left the harness asserting the wrong default.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The five-entry `THEMES` registry, White default, and registry-driven companion picker are now the load-bearing foundation every later Phase 8 plan builds on (08-02 through 08-06 all depend on this plan's registry shape being final).
- `server/test_poll_loop.py`'s pinned `panel.bin` digest is now genuinely stale (was already stale pre-phase from an unrelated macOS/Linux FreeType rendering difference; this plan's White-default flip additionally invalidates its value for real reasons). Re-pinning that digest is explicitly plan 08-05's job, not this one's — do not re-pin it here.
- None of the four new hues (White/Black/Yellow/Red) has been seen on real Spectra 6 ink yet — all four are screen-confirmed only, exactly like Sky was before Phase 7's on-glass session. Plan 08-06's blocking on-glass verification pass is where that check happens; the registry's provenance comment now records this honestly.

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*

## Self-Check: PASSED

All five modified files confirmed present on disk; all three task commit hashes (1104656, aa79d51, 0456a06) confirmed in `git log`.
