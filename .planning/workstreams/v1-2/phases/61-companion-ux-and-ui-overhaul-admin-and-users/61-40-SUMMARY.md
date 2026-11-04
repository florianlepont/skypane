# Phase 61 Plan 40: Airline collection bar and rarity colours Summary

One coherent control bar (field + sort row, chips + plain count + no-script Apply row, auto-submit with script) and tier colours for rare/occasional airlines and aircraft, with a legend and words beside every colour.

**Requirements:** W11, W12

## What changed

- `companion/pages/airline_collection_page.py`: the bar is one GET form in two rows. Row one holds the filter field and the sort select (visible "Sort by" label). Row two holds the show chips, a plain-text count ("Airlines: 12", live through `list-filter.js`) and the Apply button. A rarity legend sits under the bar.
- `companion/static/list-filter.js`: `[data-autosubmit]` controls (sort select, show chips) submit their form on change. The Apply button is hidden under `.js` and remains visible without a script.
- `companion/airline_collection.py`: aircraft types get a rarity (`AirlineEntry.type_rarities`) computed with the same `rarity_for` threshold table (`REGULAR_MIN`, `OCCASIONAL_MIN`) over every stored sighting of that type. The table stays in this one place and the legend prints its numbers.
- `companion/static/style.css`: `--color-rarity-occasional` / `--color-rarity-rare` tokens in all four theme blocks (text-safe, at least 4.5:1); tier styling on the rarity pill, the card's top border and the aircraft type chips; bar layout. The locked badge border is a thin solid line instead of dashed (the "50 airlines" dashed pill the owner saw was the locked badge).
- `companion/i18n_fr/airlines.py`: count, template, legend and range strings (FR uses non-breaking space before the colon).
- `61-UI-SPEC.md` section 12.1 updated (revision 3 wording).

## Tests

Adapted in place: the 44 px check no longer expects Apply under script (it asserts Apply hidden and the bar unclipped); the no-script test now also checks Apply is a visible 44 px target inside the viewport; the French sweep's cognate list gained "Rare" (identical in French, now always visible through the legend). Added: server tests for tier classes, words, legend, bar structure, EN/FR count; browser tests for auto-apply on change (sort and chips) and for tier colour distinctness, text contrast (both themes) and legend words. `render_baseline.json` regenerated.

## Deviations

None beyond the cognate-list entry above. Tiers stay Regular / Occasional / Rare (no new "Very rare" tier, to keep the existing semantics and tests).

## Notes

No hardware / Phase 47 files touched; app.py untouched.
