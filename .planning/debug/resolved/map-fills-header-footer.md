---
status: resolved
trigger: "Follow-up to the resolved debug session .planning/debug/resolved/location-top-status-bar-band.md (merged as PR #363, live in production). That session gave the Location (\"Lieu\") page's top a real-map lead, a frosted `::before` layer (backdrop-filter blur + eased mask, light-palette tint in both themes) blending Safari's own native status-bar blur into the sharp map below with no visible seam, and a bottom tail — but gated the whole mechanism to a plain Safari tab (`navigator.standalone !== false` in companion/static/place-map.js's leadUnderStatusBar()), leaving the Home Screen app on the older 61-112 treatment (a flat 4px fixed ground strip). The owner (Florian), after going back and forth with screenshots, has now given TWO firm, final decisions (see Eliminated below for the discarded middle positions — do not re-litigate either): (1) remove the custom frosted `::before` layer ENTIRELY, in both the Safari tab and the Home Screen app, and accept the resulting hard visual seam where Safari's own native status-bar blur stops abruptly and sharp map resumes (he was shown exactly what that looks like — a pale horizontal line above the SkyPane logo — and explicitly chose it over keeping the custom frost); (2) the Safari tab and the Home Screen app must be treated identically, no `navigator.standalone` branching at all, same code path for both."
created: 2026-11-12T20:34:21Z
updated: 2026-11-13T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

status_now: RESOLVED. The owner confirmed the fix on his real iPhone, in a
Safari tab and in the Home Screen app ("oui oui j'ai vérifié c'est top").
Fix committed as 16159b85 on claude/map-fills-header-footer-0439ca (not
pushed, no PR). Session archived to resolved/; knowledge base appended.
hypothesis (CONFIRMED): the Home Screen app showed a flat ground band under
the status bar because it never got the lead (navigator.standalone true ->
early return in leadUnderStatusBar()); in iOS 26.5 and 27 a web app with no
status-bar-style meta has the status bar as an obscured inset above the
window (safe-area top 0, innerHeight 812 of 874), exactly like a tab. The
only website-drawn layer over the map behind the app bar was the
place-lead ::before frost, which overrode (and would otherwise have fallen
back to) the unconditional canvas fade ::before.
reasoning_checkpoint:
  hypothesis: "Web app flat band = no lead because of the standalone gate;
    the website's own layer over the map = the ::before (frost, with the
    canvas fade behind it as fallback)."
  confirming_evidence:
    - "Web app probe (27.0 and 26.5): standalone true, safe-top 0,
      innerHeight 812/874, no place-lead; capture = flat band 0-62pt."
    - "Gate removed: web app gets place-lead, scrollY 80, real tiles under
      the clock, map to row 2621 (both iOS versions, both themes)."
    - "::before rules removed: Chromium window from top to search field
      with the bar's parts hidden = bare map (max diff <= 2); restoring the
      frost or the fade fails that test."
  falsification_test: "Web app still shows a flat band or is not at
    scrollY 80; any pixel between the status bar and the search field is
    drawn by the bar itself."
  fix_rationale: "Same lead/tail/lock/settle/nudge for every phone puts map
    above the window in both contexts; no ::before at all leaves only
    iOS's own status-bar blur."
  blind_spots: "Real iPhone (only simulators here); how much blur iOS
    draws differs by version and context (27 web app: tall, over the top
    of the logo; 27 tab: short; 26.5: almost none) - this is iOS, not the
    page; the wordmark now sits on bare map labels; non-iOS phone browsers
    (Android Chrome) now also get the lead/tail/scroll lock, untested on a
    device."
next_action: none. Push the branch and open a PR when the owner asks
(PRs are squash-merged).

## Symptoms
<!-- Written during gathering, then immutable -->

expected: On the Location (\"Lieu\") page, on a phone, in EITHER a Safari
tab or the Home Screen app (no distinction between the two): the map
reaches under the status-bar zone at the top (showing Safari's own native
blur where Safari naturally applies it, and sharp map immediately below
that — a visible transition is now explicitly accepted, not a bug to
fix) and under whatever inset exists at the bottom. No separate, custom-
added blur/frost layer from the website itself.

actual: In a Safari tab (PR #363, merged, live in production): real map
top and bottom, but with an added custom frosted layer blending Safari's
native blur into the sharp map with no visible seam — the owner wants
this custom layer gone. In the Home Screen app: still the older flat 4px
ground-strip treatment (not touched by #363 at all), to be unified with
whatever the Safari tab ends up looking like once the frost is removed.

errors: None — purely visual/layout, no console errors, no crash.

reproduction: Safari tab: open /detection on a phone-width viewport in a
plain Safari tab, look at the top ~150px. Home Screen app: Safari Share ->
\"Add to Home Screen\", open that icon, same page, same region.

started: The custom frost was added in cycles 2-4 of the resolved
session (location-top-status-bar-band) specifically to fix a \"hard seam\"
defect the owner rejected in an early cycle. He has now seen exactly what
that rejected look was (a screenshot) and, fully informed, has chosen to
accept it anyway in exchange for removing the added complexity — this is
a deliberate reversal of an earlier decision in the same investigation
thread, not a new, unexplained request.

## Additional scope (from conversation, not a classic symptom field)

**Owner's own words, for the exact ask (French, kept verbatim as the
clearest record of intent):**
- \"je me demande si tu peux pas juste supprimer l'effet de flou que tu as
  ajouté et laisser juste iOS gérer le flou nécessaire pour les
  contrôleurs qui sont en haut\"
- \"les deux doivent être traités pareil sans distinguo\" (Safari tab and
  Home Screen app)
- After being shown a screenshot of the rejected cycle-1 hard-seam look
  and asked explicitly whether he still wants the frost removed knowing
  it brings that back: \"Le supprimer complètement, j'accepte la coupure
  nette\" (remove it completely, I accept the hard cut).

**Explicitly settled by the owner, do NOT re-ask or re-litigate:**
- The custom frosted `::before` blur layer: REMOVE it, in both contexts,
  accepting the resulting visible hard seam where Safari's native blur
  stops. This was asked, walked back once mid-conversation, then
  reconfirmed after being shown exactly what it costs — this final answer
  stands.
- Safari tab vs Home Screen app: no distinction, identical treatment.
- The bottom tab-bar pill (`.tab-bar`, shared across every page of the
  app) stays opaque — NOT in scope, do not touch. Only the map visible
  around/behind it (already working since PR #363) matters.
- Desktop/wide screens (>= 960px): out of scope, untouched.

**Do not touch, from PR #363, outside the two changes above:** the lead/
tail map-sizing mechanism itself (80px above/below), the page-scroll-lock
(`overflow: hidden` on `<html>`), the dark-mode light-palette tint on the
logo/wordmark/pill (that part of the fix is unrelated to the frost layer
and stays), the search-field frost-clipping fix (moot once the frost
layer itself is removed, but don't go looking for other things to change
there), and the post-splash 1px nudge (still needed for Safari's \"last
scroll position\" status-bar-colour quirk, unrelated to the frost).

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

- hypothesis: the owner wants to keep the custom frosted blur layer from
  PR #363 and is only reporting an unrelated \"ligne blanche chelou\"
  artifact elsewhere.
  why_eliminated: this was the orchestrator's own mid-conversation
  misreading of a garbled voice-dictated message. The owner's follow-up,
  with an annotated screenshot circling the exact frosted region and the
  words \"il faut supprimer [ce flou], visiblement ça c'est pas normal,
  c'est quelque chose qui est généré par ton site web\", then his explicit
  final answer (\"Le supprimer complètement, j'accepte la coupure nette\")
  after being shown the cost, settle this unambiguously: he wants it
  removed. Do not revert to the earlier reading.
- hypothesis: the bottom tab-bar pill itself needs to become transparent/
  glass so the map shows through it.
  why_eliminated: owner explicitly confirmed "non, juste autour d'elle" —
  the pill stays opaque; only the map around it (already working) matters.

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-11-12T20:45:00Z
  checked: companion/static/style-place.css (phone block 711-907, the
  unconditional app-bar fade 682-705, the wide-screen `content: none`
  1077-1081, `.place-edge` 1199-1221), companion/static/place-map.js
  (leadUnderStatusBar 956-1015, nudge/afterSplash 1017-1051, start 1055,
  the failure path 1165-1184), companion/test_browser_place_document_map.py
  (all 790 lines), 61-112-SUMMARY.md.
  found: (1) The only gate between the Safari tab and the Home Screen app
  is `if (window.navigator.standalone !== false) return;` in
  leadUnderStatusBar(); every lead/tail/lock/light-ink/frost/strip-hiding
  rule in the CSS keys on the `place-lead` class it adds, and the nudge
  only runs from inside it. That gate also excludes every non-iOS browser
  (standalone is undefined there), which is how the Chromium suite sees
  the no-lead layout unless a test injects `standalone = false`.
  (2) The frost is the place-lead `::before` rule (878-898); it OVERRIDES
  the unconditional fade (694-705: canvas 85% -> transparent, from
  safe-top + 4px, 100% - safe-top + 20px tall). Deleting only the frost
  rule would bring that fade back in the lead case: in a tab (safe-top 0)
  an 85%-opaque edge 4px below the window top, i.e. right at the status
  bar's lower edge, then canvas over the logo row; in the dark theme a
  #161A24 fade under the light-palette ink (#17191F) that cycle 3 put on
  the brand and frame button, i.e. dark ink on a dark fade. So the old
  fade is not neutral under the new geometry; it is a second
  website-drawn layer over the map.
  (3) With the lead applied on every phone, `.map-ready.place-lead
  .place-edge { display: none }` hides the 4px strip in the Home Screen
  app too once the map runs (it still shows while the map loads), and the
  unconditional fade would only be reachable on a phone without the lead
  (none left) - dead code.
  implication: "remove the frost entirely" means the app bar draws NO
  backdrop of its own in the lead case (no frost, no fade); the
  canvas-fade rule must go with it or it reappears. Needs a visual check
  of the brand on the bare tiles (contrast) before deciding, and a
  standalone measurement before trusting the lead/tail there.

- timestamp: 2026-11-12T21:50:00Z
  checked: HEAD (f80ea4e1, exported to scratchpad/b366, served on :8750
  behind the signing proxy) in the iOS 27.0 iPhone 18 Pro simulator, status
  bar pinned 9:41. A real Home Screen web app installed with Maestro
  (Safari menu -> Partager -> Sur l'ecran d'accueil, "Ouvrir comme app
  web" on, named B366; opens com.apple.webapp). A probe script injected by
  the proxy (scratchpad/inject.js) logs navigator.standalone, insets and
  viewport sizes 3s and 8s after load. Captures c5/tab-before-{L,D},
  c5/app-before-{L2,D}.
  found: SAFARI TAB: standalone false, innerHeight 714, screen 874,
  safe-area top 0 / bottom 0, lvh 754, scrollY 80, scroll range 200,
  classes "map-ready place-lead": the #363 look (frost under the status bar
  into the app bar), map to row 2621/2622. HOME SCREEN APP: standalone
  true, innerHeight 812, screen 874, safe-area top 0px (!), bottom 34px,
  lvh 874, svh 812, scrollY 0, scroll range 62, no place-lead class. So
  in the iOS 27 web app the status bar zone (62pt) is ALSO an obscured
  inset above the window (the page does not reach under it, there is no
  apple-mobile-web-app-status-bar-style meta), while the window reaches the
  screen bottom (no bottom obscured inset, a 34px home-indicator safe
  area). Visually the app shows exactly the pre-#363 tab defect: a flat
  ground band 0-62pt under the clock (the 4px strip's colour extended by
  WebKit), then the canvas fade behind the logo (dark fade with white ink
  in the dark theme), map below; map to row 2621. The page is also
  hand-draggable by 62px there today (100lvh 874 > window 812).
  implication: the lead applies to the web app for the same reason as to
  the tab (map content above the window is what fills the status bar
  zone). The tail is below the screen there (window bottom = screen
  bottom), invisible but harmless; the scroll lock also removes today's
  62px drag. Same 80px constants are enough (62pt top zone < 80).

- timestamp: 2026-11-12T22:20:00Z
  checked: fix applied in the worktree (place-map.js: no standalone gate;
  style-place.css: the place-lead frost ::before, the unconditional canvas
  fade ::before and the wide-screen `content: none` all removed, the 4px
  strip now only while the map loads), served on :8745 (style-place.css
  ?v=7522cb9eee77, place-map.js ?v=4722a6c27f69); a second web clip BFIX
  installed the same way. Same simulator, fresh launch per capture:
  c5/tab-fix-{L,D}, c5/app-fix-{L,D}; grid c5/grid-before-after.png;
  profile.py (x 470-700px, the gap between the wordmark and the frame
  button); c5/inkios5.py (ink = darkest 2%, bg = lighter half); a Maestro
  drag on the sheet card (15%,77% -> 15%,57%) in each web app with the
  probe logging every new scrollY.
  found: WEB APP: classes "map-ready place-lead", scrollY 80, scroll range
  222, standalone true; real tiles under the clock with iOS's own blur,
  no flat band; map to row 2621/2622 in both themes; dark theme drawn like
  light (light ink, light blur). iOS's own blur in the web app is taller
  than in the tab: fully blurred 0-68pt (detail 0.8-1.0), fading out
  68-104pt (detail 1.2 -> 33), i.e. over the top of the logo, wordmark and
  frame button (the app bar spans 62-114pt there). TAB: Safari's blur only
  over the top of the zone, sharp map from ~32pt (detail 2.7 -> 12 at
  40pt), the accepted hard cut across the status icons; map to row 2621.
  Nothing of the page is drawn between the status bar and the search
  field but the brand and the frame button. Ink contrast (mean / worst
  bg): tab wordmark 13.3/11.2, frame 15.9/15.9, logo 13.1/10.4 (same in
  both themes); web app wordmark 11.7/8.9, frame 10.6/10.3, logo 12.1/9.7
  (iOS's blur washes them a little); tab before (frost) 14.5/16.6/14.4.
  Drag on the sheet: BFIX no scroll event, 0.00% pixels changed; B366 (the
  web app today) scrolls 5 -> 62 and stays there (42% of pixels moved).
  implication: falsification test passed in the simulator: the web app
  shows map under the status bar like the tab, identical code path; no
  website layer remains. The look differs only by iOS's own blur, which
  is taller in a web app than in a Safari tab, and by the map labels the
  wordmark happens to sit on (it is on bare map now). Bonus: the web app
  no longer drags by 62px from the sheet.

- timestamp: 2026-11-12T22:50:00Z
  checked: iOS 26.5 iPhone 17 Pro simulator (owner's phone runs iOS 26
  per ledger W169), booted for this: Safari tab on :8750 (before) and
  :8745 (fix), and a web clip F26 of :8745 installed with Maestro (iOS
  26.5 menu: "Plus" -> Partager -> Sur l'ecran d'accueil); probe logged.
  Grid c5/grid-ios26.png.
  found: iOS 26.5 web app: standalone true, safe-area top 0, innerHeight
  812 of 874, scrollY 80, place-lead - same layout model as iOS 27; map to
  row 2621. iOS's own blur is much lighter on 26.5: tab = slight softening
  over ~0-20pt (detail 2.3-2.9) then sharp (12+ at 24pt); web app = faint
  softening over ~0-24pt (detail 2.7-6) then sharp. So on iOS 26 the clock
  and status icons sit over nearly sharp map in both contexts. Before (tab,
  frost): fully blurred band (detail 0.4-1.3 to 68pt).
  implication: the mechanism holds on iOS 26.5 for the web app too. What
  "let iOS handle the blur" gives depends on the iOS version: almost no
  blur on 26.5, a short blur in a 27 tab, a tall one in a 27 web app.

- timestamp: 2026-11-12T23:05:00Z
  checked: Chromium suite. test_browser_place_document_map.py rewritten:
  the 59px-inset "Home Screen app keeps the strip" test and the three frost
  tests removed; new test_the_app_bar_draws_nothing_of_its_own_over_the_map
  (header and its pseudo elements: no fill, gradient, blur, mask; the
  window down to the search field with the bar's parts hidden equals it
  with the whole bar hidden, max diff <= 2; 2 themes x 390/360); the lead,
  no-hand-scroll and post-splash nudge tests parametrized over
  navigator.standalone false / true / undefined (Safari tab, Home Screen
  app, other browser); renamed tests that were "in a Safari tab"; the
  theme-equality test now tolerates the logo's antialiasing (15 px of
  20280 differ by up to 15 levels between themes, deterministic; a tint
  would change most of the band). Other files whose phone assumptions were
  "no lead in Chromium": place_page (box probe measured from the rest
  position, map covers the stage instead of equal height, PAGE_OVERFLOW),
  place_boot, place_compact_sheet (PAGE_OVERFLOW instead of scroll range
  0), location_full_bleed (map top/bottom = -lead/-tail), place_sheet (map
  reaches past both window edges), place_pins (no ::before instead of a
  gradient). test-support/place_map_support.py: SETTLED and HIT_PROBE
  scroll elements to the middle without moving the window when the page
  has a lead (it would settle back 250ms later, under the measurement);
  new PAGE_OVERFLOW. Mutations (scratchpad/c5/mutrun5.py): restoring the
  standalone gate fails 16 (every home-screen-app/other-browser lead,
  scroll and nudge case, plus the spanning test); restoring the frost
  fails 5; restoring the canvas fade fails 7. Render baseline regenerated
  (only style-place.css?v= moved, 4 entries, 4ece1be2a693 -> 7522cb9eee77).
  ruff (companion/, test-support/), check_comment_history, node --check
  pass. First 65-file regression run: 61 failed, 2644 passed - 24 known
  font-serialisation cases, the files fixed above, and flaky ones also
  failing on an untouched HEAD export (ux_01, ux_03 lightbox refresh 2/6 vs
  1/6 on HEAD, tab_pill_transition and search_loading 15s timeouts).
  implication: the new behaviour is locked by non-vacuous tests.

- timestamp: 2026-11-13T00:00:00Z
  checked: human verification on the owner's real iPhone, in a Safari tab
  and in the Home Screen app; re-ran companion/test_browser_place_document_map.py
  on the worktree before committing.
  found: owner: "oui oui j'ai vérifié c'est top" (confirmed fixed in both
  contexts). Test file: 43 passed.
  implication: fix accepted; committed as 16159b85.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: (1) The lead/tail mechanism of PR #363 was gated to a Safari
tab by `if (window.navigator.standalone !== false) return;` in
leadUnderStatusBar(). In iOS 26.5 and 27 a Home Screen web app without an
apple-mobile-web-app-status-bar-style meta also has the status bar as an
obscured inset above the window (safe-area top 0, innerHeight 812 of
874pt), so with no lead it showed the same flat ground band the tab had
before #363 (the 4px fixed strip's colour extended by WebKit), plus the
canvas fade behind the logo (dark fade, white ink in the dark theme), and
the page could be dragged by 62px (100lvh 874 > window 812). (2) The custom
blur the owner wants gone is the place-lead `.site-header::before` frost;
it overrode an older unconditional canvas fade `::before` (85% canvas ->
transparent from safe-top + 4px), so deleting only the frost would have
brought that fade back as another website-drawn layer (with an 85% edge at
the status bar's lower edge in a tab, and a dark fade under the cycle-3
light ink in the dark theme).
fix: place-map.js: the standalone early return is gone; the lead, tail,
scroll lock, settle-back and post-splash nudge run whenever the map runs,
on every phone (CSS still confines them to < 960px; other browsers show
neither the lead nor the tail). style-place.css: removed the place-lead
frost ::before, the unconditional canvas fade ::before and the wide-screen
`content: none` that suppressed it - the app bar has no ::before at all;
the 4px `.place-edge` strip now only shows while the map loads (the
`.map-ready` selector and the place-lead hide rule dropped); comments
updated. Kept: lead/tail sizes, overflow hidden, light-palette ink on the
brand and frame button, the nudge. Tests: see Evidence 23:05.
verification: iOS 27.0 simulator (Safari tab + real web app, light/dark):
web app now place-lead, scrollY 80, real tiles under the clock, map to row
2621, dark drawn like light, drag on the sheet moves nothing (was: flat
band, scrolls to 62 and stays). Tab: map under the clock with only
Safari's short blur and the accepted hard cut; map to row 2621. iOS 26.5
simulator: same layout in tab and web app; iOS's own blur almost absent.
Chromium: new/updated tests green, 3 mutations caught (gate 16 fails,
frost 5, fade 7); 65-file regression set 2678 passed, 27 failed = 24 known
font-serialisation cases + 3 load timeouts also seen on an untouched HEAD
export. ruff, check_comment_history, node --check pass; render baseline:
only the style-place.css hash moved. Human: confirmed fixed by the owner
on his real iPhone, Safari tab and Home Screen app (2026-11-13).
oracle_type: derived (layout contract: the map's box spans lead + window
+ tail and the page rests at scrollY = lead whatever navigator.standalone
is; the app bar's region equals bare map with the bar's parts hidden).
commit: 16159b85
prevention:
  five_whys:
    code: "The Home Screen app had no lead -> leadUnderStatusBar() returned
      early on navigator.standalone -> #363 assumed a web app draws under
      the status bar (safe-area top > 0) -> that assumption came from older
      iOS behaviour and was never measured on a real web app."
    environment: "Why was it not measured? -> the #363 work ran only in a
      Safari tab in the simulator; installing a real Home Screen web app
      took an extra Maestro flow nobody had built yet -> the Chromium suite
      only ever saw standalone undefined (no lead) or false (lead), never
      true."
    code_layering: "Why would removing the frost have left a layer behind?
      -> the frost ::before overrode an older unconditional fade ::before
      on the same element -> a CSS override hides the rule underneath, so
      deleting the winner brings back the loser."
  why_not_caught: "No gate existed for this class. The Chromium tests
    injected navigator.standalone = false for the lead case only, and one
    test locked the gate in on purpose (a 59px-inset 'Home Screen app keeps
    the strip' test). No test said the app bar draws nothing over the map,
    so neither the frost nor the fade behind it was flagged as a layer."
  recurrence_guard: "companion/test_browser_place_document_map.py:
    test_the_app_bar_draws_nothing_of_its_own_over_the_map (no fill,
    gradient, blur or mask on the header or its pseudo elements; pixel
    equality with the bar's parts hidden; 2 themes x 390/360), and
    test_the_page_starts_scrolled_past_a_lead_of_map_under_the_status_bar,
    test_the_page_does_not_scroll_by_hand_over_the_sheet and
    test_the_page_nudges_its_scroll_once_the_opening_splash_has_gone, each
    parametrized over navigator.standalone false / true / undefined.
    Mutations: restoring the gate fails 16 tests, the frost 5, the fade 7.
    43 passed on 2026-11-13."
files_changed:
  - companion/static/place-map.js
  - companion/static/style-place.css
  - companion/test_browser_place_document_map.py
  - companion/test_browser_place_pins.py
  - companion/test_browser_place_page.py
  - companion/test_browser_place_boot.py
  - companion/test_browser_place_compact_sheet.py
  - companion/test_browser_location_full_bleed.py
  - companion/test_browser_place_sheet.py
  - test-support/place_map_support.py
  - companion/testdata/render_baseline.json
  - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-UI-SPEC.md
