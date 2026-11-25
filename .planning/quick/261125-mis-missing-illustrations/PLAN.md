# Quick 261125-mis: Missing illustrations section (variant A)

Replaces "Known by name only" in /airlines/manage by "Missing illustrations · N".

Owner decisions (2026-11-25): variant A (flat list grouped by airline); one "type to choose" row per
airline with no sighting; an airline with no sighting but art for another type is not listed; one
"Other" row per airline with rare types, even for one sighting; the section stays under the table;
the "..." menu of hand-named airlines lives in the airline header.

## Tasks
1. Section module `airline_missing` (rows per airline x family from the table's `sub_rows`, header
   state texts, empty state), `airline_table.table_and_chips` wiring, chip `missing`, i18n EN/FR.
2. CSS for the section (tokens only, 44 px buttons, 360 px), filter integration (row groups,
   header hidden with its last row, section hidden when a filter hides all).
3. Tests: new HTTP tests and browser tests; update the tests that pinned the old block;
   regenerate `companion/testdata/render_baseline.json`.
4. Design-system skill page patterns updated.

## Counting rule
One row = one filter group (`missing-N`). Chip "Missing illustrations" = rows. "All" = unidentified
prefixes + airlines of the table + rows (what the filter's "x of y" counts).
