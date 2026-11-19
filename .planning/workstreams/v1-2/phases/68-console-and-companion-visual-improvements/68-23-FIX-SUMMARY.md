---
phase: 68-console-and-companion-visual-improvements
plan: 23-fix
subsystem: companion
tags: [airlines, editor, artwork, promotion]
---

# Phase 68 Plan 23 Fix: promote artwork-bearing known-by-name airlines, drop the Unidentified chip

Owner decisions applied after plan 68-23 (answers open decision 2 of that summary). No state or requirement command was run, CON-01 is not ticked, ROADMAP unchanged.

## What changed

- An airline known by name only that receives artwork (Artwork button, then the shared dialog and the existing upload route) leaves the "Known by name only" block and becomes a row of the main Airlines table: thumbnail, name, prefix, views, last seen, "..." menu (Change artwork). `airline_known_rows.promoted()` finds them; `airlines_page._table_data` appends them to the table pairs; `airline_table` shows their prefix on the row and in the filter text (`TableData.promoted_prefixes`). Hand-named prefixes keep their existing manual row. No new route.
- The amber "Unidentified" chip on unidentified-prefix rows is removed (markup, `.airlines-gap-chip` CSS, the `airlines.unidentified_label` EN constant and FR string). Those rows stay distinguishable by sitting in their own card, labelled by its caption ("Unidentified · N" / "Non identifiées · N"), above the table.
- The Close of the airline detail sheet stays the round cross (no change).
- Tests: new `companion/test_browser_airline_promotion.py` (real browser, phone, EN and FR: Artwork button, upload through the dialog, row appears in the table with picture, prefix FIN and menu; known block drops from 6 to 5); `test_airline_known_rows.py` asserts the table row over HTTP; Phase 61 `test_browser_console_groups` now asserts no chip, a labelled card holding only unidentified rows, positioned above the main table (EN/FR, both themes); `.airlines-gap-chip` removed from the text-centring selector.
- `render_baseline.json` regenerated once (end of work; captures changed through the stylesheet hash and the chip removal).

## Design-system divergences

- Default type of a promoted row shows the empty marker, not a type: the Artwork button uploads an airline-level picture (no aircraft type is chosen anywhere in that dialog and the upload route stores no default type), so there is no uploaded type to take over. The owner can set one from the type rows as for any airline. If a default type must be chosen at upload time, that needs a type field in the shared dialog (not built).
- A promoted row has no Rename entry (the built-in prefix table has no sheet for these names) and no Delete-my-name entry (the name is not hand-made); its menu holds Change artwork only.
- Promoted rows are appended after the curated and hand-named rows (the table has no sort), so a freshly promoted airline lands at the bottom.
- The unidentified card keeps its caption as the only label; no chip, no colour marker, as the mockup 68-MOCKUP-editor.html.

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p23fix/` (full page, phone 360 FR light): 1 before upload (known block of 6), 2 after upload with promotion disabled (old behaviour: Finnair vanishes from the block and has no row), 3 after upload promoted (chip still present, taken before the chip removal), 4 after upload promoted, no chip (final). Captures 1 and 2 were regenerated after the chip removal, so they show no chip either.
