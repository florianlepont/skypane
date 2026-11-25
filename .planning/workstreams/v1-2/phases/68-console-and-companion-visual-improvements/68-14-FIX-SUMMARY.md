# Phase 68 Plan 14 fix: Airlines editor matched to the approved mockup

The owner rejected the built `/airlines/manage` because it did not match `68-MOCKUP-editor.html`. This fix rebuilds the visible parts against it.

## What changed

1. **Phone airline row** is one line: 84 px thumbnail, bold name over `AFR · A320 · 37 views` in small mono, "..." menu (horizontal dots, 44 px). The whole row opens its aircraft types on a tap (the chevron summary lies under the picture and the menu; the text lets the tap through). Opened types are cards in a tinted panel under an "Aircraft types seen" label: thumbnail, code, "Default type" pill, state line, quiet "Add / Change artwork" button and the type menu. Each table is one card under a small label ("Unidentified · N", "Airlines · N", the table caption lifted above the card). The unidentified row is a plain card row (prefix, amber chip, meta, "Name it").
2. **Filter chips** are a scrolling variant of the shared chip component (`filter-bar__chips--scroll`, `chips_scroll=True` in `ui_filter.filter_bar_html`): separate pills with the count in a quieter weight, one line that scrolls sideways on a phone (scrollbar hidden, still a labelled radio group, arrow keys move through it and `list-filter.js` scrolls the whole pill into view), wrapping on a wide screen. Other pages keep the segmented look.
3. **Text centring**, root cause: a line box centres the font's content area (ascent plus descent), which is not symmetric about the capitals for every system font (Segoe UI and others), so labels sat 1 to 2 px off in chips, pills and buttons. Fixed at the source in `style.css`: text-only `.btn`, the pills of the editor and `.airline-card__chip` are inline-block with `text-box: trim-both cap alphabetic` and padding computed from the box height and `1cap`; `.filter-chip__text` and its count are trimmed. A flex or grid container cannot be trimmed, so buttons with an icon keep the flex centring; browsers without `text-box` keep it too. `test_browser_text_centring.py` measures the painted text against the box on the editor, Flights and Fleet at 390 and 1280 px, with the system font and with a deliberately lopsided font; it fails without the fix (chips 1.5 to 2 px off) and passes with it.
4. **Desktop search** is full width on its own line, the chips wrap below it (as in the mockup).
5. Other differences fixed: the unidentified rows are their own card above the table (two tables, no table header over them); labels over each card (FR "Compagnies", new FR id for "Types d'avion vus"); the amber card fill is gone (the amber chip stays); menus use the horizontal dots; row shadows removed; types heading row inside the opened airline; menu minimum widths (no wrapped "Remove as the default type"); the datalist arrow of the name field is hidden; column widths so FR "Ajouter une illustration" fits.

Tests: `test_browser_airline_table.py` gained the scrolling chips test and the phone one-line row test (EN and FR); chip count, row index (the new heading row) and phone views assertions were adapted; `test_browser_round11_fixes.py` no longer asks a phone's type card to align with the airline row's menu (cards are inset, as in the mockup). `test_view_pages_02/03.py`, `test_status_pages_05b.py` follow the new markup (two tables, count element).

## Design-system divergences

1. **Page title** stays "Airline editor" (FR "Éditeur de compagnies") where the mockup says "Airlines editor": the label is the shared navigation string used in tab titles and many tests.
2. **Search placeholder** stays "Airline or callsign…" (shared string) where the mockup says "Airline or prefix…". The filter matches prefixes and callsigns either way.
3. **Desktop aircraft types** stay table sub-rows (tinted band under a label) instead of the mockup's two-column cards: the sub-rows are real table rows that the lazy fetch and many tests rely on. The phone shows the cards of the mockup.
4. **Name dialog and rename dialog** use the shared `ui_modal` sheet and card (title with a close cross, full-width Validate, text Cancel on a phone), not the mockup's drawn approximation (side-by-side Cancel and Validate).
5. **Still not built** (plan 23 and the owner's open decisions): the Suggestion tag and round check button, the "Known by name only" block and chip, and the "Seen 4× · A320 · A321" aircraft list on unidentified rows. The unidentified row keeps its amber "Unidentified" chip.
6. **Phone views and last seen** are not shown on a phone row (only in the meta line's views count), as in the mockup.
7. **Text centring** relies on `text-box` and the `cap` unit (Chrome 133, Safari 18.2); older browsers keep the previous flex centring.

## Location page (separate commit)

The coordinator's follow-up: the round map buttons (locate, Show all of France, credits) had no visible fill (the ghost button variant overrode the France button's background; the others were translucent). They now share an opaque 44 px fill and an edge that stands out from the map in light, dark and Auto-dark; Show all of France uses the mockup's corner-brackets icon (`icon-fit`). The "Follow Paris-Orly Airport" bubble is in the approved mockup (state after "Use my position"), so it is unchanged. `test_browser_map_controls.py` asserts the computed fill is opaque and contrasts with the map ground.

## Gates

Pre-existing and not touched: `test_stylesheet_structure` reports `html[data-ui-theme="dark"]` declared in both `style.css` and `style-place.css`; `test_render_baseline` is red until plan 22 regenerates the baseline (`render_baseline.json` not regenerated).
