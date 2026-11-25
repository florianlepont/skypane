---
phase: 68-console-and-companion-visual-improvements
plan: 35
subsystem: companion
tags: [fleet-frame-page, state-tiles, health-page, versions-page, sticky-anchors, access-text, render-baseline]
requires: ["68-26", "68-02"]
provides:
  - "State section as four equal tiles (Connection, Battery with sparkline, Flight data, Firmware), each with a Details link"
  - "Health and Versions pages of a frame (views of the Fleet page, no new route)"
  - "Phone: State / Settings / Access stacked under sticky anchors; desktop: one column of equal cards"
  - "Access section without introduction, empty-state text or helper line (R14)"
key-files:
  created:
    - companion/pages/fleet_tiles.py
    - companion/static/fleet-anchors.js
    - companion/test_fleet_tiles.py
    - companion/test_browser_fleet_detail_pages.py
  modified:
    - companion/console_fleet_view.py
    - companion/pages/health_page.py
    - companion/pages/update_page.py
    - companion/pages/co_managers_card.py
    - companion/health_rows.py
    - companion/fleet_moves.py
    - companion/app.py
    - companion/static/style-admin.css
    - companion/static/style.css
    - companion/static/style-c-console.css
    - companion/i18n_fr/admin_fleet.py
    - companion/i18n_fr/co_managers.py
    - companion/testdata/render_baseline.json
decisions:
  - "No new route: Health and Versions are `/fleet?frame=<id>&view=health|versions`; the access matrix is unchanged."
  - "`tab=settings|access` stays in every redirect and is now a landing hint (a phone scrolls to that section); no tab is hidden any more."
  - "The retired /health, /device and /update addresses and the update install/cancel redirects now lead to the Health page, the Settings section and the Versions page."
metrics:
  completed: 2026-11-20
---

# Phase 68 Plan 35: Frame page tiles, Health and Versions pages, stacked sections, shorter Access Summary

The frame page of the Fleet now shows what the owner-approved mock draws: the State section is four equal tiles, each opening the page that holds the whole story; Health and Versions are real pages; Settings and Access are stacked (anchors on a phone, one column of equal cards on a desktop); the Access text is cut to the approved shape.

## What was built

- **Tiles** (`pages/fleet_tiles.py`): a 2 x 2 grid of equal tiles (equal width and height, whole tile is the link, 132 px minimum). Connection (state icon, verdict, age), Battery (percentage and millivolts, verdict, sparkline of the same series the Health chart plots), Flight data (verdict, age), Firmware (running version in monospace, the update card's headline: up to date, update available, scheduled ...). A frame that never checked in still has its four tiles ("No check-in yet" and neutral tiles). State is spelled out (visually hidden state word, verdict), never colour alone. Data comes from `health_page.frame_tiles()` (same snapshot as the Health rows) and `update_page.firmware_summary()`.
- **Health page** (`view=health`, `console_fleet_view.health_html`, `health_page.health_sections`): every block the page has today, each row's evidence open without a tap (`health_rows.opened_html`): the no-signal notice, the source-fault block and the warnings banner above; the Frame section (connection, battery with ring, readout, Percentage / Voltage switch, chart, readings table); for an administrator the Server & data section (flight data, data sources with the three outcomes, identification with the breakdown table, off-box backup). The link to the unresolved airlines is removed (`UNRESOLVED_LINK_HREF` deleted). A non-administrator keeps the flight data row in the Frame section. A frame that never checked in gets the existing empty state.
- **Versions page** (`view=versions`): the existing update card (installed version, update availability and its Install action, scheduled / installing / failed states, rollback notice) and the version list with every release and its Install or Roll back action. Install and cancel redirects come back here.
- **Detail page head**: a 44 px "Back to <frame>" link and the page's one `h1` ("Health", "Versions"); the list column is not part of these pages at any width.
- **Sections**: `frame_html` renders State (tiles), Settings (unchanged content, form, dirty bar, `value-controls.js`) and Access under three phone anchors (`nav.fleet-anchors`, sticky, 44 px, `fleet-anchors.js` marks the section in view and brings `tab=` into view). From 960 px the anchors are hidden and the sections are one column of cards of equal width and look. The segmented State / Settings / Access control, `data-fleet-tab`, the Device and version block and its CSS are removed.
- **Access (R14)**: the "Co-managers / People who can change..." purpose row, the "No co-managers yet" empty state and the typed-address helper line ("The person must already be invited") are gone from the Fleet Access section and its Add dialog (`access_rows_html(compact=True)`, `add_dialog_html` without helper); the owner with Reassign, the co-managers, one Add control and Retire with its one-line hint remain. The long Reassign / Retire sentences were already only in the confirmation dialogs. The Manage access dialog of the personal side is unchanged. `co_managers.purpose_manage` was removed from the catalogue (no orphan).
- **Icon buttons** for the personal view and Rename were already built in plan 26 and are unchanged.
- **French**: Détails, Micrologiciel, Retour à %s, Cadre (the Health Frame section); `admin_fleet.block_device_version` removed. EN/FR test and `test_i18n` green.

## Checked against the existing page before building

- Battery curve period: the existing Health chart plots **daily averages over 90 days** (falls back to the latest 20 readings when fewer than two days exist), not the mock's 7 days. The tile sparkline and the Health chart use that same series; no 7-day period was invented.
- Rows of the Health page are the existing ones (above); the mock's "Last check-in / Next wake / Last run" facts are the existing connection facts (Last check-in, Next wake; Last run exists on the flight data row).

## Deviations from Plan

- **[Rule 3]** Files outside the plan list were touched: `console_fleet_view.py`, `fleet_moves.py`, `app.py` (one function, 1493 lines), `update_page.py`, `health_rows.py`, `static_files.py`, `ui_base.py`, `layout.py`, `ui_shell.py` (script registration), `style.css` (reveal order), `motion.js` (comment), plus the tests listed in the commits.
- `tab=` kept as a landing hint instead of removing it (many redirects and tests use it).
- The plan's replacement of hand-built `banner__pill` markup needed nothing: none remains in the listed files.
- Baseline regenerated once at the end for plans 26 and 35 (68 entries: the Fleet captures and the stylesheet / script version hashes).
- STATE.md and CON-01 not touched; no `gsd-sdk state` or `requirements` command run.

## Design-system divergences

Every difference from `68-MOCKUP-frame-list.html`:

1. Tile labels use the existing row names ("Frame connection", "Battery", "Flight data") and "Firmware" (new); the mock says "Connection". Tile sentences are the existing strings ("Checking in normally", "Level looks normal", "No detection yet", "The frame is up to date", "Update available"), not the mock's illustrative ones. Battery tile shows "42% · 3777 mV" with the verdict under it (the mock shows "47 %" with "Normal level").
2. Tile icons: connection uses the state icon (tick, triangle, cross, circled i) as the Health rows do; battery uses `icon-battery`, flight data `icon-plane`, firmware `icon-nav-update` (the mock's chip glyph is not in the sprite; no sprite additions). Tiles are 22 px cards on the glass-solid fill with the shared shadow; the gap is 8 px (mock 12 px, not a token).
3. The mock's battery caption "Last 7 days" is absent from the tile (period is 90 days, see above).
4. The Health page keeps the existing structure: rows are the existing collapsible `<details>` (open without a tap, a chevron remains and a row can still be closed), grouped under two section labels "Frame" and "Server & data" in two flat glass groups; the mock draws each topic as its own card, no chevrons, a "Visible to administrators" caption on the server group, and shows the airlines table descriptions and the "2 to resolve" pill in its own layout. The warnings banner and the no-signal notice are the existing toasts, not the mock's bordered boxes. The Health title in French is the existing "État" (mock "Santé").
5. The Health page's battery block keeps the existing ring, readout line, Percentage / Voltage switch (a plain button pair), chart with its axes and "View N readings" disclosure (closed), as the page has today; the mock shows the readings table open and a simpler curve.
6. The Versions page uses the existing update card and list: the action is "Install <version>" on the card and "Roll back" on older rows (mock "Revert"); notes sit behind a disclosure; the mock's "Battery reading fix" style notes are the seeded release notes. Dates read "28 Sep 14:00 · 52d ago".
7. Desktop detail pages have no list column (as drawn) but sit in the same shell, left-aligned with the frame column's 32 px padding and a 760 px content cap; the mock draws the main column starting at the sidebar with 44 px padding.
8. Phone anchors are three equal 44 px pills stuck under the app bar with the page canvas behind them; the mock's sit inside its own scroller. The first anchor is current without script and the current one follows the scroll with script.
9. Access rows show the e-mail with the "Owner" / "You" pill (existing), not a name over a role line, and the co-manager's Remove is the existing "Remove" ghost button (mock: round X icon button). "Add co-manager" is the existing label (mock "Add a co-manager"). The Retire row keeps its quiet outlined "Retire…" link and the existing hint ("The frame stops showing anything and its owner is released."), not a chevron row with the shorter mock hint. The served frame's Access section has no Retire row (as before). "Everyone who is invited is already on this frame." still replaces the Add control when nobody is left to add (not in the mock).
10. Settings keeps its existing controls (number field with seconds, slider, Diagnostic LED switch with its On / Off label and hint) and its inner layout; the mock draws a compact two-row card. The dirty bar and `value-controls.js` are unchanged.
11. The list column, sidebar shape and row details are those of plans 26 and its corrections (status first, floating sidebar and list panel 16 px apart, System in the nav), not the mock's flush column.
12. Frame page desktop column width is 722 px at 1440 (mock 760).

## Open decisions for the owner

1. Show the Health rows' chevron (they can still be closed) or remove the disclosure so the rows are fixed open as drawn?
2. Reword the tile and Access labels towards the mock ("Connection", "Add a co-manager", "Revert" instead of "Roll back", French "Santé" for Health), or keep the existing strings?
3. Battery period: keep the existing 90-day daily series (tile and Health chart) or reduce it to 7 days as drawn?
4. A tile for a frame that never checked in shows neutral tiles; the Health page then shows the existing empty state only. Fine, or should the tiles hide?
5. `68-MOCKUP-system.html` (untracked, not created by this plan) is in the phase folder; whether and how to commit it is yours.

## Tests (behaviour over source)

New: `test_fleet_tiles.py` (tiles EN/FR, never-seen frame, no readings, sparkline, state words, Health blocks and open rows, no unresolved-airlines link, hostile frame name escaped in back link and title, translated back link and title, unknown view, Versions content, install redirect), `test_browser_fleet_detail_pages.py` (title, 44 px way back, no overflow at 360 / 390 / 1440, EN/FR, both themes, open rows, tile to page and back), `test_browser_fleet_anchors.py` (renamed from the tabs file: anchors fit and are 44 px, stacked sections in order, four equal tiles at 360 / 390 / 1440, sticky anchors and current marking, no-script anchors, landing section, desktop without anchors, dirty bar), the Access text test EN/FR, a user's Health sections.
Updated to the approved behaviour (nothing skipped or loosened): the Fleet section, page and console tests, the legacy redirects (Health and Versions targets), update flows (Versions page), page opening order and pins (anchors replace the tab strip; sections count one step each), tap counts (U4c unchanged at 4: a scroll replaces the Settings tab tap; A4 / A5 no Access tab tap), title gap (the way-back link stands where the chip row does), motion token pin, script count 28, view-transition names (no Fleet strip), Health row tests moved to the Health page.

## Verification

`SKYPANE_REQUIRE_BROWSER=1`, `server/.venv/bin/python`, chunks: fleet browser set, 73 other browser files touching Fleet / Health / Update (three chunks), re-runs of every failing file after its update, non-browser (companion, test-support, scripts, stub-server) suite, render baseline, phase 47 freeze, access tests, structure and suite guards. Gates: ruff, mypy (46 files), function size (1140 functions, none over 80), comment history, `companion/app.py` 1493 lines, `health_page.py` 1259, largest JS 1227.

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p35/mock/` and `.../p35/built/`: `{mock,built}_{frame,health,versions,settings,access}_{ph,dk}_{en,fr}_{light,dark}.png` (phone 390, desktop 1440). Compared side by side; fixed: tile "Details" mark pressed against the meta line, Health rows closed (now open), phone title gap with the way-back link (test pin adapted).

## Self-Check: PASSED

## Health page conformance to the mock (follow-up)

- Health rows are flat and always open: `companion/health_rows.py` renders a row as
  `<div class="health-row">` with a `<div class="health-row__summary">` head and a body; no
  `<details>`/`<summary>`, no chevron, no open/close state (`OPEN_STATES` and `opened_html`
  removed, the hover/focus/chevron CSS and the `:not([open])` rule removed). The battery
  "View N readings" disclosure and the Percentage/Voltage switch and ring are unchanged.
- One glass card per topic (`console_fleet_view._cards_block`): connection, battery under the
  label "Frame"; flight data, data sources, identification, backup under "Server & data ·
  Visible to administrators", stacked with a 16 px gap (`.fleet-cards`).
- Labels moved to the mock's: tile "Frame connection" -> "Connection" / "Connexion"
  (`admin_fleet.tile_connection`); FR Health title "État" -> "Santé" (`nav.health`); FR "Dernière
  connexion" -> "Dernier contact"; "Flight identification" / "Identification des vols" ->
  "Identification"; Versions "Roll back" / "Roll back to %s" -> "Revert" / "Revert to %s"; Access
  "Add co-manager" -> "Add a co-manager", FR "co-gestionnaire" -> "cogestionnaire" everywhere in
  the catalogue; "Retire this frame" -> "Retire this frame..." (FR "Retirer ce cadre...");
  new label "Visible to administrators" / "Visible des administrateurs" on the server group.
  Status sentences, the 90-day battery series and the Versions page structure are unchanged.
- Gap: the Versions page keeps its own section labels ("Versions", "Running") instead of the
  mock's "Device and version" / "Installed" / "Previous versions", which describe a different
  structure.
