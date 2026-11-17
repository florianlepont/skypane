---
status: resolved
trigger: "Location page (\"Lieu\"), iPhone Safari tab, top status-bar zone: the real map used to paint full-bleed under the status bar (confirmed by the owner ledger after PR #318, round 16: \"the top of the map now goes under the status bar\") because `.place-map` was `position: fixed; inset: 0; min-height: 100lvh` (companion/static/style.css at commit 3573db7b). Plan 61-105 moved the map out of `position: fixed` into document flow (`position: absolute; height: 100lvh` inside `.page-content`) specifically to fix a bottom-edge band under Safari's collapsing bottom toolbar — but that regressed the top: only genuinely `position: fixed` content seems to paint under Safari's translucent top status-bar overlay in a tab; ordinary document-flow content does not, even at inset:0. Plans 61-111 and 61-112 tried to recover the top without reverting to `fixed` (to avoid re-breaking the bottom): 111 matched the wrong reference build (75635805, which never had the real top behaviour); 112 correctly identified #318 as the true reference but only patched with a 4px `.place-edge` ground-coloured fixed strip plus an adjusted app-bar fade — a visual approximation, not the real full-bleed map. The owner (Florian) just re-tested in a real Safari tab (iOS simulator) and confirms the flat band is still there, matching his memory that it used to be the real map. Goal: find a fix that keeps BOTH edges correct (top full-bleed under the status bar AND bottom reaching under Safari's collapsing toolbar) in a Safari tab on iPhone, without breaking the already-fixed Home Screen app veil case from 61-112."
created: 2026-11-12T10:12:25Z
updated: 2026-11-12T16:35:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

status_final: RESOLVED. The owner confirmed cycle 4 on his real iPhone
("confirmed fixed"): the search field is solid dark from its top edge in
dark mode, and everything confirmed earlier still holds (top full-bleed
under the status bar in both themes, bottom under Safari's collapsing
toolbar, no page drag from the sheet, dark-mode tint matching light mode,
Home Screen app veil still fixed). Final gates re-run on the final tree
(Evidence 16:30); committed locally, session archived to resolved/,
knowledge base appended.
next_action: none.
cycle4_state: (below, kept for reference)
cycle: 4 (owner checkpoint: cycle-3 dark tint CONFIRMED in the simulator by
the coordinator; NEW polish issue on the real iPhone: the frost reaches down
onto the top edge of the search field "Aéroport (ORY) ou adresse", hazy top
~15-20% of the pill, very visible in dark mode, faint in light mode)
hypothesis (H-reach): the frost ::before ends 48px (--space-2xl) below the
app bar (window y 100 in a tab) while the search pill starts 12px below the
bar (window y 64); the header (z-index 15) stacks above .place-float (z 3),
so the pale tinted, blurred, half-faded frost paints over the pill's top
~36px. The geometry dates from cycle 2; cycle 3's light tint over the dark
pill made it visible in dark mode.
test: computed geometry (frost bottom vs pill top) and stacking in Chromium;
pill top rows vs middle rows with and without the ::before; cycle-2 vs
cycle-3 tree in the simulator, dark.
expecting: frost bottom 100 > pill top 64; haze gone with ::before removed;
pill background opaque (#151922 dark); cycle 2 dark shows a dark-on-dark
overlap (barely visible), cycle 3 a pale haze.
status_c4: H-reach CONFIRMED (Evidence 17:10): cause (a) only, from cycle 2.
reasoning_checkpoint_cycle4:
  hypothesis: "The haze on the search pill's top is the app bar's frost
    ::before (header z-index 15, above .place-float z-index 3) reaching 48px
    below the bar, 36px into the pill that starts 12px below the bar."
  confirming_evidence:
    - "Chromium computed boxes: frost -80..100, pill 64..118, both themes."
    - "Pill rows with the frost hidden equal the opaque fill (26.6 dark);
      with it, +66 levels at the top row fading out by 34px (cycle 3 dark)."
    - "A frost ending at 64 (variants.py): pill pixels identical with and
      without the frost (max diff 0), both themes."
  falsification_test: "With the frost ending at the bar bottom + 12px, the
    pill's top rows still differ from its fill in the simulator (dark), or
    the line-pattern profile shows a step (> 0.3 per 6px band)."
  fix_rationale: "Ends the layer where the field starts, so nothing of it is
    drawn over the field; the solid part (to the bar's middle) and the
    eased mask stay, so the blur still fades out with no edge."
  blind_spots: "Real iPhone; a 40px fade (was 76px) is steeper (max 0.27
    per 6px band vs 0.15), possibly visible as a softer-but-shorter end;
    ink contrast drops slightly (wordmark 8.0 -> 7.6, logo 9.9 -> 8.5)."
fix_c4: applied and verified in the simulator (Evidence 17:50) and in
Chromium (Evidence 18:20); awaiting the owner's real-iPhone check.
next_action: owner verifies on the real iPhone (Safari tab, dark and light,
reached from another tab and fresh open on Lieu): the search field's top
edge is crisp, with no haze, and the blur still fades out above it with no
line. On "confirmed fixed", commit the six changed files (place-map.js,
style-place.css, test_browser_place_document_map.py, render_baseline.json,
61-UI-SPEC.md, plus this session file), archive the session, append the
knowledge base. Nothing committed.
cycle3_state: (below, kept for reference)
cycle: 3 (owner checkpoint: cycle 2 top/bottom/drag confirmed; ONE issue
left, dark mode only: the frosted top band fades from a pale tint under the
status bar to dark grey behind the logo and the app bar; the owner wants it
the same as light mode, "just remove the dark here")
status: both causes confirmed and fixed in the simulator (Evidence 14:25 to
16:10); awaiting the owner's real-iPhone check.
hypothesis (H-dark-tint, CONFIRMED): the frosted layer's gradient ends on
`color-mix(var(--color-canvas) 70%)`, #161A24 in the dark theme; the logo,
wordmark and frame button carry dark-theme ink that only reads on it.
hypothesis (H-pocket, CONFIRMED): Safari keeps its status-bar pocket's look
from the page's last scroll; the page scrolls past the lead under the dark
opening splash and never again, so a grey veil stays over 0-48pt.
reasoning_checkpoint_cycle3:
  hypothesis: "Dark mode's grey gradient = the frost's dark canvas stop;
    the residual veil after a fresh open = Safari's pocket sampled under the
    dark splash at the only scroll."
  confirming_evidence:
    - "Light tokens on ::before/.brand/.frame-menu__button: rows >= 50pt in
      dark equal the light baseline exactly; clock turns black."
    - "Forcing the whole light palette, light theme-color, light html bg or
      color-scheme did not lift the 0-48pt veil; a 1px scroll nudge after
      the splash did (191 -> 218.6), and no splash (tab-bar navigation) had
      no veil at all."
  falsification_test: "With both changes, a dark-theme capture differs from
    the light-theme capture in the top 330px, or the veil remains after a
    fresh open."
  fix_rationale: "Draws the band from the same palette in both themes and
    makes Safari re-sample the page once the splash has gone."
  blind_spots: "Real iPhone timing of Safari's pocket sampling (400ms
    margin over a 300ms simulator threshold); iOS 26 not re-run this cycle;
    the Home Screen app is untouched by design and not re-checked."
next_action: owner verifies on the real iPhone (dark mode, Safari tab, both
reaching Lieu from another tab and opening the site fresh on Lieu); on
"confirmed fixed", commit the six changed files, archive the session,
append the knowledge base. Nothing committed.
cycle2_state: (below, kept for reference)
cycle: 2 (owner checkpoint NOT confirmed: new seam at the top, band still at
the bottom)
hypothesis (top, H-seam): the seam is the bottom edge of Safari's own soft
scroll-edge blur, which covers only the top ~30pt of the 63pt status-bar
zone and ends over sharp tiles; below it sharp map, then the app bar fade
(starting at 67pt) - blur/sharp/pale/sharp layers.
hypothesis (bottom, H-tail): 100lvh in iOS 26+/27 Safari stops above the
collapsed toolbar's zone, so the map (lead + 100lvh) ends ~59pt above the
screen bottom on iOS 27 (row 2447/2622) in BOTH toolbar states; the bottom
inset shows the flat body colour. Pre-existing on HEAD (same row), never
fixed by 61-105 on these iOS versions.
status: both hypotheses confirmed; cycle-2 fix applied and verified in
the simulators (see Evidence 12:24-12:45 and Resolution).
next_action: await owner human-verify on a real iPhone (Safari tab, light
and dark, top and bottom, drag on the sheet, keyboard on the radius field)
and in the Home Screen app; on "confirmed fixed", commit the five changed
files, archive this session, append the knowledge base. Nothing committed.
reasoning_checkpoint_cycle2:
  hypothesis: "Top seam = end of Safari's own soft blur (full 0-20pt, steps
    out by 48pt) over sharp map; bottom band = 100lvh (754) stops 57pt above
    the screen even collapsed, so the bottom inset shows no document, worse
    after a drag scrolls the short page to its end."
  confirming_evidence:
    - "Line probe: contrast 1-2 at 0-20pt, 7..248 from 20 to 48pt, sharp after."
    - "Probe: innerHeight 714, lvh 754, screen 874; HEAD map ends row 2447 (27.0)."
    - "Maestro drag on the sheet: HEAD and cycle 1 both scroll to the end, 98pt band."
  falsification_test: "With the frosted layer the top profile still shows a
    step, or with the tail the map still ends above row 2621 at rest or after
    a drag."
  fix_rationale: "The page supplies the blur Safari stops short of, and the
    document the toolbar inset needs, and stops hand scrolling from exposing
    the document's end."
  blind_spots: "Real iPhone rendering of backdrop-filter in the obscured
    inset; the collapsed toolbar on the real page; other iPhone sizes'
    collapsed-bar insets (80px tail assumed enough); dark-mode taste."
reasoning_checkpoint:
  hypothesis: "In an iPhone Safari tab the status-bar zone is an obscured
    inset of the scroll view ABOVE the layout viewport (safe-area-inset-top
    is 0). Safari fills it with whatever document content lies above the
    viewport, or, at scrollY=0, a flat colour (under-page background, or a
    fixed top box's colour). The Location page sits at scrollY=0 with the
    map starting at the document top, so the zone is always a flat colour;
    #318's fixed map gave the same, only in the html surface colour."
  confirming_evidence:
    - "Simulator (iOS 27.0 and 26.5): every scrollY=0 variant (fixed map,
      document map, strip, map pulled to negative coordinates) shows a flat
      63pt band; a document scrolled down by >= 63px shows real tiles there."
    - "Real #318 build and real HEAD, run locally, both show a flat band in
      the same simulator (bluish #E9EEF5 and ground #F2EFE9 respectively)."
    - "WebKit source: fixed top boxes only feed an opaque WKColorExtensionView
      or the soft scroll pocket; a fixed box itself sits below the inset."
    - "Repro with a 100px lead scrolled past shows tiles under the clock on
      both iOS versions; bottom unchanged."
  falsification_test: "With the lead applied to the real page, the
    simulator still shows a flat band at the top of the Location page, or
    the bottom of the map ends higher than on HEAD."
  fix_rationale: "The defect is that no map content exists above the
    viewport; the lead puts map content there and the initial scroll moves
    it under the status bar. It works with Safari's model instead of trying
    to paint into the inset, which no CSS/fixed technique can do."
  blind_spots: "Touch gestures (pulling the page down into the lead, the
    toolbar collapsing, keyboard focus scrolling) cannot be driven in the
    simulator from here; the settle-back logic is only exercised by
    programmatic scrolls. The Home Screen app (standalone) is untested on a
    device here: it is excluded via navigator.standalone and keeps 61-112's
    rules unchanged. Real iPhone status bar heights other than 63pt."
tdd_checkpoint: null

## Symptoms
<!-- Written during gathering, then immutable -->

expected: On the Location ("Lieu") page, viewed in a plain Safari tab on
iPhone (not added to the Home Screen), the real map should visually extend
under BOTH iOS chrome bars at once: under the translucent top status bar
(no flat colour band, no blurred veil) AND under Safari's bottom toolbar
once it collapses on scroll (no flat band at the bottom either).

actual: Right now there is a flat, ground-coloured band covering the top
status-bar zone (confirmed live on 2026-11-12 in the iOS Simulator, Safari
tab, production `skypane.algernon.is`, "Frame of The City" / "Lieu" nav tab
active) — not real map content. The owner's memory, and the project's own
`61-OWNER-VALIDATION.md` ledger, record that the real map DID paint under
the status bar in a tab for one specific build: round 16, right after PR
#318 ("the top of the map now goes under the status bar"). That is the only
build the ledger records as having the wanted top behaviour.

errors: None — purely a visual/layout regression, no console errors, no
crash. Confirmed not a 403/auth issue (the simulator session was correctly
signed in before this was observed).

reproduction: Open the companion's Location/`/detection` page in Safari as a
normal browser tab (not "Add to Home Screen") on an iPhone — a real device or
the iOS Simulator with Safari, e.g. the simulator already attached in this
session (`iPhone 18 Pro`). Look at the physical top edge of the screen, under
the clock/wifi/battery status-bar icons. Currently: a flat beige/cream band
(the tile ground colour), no map content, no blurred veil either.

started: Introduced by plan 61-105 (commit `74f5d1ae`, "Location map as
document content on phones") on top of the good build from PR #318
(`3573db7b`, round 16) — 61-105 deliberately moved `.place-map` out of
`position: fixed` to fix a bottom-edge band, trading away the top full-bleed
behaviour the owner had just confirmed as correct. Plans 61-111 (`445bfcb2`)
and 61-112 (`5d5559b2`, latest, already merged to main via PR #357) both
attempted to fix the resulting top-edge symptom without reverting to
`position: fixed`, and neither restored the real map — 112's `.place-edge`
is a decorative 4px fixed strip in the ground colour, not the map itself.
The owner re-tested live today (iOS Simulator, Safari tab) after 112 shipped
to production and the band is still there, confirming 112 did not solve this
specific defect (it only removed the earlier *blurred veil*, a related but
different symptom, which IS confirmed fixed).

## Additional scope (from conversation, not a classic symptom field)

**Constraint — do not re-break what 61-105 fixed:** whatever the fix, the
Location page must still reach under Safari's *bottom* collapsing toolbar in
a tab (the thing plan 61-105 fixed) and the Home Screen / standalone-app case
fixed by 61-112 (no blurred veil, `.place-edge` ground strip while the map or
its loading placeholder shows) must still hold. This is a three-way
constraint (top full-bleed in a tab + bottom full-bleed in a tab + no veil in
the Home Screen app), not a two-way one — re-verify all three, not just the
top.

**Suggested avenue (not yet validated):** keep `.place-map` `position: fixed`
again, but size/position it from JS using the `window.visualViewport` API
(`resize`/`scroll` listeners updating a CSS custom property, e.g.
`--real-vh`) instead of relying purely on CSS `100lvh`/`100dvh`/`100svh`,
so the fixed box can track the bottom toolbar's live collapse the same way
Safari's own chrome does. No file in this repo currently references
`visualViewport` (checked via grep across `.planning`, `companion/static`,
`companion/*.py` — zero matches), so this is unexplored territory here, not
a previously-tried-and-rejected approach.

**Verified build history** (via `git show <sha>:companion/static/style.css`):
at `3573db7b` (PR #318, the good build), the rule was:
```css
.map-ready .place-map {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: clip;
  width: auto;
  height: auto;
  min-height: 100lvh;   /* "the map also runs under the browser's
                            toolbars, which a fixed box sized to the
                            smallest viewport leaves uncovered" */
  background: var(--color-map-ground);
}
```
Even this used `min-height: 100lvh` already (an attempt at covering the
bottom toolbar collapse) — and round 16's own owner note says the bottom
band still remained afterward ("map ends about 8% above the screen bottom").
So `fixed` + `min-height: 100lvh` alone was NOT sufficient for the bottom
either; plan 61-105's document-flow approach is a materially different,
apparently more effective technique for the bottom. Any fix route that
re-adopts `position: fixed` for the top needs its own, independently-verified
technique for the bottom (visualViewport-driven sizing is untried, not
proven).

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

- hypothesis: 61-112's `.place-edge` fixed ground-coloured strip plus the
  adjusted app-bar fade recovers the full-bleed map at the top.
  why_eliminated: owner re-tested live (iOS Simulator, Safari tab, production
  after PR #357) on 2026-11-12 and the flat band is still there, unchanged
  from before 61-112. 112 only removed the blurred *veil* (a related but
  separate symptom, confirmed fixed), never the map's own absence from that
  zone.

- hypothesis: build `75635805` (PR #331) is the right reference build to
  match for the top edge (per plan 61-111).
  why_eliminated: plan 61-112's own diff analysis showed `75635805`'s
  top-edge CSS chain is identical to the then-current HEAD, and the owner
  still saw the band on that build too — it never had the real behaviour.
  The true reference is `3573db7b` (PR #318, round 16), confirmed by the
  owner ledger's explicit "the top of the map now goes under the status bar"
  note.

- hypothesis: only `position: fixed` content paints under Safari's
  status bar in a tab, so #318's fixed map showed tiles there and 61-105's
  document map lost them (the trigger's premise).
  why_eliminated: the real #318 build, run locally in the iOS 27.0 and the
  iOS 26.5 simulators, shows a flat #E9EEF5 band at the top (and the round-16
  bottom band); a fixed box at top:0 sits below the status bar (the 4px strip
  rendered at 63-67pt). Document content is what Safari shows there, once
  the page is scrolled.
  timestamp: 2026-11-12T10:55:00Z

- hypothesis: keep the map fixed and size it from visualViewport to fix the
  bottom (the suggested avenue).
  why_eliminated: a fixed box never reaches into the status-bar inset, so it
  cannot give tiles at the top whatever its sizing; WebKit only extends its
  colour (WKWebView `_updateFixedColorExtensionViews`).
  timestamp: 2026-11-12T10:20:00Z

- hypothesis (H2): a multi-coloured fixed top box makes Safari show the map
  instead of a flat colour.
  why_eliminated: WebKit samples a snapshot that excludes images (tiles) and
  treats `Multiple` as a fixed edge filled with the under-page colour; and
  the fixed box is below the inset anyway.
  timestamp: 2026-11-12T10:20:00Z

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-11-12T10:05:00Z
  checked: `.planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-OWNER-VALIDATION.md`, rounds 14-23
  found: round 15 (W170) first concluded "the full-bleed map under Safari's
  bars cannot be achieved from the page (limit of iOS 26 Safari)" and closed
  W152 as a platform limit — then immediately superseded: "the cause is the
  fixed map container background; fix tried in 61-104. W152 is not closed as
  a platform limit." Round 16, right after PR #318: "the top of the map now
  goes under the status bar; the bottom band remains (map ends about 8% above
  the screen bottom...). Plan B (non-fixed map extending under the bottom
  bar) is in plan 61-105." Round 23: "Location top band on iPhone (Safari
  tab, address bar at the bottom): still present after the fix that offsets
  the map by the top safe-area inset" (this is plan 61-110/111's attempt,
  also unsuccessful).
  implication: the "platform limit" conclusion was itself wrong and reversed
  within the same ledger — this is not a hard WebKit wall, it is a technique
  problem across multiple attempted fixes. The owner's memory of a real
  full-bleed top in a tab is independently corroborated by the ledger, not
  just recollection.

- timestamp: 2026-11-12T10:07:00Z
  checked: `git show 3573db7b:companion/static/style.css` (`.map-ready
  .place-map` rule) vs `.planning/.../61-105-SUMMARY.md` ("W171 - Location
  map as document content on phones")
  found: #318 had `.place-map { position: fixed; inset: 0; min-height:
  100lvh; background: var(--color-map-ground); }`. 61-105 replaced this with
  `.page-content { position: relative; height: 100lvh; overflow: clip }` +
  `.place-map { position: absolute; inset: 0 0 auto; height: 100lvh }` (map
  as ordinary document content, not fixed), explicitly to fix the bottom
  band; 61-105's own summary flags this as "not verifiable without an
  iPhone" at the time.
  implication: confirms the top/bottom trade-off mechanism — moving off
  `position: fixed` fixed the bottom (per lack of further owner complaints
  about the bottom after round 16) but silently cost the top full-bleed
  behaviour that only `fixed` content gets under Safari's translucent top
  chrome in a tab.

- timestamp: 2026-11-12T10:10:00Z
  checked: `grep -rn "visualViewport" .planning companion/static companion/*.py`
  found: zero matches anywhere in the repository.
  implication: a `visualViewport`-driven sizing approach for `.place-map` is
  genuinely untried here, not a previously-rejected dead end — worth
  investigating as a candidate fix.

- timestamp: 2026-11-12T10:11:00Z
  checked: live re-test in the iOS Simulator (`iPhone 18 Pro`), Safari tab,
  production `skypane.algernon.is`, Location page
  found: flat ground-coloured band at the top status-bar zone, no map
  content, no visible blur/veil gradient (the veil itself does look fixed —
  consistent with 61-112's fix for THAT symptom having worked).
  implication: current production state matches the symptom as described;
  this is confirmed live, not just inferred from planning docs.

- timestamp: 2026-11-12T10:20:00Z
  checked: WebKit main sources (fetched to scratchpad):
  `Source/WebCore/page/LocalFrameView.cpp` (`fixedContainerEdges`),
  `Source/WebCore/page/PageColorSampler.cpp` (`predominantColor`,
  `fixedContainerSampleRect`), `Source/WebCore/platform/FixedContainerEdges.cpp`,
  `Source/WebKit/UIProcess/API/Cocoa/WKWebView.mm`
  (`_updateFixedColorExtensionViews`, `_updateHiddenScrollPocketEdges`)
  found: (1) WebKit hit-tests the midpoint of the top side of the fixed
  layout rect, walks the hit node's ancestors and takes the first
  `position: fixed`/`sticky` box that is about viewport-wide as the top
  "fixed container"; a box <= 10px tall gives no CSS colour, so it samples a
  2px strip of a snapshot that EXCLUDES replaced content (img tiles) and
  paints only fixed/sticky layers. (2) `hasFixedEdge(top)` is true for a
  sampled Color AND for `Multiple`. (3) For every side with a fixed edge
  and a non-zero obscured inset, WKWebView inserts an opaque
  `WKColorExtensionView` ABOVE the web content in that inset, filled with
  the sampled colour, or `underPageBackgroundColor` when the sample is
  `Multiple`. Only with no fixed container at the top does it fall back to
  the soft scroll-edge effect over whatever the scroll view shows there.
  implication: any fixed box detected at the top edge yields a flat,
  opaque colour in the status-bar zone, never live content. 61-112's 4px
  ground `.place-edge` therefore CAUSES today's flat ground band (it was
  added precisely to be detected). The "visualViewport + fixed map" avenue
  cannot show real tiles there either: a fixed map is detected the same
  way (its CSS background colour, or under-page colour). H2 refined: real
  map content can only appear in that zone with NO detected fixed top
  container, as document content the scroll view itself shows under the
  inset.

- timestamp: 2026-11-12T10:22:00Z
  checked: `xcrun simctl list devices booted`
  found: `iPhone 18 Pro` (iOS 27.0 runtime) is booted.
  implication: direct experiments are possible: serve minimal HTML
  reproductions from the Mac, open them in the simulator's Safari tab with
  `simctl openurl`, capture with `simctl io screenshot`.

- timestamp: 2026-11-12T10:35:00Z
  checked: minimal repro page (scratchpad/repro/index.html, loud striped
  `<img>` tiles, viewport-fit=cover) in the iOS 27.0 simulator, Safari tab,
  variants: fixed318 (fixed map, min-height 100lvh), doc (61-105 document
  map), doc+edge (61-112 strip), doc+neg+noclip (map pulled 120px above the
  document top, nothing clipping it), doc scrolled by 40px.
  found: in a tab the status-bar zone is an obscured inset of ~63pt ABOVE
  the document (safe-area-inset-top = 0, innerHeight 714 of 874pt). At
  scrollY = 0 every variant shows a flat colour there: html background
  (fixed318), body/under-page ground (doc), ground (doc+edge). Content at
  negative document coordinates is not painted there either (neg+noclip).
  A fixed box at top:0 sits BELOW the status bar (the 4px strip rendered at
  63..67pt). Only when the document is scrolled down (scrollY=40) do real
  tiles appear under the clock, with Safari's soft scroll-edge blur over
  the topmost part (23pt that are still above the document).
  implication: real map under the status bar in a tab requires map content
  above the viewport top, i.e. a document scrolled down by at least the
  inset. No position:fixed technique (with or without visualViewport) can
  do it.

- timestamp: 2026-11-12T10:45:00Z
  checked: the real companion at HEAD and at `3573db7b` (#318, exported
  with git archive), each run locally behind a cookie-injecting proxy
  (scratchpad/tools/serve_location.py), opened in the same simulator Safari
  tab.
  found: HEAD = flat ground band at the top (identical to production
  00-current). #318 = flat html-surface band (#E9EEF5) at the top AND the
  flat band at the bottom (map ends at ~798pt) that round 16 reported.
  #318 never painted tiles under the status bar in this simulator.
  implication: the "good reference" was a flat pale band too (a different,
  bluish-grey colour that the owner read as the map in round 16); there is
  no build to restore. The trigger's premise (fixed content paints under
  the status bar, flow content does not) is refuted for iOS 27.

- timestamp: 2026-11-12T10:55:00Z
  checked: booted the iOS 26.5 `iPhone 17 Pro` simulator (owner's phone is
  iOS 26 per ledger W169) and opened the #318 build there.
  found: same as iOS 27: flat #E9EEF5 band at the top (rows 0-189px, 63pt)
  and the bottom band.
  implication: not an iOS 26 vs 27 difference; #318 never had tiles there.

- timestamp: 2026-11-12T11:00:00Z
  checked: repro variant `doc+lead` (document 100px taller, map extends
  into those 100px, header offset by 100px, page scrolled to 100 on load),
  on both simulators (iOS 27.0 and 26.5); plus `doc+lead+edge`.
  found: the whole status-bar zone shows real tiles under Safari's own soft
  scroll-edge effect, on both iOS versions; the bottom is unchanged from
  `doc` (map to ~817pt as today). With the 4px fixed strip added, the
  status-bar zone still shows tiles but the strip paints a ground line at
  62-66pt, right under the status bar.
  implication: technique confirmed: keep the map as document content, give
  the phone page a lead of map above the page and scroll past it, and hide
  `.place-edge` while doing so. Bottom geometry stays exactly 61-105's.

- timestamp: 2026-11-12T11:35:00Z
  checked: the fix on the real companion (local harness), iOS 27.0
  simulator, light and dark, then iOS 26.5; before/after pairs from the
  unfixed HEAD export on the same harness.
  found: before = flat (242,239,233) rows 0-190px; after = real tiles under
  the clock (Montrouge, Kremlin-Bicetre, Ivry) with Safari's own soft edge.
  Map bottom edge unchanged on both (row 2447/2622 on 27.0, 2584/2622 on
  26.5, before and after). Below the status bar only ~2.5% of pixels differ
  (the app bar fade's new soft top). A first version left a hard seam where
  the app bar fade started at 85%; the fade now ramps in from transparent in
  the lead case, seam gone on both versions.
  implication: falsification test passed: no flat band at the top, bottom
  identical to 61-105's.

- timestamp: 2026-11-12T11:45:00Z
  checked: Chromium tests (scratch venv from server/requirements-dev.txt):
  new tests in companion/test_browser_place_document_map.py, mutation runs,
  and 46 related files (place, location, detection, overhaul, foundations,
  stylesheet, page scripts, render baseline, companion_app_0*).
  found: new tests pass (8 cases); each of six mutations (no ramp, no lead
  call, strip kept, no typing guard, no settle listener, map not extended)
  makes them fail. Related set: 2307 passed, 24 failed, all 24 in
  test_browser_foundations `test_titles_are_on_the_type_scale_in_the_display_face`
  on unrelated pages (/account, /airlines, /display ...): the newly installed
  headless shell 1248 serialises `BlinkMacSystemFont` as "system-ui" in the
  computed font-family, an environment difference, not this change.
  Render baseline regenerated: only the style-place.css version hash moved.
  implication: no regression found in the Location suite.

- timestamp: 2026-11-12T12:10:00Z
  checked: owner checkpoint response (cycle 1 NOT confirmed) and the
  coordinator's simulator crop (scratchpad/top_crop.png), plus a fresh
  screenshot of the fixed worktree (scratchpad/c2/now.png, iOS 27.0).
  found: TOP: blurred, paler map over roughly the top 30-40pt, then sharp
  tiles, then the app bar fade; the owner reads the blur's end across the
  clock/wifi/battery row as a "weird bar" and wants the blur to reach further
  down with no edge. BOTTOM: with the toolbar EXPANDED the map stops at row
  2447/2622 (815pt) and the 59pt below it, around and under the floating
  address bar, is the flat ground colour. Cycle 1 measured the same row on
  HEAD and called the bottom "pixel-identical"; that only proved no
  regression, not that the bottom was right, and it was measured with the
  toolbar expanded only - the collapsed-toolbar case was never captured.
  implication: the bottom band is real and pre-existing (same row on HEAD);
  it was never fixed by 61-105 on these iOS versions.

- timestamp: 2026-11-12T12:15:00Z
  checked: probe page (scratchpad/probe2, 6px line pattern,
  viewport-fit=cover) in the iOS 27.0 iPhone 18 Pro simulator, Safari tab,
  scrolled 100px, toolbar expanded; row contrast measured with
  scratchpad/tools/rowcontrast.py.
  found: screen 402x874pt; innerHeight 714 = 100svh = 100dvh; 100lvh = 100vh
  = 754. Obscured insets: 63pt top, 97pt bottom expanded, so 57pt bottom with
  the toolbar collapsed (874-63-754). Under the status bar the line pattern is
  fully blurred 0-20pt, then the blur ramps out 20-48pt in visible steps
  (contrast 7, 16, 33, 72, 150, 212, 248), sharp from 48pt on.
  implication: Safari's own soft scroll-edge blur covers only the top 48pt of
  the 63pt zone and ends in steps right across the status icons; the page
  cannot move it, so it has to supply its own blur that continues past 48pt
  and fades out gradually. Bottom: 100lvh stops 57pt above the screen bottom
  even with the toolbar collapsed, so a map lead + 100lvh tall can never fill
  the bottom inset; it needs a tail below, like the lead above.

- timestamp: 2026-11-12T12:19:00Z
  checked: real touch drags in the iOS 27.0 simulator through Maestro 2.10
  (~/.maestro/bin/maestro, flow scratchpad/flows/swipe-*.yaml, XCUITest
  driver, no Mac pointer involved). On the tall probe page a 14% upward
  swipe collapses Safari's toolbar (innerHeight 714 -> 754, pill at the
  bottom). On the Location page the swipe was made on the sheet card (a drag
  on the map pans Leaflet and never scrolls the page). HEAD (export of
  a02acd1b on :18434) and the worktree fix (:8745), same flow.
  found: Safari does NOT collapse its toolbar on the Location page, on HEAD
  or with the fix: the document is only lvh (+lead) tall, so a drag just
  scrolls it to its end (~40pt past the rest position). There the app bar
  sits under the clock, and the bottom band grows from 59pt (row 2447) to
  98pt (row 2327) on BOTH builds; the cycle-1 settle-back only handled a
  scroll that ends inside the lead, not past it.
  implication: the bottom band the owner sees is pre-existing (identical on
  HEAD), present at rest (59pt, toolbar expanded) and worse after any drag on
  the sheet (98pt). It is not caused by the cycle-1 change. Fix direction:
  a tail of map below the page (>= 57pt, the collapsed-bar inset) and a
  settle-back from either side of the rest position.

- timestamp: 2026-11-12T12:24:00Z
  checked: worktree with (a) a --place-tail of 80px (page container and map
  lead + 100lvh + tail), (b) the settle-back from both sides, (c) the app
  bar's ::before rebuilt as one frosted layer from the top of the lead
  through the bar plus 48px (backdrop blur 8px, 45% canvas tint, mask full
  to the end of the lead then eased out). Server restarted (app.py caches
  static files per process). iOS 27.0 simulator, toolbar expanded, map
  panned so central Paris lies under the status bar.
  found: map reaches row 2621/2622 (it was 2447 on HEAD and cycle 1): no
  bottom band at rest. Top: on the line-pattern probe with the same CSS
  (scratchpad/probe2/lead.html) the pattern is fully blurred 0-62pt and its
  contrast then rises monotonically 7,16,25,34,50,71,92,112,133,154,175,196,
  213,222,230,240,247 from 63pt to 158pt, brightness monotonic 222 -> 205;
  without the layer the same page shows Safari's steps at 20-50pt. On the
  real page the 0-126pt profile has no step (scratchpad/tools/profile.py).
  implication: the seam is gone and the blur runs down through the app bar,
  as the owner asked; the bottom is filled at rest.

- timestamp: 2026-11-12T12:26:00Z
  checked: video of a Maestro drag on the sheet card (frames in
  scratchpad/c2/w4drag-frames) with (a)-(c) in place; then the line probe
  with and without `overflow: hidden` on <html>, same drag.
  found: the drag scrolls the page to its end (header under the clock, a
  flat band below the toolbar) for about a second until the settle-back
  returns it to the lead; Safari does not collapse its toolbar even with
  the 200px scroll range. With `overflow: hidden` on <html> the same drag
  does not move the page at all (scrollY stays 80.0 throughout), the
  programmatic scroll to the lead still works, the status bar still shows
  the lead and the toolbar zone the tail.
  implication: making the root unscrollable by touch in the Safari-tab case
  removes the transient band and the header jump; the settle-back stays for
  rotation and keyboard scrolls. To check: keyboard focus on the sheet's
  number field.

- timestamp: 2026-11-12T12:30:00Z
  checked: worktree with `overflow: hidden` on html.map-ready.place-lead,
  iOS 27.0 simulator: Maestro drag on the sheet (video), tap on the radius
  number field, tap on the keyboard's Done.
  found: the drag leaves every pixel in place (0.01% differ, map to row
  2621). The software keyboard opens and Safari still scrolls the field
  into view above it; after Done the page is back at rest (0.01% differ
  from before the tap).
  implication: the root lock does not break keyboard reveal; the
  settle-back on focusout restores the rest position.

- timestamp: 2026-11-12T12:32:00Z
  checked: collapsed-toolbar state. (1) Navigating to the Location page
  from a page whose toolbar was collapsed (probe GO link) - video frames.
  (2) Line probe with the exact lead/tail geometry
  (scratchpad/probe2/lead.html?pre=1): starts tall, a Maestro drag
  collapses the toolbar (innerHeight 754), then it switches to the lead
  layout and scrolls to the lead programmatically (toolbar stays
  collapsed); tail 80px vs tail 0.
  found: (1) Safari re-expands its toolbar on navigation, and the Location
  page itself never collapses it (HEAD: a drag only scrolls ~40px; fix: no
  scroll at all), so the collapsed state cannot be reached on that page in
  the simulator. (2) Collapsed, tail 80: pattern down to row 2621 under the
  pill; tail 0: content ends at row 2447 (58pt band).
  implication: the collapsed-toolbar bottom is covered by the tail
  (57pt needed, 80pt given) and the check is non-vacuous; verified on the
  probe geometry, not on the real Location page (unreachable state there).

- timestamp: 2026-11-12T12:35:00Z
  checked: dark mode, iOS 27.0, HEAD vs fix; the frosted layer's tint
  first as canvas 45% throughout, then as map ground 40% at the top to
  canvas 70% at the bar's middle with the mask solid to the bar's middle.
  found: Safari lightens the status bar zone in dark mode too (black clock;
  the tiles are light in both themes). With a dark tint all the way up the
  brightness went 171 -> 124 (45-60pt) -> 172: a dark valley just above the
  logo. With the light-to-canvas tint the dark-mode profile is monotonic
  218 -> 83 (behind the logo, 84pt) -> map below; light mode 218 -> 233 ->
  221, detail rising smoothly. HEAD dark: flat light band then the 85% dark
  fade starting hard at 63pt.
  implication: dark mode has a smooth light-to-dark gradient behind the
  white logo (the same intent as HEAD's dark fade, without HEAD's edge).

- timestamp: 2026-11-12T12:38:00Z
  checked: iOS 26.5 iPhone 17 Pro simulator (booted for this, shut down
  after): probe numbers, HEAD vs fix at rest and after a Maestro drag on
  the sheet, top profile.
  found: same viewport numbers as iOS 27 (714/754). HEAD: flat top band,
  map ends at row 2584 at rest and 2327 after the drag (header under the
  clock, page stays scrolled). Fix: frosted top with a smooth profile
  (brightness 235 -> 228 -> 233 -> 221, detail rising), map to row 2621 at
  rest and after the drag (page did not move).
  implication: same result on iOS 26.5 as on 27.0.

- timestamp: 2026-11-12T12:45:00Z
  checked: Chromium tests (scratch venv). companion/test_browser_place_document_map.py
  updated: lead test now asserts the tail (map bottom = window + 80, scroll
  range lead + tail, tail rows are map at the window's end, settles back
  from the tail); new test that a wheel over the sheet never moves the page
  (per-frame scrollY); the fade-edge test replaced by a frosted-layer test
  (layer starts at the document top, has a backdrop blur, ends >= 40px
  below the bar; on a test-only 6px line pattern the contrast seen through
  it is <= 0.2 at the window top, >= 0.95 below it, never decreasing and
  never jumping by more than 0.3 per 6px band, both themes). Mutations:
  no overflow hidden, no mask, no blur, layer not in the lead, no tail,
  one-sided settle, layer ending at the bar - each fails the new tests.
  Related set (40 files): 1973 passed, 24 failed - the same 24
  test_titles_are_on_the_type_scale_in_the_display_face cases on unrelated
  pages as cycle 1 (headless-shell font serialisation). Render baseline
  regenerated: only the style-place.css version hash moved (4 entries).
  ruff and check_comment_history pass.
  implication: no regression in the Location suite; the new behaviour is
  locked by non-vacuous tests.

- timestamp: 2026-11-12T14:25:00Z
  checked: cycle-2 build (fix server :8745, restarted) in the iOS 27.0
  iPhone 18 Pro simulator, status bar pinned (simctl status_bar override
  9:41), Safari relaunched before each shot (no "back to Settings" link),
  page theme set by a proxy route that sets the sp_ui_theme cookie; top
  330px crops in scratchpad/c3/before-{L-auto,D-auto,L-dark,D-light}-top.png
  (L/D = simulator appearance, then the page theme).
  found: light page theme (L-auto, D-light): uniform pale frost, black clock,
  graphite logo/wordmark, white glass pill. Dark page theme (D-auto and
  L-dark alike, so it is the page theme, not the system appearance): the
  zone is pale only above ~48pt (Safari's own blur over the lead), then a
  visible step into a grey band that darkens behind the logo and the pill,
  and Safari draws a WHITE clock. The cycle-2 note of a black clock in dark
  mode (12:35) does not hold on a fresh Safari launch.
  implication: matches the owner's real-iPhone report (light-to-dark
  gradient). The dark end is the frosted layer's canvas stop (#161A24 at
  70%); Safari samples the top of the window (the bar's middle, dark) and
  picks light status-bar content.

- timestamp: 2026-11-12T14:40:00Z
  checked: first fix (light canvas tint + light-palette tokens on .brand
  and .frame-menu__button in the lead case), same 4 captures
  (scratchpad/c3/after-*), brightness profile x 450-720 (profile.py).
  found: from 50pt down the dark-theme rows now equal the light baseline
  (225.8, 227.8, 229.5 ... 233.4 at 85pt, identical); clock black; logo,
  wordmark and pill render as in light mode. But 0-45pt (Safari's own soft
  pocket over the lead) stays darker in the dark page theme: 211 -> 195
  (system dark) / 192 (system light) against 221-228 with the light page
  theme, so a step of ~30 levels remains at 48pt where Safari's pocket ends.
  implication: a second dark source lives in Safari's pocket, not in the
  page's layers; the page theme drives it. Candidate: the under-page
  background (html background-color = --color-secondary, #1C222D in dark),
  which WKWebView uses as the scroll view's colour and the soft pocket's tint.

- timestamp: 2026-11-12T15:10:00Z
  checked: what drives the dim of Safari's pocket in the dark page theme,
  by elimination (proxy experiments: CSS injected per request, theme-color
  tags rewritten, a script injected; scratchpad/tools/serve_location.py).
  found: NOT the html background (light #E9EEF5 in the lead case: no
  change), NOT color-scheme (light dark / light on html: no change), NOT the
  theme-color tags (forced light: no change), NOT any token (the whole light
  palette forced on html with !important, search field and sheet rendered
  light: still 191). One earlier D-auto capture came out light (227) and
  could not be repeated. A screen sequence after load: the window is fully
  dark at ~4s (the opening splash, dark in the dark theme), then the dim
  stays constant (192 at 6, 9, 14, 25s). An injected script that, 8s after
  load, scrolls by 1px and back: pocket 192 -> 218.6. Same with a nudge of
  one DEVICE pixel (1/3 CSS px) for two frames: 191 -> 218.6, rest of the
  page unchanged (0.01% of pixels differ). Navigating Home -> Location by a
  tap on the tab bar (same session, no splash on Location): pocket 218.6
  and smooth into the bar (no step) with no nudge at all.
  implication: Safari keeps the look its soft pocket took at the page's
  last scroll. The page scrolls to the lead once, at script start, while the
  splash still covers the window (it plays once per browser session, on the
  first page opened); the page never scrolls again (overflow hidden), so in
  the dark theme the pocket stays dimmed (~13%) after the splash, leaving a
  step at 48pt even with a light frost. Fix direction: once the splash has
  gone, nudge the scroll by one device pixel for a frame.

- timestamp: 2026-11-12T15:40:00Z
  checked: nudge timing in place-map.js (MutationObserver on <html> for the
  removal of splash-on, then nudge), 4 fresh-session D-dark runs per variant;
  scratch logging of scrollY/classes per frame through the proxy.
  found: nudge in the same task as the splash removal: partial (top
  220-223, 40pt 211-216, still a step). 100ms later: 226.7/221.7. 300ms:
  227.3/222.7 on 4/4 runs, equal to the light page theme (D-light 227.3/
  222.6). WebKit floors the 1/3px scroll to 79, so the nudge is 1 CSS px;
  logged: lead scroll at 223ms (under the splash), splash off at 2135ms,
  nudge 79 -> 80 within ~25ms. Kept: 1 CSS px, two frames, 400ms after the
  splash has gone (SPLASH_SETTLE_MS).
  implication: deterministic in the simulator with margin over the 300ms
  threshold.

- timestamp: 2026-11-12T16:05:00Z
  checked: final matrix, iOS 27.0 simulator, status bar pinned, cycle 2
  (scratch copy of the tree with the cycle-3 edits removed, served on :8746;
  its style-place.css hash 4731c82a018b = cycle 2's) vs fix (:8745); flows:
  "open" = fresh Safari session straight onto /detection (splash plays),
  "nav" = fresh session on Home, then a Maestro tap on the Lieu tab (no
  splash); crops in scratchpad/c3/{c2,c3}-{open,nav}-*-top.png, grid
  scratchpad/c3/final-grid.png; masked compare (Dynamic Island area that
  Maestro sometimes lights) with scratchpad/tools/cmpmask.py.
  found: DARK, cycle 2 nav (the owner's case): 218 under the clock -> 145 at
  50pt -> 83 at 85pt behind the logo (the gradient he reported), white
  wordmark. Fix nav and open, auto and explicit dark, system dark or light:
  227 -> 222.6 -> 225.8 -> 233.4, black clock, graphite logo/wordmark, white
  pill: within 2 levels of the light page theme over the whole top 330px.
  LIGHT: nav flow pixel-identical to cycle 2 below and above (rows 0-2622,
  max diff 0 outside a 4px corner artefact); open flow identical from 50pt
  down (max 0), Safari's pocket over 0-48pt changes by at most 4 levels
  (220.8 -> 218.6) because it now re-samples the map after the splash; it
  equals cycle 2's own nav-flow pixels exactly (max diff 0). Map bottom row
  2621/2622 in every capture.
  implication: dark matches light; light unchanged except Safari's own
  re-sample of the pocket in the splash flow, which now equals what the
  light page always showed when reached from another page.

- timestamp: 2026-11-12T16:10:00Z
  checked: contrast of the app bar's ink against what is drawn behind it.
  (a) Chromium, real OSM tiles, same view, 402x754 at 3x
  (scratchpad/pw/contrast.py), worst over every pixel of each part's box with
  the part hidden. (b) the iOS screenshots, ink = darkest 2% of the box,
  background = lighter half.
  found: (a) fix, light and dark identical: wordmark #17191F worst 8.00:1
  (median 14.42), frame-button name 16.22:1 (16.65), logo 10.09:1 (14.70).
  Cycle 2 dark: wordmark #F1F3F6 worst 4.08:1, name 4.24:1 (both below AA
  4.5), logo 4.10:1. (b) fix: wordmark 14.10, name 16.65, logo 14.03 (worst);
  cycle 2 dark: 5.43, 4.47, 5.41.
  implication: the light ink on the light frost reads at AAA levels; cycle
  2's dark-mode ink was already marginal.

- timestamp: 2026-11-12T16:50:00Z
  checked: regression set (50 files: cycle 2's 40 plus splash, sky/contrast,
  contrast edges, theme switch, frame menu, brand logo, phone title, js
  minify, surfaces), -n 8; mutations; final CSS on the simulators.
  found: 27 failed / 2246 passed: the known 24 font-serialisation cases,
  test_no_selector_is_declared_in_two_rules_of_one_context (the frost's
  ::before was in two rules; merged, --color-canvas now sits in the one
  ::before rule), and two timeouts under load (full_bleed dark-360,
  overhaul_sweep dialog) which pass on a rerun: 667 passed for the place
  document map, stylesheet structure, render baseline, suite guards, full
  bleed, splash and overhaul sweep files. Render baseline regenerated (only
  style-place.css's version hash, 4 entries). 8 mutations (no palette, tint
  only, ink only, button left in the page theme, no nudge, nudge under the
  splash, nudge with no settle delay, bar ink drifting from the palette)
  each fail the new tests. Final CSS on iOS 27.0: dark captures identical to
  the pre-restructure ones (max diff 0); a Maestro drag on the sheet changes
  no pixel. iOS 26.5 iPhone 17 Pro (booted, then shut down): cycle 2 dark
  234.6 -> 167.6 (50pt) -> 85.9 (85pt); fix dark 234.6 -> 228.5 -> 233.1,
  within 2 levels of the light theme; light theme identical to cycle 2 over
  the whole screen (max diff 0). Map to row 2621 on both.
  implication: verified on both iOS versions; no regression found.

- timestamp: 2026-11-12T17:10:00Z
  checked: cycle 4. Chromium (402x754 at 3x, simulated Safari tab, real
  tiles) on the fix tree (:8745) and the cycle-2 tree (scratchpad/bc2,
  restarted on :8746): computed geometry, z-index, the search pill's
  background, and the pill's row brightness with the frost on and with
  `.site-header::before { display: none }` (scratchpad/c4/geo.py).
  found: both trees, both themes: bar 0-52, frost ::before -80 to 100
  (lead + bar + --space-2xl), search pill (.place-search__row) 64-118;
  header z-index 15 above .place-float z-index 3 (no stacking context in
  between); pill background opaque (#FFFFFF light, #151922 dark), no
  backdrop-filter, opacity 1. The frost's rule in the cycle-2 tree is the
  cycle-3 one less `--color-canvas: #F1F3F6` (same height, same mask).
  Pill rows, frost on vs off: cycle 3 dark: rows 0-34px differ, top row
  92.8 vs 26.6 (+66 levels), decaying to the fill by 34px; cycle 2 dark:
  max 8.5 levels (dark tint over a dark pill); light (both cycles): max 5.6
  levels (pale tint on white, softened top border).
  implication: H-reach confirmed and the cause is (a) only: the frost layer
  stacks above the search field and reaches 36px into it (mask ~0.46 at the
  pill's top edge); the pill's own background is solid, not (b). The overlap
  dates from cycle 2 (identical geometry); cycle 3's light tint over the
  dark pill made it visible. Fix direction: end the frost at the pill's top
  edge (bar bottom + the 12px gutter) with the mask still easing out to 0
  there; leave the solid part (to the bar's middle) as is.

- timestamp: 2026-11-12T17:25:00Z
  checked: Chromium variants (scratchpad/c4/variants.py): frost height
  lead + 100% + 12px (the stage's gutter) with the solid part ending at the
  bar's middle (lg, as now), 8px higher (md) or 16px higher (sm).
  found: all three end at 64 = the pill's top; pill pixels with and without
  the frost identical (max diff 0) in both themes. Line-pattern profile
  (frost/bare contrast per 6px band, gutter and mid-bar): monotonic, max
  step 0.27 (lg) / 0.22 (md) / 0.19 (sm), was 0.15 with the 48px reach.
  Worst-pixel ink contrast on real tiles: wordmark 7.60 / 6.51 / 5.82, logo
  8.54 / 7.33 / 6.61 (was 8.00, 9.94); frame name >= 15.6 in all.
  implication: the minimal change (lg, only the height) keeps the bar as
  it is above its middle and passes every criterion; the higher solid ends
  buy a slightly longer fade at the cost of ink contrast. Chose lg.

- timestamp: 2026-11-12T17:50:00Z
  checked: fix applied (style-place.css: height lead + 100% + --space-sm +
  --space-xs), :8745 restarted; cycle-3 reference tree scratchpad/bc3 (the
  worktree's static files with only the old height line) on :8747. iOS 27.0
  iPhone 18 Pro simulator, status bar pinned, fresh Safari launch per shot;
  "open" (straight onto /detection, splash plays) and "nav" (device page,
  Maestro tap on Lieu) in system dark and light (page theme auto); plus a
  fix capture with `.site-header::before { display: none }` injected
  (scratchpad/inject.css, removed after). scratchpad/c4/pill.py (rows inside
  the pill, x 260-330pt), pillbox.py (whole pill box), cmpmask.py, and the
  line probe scratchpad/probe2/reach.html (exact frost rule, dark pill 12px
  below the bar, ?below=48|12).
  found: DARK cycle 3 (open and nav identical): pill border row 120.6
  instead of 50.6, top 15% of the pill mean 87.7 against its fill 26.7 (max
  deviation 76), still 37.4 at its middle. DARK fix: border 50.6, top 15%
  26.6 (max deviation 0.3), middle 26.7. LIGHT cycle 3: top rows 244-250
  (max deviation 10.9); fix 250.8-253.3, which is the pill's own rendering:
  the whole pill box is pixel-identical (max diff 0) to the capture with no
  frost at all, in both themes (cycle 3 vs no frost: max 80 dark, 28 light).
  Cycle 3 vs fix: rows 0-261 (status bar zone to the bar's middle) max diff
  1, rows 545-2622 max diff 0; only the bar's lower half, the gap and the
  pill change. Map to row 2621/2622 in every capture. Light vs dark in the
  bar (rows 189-345): max 1 (was 5). Line probe in Safari, gap above the
  pill: contrast seen through the frost 0.01 (0-18pt) then 0.08, 0.18, 0.39,
  0.60, 0.81, 0.92, 1.00 at 60pt: monotonic, max step 0.21 per 6pt, no
  flat-to-sharp jump; with ?below=48 the probe reproduces the hazy top of
  the pill exactly (scratchpad/c4/probe-grid.png). Ink contrast: iOS
  screenshots (ink = darkest 2%, bg = lighter half) unchanged: wordmark
  14.52, name 16.64, logo 14.40 in both themes; Chromium worst pixel on
  real tiles 7.60 / 16.06 / 8.54 (cycle 3: 8.00 / 16.22 / 9.94).
  implication: the falsification test passed: the search field's top rows
  now equal its middle rows (and the field with no frost at all), and the
  frost still fades out with no step; nothing above the bar's middle and
  nothing below the field moved.

- timestamp: 2026-11-12T18:20:00Z
  checked: Chromium tests and checks. test_browser_place_document_map.py:
  the frost test now asserts bar bottom < field top - 1 <= frost bottom <=
  field top (was frost bottom >= bar bottom + 40); new test
  test_in_a_safari_tab_the_frost_never_falls_on_the_search_field (light/
  dark x 390/360): screenshot of the field between its rounded ends, with
  and without `.site-header::before { display: none }`, max channel
  difference <= 2 (the first version clipped the whole box and saw a 4-level
  antialiasing change at the field's curved left end, where the map shows
  through, unrelated to the frost; the clip now excludes the rounded ends).
  Mutations (scratchpad/c4/mutrun4.py): 48px reach fails 6 (both tests,
  every theme/size), 16px fails 4, 13px fails 2 (geometry), frost ending at
  the bar fails 2, no mask fails 2. Frost tests 3 runs, 8/8 each.
  Regression set (51 files: cycle 3's 50 plus test_browser_page_title_phone)
  -n 8: 2277 passed, 24 failed, all 24 the known
  test_titles_are_on_the_type_scale_in_the_display_face font-serialisation
  cases. ruff (companion/) and scripts/check_comment_history.py pass; node
  --check place-map.js passes (not changed this cycle). Render baseline
  regenerated: only the style-place.css version hash moved (ef44baa115ce ->
  4ece1be2a693, the served one).
  implication: the field's top is locked against the frost by a
  non-vacuous test; no regression found.

- timestamp: 2026-11-12T16:30:00Z
  checked: owner checkpoint response (cycle 4) and the final gates on the
  final tree before committing (real UTC clock; earlier entries in this
  file were stamped ahead of it).
  found: OWNER, real iPhone, Safari tab: "confirmed fixed". The search field
  is solid dark from its top edge in dark mode; the top full-bleed under the
  status bar (both themes), the bottom under Safari's collapsing toolbar, no
  page drag from the sheet, the dark-mode tint matching light mode and the
  Home Screen app veil fix all still hold. GATES: ruff on companion/ passes;
  scripts/check_comment_history.py check exits 0; node --check place-map.js
  passes. Render baseline regenerated with
  `test-support/companion_render_snapshot.py --write`: byte-identical to the
  file on disk (4 entries at style-place.css?v=4ece1be2a693, the served
  hash). test_browser_place_document_map.py + test_render_baseline.py, -n 8:
  first run 38 passed, 1 failed
  (test_the_phone_top_edge_is_the_bare_map_under_the_status_bar_with_one_fixed_ground_strip
  [chromium-390-light], a pre-existing test this change does not modify);
  that test alone 4/4 passed; then 3 x -n 8 (37/37), 1 serial run (37/37)
  and 5 x the original -n 8 combination (39/39): not reproduced in 9 runs.
  implication: the fix is confirmed on the target device; the single
  failure was a one-off on the first, cold parallel run.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: In an iPhone Safari tab both the status-bar zone (63pt) and the
toolbar zone (97pt expanded, 57pt collapsed) are obscured insets of the
scroll view outside the layout viewport; Safari shows the document that lies
above / below the window there, or a flat colour where there is none (a
fixed box never paints there). TOP: the page sat at scrollY=0 with the map
starting at the document top, so the zone was a flat band (cycle 1 fixed
this with the lead). The cycle-1 seam is Safari's own soft blur, which
covers only the top ~48pt of the zone and ramps out in steps across the
status icons over sharp map, followed by the app bar fade at 67pt. BOTTOM
(pre-existing, identical on HEAD): 100lvh is 754 = screen minus the status
bar minus the collapsed toolbar, so the map (100lvh tall) ends 57-59pt above
the screen bottom in every state, and a drag on the sheet scrolled the short
document to its end (98pt band, app bar under the clock) because Safari
never collapses its toolbar on this page. DARK MODE (cycle 3): the frosted
layer's tint ended on --color-canvas, #161A24 in the dark theme, so the
band went from pale (the map seen through Safari's pocket) to dark grey
behind the logo, with the dark theme's white ink on it (4.1:1 worst).
Also, Safari keeps its status-bar pocket's look from the page's last
scroll; the page scrolled past the lead under the opening splash (dark in
the dark theme) and never scrolled again, so after a fresh open a grey veil
stayed over the top 48pt. SEARCH FIELD (cycle 4, geometry from cycle 2):
the frost ::before ran 48px (--space-2xl) below the 52px app bar, to window
y 100, while the search field starts 12px below the bar (y 64); the header
(z-index 15) stacks above .place-float (z-index 3), so the frost's last
36px (mask ~0.46 fading to 0) were drawn over the field's top. Invisible in
cycle 2's dark theme (dark tint over a dark field), a pale haze once cycle 3
made the tint light; faint in light mode (pale tint on white, softened top
border).
fix: Phone layout, Safari tab only (navigator.standalone === false, class
`place-lead` set by place-map.js): (1) lead: unchanged from cycle 1 (80px of
map above the page, page opens scrolled past it). (2) tail: `--place-tail:
80px`; page container and map are lead + 100lvh + tail tall, so the toolbar
zone shows map in both toolbar states. (3) `overflow: hidden` on <html>: the
page cannot be scrolled by hand (a drag on the sheet no longer moves it);
place-map.js's settle-back now returns to the lead from either side (keyboard
reveal, rotation, programmatic scrolls). (4) the app bar's ::before is one
frosted layer from the top of the lead to 48px below the bar: backdrop blur
8px, tint map-ground 40% at the top to canvas 70% at the bar's middle, mask
solid to the bar's middle then eased out, so Safari's blur ends on already
blurred map and the blur fades out below the bar. Home Screen app and other
browsers: unchanged (strip, plain fade, no lead, no tail). (5, cycle 3) in
the lead case the frost's ::before, the brand and the frame button (not its
popover) carry the light palette's tokens (--color-canvas, --color-text,
--color-accent, --color-border, status colours, glass tokens and
--shadow-glass, plus color: var(--color-text) on them), so the band is
drawn as in the light theme in both themes. (6, cycle 3) place-map.js: if
the opening splash covers the page when it scrolls past the lead, 400ms
after the splash has gone (SPLASH_SETTLE_MS) the page scrolls to lead - 1
and back two frames later, so Safari re-samples its pocket from the map.
(7, cycle 4) the frost's height is lead + bar + 12px (--space-sm +
--space-xs, the stage's gutter) instead of + 48px: it ends at the search
field's top edge, its mask (solid to the bar's middle, then eased out by
quarters) now fading over the 40px from the bar's middle to the field.
verification (owner, real device): confirmed fixed by the owner on his real
iPhone in a Safari tab after cycle 4: the search field is solid dark from
its top edge in dark mode; the map runs under the status bar in both themes
and under Safari's collapsing bottom toolbar; a drag on the sheet does not
move the page; the dark-mode band matches light mode; the Home Screen app
still shows no veil. Final tree gates: ruff, comment-history check, node
--check, render baseline regeneration byte-identical, Location
document-map Chromium tests green (Evidence 16:30).
verification (cycle 4): iOS 27.0 simulator, status bar pinned, fresh
Safari launch per shot; cycle-3 tree (:8747, only the old height line)
vs fix (:8745); fresh open and tab-bar navigation; system dark and light.
Dark field: top 15% mean 87.7 vs fill 26.7 before, 26.6 (max dev 0.3)
after; the whole field box is pixel-identical (max 0) to a capture with no
frost at all, both themes (before: max 80 dark, 28 light). Rows 0-261
(status bar zone to the bar's middle) max diff 1 and rows 545-2622 max 0
against cycle 3; map to row 2621/2622 everywhere; open and nav flows give
the same pixels. Line probe in Safari: frost/bare contrast in the gap above
the field rises monotonically 0.01 -> 1.00 between 24 and 60pt, max step
0.21 per 6pt. Ink contrast: iOS screenshots unchanged (14.52 / 16.64 /
14.40); Chromium worst pixel on real tiles 7.60 / 16.06 / 8.54 (was 8.00 /
16.22 / 9.94), identical in both themes. Chromium: frost test now pins the
layer's end to the field's top edge; new test (2 themes x 390/360) asserts
the field's pixels between its rounded ends equal the field with no frost;
5 mutations (48px, 16px, 13px reach, ends at the bar, no mask) each fail.
verification (cycle 3): iOS 27.0 simulator, status bar pinned, cycle-2 tree
(:8746) vs fix (:8745), fresh-open and tab-bar-navigation flows, system
light/dark x page theme auto/light/dark: dark now within 2 levels of light
over the top 330px (was 218 -> 145 -> 83 behind the logo); light identical
to cycle 2 in the navigation flow (max diff 0) and from 50pt down in the
fresh-open flow, Safari's pocket over 0-48pt differing by <= 4 levels
(it now equals cycle 2's own navigation-flow pixels). Map to row 2621 in
every capture. Ink contrast on the frost, real tiles: wordmark 8.0:1 worst,
frame-button name 16.2:1, logo 10.1:1, identical in both themes (cycle 2
dark: 4.08, 4.24, 4.10). Chromium: 3 new tests (band equal in both themes;
ink contrast on the frost; nudge after the splash, not before, >= 300ms
after it); 7 mutations each fail them.
verification (cycle 2): iOS 27.0 and 26.5 simulators (real companion, light and dark,
Maestro touch drags): no step in the top profile (line probe: contrast rises
monotonically 63-158pt), map to the last screen row at rest and after a
drag on the sheet on both iOS versions (HEAD: 2447/2584 at rest, 2327 after
the drag); keyboard reveal on the radius field still works and the page
returns to rest after Done; collapsed-toolbar bottom covered on the probe
geometry (tail 0 = 58pt band, tail 80 = none). Chromium: updated/new tests
pass and 7 mutations each fail them; 40-file related set green apart from
the known 24 font-serialisation failures. NOT verified: a real iPhone; the
collapsed toolbar on the real Location page (Safari never collapses it
there in the simulator); the Home Screen app on a device.
files_changed:
  - companion/static/place-map.js
  - companion/static/style-place.css
  - companion/test_browser_place_document_map.py
  - companion/testdata/render_baseline.json
  - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-UI-SPEC.md
  - .planning/debug/knowledge-base.md
commit: ed46688c (fix, the five code/spec files); this session file and the
knowledge base entry are committed separately as docs.
