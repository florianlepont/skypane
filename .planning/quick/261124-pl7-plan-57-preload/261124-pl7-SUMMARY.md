# Plan 57 summary: splash preloads every destination's files

Logs and script: scratchpad `lda57/` (`measure.py`, `before-*.json`, `after-*.json`, `before.out`, `after.out`).
Chromium + CDP, local dev server (no compression), seeded admin with 1 frame; cold cache; throttled = 1.6 Mbps / 150 ms.
Counted: `/static/*`, `/frame-preview/*`, `/illustration/*` (map tiles excluded). "late" = requests that
reached the network after a tap, summed over all tabs of the tour.

| case | splash before | splash after | during splash (files, bytes) before / after | late network requests, bytes before / after |
|---|---|---|---|---|
| phone fast | 1.97 s | 2.72 s (cold server drew the Style pictures; 1.96 s once drawn, see desktop) | 20, 330 KB / 56, 984 KB | 32, 604 KB / 0, 0 |
| phone 1.6 Mbps | 4.17 s | 7.89 s | same | 36, 652 KB / 0, 0 |
| desktop fast | 1.94 s | 1.96 s | same | 8, 157 KB / 0, 0 |
| desktop 1.6 Mbps | 4.25 s | 7.90 s | same | 8, 157 KB / 0, 0 |
| stalled request | 3.2 s boot cap | 10.0 s (test asserts 9.7 to 10.6 s) | | |

Waiting for the preload to finish before tapping (settled) or tapping at once after the splash gives the same
numbers, because the splash itself now waits for the downloads.

## Changes
- `companion/preload_assets.py`: list built from page_styles + the tab script table (moved out of `app.py`) +
  `console_users.PAGE_SCRIPTS` + Fleet's `page_scripts` + the map page's starter scripts; role-aware from the rendered nav
  (Console entries added when Fleet is linked); `?v=` tokens via `static_files.asset_version`; Style pictures from
  `layout_picker.first_view_preview_srcs`.
- Splash: overlay carries `data-splash-preload`; `splash.js` fetches with 6 in parallel (map library last), also w=450 siblings
  of the w=264 airline pictures; new progress group "others" (weights 0.05/0.1/0.15/0.3/0.4); FORCE_DONE removed; cap 10 s
  (boot cap 10.2 s). Hold = existing phase wait for 100% after the scan; one flash only.
- Tests: `test_browser_splash_preload.py` (new; all four fail without the list), `test_browser_splash.py` (fast, slow hold, stalled).

## Still late / not verified
- Airline pictures at w=450 are only covered for airlines also shown on Home (w=264 siblings); other Airlines-tab pictures load on tap
  (none late in the tour here because the seed's airlines overlap). Style pictures for non-current themes load lazily.
- Map tiles (third party) not measured. Real iPhone Safari, production compression (Caddy gzip/zstd would cut the 7.9 s) not verified.
- First visit to a frame makes the server draw the Style pictures (about 0.75 s extra splash, measured on phone-fast).
- Unification of w=264/w=450 not done (different card sizes); both are fetched instead.

## Correction after CI (commit c52e5f43)

The preload list follows the space of the page being rendered (personal or Console), never the
viewer's role, so a personal page is byte-identical for an administrator and a user and a signed-out
shell carries no list. The "late requests = 0" figures above were measured with the earlier
role-aware list: a session's first tap from a personal page into the Console still loads five Console
scripts late (about 19.6 KB uncompressed). The Console stylesheets are already cached.
