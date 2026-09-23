---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 05
subsystem: testing
tags: [test-harness, coverage-ledger, config-page, accordion, editorial-floor]

requires:
  - phase: 30-03
    provides: "_ASPECT_REPIN_LEDGER (test_config_page.py) — the 19-row coverage-gap ledger this plan pays 12 rows of, and its own self-reading guard check"
  - phase: 30-04
    provides: "_aspect_card_html()/_usage_row_html()/_palette_grid_html() (companion/pages/config_page.py) — the shipped accordion markup every replacement check in this plan asserts against; also the plan's own \"Escalated Red-Check Inventory\" naming 11 of the 15 unledgered misses this plan owns"
provides:
  - "Twelve replacement checks in companion/test_config_page.py, each re-proving a property _ASPECT_REPIN_LEDGER owed 30-05, derived from the registry/COLOUR_USAGES at check time (never a restated literal)"
  - "_rules_row_segment() (renamed from _rules_panel_segment()) — locates the rules row via its own data-usage attribute, replacing the retired COLOUR_USAGE_PANEL_TARGET_ATTR locator that broke 8 checks across two harnesses"
  - "_aspect_usage_row_bounds() — a shared helper every row-scoped check in this plan uses to slice one accordion row's own markup out of a full render"
  - "_ASPECT_REPIN_LEDGER's own 12 rows owed to 30-05 cleared (owed_by=\"\"), three with a recorded divergence note explaining a forced rename"
  - "test_companion_app.py's two remaining escalated CFG-85 misses repointed: _display_and_device_pages_split_the_groups' rules-row locator, and _site_wide_editorial_floor_all_six_routes_both_languages' re-derived Display/site-wide caption-count minimums"
affects: [30-06, 30-07, 30-08]

tech-stack:
  added: []
  patterns:
    - "When a ledger row's own predicted replacement name equals its retired name (_ASPECT_REPIN_LEDGER's own convention for a same-name repoint), the ledger guard's 'retired name must have no live def' clause makes that literal name unrepayable the moment the replacement lands under it — the guard itself, not the property being tested, forces a rename. Fix: rename the replacement, record the divergence in the ledger row's own 'why' field, per the plan's own Task 3 instruction for exactly this case."
    - "A page-wide `rendered.index(\"</form>\")` search for 'the settings form's own closing tag' is fragile the moment ANY earlier <form>...</form> exists on the page before the settings form opens (here: the Frame strip's own quick-switch forms) — it silently resolves to the WRONG form's closing tag while still passing every existing assertion, because the accidental value happens to satisfy the same inequality the real value would. The retired check this plan replaced carried the identical bug. Fix: anchor the search to the settings form's own opening tag first (`rendered.index('<form class=\"config-form\" id=\"%s\"' % SETTINGS_FORM_ID)`), then search for `</form>` from THAT position onward — caught by this plan's own Task 2 mutation test (\"move the Aspect card before </form>\"), which the unfixed check let through silently."

key-files:
  created: []
  modified:
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "Three ledger rows (_english_display_render_still_carries_every_pinned_english_string, _scoped_render_carries_hidden_fields_and_omits_other_groups, _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions) predicted a replacement with the SAME NAME as the retired check — 30-03's own convention for a same-name repoint. That collides with the ledger guard's own unconditional 'no def named {retired} survives' clause: the moment a same-named replacement lands, the guard reads it as \"the retired check was left behind\" and fails, regardless of owed_by. Resolved by renaming each replacement to this phase's Aspect naming convention (_aspect_display_render_still_carries_every_pinned_english_string / _aspect_scoped_render_carries_hidden_fields_and_omits_other_groups / _aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions) and recording the divergence in each row's own 'why' field, per Task 3's own explicit instruction for exactly this case."
  - "_rules_copy_appears_escaped_verbatim's own ledger row states its 'why' as 'this check reads config_page.FRAME_COLOURS_ROW_LABELS, the constant CFG-85's rebuild renames' — verified against the shipped 30-04 code that this premise is STALE: 30-04-PLAN.md Task 1 kept FRAME_COLOURS_ROW_LABELS' own name deliberately (30-UI-SPEC.md's Copywriting Contract cites it by this exact name). The retired check's own body was re-run unmodified against the real render and every assertion held — only the function's own name changes (to _aspect_rules_copy_appears_escaped_verbatim), recorded as a divergence rather than silently treated as a real rewrite."
  - "_aspect_rules_row_label_locked_verbatim adds a second lock beyond the retired check's own single assertion: the rules row's empty-state meta must read FRAME_COLOURS_RULES_EMPTY_META's real value ('No rules yet'), never ROADMAP's own plausible-sounding paraphrase 'Aucune règle · Ajouter' — per Task 2's own explicit instruction, since that paraphrase is exactly the kind of copy a later editorial pass could 'restore' without a dedicated check catching it."
  - "_rules_row_renders_inside_aspect_after_form's own </form> locator was fixed to anchor off the settings form's own opening tag before searching for its closing tag, rather than the retired check's own bare rendered.index('</form>') (which silently resolves to the Frame strip's own quick-switch form's closing tag instead — a bug carried over unnoticed from the RETIRED check, caught only by this plan's own required mutation test for 'move the Aspect card before </form>'). See tech-stack patterns above for the full mechanism."

patterns-established: []

requirements-completed: [CFG-85]

coverage:
  - id: D1
    description: "Twelve replacement checks in companion/test_config_page.py pay back every _ASPECT_REPIN_LEDGER row owed to 30-05 — the Aspect card's full shape as a relationship (locked row order, exactly-one-open, secondary rules row, one palette per theme row, zero retired-mechanism markup), per-registry theme/id/label/leading-option coverage on all three palettes, the default White-departures selection asserted per group, the arrivals override's cross-row independence from the calendar row, the calendar palette's registry-order/no-id contract, the rules row's placement after the settings form's own closing tag, its locked label plus the FRAME_COLOURS_RULES_EMPTY_META lock, the rules copy escaped-verbatim check, the pinned-English-strings set, the scoped-render check, and the live preview figure's own class/position — every count derived from device_config/COLOUR_USAGES at check time"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (run) — 269/269 checks pass, EXPECTED_CHECK_COUNT re-derived 257 -> 269"
        status: pass
      - kind: other
        ref: "six mutations (row-order swap, second-row open, duplicated palette id, dropped arrivals leading option, preview moved below the rows, Aspect card moved before </form>) — every one caught, messages quoted below"
        status: pass
    human_judgment: false
  - id: D2
    description: "_ASPECT_REPIN_LEDGER's own guard proves all 12 rows owed to 30-05 are cleared and resolve to a live def, the ledger is not empty, and every remaining row is owed by 30-06 or 30-07 only"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement — PASS; standalone script confirms 12 cleared / 7 still-owed (5x 30-06, 2x 30-07) of 19 total rows"
        status: pass
    human_judgment: false
  - id: D3
    description: "companion/test_companion_app.py's two remaining escalated CFG-85 misses (from 30-04-SUMMARY.md's own inventory) are repointed: _display_and_device_pages_split_the_groups' rules-row locator moves onto data-usage=\"rules\"; _site_wide_editorial_floor_all_six_routes_both_languages' Display/site-wide caption-count minimums are re-derived by running against a real server (13->9 per-route, 55->47 site-wide)"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py (run) — 317/317 checks pass"
        status: pass
    human_judgment: false
  - id: D4
    description: "companion/test_config_page.py's own two escalated, unledgered misses (Group B: the stale editorial-floor caption minimum; Group C: the retired four-grid density/legend check) are fixed — the floor minimum re-derived by running (16->12 measured on /display), and the density/legend check rewritten to assert the new real shape (one .theme-chip-grid plus three legend-free .palette grids)"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (run) — both checks pass at 269/269 total"
        status: pass
    human_judgment: false
  - id: D5
    description: "Zero production files touched — companion/pages/config_page.py is byte-identical to the end of 30-04; companion/test_browser_ux.py is untouched, still exactly 7 red (3 pre-existing floor + 4 rows routed to 30-08); scripts/run-all-tests.sh reports 21/22 harnesses PASS, with test_browser_ux.py the one documented, expected FAIL"
    requirement: CFG-85
    verification:
      - kind: other
        ref: "git diff --stat HEAD~2 (this plan's own two commits) — companion/test_config_page.py, companion/test_companion_app.py only; git diff --exit-code companion/pages/config_page.py against 30-04's final commit (3fea044) — empty"
        status: pass
      - kind: integration
        ref: "companion/test_browser_ux.py (run) — 84/91, same 7 names as 30-04's own inventory, unchanged"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh JOBS=4 (run twice) — 21/22 PASS both times; the one FAIL is test_browser_ux.py's documented floor"
        status: pass
    human_judgment: false

duration: ~46min (from 30-04's own completion commit, 3fea044, to this plan's last commit, 1fc07f2)
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 05: Re-pin every check plan 30-03 and 30-04 owed the accordion Summary

**Twelve replacement checks in `companion/test_config_page.py` pay back every `_ASPECT_REPIN_LEDGER` row owed to 30-05 — the Aspect card's full shape, per-theme coverage, default selection, arrivals override, calendar palette, rules placement/label/copy, pinned English strings, scoped render and live-preview figure — plus all 11 of 30-04's own escalated, unledgered misses across both harnesses, leaving `test_config_page.py` at 269/269 and `test_companion_app.py` at 317/317, with `test_browser_ux.py` untouched at exactly its documented 7-check floor.**

## Performance

- **Duration:** ~46 min (from 30-04's own completion commit, `3fea044`, to this plan's last commit, `1fc07f2`)
- **Started:** 2026-09-22 (following 30-04's completion)
- **Completed:** 2026-09-22T18:28:28+02:00
- **Tasks:** 3/3 (executed as a single continuous editing pass — see Deviations for the process note on commit granularity)
- **Files modified:** 2 (`companion/test_config_page.py`, `companion/test_companion_app.py`)

## Accomplishments

- **`companion/test_config_page.py`** (257 → 269 checks): twelve new replacement checks land, each named in `_ASPECT_REPIN_LEDGER` and each derived from `device_config`/`COLOUR_USAGES` at check time:
  - `_aspect_card_full_shape_checklist()` — the relationship check: exactly one `.aspect-card` after the Look intro; the four accordion rows' `data-usage` values, in document order, equal `COLOUR_USAGES` exactly; exactly one row `open` (departures); only the last row `usage-row--secondary`; exactly one `.palette` grid per theme row and none in the rules row; zero occurrences of any retired-mechanism token (`theme-carousel`/`frame-colours`/`colour_usage`/`usage-panel`/`__dots`/`theme-chip-grid--strip`); and no `section-caption` paragraph immediately after the `<h2>`.
  - `_aspect_card_covers_every_registered_theme_with_own_id_and_label()` — per saved field (`theme`/`theme_arriving`/`calendar_theme_id`), one radio per `THEME_IDS` entry in registry order, each carrying its own value/translated label/`data-preview-src`/`form=settings-form`, with the correct leading-option count (0 for departures, 1 each for arrivals/calendar).
  - `_aspect_card_default_selects_exactly_the_white_departures_option()` — exactly one checked radio per group, asserted per group rather than as a page-wide count.
  - `_aspect_arrivals_row_carries_leading_option_no_checkbox()` — the leading option's own markup (`class="leading-option"`, `form=settings-form`) and a page-wide absence of `type="checkbox"`.
  - `_aspect_arrivals_override_preselects_the_override_not_same_as_departures()` — a stored override checks itself (not the leading option, not departures), names itself in the row's own summary meta, and leaves the calendar row's own Same-as-departures state unaffected in the same render.
  - `_aspect_calendar_row_palette_populated_in_order()` — the calendar palette is a real `role="radiogroup"`, populated in registry order, carrying no `id` of its own.
  - `_rules_row_renders_inside_aspect_after_form()` — the settings form's own `</form>` (anchored off its own opening tag, not a bare page-wide search — see Deviations) precedes the Aspect card, which precedes the rules row; every theme/theme_arriving/calendar_theme_id radio still carries `form=settings-form`.
  - `_aspect_rules_row_label_locked_verbatim()` — the locked `"Per-flight rules"` label plus a second lock: the rules row's empty-state meta reads `FRAME_COLOURS_RULES_EMPTY_META` verbatim, never ROADMAP's own paraphrase.
  - `_aspect_rules_copy_appears_escaped_verbatim()` — every rules-editor copy string, unchanged from the retired check's own body (the ledger's stated reason for retiring it turned out to be stale — see Deviations).
  - `_aspect_display_render_still_carries_every_pinned_english_string()` — the pinned set loses `FRAME_COLOURS_CAPTION`, gains `ASPECT_HEADING`, keeps everything else (including `CALENDAR_CAPTION`, which survives until 30-06).
  - `_aspect_scoped_render_carries_hidden_fields_and_omits_other_groups()` — every prior assertion unchanged, rules-row locator repointed onto `data-usage="rules"`.
  - `_aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions()` — the figure's new class (`theme-live-preview aspect-card__preview`), plus a new relationship: the figure's own index precedes the first `name="aspect-rows"` row's.
  - `_rules_panel_segment()` renamed to `_rules_row_segment()`, repointed from the retired `COLOUR_USAGE_PANEL_TARGET_ATTR` locator onto the row's own `data-usage` attribute — the single fix that pays back all seven Group-A checks 30-04's own escalation inventory named (`_rules_section_empty_state_then_list_once_a_rule_exists`, `_rules_no_select_and_three_named_radios_one_checked`, `_rules_empty_state_carries_no_heading_element`, `_rules_suggestion_chips_present_with_data_and_absent_with_no_events`, `_plain_render_carries_both_disclosures_in_full_never_collapsed`, `_rules_section_carries_no_dirty_section_attr`, `_calendar_d01_registry_entries_never_appear_in_rules_list`).
  - `_settings_pages_editorial_floor_render_level_both_languages`'s own `_FLOOR_MIN_MEASURED["display"]` re-derived by running (16 measured → 12, minimum 14 → 10; `/device` unaffected).
  - `_display_renders_one_chip_density_and_a_swatch_legend_under_every_grid` rewritten in place as `_display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend` — asserts the real new shape (one `.theme-chip-grid`, the rule-add form's own compact grid, plus three legend-free `.palette` grids) rather than the retired four-identical-grids shape.
  - `_ASPECT_REPIN_LEDGER`'s own 12 rows owed to 30-05 cleared (`owed_by=""`); three carry a divergence note (see Decisions) explaining a forced rename away from the ledger's own predicted same-name replacement.
  - `EXPECTED_CHECK_COUNT` re-derived 257 → 269 by running.
- **`companion/test_companion_app.py`** (317 checks, unchanged count): `_display_and_device_pages_split_the_groups`' `rules_panel_marker` repointed from `data-usage-panel-target="rules"` to `data-usage="rules"`; `_site_wide_editorial_floor_all_six_routes_both_languages`' `per_route_min[DISPLAY_ROUTE]` re-derived 13 → 9 and `site_total_min` re-derived 55 → 47, matching the real measured drop (Display 15 → 11 captions; site-wide total 62 → 54).
- All three harnesses re-verified: `test_config_page.py` 269/269, `test_companion_app.py` 317/317, `test_browser_ux.py` unchanged at 84/91 (the same 7 named checks 30-04 documented — 3 pre-existing floor, 4 routed to 30-08). `scripts/run-all-tests.sh` (JOBS=4) reports 21/22 harnesses PASS on two separate runs; the one FAIL is `test_browser_ux.py`'s own documented floor.

## Task Commits

1. **Tasks 1+2+3 (test_config_page.py): re-pin every owed check, clear the ledger, fix the two in-file escalated misses** — `01f91c9` (test)
2. **Task 3 (test_companion_app.py): repoint the two escalated CFG-85 misses in this file** — `1fc07f2` (test)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `companion/test_config_page.py` — 12 new/renamed replacement checks, `_rules_row_segment()` (renamed from `_rules_panel_segment()`), `_aspect_usage_row_bounds()`/`_ASPECT_RETIRED_MARKUP_TOKENS` shared helpers, `_ASPECT_REPIN_LEDGER`'s 12 owed-to-30-05 rows cleared, `_FLOOR_MIN_MEASURED` re-derived, the chip-density/legend check rewritten in place, `EXPECTED_CHECK_COUNT` 257 → 269.
- `companion/test_companion_app.py` — `_display_and_device_pages_split_the_groups`' locator repointed, `_site_wide_editorial_floor_all_six_routes_both_languages`' per-route/site-wide minimums re-derived.

## Mutation Test Results (Task 1's four + Task 2's two, all six required)

Each mutation applied directly to `companion/pages/config_page.py`, run against `companion/test_config_page.py`, failure message captured, then reverted with `git checkout-index -f -- companion/pages/config_page.py` and `__pycache__` cleared.

1. **Swap rows 2 and 3 at the call site (order).** `rows_html = departures_row + calendar_row + arrivals_row + rules_row`:
   > `expected the accordion rows' data-usage values, in document order, to equal COLOUR_USAGES exactly, got ['departures', 'calendar', 'arrivals', 'rules']`

2. **Add ` open` to row 2 (exactly-one-open).** `arrivals_row = _usage_row_html(..., is_open=True)`:
   > `expected only the departures row open by default, got ['departures', 'arrivals']`

3. **Give `_palette_grid_html()` an `id` (duplicate id).** `'<div class="palette" role="radiogroup" id="palette"%s>...'`:
   > `expected _palette_grid_html() to emit no id attribute of its own — three call sites on one page sharing an id is the exact CFG-68 collision trap` (also independently caught by `_aspect_calendar_row_palette_populated_in_order` and the pre-existing page-wide duplicate-id check — three checks, non-vacuous from three directions)

4. **Drop the arrivals leading option.** Removed `leading_html=arrivals_leading` from the arrivals `_palette_grid_html()` call:
   > `expected 1 leading Same-as-departures option(s) for 'theme_arriving', got 0` (also independently caught by two more checks)

5. **Move the preview below the rows.** Swapped `live_preview_html`/`rows_html` in `_aspect_card_html()`'s own return tuple:
   > `expected the live preview figure ABOVE the first accordion row`

6. **Move the Aspect card before `</form>`.** Moved the `"</form>"` literal in `render()`'s own return format string one placeholder later:
   > `expected </form> < the Aspect card < the rules row, got positions 43012/3391/25748` (also independently caught by the pre-existing no-nested-`<form>` check, since moving the card into the form now nests the rule-add form's own `<form>` inside it)

Mutation 6 exposed a real bug in this check's own first draft — see Deviations below for the fix and why the mutation initially passed silently.

## `EXPECTED_CHECK_COUNT` Trajectory (as required by Task 3)

| Point | `companion/test_config_page.py` count |
|---|---|
| Before Phase 30 (pre-30-03) | 274 |
| After 30-03's retirements | 257 |
| Now (after 30-05) | **269** |

12 new/net checks land this plan (12 payback checks; the density/legend check and the `_FLOOR_MIN_MEASURED` fix are in-place edits, contributing 0 to the count).

## Ledger Tally (as required by Task 3)

`_ASPECT_REPIN_LEDGER` — 19 rows total, none deleted:

- **Cleared this plan (12):** `_frame_colours_card_covers_every_registered_theme_with_own_id_and_label`, `_frame_colours_card_default_selects_exactly_the_white_departures_option`, `_frame_colours_arrivals_grid_carries_leading_chip_no_checkbox`, `_frame_colours_arrivals_override_preselects_the_override_not_same_as_departures`, `_frame_colours_card_full_shape_checklist`, `_rules_section_renders_inside_frame_colours_after_form`, `_rules_copy_appears_escaped_verbatim`, `_frame_colours_rules_row_label_locked_verbatim`, `_calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order`, `_english_display_render_still_carries_every_pinned_english_string`, `_scoped_render_carries_hidden_fields_and_omits_other_groups`, `_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions`.
- **Still owed (7):** 5 to 30-06 (`_calendar_placement_after_display_form_close_with_dirty_attr`, `_calendar_group_no_inline_js_and_chip_grid_cross_submits_form`, `_display_h2_order_matches_d12_after_calendar_placement_fix`, `_title_form_inventory_classifies_every_h2_text_heading_on_both_routes`, `_no_card_builder_function_ever_calls_section_intro_html`); 2 to 30-07 (`_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable`, `_segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif`).

`_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()` PASSES against this state.

## Decisions Made

See `key-decisions` in the frontmatter above for the three substantive ones: the forced rename on three ledger rows whose predicted same-name replacement collides with the guard's own "retired name has no def" clause; the stale "why" on `_rules_copy_appears_escaped_verbatim`'s own ledger row (FRAME_COLOURS_ROW_LABELS survives unrenamed, contrary to the row's own stated reason); and the `_rules_row_renders_inside_aspect_after_form` `</form>`-locator fix (see Deviations for the mutation that caught it).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_rules_row_renders_inside_aspect_after_form`'s own `</form>` locator silently resolved to the wrong form**
- **Found during:** Task 2's own required mutation test ("move the Aspect card before `</form>`")
- **Issue:** The check's first draft used `rendered.index("</form>")` — a bare, page-wide search for the FIRST `</form>` in the whole document. The Frame strip renders its own `quick_action__form` (a `<form>...</form>` pair) BEFORE `<form id="settings-form">` even opens, so this search always resolved to the Frame strip's own closing tag, not the settings form's — and that wrong value happened to satisfy the check's own `form_end < aspect_pos < rules_start` inequality regardless of where the real settings form actually closed. The RETIRED check this plan replaced (`_rules_section_renders_inside_frame_colours_after_form`) carried the identical bug, undetected until this plan's own required mutation testing exercised it.
- **Fix:** Anchored the search to the settings form's own opening tag first (`rendered.index('<form class="config-form" id="%s"' % SETTINGS_FORM_ID)`), then searched for `</form>` starting from that position — the settings form's OWN closing tag, never an earlier unrelated one.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** Re-ran mutation 6 after the fix — the check now correctly fails with `expected </form> < the Aspect card < the rules row, got positions 43012/3391/25748`. Full suite re-confirmed green at 269/269 after the fix landed.
- **Committed in:** `01f91c9` (the fix is folded into the single check's own commit; the buggy draft was never itself committed)

**2. [Escalated per 30-04-SUMMARY.md's own instruction, paid back not re-escalated] 11 of the 15 checks 30-04's own full-suite sweep found red and documented**
- **Found during:** Read of 30-04-SUMMARY.md's "Escalated Red-Check Inventory" before starting this plan's own work
- **Issue:** 30-04's own required full-suite sweep found 15 red checks across three harnesses that plan 30-03's own coverage ledger did not anticipate (a locator-loss root cause for 7, a stale hardcoded caption-count baseline for 2, and a retired-by-design property assertion for 1, in `test_config_page.py`/`test_companion_app.py`; 4 more, routed to 30-08, in `test_browser_ux.py`).
- **Fix:** All 11 checks routed to 30-05 by 30-04's own inventory are paid back in this plan — 7 via the `_rules_row_segment()` locator repoint, 2 via re-derived caption-count minimums (`test_config_page.py`'s own `_FLOOR_MIN_MEASURED` and `test_companion_app.py`'s own `per_route_min`/`site_total_min`), 1 via the chip-density/legend check's own rewrite, and 1 (`_display_and_device_pages_split_the_groups`) via the same locator repoint applied to `test_companion_app.py`.
- **Files modified:** `companion/test_config_page.py`, `companion/test_companion_app.py`
- **Verification:** Both harnesses green (269/269, 317/317); `test_browser_ux.py`'s own 4-check subset of the original 15 (routed to 30-08, not this plan's scope) left untouched and reconfirmed unchanged at 84/91.
- **Committed in:** `01f91c9`, `1fc07f2`

---

**Total deviations:** 1 auto-fixed bug (a locator gap this plan's own mutation testing caught and fixed before committing) + 1 large, already-escalated category paid back in full per its own routing (11 of 15 checks; the remaining 4 correctly stay 30-08's scope)
**Impact on plan:** The locator fix was necessary for the replacement check to genuinely prove the property it claims — without it, the check would have silently passed the exact mutation Task 2 requires it to catch. No production file touched anywhere in this plan.

## Issues Encountered

None beyond the deviation documented above. A transient API/network interruption occurred mid-verification (after `test_config_page.py` first reached 269/269, before the `test_companion_app.py`/`run-all-tests.sh` re-confirmation and commits) — resumed cleanly from the coordinator's own resume instructions with no work lost; the interruption is not a plan-content issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/test_config_page.py` is green at `EXPECTED_CHECK_COUNT = 269`; `companion/test_companion_app.py` is unchanged in count at `317/317`; `companion/test_browser_ux.py` is unchanged at `84/91` (3 pre-existing floor + 4 rows still owed to 30-08).
- `_ASPECT_REPIN_LEDGER` carries 7 remaining rows, all correctly owed to 30-06 (5) or 30-07 (2) — 30-05 owes nothing further.
- `scripts/run-all-tests.sh` (JOBS=4) reports 21/22 harnesses PASS on two independent runs; the one reported FAIL is `test_browser_ux.py`'s own documented, unchanged 7-check floor — not a regression from this plan.
- `companion/pages/config_page.py` is byte-identical to 30-04's final commit (`3fea044`) — this plan touched zero production files, confirmed by `git diff --exit-code`.
- 30-06 can proceed against a fully re-pinned `test_config_page.py`/`test_companion_app.py` baseline; its own 5 ledger rows (calendar placement/inline-JS/h2-order/title-inventory/no-card-builder) are the only ones it needs to pay.
- 30-08 inherits the same 6 ledger rows 30-03 already routed to it (all in `test_browser_ux.py`) plus the 4 newly-discovered `.theme-chip`-locator misses 30-04's own inventory documented — none of those are touched by this plan, per the plan's own explicit instruction not to.

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-05-SUMMARY.md`
- FOUND: commit `01f91c9` in `git log --oneline --all`
- FOUND: commit `1fc07f2` in `git log --oneline --all`
