# Quick 261125-mis-sibling-label: Missing illustrations as a sibling label

Owner approved the mockup (390 and 1280, light and dark). On /airlines/manage the "Missing
illustrations" section becomes a sibling of "Unidentified" and "Airlines".

## Tasks
1. `airline_missing.section_html`: the 22px h2 and the caption sentence give way to the shared small
   `.airlines-label` ("Illustrations manquantes · N"); the caption sentence stays in the empty state.
   `id="airlines-missing"` and `aria-labelledby` stay.
2. `airline_table.table_and_chips`: order = Unidentified, Missing illustrations, Airlines.
3. CSS: relative wrapper with the label lifted above the list, 24px between blocks.
4. Tests: served-HTML and Playwright sibling checks; update the tests that pinned the old shape;
   regenerate `companion/testdata/render_baseline.json`; skill page patterns and "as of" line.
