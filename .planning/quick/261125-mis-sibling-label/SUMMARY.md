# Quick 261125-mis-sibling-label: summary

- The section's title is now the same small label as the two tables' captions (13px, 600, 70% ink,
  16px indent, lifted above the list); no h2 and no caption sentence (kept only in the empty state).
- Order on the page: Unidentified, Missing illustrations, Airlines.
- `id="airlines-missing"` and `aria-labelledby="airlines-missing-title"` are unchanged.
- Tests: served-HTML test, Playwright test comparing the label with the "Airlines" label.
