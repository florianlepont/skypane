---
phase: 68-console-and-companion-visual-improvements
plan: 40
subsystem: companion
tags: [airlines-editor, known-by-name, filters, render-baseline]
key-files:
  modified:
    - companion/pages/airline_known_rows.py
    - companion/pages/airline_rows.py
    - companion/pages/airline_table.py
    - companion/static/style-airlines.css
    - companion/i18n_fr/airlines.py
    - companion/testdata/render_baseline.json
  created:
    - companion/test_browser_airline_named_known.py
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 40: "Known by name only" lists every airline without artwork

Owner request after using the AI suggestions: an airline he names (by hand or by validating a suggestion) jumped into the main table. New rule: the block "Known by name only" ("Connues par leur nom seulement") lists every airline that has a name and no artwork, whoever named it; the table "Airlines" lists only airlines with artwork; adding artwork moves a row from the block to the table (existing flow, unchanged).

## What changed

- `airline_table.table_and_chips`: an airline of `data.pairs` (curated, hand-named, promoted) whose `has_art` is false is rendered as a known-by-name row instead of a table row; indexes, anchors and `types_fragment` are unchanged because the enumeration is over the same pairs. The block is the sorted union of the application-named rows (`airline_known_rows.rows`, unchanged) and these rows. Caption, "Known by name only" chip, "All" chip and rows come from one list, so they cannot disagree.
- `airline_known_rows.group_html` takes the row's key (anchor `id="airline-<key>"`, so a refused upload lands on the row), its filter text, the "..." menu and the rename dialog; `table_html` receives the finished rows.
- Menu on a known row = the table's own menu (`_menu_parts`, same markup): "Delete my name" for an owner-named airline, "Rename" and "Reset to the original name" for a renamed built-in airline. No "Change artwork" item (the Artwork button is the row's artwork control). Rows without a menu get an empty 44 px slot when any row of the block has one, so the Artwork buttons line up.
- The "No artwork" chip is removed (id `airlines.chip_no_artwork` and its French entry deleted, no orphan). Decision: it can no longer match anything, since every no-artwork airline is in the block, whose chip is "Known by name only". Chips are now All, Unidentified, Known by name only, Seen, Not seen yet. Known rows carry only the `known` kind, so Seen + Not seen yet = the airlines of the table, and All = Unidentified + Known + table (asserted in the browser tests).
- Dead code removed: the table's needs-artwork picture-as-resolve-link branch (`_artwork_cell`), now unreachable.
- AI suggestion flow untouched: the check posts to `/airlines/resolve` with `inline`, the redirect and flash text are unchanged, and the airline now appears in the block.
- No route, access-matrix, post handler, STATE.md, ROADMAP or requirements change.

## Decisions

- Block ordering: by name (case-insensitive) then prefix, application-named and owner-named rows mixed.
- Hand-named rows use the same Artwork button as the others (airline-level step with the aircraft-type question), not the older per-row "needs-artwork" resolve dialog; the delete action is in the row menu instead of that dialog.
- A built-in airline that has no artwork under its (renamed) name also goes to the block, with Rename and Reset in its menu.

## Design-system divergences

- Known rows gain the existing `row-menu` "..." control (from the table) and a 44 px empty slot on menu-less rows; no new component, no new token, one small CSS rule (`.airlines-known > .row-menu, .airlines-known__slot { flex: none; width: 44px }`).
- The Airlines table no longer shows a placeholder thumbnail row for an airline without artwork.
- The `sketch-findings-skypane` Skill tool could not be loaded in this run (no Skill tool); `.claude/skills/sketch-findings-skypane/SKILL.md`, existing CSS and tokens were used instead.

## Tests

New `companion/test_browser_airline_named_known.py` (14 tests): hand-named airline in the block and not in the table, EN light and FR dark; suggestion validated (check button) lands in the block with the unchanged flash, EN/FR; typed name lands in the block; adding artwork moves it to the table and the caption/chip counts follow; "Delete my name" reachable and working, EN/FR; no overflow, 44 px targets and menu inside the viewport at 320, 390, 1440. HTTP tests in `test_airline_known_rows.py` (hand-named listed once with prefix, menu and delete route, caption/chip counts, FR strings, hand-named with artwork in the table). Existing tests that asserted the old placement (`test_airline_editor`, `test_airline_sheet`, `test_status_pages_05b`, `test_status_pages_06`, `test_browser_airline_table`, `test_browser_airline_promotion`) were rewritten to the new rule.

Results: core suite 12310 passed, 7 skipped, 0 failed; airline browser tests 128 passed (88 + 40). One deliberate `render_baseline.json` regeneration (commit 782788a5, the `style-airlines.css` hash on the editor's pages in 4 variants).

## Open owner questions

- Rename of a hand-named airline is not possible today (the rename route only knows built-in airlines; the existing correction path is Delete my name then name the prefix again). It is therefore not offered on these rows; adding it needs a route.
