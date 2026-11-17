---
status: resolved
trigger: "Follow-up to the just-merged PR #369 (companion, commit 390afaa7 on main — a two-part fix series: location-top-status-bar-band and map-fills-header-footer, both archived under .planning/debug/resolved/). That series gave the Location (\"Lieu\") page's map a real-map lead/tail under the status bar and bottom inset, in an iPhone Safari tab AND the Home Screen app alike (gated on `navigator.standalone` being defined at all), and removed a custom blur layer so only iOS's own native status-bar blur applies there. The owner (Florian) deployed, confirmed the Location page itself is good (\"j'ai déployé et vérifié : c'est tout bon!\"), then immediately flagged a NEW, separate symptom on a DIFFERENT page: in the Home Screen app (standalone), on the Accueil (Home) page, the \"SkyPane\" wordmark/logo in the app bar shows a soft blur/ghosting artifact (a screenshot was attached — the wordmark text looks smeared/double-exposed, not crisp), and he says this happens on every page of the app (\"tous les onglets\"), not just Location. He explicitly confirmed this is Home-Screen-app only (not reproduced by him in a Safari tab) and that it affects every page (Accueil, Vols, Lieu, Style), not only after visiting Lieu first — though note: his confirmation of \"every page\" is based on his general experience using the app, not necessarily a verified fresh-launch-straight-to-Accueil-without-ever-touching-Lieu test in this exact session; the debugger should still verify that distinction explicitly rather than assume it."
created: 2026-11-13T07:52:08Z
updated: 2026-11-13T11:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

RESOLVED 2026-11-13: the owner confirmed the fix on his real iPhone (iOS
27.x, Home Screen app): "c'est tout bon, j'ai vérifié". Session archived to
.planning/debug/resolved/, knowledge-base entry appended. Not requested by
the owner, and out of scope for this session: the top toasts and the
Airlines sticky filter bar that also sit in the frost, and landscape
behaviour. The history below is kept as it was at the checkpoint.

known_pattern_candidate: "map-fills-header-footer — its Evidence
2026-11-12T22:20 measured iOS 27's OWN blur in a Home Screen web app as
fully blurred 0-68pt and fading out 68-104pt in screen coordinates, i.e.
over the top of the logo, wordmark and frame button (app bar 62-114pt),
while a Safari tab's blur stops at ~32pt. Hypothesis (c): that iOS
scroll-edge blur covers the app bar on EVERY page of the web app, since
the web app's window starts below the status bar (safe-area-inset-top 0,
status bar an obscured inset) and the app bar sits at the window top."
bug_class: Bohrbug (deterministic: reproduced on every fresh launch,
pixel-identical across builds)
status_of_hypotheses: (a) eliminated, (b) eliminated, (c) CONFIRMED - see
Resolution.root_cause.
owner_decision (2026-11-13, checkpoint answered): option B, 24px, Home
Screen web app only (navigator.standalone === true), Lieu INCLUDED (its
app bar and search field move down by the same 24px, deliberately). Owner's
iPhone runs iOS 27.x (matches the 27.0 simulator measurements).

reasoning_checkpoint:
  hypothesis: "iOS 27 frosts the top 36pt of a Home Screen web app's
    window (screen 62->98pt) over the web view; the app bar sits at the
    window top on every page, so its glyphs (74-100pt) are blurred."
  confirming_evidence:
    - "stripe probe: amplitude <=2/255 to 60pt, 107 at 80pt, 255 from 98pt,
      screen-fixed (Evidence 08:40 (1))"
    - "app bar padded +42px by injected CSS: wordmark/pill sharpness equal
      to a Safari tab row for row (Evidence 08:40 (2))"
    - "fresh launch to Accueil, Lieu never opened, pre-#369 build
      pixel-identical (Evidence 08:15)"
  falsification_test: "with the class + 24px drop live in the web app, the
    wordmark/pill glyph rows still measure well below the tab's sharpness
    (sharp.py) -> the frost is not what blurs them, or 24px is not enough"
  fix_rationale: "the frost is drawn by iOS over the web view and cannot be
    removed from the page (meta black-translucent, colour strip, Reduce
    Transparency is a user setting); moving the app bar below the frost is
    the only page-side lever, gated to the one client that has the frost"
  blind_spots: "iOS 27.2 on the owner's device may frost a slightly
    different depth than the 27.0 simulator; toasts (top 8px) and the
    Airlines sticky controls also sit in the frost but are out of the
    owner's chosen scope; an iPad Home Screen web app (wide layout) is not
    changed (rule scoped to the phone layout)"
  candidate_causes:
    - "environment: iOS 27 Home Screen web app frosted status-bar zone
      (WebKit bug 301994) - CONFIRMED"
    - "code: a leaky selector or blur from #369 - ELIMINATED (Evidence 08:00)"
    - "environment/state: session carryover after Lieu - ELIMINATED (08:15)"
  and_gate: "yes, two conditions: iOS's frost reaching below the status bar
    (platform) AND the app bar placed at the window top (our layout); the
    fix acts on the second, the only one under our control"

fix_plan: `--app-bar-drop` custom property (0px; 24px on html.web-app under
the phone media query) added to the `.site-header` top padding/min-height
and to `--place-top` (Location stage + loading placeholder), so the search
field, chips, offer and details card follow the app bar on Lieu. Class set
by splash-boot.js when navigator.standalone === true.
next_action (now): CHECKPOINT (human-verify) returned. Fix committed on
branch claude/home-screen-app-wordmark-blur-0439ca as c387ea2e (not pushed,
no PR). The owner must ship it and check on his iPhone (iOS 27.x) in the
Home Screen app: Accueil, Vols, Lieu, Style, light and dark - wordmark,
logo and frame name sharp, bar and (on Lieu) the search field 24px lower;
a Safari tab unchanged. On "confirmed fixed": archive to resolved/, append
the knowledge-base entry, commit the docs. If still blurred on 27.x: the
device's frost is deeper than the 27.0 simulator's - revisit 36px
(option A).

hypothesis (original framing): Two candidate explanations, not yet
distinguished — the debugger must gather evidence before picking one:
(a) A genuinely global CSS/markup regression: something in the just-
merged fix (companion/static/place-map.js, companion/static/style-
place.css) unintentionally affects the shared `.site-header`/`.brand`
markup that every page uses (not just the Location page's `.place-stage`-
scoped rules), e.g. a selector that is broader than intended, or a shared
stylesheet rule whose specificity/cascade changed.
(b) An iOS WebKit session-level carryover, not a per-page CSS bug: the
prior investigation (.planning/debug/resolved/location-top-status-bar-
band.md) already established that iOS Safari's rendering of the obscured
status-bar zone in a Safari tab depends on scroll-position/content state
at a given moment, not fixed CSS alone. It is plausible that something
similar happens in standalone/Home-Screen-app mode at the WHOLE-WINDOW
level: once the Location page's lead mechanism causes WebKit to render a
blurred status-bar chrome for that window/session, WebKit may continue
rendering with that same blurred style on subsequent page navigations
within the same standalone app window/session, even on pages whose own
markup has nothing unusual at the top — i.e. the blur the owner is
pointing at might not be caused by the Home page's own CSS at all, but be
a carryover rendering artifact from the webview's own chrome state after
visiting Location earlier in the same session. This would explain "every
page" without requiring a broad/leaky CSS selector.
These are not mutually exclusive — gather evidence before committing to
either.
test: not yet run — gathering evidence first.
expecting: n/a yet.
next_action: gather initial evidence — (1) read companion/static/style-
place.css's current selectors (particularly the light-palette ink block
and any `.map-ready`/`.site-header` rule) to check whether any of them
could match outside the Location page's `.place-stage` context; (2)
reproduce in the iOS Simulator, standalone/Home-Screen-app mode: force-
quit and relaunch landing DIRECTLY on Accueil without ever visiting Lieu
in that session, to test whether the blur appears even without visiting
Location first (distinguishes hypothesis (a) from (b)); (3) if it only
appears after visiting Lieu, that confirms (b) — a WebKit session/window-
level carryover, not a CSS bug, and the "fix" (if any exists at all) would
need to work at that level, e.g. forcing a reload or a different technique
when leaving the Location page; (4) if it appears on first launch
regardless, inspect the actual computed styles/DOM around the blurred
"SkyPane" wordmark on the Accueil page for anything unexpected (backdrop-
filter, blur filter, a stray selector match).

## Symptoms
<!-- Written during gathering, then immutable -->

expected: In the Home Screen app, on every page (Accueil, Vols, Lieu,
Style, etc.), the "SkyPane" wordmark and logo in the app bar render crisp
and sharp, as they did before PR #369, with no blur or ghosting — only
the Location page's own map should show the deliberate, now-accepted
native-iOS-blur-then-sharp-cut look under the status bar.

actual: On the Home Screen app (standalone), the owner reports the
"SkyPane" wordmark/logo shows a soft blur/double-exposure artifact in the
app bar, and says this happens on every page he's used recently, not only
Location — confirmed live on his real iPhone, 2026-11-13, post-deploy of
PR #369 (commit 390afaa7). A screenshot of the Accueil (Home) page shows
the wordmark with a visible soft/smeared appearance, not a hard edge.

errors: None reported — purely visual.

reproduction: Open the Home Screen app (not a Safari tab — confirmed by
the owner the issue does NOT appear in a Safari tab), navigate around the
app (owner describes it on "tous les onglets" — the bottom nav tabs:
Accueil, Vols, Lieu, Style, Plus). Not yet confirmed whether a single
fresh launch landing directly on Accueil (without visiting Lieu first in
that session) reproduces it — this needs to be tested explicitly, see
next_action above.

started: First reported by the owner immediately after deploying PR #369
(companion, commit 390afaa7 on main, merged 2026-11-13T07:34:33Z) — the
two just-resolved debug sessions (location-top-status-bar-band,
map-fills-header-footer) are the only recent changes to this area of the
app. Not yet confirmed whether this exact symptom pre-existed PR #369 (the
owner did not say "this is new since the deploy" explicitly — only that he
deployed, verified Location was good, and then flagged this separately;
confirm with him if genuinely uncertain, but default working assumption is
that it is connected to PR #369 given the timing and the visual similarity
to the blur mechanism that series worked on).

## Additional scope (from conversation, not a classic symptom field)

**Confirmed by the owner, do not re-ask:**
- Home Screen app only — not reproduced in a Safari tab.
- Affects every page he's checked (Accueil, Vols, Lieu, Style), not only
  after visiting Lieu — though see the hedge above: this is the owner's
  general impression, not a controlled fresh-launch test; the debugger
  should verify the fresh-launch-direct-to-Accueil case explicitly rather
  than treat hypothesis (b) (session carryover from Lieu) as eliminated.

**Constraint:** whatever the fix, do not regress anything already
confirmed working in the two resolved sessions this builds on (Location
page's own top/bottom/drag/dark-mode/search-field behaviour in both a
Safari tab and the Home Screen app).

**Out of scope:** re-investigating the Location page's own, already-
accepted native-blur-then-sharp-cut look there — that is settled and
should not change.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

- hypothesis: (a) a selector or script changed by PR #369 leaks onto the
  shared app bar of other pages
  evidence: Accueil does not link style-place.css or place-map.js at all;
  its asset list and content hashes are identical at 9c0bffba and
  390afaa7 (Evidence 08:00).
  timestamp: 2026-11-13T08:00:00Z

- hypothesis: (b) a WebKit session carryover after visiting Lieu
  evidence: a fresh launch straight onto Accueil from a web clip of
  Accueil, Lieu never opened, shows the same blur; the pre-#369 build is
  pixel-identical (Evidence 08:15).
  timestamp: 2026-11-13T08:15:00Z

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-11-13T07:50:00Z
  checked: owner's screenshot of the Accueil (Home) page, Home Screen app,
  iPhone, 2026-11-13 08:48 local time, post-deploy of PR #369
  found: the "SkyPane" wordmark and logo icon in the top app bar show a
  soft, blurred/ghosted appearance — not a hard-edged status-bar artifact
  like the one investigated in the resolved sessions, but a blur localized
  around the brand text itself, which sits well below the physical status-
  bar icon row (clock/battery), at the normal app-bar vertical position
  every page shares.
  implication: this is a distinct symptom from the Location-page status-
  bar band/seam work — the blur is around shared header markup used by
  every page, not Location-specific map/frost CSS, which is the puzzle
  this session needs to resolve (how could Location-scoped CSS, or
  something it triggers at the WebKit level, affect a shared component on
  unrelated pages).

- timestamp: 2026-11-13T07:58:00Z
  checked: owner's follow-up on the same screenshot
  found: the "Frame of The City" pill (the device-name pill next to the
  brand, on the right side of the app bar) is ALSO visibly blurred, not
  only the "SkyPane" wordmark/logo on the left. Owner's exact words: "On
  voit bien que le 'frame of the city' est flou aussi" (you can clearly
  see that 'frame of the city' is blurry too).
  implication: the blur affects the WHOLE app-bar row (both ends of it,
  not just the brand/logo on the left), strengthening the hypothesis that
  this is a status-bar/chrome-level rendering effect bleeding down over
  the entire app bar area — not a narrow CSS selector that happens to
  match only the brand markup. Points more toward hypothesis (b) (a
  WebKit-level rendering carryover) or a broad shared rule/region (e.g. a
  backdrop-filter or blur applied to the whole `.site-header` or a
  container around it) rather than something specific to the `.brand`
  element alone.

- timestamp: 2026-11-13T08:00:00Z
  checked: companion/page_styles.py (which area sheets a route links) and
  the Home page HTML served by HEAD 390afaa7 (:8745) and by a 9c0bffba
  export (pre-#369, :8750), diffing every <link> and <script src>
  found: "/" links only style.css + style-home.css; style-place.css and
  place-map.js are linked on /detection only. The Home page's full asset
  list, content hashes included (style.css?v=2a0ca9328884,
  style-home.css?v=e2f1799724af, every script), is IDENTICAL before and
  after #369.
  implication: no rule or script #369 changed is present on Accueil, so a
  leaky selector from #369 cannot affect it (hypothesis (a) eliminated for
  Accueil). What remains: (b) a carryover from visiting Lieu in the same
  web app session, or (c) iOS's own blur in a web app, which would exist
  regardless of #369.

- timestamp: 2026-11-13T08:15:00Z
  checked: iOS 27.0 iPhone 18 Pro simulator, light appearance. Two NEW
  Home Screen web clips installed from Accueil itself (Safari -> Partager
  -> Sur l'ecran d'accueil): HHEAD from :8745 (HEAD 390afaa7) and H368
  from :8750 (9c0bffba, pre-#369). Each force-quit, then fresh-launched
  from SpringBoard straight onto Accueil; Lieu never opened in that
  session. Probe (scratchpad/inject.js) logged at 3s/8s; screenshots
  c6/hhead-fresh-L.png, c6/h368-fresh-L.png, plus a Safari tab of the
  same HEAD Accueil (c6/tab-home-head.png). Sharpness = max horizontal
  gradient per row (scratchpad/tools/sharp.py) over the wordmark (x
  155-440 px) and the pill text (x 830-1115 px).
  found: REPRODUCED on a fresh launch straight to Accueil: the top of the
  logo, the "SkyPane" wordmark and the "Live frame" pill are blurred,
  sharpening downwards. Probe: standalone true, innerHeight 812 of 874,
  safe-area top 0, scrollY 0, header 0-52 in the window (screen 62-114pt),
  header background transparent, backdrop-filter/filter none on the
  header, brand and both pseudo elements. Sharpness, web app vs tab at the
  same screen rows: wordmark 80pt 36 vs 183, 84pt 58 vs 206, 90pt 77 vs
  197, 94pt 111 vs 206, equal only from 98pt (173 vs 173); pill 84pt 50
  vs 206, 88pt 76 vs 211, 92pt 92 vs 211. HHEAD and H368 screenshots are
  pixel-identical over the top 600 rows (max diff 0).
  implication: (b) is eliminated: no Lieu visit is needed. The blur
  predates #369 (identical pixels on the pre-#369 build). The page draws
  no blur (no filter anywhere on the bar) and the same markup is sharp in
  a Safari tab, so the blur is iOS 27's own top edge effect in a web app,
  which reaches ~36pt below the status bar into the window (62 -> ~98pt)
  and so over the app bar every page puts at the window top. Matches the
  map-fills-header-footer measurement (fully blurred to 68pt, fading
  68-104pt).

- timestamp: 2026-11-13T08:25:00Z
  checked: WebKit bug 301994 "REGRESSION (iOS 26.1): Status bar remains
  visible in fullscreen mode in Home Screen Web apps"
  (https://bugs.webkit.org/show_bug.cgi?id=301994), status REOPENED,
  rdar://184081721.
  found: reporters measure exactly our numbers in a Home Screen web app on
  iOS 26.5.2 (screen 874, innerHeight 812, safe-area top 0, a 62px zone
  "drawn by the system above the web layer and unreachable by any DOM
  element"); Apple (Marcos Caceres) confirmed it on the iOS 27 beta and
  reopened it on 2026-08-04. Comment 17 (2026-11-10, iOS 27.2): "A
  translucent, frosted system bar overlays the upper part of the
  application, obscuring an interactive CLOSE button"; Reduce Transparency
  removes the frost. Briefly fixed in 26.2, regressed again. Not fixed as
  of 2026-11-10.
  implication: the blur is a known, open iOS/WebKit platform behaviour
  in Home Screen web apps, not something the page draws. Any fix on our
  side is a workaround (move the app bar out of the frost), not a repair.

- timestamp: 2026-11-13T08:40:00Z
  checked: diagnostic and candidate-workaround launches of HHEAD (fresh
  launch onto Accueil each time, iOS 27.0 simulator), CSS injected by the
  proxy (scratchpad/inject.css), plus one new clip HBT installed from
  Accueil with apple-mobile-web-app-capable + status-bar-style
  black-translucent injected into <head> (scratchpad/inject.head).
  found: (1) Frost profile, measured with a fixed full-screen 2px stripe
  pattern (c6/hhead-stripes-L.png): stripe amplitude <= 2 of 255 from 0
  to 60pt (status bar zone fully frosted), 5 at 62pt, 54 at 74pt, 107 at
  80pt, 206 at 90pt, 253 at 96pt, 255 from 98pt. The frost reaches 36pt
  into the window (62 -> 98pt), screen-fixed. (2) App bar pushed down by
  42px (padding injected): wordmark and pill sharpness equal to the tab
  row for row (184/207/207... vs 183/207/206...): the blur moves with the
  screen, not with the bar. (3) A 4px fixed solid strip at the window top
  (WebKit colour extension): sharpness identical to no strip, frost
  unchanged. (4) black-translucent clip: innerHeight 874, safe-area top
  62px (the page DOES reach under the status bar on 27.0 with the meta),
  status bar ink stays dark, but the frost is identical (max diff 2 over
  the top 600 rows): the meta does not remove it. (5) Dark theme: same
  frost depth (wordmark 38/48/60 at 80/82/84pt vs 36/43/58 light).
  (6) matchMedia("(display-mode: standalone)") is FALSE in the web app
  (no manifest; display-mode: browser matches); navigator.standalone is
  true; calc(100lvh - 100svh) = 62px there. (7) Prototypes: +36px top
  padding on the app bar in the web app = wordmark, pill text AND pill top
  edge as sharp as the tab (edge step 19 vs 20); +24px = every glyph as
  sharp as the tab, only the pill's top edge softened (step 8 vs 20).
  Grid: c6/grid-proto36.png (today L, +36 L, today D, +36 D).
  implication: the only page-side lever is to start the app bar below
  the frost in a Home Screen web app (24-36px more top space on every
  page there). Gate must be navigator.standalone (a class set by the head
  script), not a display-mode media query. The frost depth is iOS-version
  dependent (26.5 simulator: barely reaches the window), so the cost and
  the gain depend on the owner's iOS version; this is a design trade-off
  the owner has to choose.

- timestamp: 2026-11-13T09:20:00Z
  checked: Chromium, new companion/test_browser_web_app_bar.py (navigator
  .standalone true/false/undefined x 390/360/1280, routes /, /flights,
  /detection, /display) and a mutation run against it
  found: web app only: html.web-app set, bar 0-76 (52 elsewhere), logo top
  36 / button top 28 (12 / 4 elsewhere), first painted glyph row 36 (>=
  FROST); Lieu search row 88-142 and chips 150 (64 / 126 elsewhere), gap
  under the bar 12 in every client; loading placeholder search 88 (64);
  wide screen unchanged in every client. Mutants: no class -> 4 fail;
  drop 0 -> 3 fail; --place-top without the drop -> 3 fail; class on any
  defined navigator.standalone (Safari tab too) -> 4 fail; drop 12px -> 3
  fail; drop not phone-scoped -> survives, equivalent (every wide-screen
  consumer is overridden: bar padding/min-height 0, --place-top 0px,
  loading search at --space-md).
  implication: the test pins the gate, the amount, the Lieu follow-through
  and the frost clearance.

- timestamp: 2026-11-13T09:35:00Z
  checked: iOS 27.0 iPhone 18 Pro simulator, proxy :8745 restarted on the
  fixed worktree, fresh launches: HHEAD (Accueil) light + dark, BFIX
  (Lieu) light + dark, Safari tab Accueil light + dark, Safari tab Lieu
  light (c6/fix-home-L, fix-home-D, fix-lieu-L, fix-lieu-D, tab-home-fix-L,
  tab-home-fix-D, tab-lieu-fix-L); sharpness with scratchpad/tools/sharp2.py
  (web app rows shifted 72px = 24pt against the tab's rows)
  found: probe in the web app: standalone true, cls "web-app js
  [map-ready place-lead]", header 0-76, Lieu scrollY 80. Accueil light,
  web app vs tab, per glyph row: wordmark 184/183, 207/207, 207/206,
  195/195, 198/197, 207/207, 206/206, 173/173, 119/118; pill 72/72,
  206/206, 211/211 x4. Dark: wordmark 193/193, 215/214, 214/215, 204/204,
  ... 123/123; pill 64/64, 183/184, 187/188 x4. Pill top edge step 10 vs 21
  light (the accepted softening). Fix screenshot pixel-identical (max diff
  0) to the approved +24px prototype (c6/proto24-L). Lieu web app light and
  dark: wordmark and pill crisp, search field and chips 24pt lower, map
  still under the status bar. Safari tab: standalone false, no class,
  header 0-52 on Accueil and Lieu (lead scroll 80 kept); light tab
  Accueil pixel-identical to the pre-fix tab capture below the clock.
  implication: falsification test passed: the glyphs are as sharp as a
  tab in the web app; the Safari tab and the Location page's resolved
  behaviour are unchanged.

- timestamp: 2026-11-13T10:00:00Z
  checked: full suite (scripts/run-all-tests.sh, PYTHON=main checkout's
  server/.venv, SKYPANE_REQUIRE_BROWSER=1) on the fix, then the companion
  failures re-run in isolation on the fix and on a clean `git archive
  HEAD` export (scratchpad/base-head)
  found: 154 failed / 14502 passed. Deploy (GNU `mv -T` on macOS), server
  golden/mask/pairing renders (macOS font drift) and 29 companion cases
  (test_browser_foundations display face x24, display_looks x2, ux_03,
  app_server_fixture x2) fail IDENTICALLY on clean HEAD: environment, not
  this change. home_state_card[1024] and fleet_users_fixes[fr-360] pass in
  isolation on the fix (load flakes in the parallel run). The one real
  consequence, test_render_baseline, failed on the changed asset hashes;
  baseline regenerated (test-support/companion_render_snapshot.py --write):
  the diff is exactly the hashes of style.css, style-place.css and
  splash-boot.js, nothing else; it passes now.
  implication: no regression from the change.

- timestamp: 2026-11-13T10:20:00Z
  checked: session manager's independent re-check of c387ea2e:
  test_browser_web_app_bar.py + test_browser_place_document_map.py +
  test_suite_guards.py (main checkout's server/.venv,
  SKYPANE_REQUIRE_BROWSER=1), at -n 4 x2, at -n auto x4, and the same
  place-map + guards files at -n auto x3 on a `git archive 390afaa7`
  export; plus check_comment_history.py and ruff on the changed tests
  found: -n 4: 58/58 pass both runs. -n auto: 0-2 failures per run,
  different place-map tests each time (scroll/splash/floating-parts
  cases), each passing when re-run alone. The unfixed base 390afaa7 shows
  the same pattern at -n auto (1-3 failures per run, also varying:
  wide-screen-no-lead, starts-scrolled-past-lead, map-spans-window).
  Comment-history guard and ruff pass.
  implication: the place-map browser tests are timing-flaky under full
  parallel load on this Mac, and they already were before this fix, so
  the fix did not cause it. Worth watching in CI, but no action for this
  session.

- timestamp: 2026-11-13T10:50:00Z
  checked: owner's human-verify answer, real iPhone, iOS 27.x, Home Screen
  app, with c387ea2e deployed
  found: "confirmed fixed" ("c'est tout bon, j'ai vérifié"). He did not
  ask for the two optional checks offered at the checkpoint (top toasts
  and the Airlines sticky filter bar in the frost, landscape).
  implication: the fix holds on the real device's iOS 27.x frost depth,
  not only on the 27.0 simulator (the main blind spot at the checkpoint).
  Toasts, sticky filter bar and landscape are recorded as out of scope,
  not as verified.

- timestamp: 2026-11-13T10:55:00Z
  checked: recurrence guard before archiving:
  companion/test_browser_web_app_bar.py at c387ea2e (main checkout's
  server/.venv, SKYPANE_REQUIRE_BROWSER=1, -n 4)
  found: 12 passed (6 phone cases: 3 clients x 390/360, each looping over
  /, /flights, /detection, /display; 3 Location loading-state cases; 3
  wide-screen cases). The earlier "15 cases" count was wrong.
  implication: the guard exists and passes; the KB entry records it.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: iOS draws its own frosted status-bar zone over a Home Screen
web app and, on iOS 27, fades it out 36pt BELOW the status bar (screen
62 -> 98pt on an iPhone 18 Pro), on top of the web view. Every page puts
its app bar at the top of the window (screen 62-114pt; logo, wordmark and
frame pill glyphs at 74-100pt), so the top of the logo, the wordmark and
the pill are blurred on every page, in both themes, from a fresh launch,
whether or not Lieu was visited. The page draws no blur (no filter or
backdrop-filter on the bar; the same markup is sharp in a Safari tab).
Not caused by PR #369: Accueil does not load anything #369 changed and
the pre-#369 build is pixel-identical. Known open platform issue: WebKit
bug 301994 (REOPENED, rdar://184081721), comment 17 on iOS 27.2 describes
the same frosted system bar over the top of a web app's UI.
fix: owner's option B (24px, Lieu included). The head script
(companion/static/splash-boot.js) puts `web-app` on <html> before the
first paint when navigator.standalone === true (a Home Screen web app
only). style.css adds `--app-bar-drop` (0px; 24px on html.web-app under
max-width 959.98px) to the phone app bar's top padding and min-height;
style-place.css adds it to `--place-top` for the Location stage and its
loading placeholder, so the search field, chips, offer and details card
move down with the bar and keep their 12px gap below it. A Safari tab,
other browsers and the wide layout are unchanged.
oracle_type: specified (layout boxes and the frost depth measured on iOS
27.0) + derived (first painted glyph row >= the frost depth)
verification:
  - signal: human verification - owner confirmed on his real iPhone (iOS
    27.x, Home Screen app) on 2026-11-13: "c'est tout bon, j'ai vérifié".
    Not checked, and out of scope by the owner's choice: top toasts, the
    Airlines sticky filter bar, landscape
  - signal: regression test - companion/test_browser_web_app_bar.py (12
    cases: 3 clients x 390/360, each looping over 4 routes; Lieu loading
    state x 3 clients; wide screen x 3 clients) passes, re-run before
    archiving; Location layout test updated for the web app's 24px
    (test_browser_place_document_map.py); 117/117 Location + new tests pass
  - signal: mutation - 5 of 6 mutants killed (no class, drop 0, place-top
    without drop, class in a Safari tab, 12px drop); the survivor (drop not
    phone-scoped) is equivalent (no wide-screen consumer)
  - signal: real-platform reproduction - iOS 27.0 simulator fresh launches:
    web app glyph-row sharpness equal to the Safari tab (light and dark,
    Accueil and Lieu); pixel-identical to the approved +24px prototype;
    Safari tab pixel-identical to before
  - signal: static gates - ruff, comment-history guard, function-size gate,
    suite guards pass; full suite: see Evidence/commit
guardrail_verdict: accepted
commit: c387ea2e
files_changed: [companion/static/splash-boot.js, companion/static/style.css,
  companion/static/style-place.css, companion/test_browser_web_app_bar.py,
  companion/test_browser_place_document_map.py,
  companion/testdata/render_baseline.json]

## Prevention
<!-- Blameless postmortem, written at archive -->

five_whys (branching):
  environment branch:
    - why blurred? iOS 27 draws a frosted band over the top of a Home
      Screen web app's window, fading out ~36pt below the status bar.
    - why does the page not avoid it? The frost is drawn above the web
      view and no page-side switch removes it (status-bar-style meta,
      colour strip and fixed top box all measured: no effect). It is an
      open WebKit regression (bug 301994), version-dependent (barely any
      on 26.5, tall on 27).
  code/layout branch:
    - why does it hit the brand? Every page puts its app bar at the
      window top, and the window starts at the status bar's bottom edge in
      a web app (safe-area-inset-top 0), so the glyphs sat at 74-100pt,
      inside the 62-98pt frost.
    - why was the layout never adjusted? Nobody had measured where iOS's
      own blur ends in a web app until map-fills-header-footer (Evidence
      2026-11-12T22:20), and that session read it as a Location-page
      matter, not as something every page's app bar sits in.
  process branch:
    - why did it look like a #369 regression? The owner reported it right
      after checking the #369 deploy at the top of the web app; the
      pre-#369 build is pixel-identical, so it predates #369 and only the
      timing linked them. Diffing the page's asset list across the two
      builds settled it in one step.
and_gate: yes - platform frost reaching below the status bar AND the app
  bar placed at the window top; the fix acts on the second.
why_not_caught: no gate existed for this class. The Chromium suite cannot
  render iOS's frost, and no test or check asserted where the app bar's
  glyphs sit relative to an iOS-drawn zone in a Home Screen web app; real-
  device and simulator checks covered the Location page's map, not the
  shared app bar on other pages.
recurrence_guard: companion/test_browser_web_app_bar.py -
  `test_the_phone_app_bar_starts_below_the_frost_only_in_a_home_screen_web_app`
  (gate on navigator.standalone === true only, 24px drop, first painted
  glyph row >= the measured frost depth, Lieu search/chips follow the
  bar), `test_the_location_loading_state_follows_the_app_bar`,
  `test_a_wide_screen_keeps_the_frame_button_where_it_was`; 12 passed on
  2026-11-13; 5 of 6 mutants killed (survivor equivalent). Plus this KB
  entry, so a new "blur at the top of the Home Screen app" report starts
  from the frost-depth measurement, re-measured on the owner's iOS
  version.
