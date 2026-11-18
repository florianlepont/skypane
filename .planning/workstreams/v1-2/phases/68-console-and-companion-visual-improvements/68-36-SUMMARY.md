---
phase: 68-console-and-companion-visual-improvements
plan: 36
subsystem: companion
tags: [style, previews, cache, browser-test]
requires: ["68-01", "68-09"]
provides:
  - content-addressed frame preview URLs (`&v=<signature>`) with a year-long immutable private cache entry
affects: [68-22]
key-files:
  modified:
    - companion/theme_preview.py
    - companion/preview_images.py
    - companion/app.py
    - companion/test_browser_style_tab_previews.py
    - companion/test_preview_cache.py
    - companion/test_theme_preview_layout.py
requirements: [CON-01]
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 36: Style tab previews no longer reload Summary

Frame preview URLs now carry their content address (`v`, the existing cache signature) and an image requested with the current address is cached for a year as `private, immutable`, so a Style tab switch no longer revalidates or re-downloads unchanged previews.

## Measured cause (plan 01)

Plan 01 recorded: each tab is a full document navigation with `loading="lazy"` images, URLs are stable, and the cache is hit within `max-age=300`. Re-measuring with a wait past that lifetime showed what plan 01 could not see: five minutes after the first pass, a tab switch sent 9 conditional requests on Departures (all `304`) and re-downloaded 5 bodies on Arrivals, i.e. every switch reloaded all previews once the 300 s lifetime lapsed. The fix targets that: the lifetime was short only because the URL was not content-addressed.

## What changed

- `theme_preview.frame_preview_version()` returns the existing `frame_preview_signature()` for the current frame's profile; `frame_preview_src()` appends `&v=` (nothing for the `__THEME__` placeholder the picker script fills in).
- `preview_images._serve_frame_preview_image` answers a request whose `v` equals the current signature with `private, max-age=31536000, immutable`; a stale, missing or foreign `v` keeps `private, max-age=300` and the same pixels, so a changed setting (new theme, state, size, layout, hardware profile, palette or cache version = new signature = new URL) can never be pinned by an old entry.
- `app.send_bytes` gained an `immutable` flag (app.py stays at 1490 lines).
- No stylesheet, page module or JS change; the pictures are byte-identical.

## Network counts (real Chromium, real app, seeded fleet; 1280px; Playwright CDP)

Tab pass Departures, Arrivals, Special looks, Calendar, Departures, then again after 320 s.

| Pass | Before: preview requests / bodies over network / revalidations | After |
|---|---|---|
| first pass (warm) | 9, 10, 5, 5, 9 requests; bodies only for Arrivals' 5 new previews | same |
| after 320 s, Departures | 9 requests, 9 conditional (304) | 9 requests, 0 to the server |
| after 320 s, Arrivals | 10 requests, 5 re-downloaded bodies | 0 bodies, 0 to the server |
| after 320 s, other tabs | 5 requests each, 5 to the server | 0 to the server |

(Request events still fire for copies the browser serves from its own cache; the plan's "no network request" is read as no request reaching the server.) Raw output: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p36/before_requests.txt` and `after_requests.txt`.

## Visual check

32 full-page captures (phone 390 and desktop 1280, FR and EN, light and dark, four Style tabs) before and after, in `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p36/` (`before_*`, `after_*`). All 32 are pixel-identical (image diff bounding box empty); two were viewed and look correct.

## Tests

`companion/test_browser_style_tab_previews.py` (SKYPANE_REQUIRE_BROWSER=1) was rewritten from measurement to regression tests: stable addressed URL on every tab; `private`, `immutable`, `max-age >= 1 year` on every preview response; no unchanged preview body crosses the network on a revisit; a stale or missing address gets `private, max-age=300` with identical bytes. Three of the four fail against the old code (verified by reverting the source). `test_preview_cache.py` covers the address changing with each input. Principal isolation is unchanged: the route is still behind the owner-device gate (`test_access_matrix.py` passes) and the header stays `private`.

## Gates

Passed: the four plan test files, `test_display_looks`, `test_theme_preview_layout/profile`, `test_i18n`, `test_structure_guards`, `test_suite_guards`, `test_access_matrix` (2530 passed in the focused run), ruff, mypy (no error in the touched modules; 14 existing import-not-found errors for PIL/requests stubs), function size (2788 scanned, none over 80), comment-history check, app.py 1490 lines. `server/test_golden_render.py` was not run (no server/ change).

## Baseline (not regenerated)

`companion/test_render_baseline.py` fails, as already expected before this plan: the CSS cache-bust hashes (`/airlines`, ...) differ from the committed baseline because of earlier plans. In addition, the 28 captures that embed `/frame-preview/` URLs (the seven `/display*` routes x language/theme) will differ by the new `&v=<12 hex>`; plan 22 regenerates them.

## Open pull requests

None open on florianlepont/skypane (REST listing), so no overlap with `settings/theme.py` or the Style files.

## Deviations from Plan

- [Rule 1] `test_theme_preview_layout.py::test_frame_preview_src_adds_layout_only_when_given` asserted the URL ended with `&layout=b`; it now expects `&layout=b&v=`.
- `companion/app.py` (not in the plan's file list) got the one-argument `immutable` flag for `send_bytes`.
- The fix is cache-side, not the page-side re-decode change plan 01 suggested; the re-measurement above is why.

## Design-system divergences

None.

## Known Stubs

None.

## Self-Check: PASSED
