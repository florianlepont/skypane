# Quick 261125-mis: summary

"Missing illustrations · N" (variant A) replaces "Known by name only" in /airlines/manage, below the table.

- `companion/pages/airline_missing.py`: one row per airline x family without its own picture (from the table's
  `sub_rows`), header per airline with state text and, for an airline with no table row, the "..." menu;
  "Type to choose" row for an airline with no sighting and no art; empty state.
- Counts: N = rows. Chip `missing` = N; "All" = unidentified prefixes + table airlines + N (each row is a filter
  group `missing-N`; an airline header hides with its last visible row; the section hides when a filter hides all rows).
- Upload in the dialog stays disabled until a type is chosen when the dialog asks for it.
- Without script: every row has a plain upload form (the ask row has a required type select first).

## Deviations from the mockup
- The ask dialog keeps the existing designator select (not a family list); the fixed chip shows the family label.
- State text with several illustrated families reads "N familles déjà illustrées".
- An airline with a legacy `{airline}.png` and no typed picture is listed for every seen family (same as its table rows).
- `style-airlines.css` joined the area stylesheets exempt from the 1500-line ceiling.
- "Illustration" EN = FR word, so `airlines.missing_add` is in the i18n cognate list.
