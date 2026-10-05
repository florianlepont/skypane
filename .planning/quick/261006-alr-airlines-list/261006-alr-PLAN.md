---
quick_id: 261006-alr
type: quick
autonomous: true
branch: claude/airlines-list
---

# 261006-alr: Airlines page, direction C ("list"), plus the aircraft-type label fix

## Objective

Ship the owner-approved redesign of the companion "Compagnies" page and its airline sheet.
Sketches and the root-cause analysis live outside the repo (scratchpad `sketches-airlines2/`).
Owner decisions: one fixed-height row per airline (small picture, name, every aircraft type as
text, chevron), the whole row opens the sheet; no status chips on rows; a card never shows "Tout
appareil" instead of an aircraft; the sheet has one title with the prefixes as quiet chips, a
per-type switcher, the replace zone, the name form and Close.

## Tasks

1. `server/plane/illustrations.py`: an explicit aircraft label for every curated picture
   (`PRIMARY_AIRCRAFT_LABELS`, `VARIANT_AIRCRAFT_LABELS`, `aircraft_label()`), transcribed from
   `VENDOR.md`; designators (E190/E145), never the "Embraer" family. The dead A350-1000 slide is
   fixed rather than dropped: `select_illustration()` tries a sub-type file for an ICAO designator
   in `_TYPE_VARIANT_SLUGS` (A35K -> `a350-1000`) before the shape bucket.
2. `companion/pages/airlines_page.py`: `.airline-list` of `<li>` rows; the row is the trigger
   (an `<a>` to `?sheet=` or `?resolve=`, else a `<button>`), with a hidden twin trigger per further
   type so the sheet can switch type; owner-named airlines read "All types"; needs-artwork keeps a
   dashed placeholder frame. Status chips, carousel, dots and zoom button removed. Shared dialog
   reordered: one title with chips, picture, type switcher, replace zone, name form, manual note,
   delete form. No-script in-page sheet gains the same head, picture and `?sheet=<type>` links.
3. `companion/pages/airline_sheet.py`: sixth trigger attribute (the row's types), head/chips/type
   switcher builders; the two explanatory sentences and the prefixes block removed.
4. `companion/static/panel-lookup.js`: fills the type switcher, hides the caption in art modes,
   re-fills an open sheet when a type tab is pressed (the file chosen for the previous type is
   cleared). `airline-types.js` is no longer wired to any markup (left in place: removing it would
   touch every page's script list and baseline).
5. `companion/static/style.css`: `.airline-list`, `.airline-row*`, `.airline-sheet__head/types/type`;
   carousel/zoom/dots/old chip-block rules removed. No new token, colour, size or keyframes; the
   shown type tab joins the accent list as a selection indicator.
6. French strings in `companion/i18n_fr/airlines.py` (retired ids removed, "Tous types" added).
7. Tests rewritten to served HTML and a browser: `test_status_pages_05b/06`, `test_airline_sheet`,
   `test_view_pages_02/03`, `test_browser_airline_sheet`, `test_browser_ux_01/04`, new
   `test_browser_airline_list`, label and A35K tests in `server/test_illustrations.py`.
8. Regenerate the render baseline; verify only the Airlines entries (and Health's shared dialog
   markup) changed.
