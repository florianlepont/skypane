# Phase 21 — PRD: frame controls up front, Home with three tiles, one Frame colours view, one calendar tile, compact flights table, simple mode removed, artwork upload restored

Source: the developer's feedback after phase 20 (2026-09-12), given as fifteen
numbered points, plus the developer's approval of the orchestrator's proposal
for points 2/3/8, 4/5 and 6/7 ("2, 3 et 8 ok / 4 et 5 ok / Piste, Écran, Heures
calmes ok").

The developer's words, verbatim:

> 1 - supprimer le togglet complet/simple
> 2 - l'écran home n'est vraiment pas satisfaisant ni joli.
> 3 - en fait les écrans allumés et heures calmes devraient avoir une place
>     prépondérante dans l'interface. Dans la barre de navigation ? ou au moins
>     tout en haut de l'accueil ou de l'affichage.
> 4 - aspect mériterait quelque chose de plus beau et travaillé pour unifier la
>     vue des thèmes d'avion et éviter d'en avoir 4 en tout. une vue avec
>     calendrier, règles, arrivées et départs fusionnées ?
> 5 - Aperçu du thème. Oui ça fonctionne mais sur PC ça mériterait d'être
>     optimisé ... preview à gauche, options à droite ?
> 6 - Calendrier et url du calendrier ne sont pas dans la même tuile
> 7 - Une fois connecté, l'interface laisse vraiment à désirer (voir photo)
> 8 - Lecteur d'écran et garde de sortie. -> je trouvais ça mieux comment
>     c'était fait en phase 19 (3 tuiles séparées)
> 9 - Persistance des choix. ok
> 10 - à quoi sert le bouton suspendre les mises à jour ? il est inutile pour moi
> 11 - Compte à rebours du poll. ok
> 12 - Tableau des vols peut être clairement optimisé en terme de place pour
>      éviter le scroll sur desktop
> 13 - Graphique de batterie. ok
> 14 - Lecture à voix haute de État ok
> 15 - Pourquoi je ne peux plus uploader une nouvelle image d'avion ?

Points 9, 11, 13 and 14 are accepted as they are and need no work. Runway,
Screen on/off and Quiet hours stay on Display ("Piste, Écran, Heures calmes
ok").

Audience framing carried over from phases 18–20: a second household member
with basic computer skills uses the companion. Everyday pages (Home, Display,
Flights, Airlines) stay plain-language; Advanced pages (Health, Device) may
keep technical terms as tooltips. Both languages (French and English) are kept
and every new string goes through the phase 20 catalogue with the
completeness harness green.

## Goal

Put the two everyday frame controls (Screen on/off, Quiet hours) and the next
update time where they are seen first — a "Frame" strip at the top of Home and
of Display, with a state reminder in the nav — rebuild Home around the three
separate status tiles of phase 19 plus the frame picture and the recent
flights side by side, merge the four theme chip grids into one worked
"Frame colours" view (preview on the left, a four-row assignment list on the
right), put the calendar status and its feed URL in one tile with a quiet
"replace" link and a small grey "disconnect" button once connected, make the
Flights table fit a 1280 px desktop without horizontal scroll, remove the
simple/full mode and the Health "Pause updates" button, and restore the
artwork upload in the Airlines "name an airline" flow.

## Requirements covered

CFG-19 (frame controls up front + Home rebuilt), CFG-20 (one Frame colours
view), CFG-21 (calendar in one tile), CFG-22 (compact Flights table),
CFG-23 (simple mode and pause button removed), CFG-24 (artwork upload in the
resolve flow restored) — added to `.planning/REQUIREMENTS.md` by this phase's
cadrage. CFG-18 (simple mode) is superseded by CFG-23 and marked as such.

## Decisions

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

## Out of scope

- Any change to Runway, Screen on/off (beyond moving the instant switch into
  the strip) or Quiet hours behaviour — they stay on Display as they are.
- The battery chart, the poll countdown, the "State" read-aloud text and the
  per-browser persistence of the language/theme choice (points 9, 11, 13,
  14 — accepted).
- Notifications, the Device page, the theme preview renderer, the panel
  renderer, the frame firmware and the on-disk state layout.
- A third language, or any change to how the catalogue works.

## Acceptance criteria

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
