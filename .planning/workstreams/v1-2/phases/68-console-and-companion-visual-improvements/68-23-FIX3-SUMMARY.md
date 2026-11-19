---
phase: 68-console-and-companion-visual-improvements
plan: 23-fix3
subsystem: companion
tags: [airlines, update, removals]
---

# Phase 68 Plan 23 Fix 3: drop the "Named by hand" chip and the update confirmation's "For <hardware>" line

Owner-decided removals. No state or requirement command was run, CON-01 is not ticked, ROADMAP unchanged.

## What changed

- The "Named by hand" / "Nommée à la main" pill is gone from the airlines editor table: `HAND_NAMED_TEXT`, its i18n id `airlines.named_by_hand`, the pill markup in `airline_table._name_cell` and the then-dead `.airlines-namebox > .airlines-pill` rule are removed. `.airlines-pill` itself stays (the "Default" star pill uses it). A hand-named airline keeps its row and its row menu ("Delete my name" and the other actions are untouched); the row is now told apart only by that menu entry, as in the mockup.
- The "For <hardware>" / "Pour <matériel>" line is gone from the install-confirmation page of the firmware update flow (`update_page.CONFIRM_TYPE_TEMPLATE`, the line's markup and the orphan id `update.for_hardware_type_s`). The confirmation still carries the chosen type in its hidden field when the chooser is shown.
- Tests: `test_airline_editor` and `test_browser_airline_table` assert the pill is absent; `test_browser_airline_editor` selects hand-named rows by their delete-name form instead of the pill; `test_update_actions` asserts the confirmation no longer names the hardware label (and still carries the type only with the chooser).
- `render_baseline.json` regenerated once at the end (captures changed).

## Verification

ruff, mypy, function size (max 80), comment-history, `companion/app.py` 1490 lines. The airline/update/i18n/stylesheet/guard/render subset (1751 tests) and `stub-server/test_phase47_freeze.py` pass. Four failures also occur on a clean checkout of the previous commit and are not caused by this change (recorded, not fixed): `test_companion_app_03::test_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard`, `test_config_page_05::test_aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions`, `test_sign_in_surfaces::test_error_pages_render_byte_identical_output` and `::test_shell_without_a_principal_is_byte_identical_to_before`.

## Design-system divergences

None. Both removals follow the owner decision and the mockups; no new component, token or string.
