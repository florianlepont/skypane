# Page patterns

What each page is made of today. Components are in `components.md`, navigation in
`navigation.md`. Page code is under `companion/pages/`, area CSS in `companion/static/style-*.css`.
Every page: one `h1`, sections as `section-label` + group (or a `.page-section` card for free
content), complete and correct with scripts blocked, 360px without horizontal scroll, EN and FR.

## Home (`pages/home_page.py`, `home_state.py`, `home_flight_card.py`, `home_pills.py`, `style-home.css`)

One column of blocks, built for three states: online, sleeping (quiet hours or screen off) and
offline (no contact).
- **Title block** (`home_state.py`): the `h1` is the frame name (32px phone, 44px from 700px) with
  no rename control (renaming lives in Account and the Fleet header; `pages/home_title.py`); under it the status dot and its word, then the next update
  sentence ("Next update in 12 min", or "Last contact 3h ago" for a frame that lost contact) ending
  with the cadence "i" button inside the sentence (held with the last word, so it never wraps under the text). The dot halo pulses and stops under reduced
  motion, at rest after a minute idle and while a dialog is open.
- **Flight card** (`home_flight_card.py`): the newest archived picture beside a direction badge,
  callsign, airline, route and type ("ORY → TLS · A320") and a live "Detected 4m ago". A thin ring
  outside the picture fills with the elapsed share of the frame cycle and flashes green once at
  100% (drawn by the server, repainted by `relative-time.js`; shown only for an online frame). A
  landscape frame stacks the picture over the text on a phone. A frame with no picture keeps the
  empty-picture box.
- **Pills** (`home_pills.py`): Screen (a whole-pill switch), Quiet hours (a link pill, 44px tall at
  every width, opening the quiet-hours dialog), the place (leading to Location) and the battery
  (with the hedged charging pill and a word for a low level).
- **Statistics card**: a Day / Week pair of native radios with both panels in the markup. Day: the
  total split into departures and arrivals, a timeline of the hours (departures above the axis,
  arrivals below) and the busy hours; Week: seven bars scaled to the tallest with today marked;
  facts such as "1 new airline" (singular and none handled). No flight at all is the card at zero.
- **Recent flights strip**: a scroll-snap row of 3:4 tiles (picture, caption such as "Arrival · 12
  min"), 5:3 for a landscape frame; a heading row with a 44px link to Flights; empty state when
  none. A new flight slides in; the strip is a region the 45-second refresh swaps.
- A notice or attention row sits above the blocks (amber/red frame: figures, a tip, a mailto to the
  first active administrator; `home_notice.py`). The Detection and Frame groups, the battery dial
  and the old hero are gone.
- Quiet-hours dialog (`settings/quiet_hours.py`): preset cards Night, Day, Always on; Start and
  End time tiles; a 24-hour dial driven by `value-controls.js`. The dial arc is server-drawn
  (correct without script); only the two handles are script-gated; handle hit area `inset: -12px`
  (about 45px measured, set above 44 on purpose because the handle lands on fractional pixels). Its
  note links to Location ("Location" / "Lieu") with a 44px tap area. It is a sheet with a field,
  so it lifts above the keyboard.
- Live: `freshness.js` refreshes regions in the background; `relative-time.js` ticks ages;
  `motion.js` counts numbers up once. The ambient loops rest when the page is idle
  (`html[data-ambient="rest"]`).

## Flights (`pages/history_page.py`, `style-flights.css`)

- Under the title the shared filter controls (`ui_filter.controls_html`): search, sort and an info
  button on row 1, All / Departures / Arrivals chips with their counts on row 2 (they scroll on a
  phone), then the count line ("34 of 148 flights"). Search, sort, chips and "Load more" run on
  the server (`?q`, `?kind`, `?sort`); the chip counts follow the search.
- Phone: one glass group per Paris calendar day (section label "Today", "Yesterday", "3 Sep"); a
  row is a 56x36 thumbnail (a 44px-tall picture control), the airline over one route line (an
  arrow-over-runway icon for the direction, two airport codes, a chevron), and the time (bold) over
  its age. No "departing / arriving" wording is drawn: the direction is an `aria-hidden` icon plus a
  visually hidden word. A row with no route shows only the direction.
- Desktop (from 960px): a glass table led by the thumbnail (72x46, the row's picture control),
  columns Flight (airline over call sign), Route, Aircraft ("Avion"), When; the header row is kept
  for screen readers and not drawn; day separator rows. The aircraft type appears only here.
- Thumbnail rule: a render counts only if archived at most 90s before and 10s after the
  detection (`GALLERY_MATCH_BEFORE_S`, `GALLERY_MATCH_AFTER_S`); the flight stores the archived
  render's name; otherwise the airline illustration; otherwise the plane icon.
- The picture opens the opaque lightbox dialog. Pull to refresh on a phone's list
  (`motion.js`); the page opens with the standard opening, at most the first three days enter.

## Location (`pages/place_page.py`, `style-place.css`, `place-*.js`)

- The map fills the page (vendored Leaflet 1.9.4 in `companion/static/vendor/`, OpenStreetMap
  tiles, Nominatim search). One search field floats at the top (an airport code or name picks an
  airport, anything else is geocoded). One panel carries the rest: a bottom sheet on a phone
  (compact, capped height), a card at the left of the map from 960px.
- The map is dark in Dark and in Auto-dark (see `tokens-and-theming.md`), so the runway line
  reads; Light keeps the plain tiles.
- Mode switch "What the frame follows": **By position** (default for a frame with no setting; French
  "Par position") and Airport. Airport mode shows the runway choice (runway cards whose pills are
  catalogue pills); By position shows the pin readout and detection radius.
- Round 44px icon buttons, named by `aria-label` and tooltip: locate ("Use my position") and
  "Show all of France" (a globe, opaque with a visible edge). After locating, no visible text
  reports the position: the pin moves and a visually hidden `role="status"` line says it; errors
  keep a visible message. An "i" opens the map credits. Tap the map to place.
- Save and Cancel are the shared Save bar (page mode, `reveal_on_change`), docked on desktop and
  inline in the sheet on a phone. No-script floor: the details block with plain coordinate fields
  and one native POST (`action=save_place`); choosing an airport is a GET (`?airport=`, `?q=`).
- iPhone only (`navigator.standalone` exists): the map runs under the status bar and the
  bottom toolbar (`--place-lead` / `--place-tail` 80px, scroll lock, no added frost); the app
  bar chrome is forced to the light palette over light tiles; the More panel's scrim covers the
  map lead and tail. Details: `style-place.css`. Test: `test_browser_place_pins.py`. The
  foreign-frame marker spans the page above the floating app bar here.

## Style (`pages/personalisation_cards.py`, `settings/*`, `style-display.css`)

- Four tabs (`data-tabs="display"`): Departures, Arrivals, Special looks, Calendar. Each tab
  has its own route and document title; the calendar look and the add/edit special look and
  calendar-connect screens are sub-pages with their own title and a page-mode Save bar.
- The look picker fits one 360x740 screen above the tab bar without scrolling: a 31-theme
  swatch catalogue (colour, background, stripe; swatches 32px in 44px targets), segmented
  controls for background and band, and a preview. The light-yellow tile has a 3px darker edge
  (`--color-yellow-tile-edge`) so its shape shows; no other tile has one.
- Previews are content-addressed: one URL per picture, `private`, `immutable`, cached for a year, so
  switching a tab fetches no unchanged preview and a stale or missing address never pins an image.
  The address carries a stamp of the artwork a scene draws, so a replaced picture changes it, and
  previews draw uploaded illustrations.
- A tab or link press with an unsaved change asks first in the question dialog ("Leave without
  saving?": two equal answers and a cross; see `components.md`), on the bottom bar, the desktop
  sidebar, a link in the open More sheet and the browser's own back. Without script the tabs are
  plain links. Wake interval slider and wake settings live in `settings/wake_interval.py`.

## Airlines (`pages/airline_collection_page.py`, `airline_types_fragment.py`, `style-airlines.css`)

Read-only, and different by role.
- **A user** sees the airlines the frame they opened has seen, nothing else (one frame at a time,
  never another frame's sightings); the purpose line reads "Airlines your frame has seen". No dimmed
  "not yet seen" cards, no progress bar, no All / Spotted / Not yet seen chips; a frame with no
  sighting shows only the empty state. A fleet-wide name or picture shows on an airline the frame
  saw. Unidentified prefixes are never shown to a user, with no resolve form or route.
- **An administrator** on the personal page sees the same per-frame collection; the fleet-wide
  view is the Editor (below).
- A grid of glass cards (artwork on a neutral plate, name) with a **filled rarity pill** on every
  card (tinted by `--rarity-tint`, a word as well as a colour), and the shared filter controls (the
  same module and placement as Flights): a filter field, a sort icon menu (Most seen, Rarest,
  Latest, A to Z; Rarest is the default) and the rarity legend behind the info button on row 1;
  All / With artwork / No artwork / Seen this month chips with counts on row 2 (script-driven, so
  hidden without a script), then the count line ("21 of 36 airlines") and the next-badge goal line.
- Detail sheet: three facts as hairline rows under the picture and the rarity pill, the round
  opaque cross at the top as the only Close (the foot strip is hidden), no inner scroll on a phone
  or desktop; aircraft types load lazily as a fragment. A newly seen airline's card plays an unlock
  flip once (`motion.js`, tracked in `localStorage`; no animation if storage fails) and carries a
  "New" pill in its corner.

## Editor (`pages/airlines_page.py`, `airline_table.py`, `airline_rows.py`, `airline_missing.py`)

Administrator only, **fleet-wide**: the airlines seen by any frame, one registry of names and one
directory of artwork for the whole fleet (a name or picture given on one frame shows on every
frame). Console label "Airline editor", bar label "Editor".
- Order: the unidentified prefixes (first, compact), then the **Missing
  illustrations** section, then the Airlines table. A filter bar with a search field and five wrapping chips with counts: All,
  Unidentified, Missing illustrations, Seen, Not seen yet.
- **Unidentified prefix:** one compact row on a phone and desktop: the prefix, an example callsign,
  the count and last seen, and one **Name it** button (a sheet on a phone, a centred card on
  desktop) that posts to the resolve route. There is no Ignore. When the suggestion service is on, a
  cached suggestion shows as a Suggestion tag with the proposed name in bold, an Edit link and a
  round 44px check (a real form), never blocking the Name it flow; a pending prefix says "Looking
  for a name".
- **Missing illustrations · N:** a sibling of the two tables: the same small label (`.airlines-label`,
  13px 600, 70% ink, 16px indent) lifted above its list, no 22px heading and no caption sentence
  (the sentence stays in the empty state); the section keeps `id="airlines-missing"` and is named
  by the label (`aria-labelledby`); 24px between blocks. N counts rows, one per airline x aircraft family without a picture
  (a family is one of the picture slots, "Other" for rare designators). One solid list surface; each
  airline has a small header (name, prefix, "No artwork yet" or "<family> already done", "· n to
  do") and its rows: a dashed 44px slot, the family, the designators and views, and a 44px
  icon-only add button (a picture with a plus, 44px, tooltip "Add artwork", aria-label "Add an illustration for <airline>, <family>") that opens the add dialog with the family in its chip. An airline with
  no sighting and no artwork has one "Type to choose" row whose dialog asks the type first; one with
  art and no sighting is not listed. The "..." menu (Rename, Reset or Delete my name) is in the
  header of an airline that has no row in the table. After an upload the page reloads and the row is
  gone; an empty list says "All illustrations are in place" with a check. The chip counts the same
  rows and "All" adds the unidentified prefixes and the airlines of the table.
- **Airlines table:** only airlines with artwork. The airline's name is plain text with its
  default type's picture; Rename (a dialog), Reset to the original name and Delete my name are in
  the "..." menu (even padding, 44px items, Escape closes). The chevron opens one row per aircraft
  type, loaded lazily and quickly, with no overlap on the next row; a type row is labelled with its aircraft family name (interface font, 16px/600, no "(famille)"; focusable, the codes seen are a mono 14px tooltip on hover and keyboard focus beside the name, past the star, 320px wide at most; in a card they are a 13px secondary line, two lines then an ellipsis, a tap on the name expands it), the default type is a text-free star with an accessible name and its own tooltip, and it has one upload entry, an icon-only 44px outlined button (a picture with a plus for Add artwork, a picture with a pencil for Change artwork; aria-label names the airline and the family, tooltip on hover and keyboard focus, to the left of the button in the table; in a card it sits right of the thumbnail block with the menu under it) and a
  menu with Set as default type and Delete the artwork (only for an uploaded picture). A refused
  name or picture reopens its dialog on that row.
- Artwork has no "Revert to default" and no separate Customise: one upload entry per type.

## Fleet (administrator: `console_fleet_view.py`, `fleet_page.py`, `pages/fleet_*.py`, `style-admin.css`)

- **List** (`/fleet`): the page opens on the list of frames, never on the first frame; from 1200px the pane beside
  the list is a neutral "Select a frame" state (icon, short heading, one muted line, no frame data, no
  selected row) until a row is chosen, and the list's title is the only `h1`. A list
  panel with the title, "Add a frame", a search field from 8 frames, groups Live / Waiting to be
  paired / Retired with counts, and a System row; each row is one link (status dot, name, state and
  owner, last seen, chevron; the selected row is `aria-current` and is scrolled into view in its
  own column). From 1200px the list is a left column beside the frame; on a phone a bounded chip
  switch ("All frames (N)", the frame in view first, at most 8 live frames) replaces it. A pending
  or retired frame is reachable only from the list and has its own page (see below); an unknown
  `?frame=` shows the list with a not-found note. Scales to 30 frames.
- **Frame page** (`/fleet?frame=<id>`): a header with the `h1` name, the state line and two 44px
  icon buttons (personal view, Rename); then a State section of **three equal tiles** and the
  Settings and Access sections stacked in one column of equal cards (on a phone, three sticky
  anchors State / Settings / Access, 44px, mark the section in view on a solid bar whose gap above (safe area and app-bar drop) is painted too; from 960px the anchors are
  hidden):
  - **Connection** tile: a verdict and two lines, "Last check-in <age>" and "Next wake <clock>"; a
    plain block, not a link, no Details mark. A frame that never checked in says so once and still
    has its tiles.
  - **Battery** tile: percentage and millivolts, a verdict and a sparkline of the 90-day series;
    links to the Battery page. A low level turns the tile to a warning in words.
  - **Firmware** tile: the running version in mono and the update headline; links to Versions.
  The tiles' state is spelled out, never colour alone.
- **Battery page** (`?frame=<id>&view=battery`, administrators only): a Back link to the frame and
  the one `h1` "Battery". The card has a 270 degree gauge with the percentage as the hero and a tick
  at 20%, a status pill with the verdict ("Level looks normal", "Level is low"), the voltage once,
  one "Last reading" line, a Percentage / Voltage segmented switch (two 44px radios, arrow keys),
  a chart (90-day daily averages, y-range fitted to the data, end marker, the low-battery line only
  when the data comes near it, otherwise a caption) and the readings table shown open under it
  with a "Readings (N)" heading (Time, Voltage, Level; the latest row tagged), never behind a
  toggle. The page takes the whole page column: from 720px of card width the gauge and the facts
  (pill, voltage, last reading) share one header row, from 960px the chart is 360px tall (about
  190px on a phone). Too few readings shows a dashed note and keeps the gauge. This page replaced the Health
  view; the old Health addresses are gone and answer the ordinary not-found page. The user's own Home battery pill is separate.
- **Versions page** (`?frame=<id>&view=versions`): the Update panel. One card per state (up to
  date, update available, scheduled, installing, failed) with an icon headline, the version in
  mono, the release age, the release note cut at two lines and one action on the right (full width
  under the text on a phone); a rollback notice is a bordered warning card above it. Under it a
  "Versions" label and one card of flat rows (status dot, mono version, a Newest or Running
  catalogue pill, date and age, notes behind one native disclosure, a quiet underlined Roll back).
  Install and Roll back ask once in the shared dialog (a card from 700px, a bottom sheet below,
  built by `update-question.js`); without script the form posts without `confirm` and the server
  answers with one confirmation card (the question, what will happen, Cancel beside Install). The
  standalone `/update` page redirects to the frame's Versions page when it can.
- **Settings and Access:** Settings are edited inline and saved through the Save bar. Access is one
  compact section: the owner with Reassign, the co-managers, one Add control and Retire with its
  one-line hint (no helper sentences; the long wording lives in the confirmation dialogs). The
  personal side's Manage access dialog is a separate surface.
- **Retired and waiting frames:** a retired frame's page shows only its action: "Re-activate" with
  a sentence that the frame shows its pairing code at its next wake (up to 24 hours) unless Reset is
  pressed, and a header "Retired · Belonged to <owner>"; a pending frame shows "Pair frame". The
  frame itself shows "This frame was removed from SkyPane. Press Reset to set it up again." on every
  hardware type. A refused pairing code on the Add a frame page is one tinted alert (icon, bold
  sentence, validity line), and the page tells a frame that shows no code to press Reset.
- **System** (`/fleet?view=system`): a full-width page with the standard header (`h1` "System" and
  its purpose line, "The server behind every frame. Visible to administrators."), no frames list, no
  chips, no Add button. A warnings banner (a card with pills and the sentence), then **compact
  tiles** (2 columns on a phone, 3 from 960px, 44px, the chevron at the end of the label row):
  Server, Data sources, Identification, Route directories, Answered by, Off-box backup (left out
  with its block when no backup marker is configured). Each tile is a link to its block below on
  the same page; then one glass group per topic. The two route topics show each directory (VRS
  standing data, adsbdb) as its own card: role in the small line, name in bold, "Reachable" / "Not
  reachable" / "No request yet" at the right, last answer and lookups of the last 24 hours; and
  "Answered by" with the share of flights each directory answered over 7 days. The page footer
  links to `/components`.

## Users (`pages/users_page.py`, `style-admin.css`)

- Header: the title and a 44px dark "+" button beside it on a phone (its label "Invite a user" is
  its accessible name; a wide screen shows the label and hides the icon).
- Below 79.5rem one card of rows, each person one row with a divider: avatar, the address on one
  line with an ellipsis at every width, a status pill, then "Role · frames", the Active switch and
  the "..." menu. The role is changed from the person's menu ("Make administrator" / "Remove
  rights", never for yourself or the last active administrator), which opens the role confirmation.
  From 79.5rem a glass table: the role is a bordered select with a chevron (still a real native
  `<select>` with a no-script Save), the frames and last sign-in cells show.
- The **invite sheet** is a short compact dialog (labelled address field, one Administrator
  checkbox, Cancel and Invite) that stays above the keyboard. The result is an "Invitation ready"
  dialog with the Auth0 password-change link shown once (Copy writes a message with the link and
  the address to open; Done removes it and a reload never posts again); a failure keeps the local
  invite and offers Try again. Re-inviting someone who has not signed in renews the link for 24
  hours. The role and delete confirmations have even margins and one sentence.
- The Active switch acts in place with a toast.

## Audit (`pages/audit_page.py`, `style-c-lists.css`)

One glass list. The category filter is a single line on a phone that scrolls sideways (the
current category filled and opened into view, the right edge faded); from 700px it is the full-width
track. An opened event shows its details in a tinted panel, label left (a 6rem column, 80% text
ink) and value right.

## Account (`pages/account_page.py`)

Groups: My frames (one row per frame: the drawn portrait frame, name, owner line, an Owner or
Co-manager pill, a status dot with a name and the last-seen word, never a battery percentage and
never the hardware type; two 44px icon buttons at the row's right, "Manage access: <frame>" (a key)
and "Leave frame" (a door), named by `aria-label`; the last row "Add a frame"), Identity (Email,
Role; a co-manager sees "Co-manager of N frames"), Preferences (Language and Theme segmented
controls), **About** (a Credits row, for users and administrators alike) and Sign out as a group of
its own. Leaving a frame opens a dialog with "Stay on this frame".

## Sign-in, Credits and error pages

- `login_shell` (`ui_shell.py`) is a separate minimal document with no nav: a glass card whose mark
  sits at the start of the heading line, one Sign in button, then **one small muted centred
  first-visit line** (caption size, secondary ink, plain card only), then Credits. A real error
  state, sign-in cancelled returns 303. A page restored after the session ended shows the translated
  "session expired" toast (`session-guard.js`) and redirects to `/login?next=...&expired=1`. A refused
  pairing code is kept 2 minutes in the `sp_pair_code` cookie for one showing (`pair_code_cookie.py`).
- Credits (`credits_page.py`): reachable from Account's About group and from sign-in; signed in, the page
  is drawn with no navigation at all (`page_shell(bare=True)`: no sidebar, tab bar, space switch or frame
  button) and a chevron "Back to Account" link above the title; anonymous, "Back to sign in" at the bottom.
- **404:** an "empty frame" drawn inline (an SVG in the page ink, decorative, 260px at most) over one
  muted caption ("Nothing hangs on this wall.") on a panel, the same for every caller; status stays
  404 and the back link goes to the frame home, Account or sign-in as the caller needs. 403 and 500
  keep one line and a one-row glass `.error-actions` group.

## Components page (`/components`, administrator)

The living catalogue (`pages/components_page.py`): one section per family in every state,
guarded by tests (see `components.md`). Includes the page-name table, the motion index, the
foreign-frame marker, the scrolling chip row and the short dialog.

## Opening splash

"Cadre" splash (`splash-boot.js` decides before first paint, `splash.js` plays): once per
browser session, hard cap about 3.2s, real preload progress, no splash without scripts or
session storage, reduced-motion fallback. Navigation inside the session never replays it.
