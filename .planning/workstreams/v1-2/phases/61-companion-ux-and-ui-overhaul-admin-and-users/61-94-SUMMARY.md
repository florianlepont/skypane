---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 94
subsystem: companion-performance
tags: [performance, caching, css, images, motion]
key-files:
  modified:
    - companion/static_files.py
    - companion/app.py
    - companion/ui_shell.py
    - companion/static/splash-boot.js
    - companion/static/motion.js
    - companion/static/style.css
    - companion/illustration_normalize.py
    - companion/pages/airline_table.py
    - companion/pages/airline_collection_page.py
    - companion/pages/place_page.py
    - companion/pages/home_page.py
  created:
    - companion/test_browser_perf_quick_wins.py
metrics:
  completed: 2026-11-08
---

# Phase 61 Plan 94: Performance quick wins Summary

Served CSS without comments, content-addressed `?v=` asset URLs answered as immutable, a WebP thumbnail variant of the airline artwork, splash.js loaded only when the splash plays, Home's ambient loops resting after a minute, a 260 ms page-change transition, a frame-batched pull-to-refresh and a lighter Location list.

## What was done (audit finding, change, measured effect)

| Finding | Change | Measured |
|---|---|---|
| P02 comments in served CSS | `static_files.minify_css` (string-aware comment strip, trimmed lines, no blank lines) applied to `style.css` when it is read into the per-process cache; the source keeps its comments; output is a pure function of the input bytes. The vendored Leaflet CSS is served byte for byte (a test pins it). | style.css 386,745 B -> 250,908 B raw; gzip -6: 87,988 B -> 37,235 B (-58 %) |
| P01 cache | `static_files.version_static_urls` adds `?v=<12 hex of the served payload SHA-256>` to every `/static/*.css` and `*.js` href/src at `send_html` time (page modules keep naming plain routes). `cache_control_for` answers `public, max-age=31536000, immutable` only when `v` equals the current token; a missing or stale token keeps `public, no-cache`. Icons keep their plain URL. | a warm tab switch no longer revalidates 11-18 files; the audit measured 15 -> 3 requests and FCP 264 -> 206 ms for this change (prod-like) |
| P10 splash.js | removed from the page's script list; `splash-boot.js` reads `data-splash-src` from its own tag and adds the script after parsing, only when it sets `splash-on` | one request and 13.4 KB raw (4.1 KB gz) fewer on every page load except the first of a session; the page script count drops by one |
| P03 thumbnails | `/illustration/<key>.png?w=264` or `?w=450` returns a Pillow WebP (PNG fallback when WebP is unavailable), cached per (path, mtime, width), `private, max-age=3600`; other widths get the normal PNG. List thumbnails ask for 264, collection cards for 450. The lightbox and sheets keep the full picture. | air-france.png 49,163 B -> 7,094 B (264) / 11,014 B (450); all 52 pictures 2,412,196 B -> 349,682 B at 264 (-86 %) |
| P04 ambient loops | `motion.js` puts `data-ambient="rest"` on `<html>` after 60 s without a touch or key, or when the tab is hidden; style.css then sets `animation-iteration-count: 0` on the status dot, the glow and the glint (halo opacity 0). A pointer, key or the tab returning wakes them for another minute. Done with a timer rather than finite iteration counts so existing "wait for finite animations" browser helpers are not made to wait 30+ s. | the audit measured 601 compositor draws per 10 s idle with the loops against 12 without; after a minute at rest Home matches the "without" figure (the browser test asserts no running infinite loop at rest; the draw count was not re-traced) |
| P06 view transition | new token `--motion-view-transition: 260ms` for the tab-slider group (was the 420 ms spring duration); the spring stays for in-page motion | the transition no longer outlasts the page by about 160 ms |
| P11 pull to refresh | `pointermove` stores the offset and paints once per `requestAnimationFrame`; the label text is written only when the hint/release state changes; release cancels the pending frame | style writes during a 40-move drag: at most 3 (browser test) against 3 per move before |
| P16 previews | Home hero image gets `fetchpriority="high"` | see skipped list for the rest |
| P07 (part) | `<link rel="preconnect">` to the tile host at the top of the Location body | tile connection set-up overlaps parsing |
| P08 (part) | the airport list rows no longer repeat `data-iata/lat/lon/name` (the map reads its JSON; nothing read them) | list HTML for the 272 airports 121,648 B -> 97,190 B raw, 19,290 -> 13,880 B gzip |

## Skipped, and why

- P05 splash shortening: the splash duration must not change. Not touched.
- P09 `content-visibility` on long lists: it implies paint containment, which would clip the glass shadows and the spring-scaled cards, and the intrinsic heights (variable rows) cannot be verified without a real device; it would change the look.
- P07 canvas markers and P08 de-duplicating the airport JSON from the markup: a rewrite of place-map.js marker/cluster code and of the no-script list; too large and risky for a quick win.
- P16 `loading="lazy"` on Display previews: the shipped test pins them eager on purpose (both large previews are live); changing that is a behaviour decision. The 0x0 arrivals preview and the 2x sizing are unchanged.
- P12 (blur cost), P13 (Caddy precompression), P14 (bfcache vs `no-store`), P15 (CSS split): need a real phone or deploy changes, or are explicitly deferred by the audit.

## Deviations from Plan

- [Rule 3] Tests that pin exact asset URLs or glob routes were updated in place for the `?v=` token and the lazily added splash script: `test_page_scripts.py`, `test_companion_app_03.py` (20 deferred scripts instead of 21, 7 global scripts), `test_place_map_assets.py`, `test_config_page_05.py`, `test_ui_modal.py`, `test_status_pages_05b.py`, `test_status_pages_06.py`, `test_place_page.py`, `test_static_cache.py` (immutable vs revalidating policy, stale token, minified stylesheet, WebP route), `test_companion_app_04.py` (new motion token), the two Playwright `route(...)` globs in `test_browser_place_boot.py` and `test_browser_place_map.py` (now `...js*`), the three pinned digests in `test_sign_in_surfaces.py`, and `testdata/render_baseline.json`.
- The Playwright route guard turns the browser cache off, so a warm-load request count cannot be asserted in a browser; the cache policy is asserted on the response headers instead.

## Verification

Run: ruff, mypy, `check_comment_history.py`, `check_function_size.py`, `stub-server/test_phase47_freeze.py`; the render snapshot rewritten; the non-browser companion, test-support and stub-server suite (`-n 8`); whole browser files for Home, splash, Flights, Airlines, Location/place, Display, personalisation, motion, tab bar, overhaul sweep (finite-animation guard), static cache, plus test_page_scripts, test_companion_app_0*, test_stylesheet_structure, test_suite_guards, test_structure_guards, test_sign_in_surfaces, test_render_baseline. The new browser file passed 4 parallel runs with no failure. `test_browser_home_signature.py::test_a_refresh_that_starts_a_new_cycle_gives_the_ring_one_flourish` failed once under load and passed on its own re-run.

`companion/app.py` is 1481 lines; the largest JS file is 1483 lines.
