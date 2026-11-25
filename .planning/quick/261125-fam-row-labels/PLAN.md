# Quick 261125-fam: Family names as the type row labels

The aircraft type rows of the airline editor (/airlines/manage) show the aircraft family name
instead of the designators seen. Follows the approved mockup.

Owner decisions (2026-11-25):
1. Label = family name ("Boeing 737", "Autre"), interface font, primary ink, 16 px / 600. The
   "(famille)" suffix is removed from every family label.
2. The codes leave the label: a tooltip on hover and keyboard focus on a desktop (mono 14 px, 320 px
   wide at most, wrapping, to the right of the label past the star; a single designator reads
   "A339 · A330-900neo"); a 13 px secondary line under the name in a card (two lines, ellipsis, a tap
   on the name expands it). The label is focusable, described by the codes.
3. "Type par defaut" is a star only, with an accessible name and a tooltip.
4. Thumbnail, views, action button, menu, 44 px targets, grid and order unchanged.

## Tasks
1. Markup (`airline_table`), family labels (`airline_families`, FR catalogue), CSS, tap-to-expand in
   `airline-types.js`.
2. Update the tests pinning the old label; new browser tests (desktop tooltip, card line, star,
   focus ring, themes, languages, 360/390/1280, no script).
3. Design-system skill page patterns; regenerate `companion/testdata/render_baseline.json`.
