# Phase 61 Plan 107: One page opening and one tab strip behaviour (W173 / W174) Summary

Every page now opens the same way, and every segmented tab strip moves the same way, with compositor-only motion (opacity and translate), no per-row animation and everything off under reduced motion.

## What changed

**Page opening (W174)**
- The shell marks `<main>` with `data-page-open`. One rule family in `companion/static/style.css` (next to the existing `.reveal` entrance, same `--motion-enter` / `--motion-stagger` tokens, no new numbers) animates: the page header (fade only: a rising header would paint over the first 12px of the block under it and cover its controls), then one stagger step later the filter bar, filter chips, Home facts, Users section, components index, error actions and the form view of the Style form pages. Pages that were missing the opening now have it: Airlines, airline editor, Users, Audit, Location (header only, the loader and map untouched), special look new/edit, Components, Credits, 404.
- Tall content is never animated whole or per row: `ul`/`table`/map are not in the list; sections and group blocks animate only for the first six siblings; the Flights phone list animates the first three days only.
- `companion/test_companion_app_04.py` pins the entrance selector lists (three constants) in place of the old single list.

**Shared tab strip (W173)**
- Any strip with `data-tabs="<name>"` gets one `.tabs-thumb` from `motion.js` (the Style nav's thumb code moved out of `theme-preview.js` and generalised; the server-rendered thumb span and its CSS are gone). It slides by transform and width from the segment of the page that was left (sessionStorage) to the current one; strips of radios slide on `change`. Applied to: Style nav, Fleet tabs, Flights chips, Airlines chips, Audit chips. Location's My position / Airport strip opts out of the thumb (`data-tabs-thumb="none"`: its phone form is two separate floating pills) but replays its sheet with a fade.
- Content replay: `data-tabs-content` / `data-tabs-replay="fade"` plus `SkyPaneMotion.replay` (class `.reveal-replay`, cancel-and-restart). Flights in-place swaps (the strip itself is re-rendered by the swap) carry the thumb across (`enhanceTabs` / `tabsState`) and fade the swapped list; before this the swap's entrance was finished instantly and nothing animated.
- "Load more" (`list-filter.js`): the first three newly appended cards/rows get `.reveal-appended` on phone and desktop (the hidden rendering is skipped).
- Bottom tab bar: a page that belongs to no bar cell (Credits, Components, 404) now makes More the active cell, so the sliding pill exists on every page.
- Components page: new family "Page opening and tab strips" (EN/FR) with a live tab strip state and notes; catalogue reference updated (`component-catalogue.md`).
- Render baseline and the two sign-in digests regenerated.

## Tests

New `companion/test_browser_page_opening.py` (93 tests): per-page table of 19 pages at 360 and 1280 with and without reduced motion (opening class present, header enters, zero rows animate, at most 6 animated elements on tall pages and 8 otherwise, entrance keyframes touch only opacity and transform and no margin/height/filter/width, reduced motion = zero duration), tab strips (Audit, Fleet, Style, Airlines slide the thumb and replay; Flights in-place swap keeps the document and fades the list; Location mode switch replays the sheet; Style no slide under reduced motion), Load more enters at most three new items on both layouts, tab bar pill on Credits/Components/404/Home/Account. Stressed 4 parallel runs, 0 failures.

Updated in place: `test_companion_app_01` (main marker), `test_companion_app_04` (entrance selectors), `test_sign_in_surfaces` (digests), `test_browser_personalisation` (`data-tabs` hooks), `test_browser_page_title_phone` (waits for the header to land before measuring).

## Deviations

- [Rule 1] Header fade only (not rise): the rising header covered controls in the first 12px of the next block (caught by `test_controls_keep_44px_at_every_point_of_the_entrance`).
- Location's replay is a fade, not fade plus rise: several Location tests hit-test the sheet right after a mode switch and a 12px rise shifted its controls.
- The Airlines and Audit chips are form/link navigations, so their "content switch" is the page opening (header and filter bar); their long list is deliberately not animated (a 6,603px layer cost +95 ms at CPU x4).
- Fleet tabs are hidden at >= 960px by design, so there is nothing to apply on desktop.
- Users filters: none exist.

## Not done

No ROADMAP/STATE/REQUIREMENTS edits. The full suite and `run-all-tests.sh` were not run (cadence). No frame captures of reduced motion.

## Self-Check: PASSED

Gates: ruff, mypy, comment history, function size, Phase 47 freeze green. All 110 `companion/test_browser_*.py` files (2867 tests) and the non-browser companion/test-support suite (6870) green after the last edit.
