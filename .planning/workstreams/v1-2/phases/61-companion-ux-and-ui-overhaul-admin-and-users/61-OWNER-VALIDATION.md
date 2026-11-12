# Phase 61 — owner validation on the deployed companion (plan 61-13)

Deployed: PR #287 merged 2026-11-03, CI green, production deploy green.
Verdict so far: first pass by the owner, as administrator, FR (screenshot of
the frame switcher). Not approved yet: issues below.

## Issues raised (priority proposed by the assistant, to confirm)

Most shocking for the owner (V0, structural, P0):
- V0 The administrator's view of a frame differs from the view a user has of
  the same frame. It must be the same. Only the Console / personal-space
  switch should tell an admin from a user. (V3 and V5 are consequences.)

Small, fixable in this phase:
- V1 "Mes vues" is unclear as a label for the personal space.
- V2 The Console / My views switch is not visible enough.
- V3 "All frames (Fleet)" must not appear in the frame switcher: an admin's
  personal view must not differ from any user's; only the Console/personal
  switch differs.
- V4 "Flights" should be named "Flight history" ("Historique des vols").
- V5 Health and Device should be tabs reachable only from the admin Console.

Larger redesigns (new design work, owner decision on scope):
- V6 The frame switcher is a drop-down; the owner expected something nicer.
- V7 "Location and detection" should have its own tab with a much more
  modern, polished UI (a map was suggested). The owner does not see why
  saved locations exist: they would just state the place each time.
- V8 Quiet hours and their settings should leave the Display page and
  appear as a modal opened by clicking the schedule on Home.
- V9 Display becomes a "Personalisation" tab with much more room to manage
  the displays clearly.
- V10 "Airlines" becomes a more gamified page of airlines observed; users
  must not be able to edit pictures or airline information: those options
  only for the administrator through a dedicated view.

## Decisions after the first pass (2026-11-03)
- D16 (owner) V0 confirmed: the personal space has the same pages for an
  administrator and a user on a frame (Home, Flights, Display, Account);
  Health, Device, airline editing, Fleet, Users, Locations, Audit and
  Releases live in the Console.
- D17 (owner) All of V1-V10 is done in this phase (not a separate phase).
  This needs an updated design contract and new plans before execution.
- D18 (owner) The "Location and detection" tab uses a real OpenStreetMap map
  (option A). This lifts the no-external-content rule for map tiles: the
  CSP img-src needs the tile host, and a map script must be vendored
  (first-party static file, no CDN). Attribution required. To specify in
  the updated UI-SPEC.
- D19 (owner) Place choice on the map: move the map and drop a pin, a local
  list of French airports, a search bar (Nominatim, external) and a "my
  position" button (browser geolocation, needs a permission prompt; check
  the Permissions-Policy header).
- D20 (owner) Saved locations are removed: no Locations page in the
  Console, a frame carries its own position chosen on the map. Expand-only
  for the live frame (its position and responses must not change); the
  existing locations table/column are not dropped by this phase.
- D21 (owner, answers R2-10) A user has no Health page: the status dot on
  Home is enough. When the dot is amber, a notification gives more
  information and offers to contact an administrator (mechanism to settle).
- D22 (owner) Contact an administrator from the amber-dot notification: a
  mailto link addressed to the administrator's email (no server-side
  sending). To be covered by the plans.
- D23 (owner, answers R2-20) Only administrators change the wake interval
  ("Refresh"), in the Console Device page. It does not move to
  Personalisation.
- D24 (owner) The Home notification with the "write to the administrator"
  link also appears for the red state (frame without contact), not only for
  amber.
- D25 (owner) The Home notification for the amber and red states says more
  of what the server already knows (low battery or delay, for how long, a
  fitting tip) so that a user can manage on their own on the things they can
  act on (charge the frame, check the Wi-Fi, ...). The frame cannot report
  the cause of a lost connection (frozen phase-47 protocol): Wi-Fi,
  internet and server-down all read "no contact".

## Validation of the deployed round 2 (2026-11-04), owner feedback
- W6 The status notification sat in the middle of Home. Decision D26a:
  it goes at the very top of Home, under the page title, before the state
  card (in progress, task 61-35).
- W6b Home state card: an orange dot beside the title "Écran allumé" while the
  frame never contacted SkyPane contradicted itself. Decision D26b (answer
  A): the card title shows the same word as the status dot.
- W8 The quiet-hours dialog works but is not pretty. Sketches A (dial), B
  (strip with − and +), C (preset cards) were shown. Decision D27: option C,
  three preset cards (Night, Day, Always active) with their hours, and the
  two big Start/End tiles below ("Or choose your hours"). To build in the
  next batch of corrections.
- Further feedback is being collected by the owner; batch the fixes.
- W9 "Location and detection" page (owner words, FR summary):
  - The main entry point is the mode: airport mode or "my position" mode.
  - The current "settings" card is hard to read and its purpose is unclear.
  - Coordinates and time zone are useless as inputs: they are outputs of the
    chosen place or airport.
  - Everything could be merged onto the map: click an airport, then pick the
    runway, and the page is in airport mode; give an address or use my
    position, then pick the detection radius, and the page is in "my
    position" mode.
  Direction (to sketch and confirm): a map-centred page with a mode switch,
  a context panel (runway cards in airport mode; radius control in position
  mode), coordinates and time zone derived and shown only as a small
  read-only line; the no-script fallback form stays.
- D28 (owner) The Location and detection page follows sketch V1: the map
  fills the page; a mode switch (Airport / My position) and a search float
  on it. Phone: bottom sheet (runway cards in Airport mode; radius control
  in My-position mode). Desktop: a floating card at the left of the map with
  the same content. Coordinates and time zone are derived outputs shown as
  a small read-only line. The map recentres on the part not covered by the
  card. Sketches: scratchpad/sketches (v1-tel, v1b-tel, v1d, v1d2).
- W10 Personalisation page (owner words, FR summary): the "On this page"
  list is a plain list of links; he wants a more styled, animated second
  navigation, with a dedicated page per item (Look, Special looks, Calendar,
  Screen). The Look view should show the look picker sheet (colour, background,
  diagonal band) as the main view instead of showing every possible panel.
- W11 (owner) The airline collection sort control is poorly integrated: the
  "50 airlines" pill, text filter, sort select and a clipped "Apply" button
  do not read as one control bar.
- W12 (owner) Rarity colours: rare airlines and aircraft should stand out
  through colour in the collection (and wherever they are listed).
- W13 (owner) The Account page "Preferences" card is under-designed: two
  full-width segmented bars (FR/EN and Auto/Light/Dark) with no labels or
  hierarchy, stretched across the desktop width.
- W14 (owner) The language (FR/EN) and theme (Auto/Light/Dark) switches in
  the navigation sidebar should be removed from the navigation bar; they
  belong on the Account page preferences only.
- W15 (owner) The Account navigation icon (a robot) does not read as an
  account icon; it looks more like preferences. Use a person icon.
- D29 (owner) Personalisation follows mockup P1: a styled, animated
  secondary navigation (Look, Special looks, Calendar, Screen), one page per
  entry, the look picker (preview, colour, background, diagonal band) as the
  main view of Look. Mockups: scratchpad/sketches (p1, p1d).
- W16 (owner) He cannot see the multi-frame management (switching between
  several frames) in the deployed companion. To clarify: which account and
  how many frames he has, so we know whether the switcher is hidden by
  design (one frame) or missing.
- W16 resolved: the owner tested the multi-frame management with an account
  that has several frames; nothing missing (the switcher is hidden by design
  with a single frame).
- W17 (owner, assumed to be the frame switcher, to confirm) Still not great:
  it should be shown at the top of the window or in the navigation, in a more
  graphical way, with the frame represented (for example a small picture of
  the frame) rather than a plain control.
- D30 (owner) The frame switcher follows mockup F2: a strip of frame tiles
  (small frame picture, name, status dot, last-seen word) with the active
  frame outlined and an "Add a screen" tile, instead of the dropdown.
  Mockups: scratchpad/sketches (f2, f2d; alternative f1 not chosen).
- W18 (owner, Console) The Fleet, Status, Version and Device tabs could be
  merged into one single view. He asks for sketches.
- W19 (owner, Console) The Users view could be a table and drop the manage
  modal (screenshot of the "Manage user" modal: role, access, sign-in).
  He asks for sketches.
- W20 (owner, Console) The airline editor could also be improved by laying
  everything out as a table. He asks for sketches.
- W18 refined (owner) Neither C1 (expandable table) nor C2 (table + side
  panel) fits. Reuse the graphical frame selector (tile strip, D30) in the
  Console: clicking a frame tile opens one detailed view with its state,
  settings, version and device. Mockup C3 (scratchpad/sketches c3, c3t).
- D31 (owner) Console Fleet = mockup C3 with full content: the tile strip of
  frames plus a last "System" tile. A frame's detail view holds four complete
  blocks: State (connection, battery, last detection, current flight),
  Device and version (model, version history, scheduled update), Settings
  (wake interval and other device settings), Access. System-wide information
  (ADS-B sources, backups, server anomalies) lives in the System tile. The
  separate Status, Version and Device Console tabs go away.
- D32 (owner) Console Users = mockup U1: a table without the manage modal;
  role editable in the row and saved at once, an Active switch, a "..." menu
  for rare actions (unlink identity, resend invitation, delete); phone shows
  cards. Mockups: scratchpad/sketches (u1, u1t).
- D33 (owner) Console Airlines editor = mockup E1 (table, name editable in
  place, artwork thumbnails, prefixes, views, unidentified airlines on top).
  A toggle lets the table manage several aircraft types per airline (one
  artwork per type) or a single artwork per airline. The row "..." menu holds
  the rare actions: edit callsign prefixes, reset to SkyPane's name, delete
  my name, open the artwork full size.
- D33 refined (owner) Airlines editor = mockup E3: each airline row has an
  expand chevron; expanded, one sub-row per aircraft type seen (aircraft
  info, views, its own artwork to replace, or "uses the airline's artwork").
  Callsign prefixes are shown read-only in the table. The row "..." menu is
  reduced to "Reset to the original name" and "Enlarge the artwork". The
  per-table toggle of E2 is dropped. Mockup: scratchpad/sketches e3.
- W21 (owner, screenshot) The Console / "My frame" space switch is broken in
  the desktop sidebar: the "My frame" label overflows its segment and the
  active segment is wider than the pill. The labels must fit.

## Round 4: validation of the deployed batch 3 on iPhone (2026-11-05)

- W22 (owner) On phone, the header gear button and the "Sign out" panel
  below it must disappear (Sign out stays on the Account page).
- W23 (owner) On phone, the frame tile strip must be smaller: only the
  picture and the name (no text underneath). The strip should open and
  close, and be more visually marked (a darker or lighter background for
  texture).
- W24 (owner) The Home notification text "Your frame has not contacted
  SkyPane yet. Check the frame is powered, then wait one cycle. If it does
  not recover, an administrator can help you." is too long.
- W25 (owner) The Location page is unusable on phone (small map strip, the
  floating cards cover it, the airport filter field renders empty, the sheet
  is cut).
- W26 (owner) Special looks texts are too long ("Current: no special look
  yet", the section intro, the empty state with its explanation). The
  preview should be bigger with the interface laid over it; the preview in
  the "New special look" sheet is ridiculously small.
- W27 (owner) "Screen on" has no place on the Personalisation Screen view,
  it is already on Home.
- W28 (owner) The aircraft/airline detail modal is too tall for a phone
  screen (the Close button is cut off).
- W29 (owner) The badges tile on the airline collection page is too big on
  phone.
- W30 (owner) On the Account page, "My frames" deserve a graphic preview of
  the frame.
- W31 (owner) Console feedback to come.
- W32 (owner) He cannot see where a new user adds a new frame by themselves.
  Finding: pairing (/fleet/pair, "Add a screen") is Console-only and
  administrator-only; a plain user has no way to pair a frame. Product
  question open: should a user be able to add their own frame?
- D34 (owner) A user can add their own frame by pairing it with the code
  shown on the frame. The "Add a screen" entry is available to every user:
  on the Account page and as the last tile of the frame strip. A user with
  zero frames is offered to add one from the very first sign-in (an empty
  Home state whose main action is "Add your frame"). The new frame is owned
  by that user. Needs: access matrix row for users on the pairing routes,
  ownership assigned to the pairing user, audit entry, abuse limits (same
  code validation and rate limiting as today), tests with the fake frame
  protocol only.

### Round 4, Console feedback (iPhone, 2026-11-05)

- W33 (owner) The "Add a frame" button must appear only in the frame
  navigation (the tile strip). Access is currently both the "..." menu and
  the tile: keep the more relevant one (he leans to dropping the tile).
  (See D34: users can pair too.)
- W34 (owner) Remove the explanatory subtitles on Console pages ("All the
  frames of the platform: who owns them and whether they are up to date"):
  an administrator does not need them. Same for the long helper captions in
  the Airlines editor ("Rename in place, click the artwork..., Unidentified
  prefixes first...", "Every flight using the prefix DEF will show under this
  airline", "start typing").
- W35 (owner) Users, phone: the "Invite a user" button collides with the
  page title (title overlaps the button). Make inviting a button or modal at
  the start or end of the user list instead.
- W36 (owner) Airlines editor: the frame navigation strip is useless there;
  the list could be global (not per frame).
- W37 (owner) Airlines editor: enlarging the artwork should happen on tap of
  the image; changing the image goes in the "..." menu. Filters scroll
  sideways instead of wrapping on two lines.
- W38 (owner) Navigation, phone: remove the Console / My frame switch from
  the "More" menu and remove the big switch at the top of the page. Instead,
  the first button of the tab bar is a Console / My frame button, set apart
  from the others, that switches from one to the other.
- W39 (owner) In general, the phone header is too tall. Make it compact
  (with W22 removing the gear button and the Sign out panel, and W38 moving
  the space switch into the tab bar, the header can shrink to a slim bar).

### Round 4, Location page on desktop (2026-11-05)

- W40 (owner) The map on desktop could be even bigger.
- W41 (owner) Filter and switch buttons are often not centred (the
  Departures / Arrivals count tabs, the Airport / My position switch: label
  alignment inside the segments is off). Centre them everywhere.
- W42 (owner) Search should be a single field that accepts both an IATA
  code and a normal address, placed above and separate from the rest of the
  panel. The two fields today (place search and airport filter) are
  confusing.
- W43 (owner) Bug: tapping the round "my position" button at the bottom
  right of the map does nothing.
- W44 (owner) Coordinates and time zone line is useless: remove it from the
  page (they stay derived and stored).
- W45 (owner) "Saved settings" disclosure is useless: remove it. The map
  credit and "about this map" text become a discreet "i" icon on the map.
- W46 (owner, screenshot of the airline collection header on desktop) The
  header is heavy and cluttered: a large progress card with five badge
  pills, then a filter field, a sort select, a three-way count segment, a
  repeated "Airlines: 40" count and a rarity legend line, all stacked.
  Simplify.
- W47 (owner, screenshot) Personalisation has two layers of navigation (the
  pill bar Look / Special looks / Calendar / Screen, then the Departures /
  Arrivals tabs). Merge them into one main tab bar: Departures, Arrivals,
  Special looks, Calendar. (Open: where the Screen view goes, since his list
  names four entries and does not mention Screen.) Joins plan 61-48.
- W48 (owner, screenshot of the Look view on desktop) The screen is not
  optimised: the preview sits on top and the settings card fills the width
  below, leaving a large empty area at the right. On desktop put the preview
  on the left and the settings on the right (two columns, both visible
  without scrolling). Phone keeps the stacked layout. Joins plan 61-48.
- D35 (owner) The Personalisation "Screen" view is removed (it only holds
  the screen on/off switch, which already lives on Home; supersedes W27).
  Personalisation = one tab bar: Departures, Arrivals, Special looks,
  Calendar. /display/screen stays served (expand-only) and redirects to the
  Look view. Plan 61-48.
- D36 (owner) Location page follows mockups L1 (phone, Airport mode), L2
  (phone, My position mode) and L3 (desktop): one floating search field
  (IATA code or address) at the top of the map, separate from the panel; the
  mode chips under it on phone, the mode switch inside the floating card on
  desktop; compact bottom sheet on phone (name, runways or radius, Save);
  floating card at the left of a full-height map on desktop; working "my
  position" button at the bottom right; discreet "i" for map credits; no
  coordinates/time-zone line, no saved-settings disclosure. Mockups:
  scratchpad/sketches (l1, l2, l3). Plan 61-50.
- D37 (owner) The companion takes visual direction A, "sky and motion": a
  sky gradient background that follows the time of day (dawn, day, dusk,
  night), frosted-glass cards, a personal greeting title, a small plane that
  follows a trail under the Home title when a flight is detected, pulsing
  status dot, progress bars and badges that fill in, staggered card
  entrance, bigger serif titles. Owner wants a bolder, more modern, more
  animated look. Mockups: scratchpad/sketches (a1 day, a2 night; the
  editorial option C was not chosen). Motion respects reduced-motion.
- D38 (owner) Go with style A as drawn. The mockups are a visual direction
  only: they do not show the latest companion structure (slim phone header,
  first tab-bar space-switch button, collapsible frame strip, notification
  under the title, one-level Personalisation tabs, Location sheet, etc.).
  The style is applied to the real current pages and keeps all their
  content, controls and rules; nothing is redrawn from the mockups.

### Round 5, first look at style A in production (2026-11-05)

- W49 (owner) Overall, the owner does not like the new design much: unsure
  whether it comes from inconsistencies or from the whole direction.
  Decision pending: refine versus roll back (do not merge PR #301 meanwhile).
- W50 (owner) The translucent navigation bar should be an iOS "Liquid Glass"
  effect (strong refraction/blur of what scrolls under it, specular edge,
  floating pill), not a flat translucent bar.
- W51 (owner) Frame choice: a button at the top right that opens the frame
  choice panel (well integrated popover or sheet), instead of the tile strip
  shown on the page. Supersedes D30 in the user view; the Console view needs
  the same logic.
- W52 (owner, bug) Better transparency handling of the header and footer: on
  iPhone there are black bars at the top and bottom (safe areas / status
  bar / home indicator area not covered by the page background; check
  viewport-fit=cover, theme-color, env(safe-area-inset-*) and the fixed sky
  layer).
- D39 (owner) Refined visual direction, replacing the deployed style A
  execution. Decisions: a single very pale sky background in Light (no more
  time-of-day skies) and an ink-dark background in Dark; GRAPHITE accent
  (#1F2430) in Light, ivory in Dark (links, toggles, active tab, primary
  buttons, icon chips), status and rarity colours kept; system sans-serif
  only (no serif titles); fewer tiles: titles and a single "hero" without
  cards, then grouped lists (one glass surface per section, rows with icon,
  label, value, chevron, hairline separators), grids of cards only for the
  airline collection; Liquid Glass floating tab bar on phone; frame choice
  as a button at the top right opening a popover (sheet on phone), also in
  the Console; fix the black bars on iPhone (viewport-fit=cover, theme-color,
  safe areas, canvas colour). Mockups: scratchpad/sketches m1-m3, d1, g1-g3,
  bg4, acc6, sheetA, sheetB, q1-q9. Audit report: scratchpad/audit/AUDIT.md.
  The owner asked not to approve the production deploy of the style A pages
  until the refinement is ready (note: the style A deploy from PR 301 is
  pending approval on main).
- D40 (owner) Console Fleet frame choice: a button at the top right showing
  the selected frame (name, status dot, chevron) opens a glass popover with
  the platform's frames (thumbnail, status, owner for others' frames, check on
  the active one), then "System" and "Add a frame". The page content follows
  the selected frame in grouped lists (State, Device and version, Settings,
  Access). Phone Console tab bar: "My frame" switch first and set apart, then
  Fleet, Users, Airlines, More. Mockups: scratchpad/sketches r1, r2. Plan
  61-57.

### Round 6, first look at the refined design in production on iPhone (2026-11-06)

Owner: "C'est beaucoup mieux !" Then:
- W53 Remove the plane-on-a-trail animation on Home: it does not work well and
  takes too much room.
- W54 The Home title should be a personal greeting ("Bonjour Florian") as in
  the mockups, instead of "Accueil" (first name from the account; fall back
  to a neutral greeting).
- W55 Home, Recent flights: every row links to the same flights page as "See
  all flights", which is odd. Rows should not all act as the same link.
- W56 The header area under the iPhone status bar / battery is still not the
  same colour as the site background (a lighter band at the top).
- W57 Flights: the Departures/Arrivals filter is still not centred, and the
  text inside the filter is not centred in its box (count stacked above the
  label).
- W58 Flights rows: the little plane icon on each row and the image button
  could be merged into one.
- W59 Personalisation: the buttons and swatches in the settings box could be
  smaller so more of the interface fits on screen.
- W60 Airline collection: the filter and sort part is still not nice; it
  should be clearly merged and improved.
- W61 Account of a co-manager (Marco Alfinito): the Account page says
  "User" while he is in fact a co-manager of a frame; show that.
- W62 Manage access (dialog): completely broken on phone (title clipped under
  the sheet edge, grey wash, input instead of a select for a co-manager).
- W63 The little frame picture before each frame in the frame selector
  popover is broken (renders as a warped capsule).
- W64 The background of the "More" menu in the navigation is too
  transparent, text cannot be read; give it the same background as the tab
  bar.
- D41 (owner) After plans 61-61 to 61-63, the owner wants a complete audit by
  Claude, on both desktop and phone views, to detect display bugs, UI bugs
  and UX bugs, and above all to propose improvements so the application feels
  finished, modern, dynamic and simple. Plan 61-64 (audit and proposals, no
  code changes; the owner picks what to build).
- D41 refined (owner) Present the audit results as an infographic (clear
  visual summary: findings by severity and area, UX journeys with step counts,
  prioritised improvement proposals), not as a long text report.
- W65 (owner, screenshot) Location page on phone: the bottom panel (runway
  choice, or radius around a position) is far too big; the map is barely
  visible. Make the panel compact so the map dominates.
- W66 (owner) In Airport mode he expected pins for all the airports of France
  to be displayed on the map, tappable to select one. Nothing is drawn in
  production (the 61-41/61-50 airport dots do not show): investigate and fix.
- W67 (owner) In My position mode he expects to pick a position by tapping the
  map.
- W68 (owner) Typing in the search bar shows no suggestion, neither an airport
  nor an address. Suggestions wanted. Constraint: the public Nominatim service
  forbids search-as-you-type autocomplete (usage policy), so: airport
  suggestions instantly from the local airport list while typing; address
  results as a suggestion list on submit (Enter / search button) from
  Nominatim (D19), no per-keystroke requests to Nominatim.
- W69 (owner) Location page: the map could go beyond the header and pass under
  it (full-bleed under the status bar and the app bar). If that hurts
  readability of the site name, add a small soft gradient scrim behind the
  header (a nice-looking fade), not a hard bar. Joins plan 61-65.

## Audit decisions (D42), owner answered point by point

Source: scratchpad audit (30 findings, 12 proposals) and mockups P01..P10
(before/after). The owner validated all 12 points as proposed:

- P01 Fleet save bar docked at the bottom (above the tab bar on phone).
- P02 Redirect /health, /device, /update and old bookmarks for every role.
- P03 Phone More sheet: theme, language, Account, Sign out (mockup).
- P04 Personalisation: one 4-segment selector, same list layout for Special
  looks and Calendar (mockup).
- P05 Location map: opens on the airport, numbered clusters, runway badge in
  the corner, readable dark ORY label (mockup).
- P06 Flights: stable inline search, Load more (mockup).
- P07 Switches: darker off track, contrasting thumb, dark contrast fixes.
- P08 One toast, one sheet style, error shown once, focus trap, no time
  auto-focus.
- P09 Users: ellipsis, status pills, co-manager frame count, copyable invite
  message (mockup).
- P10 Fleet on phone: State / Settings / Access sub-tabs (mockup).
- P11 Plural, frame name and validation i18n sweep, consistent page titles.
- P12 404/forbidden page: visible Home button, clear admin-only message.

Plans: 61-66..61-71 in `61-BATCH3-PLAN.md` (batch 8).

## Round 7 (iPhone, Safari with floating toolbar)

- W70 (owner) Small bug with the shadow at the bottom of the page (Home on
  iPhone, screenshot): the floating tab bar sits well above the Safari
  toolbar, and below it a pale wash with a hard horizontal edge crosses the
  full width, with the page content visible between the bar and the toolbar.
  Investigate (safe-area-inset-bottom with the floating Safari toolbar,
  `--bar-shadow`, `100dvh`/`svh` fixed-element bottom edge, body background
  vs the page canvas) and fix: no hard edge, shadow soft and clipped to the
  bar. Planned inside 61-67.

## Motion decisions (D43), owner answered idea by idea on real-page demos

All ten motion ideas validated as demoed (CSP-safe: no inline style; reduced
motion respected; whole-pixel moves; works without JS where noted):

- M1 Live Home (pulsing dot, ticking countdown, count-up, new flight slides in).
- M2 Skeletons then blur-up picture fade.
- M3 Pull to refresh on Flights (Refresh link stays without JS).
- M4 Spring press feedback on buttons, rows, chips (CSS only).
- M5 Sliding tab-bar pill.
- M6 Flight thumbnail to picture shared transition; owner: show the picture
  alone, no white card around it.
- M7 Draggable bottom sheets (grabber, drag to close).
- M8 Spring switch with tick (vibrate where supported).
- M9 Swipeable toast.
- M10 Airline card unlock (3D flip, glint, sparks, once).

Plans (batch 9) in `61-BATCH3-PLAN.md`: 61-72 (M2, M4, M5, M8), 61-73 (M1, M3),
61-74 (M7, M9), 61-75 (M6, M10).

## Round 8 (desktop test of the deployed round 7), in progress

- W71 (owner) General: the title transition effects from one page to the
  next are a bit buggy and differ every time.
- W72 (owner) Home: the empty-state sentence "Vérifiez qu'il est alimenté ;
  s'il reste muet, contactez un administrateur." must use a comma, not a
  semicolon.
- W73 (owner) Home, Quiet hours dialog (desktop screenshot): contrast problem
  (grey translucent panel, grey secondary text on grey).
- W74 (owner) Flights history (desktop screenshot): the search field runs
  into / under the frame picker button at the top right.
- W75 (owner) Flights: clicking a picture whose image has not loaded yet shows
  an odd visual glitch. More generally the site has no loading indicator where
  one is needed; avoid odd transition effects.
- W76 (owner) Location: while the page and the map load there is an odd
  intermediate state; a small loading icon is probably missing.
- W77 (owner) Location (screenshot): the sheet tiles are too transparent, the
  text over the map is hard to read; the runway cards' text (length, surface)
  sits off-centre / overflows its card and the check mark overlaps.
- W78 (owner) Location (screenshot): the Airport / My position segmented
  control is still offset inside its container.
- (A desktop screenshot of the Account "Mes cadres" group was also attached,
  no comment yet.)
- W79 (owner) Location (screenshot): a gap is missing between the airport
  info (name, codes) and the "Piste à suivre" heading.
- W80 (owner) Location: the Save place button behaves differently from the
  rest of the site; it should be the small popup/bar "Save or Cancel" that
  appears (the docked unsaved-changes pattern), not an always-visible footer.
- W81 (owner) Location: he likes the nearest-airport follow suggestion. "My
  position" should be the first tab when the page opens, and the sheet's text
  sizes and margins need visual rework (not pretty: runway card text clipped,
  "Rayon" row, suggestion button, footer not aligned with the sheet padding).
- W82 (owner) Location: the map could also pass behind the navigation menu
  (desktop sidebar) for a really cool effect.
- W83 (owner) Personalisation: the Departures and Arrivals tabs do not have
  the opening effect the other two tabs have.
- W84 (owner, positive) The picture reveal when changing colour etc. is very
  stylish.
- W85 (owner) Personalisation vocabulary: "Couleur" should read "Couleur
  principale"; "Papier" should read just "Blanc"; the "Bande diagonale"
  wording to change. His message was cut off; its continuation says: "...
  should not have a 'Claire' option" (the diagonal band selector, options
  None / Pleine / Claire, most likely; to confirm with the owner which
  selector and what the options become).
- W85b (owner, screenshot) Clarified: in the new-look dialog the diagonal band
  option "Claire" shows struck through ("Le cadre n'a pas encore de thème pour
  cette combinaison"); an option with no theme should not be offered at all.
- W86 (owner) Personalisation: the "new special look" dialog is broken on
  desktop; he expected the options in a full page like the Departures and
  Arrivals tabs, not a modal.
- W87 (owner) Personalisation: the Calendar view is completely broken when
  editing a calendar's configuration or adding a new one. Same wish: go to a
  page instead of a modal where possible (also for the other dialogs).
- W88 (owner) Airline collection: the title is too big; call it "Compagnies"
  (preferred) or "Collection". The desktop view is far too busy, illegible:
  he wants a detailed, near-real mockup proposal.
- W89 (owner) Account: the frame rows should breathe more; as a user he does
  not care about the hardware detail line.
- W90 (owner, screenshots) Account: the Manage access dialog (add a
  co-manager) is a bit broken (empty-state heading inside the owner group,
  uneven paddings, Done button off-grid).
- W91 (owner, question) As a user (owner of a frame) there is no option to
  remove a frame: is that normal? Answer: today only administrators can retire
  a frame; owners see Manage access, co-managers see Leave frame. Product
  decision needed (owner "Remove frame" with confirmation?).
- W92 (owner) In the Manage access dialog the e-mail field pre-fills itself
  (browser autofill suggestions); very annoying: disable autofill on that
  field (autocomplete off, no autofill of the owner's own address).

### Admin account (desktop)

- W93 (owner, screenshot) Fleet (admin, desktop): the visual principle is
  right but the rendering is a bit broken and too busy: box sizes and the
  amount of information shown need rework; there are holes (empty space) in
  places and too much text elsewhere (State group short vs a tall Device and
  version group with the versions list; Settings and Access below). He asks
  me to make a proposal.
- W94 (owner) Idea: on desktop the Fleet groups could stop being toggles /
  expandable blocks and become dialogs that open. (To weigh against W86/W87,
  where he prefers pages over modals for Personalisation.)

#### Users

- W95 (owner, question) What does "Dissocier l'identité" mean? Answer: it
  detaches the person's sign-in identity (the sign-in provider account linked
  at first login) from their SkyPane user and closes their session; the
  identity is linked again at their next sign-in. Wording to make clearer.
- W96 (owner, screenshot) Users: his own row is far too wide compared with the
  rest (the self-protection explanation under the role, five lines of text,
  "2 cadres · co-gestionnaire" wrapping).

#### Airline editor

- W97 (owner, screenshot) Unidentified airline rows lack finesse: the "Nommer"
  button is not centred and a bit too big.
- W98 (owner, question) Why can the visual of some aircraft types not be
  changed? e.g. for Air France nothing can be done on the type rows (their
  row menu offers nothing / "Utilise celle de la compagnie").
- W99 (owner) Missing option to delete an illustration, with a default
  behaviour: the type (or airline) reverts to the default illustration; this
  also means being able to pick a flight type as the airline's default one.
- W100 (owner) Why is there a separate "manual resolution" table? Resolution
  should happen directly in the airline table.
- W101 (owner) The "unresolved fleets" table in System should no longer exist
  since it is already in Airlines.

#### Audit log

- W102 (owner, screenshot) Too much information per row and the table
  overflows the page; use a toggle (expandable row) to show more detail.
- W103 (owner, question) Wouldn't "Delete user" be simpler than "Unlink
  identity"? Open: today a user can only be disabled (Active switch) or have
  the identity unlinked; no delete exists. Needs a product decision on what
  happens to the user's frames (owner) and the audit trail before building.

### Round 8, iPhone checklist (owner answers, numbered as the checklist)

- Items 1 (bottom shadow/bars) and 6 (Home): all OK. Item 5 Vols and 8
  Personalisation: OK except as noted below.
- W104 (owner, item 2) The animations play late the first time they load, so
  they lose their dynamism. General question: should there be a preload at
  site opening that loads the animations and everything needed into cache,
  with the loading logo he mentioned was missing (also W75, W76)?
- W105 (owner, item 3) The More menu is much better, but "Collection de
  compagnies" is lost among all the information. Idea: dim/blur the site
  behind so the More panel stands out more.
- W106 (owner, item 4) Better, but e.g. the Quiet hours sheet needs scrolling
  to reach Save (a problem). On desktop and mobile, the modal backgrounds
  have a fake transparency effect that does not work and makes the content
  hard to read (same as W73).
- W107 (owner, item 5) Opening a picture: the blurred yellowish band below the
  image falls oddly: the backdrop is not covering enough (screenshot: caption
  pill and Close over a half-transparent strip, the tab bar and list show
  through).
- W108 (owner, item 7) Location: the map is still not fully full-screen; it
  does not pass under the floating navigation bar. Should "Save place" use the
  floating Save/Cancel popup like the other save buttons? Maybe not possible
  with the nav bar.
- W109 (owner, item 8 Personalisation) Same remark as Location: the Save
  button does not have the floating popup behaviour agreed earlier.
- W110 (owner, item 9, screenshot) Fleet sub-tabs on phone: the selected
  segment is a tiny black pill, broken (thumb not sized to its tab). The
  admin "Mon cadre" tab label is clipped and outlined.
- W111 (owner) When changing tab, the bar briefly becomes transparent then
  opaque (screenshot also shows page content showing through the tab bar).
- (owner has not finished; more items to come.)

## Round 8 grouping (D44)

The owner finished his round 8 feedback (W71-W111). Grouping:

Straight fixes, no decision needed (plan 61-76): W72, W73, W74, W77, W78,
W79, W83, W85 (Couleur principale, Blanc, hide unavailable options), W89,
W90, W92, W95 (reword), W96, W97, W106 (opaque modal backgrounds, Save
reachable without scrolling), W107, W110, W111.

Decisions with mockups (asked one by one): D-A Collection page desktop (W88),
D-B Fleet admin desktop (W93, W94), D-C airline editor (W98-W101), D-D audit
log (W102), D-E Location (W80, W81, W82, W108), D-F preload and loading
indicator (W71, W75, W76, W104), D-G More menu (W105), D-H Special looks and
Calendar as pages (W86, W87, W109), D-I Users: delete user (W103), D-J owner
removes a frame (W91).

- W112 (owner) The Home page really lacks a signature element: a stylish
  animation with a "wow" effect, without taking much space. Concepts to be
  shown as live demos on the real Home page (decision D-K).
- W112b (owner) The frame will later also display photos, so aircraft are one
  use and not the only one: the signature animation must not be built around
  planes; it should be about the frame and the app in general (content
  neutral).

## Decision D-K (signature animation), owner answered

S1 Respiration (glass glint every ~12 s, breathing halo and status dot) and S3
Cycle (thin ring around the picture showing the wake, poll, display, sleep
cycle until the next update, small flourish on refresh) together, both
content-neutral. S2 and S4 not retained (so the S4 flash limit does not
apply). Planned as plan 61-78 after 61-76.

## Round 8 decisions (D45), owner answered one by one

- D-A Collection: the mockup, but the page title keeps the standard size used
  by the other pages (consistency); renamed "Compagnies".
- D-B Fleet admin desktop: option 2, summary rows that open dialogs.
- D-C Airline editor: the mockup (inline resolution, editable type rows with
  "same as airline" default, delete illustration / revert to default, star
  for the airline default type, no separate manual-resolution table, no
  unresolved-fleets table in System).
- D-D Audit log: the mockup (compact rows, expandable detail).
- D-E Location: the mockup, "My position" first; on mobile in My position the
  nearest-airport suggestion is removed to leave room for the map and the rest
  of the sheet is compressed without becoming illegible; floating Save/Cancel
  bar; map behind the sidebar / tab bar.
- D-F Preload: opening splash once per session plus map/picture loading
  indicators; the splash must be much more signature (3 concepts to choose).
- D-G More menu: dimmed page behind; navigation pages (Companies, ...) at the
  top as the continuation of the tab bar, then a separator, then settings
  (theme, language, account, sign out).
- D-H Special looks and Calendar as full pages with floating Cancel/Create.
- D-I Delete user: with confirmation, refused while the person owns a frame,
  e-mail kept in the audit log.
- D-J Owner can remove their frame from Manage access, with confirmation;
  admin can reassign; co-managers keep Leave frame.
- D-K Signature animation: S1 + S3 (content-neutral).

Plans (batch 11): 61-77 Compagnies page + More menu + Fleet desktop rows;
61-78 Home signature S1+S3; 61-79 Location + Special looks/Calendar pages;
61-80 airline editor + audit log; 61-81 delete user + owner removes frame;
61-82 opening splash and loading indicators.

## Decision D-F (opening splash), owner direction

He chose the "Cadre" concept (P2 / V2 Cadre fidèle) with these changes: the
coloured artwork drawing (sun, hill) that has nothing to do with the app goes
away; the e-ink refresh instead reconstitutes, in ink, the real interface of
the site (the page being revealed); the logo is much smaller, centred and
present from the very start of the splash. Planned as plan 61-82 once the
revised demo is validated.

D-F final: the owner rejected the ink-rendered-interface variant ("j'aime
pas"); the original P2 "Cadre" concept (splash79: frame outline draws, e-paper
refresh inside it, logo revealed, page opens from the frame rectangle) is the
one to build, no coloured artwork, no dithered interface. Logo to stay small
and centred. Reference: scratchpad splash79/demo.html section p2. Plan 61-82.

- W113 (owner) There is no battery indication left for the user on the Home
  screen (a surprise to him). Cause: plan 61-17 removed the battery tile from
  Home for users (administrators keep a small pill; users only get the amber
  or red notification when low). He asked for mockups of where to put it back
  before choosing (decision D-L).

## Decision D-L (battery on Home), owner answered

Option C: a "Batterie" row in the Home Frame group (under Screen and Quiet
hours): icon tile, "69 % · Niveau normal", a thin level bar and the estimated
autonomy ("environ 3 semaines") only when an honest figure exists; "Aucune
mesure pour l'instant" with no bar when there is no reading. For every user
(not only administrators). Mockups: scratchpad battery82/. Planned as plan
61-83.

## Round 9 (production review of round 8, page by page; in progress)

Home
- W114 (owner) "À jour" and "Prochaine mise à jour dans 25 min" are not
  coherent: merge the two lines into one coherent statement.
- W115 (owner) Battery row: "Niveau normal" is useless: drop it; show the
  autonomy ("~6 semaines") beside the percentage, not below it.
- W116 (owner) Clicking a toggle (such as Quiet hours) reloads the page with a
  strange effect.
- W117 (owner) The title "Bon après-midi, Florian" and "À jour" are the same
  size, which is confusing.
- W118 (owner, screenshot) The Quiet hours sheet does not show everything at
  once on iPhone: the end time is hidden below Start, scrolling is needed.
- W119 (owner) "Toujours actif" is useless: it is the same as switching the
  toggle off; remove it.

Flights
- W120 (owner) Too much information per row, hard to read on mobile: remove
  the flight ID number and the small plane icon (it carries no information).
- W121 (owner) Opening a picture: the navigation bar is briefly above the
  Close button, then goes under it: a visual glitch.

Location
- W122 (owner, screenshot) On desktop and phone, the Location page shows
  another interface (an empty grey rectangle) for a few milliseconds before
  the map: very disturbing; he expected the loading bar here.
- W123 (owner) Picking an airport from the search results reloads the page and
  shows that temporary interface again.
- W124 (owner, screenshot) On mobile the page still has an ugly grey header
  band and footer band instead of the map full-bleed.

Personalisation
- W125 (owner) Still a bug on the Calendar view.
- W126 (owner, screenshot) The Save button inside the look tile (as on
  Departures) is a duplicate: remove it, the "Save settings" floating bar
  already exists. (Desktop screenshot also shows the "Comme les départs" card
  clipped at its top edge.)

Airlines
- W127 (owner) Much better, but the aircraft are too big for their box: make
  them a bit smaller to air out the page and each card.

Mobile
- W128 (owner, screenshot) The floating "Save settings" bar: its button is too
  big and wraps onto two lines: just "Enregistrer".
- W129 (owner, screenshot) The More menu is still not right. Order: Compagnies,
  then Compte, then Thème, then Langue, then Déconnexion. Its background is
  half transparent (odd): it should be the same colour as the navigation bar.
- W130 (owner) The tab bar is too high: too far from the search and from the
  Safari bottom UI.
- W131 (owner) The tab bar is not visible enough against the rest of the
  interface, which is mostly white or light blue.
- W132 (owner) The sliding tab pill works about one time in ten when changing
  tab.
- W133 (owner) When changing tab, a light-blue footer appears for half a
  second then disappears.

Console
- W134 (owner) Switching between the My frame view and the Console view: the
  space switch is not aligned the same in the two views, and neither is the
  logo.

Fleet (admin, desktop)
- W135 (owner) The Fleet view still does not work well: some elements open
  inline (toggles), others open in modals, and information is repeated. It
  needs rework: he wants proposals (mockups).

Users
- W136 (owner, screenshot) Buttons on two lines are a problem, illegible (the
  row menu items "Réinitialiser la connexion" and "Supprimer l'utilisateur"
  wrap onto two lines).
- W137 (owner, screenshot) Display bug in the Users table: the "6
  utilisateurs" caption sits on the top edge of an outer translucent panel
  whose border runs through it, with the table card nested inside it (double
  panel, caption overlapping the border).

Airline editor
- W138 (owner, screenshot) The name field and the aircraft-type field in the
  inline resolve rows are too long, which makes the row less pretty (the name
  input stretches across most of the row).

Audit log
- W139 (owner, screenshot) A strange number appears in the audit log next to
  the e-mail (the target's internal id, e.g. "...le.org4", glued to the
  address with no separation): hide it or show it clearly as secondary.

Airlines header
- W140 (owner, screenshot) Everything is a bit too tight to the title: the
  identified-airlines counter / progress should drop below the title so the
  header breathes.
- W141 (orchestrator, from the same screenshot) The counter text reads "38
  compagnies sur 36 repérées" (38 of 36), which is incoherent: the wording or
  the figures are wrong (chips say Toutes 47, Repérées 38). To fix with W140.
- (owner has not confirmed he is done; more may come.)

## Round 9 grouping (D46)

The owner finished his round 9 feedback (W114-W141). Grouping:

Straight fixes, no decision needed (plan 61-84): W116, W119, W121, W125,
W126, W127, W128, W132, W133, W136, W137, W138, W139, W140, W141.

Decisions with mockups (asked one by one, mockups in scratchpad mockups90/):
Home status coherence and battery (W114, W115, W117), Quiet hours compact
(W118), Flights rows (W120), tab bar and More menu (W129, W130, W131),
Console/My frame switch (W134), Fleet desktop (W135), Location mobile
full-bleed and loading state (W122, W123, W124).

## Round 9 decisions (D47), owner answered one by one (mockups90/)

- R9-1 Home status block: layout option 1 (single line); wording: the normal
  state word becomes "En ligne" (EN "Online") instead of "À jour", and the
  line reads "Prochain rafraîchissement dans N min" (EN "Next refresh in N
  min"); the owner's point: "À jour" next to "next update" contradicts
  itself. Greeting small and grey; battery "69 % · autonomie ~6 semaines" on
  one line without "Niveau normal".
- R9-2 Quiet hours sheet compact (Nuit / Journée side by side, no Toujours
  actif, Début / Fin side by side, Enregistrer, Fermer), all visible on
  iPhone.
- R9-3 Flights rows: option 1 (two lines), no plane icon, no call sign in the
  row (kept in the detail).
- R9-4 Tab bar: option A (floating, low, opaque, strong active pill, clear
  contrast, no pale band); More menu opaque, same colour as the bar, order
  Compagnies, Compte, Thème, Langue, Déconnexion.
- R9-5 Console / My frame: logo 44 px in both views, 6 tab cells in both
  (Console gains Journal).
- R9-6 Fleet desktop: option 1, one column of coherent sections with
  everything inline and nothing repeated; the only dialog left is the
  confirmation for Remove this frame (replaces the summary rows and dialogs).
- R9-7 Location: full-bleed on phone, designed loading state with a progress
  bar replacing the no-JS form flash, picking an airport moves the map in
  place without reloading.

Plans (batch 13): 61-85 Home status wording and battery, Quiet hours,
Flights rows; 61-86 tab bar, More menu, Console switch; 61-87 Fleet desktop
single column; 61-88 Location full-bleed, loading, in-place airport.

## Round 10 (production review of round 9, desktop; in progress)

- W142 (owner, screenshot) Flights: the page is buggy when the list is empty:
  header chips read "Tous 0 / Départs 0 / Arrivées 0" while the empty state
  says "44 vols", the table header is shown under the "Aucun vol
  correspondant" card, and "44 vols affichés" + "Charger plus" still appear.
- W143 (owner) "Charger plus" sends him back to the top of the table, which
  makes no sense (it should keep the position / land on the first new row).
- W144 (owner, screenshot of Location search) Typing a city ("Arrou"): the
  hint "Un code ou un nom d'aéroport choisit cet aéroport. Tout le reste est
  envoyé au service de recherche d'OpenStreetMap (Nominatim)." covers the
  suggestions; he has to press Enter to see a city name.
- W145 (owner, screenshot) Personalisation Departures: the caption under the
  picture ("Départs · Rouge, bande sur fond clair") is useless: remove it.
- W146 (owner) Generate ALL possible backgrounds in the customisation: for
  example the light yellow background or the band with light yellow are
  missing (options with no theme are hidden since 61-76). Every colour x
  background x band combination should exist as a theme.
- W147 (owner) The size of the "save the detected changes" popup (floating
  bar) is never the same: the same component must be used everywhere.
- W148 (owner, screenshot) Calendar view still broken on desktop: it shows
  the Departures "Comme les départs" customisation card, clipped at the top,
  next to an empty panel.
- W149 (owner, screenshot) Fleet versions table: display bug (the "Toutes
  les versions (3)" disclosure and its rows overlap / misaligned, the open
  row's detail not aligned), and the rollback (downgrade) button should be
  available directly in the view, not inside the toggle.
- W150 (owner, screenshot of the Fleet Access card) These last two options
  ("Personne invitée / Ajouter un co-gestionnaire" and "Nouveau propriétaire
  / Réattribuer") are very ugly (two stacked form rows with a wide select and
  a heavy button); the reassignment should rather be a button next to the
  owner (in the owner row). ("rétribution" in his message read as
  réattribution.)
- W151 (owner, screenshot) Airline editor, aircraft-type sub-rows (Air France
  expanded): small display bug: the type rows' cells do not line up with the
  airline row (the row backgrounds stop short, leaving a pale block at the
  right; the ⋮ menu column is not aligned with the parent row's; some rows
  show "Utilise celle de la compagnie" wrapped on two lines while others show
  the picture).
- W152 (owner, screenshot) On mobile the Location map is still not full
  screen. Note: the screenshot's status-bar clock reads 16:54, the same
  capture as the round 9 one (before plan 61-88, which was deployed on
  2026-11-07 at 21:37 UTC); a fresh screenshot of the deployed version is
  needed to tell whether 61-88 changed anything. Grey bands: the status-bar
  strip at the top and the strip under the tab bar (above Safari's floating
  toolbar).
- W153 (owner, fresh iPhone screenshot 12:24, deployed version)
  Personalisation > Looks spéciaux on phone: the panel is broken: the row's
  text column is squeezed to about 60 px (the "Compagnie" tag, the name
  "French Air Force", the call sign and "Jaune, plein" break letter by
  letter) because the "Modifier" and "Retirer" buttons sit inline beside it
  (the Modifier link was added in plan 61-79). Stack the actions under the
  text or move them into a row menu on phone.
- (owner may have more; not confirmed done.)

## Round 10 grouping (D48)

The owner finished his round 10 feedback (W142-W153) and asked for a detailed
audit of visual bugs, improvements, performance and end-to-end workflows
(three read-only agents: audit100, perf101, workflows102). Plan: group his
items with the audit findings into plan 61-89 (straight fixes) and further
plans after the audits report; W146 (all theme combinations) needs an
investigation of how themes are produced before it is planned.

Straight fixes: W142, W143, W144, W145, W147, W148, W149, W150, W151, W152
(needs a fresh iPhone capture), W153.
To investigate first: W146.

- W154 (owner) The opening animation is not shown "exactly everywhere as we
  said": he expects the splash at the opening of the site (each time he opens
  it), not only on the very first visit or after a stylesheet change (the
  61-82 rule skipped it whenever the stylesheet came from the cache).
  Decision: show it once per browser session, at site opening, whatever the
  cache state; skip on in-session navigation, no JS, reduced motion keeps the
  static variant.
- W155 (owner) In general the pages do not seem to be preloaded: navigating
  between pages should feel instant. To be shaped with the performance audit
  (what is possible given authenticated, non-cacheable pages and iOS Safari
  without Speculation Rules: prefetch of tab destinations on touch/hover,
  warming of static assets and images, view-transition continuity).

## Audit 2 decisions (D49), owner answered

The owner accepted the whole proposed order (audit100 visual/UX 33 findings,
perf101 performance, workflows102 end-to-end) and the splash stays as is
(no shortening: it keeps its current ~2 s).

Plans (batch 14): 61-89 one SaveBar component; 61-90 Flights and empty
states; 61-91 Personalisation (calendar, matrix, caption, looks rows);
61-92 Fleet and Users; 61-93 Location, accessibility, navigation naming and
overflow polish; 61-94 performance quick wins; 61-95 splash at every session
opening, page preloading and session-expiry feedback.

## Coverage check of batch 14 (owner asked: does the plan cover every point?)

Owner W142-W155: all assigned (61-89 W147; 61-90 W142 W143; 61-91 W145 W146
W148 W153; 61-92 W149 W150 W151; 61-93 W144; 61-95 W154 W155) EXCEPT W152
(Location phone map full-bleed, still open: moved to a dedicated plan 61-93b).
W146 (all look combinations) is large enough for its own plan, 61-91a: a
server-side theme catalogue with all 5 colours x 3 backgrounds x 3 stripe
states (45, today 18) rendered for the frame, expand-only, live frame
unchanged; the UI part stays in 61-91.

Audit 2 findings F01-F33: all assigned except F22 (Home banner/greeting
spacing, now 61-93), F26 (splash dismiss when ready: owner decided to keep
the current duration) and F33 (/devices/<id>/update 404: now 61-92).
Workflow findings: all assigned to 61-90..61-95 except the radius field
showing 999 until Save (now 61-93) and two missing features: rename a frame
and a Flights sort (owner decision pending).
Performance: P01-P11 and P16 in 61-94; P12 (backdrop-filter cost) and P14
(bfcache) need a real phone; P13 (precompressed static in Caddy) is deploy
config; P15 (CSS split) after P01+P02.

Owner decision on the two missing features: both added. Rename a frame: a
name field on the frame page for the owner and administrators, saved through
the common SaveBar (plan 61-92). Sort in Flights: by date, airline or
direction, like the Airlines collection (plan 61-90). Radius display clamp
and F22 go to 61-93, F33 to 61-92.

## Decision D50 (look themes, W146), owner answered

Investigation themes91a: 45 combinations, 22 have a theme, 13 readable ones to
create (all yellow stripes get black text inside the band; 31 themes in
total), 10 combinations cannot exist (Full background + full stripe, Soft
background + soft stripe: stripe invisible). Owner chose option A: those 10
stay visible in the selector but greyed with a reason ("same rendering as
without stripe"), no extra theme. Plan 61-91a: generate the catalogue with a
(colour, background, stripe) builder keeping the 18 historical ids frozen,
add the 13 new ids after them, black text in yellow bands (portrait and
landscape renderers), cache bounds raised to 4 x number of themes, 13 new
golden cases without touching the 18 existing hashes, contrast test over the
catalogue (floor 2.7). Yellow Full/Soft-stripe and Soft/Full-stripe have a
stripe contrast of 1.12 (nearly invisible): to validate on the real panel.
Report: scratchpad themes91a/ (planches, report text in the hand-back).

## Round 11 (production review after PR #310, 2026-11-08)

- W156 Flights: the sort select should reuse the Airlines collection filter
  design (it is a native select styled differently from the chips).
- W157 Personalisation (look sheet): the segmented tabs (Fond / Bande
  diagonale) have labels that are not centred inside their pill (swatch and
  label sit off-centre, uneven cells).
- W158 Personalisation Calendar: the look popover is still broken/clipped on
  desktop; the owner wants a dedicated page like the special looks instead of a
  popover.
- W159 Location: typing a city or address keeps the airport suggestions until
  Enter; airports and places must be one grouped search that updates as you type.
- W160 Location (night mode): the unsaved-changes bar over the map is
  unreadable (light glass, pale text).
- W161 Fleet firmware versions table deserves a nicer design.
- W162 Users: the Active quick switch renders broken (misshapen knob, wrong
  colours, mixed states across rows) after the in-place switch change.
- W163 Airlines collection (type rows): "Utilise celle de la compagnie"
  overlaps the views count and the actions column is misaligned (dark block at
  the right), after the type row alignment change.

## Audit 3 and design-system decisions (D51)

- Third audit (visual 29 findings, performance 26, workflows 272 with 14 partial,
  0 failures) published as an artifact; reports in scratchpad `audit3/`.
- D51 (owner, "Oui ! ... pas seulement de créer la page, mais aussi de s'en
  servir pour corriger certains points de l'audit et homogénéiser l'interface"):
  build an admin-only "Components" reference page showing every shared UI
  component in all its states, light/dark, EN/FR, with one geometry and
  contrast browser test, and USE it to replace parallel variants (switches,
  selects, segmented controls, chips, buttons, cards, tables, dialogs) by one
  component each, fixing the audit-3 visual findings that come from
  inconsistent components (V03, V04, V06, V07, V26, V29 and related).

## Round 12 validation and remaining audit points (D52)

- Owner validated the production build of PRs #310, #312, #313 ("tout est ok").
- D52 (owner, "Traite tous les points restants"): treat every audit point left
  open, including those previously set aside as by design: V15, V19, V22, V27,
  V28 wording, offer of the nearest airport on phones, /ui-theme and /ui-lang CSRF,
  the naming glossary, tinting the Safari bands around the Location map, and all
  performance items not yet done (P07, P08, P09, P12, P13-P15, N04, N05, N07-N09).
  The splash duration stays unchanged (earlier decision). The Home greeting is
  handled in a separate session.

## Round 13 (production review of the Home title, 2026-11-09)

- W165 Fleet (State card, desktop dark): the state card text sits flush against
  the card's left edge and is clipped (no inner padding); the header actions
  ("Ouvrir la vue personnelle", "Renommer") float on their own row. To rework.
- W166 Home hero: the round "Rename frame" pencil next to the frame name is too
  large for the title; make it a small, quiet icon (still a >= 44px hit area).

## Round 14 (production review of round 14, 2026-11-09)

- W168 Rename frame: clicking "Rename" (Fleet header, and the Home pencil) takes the
  person to the console's settings page. A normal user should stay on Home: rename
  in place (small dialog or sheet with the field and Save), and Back must return to
  where they came from (Home), never land in console settings. Everything else in the
  round-14 review is ok.
- W169 Location on iPhone (Safari tab, dark theme, iOS 26): the two dark bands above
  and below the map are still there after the strip/tint change. Probable cause: the
  strips use the theme's dark secondary colour, while the visible map tiles are light,
  so Safari tints its bars dark. To fix: tint with the tile ground colour (light, in
  both themes) and ship temporary `?bands=` variants for on-device comparison.

## Round 15 (iPhone map bands, 2026-11-10)

- W170 Location on iPhone: none of the four `?bands=` variants removes the two bands in
  a Safari tab (Safari's own bars). From the Home Screen icon it is worse: the bars are
  bigger and the tab bar moves up, only on the Location view. Decision: revert the
  iPhone tint experiments (Home Screen web-app meta tags, edge strips, `?bands=` variants,
  map-ground page background, theme-color changes) and accept Safari's bars in a tab;
  the full-bleed map under Safari's bars cannot be achieved from the page (limit of
  iOS 26 Safari). W152 is closed as a platform limit.
- Superseded: the cause is the fixed map container background; fix tried in 61-104. W152 is not closed as a platform limit.

## Round 16 (production review after PR #318, 2026-11-10)

- W171 Location on iPhone: the two bands are still present after the map container got
  the tile ground colour (PR #318). Next try: take the map out of `position: fixed`
  (plan B), and check the `.place-boot` loading placeholder.
- W172 Flights (and any tab strip): remove the counts inside the filter chips
  ("Tous 18190 / Départs 7529 / Arrivées 10…") that serve no purpose; on a phone the
  last chip is cut off.
- W173 The animation of the Style page's tabs (look views entering) is missing on the
  other tab strips; one consistent tab content animation everywhere.
- W174 The page-opening animations are missing on many pages; every page should have
  the same opening animation (respecting reduced motion).
- Owner asked for another full audit (visual and UX, performance, workflows).
- W171 update (iPhone, light, after PR #318): the top of the map now goes under the
  status bar; the bottom band remains (map ends about 8% above the screen bottom, a
  flat page-background band below the tab bar). Plan B (non-fixed map extending
  under the bottom bar) is in plan 61-105.
- W175 Location, airport choice: on a phone the map is still too little visible while
  choosing an airport (card, runway chips, the unsaved-changes bar and the tab bar
  cover about 60%). D53 (owner): option 1, "compact sheet": airport name, runways and
  Cancel/Save in one card (about 130px), no separate unsaved-changes bar, about 55%
  of the screen left to the map. To be done in plan 61-106 after 61-105.

## Audit 4 decision (D54)

- Owner: "je veux que tu traites 100 % de l'audit": every finding of audit 4 is treated:
  23 visual (W01-W23, including those previously left by design), 5 workflow partials
  (CSRF on six routes, rename return_to scope, Flights search history, no-JS image
  load, broken-pipe log noise, refused special-look reload), and every open performance
  finding (R01 shared place-search limiter, R02/R03 history and collection caches with
  single flight, R05 editor type templates, R07 deferred map init, R10, R14 CSS split,
  R15 Flights duplication, R17 cheap freshness token, R18 empty 404 for asset paths,
  R22 splash preload, R23, R28). The splash duration stays unchanged.

## Remaining audit-4 points (D55)

- Owner: "Traite les cinq points restants": R10 and R15 (Flights card and table
  duplication, content-visibility with deterministic card heights), R23 (bfcache with a
  pageshow session check, keeping the sign-out guarantee), R07 (split place-map.js, the
  map evaluation cost), R14 (go further on the stylesheet split to the 20-25 KB gz
  target). Brotli stays an owner deploy decision (Caddy build).

## Round 23 (owner, Companies tab and last two polish items)

- W176: Companies page, the card shows a double box for the flights (a box inside the
  card) and the aircraft pictures are now too small.
- W177: Companies page, tapping a tab of the Companies tab strip reloads the whole page
  with the page-opening animation replayed, which breaks the app feel; the other tab
  strips do not do it. Tab changes there must switch in place like the others.
- W178: The page loading animation: its animated frame is too big, the owner pictured
  it smaller. The splash duration stays unchanged.
- W179: The logo, above all the page icon, is still orange and no longer matches the new
  design; change its colour (mockups first).
- Location top band on iPhone (Safari tab, address bar at the bottom): still present
  after the fix that offsets the map by the top safe-area inset; to be investigated by
  comparing with the last good build, separately from plan 61-110.
- Queue after plan 61-110: plan 61-111 for W176-W179 and the Location top band.

## Round 24 validation

- Owner: everything is fine except Location (W176-W178 confirmed on device; the graphite
  logo with a night-mode favicon, W179, confirmed on device).
- Location top edge on iPhone (Safari tab and Home Screen app) is still not right after
  plans 61-111 and 61-112. The owner opened a local session with the iOS simulator to
  debug it on real WebKit; the result will come back as a branch.
- Brotli stays an owner deploy decision (Caddy), left aside for now.

## Round 25: audit 5 fixes (D56)

- D56: all 84 audit-5 findings are treated, in lots A to D, by sequential executors.
- Lot A (61-115) and lot B (61-116) merged and deployed; owner validated all tests of both lots.
- Owner decision: keep the role-change confirmation on Users (it supersedes the "no confirmation" line of the UI spec).
- Open: X03 (Users table wrapping) needs a design choice; lot C and lot D follow.
- Owner decision (X03): Users table option A, e-mail addresses on one line with an ellipsis (full address in the person's detail), so every row has the same height. Goes into lot D.
