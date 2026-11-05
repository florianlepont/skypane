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
