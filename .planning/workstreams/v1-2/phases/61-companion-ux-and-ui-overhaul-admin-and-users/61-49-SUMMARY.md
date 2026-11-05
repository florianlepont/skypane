# Phase 61 Plan 49: Airline collection header, badges and detail sheet Summary

A one-line collection header (title, thin progress bar with one short sentence, small round badge icons), one control bar with the rarity legend behind an "i" button, and a detail sheet that fits a phone screen.

**Requirements:** W28, W29, W46

## What changed

- `companion/pages/airline_collection_page.py`: the header is the shared page header with the status block as its action (title only, purpose line and the big progress card removed). The status is a 6px `<progress>` plus "28 airlines spotted · 22 more for the 50 badge", then five 30px round badge icons (earned: check, locked: dashed star), each with a `title` and visually hidden words. The control bar is one GET form: field, All / Spotted / Not yet seen segments (label and count side by side, centred), sort in a bordered wrapper, and a 44px "i" button opening the legend (native `<details class="row-menu">`, so `modal.js` already closes it on Escape or an outside tap). The visible "Airlines: N" count and the stacked legend line are gone; the count stays as a visually hidden live status. Detail-sheet facts are reordered (Times seen / Rarity, First / Last seen) with the types and callsigns spanning the row.
- `companion/static/style.css`: new header, badge-icon, control-bar, segment and sheet rules (title 26px on a phone, segments and badge row scroll sideways on one line, sheet at most 85dvh with a flex column so the head and the Close foot stay put and only the body scrolls, picture 72px high on a phone, facts two per row). No colour literals.
- `companion/i18n_fr/airlines.py`: new status string, shortened next-goal string ("encore %d pour le badge %d"); the purpose string removed.
- Tests adapted in place: `companion/test_airline_collection_page.py` (status text, badge titles, legend behind the button, two-per-row facts), `companion/test_browser_airline_collection.py` (icon badges, centred segments, one-row bar on desktop, legend opened by click and closed by Escape, phone header at most a third of 740px, FR title on one line, chips on one line, detail sheet fits the viewport with its head, close X and Close foot in reach, both languages and both viewports). `companion/testdata/render_baseline.json` regenerated.
- `61-UI-SPEC.md` section 12.1 updated (revision 4).

## Deviations

None. `companion/app.py` untouched (1473 lines). The badge icons are not interactive, so they are not 44px targets (the old 44px badge-pill assertion became an icon-size and accessible-name assertion).

## Notes

No hardware / Phase 47 files touched. The "Airlines: N" status text is kept as a visually hidden `role="status"` so a screen reader still hears the live filter count.
