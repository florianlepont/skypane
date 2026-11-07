# Phase 61 Plan 80: Airline editor in place and a compact audit log Summary

Owner decisions D45 D-C (airline editor, W97-W101) and D-D (audit log, W102): unidentified airlines are named directly in the Console Airlines table, every aircraft-type row is editable with a default state, artwork can be deleted back to the default, and the audit log is one compact expandable row per event.

## What changed

- **D-C inline resolution.** An unidentified prefix is one highlighted row holding a form: a name field with suggestions (one shared `<datalist>` of the known airlines), an aircraft-type select (the designators of the curated pictures, optional), Valider and Ignorer. Valider posts to the existing `/airlines/resolve` route with `inline=1`; the editor comes back with the row identified, no second step and no dialog. Ignorer is a `type="reset"` button: it clears the fields and saves nothing (there is no stored "ignored" state).
- **Hand-named airlines** stay in the table with a "Nommée à la main" pill. Their row menu has "Supprimer mon nom" (the existing manual-name delete route). The separate "Résolutions manuelles" section and its confirmation dialog (`companion/pages/airline_resolutions.py`) are gone.
- **System view.** The unresolved-prefixes table, its filter bar and the resolve dialog are removed from the System view (`health_page`, `health_sections`). The Identification row keeps its count and now links to `/airlines/manage`. The `/airlines/resolve` POST, its `return=health` allow-list and the no-script `?resolve=` section keep working.
- **Every type row is editable.** The picture slot of a type is now `{airline}-{slug}` for any classifiable aircraft type (the exact-type tier of `select_illustration()`), not only for the curated variants. The artwork upload and image routes accept those keys (`post_actions.illustration_filename_known()`, expand-only). A type row starts as "Celle de la compagnie" (the airline's picture, dimmed) with a "Personnaliser" action; with its own picture it shows "Illustration propre" and "Revenir à celle par défaut". Row menus: Changer l'illustration, Revenir à celle par défaut, Définir / Retirer comme type par défaut, Supprimer l'illustration. A star pill "Type par défaut" marks the airline's default type.
- **New actions.** `POST /airlines/artwork/delete` (removes the uploaded override file of a validated key; the vendored picture is never touched) and `POST /airlines/default-type` (sets or clears the default type). Both are admin-only on one frame, carry the CSRF token, redirect to the editor with a flash. `companion/airline_actions.py` holds them. Audit rows (same standalone pattern as the other console actions): `airline.resolve`, `airline.artwork_delete`, `airline.default_type`, with English and French labels.
- **Default type storage.** New `server/plane/airline_default_types.py`: `{state_dir}/airline_default_types.json`, `{airline illustration key: type code}`, never-raising validated load, validate-before-write, atomic write, cap. Nothing on the live frame's path reads it.
- **D-D audit log.** One `ul.audit-cards` glass group of `<details>` rows: Quand (time and age), Qui, Action, Résultat and a chevron. The panel shows Cible, Depuis (IP), Date exacte (Europe/Paris, with year), Auteur and, for co-manager rows, Personne and Raison. No script. From 640px of group width the four columns sit on one line under a header; below, when/outcome, action and who stack. Values wrap, so nothing widens the page. Filters, paging, access and the console routes are unchanged (there is no CSV route in this app, nothing to keep).
- Stylesheet: new `.airlines-*` and `.audit-*` rules (tokens only, one rule per selector per context, no new motion), the dead `data-table--registry` and `airlines-name-it` rules removed, the editor's column widths retuned.

## Tests

Added or rewritten (behaviour only):

- `companion/test_browser_audit_page.py`: rows compact, expand, detail fields visible, no sideways scroll and 44px rows at 360, 390, 1280 and 1440; header shown only on desktop.
- `companion/test_browser_airline_table.py`: inline resolve saves and the row becomes identified (name, type, pill, default-type file); Ignorer clears without saving; customise then "Revenir à celle par défaut" at 360 and 1280; menu delete and star default type; every Air France type row has a menu and a state; naming is audited; 44px targets of the new controls; chevron test updated.
- `companion/test_browser_airline_editor.py`: hand-named airlines keep a row and pill, no separate list, "Supprimer mon nom" works with and without script.
- `companion/test_airline_editor.py`: artwork delete (revert, idempotent, audit), unknown or hostile keys change nothing, default type stored, cleared, validated and audited, non-admin callers refused, inline naming stays on the editor.
- `server/test_airline_default_types.py`: file contract of the new registry.
- Updated in place for the new structure: audit page and co-manager detail tests, airline sheet and table render tests, status pages 02-06 and view pages 02/03 (registry assertions removed or turned into "absent"), route table, access matrix, device routes, CSRF, device actions (fleet.db now holds an audit row), ux_01/03/04, fleet view (System view now 3 blocks), round-8 and sweep helpers. `render_baseline.json` regenerated (two new routes).

Deleted tests (their subject no longer exists):

- `companion/test_browser_health_resolve.py` (all 6: resolve dialog on the System view).
- `companion/test_health_resolve_dialog.py`: `test_every_resolve_row_is_a_trigger_with_the_full_vocabulary_and_keeps_its_link`, `test_the_dialog_is_on_health_once_with_a_return_field_and_not_on_airlines`, `test_the_dialog_is_absent_when_the_table_is_empty` (replaced by "no unresolved table and no dialog on the System view"), `test_naming_from_health_without_artwork_returns_to_health_for_step_b`, `test_a_refused_name_reopens_the_dialog_on_health` (kept as a POST-only check), `test_the_reopen_parameter_only_acts_on_known_prefixes` (replaced).
- `test_status_pages_03.py`: `test_registry_card_keeps_filter_bar_note_and_button_clear`, `test_registry_seen_cells_age_is_a_live_time_element`, `test_read_only_note_reworded_to_point_at_airlines_not_the_runbook`, `test_registry_resolve_link_pairs_desktop_and_mobile_and_escapes_hostile_input`.
- `test_status_pages_04.py`: `test_registry_table_fits_by_stacked_cells_and_short_french_headers`, `test_registry_mobile_cards_paired_with_the_desktop_table`.
- `test_status_pages_06.py`: `test_health_resolve_link_template_matches_airlines_route_constants`.
- `test_empty_state_scale.py`: `test_health_coverage_gaps_empty_state_is_compact`.
- `test_browser_round8_fixes.py`: `test_the_name_it_pill_is_a_small_centred_button_with_a_44px_target`; `test_browser_ux_03.py`: the `health-registry` ticker case; `test_browser_airline_table.py`: `test_the_resolve_dialog_still_focuses_its_name_field`; `test_browser_airline_editor.py`: the three delete-dialog tests (replaced by the menu tests above).

Screenshots: scratchpad `shots80/` (`gap_*`, `types_*`, `audit_*` at 360, 390, 1280, 1440, French).

## Deviations from Plan

- **Default type lives in a new small file, not in the override record.** The name-override and manual-resolution records are per prefix and rebuilt field by field on load, and a built-in airline such as Air France has no record at all, so a field there could not hold a default for it. The new file is expand-only and read by the editor only.
- **"Revenir à celle par défaut" and "Supprimer l'illustration" are the same change** (remove the uploaded file). Both items are listed where an upload exists, as the owner listed them; a vendored picture cannot be deleted, so a type with only a vendored picture has no revert item.
- **Aircraft types with no classifiable shape** (no entry in the ICAO type table) have no picture slot: their row says "Utilise celle de la compagnie" and offers only the default-type item.
- **Ignorer does not persist** (resets the fields). A persistent dismissal would need new storage the owner did not ask for.
- "Supprimer mon nom" posts directly; the old confirmation dialog went with the removed manual-resolutions section.
- The editor page title stays "Éditeur de compagnies" / "Airline editor" (distinct from the personal "Compagnies" page); only the table caption and column keep "Compagnie".

## Known Stubs

None.

## Self-Check: PASSED
