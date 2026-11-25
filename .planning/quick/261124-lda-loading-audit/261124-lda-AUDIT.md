# Loading audit, SkyPane companion (branch phase-68-loading-audit)

Measured with Playwright chromium + CDP Network events against a local `AppServer` (seeded: 1 frame, 24 runway events, 6 airlines), fresh context, splash NOT skipped, signed-in admin. Viewports 390x844 and 1280x900. Conditions: cold cache, warm (second tab in the same context), throttled (CDP 1.6 Mbps down / 0.75 up / 150 ms RTT). Raw logs: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/log-{phone,desktop}-{cold,warm,cold-throttled}.json`, splash probe `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/splashprobe.json`, scripts `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/audit.py`, `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/splashprobe.py`, `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/headers.py` (all under the scratchpad dir `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/lda/`).

## (a) Answer to the owner

No: the splash only preloads what the Home page itself uses (core `style.css`, `style-home.css`, 14 scripts, 5 Home images: 21 files, 326 KB), so every other tab still downloads its own page stylesheet, scripts and images the first time you tap it. In a cold phone session touring all tabs, 36 further files (about 636 KB uncompressed: 184 KB CSS, 309 KB JS, 143 KB images, map tiles excluded) were fetched after the splash; the Style tab alone pulls 12 files (173 KB) including `style-display.css` and 6 server-rendered preview PNGs that finish 1.8 to 2.0 s after the tap. The owner's impression is therefore correct, but the delay is small on a fast link (page CSS done 115 to 140 ms after tap, apart from Style's previews and Location's map) and noticeable only on a slow one (CSS 335 to 1055 ms, scripts up to 3.1 s, Style previews 3.2 s at 1.6 Mbps / 150 ms).

## Measured facts

- Splash length: the overlay class `splash-on` is removed at 2.23 s (phone) / 2.15 s (desktop) on a fast link, and 4.17 s / 4.28 s at 1.6 Mbps (first paint of the overlay at 1.56 s there, because the HTML arrives late). At that moment `readyState=complete`, 0 stylesheets pending, 0 `<img>` pending, progress text `100%` (`splashprobe.json`). A warm second tab still plays the whole sequence: 1.9 s (phone-warm 1885 ms), because the sequence is timed, not load-driven.
- Everything static is versioned and immutable: `/static/*.css|js?v=<sha12>` answers `public, max-age=31536000, immutable` (companion/static_files.py:223, `version_static_urls` :240, `_STATIC_URL` :225). In the cold phone tour, 178 repeat static requests were served from cache, 0 went to the network (the 6 "net" repeats were distinct image URLs). Un-versioned static routes are `public, no-cache` (revalidate) (static_files.py:142). HTML is `no-store` (headers.py output); prefetched HTML is `private, max-age=10`. Illustrations are `private, max-age=3600`; frame previews `private, max-age=31536000, immutable` (log field `cache_control`).
- No web fonts: `style.css:4` comment says "no @font-face, no remote asset"; zero Font requests in any log. The icon sprite is inline in the HTML (63 `<symbol>`, headers.py), so there is no sprite request. No service worker (no `serviceWorker` in companion/ py/js/html) and no manifest (splash-boot.js comment).
- Dev server sends no `Content-Encoding` (style.css = 145,838 bytes raw). Production Caddy has `encode zstd gzip` (deploy/Caddyfile:53), not measured here, so KB below are uncompressed and throttled byte-time is pessimistic; the latency part is not.
- Not measured: OpenStreetMap tiles on Location (10 requests phone, 30 desktop, to `tile.openstreetmap.org`; they failed here with ERR_CERT_AUTHORITY_INVALID because the sandbox has no outbound TLS, so Location never reaches "settled" in my logs); real iPhone Safari; production compression; warm cache after a full tour (inferred from the 178/0 above, not run separately).

## (b) Late requests per destination (phone 390x844; ms are after the tap)

"Late" = first request of that URL in the session, i.e. not fetched during the splash. Documents/prefetch fetches are excluded here (see notes). Page HTML is warmed by `prefetch.js` only, never its CSS/JS/images.

Summary of "done" times after tap (cold / throttled), CSS = render-blocking stylesheets:

| Destination | late files, KB | CSS done | JS done | images done |
|---|---|---|---|---|
| Home (revisit) | 0 | 77 / 252 (desktop) | - | - |
| Flights | 4, 65 | 114 / 359 | 123 / 743 | none new |
| Airlines | 5, 68 | 118 / 598 | none new | 195 / 1009 |
| Style | 12, 173 | 137 / 819 | 170 / 1639 | 2040 / 3160 (desktop 1832 / 3189) |
| Location | 9, 258 (+tiles not measured) | 113 / 841 | 239 / 3149 | tiles n/m |
| Account | 1, 57 | 509 / 1055 (includes ~410 ms document wait) | none | none |
| Console (Fleet) | 2, 6 phone (after Account); 3, 63 desktop (admin CSS first hit) | 493 / 601 | 503 / 1027 | none |
| Users | 1, 4 | 83 / 233 | 94 / 629 | none |
| Airline editor | 2, 6 | 122 / 234 | 130 / 1219 | none |
| Console System, Audit | 0 | 101 / 265, 453 / 594 | - | - |

Per-file tables follow (phone; desktop in the appendix). "warm run" column: the warm tab only had Home cached, so every non-Home asset shows `net`; this is the expected state of a second visit before the other tabs were ever opened.


**/devices/D/flights** (phone) - 4 new files, 65 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-c-lists.css | Stylesheet | 11.1 | 98-114 | 108-359 | net |
| /static/style-flights.css | Stylesheet | 6.4 | 99-114 | 108-335 | net |
| /static/list-filter.js | Script | 25.1 | 100-123 | 108-729 | net |
| /static/panel-lookup.js | Script | 22.2 | 100-123 | 108-743 | net |

**/devices/D/airlines** (phone) - 5 new files, 68 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-airlines.css | Stylesheet | 25.1 | 101-118 | 241-598 | net |
| /devices/D/illustration/easyjet.png?w=450 | Image | 10.9 | 127-195 | 611-1008 | net |
| /devices/D/illustration/tap-air-portugal.png?w=450 | Image | 9.6 | 127-196 | 611-963 | net |
| /devices/D/illustration/transavia-france.png?w=450 | Image | 11.5 | 127-196 | 611-1009 | net |
| /devices/D/illustration/air-france.png?w=450 | Image | 11.3 | 127-195 | 611-1009 | net |

**/devices/D/display** (phone) - 12 new files, 173 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-c-console.css | Stylesheet | 10.4 | 106-137 | 235-565 | net |
| /static/style-display.css | Stylesheet | 25.0 | 106-137 | 236-819 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=classic&eecac10a3c91 | Image | 6.1 | 106-665 | 353-669 | net |
| /devices/D/frame-preview/white.png?state=departing&size=large&c8d0050cc3d2 | Image | 47.2 | 106-666 | 383-1179 | net |
| /static/confirm-submit.js | Script | 1.2 | 107-162 | 1216-1386 | net |
| /static/theme-preview.js | Script | 17.0 | 107-163 | 1216-1477 | net |
| /static/value-controls.js | Script | 18.6 | 108-163 | 1217-1632 | net |
| /static/calendar-connect.js | Script | 1.0 | 108-170 | 1217-1639 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=a&a0c4242799cd | Image | 14.2 | 159-2039 | 1214-3029 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=b&4696ecff99e9 | Image | 9.2 | 159-942 | 1214-2242 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=c&06d088116061 | Image | 9.0 | 159-718 | 1214-1937 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=a_diagonal&df7cab7554 | Image | 14.2 | 159-2038 | 1214-3160 | net |

**/devices/D/detection** (phone) - 9 new files, 258 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-place.css | Stylesheet | 34.3 | 96-112 | 249-841 | net |
| /static/vendor/leaflet/leaflet.css | Stylesheet | 15.0 | 96-113 | 249-648 | net |
| /static/place-start.js | Script | 1.9 | 97-120 | 917-1088 | net |
| /static/vendor/leaflet/leaflet.js | Script | 144.7 | 132-173 | 1107-2016 | net |
| /static/place-search.js | Script | 3.3 | 157-174 | 2014-2234 | net |
| /static/place-map.js | Script | 30.6 | 162-174 | 2191-2538 | net |
| /static/place-map-search.js | Script | 13.9 | 191-238 | 2521-2754 | net |
| /static/place-card.js | Script | 10.8 | 201-239 | 2746-2971 | net |
| /static/place-airport-list.js | Script | 3.3 | 230-239 | 2970-3149 | net |

**/account** (phone) - 1 new files, 57 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-admin.css | Stylesheet | 56.8 | 494-509 | 608-1055 | net |

**/fleet** (phone) - 2 new files, 6 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/update-question.js | Script | 2.8 | 480-503 | 829-1010 | net |
| /static/fleet-anchors.js | Script | 3.2 | 481-503 | 829-1027 | net |

**/users** (phone) - 1 new files, 4 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/copy-button.js | Script | 3.9 | 77-94 | 453-629 | net |

**/airlines/manage** (phone) - 2 new files, 6 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/airline-types.js | Script | 2.0 | 110-130 | 1023-1202 | net |
| /static/airline-suggest.js | Script | 3.7 | 111-130 | 1023-1219 | net |

Notes on the tables:
- Style: the two large images are the current-frame preview (47.2 KB) and the 4 layout thumbnails (9 to 14 KB) plus a 6.1 KB classic preview. They are `loading="lazy" decoding="async" fetchpriority="low"` (companion/settings/layout_picker.py:83) and generated on the server; the requests start 106 to 159 ms after the tap but finish at 665 ms (previews) and 718 to 2039 ms (layout a / a_diagonal), so the Style tab shows its thumbnails popping in over about 2 s on a loopback link. Scripts `confirm-submit/theme-preview/value-controls/calendar-connect` start only 1.2 s after the tap at 1.6 Mbps (the CSS starts at 0.24 s) because they are `defer` tags at the end of `<body>` (headers.py, Home body scripts), found after the 100 KB HTML has streamed.
- Airlines: illustrations are fetched again at `?w=450` although Home loaded the same airlines at `?w=264`; 4 images, 43 KB, 195 ms cold, 1009 ms throttled.
- Location: `leaflet.js` 144.7 KB + `leaflet.css` 15 KB + 5 place scripts, then tiles (10 phone / 30 desktop requests). Scripts chain: `place-start` 917 ms, `leaflet` 1107 to 2016 ms, last place script 3149 ms at 1.6 Mbps.
- Account / Console / Audit / Home-by-tap: the ~410 to 500 ms "settle" is the document (the prefetch Fetch at touchstart adopted by the navigation; `/account` 412 ms, `/fleet` 411 ms, `/audit` 413 ms in the log), not assets. Flights and Style documents were already warm from idle prefetch (cache); Airlines and Location documents were fetched at tap time (about 50 to 70 ms on loopback).
- Desktop: same files. In the final desktop run Console (/fleet) is tapped after Style, so it shows 3 new files, 63 KB (`style-admin.css` 56.8 KB + 2 scripts); on a first visit to Console before other tabs it would also pull `style-c-lists`, `style-display`, `list-filter`, `value-controls` (an earlier desktop run, superseded, showed 8 files / 153 KB, not kept in the final logs). Desktop taps on /users, /airlines/manage, /audit were not reachable from the Console sidebar in my script, so those three are phone-only.
- Lazy images: no late-popping content was seen on Home (the 4 `loading=lazy` thumbnails are in view and requested at 134 to 163 ms, inside the splash, and the splash waits for in-view lazy images, splash.js:190). `IntersectionObserver` in motion.js:1024 only triggers a card flip animation, not a fetch. The late popping is Style's preview/thumbnail PNGs and Airlines' `w=450` illustrations.

## (c) What the splash waits for (and does not)

- Gate: `splash-boot.js` is a synchronous head script (ui_shell.py:349). It plays once per browser session using `sessionStorage["skypane.splash"]` (splash-boot.js:92-95), adds `splash-on`, and loads `splash.js` through a `<link rel=preload as=script>` (the only preload hint on the site, splash-boot.js:74-77). Hard cap 3200 ms after the boot script runs (splash-boot.js:27, :103).
- Progress = 4 weighted groups (splash.js:117: fonts 0.1, styles 0.2, scripts 0.3, images 0.4): `document.fonts.ready` (always instant here, no web fonts); `link[rel=stylesheet]` already in the current document (:135-136); `script[src]` of the current document seen via resource timing (:158-175); `<img>` that are in view or not lazy (:184-190). The window `load` event forces all four to 1 (:214).
- Timers: the animation is a fixed ~1.8 s sequence (outline 0, flash 420, sweeps 740-950, scan 950, open 1330 + 400 ms; splash.js:38-45), progress forced to 100% at 1900 ms (`FORCE_DONE_MS`, :36), whole splash capped at 3000 ms (`CAP_MS`, :33). Measured finish 1.79 to 1.83 s after splash.js starts, in cold, warm and throttled runs alike.
- It does NOT wait for or fetch: any other tab's stylesheet/script/image, the Location map library, previews or layout thumbnails, other pages' HTML (prefetch.js starts 2500 ms after load, prefetch.js:31, and fetches only HTML of the 2 likely next pages, :40-43; the tap/hover/touch warm-up also fetches HTML only). `style.css` and `style-<area>.css` are linked per page (page_styles.py:20-57), so a page's own area sheet is never in Home's `<head>`.
- It cannot be longer than needed on a slow link but also does not extend for slow links: on throttled phone Home was fully loaded (load event 2335 ms) before the splash closed at 4.17 s, so the splash end tells nothing about the other tabs.

## (d) Ranked fixes (not implemented)

1. Warm the other tabs' static files during/after the splash (CSS + small scripts, ~184 KB CSS and ~165 KB non-map JS, 19 files). Either add them to the splash's script/style group (splash.js :135-175; risk: longer splash on slow links) or, better, fetch them from `prefetch.js` after splash done / on idle using the same `?v=` URLs (so they are immutable cache hits). Effect: taps lose the 65 to 258 KB late static and the 114 to 509 ms (fast) / 359 to 1055 ms (1.6 Mbps) CSS wait. Size: small to medium. Files: `companion/static/prefetch.js` (or `splash.js`), `companion/page_styles.py` and `companion/static_files.py` (list of versioned URLs, e.g. emitted as `data-` attribute or inline JSON by `companion/ui_shell.py`), tests `companion/test_browser_navigation_assist.py`.
2. Style previews: 173 KB tab, previews finish at 2.0 s (3.2 s throttled). Prefetch the preview URLs (immutable, `?v=`) on idle from Home, and/or render/cache them ahead on the server; keep `width/height` attributes (already present) so no layout shift. Size: medium. Files: `companion/settings/layout_picker.py`, `companion/theme_preview.py`, `companion/static/prefetch.js`.
3. Location: prefetch `leaflet.js/css` + place scripts on touchstart/hover of the Location link or idle (145 KB library; scripts chain to 3.1 s throttled). Make the 5 place scripts one request or add `<link rel=preload as=script>` in the head so they are not discovered only at the end of `<body>`. Tiles remain third-party and un-measured. Size: medium. Files: `companion/static/prefetch.js`, `companion/ui_shell.py`, `companion/pages/detection*` (page that lists LEAFLET/PLACE scripts, `ui_base.py:~237`).
4. Preload hints for deferred scripts: `defer` scripts at the end of `<body>` start ~1 s after tap at 1.6 Mbps (Style, Airline editor). Add `<link rel=preload as=script>` (or move `defer` scripts into `<head>`) so they start with the CSS. Size: small. Files: `companion/ui_shell.py`, `companion/ui_base.py`.
5. Airlines `w=450` vs Home `w=264` illustrations are separate downloads (43 KB): share one size, or prefetch `w=450` with the Airlines page. Size: small. Files: `companion/pages/airline_table.py:122`, `companion/pages/home_recent_strip.py:91,98`, `companion/pages/airline_collection_page.py:211`.
6. Account/Console/Audit document latency (~410 ms, not assets): add them to the idle warm list (prefetch.js `IDLE_LIKELY`, :40-43) or cache briefly server-side. Size: small. Files: `companion/static/prefetch.js`.
7. `style-admin.css` is 56.8 KB on first Account/Console visit (largest page sheet): split rarely used rules or let fix 1 cover it. Size: medium. File: `companion/static/style-admin.css`.
8. Verify in production that Caddy compresses `/static` and the PNGs, and that illustrations without a `?v=` token (`private, max-age=3600`) are fine: tap-air-portugal already has `?v=` while the others do not. Size: small. Files: `deploy/Caddyfile`, illustration URL builder.

Not recommended: lengthening the splash to wait for all tabs (the animation is already about 1.9 s warm and 4.2 s throttled); a service worker (none exists; fix 1 gives most of the effect with the existing immutable headers).

## Appendix: desktop per-file tables (1280x900)


**/devices/D/flights** (desktop) - 4 new files, 65 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-c-lists.css | Stylesheet | 11.1 | 107-130 | 112-367 | net |
| /static/style-flights.css | Stylesheet | 6.4 | 107-131 | 113-344 | net |
| /static/list-filter.js | Script | 25.1 | 107-136 | 113-739 | net |
| /static/panel-lookup.js | Script | 22.2 | 108-136 | 114-755 | net |

**/devices/D/airlines** (desktop) - 5 new files, 68 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-airlines.css | Stylesheet | 25.1 | 114-128 | 238-594 | net |
| /devices/D/illustration/easyjet.png?w=450 | Image | 10.9 | 140-210 | 605-1015 | net |
| /devices/D/illustration/tap-air-portugal.png?w=450 | Image | 9.6 | 140-210 | 605-972 | net |
| /devices/D/illustration/transavia-france.png?w=450 | Image | 11.5 | 140-210 | 605-1015 | net |
| /devices/D/illustration/air-france.png?w=450 | Image | 11.3 | 140-210 | 605-1015 | net |

**/devices/D/display** (desktop) - 12 new files, 173 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-c-console.css | Stylesheet | 10.4 | 79-129 | 213-540 | net |
| /static/style-display.css | Stylesheet | 25.0 | 79-129 | 214-795 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=classic&eecac10a3c91 | Image | 6.1 | 79-680 | 336-629 | net |
| /devices/D/frame-preview/white.png?state=departing&size=large&c8d0050cc3d2 | Image | 47.2 | 79-680 | 366-1154 | net |
| /static/confirm-submit.js | Script | 1.2 | 80-130 | 1196-1360 | net |
| /static/theme-preview.js | Script | 17.0 | 80-135 | 1196-1466 | net |
| /static/value-controls.js | Script | 18.6 | 80-138 | 1196-1638 | net |
| /static/calendar-connect.js | Script | 1.0 | 80-178 | 1196-1623 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=a&a0c4242799cd | Image | 14.2 | 126-1440 | 1193-3189 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=b&4696ecff99e9 | Image | 9.2 | 128-954 | 1194-1883 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=c&06d088116061 | Image | 9.0 | 128-733 | 1194-1882 | net |
| /devices/D/frame-preview/white.png?state=departing&size=small&layout=a_diagonal&df7cab7554 | Image | 14.2 | 128-1832 | 1194-3189 | net |

**/devices/D/detection** (desktop) - 9 new files, 258 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-place.css | Stylesheet | 34.3 | 80-101 | 224-825 | net |
| /static/vendor/leaflet/leaflet.css | Stylesheet | 15.0 | 80-101 | 225-629 | net |
| /static/place-start.js | Script | 1.9 | 81-102 | 895-1066 | net |
| /static/vendor/leaflet/leaflet.js | Script | 144.7 | 145-191 | 1162-2082 | net |
| /static/place-search.js | Script | 3.3 | 169-192 | 2072-2253 | net |
| /static/place-map.js | Script | 30.6 | 173-192 | 2249-2598 | net |
| /static/place-map-search.js | Script | 13.9 | 219-277 | 2597-2837 | net |
| /static/place-card.js | Script | 10.8 | 238-277 | 2827-3064 | net |
| /static/place-airport-list.js | Script | 3.3 | 315-339 | 3041-3238 | net |

**/fleet** (desktop) - 3 new files, 63 KB
| file | type | KB | cold: start-end ms after tap | throttled: start-end ms | warm run (only Home was primed) |
|---|---|---|---|---|---|
| /static/style-admin.css | Stylesheet | 56.8 | 136-159 | 221-774 | net |
| /static/update-question.js | Script | 2.8 | 137-159 | 555-737 | net |
| /static/fleet-anchors.js | Script | 3.2 | 137-170 | 555-909 | net |
