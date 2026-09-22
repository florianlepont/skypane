---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 03
subsystem: testing
tags: [test-harness, coverage-ledger, playwright, regex-derivation, ci]

requires:
  - phase: 30-02
    provides: "_palette_swatch_html()/_palette_chip_html()/_palette_grid_html()/_usage_row_summary_html() — the new palette renderers this plan's re-homed check and ledger comments reference, called by nothing yet"
provides:
  - "_ASPECT_REPIN_LEDGER (companion/test_config_page.py) — 19 rows naming a retired check's PROPERTY, its future replacement, and which of 30-05/06/07 owes it"
  - "_ASPECT_REPIN_LEDGER (companion/test_browser_ux.py) — 6 rows, all owed by 30-08, this file's own copy since its guard reads its own file's source"
  - "_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement() — the guard check, registered once per file, proven non-vacuous against three deliberately wrong ledgers"
  - "_the_display_page_carries_exactly_one_radio_set_per_theme_field() (companion/test_config_page.py) — the one re-homed property, written with zero retired-mechanism vocabulary"
  - "_the_theme_still_saves_with_scripts_blocked() / _arrivals_still_saves_with_scripts_blocked() (companion/test_browser_ux.py) — the two narrowed scripts-blocked-save proofs, markup-agnostic half only"
affects: [30-04, 30-05, 30-06, 30-07, 30-08]

tech-stack:
  added: []
  patterns:
    - "A coverage-gap ledger (_ASPECT_REPIN_LEDGER: retired/property/replacement/owed_by/why) plus a self-reading guard check turns 'we deleted a check early' from a silent coverage loss into a red build the moment a later plan forgets to pay it back."
    - "When a plan's own <verify> script uses a naive whole-file substring check (`if token in src`) to prove a retired identifier is gone, and the SAME plan requires documenting the retirement in a comment that necessarily names that identifier, the check collides with its own required documentation. Fix: strip full-line comments before the substring search, not the documentation."
    - "Before retiring a family of small JS-string helper constants (selector/probe literals), grep the WHOLE file for every one of them individually, not just the ones the plan names by name — helpers the plan doesn't mention by name (here: _SETTLE_CAROUSEL, _CAROUSEL_INSTANCE_PROBE, _TOGGLE_OWN_DISCLOSURE) can still be orphaned by the same wave of check deletions and must go with them or become dead code."

key-files:
  created: []
  modified:
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py

key-decisions:
  - "The plan's own <derivation_first> script under-counts test_browser_ux.py's affected blocks (11 found vs. the plan's stated 13) because several routing-table-listed checks (_selecting_a_theme_chip_answers_and_moves_no_layout_box, _the_live_preview_crossfade_settles_correct_through_its_own_listener, _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom, _images_hold_their_place_before_they_arrive) reference `.theme-chip`/`data-usage-panel-target` rather than the six literal retiring-identifier patterns the derivation regex matches. Resolved by grepping EVERY constant's real consumers whole-file (not trusting either the narrow regex or the routing table's prose alone): _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom turned out to be THEME_PREVIEW_SEL's ONLY surviving consumer in the whole file, which is direct evidence it must NOT be touched in this plan (the plan's own instruction says THEME_PREVIEW_SEL 'survives... other checks read it' — that claim is only true if this check stays). _selecting_a_theme_chip_answers_and_moves_no_layout_box, _the_live_preview_crossfade_settles_correct_through_its_own_listener and _images_hold_their_place_before_they_arrive were left untouched for the identical reason: none references a retiring identifier, Task 3's own <action> text never names them, and the <verify> script's literal checks are silent about them. _the_no_js_floor_holds_for_both_settings_pages is the one exception: the plan's own <no_js_floor_note> explicitly says 'The ledger row for _the_no_js_floor_holds_for_both_settings_pages must state this discrepancy in its own comment' — a directive too specific to be read any way but 'delete and ledger this one now' — so it was retired despite not being named in Task 3's five-carousel-checks bullet."
  - "Rule 1 bug in the ledger guard's own first draft: the key-presence loop treated `owed_by: \"\"` (the legitimate 'repaid IN THIS FILE' signal the plan's own spec calls for) as a missing/empty key, which made that branch of the guard structurally unreachable — no row could ever legitimately claim in-file repayment. Fixed by splitting the required-non-empty keys (retired/property/replacement/why) from the merely-required-present key (owed_by, which may be the empty string). Caught during the plan's own mandated mutation test (a): a row with owed_by cleared and no matching replacement def was supposed to fail via the 'repayment claim is false' branch, and initially failed via the wrong branch ('missing/empty key') instead — same FAIL verdict, wrong reason, so the bug was still worth fixing rather than leaving a passing-for-the-wrong-reason guard."
  - "Rule 1 bug in Task 3's own inline <verify> script: `if token in src` for THEME_STRIP_SEL/THEME_PAGERS_SEL/THEME_DETAILS_SEL/_STRIP_PROBE is a plain whole-file substring search, which the SAME plan's own required retirement-comment convention ('name what used to live here') necessarily trips — a comment naming the retired constant for a future reader collides with a check meant to prove the constant is gone. Verified the same underlying property (no live CODE reference, i.e. no use as a Python identifier) with a comment-stripped search instead, and confirmed by direct inspection that all four occurrences are inside two retirement-comment blocks, never a code reference."

patterns-established:
  - "companion/test_browser_ux.py now carries its own _ASPECT_REPIN_LEDGER + guard, deliberately NOT shared with companion/test_config_page.py's copy — each guard reads its OWN file's source via __file__, which is what makes it a guard rather than a cross-file assumption a future refactor could silently break."

requirements-completed: [CFG-85]

coverage:
  - id: D1
    description: "test_config_page.py: 22 checks referencing CFG-85's retiring identifiers are removed (3 retired outright with no ledger row, 19 deleted-and-ledgered to 30-05/06/07), one new check re-homes the one surviving property (page-wide theme-radio-set uniqueness) with zero retired-mechanism vocabulary, EXPECTED_CHECK_COUNT re-derived 277 -> 257 by running"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (run) — 257/257 checks pass"
        status: pass
      - kind: other
        ref: "inline verify script from 30-03-PLAN.md Task 1 — 19 well-formed ledger rows, every retired name has no surviving def, every owed_by in {30-05,30-06,30-07}, the re-homed check's own source contains none of (strip/pager/carousel/dots/usage-panel/disclosure)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A non-vacuous coverage-gap guard (_ASPECT_REPIN_LEDGER + _every_aspect_repin_ledger_row_names_a_live_or_owed_replacement) is added to test_config_page.py, proven against three deliberately wrong ledgers with all three failure messages quoted and reverted"
    requirement: CFG-85
    verification:
      - kind: other
        ref: "mutation (a): owed_by cleared on a row whose replacement has no def — FAILed with \"ledger row '_frame_colours_card_covers_every_registered_theme_with_own_id_and_label' names owed_by='' (repaid in THIS file) but its replacement '_aspect_card_covers_every_registered_theme_with_own_id_and_label' has no def here — the repayment claim is false\", then reverted"
        status: pass
      - kind: other
        ref: "mutation (b): a retired check's def re-inserted into the file — FAILed with \"retired check '_frame_colours_card_covers_every_registered_theme_with_own_id_and_label' still has a def in this file — a retired check left behind is the OTHER failure shape this guard exists to catch\", then reverted"
        status: pass
      - kind: other
        ref: "mutation (c): the ledger tuple emptied — FAILed with \"_ASPECT_REPIN_LEDGER is empty — this guard must never pass vacuously; if every row has genuinely been repaid, this check itself should be retired, not left to pass against nothing\", then reverted"
        status: pass
    human_judgment: false
  - id: D3
    description: "test_companion_app.py: _NO_JS_CONTROL_REGISTRY's carousel-pagers row is deleted outright (not repointed), THEME_CAROUSEL_WRAPPER_ATTR/_frame_colours_card_html no longer referenced anywhere in this harness, EXPECTED_CHECK_COUNT unchanged at 317 (a registry row is an assertion inside a check, not a check of its own), the contract machine and its four fixtures untouched"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py (run) — 317/317 checks pass"
        status: pass
      - kind: other
        ref: "inline verify script from 30-03-PLAN.md Task 2 — THEME_CAROUSEL_WRAPPER_ATTR/_frame_colours_card_html absent, 4 registry rows remain, git diff shows no hunk inside lines 7083-7240"
        status: pass
    human_judgment: false
  - id: D4
    description: "test_browser_ux.py: 6 checks referencing the retiring carousel are removed (2 retired outright, 4 ledgered to 30-08), 2 checks narrowed (markup-agnostic scripts-blocked-save half kept, strip-probe half ledgered), the shared selector/probe block retired with its last consumer (grepped whole-file first), THEME_PREVIEW_SEL kept live via its one surviving consumer, EXPECTED_CHECK_COUNT re-derived 96 -> 91 by running"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_browser_ux.py (run) — 91/91 registered, 88/91 pass; the 3 FAILs are the pre-existing floor documented in 30-01/30-02-SUMMARY.md (leave-guard-armed-before-commit, fallback-Save-click-timeout, wake-interval-echo), unchanged in count and unrelated to this plan's diff"
        status: pass
      - kind: other
        ref: "inline verify script from 30-03-PLAN.md Task 3, run against a comment-stripped source view (see key-decisions for why) — all clauses pass"
        status: pass
    human_judgment: false
  - id: D5
    description: "Plan-wide: exactly three changed files (all under companion/, all test harnesses), zero production files touched, every commit green at its own re-derived count"
    requirement: CFG-85
    verification:
      - kind: other
        ref: "git diff --stat 407b240 ccc275f — companion/test_browser_ux.py, companion/test_companion_app.py, companion/test_config_page.py only"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh (JOBS=4) — 21/22 harnesses PASS; companion/test_browser_ux.py reports FAIL only because of the 3 pre-existing floor failures above (main() returns 1 when passed != total), not a new regression"
        status: pass
    human_judgment: false

duration: 44min
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 03: Retire the pins before removing the thing they pin Summary

**Twenty-eight checks across three test harnesses that pin CFG-85's retiring frame-colours/carousel/colour_usage/usage-panel markup are retired or narrowed in one wave, each retired property either re-homed immediately or ledgered by name to the exact plan (30-05/06/07/08) that owes its replacement, with a self-reading guard check that turns a forgotten re-pin into a red build.**

## Performance

- **Duration:** ~44 min
- **Started:** 2026-09-22T14:08:13Z
- **Completed:** 2026-09-22T14:52:00Z (approx)
- **Tasks:** 3/3
- **Files modified:** 3 (`companion/test_config_page.py`, `companion/test_companion_app.py`, `companion/test_browser_ux.py`)

## Accomplishments

- **`companion/test_config_page.py`** (277 → 257 checks): three checks pinning the retiring departures-strip/dots-row/full-grid-pagers markup are retired outright (no surviving property once the accordion replaces them); one new check, `_the_display_page_carries_exactly_one_radio_set_per_theme_field()`, re-homes the one property that DOES survive — the whole Display page carries exactly `len(device_config.THEME_IDS)` radios named `theme` — written with zero references to a strip, pager, gate, disclosure or dots row (confirmed by a source-level scan for those exact words). Nineteen more checks are deleted and ledgered into a new `_ASPECT_REPIN_LEDGER` tuple, each row naming the deleted check's PROPERTY (not its markup), a proposed replacement name, and which of 30-05/30-06/30-07 owes it. A new guard check, `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()`, reads this file's own source and fails the harness if any row's replacement is neither present nor owed, or if a retired name's `def` is left behind — proven non-vacuous against three deliberately wrong ledgers (see coverage D2).
- **`companion/test_companion_app.py`** (317 checks, unchanged): `_NO_JS_CONTROL_REGISTRY`'s `"the theme carousel's two pagers (D5)"` row is deleted outright per 30-RESEARCH.md's own Pitfall 2 — not repointed at the palette radios, since the accordion introduces zero `.js`-gated elements and repointing would claim a JS-optionality property never at risk for them. The registry's header comment now records this argument for a future reader. `THEME_CAROUSEL_WRAPPER_ATTR` and `_frame_colours_card_html` no longer appear anywhere in this harness.
- **`companion/test_browser_ux.py`** (96 → 91 checks): two checks retire outright (scroll-into-view and per-carousel disclosure toggling have no meaning over a static wrapping grid); four more (including `_the_no_js_floor_holds_for_both_settings_pages`, per the plan's own explicit `<no_js_floor_note>` instruction) are deleted and ledgered to 30-08 in this file's own `_ASPECT_REPIN_LEDGER`. The two scripts-blocked-save proofs are narrowed — the markup-agnostic `_persist_without_js()` half survives verbatim under new names (`_the_theme_still_saves_with_scripts_blocked`, `_arrivals_still_saves_with_scripts_blocked`); the trailing strip-probe halves are ledgered. The shared carousel selector/probe block (`THEME_STRIP_SEL`, `THEME_PAGERS_SEL`, `THEME_DETAILS_SEL`, `_STRIP_PROBE`, and three more helper constants the plan didn't name individually — `_SETTLE_CAROUSEL`, `_CAROUSEL_INSTANCE_PROBE`, `_TOGGLE_OWN_DISCLOSURE` — found orphaned by the same grep-before-delete pass) is retired with its last consumer. `THEME_PREVIEW_SEL` survives, because `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom` — deliberately left untouched by this plan — is still its one live consumer.
- All three harnesses green at their re-derived counts, at every commit in this plan. `scripts/run-all-tests.sh` shows 21/22 harnesses PASS; the one reported FAIL (`test_browser_ux.py`) is the pre-existing 3-failure floor documented since 30-01, unchanged in count.

## Task Commits

1. **Task 1: The ledger, its guard, and test_config_page.py's retirements** — `a224e4e` (test)
2. **Task 2: Delete the no-JS registry's carousel-pagers row** — `b03dc7e` (test)
3. **Task 3: Retire the carousel's browser checks; narrow the two scripts-blocked-save proofs** — `ccc275f` (test)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `companion/test_config_page.py` — 3 checks retired outright, 1 new re-homed check, 19 checks deleted and ledgered, `_ASPECT_REPIN_LEDGER` + its guard added. `EXPECTED_CHECK_COUNT` 277 → 257.
- `companion/test_companion_app.py` — `_NO_JS_CONTROL_REGISTRY`'s carousel-pagers row deleted with its own comment block; header comment records the accordion's deliberate non-registration. `EXPECTED_CHECK_COUNT` unchanged at 317.
- `companion/test_browser_ux.py` — 2 checks retired outright, 4 more deleted and ledgered, 2 checks narrowed (renamed), the shared selector/probe block (7 constants total, 4 named by the plan + 3 found orphaned) retired with its last consumer, this file's own `_ASPECT_REPIN_LEDGER` + guard added. `EXPECTED_CHECK_COUNT` 96 → 91.

## Derivation Script — Verbatim Output

Run against the SHA this plan started from (`407b240`), exactly as `<derivation_first>` specifies:

```
=== companion/test_config_page.py 25 blocks
   _frame_colours_card_covers_every_registered_theme_with_own_id_and_label def@2115   hits=4
   _frame_colours_card_default_selects_exactly_the_white_departures_option def@2135   hits=4
   _usage_row_summary_html_joins_row_label_and_meta_with_one_em_dash_source def@2310   hits=2
   _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox          def@6224   hits=2
   _frame_colours_arrivals_override_preselects_the_override_not_same_as_departures def@6278   hits=6
   _destructive_disconnect_is_secondary_and_selection_is_free_and_focusable def@7008   hits=3
   _rules_panel_segment                                                   def@7462   hits=1
   _frame_colours_card_full_shape_checklist                               def@7468   hits=12
   _rules_section_renders_inside_frame_colours_after_form                 def@7582   hits=3
   _rules_copy_appears_escaped_verbatim                                   def@7691   hits=1
   _frame_colours_rules_row_label_locked_verbatim                         def@7727   hits=4
   _calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order def@8250   hits=4
   _calendar_placement_after_display_form_close_with_dirty_attr           def@8346   hits=4
   _calendar_group_no_inline_js_and_chip_grid_cross_submits_form          def@8388   hits=2
   _display_h2_order_matches_d12_after_calendar_placement_fix             def@9289   hits=1
   _title_form_inventory_classifies_every_h2_text_heading_on_both_routes  def@9422   hits=1
   _no_card_builder_function_ever_calls_section_intro_html                def@9551   hits=2
   _english_display_render_still_carries_every_pinned_english_string      def@9970   hits=1
   _scoped_render_carries_hidden_fields_and_omits_other_groups            def@10036  hits=1
   _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions def@11404  hits=3
   _segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif def@11668  hits=1
   _the_departures_grid_is_the_one_renderer_presented_as_a_strip          def@12843  hits=4
   _the_carousel_dots_are_real_colours_and_the_strip_rules_are_declared   def@12995  hits=7
   _the_full_grid_sits_behind_a_native_details_and_the_pagers_behind_the_gate def@13166  hits=31
   _the_rendered_settings_page_carries_no_duplicate_id                    def@13431  hits=1
=== companion/test_browser_ux.py 11 blocks
   _display_page_height                                                   def@2870   hits=1
   _selecting_a_theme_chip_answers_and_moves_no_layout_box                def@5012   hits=2
   _the_live_preview_crossfade_settles_correct_through_its_own_listener   def@5304   hits=2
   _the_no_js_floor_holds_for_both_settings_pages                         def@5552   hits=2
   _the_slider_meets_its_floors_at_360px_in_both_themes                   def@13225  hits=8
   _arrivals_still_saves_with_scripts_blocked_through_its_own_carousel    def@13714  hits=1
   _each_carousels_own_disclosure_toggles_only_its_own_strip              def@13863  hits=3
   _arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed        def@13935  hits=7
   _keying_the_strip_selects_scrolls_into_view_and_moves_the_preview      def@14390  hits=4
   _scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_selects_nothing def@14600  hits=15
   _the_carousel_meets_its_floors_at_360px_in_both_themes                 def@15226  hits=6
=== companion/test_companion_app.py 3 blocks
   None                                                                   def@0      hits=2
   _theme_preview_script_es5_safe_and_no_html_write                       def@5435   hits=2
   _display_and_device_pages_split_the_groups                             def@8428   hits=1
```

**Disagreements against the plan's own `<routing_table>`, both explained:**

1. **`test_config_page.py`: 25 blocks found, not the plan's stated 24.** The extra block, `_usage_row_summary_html_joins_row_label_and_meta_with_one_em_dash_source` (added by 30-02, not in the routing table at all), is a **false positive**: it matches the regex only because it references `config_page.COLOUR_USAGE_DEPARTURES`/`COLOUR_USAGE_RULES` — constants 30-RESEARCH.md's own Structural/Markup Contract table explicitly says survive as `data-usage` attribute values, not the retiring `colour_usage` radiogroup field. This check tests a genuinely new, genuinely surviving renderer (`_usage_row_summary_html()`) and was correctly left untouched. 25 − 1 false positive = 24, matching the plan's own count exactly.
2. **`test_browser_ux.py`: 11 blocks found, not the plan's stated 13.** The gap is explained by the derivation regex's own narrowness, not a routing-table error: several routing-table rows (`_selecting_a_theme_chip_answers_and_moves_no_layout_box`, `_the_live_preview_crossfade_settles_correct_through_its_own_listener`, `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom`, `_images_hold_their_place_before_they_arrive`) reference `.theme-chip`/`data-usage-panel-target`/`window.SkyPaneLivePreview` rather than any of the six literal patterns (`frame[-_]colours|FRAME_COLOURS|theme[-_]carousel|THEME_CAROUSEL|colour_usage|COLOUR_USAGE|usage-panel`) the derivation script matches, so the mechanical script cannot see them at all regardless of which are ultimately touched. Two of the four (`_selecting_a_theme_chip_answers_and_moves_no_layout_box`, `_the_live_preview_crossfade_settles_correct_through_its_own_listener`) DO appear in the 11-block list because their bodies separately reference `data-usage-panel-target`, matching the `usage-panel` pattern; the other two (`_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom`, `_images_hold_their_place_before_they_arrive`) reference none of the six patterns anywhere and so never surface in the derivation at all, even though the routing table names them. See the key-decisions entry above for how each of these four was actually handled.

## Per-Constant Pre-Delete Grep Counts (companion/test_browser_ux.py's shared selector block)

Taken immediately before deleting the block, after the narrow/retire/ledger steps above had already run (so counts reflect ONLY the remaining consumer, `_the_carousel_meets_its_floors_at_360px_in_both_themes`, about to be deleted itself):

| Constant | Definition line | Remaining consumer sites | Disposition |
|---|---|---|---|
| `THEME_STRIP_SEL` | 13393 | 5 (all inside the about-to-be-deleted floors check) | Retired with its last consumer |
| `THEME_PAGERS_SEL` | 13394 | 0 | Retired (orphaned by the narrowed departures check) |
| `THEME_DETAILS_SEL` | 13395 | 4 (all inside the same check) | Retired with its last consumer |
| `THEME_PREVIEW_SEL` | 13396 | 3 (all inside `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom`) | **Kept** — this is its one surviving consumer |
| `_STRIP_PROBE` | 13400 | 1 (same check) | Retired with its last consumer |
| `_SETTLE_CAROUSEL` | 13432 | 1 (same check) | Retired — not named individually by the plan, found orphaned by the same grep pass |
| `_CAROUSEL_INSTANCE_PROBE` | 13454 | 0 | Retired — not named individually by the plan, found orphaned |
| `_TOGGLE_OWN_DISCLOSURE` | 13484 | 0 | Retired — not named individually by the plan, found orphaned |

## Re-derived `EXPECTED_CHECK_COUNT` Values

| File | Before | After | Delta | Confirmed by running |
|---|---|---|---|---|
| `companion/test_config_page.py` | 277 | 257 | −20 (−22 removed +1 re-homed +1 the ledger's own guard) | 257/257 |
| `companion/test_companion_app.py` | 317 | 317 | 0 (a registry row is an assertion inside a check, not a check) | 317/317 |
| `companion/test_browser_ux.py` | 96 | 91 | −5 (−6 removed +1 the ledger's own guard; 2 narrowed checks are a retarget, not a count change) | 91/91 registered, 88/91 pass (see below) |

## The `<no_js_floor_note>` Discrepancy — Flagged For The Developer

CFG-85's own requirement text includes "every row open with scripts blocked," and ROADMAP repeats it. The developer-approved sketch and 30-UI-SPEC.md ship a native `<details name="aspect-rows">` accordion where a grouped `<details>` set is mutually exclusive **by construction** — so "every row open" is not achievable while keeping the zero-script accordion the developer signed off on.

The property CFG-85 is actually protecting — no control is unreachable or unsaveable with scripts blocked — is met, and met **more strongly** than by a visible stack:

1. A closed `<details>`'s form controls remain in the DOM and DO participate in form submission.
2. `<summary>` is natively activatable by pointer and keyboard with scripts blocked, so a visitor can open any row themselves.
3. The preview is server-rendered for the SAVED theme in either case.

`_the_no_js_floor_holds_for_both_settings_pages` was retired and ledgered to 30-08 in this plan (per the plan's own explicit `<no_js_floor_note>` instruction, not just its routing-table row), with its former call site now carrying the full argument above so a future reader finds it in the code, not only in a planning file. **30-08's replacement must prove all three points above, with scripts blocked, at 360px, in both languages, with the verdict read back from disk — a stronger proof than the retired check's single collapsed-usage-panel count, never a quietly narrowed one.**

## Decisions Made

See `key-decisions` in the frontmatter above for the three substantive ones: (1) which of the routing table's "Ledger → 30-08" rows were actually actioned in this plan vs. left untouched, resolved by grepping every constant's real whole-file consumers rather than trusting either the derivation script or the routing table's prose alone; (2) the ledger guard's own `owed_by=""` handling bug, caught by the plan's own mandated mutation test; (3) Task 3's own `<verify>` script bug (a substring check colliding with its own required documentation convention).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The ledger guard's key-presence check made legitimate in-file repayment (`owed_by=""`) structurally unreachable**
- **Found during:** Task 1's mandated mutation test (a)
- **Issue:** The first draft of `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()` looped `for key in ("retired", "property", "replacement", "owed_by", "why"): if not row.get(key): return False`, which treats the empty string — the guard's OWN spec's signal for "repaid in this file" — as a missing key. No row could ever legitimately claim in-file repayment; that whole branch of the guard was dead code.
- **Fix:** Split the required-non-empty keys (`retired`/`property`/`replacement`/`why`) from the merely-required-present key (`owed_by`, which may legitimately be `""`), then re-ran all three mutation tests to confirm each still fails with the correct, specific message.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** All three mutation tests produce their intended failure message (quoted in coverage D2); reverted each time; `257/257` green after the fix.
- **Committed in:** `a224e4e` (the fix is folded into the single Task 1 commit; the bug was never itself committed)

**2. [Rule 1 - Bug] Task 3's own `<verify>` inline script collides with its own required retirement-comment convention**
- **Found during:** Task 3's `<verify>` step
- **Issue:** `if token in src` for `THEME_STRIP_SEL`/`THEME_PAGERS_SEL`/`THEME_DETAILS_SEL`/`_STRIP_PROBE` is a plain whole-file substring search. Task 1's own established convention (and this plan's own practice throughout) requires every retired check's replacement comment to explicitly name what used to live there — which necessarily spells out these exact constant names in prose, tripping the literal check.
- **Fix:** Verified the same underlying property — no live CODE reference to any of the four, i.e. neither a definition nor a usage as a Python identifier — with a comment-stripped search instead (drop lines whose stripped text starts with `#` before searching), then confirmed by direct grep that all four occurrences in the final file are inside exactly two documentation comment blocks (lines 13507-13508, 14392-14393), never a code reference.
- **Files modified:** none (the fix is in how the verification is performed, not in `test_browser_ux.py`'s own content)
- **Verification:** comment-stripped script prints `OK`; direct grep confirms zero non-comment occurrences of any of the four tokens.
- **Committed in:** `ccc275f`

**3. [Rule 1 - Bug] My own draft `EXPECTED_CHECK_COUNT` arithmetic for test_browser_ux.py was wrong before the first run**
- **Found during:** Task 3, first full `test_browser_ux.py` run after all edits
- **Issue:** The history comment I first wrote said "−6/+3 = −3" (96 − 6 + 3 = 93), incorrectly counting the two NARROWED checks (`_the_theme_still_saves_with_scripts_blocked`, `_arrivals_still_saves_with_scripts_blocked`) as net-new `check(...)` registrations. They are retargets of already-registered checks (matching this file's own established "retargeted in place" convention) and contribute 0 to the count; only the new guard check is a genuine addition.
- **Fix:** Re-derived by running (91 total `check(...)` calls registered, confirmed by two independent greps), corrected the history comment and `EXPECTED_CHECK_COUNT` to 91 before committing.
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** `91/91` registered; both `^\s*check($` grep and the harness's own printed tally agree.
- **Committed in:** `ccc275f` (caught and fixed before commit; never landed in an intermediate commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — one bug in the guard's own key-presence logic, one bug in the plan's own `<verify>` script colliding with its own documentation convention, one arithmetic slip in my own draft history comment, caught before committing)
**Impact on plan:** All three were necessary to reach a genuinely green, non-vacuous state at the correct counts. None changed which checks are retired/ledgered/narrowed from what the routing table specifies (beyond the documented interpretation decision on which of the ambiguous rows to action now vs. leave for 30-04/30-08 — see key-decisions). No production file touched anywhere in this plan.

## Issues Encountered

None beyond the deviations documented above. The 3 pre-existing `companion/test_browser_ux.py` floor failures (leave-guard-armed-before-commit, fallback-Save-click-timeout, wake-interval-echo — all in Display/Device save-bar and validation-echo behavior, unrelated to Aspect) carry forward unchanged from 30-01/30-02; re-confirmed at 88/91 with no new, reproducible failures and no change in count.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every commit in this plan lands green at its own re-derived count — 30-04 can start its markup rebuild without inheriting a wall of expected-red checks.
- Two coverage-gap ledgers now exist (`companion/test_config_page.py::_ASPECT_REPIN_LEDGER`, 19 rows across 30-05/06/07; `companion/test_browser_ux.py::_ASPECT_REPIN_LEDGER`, 6 rows all owed by 30-08), each proven non-vacuous and each enforced by its own file-local guard check. 30-05/30-06/30-07/30-08 must each delete their own owed rows in the SAME commit that lands the named replacement check — leaving a row behind after its replacement exists will fail nothing (the guard only catches a MISSING replacement, not a stale row), so this is a discipline the next four plans must self-enforce, not something this plan's own guard can catch for them.
- The `<no_js_floor_note>` discrepancy (CFG-85's "every row open" text vs. the developer-approved accordion's native mutual exclusivity) is recorded both in code (at `_the_no_js_floor_holds_for_both_settings_pages`'s former call site) and in this SUMMARY, flagged for the developer — 30-08's replacement check is the one that must resolve it by proving the stronger, alternative property, not by silently narrowing the claim.
- `_NO_JS_CONTROL_REGISTRY`'s header comment now records why the accordion introduces zero rows — a future reader who wonders "shouldn't the palette be registered here?" finds the argument at the registry itself.
- `companion/test_config_page.py` is green at `EXPECTED_CHECK_COUNT = 257`; `companion/test_companion_app.py` is unchanged at `317/317`; `companion/test_browser_ux.py` is green at `EXPECTED_CHECK_COUNT = 91` (91/91 registered, 88/91 passing against the documented pre-existing floor).

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-03-SUMMARY.md`
- FOUND: commit `a224e4e` in `git log --oneline --all`
- FOUND: commit `b03dc7e` in `git log --oneline --all`
- FOUND: commit `ccc275f` in `git log --oneline --all`
