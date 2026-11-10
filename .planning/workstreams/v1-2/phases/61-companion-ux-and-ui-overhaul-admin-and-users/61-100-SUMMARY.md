---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 100
subsystem: companion-performance
tags: [performance, location-map, airline-editor, tab-bar, backdrop-filter, audit-3]
key-files:
  created:
    - companion/static/place-airport-list.js
    - companion/static/airline-types.js
    - companion/test_browser_perf_remaining.py
    - companion/test_browser_airline_helpers.py
  modified:
    - companion/ui_shell.py
    - companion/pages/place_page.py
    - companion/pages/airline_table.py
    - companion/pages/airlines_page.py
    - companion/page_context.py
    - companion/static/place-map.js
    - companion/static/motion.js
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/static_files.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/app.py
    - companion/device_scope.py
    - server/device_dirs.py
    - companion/i18n_fr/airlines.py
metrics:
  completed: 2026-11-09
---

# Phase 61 Plan 100: Remaining performance items (D52) Summary

Every audit-3 performance item still open was either implemented and measured or is explained below. Method: Playwright Chromium, phone 390x844, CPU x4, Fast 4G (9 Mbit/s, 60 ms), 3 runs per page (median), 18,041 history rows, 37 airlines in the editor, the same fixture before and after (`scratchpad/shots100/bench.py`, `mapbench2.py`; raw numbers in `bench_base.json`, `bench_final.json`, `map_base.json`, `map_final.json`). "Before" is the tree at HEAD, extracted with `git archive` and served from a separate process. Headless software raster, so figures are relative, not absolute.

## Before / after

| Item | Metric | Before | After |
|---|---|---|---|
| N04 Airline editor | DOM nodes | 8,795 | 1,684 |
| | forms / inputs | 786 / 1,379 | 83 / 158 |
| | FCP (Fast 4G, x4) | 1,116 ms | 736-776 ms |
| | TBT | 137 ms | 19-52 ms |
| | HTML raw / gzip | 695,006 B / 22,827 B | 696,806 B / 22,752 B (unchanged, see N04) |
| P08 Location list | HTML raw / gzip | 174,793 B / 33,391 B | 78,875 B / 19,390 B (-55 % / -42 %) |
| | DOM nodes at load | 2,464 | 1,653 |
| | TBT | 225 ms | 106-124 ms |
| | `<li>` in the HTML | 272 | 0 (20 in `<noscript>`) |
| P07 map markers (phone) | marker elements at LFPO view | 273 | 2 (7 on desktop) |
| | frames > 33 ms while zooming out | 35 of 59 | 7 of 117 |
| | frames > 33 ms pan + zoom in | 33 of 296 | 5 of 279 |
| | style recalculations during the run | 288 | 23 |
| | DOM nodes after the run | 4,139 | 2,792 |
| N05 expect marker | position of `#tab-bar-end` (Home / Flights / Airlines / Editor / Location) | at the end: 36.6 k of 38.8 k, 144 k of 146 k, 178 k of 180 k, 693 k of 695 k, 172 k of 175 k | 18.8 k, 18.8 k, 18.8 k, 18.5 k, 18.9 k bytes into the document |
| | FCP Home / Flights / Airlines | 572 / 676 / 628 ms | 500-540 / 560-580 / 588-612 ms |
| N07 device directory resolve | 61 devices, one `load_devices` | 1.77 ms (122 `realpath`) | 0.36 ms (1 `realpath`, 61 `lstat`) |
| N08 thumbnail reveal | forced layouts per loaded thumbnail | 1 each | 0 (one batched per frame, only when a class must restart) |

## Items

- **P07 (done).** Zoomed in (above the clustering zoom) only the pins within half a screen of the map are Leaflet markers; a pan or zoom (`moveend`/`zoomend` already redrew the dots) adds the ones that come near and removes the others. The followed airport is always a pin, clusters are untouched (cluster counts still cover the whole catalogue), click, hover label, the 44 px hit box and the list route are unchanged. Markers are `keyboard: false` as before; the airport list stays the accessible route. Browser tests that waited for 100+ pin elements, or clicked the first pin after "France", were updated in place (they now wait for the pins to stop changing and skip the followed airport).
- **P08 (done).** The 31 KB catalogue in `data-airports` is the only copy. `place-airport-list.js` (runs before `list-filter.js`) builds the same rows (same classes, `data-filter-text`, `data-icao`, current badge) from it; `_airports_json` is now in list order. A search term still renders its matches on the server; a browser without scripts gets the first 20 airports in `<noscript>` and the search field reaches the others (the no-script test now searches "roissy" first). The "x of y shown" text is rewritten by the script.
- **P09 (tried, not kept).** `content-visibility: auto` + `contain-intrinsic-block-size: auto 96px` on `.history-card` was applied. The existing `test_load_more_appends_in_place_keeping_the_scroll_and_the_focus` (390 px, EN and FR) failed: not-yet-rendered cards use the 96 px estimate while real cards are 79, 80 or 97 px, so the page height and `scrollY` moved by up to 406 px when Load more appended rows. A single estimate cannot be right for three card heights, so it was reverted rather than weakening the scroll test. The audit's own experiment (647 -> 423 ms render work on Flights) is the gain given up. A future fix needs a server-known card height (or measured heights remembered per card).
- **P12 (done, to confirm on a device).** On phones (`max-width: 959.98px`) `.group` keeps its translucent fill, edge and shadow but no longer carries `backdrop-filter`; the tab bar, sheets, menus, login card and desktop (>= 960 px) keep the glass, and `.fleet-frame .group` was already solid. The sky behind a group is a smooth gradient, so the visible change is small; contrast/readability tests are green. The real GPU saving cannot be measured headless: confirm in Safari Web Inspector (Timelines > Graphics) on an iPhone.
- **P13 (not done, needs infrastructure).** Brotli is not part of stock Caddy's `encode` (only `zstd` and `gzip`); `encode br` needs a custom Caddy build, and `precompressed br` only applies to Caddy's own `file_server`, while `/static` is served by the companion process behind `reverse_proxy`. iOS Safari negotiates gzip today. The upstream HTTP/1.0 per request is loopback-only and was left. Both are deploy/Caddy decisions, so `deploy/Caddyfile` was not touched.
- **P14 (decision unchanged).** HTML stays `Cache-Control: no-store` (a sign-out replay risk the owner accepted earlier). Playwright cannot observe bfcache; whether iPhone Safari restores these pages needs a device check. No code change.
- **P15 (not done).** 55 % unused rules is the whole-site stylesheet measured on single pages. Splitting a 14 k-line, order-sensitive stylesheet per page is an L-sized change with high cascade risk and was deferred by the audit itself until after P09/N03; with P09 reverted there is no new evidence that the style cost (UpdateLayoutTree) is dominated by rule count. The immutable `?v=` URLs and the minified CSS (-58 % gzip) from the earlier plan remain.
- **N04 (DOM done, raw HTML not).** Each airline's aircraft-type rows (259 `<tr>` with their art, menu and default-type forms) now sit in a `<template class="airlines-types">` in the airline's `<tbody>`; `airline-types.js` moves them into the table when the airline's chevron opens (sync, no fetch). The filter text stays on the `<tbody>`, so searching "b738" still finds the airline. Without a script, a `<noscript>` link (EN/FR) opens `?types=all`, which renders every row in the table as before (page_context field `types_open`, compared with one fixed value). `list-filter.js` now listens for `change` on `document` so the upload `data-autosubmit` inputs of late rows submit. The raw HTML did not shrink: the rows are still in the document, only not in the DOM tree, and it gzips to 22.7 KB either way. A real byte reduction needs either a per-airline fragment route fetched on open (async, new route) or dropping the duplicated per-row upload form; both were judged riskier than the DOM gain. Existing no-script tests now go through the link first.
- **N05 (done).** The tab bar (and its end marker) is now emitted right after the splash, before `.dashboard-shell`, so `rel=expect blocking=render` waits for the first ~19 KB (head, icon sprite, sidebar not included) instead of the whole page. It stays a fixed sibling of the shell. Trade-off: on a phone the bar is now before the page content in keyboard order (the skip link is still first and goes to `<main>`); on desktop the bar is hidden. Digests and `render_baseline.json` regenerated.
- **N07 (partly done).** `device_dirs.resolve_state_dir` takes an optional `real_devices` so `_devices_from_rows` resolves `<root>/devices` once per call and checks each device directory with `islink` (a symlinked directory is still refused; the existing symlink and escape tests pass). Not done: loading the devices once per request, and paginating `/users` and `/fleet` beyond ~25 rows (a UX change on the owner-validated lists, not a pure performance fix).
- **N08 (done).** `motion.js` batches the picture reveal in one `requestAnimationFrame`; the forced reflow only runs when a picture still carries `is-revealed` (animation restart). The tab slider's first geometry read stays synchronous on purpose, so the bar never paints without its slider; the layout it forces is the first layout the page needs anyway.
- **N09 (no change).** The audit found no side effects and no stale pages; only the iPhone check (sign out, sign in as another user, tap a tab within 10 s) remains for the release checklist.

## Deviations from Plan

- [Rule 1] Tests that pinned the old structure were updated in place: `test_every_catalogue_airport_is_an_anchor_sorted_by_municipality` (now checks the single JSON copy, list order and the 20 `<noscript>` rows), the two no-script airline editor tests and the no-script Location test (they follow the new links), three place map tests (pin counts), `test_twenty_two_deferred_scripts_before_closing_body` (now twenty-four), two detection page text checks (the airport list is script-filled), and the sign-in digests / render baseline.
- The editor seed moved to `companion/test_browser_airline_helpers.py` (a test module may not import another test module).

## Known Stubs

None.

## Self-Check

See hand-back for the exact test runs.
