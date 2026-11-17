# Page patterns

What each page is made of today. Components are in `components.md`, navigation in
`navigation.md`. Page code is under `companion/pages/`, area CSS in `companion/static/style-*.css`.
Every page: one `h1`, sections as `section-label` + group (or a `.page-section` card for free
content), complete and correct with scripts blocked, 360px without horizontal scroll, EN and FR.

## Home (`pages/home_page.py`, `style-home.css`)

- `h1` is the frame name with a rename pencil (`pages/home_title.py`). The greeting title is
  gone (JS, CSS and strings deleted).
- Order: notice or attention row (amber/red frame: figures, a tip, a mailto to the first active
  administrator; `home_notice.py`), the frame-state card (current picture beside the state word
  and next update, cycle ring, status dot), the Detection group, the Frame group, Recent
  flights, the quiet-hours dialog.
- Detection group (`detection_summary.home_card_html`): one link row naming the active mode,
  "Position mode", "Airport & runway mode" or "No place set", leading to Place.
- Frame group: Screen and Quiet hours switch rows (quick switches posted with `fetch`, toast on
  failure) and the Battery row (`home_battery_row.py`: charge with a level word, thin bar,
  estimated autonomy only when honest, "Probably charging" while charging; every signed-in
  person sees it).
- Recent flights: one informational row per flight (plane chip turned by direction, callsign,
  detail line, age) and a "See all flights" link row; empty state when none.
- Quiet-hours dialog (`settings/quiet_hours.py`): preset cards Night, Day, Always on; Start and
  End time tiles; a 24-hour dial driven by `value-controls.js`. The dial arc is server-drawn
  (correct without script); only the two handles are script-gated; handle hit area `inset: -12px`
  (about 45px measured, set above 44 on purpose because the handle lands on fractional pixels).
- Live: `freshness.js` refreshes regions in the background; `relative-time.js` ticks ages;
  `motion.js` rolls the countdown and counts numbers up once. The ambient loops (dot breathe,
  picture glow, glint) rest when the page is idle (`html[data-ambient="rest"]`, `style-home.css`).

## Flights (`pages/history_page.py`, `style-flights.css`)

- Title row with a search field that opens from the title; a Departures / All / Arrivals
  segmented filter (no counts) and a sort menu. Search, sort and "Load more" run on the server
  (`?q`, `?kind`, `?sort`); counts stay at the whole history's.
- Phone: one glass group per Paris calendar day (section label "Today", "Yesterday", "3 Sep");
  desktop (from 960px): a glass table with day separator rows. One lead element per row: a
  44px target holding a 40px thumbnail with a direction glyph (nose up departure, down
  arrival), else a 40px plane chip.
- Thumbnail rule: a render counts only if archived at most 90s before and 10s after the
  detection (`GALLERY_MATCH_BEFORE_S`, `GALLERY_MATCH_AFTER_S`); the flight stores the archived
  render's name; otherwise the airline illustration; otherwise the plane icon.
- The picture opens the opaque lightbox dialog. Pull to refresh on a phone's list
  (`motion.js`); the page opens with the standard opening, at most the first three days enter.
- No detail row, no `flight-rows.js`: removed.

## Place (`pages/place_page.py`, `style-place.css`, `place-*.js`)

- The map fills the page (vendored Leaflet 1.9.4 in `companion/static/vendor/`, OpenStreetMap
  tiles, Nominatim search). One search field floats at the top (an airport code or name picks an
  airport, anything else is geocoded). One panel carries the rest: a bottom sheet on a phone
  (compact, capped height), a card at the left of the map from 960px.
- Mode switch "What the frame follows": My position (default for a frame with no setting) and
  Airport. Airport mode shows the runway choice; My position shows the pin readout and detection
  radius. A round locate button and an "i" opening the map credits. Tap the map to place.
- Save and Cancel are the shared Save bar (page mode, `reveal_on_change`), docked on desktop and
  inline in the sheet on a phone. No-script floor: the details block with plain coordinate fields
  and one native POST (`action=save_place`); choosing an airport is a GET (`?airport=`, `?q=`).
- iPhone only (`navigator.standalone` exists): the map runs under the status bar and the
  bottom toolbar (`--place-lead` / `--place-tail` 80px, scroll lock, no added frost); the app
  bar chrome is forced to the light palette over light tiles; the More panel's scrim covers the
  map lead and tail. Details: `style-place.css`. Test: `test_browser_place_pins.py`.

## Style (`pages/personalisation_cards.py`, `settings/*`, `style-display.css`)

- Four tabs (`data-tabs="display"`): Departures, Arrivals, Special looks, Calendar. Each tab
  has its own route and document title; the calendar look and the add/edit special look and
  calendar-connect screens are sub-pages with their own title and a page-mode Save bar.
- The look picker fits one 360x740 screen above the tab bar without scrolling: a 31-theme
  swatch catalogue (colour, background, stripe; swatches 32px in 44px targets), segmented
  controls for background and band, and a preview. A sub-tab switch with an unsaved layout asks
  first (round 36). Wake interval slider and wake settings live in `settings/wake_interval.py`.

## Airlines (`pages/airline_collection_page.py`, `airline_types_fragment.py`, `style-airlines.css`)

- A grid of glass cards (artwork on a neutral plate, name, rarity pill) with a filter: tabs
  All / Spotted / Not yet seen (`data-tabs="airlines"`), a filter field, a sort icon menu
  (Most seen, Rarest, Latest, A to Z) and a legend button. Two lines on a phone.
- Detail sheet: facts as hairline rows; aircraft types load lazily as a fragment. A newly seen
  airline's card plays an unlock flip once (`motion.js`, tracked in `localStorage`; no animation if
  storage fails).

## Console (administrator)

- Fleet (`console_fleet_view.py`, `fleet_page.py`, `style-c-console.css`): a frames list and a
  per-frame view whose blocks are glass groups: State, Device and version, Settings, Access
  (tabs State / Settings / Access on a phone, plain links `?frame=<id>&tab=<tab>`). The System view
  groups flight data, data sources, identification, backups and the unresolved-airline registry;
  its footer links to `/components`. Health, Device and Releases are folded here.
- Device and version panel (round 39, `update_page.py` helpers): "On the frame" summary with the
  installed version large in mono and a state chip (`pill_html` tone); one update card with a
  single primary Install; a flat version list of native `<details>` rows (dot, version, date, age,
  Installed/Newest chip, notes) with a ghost "Revenir" action. The standalone `/update` page
  keeps its older markup. Test: `test_browser_firmware_panel.py`.
- Users (`pages/users_page.py`, `style-admin.css`): a glass table from 79.5rem, cards below.
  E-mail on one line with ellipsis; the Active switch acts in place with a toast; a role change
  asks for confirmation; invite button under the title on a phone; the role select clears its
  French label at 360px.
- Airline editor and Audit log: the same table language; audit list is one glass group on a
  phone (`ul.audit-cards`).

## Account (`pages/account_page.py`)

Groups: My frames (one row per frame with the drawn portrait frame, name, hardware or owner
line, Owner or Co-manager pill, status dot, last seen; Manage access / Leave frame; last row
"Add a frame" with an accent chip, leading to the pairing flow), Identity (Email, Role; a
co-manager sees "Co-manager of N frames"), Preferences (Language and Theme segmented controls),
and Sign out as a group of its own.

## Login and system pages

`login_shell` (`ui_shell.py`) is a separate minimal document with no nav: a glass card, a real
error state, sign-in cancelled returns 303. A page restored after the session ended shows the
translated "session expired" toast (`session-guard.js`) and redirects to
`/login?next=...&expired=1`. A refused pairing code is kept 2 minutes in the `sp_pair_code`
cookie for one showing (`pair_code_cookie.py`). Error pages (404, 403, 500) show one line and a
one-row glass `.error-actions` group.

## Components page (`/components`, administrator)

The living catalogue (`pages/components_page.py`): one section per family in every state,
guarded by tests (see `components.md`). Includes the page-name table and the motion index.

## Opening splash

"Cadre" splash (`splash-boot.js` decides before first paint, `splash.js` plays): once per
browser session, hard cap about 3.2s, real preload progress, no splash without scripts or
session storage, reduced-motion fallback. Navigation inside the session never replays it.
