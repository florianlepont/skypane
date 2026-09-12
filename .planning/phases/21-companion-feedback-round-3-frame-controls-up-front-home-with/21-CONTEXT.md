# Phase 21: Companion feedback round 3 — frame controls up front, Home with three tiles, one Frame colours view, calendar tile, compact flights table, simple mode removed, artwork upload restored - Context

**Gathered:** 2026-09-12
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-PRD.md` — written from the developer's fifteen post-phase-20 feedback points and the developer's approval of the orchestrator's proposal for points 2/3/8, 4/5 and 6/7)

<domain>
## Phase Boundary

The companion web app (`companion/`) only — no server seam changes are expected (the theme fields, calendar fields, quick-toggle routes and rules routes all exist since phases 16–20). Six areas, all locked by the PRD:

1. **Frame controls up front** (CFG-19, D-01..D-05) — a shared "Frame" strip (Screen switch, Quiet hours switch, next update as the largest text) at the top of Home and Display; a state-only reminder link in the nav; Home rebuilt as strip → three phase-19 stat tiles → picture and recent flights side by side; the phase 20 single status card deleted.
2. **One "Frame colours" view** (CFG-20, D-06..D-12) — the four theme chip grids (departures, arrivals, calendar, rules) become one card: live preview left, four-row assignment radiogroup right, one chip grid for the selected row, "Same as departures" chips for arrivals and calendar, the rule list and add form under the rules row; `theme-preview.js` extended (ES5, no HTML sink); a no-JS floor that still saves every value.
3. **Calendar in one tile** (CFG-21, D-13..D-14) — status + URL field/connect button in one card; once connected a masked URL, a "Replace the feed URL" `<details>` link and a small grey "Disconnect" secondary button that still confirms.
4. **Compact Flights table** (CFG-22, D-15..D-16) — five merged columns that fit 1280 px in FR and EN; hex, ISO timestamp, runway and copy button in an expandable detail row; phone cards unchanged.
5. **Simple mode and the Health pause button removed** (CFG-23, D-17..D-18) — prefs/cookie/route/nav switch/gates/tests/catalogue entries deleted; `freshness.js` pause branch deleted.
6. **Artwork upload restored in the resolve flow** (CFG-24, D-19..D-20) — the step-B upload zone is unconditional again; "Change pictures" keeps only replace/delete of existing artwork.

The audience framing from phases 18–20 governs every change: a second household member with basic computer skills uses the everyday pages; a change that makes an everyday page more technical is the wrong change. Both languages are kept and every new string goes through the phase 20 catalogue (`companion/i18n_fr/`), with `companion/test_i18n.py`'s completeness harness green. Runway, Screen on/off and Quiet hours behaviour, the battery chart, the poll countdown, the read-aloud "State" text, notifications, Device, the renderers, the firmware and the on-disk state layout are out of bounds.

</domain>

<decisions>
## Implementation Decisions

Every decision below is locked (it comes from the PRD, which records the developer's own requests verbatim and the proposal the developer approved).

### A. Frame controls up front (points 3, 8 — CFG-19)

- **D-01 A "Frame" strip at the top of Home.** Directly under the page header,
  before anything else, Home shows one full-width strip (heading "Frame" /
  "Cadre") holding, left to right: the Screen switch (state "On"/"Off" plus
  the instant "Switch on"/"Switch off" button), the Quiet hours switch (state
  "On — 23:00 to 07:00"/"Off" plus "Turn on"/"Turn off"), and the next update
  ("Next update ≈ 22:25", or "Expected since 22:25" when it is in the past,
  exactly the phase 20 wording from `home_page.NEXT_UPDATE_TEMPLATE` /
  `EXPECTED_SINCE_TEMPLATE`). The next update is the largest text in the
  strip (the `stat-tile__value` size), so it "stands out" as the developer
  asked in phase 20. The two switches post to the existing
  `POST /quick/display` and `POST /quick/quiet-hours` routes (`app.py`
  `QUICK_DISPLAY_ROUTE` / `QUICK_QUIET_HOURS_ROUTE`, `_handle_quick_toggle`)
  and redirect back to the page they were pressed on — no new routes, no JS.
  The strip is rendered by one shared helper (a new `companion/pages/
  frame_strip.py` or a function in `layout.py`) that both Home and Display
  call with the same `ctx`, so the two copies can never diverge.
- **D-02 The same strip at the top of Display.** Display's "When it is on"
  supersection keeps the full Screen on/off and Quiet hours cards (presets,
  custom times, save button) below, unchanged in behaviour; the instant
  switches currently embedded in those cards (`config_page.py`'s
  `quick-action-slot` markup around lines 1732 and 2098) move up into the
  strip and are removed from the cards, so each switch exists exactly once
  per page.
- **D-03 The nav shows a state reminder, not buttons.** The sidebar (and the
  mobile dropdown) gets one line under the brand/above the page list:
  "Screen on · Quiet hours off" (FR "Écran allumé · Heures calmes off"),
  rendered as a link to Home (`/`), in `text-caption` size with the same
  green/grey dot idiom as `layout.status_dot()` before each word. No form
  and no button in the nav — the nav stays a navigation element (A-xx of the
  phase 18 audit: no actions in the nav). The reminder reads the same
  `ctx["device_config"]` the strip reads, so it is always consistent with
  it. Text and dots are computed server-side; no script.
- **D-04 Home is rebuilt as: strip, three tiles, then picture + recent
  flights side by side.** Order on desktop (≥ 1024 px):
  1. the Frame strip (D-01);
  2. the three status tiles of phase 19 — "Frame", "Battery", "Flight data"
     — using `layout.stat_tile(label, value_html, state, icon=...)` in a
     three-column grid (the phase 19 `_status_tiles_html()` shape, git
     `614d41e~1:companion/pages/home_page.py` lines 166–218, with the phase
     20 wording of `FRAME_STATE_TEXT` / `BATTERY_STATE_TEXT` /
     `DATA_STATE_TEXT` and the "See details on Health" link under the grid);
     the phase 20 single status card (`_status_card_html()`, `.status-card*`
     CSS) is deleted — the next update it headlined now lives in the strip;
  3. a two-column row: the frame picture (`_hero_figure_html()`, caption
     "Rendered 22:14 · Departing AF1234 …", lightbox as today) on the left and
     the "Recent flights" list (five rows, thumbnails as today, "See all
     flights" link) on the right; the picture column is the wider one
     (about 3:2).
  On phones (< 700 px) everything stacks in the same order; the three tiles
  stack in one column below 480 px as in phase 19. The strip's three cells
  wrap to one per line on phones.
- **D-05 "Pretty" is a hard criterion, checked by screenshot.** The UI-SPEC
  must give the strip and the Home layout an explicit look (surface,
  border-radius, spacing, dot/pill idiom) drawn from the existing tokens, and
  the phase's headless sweep must produce Home screenshots at 1280 px and
  390 px in both languages that the verifier compares against the UI-SPEC's
  description. No new colour tokens; the strip uses the accent surface
  (`stat-tile--accent`) so it reads as the "control" area, distinct from the
  three neutral/ok/warn tiles.

### B. One "Frame colours" view (points 4, 5 — CFG-20)

- **D-06 One view replaces the four chip grids.** Today Display renders the
  theme chip grid four times: departures (`theme_id`), arrivals
  (`theme_arriving`, behind the "Use a different theme for arrivals"
  checkbox), calendar flights (`calendar_theme_id`, compact grid inside the
  Calendar card) and per-flight rules (`rule_theme_id`, compact grid inside
  the rule form). Phase 21 replaces all four with one card, "Frame colours"
  (FR "Couleurs du cadre"), at the top of the "Look" supersection.
- **D-07 Layout: preview left, assignment list right.** On desktop the card
  is two columns (about 1:1, preview column never narrower than 360 px): the
  live preview on the left (the phase 20 `/theme-preview/{id}.png?live=1`
  image with its "Preview with your last flight: AF1234" caption); on the
  right a list of four rows, in this order and with these labels:
  "Departures" (FR "Départs"), "Arrivals" (FR "Arrivées"),
  "Calendar flights" (FR "Vols du calendrier"), "Per-flight rules" (FR
  "Règles par vol"). Each row shows its current theme as a small swatch
  (the existing chip's colour dots) plus the theme name, or "Same as
  departures" (FR "Comme les départs") for Arrivals/Calendar when unset, or
  "3 rules" / "No rules yet" for the rules row. On phones the preview goes on
  top and the rows below.
- **D-08 Clicking a row selects what is being edited.** The rows are a
  radiogroup (`name="colour_usage"`, values `departures` / `arrivals` /
  `calendar` / `rules`, "departures" checked by default; the radio input is
  visually hidden, the whole row is its label). Under the list, one chip
  grid (the existing `_theme_chip_grid_html()` markup and styles, rendered
  once) shows the theme choices for the selected usage; the preview shows
  the selected usage's theme. Selection is carried out by
  `static/theme-preview.js` (extended, still ES5, still no HTML sink): it
  reads `data-usage`/`data-preview-src` attributes the server rendered, swaps
  the preview `src`, and toggles which hidden `<input name="theme_id" |
  "theme_arriving" | "calendar_theme_id">` the visible chips write to. The
  no-JS floor: without script the four rows are plain radios and the card
  shows four stacked chip grids (one per usage, each `<fieldset>` labelled
  by its row) — every value can still be saved, the page is just longer.
- **D-09 Arrivals and Calendar keep "Same as departures".** The chip grid for
  Arrivals and Calendar has one extra first chip "Same as departures" (FR
  "Comme les départs") which submits the empty value, replacing the phase 20
  "Use a different theme for arrivals" checkbox (`THEME_ARRIVING_CHECKBOX_
  LABEL`, `THEME_ARRIVING_TOGGLE_ID`) and the Calendar card's own compact
  grid. Server-side semantics are unchanged: `theme_arriving=""` →
  `None`, `calendar_theme_id=""` → `None` through the existing
  `normalise_theme_arriving()` / `normalise_calendar_theme_id()`.
- **D-10 Per-flight rules keep their small form, under the list.** Selecting
  the "Per-flight rules" row shows, instead of a chip grid, the existing
  rule list (`_rule_list_html()`, delete buttons unchanged) and the existing
  "add a rule" form (`_rule_add_form_html()`: Match by Flight/Aircraft/
  Airline, Value, suggestion chips) with its own compact chip grid for
  `rule_theme_id`, posting to `/settings/rules/add` as today. The "How rules
  combine" disclosure stays with the rules. The old separate "Flight
  colours" card (`_rules_section_html()`, `RULES_SECTION_HEADING`) is
  removed; the rules are reached only through this row.
- **D-11 One save for departures/arrivals/calendar.** The three theme fields
  stay part of `settings-form` (the `form="settings-form"` idiom introduced
  in phase 20), so the Display "Save" button saves them together, and the
  dirty-state guard (`dirty-state.js`) covers them. Rule add/delete keep
  their own immediate POSTs.
- **D-12 Preview follows the selection in both dimensions.** The preview
  image shows the theme of the selected row; when the user then clicks a
  chip, the preview updates to that chip (as in phase 20). For "Same as
  departures" the preview shows the departures theme. For the rules row the
  preview shows the theme selected in the rule form's grid (defaults to the
  first theme).

### C. Calendar in one tile (points 6, 7 — CFG-21)

- **D-13 One Calendar card, status and URL together.** The Calendar card in
  "What it watches" contains, in this order: the status row ("Connected ·
  3 upcoming flights · checked 5 min ago" / "Not connected", the existing
  `status_row` verdicts), then — when not connected — the feed URL field
  with its hint and the primary "Connect calendar" button; when connected,
  the masked feed URL (host + "…", never the full token-bearing URL) on one
  line. The connect form (`POST /settings/calendar/connect`) is rendered
  inside the card, never as a separate section, and the "How it works"
  disclosure stays at the bottom of the card. The calendar theme chip grid
  leaves this card (D-06).
- **D-14 Once connected: a link and a small grey button.** "Replace the feed
  URL" (FR "Remplacer l'URL du flux") is a plain text link (`text-link`
  idiom) that expands the URL field inline (a `<details>` whose summary is
  the link text, so it works without script), with the same "Connect
  calendar" button renamed "Replace" (FR "Remplacer") inside it. "Disconnect"
  (FR "Déconnecter") is a small secondary button (`btn btn--secondary
  btn--small`, grey, right-aligned on the same line as the replace link),
  never the long red primary of phase 20. Disconnect keeps its confirmation
  step (the existing confirm page/route `CALENDAR_DISCONNECT_ROUTE` with
  `confirm=yes`) — the button is small, the safety net is unchanged.

### D. Compact Flights table (point 12 — CFG-22)

- **D-15 No horizontal scroll at 1280 px.** The Flights table
  (`history_page._history_table_html()`, headers `_HEADERS`) is compacted so
  that at 1280 px viewport width (the nav sidebar open) the table fits its
  column with no `.data-table-wrap` horizontal scrollbar, in both languages.
  Columns become: "When" (clock on the first line, "12 min ago" on the second
  line, using the existing `cell-primary`/`cell-secondary` pair), "Flight"
  (callsign on the first line; airline + aircraft type words on the second
  line, e.g. "Air France · A320"), "Route" (as today), "State" (as today),
  "Corroboration" (dot only, as today). The ICAO24 hex, the exact ISO
  timestamp, the runway and the copy-name button move into an expandable
  detail row: each table row gets a small "More" (FR "Plus") toggle at the
  end that reveals a second `<tr>` beneath it (a `<details>`-free
  implementation is not possible inside a table, so this uses one
  `data-row-toggle` attribute handled by a new tiny ES5 script or by
  extending an existing one; no-JS floor: the detail rows are rendered
  visible when script is absent, hidden by a class the script adds at load).
- **D-16 The mobile cards are unchanged.** The phone card layout
  (`_history_cards_html()`, "More details" `<details>`) already carries the
  same detail; only the desktop table changes. The filter bar and the
  "View panel" lightbox stay.

### E. Simple mode and the pause button removed (points 1, 10 — CFG-23)

- **D-17 Simple mode is removed entirely.** Delete `prefs.MODE_CHOICES`,
  `_MODE_CTX`, `simple_mode()`, `DEFAULT_MODE`, the `mode` argument of
  `set_request_prefs()`; `auth.UI_MODE_COOKIE_NAME` and the cookie read in
  `app.py`; `POST /ui-mode` (`MODE_ROUTE`) and its handler; `ctx["simple_
  mode"]`; the nav footer "Simple · Full" switch (`layout._mode_form_html`);
  every `simple_mode`/`ctx.get("simple_mode")` gate in `home_page.py`,
  `config_page.py` (calendar "How it works" short sentence, rules "How rules
  combine" short sentence, the Advanced-affordance omissions) and
  `airlines_page.py` (`_edit_toggle_html`) — the full-mode branch is kept in
  every case; the `CALENDAR_HOW_IT_WORKS_SIMPLE` / `RULES_HOW_RULES_
  COMBINE_SIMPLE` constants and their catalogue entries; the simple-mode
  tests (about 16 checks in `test_companion_app.py`, plus the ones in
  `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`,
  `test_i18n.py`) with the `EXPECTED_CHECK_COUNT` pins updated. A stale
  `sp_ui_mode` cookie in a browser is simply ignored. The CSS for the
  removed switch is deleted if it was specific to it.
- **D-18 The Health "Pause updates" button is removed.** Delete the button
  (`health_page.py` around line 2910, `REFRESH_PAUSE_TEXT` / the resume text
  and their catalogue entries) and the pause branch in
  `static/freshness.js` (`wireToggle()`, the `paused` flag): the freshness
  loop simply always runs. The countdown (point 11) and the battery chart
  (point 13) are untouched.

### F. Artwork upload restored in the resolve flow (point 15 — CFG-24)

- **D-19 Uploading a new picture is part of naming an airline again.** In
  `airlines_page._resolve_section_html()` the upload zone is rendered
  unconditionally (`upload_zone = _resolve_upload_form_html(upload_action,
  "")`, dropping the `if edit_mode` guard added by phase 19's `?edit=1`
  gating, line 1733), so step B of the resolve flow always offers the drop
  zone / file picker, in both modes of the page. The lightbox's upload
  affordance for an airline with no artwork yet follows the same rule.
- **D-20 "Change pictures" keeps only replace/delete of existing images.**
  The `?edit=1` toggle (`_edit_toggle_html`, the phase 20 "Change pictures"
  button) continues to reveal the replace/delete forms on airlines that
  already have artwork, and nothing else. The button is always visible now
  that simple mode is gone (D-17).

### Claude's Discretion

- Exact CSS class names and the internal layout of the strip and the Frame colours card, within the tokens and idioms of the design-system skill (`sketch-findings-skypane`) and the phase 21 UI-SPEC.
- Whether the strip helper lives in `companion/layout.py` or a new `companion/pages/frame_strip.py` (D-01 allows either; one write site is the requirement).
- Whether the flights detail-row toggle is a new ES5 file or an extension of an existing static script (D-15 allows either; the six-touch-point static-script contract applies to a new file).
- How the four no-JS chip grids are collapsed to one by script (a class the script adds at load, matching the D-15 pattern, is the expected shape).
- Which existing tests are retargeted versus deleted when the simple-mode checks go (D-17), as long as every `EXPECTED_CHECK_COUNT` pin is updated and no behaviour outside D-17 loses coverage.

</decisions>

<canonical_refs>
## Canonical References

**Downstream must read these** before planning or executing.

### This phase
- `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-PRD.md` — the decisions D-01..D-20, out of scope, acceptance criteria.

### Design contract and prior phases
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the companion's design system (tokens, cards, control density, page patterns); the new strip, the Frame colours card and the calendar tile must be documented there when done.
- `.planning/phases/20-companion-suggestions-from-the-audit-french-localisation-liv/20-PRD.md`, `20-CONTEXT.md`, `20-UI-SPEC.md`, `20-VERIFICATION.md`, `20-HUMAN-UAT.md` — what phase 20 shipped (Display supersections, `form="settings-form"` idiom, status_row/stat_tile/section_intro_html primitives, theme-preview route and script, catalogue package, simple mode) and what this phase undoes or reshapes.
- `.planning/phases/19-companion-audit-follow-through-fix-the-open-findings-from-18/` — the three-tile Home this phase restores (`git show 614d41e~1:companion/pages/home_page.py`, `_status_tiles_html()` lines 166–218) and the `?edit=1` gating this phase relaxes (19-08).
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` — the audience framing and the "no actions in the nav" finding.

### Code seams named by the decisions
- `companion/pages/home_page.py` — `_status_card_html()`, `_hero_figure_html()`, `_recent_flights_html()`, `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE`, `FRAME_STATE_TEXT`/`BATTERY_STATE_TEXT`/`DATA_STATE_TEXT`.
- `companion/pages/config_page.py` — `theme_fieldset()` (line ~1138), `_theme_chip_grid_html()` (~966), `THEME_ARRIVING_*` constants (~227–235), `quick-action-slot` markup (~1732, ~2098), `QUICK_ACTION_*` constants (~431–446), `calendar_group()`/`calendar_connect_section()` (~2145+), `CALENDAR_*` constants (~654–787), `_rule_add_form_html()` (~2608), `_rule_list_html()` (~2785), `_rules_section_html()` (~2805), `_display_groups_html()`, `render()`.
- `companion/pages/history_page.py` — `_HEADERS` (141), `_history_table_html()` (807), `_merged_cell()` (565), `_callsign_hex_cell()` (644), `_type_airline_cell()` (703), `_clock_cell_html()` (777), `_history_cards_html()` (867).
- `companion/pages/health_page.py` — `REFRESH_PAUSE_TEXT` (343), the pause button (~2910); `companion/static/freshness.js` — `wireToggle()`, the `paused` flag.
- `companion/pages/airlines_page.py` — `_resolve_section_html()` (1608; the `if edit_mode` guard at 1733), `_edit_toggle_html()` (1829), `_lightbox_html()` (1160).
- `companion/prefs.py`, `companion/auth.py` (`UI_MODE_COOKIE_NAME`), `companion/app.py` (`MODE_ROUTE`, the cookie read ~1156, `page_context()` ~1258/1304, the `/ui-mode` handler ~2858, `_handle_quick_toggle` ~2787, `QUICK_DISPLAY_ROUTE`/`QUICK_QUIET_HOURS_ROUTE`), `companion/layout.py` (`_mode_form_html()` ~1010, nav/sidebar builders, `stat_tile` ~1460, `status_row` ~1551, `status_dot`).
- `companion/static/theme-preview.js`, `companion/static/dirty-state.js`, `companion/static/style.css` (`.stat-tile*` ~2999, `.home-*` ~4915, `.quick-action*` ~4947, `.home-hero` ~5269, `.status-card*` ~5322).
- `companion/i18n_fr/` (per-page catalogue modules; `__init__` raises on duplicate keys), `companion/test_i18n.py` (completeness harness).
- `server/wake.py` — `next_wake_at_iso()`; `server/device_config.py` — `normalise_theme_arriving()`, `normalise_calendar_theme_id()`.
- Tests with pins to update: `companion/test_companion_app.py` (267), `test_config_page.py` (212), `test_status_pages.py` (213), `test_view_pages.py` (107), `test_i18n.py` (24), `test_contrast_check.py` (39).

</canonical_refs>

<specifics>
## Specific Ideas

- The developer's exact words are quoted at the top of the PRD; "place prépondérante" for the two switches is D-01/D-02/D-03, "3 tuiles séparées" is D-04, "preview à gauche, options à droite" is D-07, the photo of the connected calendar card is D-14.
- The next update time must be the largest text in the strip (D-01) — it was "mériterait d'être plus en avant" in the phase 20 feedback and headlined the status card this phase deletes.
- The Frame colours card must keep a no-JS floor (D-08): the four rows are plain radios and four stacked chip grids without script; the script collapses them to one.
- "Same as departures" replaces the arrivals checkbox and the calendar card's compact grid (D-09); server semantics unchanged (empty value → `None`).
- The Flights table's fit at 1280 px is measured in both languages (D-15) — French headers and labels are longer.
- Five checks fail identically on main in the root sandbox (read-only-dir cases: two in `companion/test_companion_app.py`, two in `server/test_manual_resolutions.py`, `anomaly_active()` in `companion/test_status_pages.py`) — never edit them.

## Out of scope (from the PRD)

- Any change to Runway, Screen on/off (beyond moving the instant switch into
  the strip) or Quiet hours behaviour — they stay on Display as they are.
- The battery chart, the poll countdown, the "State" read-aloud text and the
  per-browser persistence of the language/theme choice (points 9, 11, 13,
  14 — accepted).
- Notifications, the Device page, the theme preview renderer, the panel
  renderer, the frame firmware and the on-disk state layout.
- A third language, or any change to how the catalogue works.

## Acceptance criteria (from the PRD)

1. Home, at 1280 px, shows in order: the Frame strip (Screen switch, Quiet
   hours switch, next update in the largest text), the three tiles Frame /
   Battery / Flight data, then the picture and the recent flights side by
   side; at 390 px the same in one column. No quick-action widgets anywhere
   else on Home.
2. Display shows the same strip at the top; the Screen and Quiet hours cards
   below no longer contain an instant switch. Pressing a switch on either
   page redirects back to that page with the state changed.
3. The nav shows "Screen on · Quiet hours off" (or the matching states, in
   the current language) as a link to Home, with no button or form.
4. Display's "Look" supersection has one "Frame colours" card: preview left,
   four rows right on desktop (preview on top on phones); clicking a row
   changes which usage the single chip grid edits and what the preview
   shows; Arrivals and Calendar offer "Same as departures"; the rules row
   shows the rule list and add form; the "Use a different theme for
   arrivals" checkbox, the Calendar card's chip grid and the separate
   "Flight colours" card are gone. Saving Display persists all three theme
   fields; the no-JS page still lets every value be saved.
5. The Calendar card holds the status, the URL field/connect button when not
   connected, and — once connected — the masked URL, a "Replace the feed
   URL" link and a small grey "Disconnect" button that still confirms.
6. The Flights table at 1280 px has no horizontal scrollbar in FR or EN;
   the hex, ISO timestamp, runway and copy button are in an expandable
   detail row; the phone cards are unchanged.
7. No "Simple/Full" switch, no `/ui-mode` route, no `simple_mode` reference
   anywhere in `companion/`; the everyday pages show the full-mode content.
8. No "Pause updates" button on Health; the freshness loop runs without a
   pause branch.
9. On Airlines, naming an unrecognised airline offers the picture upload in
   step B without `?edit=1`; "Change pictures" still reveals replace/delete
   on existing artwork.
10. The French catalogue is complete (test_i18n harness green); all test
    harnesses pass with their pins updated; ruff clean; the headless sweep
    (EN/FR × 1280/390) reports no overflow, no inline script, no 404.

</specifics>

<deferred>
## Deferred Ideas

- Any further Home widgets (the developer wants Home glanceable, not busy).
- Per-screen state directories (the `screen_id` seam from phase 19 stays as is).
- A third UI language.
- Any change to the frame firmware or to the panel renderer's output.

</deferred>

---

*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Context gathered: 2026-09-12 via PRD Express Path*
