# Phase 61 Plan 97: Design system (admin Components page, one component per family) Summary

An admin-only `/components` page renders every shared component through its real Python helper in every state, one 56-case geometry/contrast browser test and a catalogue guard keep it honest, and the parallel segmented-control, chip, button, switch, field and pill variants were folded onto one component each (owner decision D51, audit 3 findings V03, V04, V06, V07, V09, V10, V26, V29).

## Inventory (before the work)

| Family | Variants found | Outcome |
|--------|----------------|---------|
| Switch | `ui_components.quick_switch_html` (`.switch`), hand-copied `.switch` markup in `users_page` and `settings/theme.py` (Same as departures), native checkbox `.settings-checkbox` in the quiet-hours dialog | one `switch_button_html` for every `.switch`; the checkbox is drawn as the same switch (`form_switch_html`) |
| Select / sort menu | `ui_filter.sort_menu_html`, `ui_entity_list.row_menu_html` | already one helper each; catalogued |
| Segmented control | `.theme-form` (theme/language buttons, look kind radios in `settings/rules.py`, update type chooser), `.look-seg` (Fond / Bande), `.personalisation-nav` (Departures/Arrivals/Special looks tabs, fleet tabs), `.filter-chip` (Flights chips, collection chips), audit link chips (`filter-chip--current`, faint in dark, cut off), `.place-modes`, `.space-switch` | one token contract `--seg-edge/--seg-selected-bg/--seg-selected-fg/--seg-idle-fg`; three helpers in `ui_segmented.py` (radios, buttons, links) now build theme/language, rule kind, update type, fleet tabs and personalisation tabs; audit chips use `ui_filter.chip_links_html`; selected is a solid pill everywhere, 44px segments |
| Chips / filter chips | radios in `ui_filter.filter_bar_html`, hand-built radios in `history_page`, hand-built links in `audit_page`, own scroll rules in `.audit-chips` and `.collection-controls` | link chips wrap instead of scrolling, collection chips shrink to fit (no cut label), shared selected style |
| Buttons | global `button` (grey), `button[type=submit]` (primary), `.calendar-disconnect-btn` (secondary, 30px, button and link forms), `.dirty-bar__save/__cancel`, `.co-manager__remove-btn`, `.special-row__remove`, per-page classes | one `.btn` with `--primary/--secondary/--ghost/--danger/--icon` (44px) and `button_html` / `icon_button_html`; `calendar-disconnect-btn` removed everywhere, Save bar, co-manager remove, special-look remove, dialog destructive submit, Clear buttons migrated |
| Cards / sections | `ui_groups.group/group_panel/row/hero`, `stat_tile`, `status_row` | already shared; catalogued |
| Tables | `ui_components.data_table` | catalogued |
| Dialogs / sheets | `ui_modal.dialog_html`, `sections_dialog_html` | catalogued; destructive submit is `.btn--danger` |
| Toasts | `toast_html` and parts, `anomaly_banner` | catalogued (docked on the page) |
| Badges / pills | raw `<span class="banner__pill">` at eight sites, `status_dot`, charging pill | `pill_html` (used by audit and co-manager pages) |
| Empty states | `empty_state`, `filter_empty_html` | catalogued; Clear is the standard secondary button |
| SaveBar | `ui_save_bar.save_bar_html` | primary + secondary `.btn` |
| Inputs | text fields in `.modal__field` (no width rule), wake interval number, search | `text_field_html`; `.modal__field > input` is full width; wake interval 11rem with a short placeholder |
| Page header | `ui_components.page_header` | catalogued |

## What changed

- Components page: `companion/pages/components_page.py` (catalogue of 13 families, states, helper list per family, EXEMPT table with reasons), route in `companion/console_components.py` (admin only, 404 for others, in the access matrix rows, not in the nav, linked from the Fleet System view footer), French strings in `companion/i18n_fr/components.py`. `companion/app.py` untouched (1479 lines).
- Fixes: V03/V04/V26 (one segmented look, solid selected pill in both themes, visible track edge), V03/V07 (chip rows wrap or shrink, no cut label), V06 (empty Flights search keeps whole-history chip counts via `history_query.Result.chip_counts`, Clear is the standard secondary button), V09 (wake interval input wide enough, shorter French placeholder), V10 (rename input full width, visible primary Save), V29 (look sheet hides Main colour/Background/Stripe while "Same as departures" is on).
- Docs: `.claude/skills/sketch-findings-skypane/references/component-catalogue.md` (catalogue, rule "new UI uses a catalogue component or extends it and its page entry") indexed in `SKILL.md`.

## Tests

- `companion/test_browser_components_page.py`: the Components page at 360 and 1280, light and dark, EN and FR (8 renders x 7 checks): no overflow, centred labels, selected pill against track >= 3:1 and text >= 4.5:1 in every segmented control, buttons >= 44px and >= 4.5:1, 44px targets, switch knob inside track with distinct on/off colours, no sibling overlap, a dialog opens inside the viewport; plus rename field, wake interval field and empty Flights search checks.
- `companion/test_components_page.py` (non-browser): admin 200 / user 404, not in the nav but linked from System, French render, every catalogued helper is called while the page renders, every public helper of the component modules is catalogued or exempt with a reason (the guard against a new helper skipping the page).
- Tests that pinned old classes were retargeted in place (`calendar-disconnect-btn` -> `.btn` variants, `.audit-chips` -> `.filter-bar__chips--links`, 28px segment height -> 44px, 12% accent wash -> the selected pill token, 8ch wake width -> 11rem, the "no .btn-- family" guards -> only the shared variants, accent budget allows the theme/language selected pill, Flights empty search chips, look-dot target measure while following departures). No test was weakened or skipped.

## Deviations from Plan

- Per-family unification is at the CSS-token and helper level for the segmented family (the `.theme-form`, `.personalisation-nav`, `.filter-chip` and `.look-seg` class names stay, because tests and scripts key on them); the tracks use the glass token (a glass fill where backdrop-filter exists) with a visible `--seg-edge`.
- Space switch and place-mode switch keep their own geometry (they use the tokens only for the selected look where already accent).
- Select/dialog/table/card families already had one helper each; no markup change.

## Known limits / not done

- The `.space-switch` and `.place-modes` rules were not folded onto the token set beyond colours.
- Hand-built pill markup remains at credits, detection summary, place, update and account pages (only audit and co-manager pages moved to `pill_html`).
- Dialogs are rendered closed with triggers on the Components page (an open dialog would overlay the page); the browser test opens one.
- `companion/test_browser_round8_fixes.py::test_the_users_self_row_is_not_wide_and_frames_never_wrap_on_desktop` fails locally before and after this plan (passes in CI).
