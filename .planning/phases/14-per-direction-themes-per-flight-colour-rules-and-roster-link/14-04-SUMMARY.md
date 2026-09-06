---
phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link
plan: 04
subsystem: ui
tags: [settings-page, css-only-reveal, checkbox, chip-grid, form-validation, python-stdlib]

requires:
  - phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link (plan 02)
    provides: "device_config.CLEAR_THEME_ARRIVING sentinel, theme_arriving config key, save_device_config()'s three-state theme_arriving contract"
provides:
  - "The Settings page's Theme group renders a settings-checkbox toggle plus a second, identical 18-chip grid for the arrivals theme override, both always present in the HTML"
  - "A CSS-only :has() reveal (inside @supports selector(:has(*))) hides the second grid/label when the checkbox is unchecked, with a no-JS/no-:has() fallback that always shows both"
  - "handle_post() genuinely clears theme_arriving back to None when the arrivals checkbox is unchecked, keyed on the checkbox field alone, never on theme_arriving's presence"
affects: [14-05, settings-page-verification]

tech-stack:
  added: []
  patterns:
    - "Shared chip-grid renderer (_theme_chip_grid_html()) called twice with a field-name/extra-class/extra-attr parameterization, so two structurally-identical grids can never drift apart"
    - "Checkbox-keyed clear-vs-carry-forward resolution for a field whose companion value is always submitted (the second grid renders unconditionally), as opposed to the absent-means-unchanged idiom every other non-checkbox field on this page uses"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_config_page.py

key-decisions:
  - "theme_fieldset()'s new current_theme_arriving parameter defaults to None so every pre-Phase-14 call site (including test call sites) keeps working unchanged, rather than requiring every caller to pass two args"
  - "The second grid pre-selects the EFFECTIVE arrivals theme (the stored override if set, otherwise the same theme the first grid has selected) so ticking the checkbox starts from the theme already in use, not from nothing"
  - "handle_post() branches on the theme_arriving_enabled checkbox field, never on theme_arriving's own presence, and passes CLEAR_THEME_ARRIVING (not None) when unchecked — the two failure modes 14-RESEARCH.md's Pitfalls 2/3 warned about"

requirements-completed: []

coverage:
  - id: D1
    description: "The arrivals checkbox and second (arrivals) chip grid render inside the Theme group's existing .theme-status card, both always present in the HTML"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_theme_arriving_markup_both_grids_copy_and_checkbox_present"
        status: pass
    human_judgment: false
  - id: D2
    description: "The reveal is CSS-only (@supports selector(:has(*))), scoped to #theme-arriving-toggle, with a graceful always-both-visible fallback for browsers without :has() support"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_strong_selected_treatment_is_keyed_to_the_live_checked_radio (supports_marker count assertion)"
        status: pass
    human_judgment: false
  - id: D3
    description: "handle_post() genuinely clears a previously-set theme_arriving override back to None when the arrivals checkbox is unchecked, even though theme_arriving itself is still present with a valid id"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_theme_arriving_clearable_contract_full_round_trip (14-VALIDATION.md row 7)"
        status: pass
      - kind: integration
        ref: "companion/test_config_page.py#_settings_form_raw_post_no_js_clears_and_sets_theme_arriving (14-VALIDATION.md row 11)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A crafted checkbox value or a non-member theme_arriving (including path-traversal and SQL-shaped payloads) rejects the whole submission, writing nothing"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_handle_post_crafted_theme_arriving_checkbox_value_rejected"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_handle_post_nonmember_theme_arriving_rejected"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 04: Arrivals-Theme Checkbox and Clearable Override Summary

**The Settings page's Theme group gains a CSS-only-revealed second chip grid for the arrivals theme, and `handle_post()` now genuinely clears the override on uncheck instead of silently carrying it forward.**

## Performance

- **Duration:** 55 min
- **Completed:** 2026-09-06
- **Tasks:** 3/3 completed
- **Files modified:** 3

## Accomplishments

- Extracted `theme_fieldset()`'s inline chip loop into a shared `_theme_chip_grid_html()` helper, called twice (departures grid unchanged, arrivals grid new) so the two markups can never drift apart
- Added the `settings-checkbox`-wrapped arrivals toggle, the "Arrivals theme" label, and the second 18-chip grid — both grids and the checkbox always render in the HTML; a new, separate `@supports selector(:has(*))` block in `companion/static/style.css` hides the second grid/label only when the toggle is unchecked and `:has()` is supported
- Extended `handle_post()` with `theme_arriving`/`theme_arriving_enabled`, validated by the same membership test `theme` uses, then branched on the checkbox field alone — passing `device_config.CLEAR_THEME_ARRIVING` (never `None`) when unchecked, closing the exact two failure modes `14-RESEARCH.md`'s Pitfalls 2/3 warned about
- Repaired five pre-existing count-shaped assertions in `companion/test_config_page.py` that the second grid legitimately doubled, and added 9 new checks (markup, pre-selection, one per Task 2 behavior bullet, the named clearable-contract round trip, and a raw no-JS HTTP POST), raising `EXPECTED_CHECK_COUNT` from 92 to 101

## Task Commits

1. **Task 1: Add the arrivals checkbox and the second chip grid to the Theme group, plus their CSS (D-05)** - `8027a70` (feat)
2. **Task 2: Make the unchecked checkbox genuinely clear theme_arriving in handle_post() (D-04/D-05)** - `0f83a00` (feat)
3. **Task 3: Extend companion/test_config_page.py with the arrivals-override checks (14-VALIDATION.md row 7)** - `72235aa` (test)

_Note: Task 1 and Task 2 both touch `companion/pages/config_page.py` but in disjoint regions (the markup helpers/`theme_fieldset()`/`render()` wiring vs. `handle_post()`'s validation branch); each commit was constructed to contain exactly its own task's hunks._

## Files Created/Modified

- `companion/pages/config_page.py` - New constants (`ARRIVING_CHECKBOX_VALUE`, `THEME_ARRIVING_TOGGLE_ID`, `ARRIVAL_GRID_ATTR`, `THEME_ARRIVING_CHECKBOX_LABEL`, `THEME_DIRECTION_LABEL`), the shared `_theme_chip_grid_html()` helper, `theme_fieldset()`'s new `current_theme_arriving` parameter (default `None`), `render()`'s explicit `.get("theme_arriving")` read, and `handle_post()`'s checkbox-keyed clear/set branch
- `companion/static/style.css` - `.theme-direction-label` (the reused 12px/semibold/uppercase/0.06em/70%-muted label voice) and a second, separate `@supports selector(:has(*))` block implementing the CSS-only reveal
- `companion/test_config_page.py` - Five repaired count-shaped assertions, 9 new checks, and the `EXPECTED_CHECK_COUNT` ledger update (92 → 101)

## Decisions Made

- `theme_fieldset()`'s new parameter defaults to `None` rather than being required, so pre-existing call sites (including many in the test harness that exercise single-theme/monkeypatched-registry branches) keep working unchanged; every acceptance-criterion command in the plan happens to pass both args explicitly anyway, so this default is purely a compatibility choice, not a behavior change.
- The second grid's pre-selection uses the *effective* arrivals theme (override if set, otherwise the departures theme) rather than leaving it unselected, so an operator who ticks the box for the first time starts from a real, visible choice.
- Kept `_theme_chip_grid_html()`'s markup byte-identical to the pre-Phase-14 output for the first (departures) grid — verified directly by an acceptance-criterion assertion (`'<div class="theme-chip-grid">' in h`) — so no existing consumer of that markup shape needed to change.

## Deviations from Plan

**None — plan executed exactly as written.** All acceptance criteria in the plan's three tasks were run directly (not just inferred) and passed, including the deliberate-break verification for the clearable contract (temporarily changing the unchecked branch to pass `None` instead of `CLEAR_THEME_ARRIVING` confirmed the harness fails with exactly the three expected checks, then the fix was restored).

## Issues Encountered

- **No `server/.venv` in this worktree.** Gitignored virtualenvs aren't checked out into a fresh git worktree. Located the real venv at the main checkout (`/Users/florian/Projects/skypane/server/.venv/bin/python3`, Python 3.11 with Pillow etc. installed) and invoked it directly by absolute path against the worktree's own `sys.path`/cwd for every verification command and the full `scripts/run-all-tests.sh` run (via `PYTHON=... scripts/run-all-tests.sh`). This is a read-only use of an external interpreter, not a modification to either checkout.
- **A literal-string acceptance criterion diverged from this file's own established pattern.** The plan's Task 3 acceptance criteria grep for the raw copy strings ("Use a different theme for arrivals", "Arrivals theme") directly in `test_config_page.py`, but this harness's existing convention is to reference the `config_page` module's own constants rather than hardcode copy text. Resolved by hardcoding the literal strings in the new markup check (satisfying the grep) while also asserting the constants equal those exact strings — so a future accidental rewording of either the constant or a copy-paste in the test would be caught by the other.
- **The `@supports selector(:has(*))` count acceptance criterion needed a specific phrasing choice.** The plan requires the literal grep count in `style.css` to rise by exactly one; a first draft of the new CSS comment repeated that exact phrase in prose, which would have raised the count by two (one prose mention, one real block). Reworded the comment to avoid the literal substring while keeping the explanation intact, then confirmed the exact `+1` delta via `grep -o | wc -l`.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

This plan is independent of 14-01/14-03 and depends only on 14-02 (already landed in wave 1). Plan 14-05 (per-flight colour rules) can proceed without waiting on this plan's own artifacts, per the phase's dependency map. The Theme group's markup, CSS, and `handle_post()` contract are all stable and fully covered by the 101-check harness; no follow-up work is implied.

## Self-Check: PASSED

- FOUND: `companion/pages/config_page.py`
- FOUND: `companion/static/style.css`
- FOUND: `companion/test_config_page.py`
- FOUND: commit `8027a70` (Task 1)
- FOUND: commit `0f83a00` (Task 2)
- FOUND: commit `72235aa` (Task 3)

---
*Phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link*
*Completed: 2026-09-06*
