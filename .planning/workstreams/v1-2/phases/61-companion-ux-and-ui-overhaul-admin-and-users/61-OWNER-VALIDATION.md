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
