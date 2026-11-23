# Phase 68 Plan 53: An airline has no picture of its own, only its aircraft types do

Owner decisions of 2026-11-23. Captures (separate images): `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p53/{before,after}/` (`editor-{390,1440}-{en,fr}.png`, `user-airlines-{390,1440}-{en,fr}.png`, light).

## The model

An airline has no picture of its own. Only its aircraft types do. One type is the airline's default type: the safety net shown when a flight has a type with no picture (default A320, flight on a 737 without a picture: the A320 picture is shown). The older `{airline}.png` files are not renamed or deleted: each counts as the picture of its airframe type.

Runtime order (`illustrations.select_illustration`): 1 exact airline+type picture; 2 the airline's EFFECTIVE default type picture; 3 generic by shape; 4 universal. Effective default = the stored default (fleet root `airline_default_types.json`) when it has a picture, else the airframe of the legacy picture. Golden renders, `test_giant_compose`, `test_orly_replay`, `test_illustrations*` are unchanged and green (airlines with a legacy picture and no stored default behave as before).

One function lists an airline's pictures by type: `illustrations.type_pictures(key, state_dir, codes=())` returns `{type code: TypePicture(key, path)}` (built-in files, fleet uploads, the legacy picture under `legacy_picture_type`). Built-in airframe: curated label (`aircraft_label`), also for a renamed built-in airline (through the name overrides); hand-named airline: the type stored when the picture was uploaded. Used by the Editor rows, `has_type_livery` (the livery rule), `default_picture`, `effective_default_type`, `display_key` and the migration.

## Commits

| Item | Commit |
| ---- | ------ |
| Runtime + abstraction | a42fbdda |
| Editor | 08a1b115 |
| Automatic default, mandatory type | 15f41e81 |
| Migration | fd4e0461 |
| Docs, baseline | final docs commit |

## Editor

The airline row has no picture and no "All types" row; its default type column is the code only. Each airline shows its type rows (seen types most-seen first, then pictured and curated types by code): picture, views, last seen, menu; star pill on the effective default; menu item "Use as the airline's default picture" on a type with a picture. A legacy picture of an unknown airframe is listed as one row with code "—" so it is never hidden. Removed: constants/strings `airlines.all_types`, `airlines.aircraft_type`, `ROW_TYPES_*`, the airline thumbnail layout and the "Change artwork" fallback in the airline menu (EN/FR, no orphans). On a phone the row is name over `AFR · A320 · 37 views` plus the menu: the thumbnail of the approved mockup is gone, by the owner's model. The user Airlines page, the Home strip and the Flights stand-in show `display_key` (the effective default type's picture): unchanged for the user (checked in the captures).

## Upload and automatic default

An upload to an airline key with no picture and no type is refused (`artwork_type_invalid`); the dialog select (required) now also appears for needs-artwork triggers; type rows upload with `?default_type=<their code>`. After storing, an airline with no effective default gets the type as default through `set_default_type` (livery rule), audited as `airline.default_type` with `automatic: true`; an airline that has a default keeps it. Deleting artwork: a default left without a picture is re-pointed to the first remaining type (alphabetical) or cleared; the artwork-delete audit row carries the change. `set_default_type` copies an uploaded legacy picture to its type slot before the default moves away from it (nothing overwritten or deleted), so it stays listed under its type. No toast wording for the re-point exists in the codebase; only the audit detail says it.

## Migration (`server/plane/fleet_set_defaults.py`, called by `fleet_migrate` after the clearing of plan 52)

For every airline with pictures and no stored default: (a) legacy picture with a known airframe: that type; (b) else typed pictures: one: that type; several: most sightings across the fleet, tie or none: first type code alphabetically; (c) legacy picture of an unknown airframe: most-seen typed picture, else `unresolved` with the reason; (d) no picture: nothing. Sightings: `runway_events` of the root and every frame, read-only, a flight of a type without a picture counting for the picture it is drawn with, a built-in original counting for its renamed airline. Examples: (a) Air France: A320; (b) `acme-air-a320` + `acme-air-b737`, 4 B739 flights: B737; (c) `acme-air` of unknown airframe + typed pictures with a B738 seen: B737; unresolved: nothing seen. Log lines: dry run `airline default types: would set N`, one `would set <key>: <type> (rule a|b|c)` each; real `set N` and lines; `unresolved M` + `unresolved <key>: <reason>`; `nothing to do` on a second run (the clearing prints its own `nothing to do` too). Archive `airline_default_types_set.json` (airline, type, rule, time), marker `airline_default_types_set_migration.json`, both in the backup include list. Dry run reads the fleet root before that run's own merges (as plan 52); it does count the defaults the clearing is about to remove as gone. Seeded fixture (`seed_airline_editor`): `would set 37`, all rule a (Transavia B737, renamed TAP A321 via its original), no unresolved.

## What changes on frames

Nothing visible except airlines whose chosen default now wins (as in plan 52). On the first deploy about 40 airlines get a stored default (their airframe).

## Tests adapted (intended behaviour)

`test_airline_default_types` (A320 is a livery of Air France: refusal case uses B738), `test_fleet_default_types` / `test_fleet_migrate` / `deploy/tests/test_default_types_migration_log` (cleared airlines now get their airframe by rule a; two `nothing to do` lines), `test_airline_editor` (default deletion re-points/clears, legacy livery), `test_fleet_artwork_pages`, `test_airline_known_rows`, `test_companion_app_04b` (uploads name a type), `test_airline_sheet`, `test_status_pages_05b/06/07`, `test_view_pages_02/03` (type rows replace the airline thumbnail; rendered with `types_open`), `test_airline_fleet_roles` (`?types=all`), browser: `test_browser_airline_table` (chevron, thumbnails, menu, phone row, uploads), `test_browser_airline_promotion`, `test_browser_airline_editor` (no-JS test uses reduced motion: without a first-viewport image no frame is produced and the animation wait hangs). New: `server/test_type_pictures.py`, `server/test_fleet_set_defaults.py`, `companion/test_airline_type_pictures.py`, `companion/test_browser_airline_type_rows.py`.

## Owner decisions needed

1. Phone row lost its thumbnail (approved mockup showed it): confirm.
2. Seen types and legacy airframe can duplicate (Transavia: seen B738 and legacy B737 are two rows).
3. The no-JS first-artwork fallback form has no type field: it is refused; only the dialog asks for the type.
4. A legacy picture of a renamed airline not tied to a built-in original has an unknown airframe until a default is chosen (shown as a "—" row; migration rule c or unresolved).
