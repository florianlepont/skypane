---
phase: 68-console-and-companion-visual-improvements
plan: 37
subsystem: companion
tags: [system-page, tiles, console-fleet-view, render-baseline]
key-files:
  modified:
    - companion/pages/health_page.py
    - companion/pages/fleet_tiles.py
    - companion/pages/fleet_frames_list.py
    - companion/console_fleet_view.py
    - companion/static/style-admin.css
    - companion/i18n_fr/admin_fleet.py
    - companion/i18n_fr/health.py
    - companion/testdata/render_baseline.json
  created:
    - companion/test_system_tiles.py
    - companion/test_browser_system_tiles.py
decisions:
  - "No new route and no new data: the tiles summarise the four existing blocks from the snapshot the page already computes. Access matrix unchanged (administrators only)."
metrics:
  completed: 2026-11-20
---

# Phase 68 Plan 37: System page tiles

`/fleet?view=system` now opens with the owner-approved tiles: a 2 x 2 grid of equal tiles in the frame Overview look (`fleet_tiles._tile`, `.fleet-tile`, Details mark), placed under the warnings banner and above the existing detail blocks, which are unchanged. Each tile is a plain link to its block on the same page (`#system-topic-<key>`).

## What was built

- **Tiles** (`health_page.SystemTile`, `_system_tiles`, `fleet_tiles.system_tiles_html`):
  - Server: poll-pipeline verdict ("Running on schedule", "A little behind", ...) and "Last run <age>" (the existing flight-data facts). No machine health (disk, uptime, version) was added.
  - Data sources: corroboration verdict and the number of disagreements; neutral before any cycle.
  - Identification: "<n>% of flights identified" and "<n> to resolve" / "Nothing to resolve"; neutral (the rate has no pass mark).
  - Off-box backup: "Up to date" / "Overdue" and the age of the last backup; left out, with its block, when no marker is configured.
  - State is spelled out (visually hidden state word + headline), never colour alone; a warning or error tile also gets a coloured border (System page only).
- **Title line**: "The server behind every frame. Visible to administrators." / "Le serveur derrière chaque cadre. Visible des administrateurs." under the System title (`fleet-head__sub`).
- **FR**: "Serveur", subtitle; every other label is an existing string. No orphan ids (`test_i18n` green).
- No unresolved-airlines link anywhere on the page (the identification block already had none after plan 35; tested).

## Design-system divergences

Against `68-MOCKUP-system.html`:

1. Tile icons: Server uses the pipeline glyph, Data sources the corroboration (two circles) glyph, Identification the tag glyph, Off-box backup the upload glyph. The mock's server, radio and cloud glyphs are not in the sprite and the sprite is not extended (same rule as plan 35).
2. The tiles are the plan 35 `.fleet-tile`, so values and Details marks sit at the shared sizes (mock: 19 px value, a 14 px padding card); the gap is 8 px (mock 12 px).
3. The detail blocks are unchanged, as the owner asked: one glass card per topic whose section label is only for assistive technology, the existing row layout (name above verdict, facts as label/value, outcome notes in full), and the existing identification table (Source / Description / Count, with long descriptions). The mock draws a visible label above each card and the shorter illustrative descriptions; sentences are the existing ones.
4. Sentences and numbers are the existing strings ("Sources disagreed recently", "3 disagreements", "92.4% of flights identified" with the decimal point in English), not the mock's illustrative ones ("92.4 %"). The Server tile reads "Last run 40 s ago" with the live relative age.
5. The warnings banner is the existing docked toast (pills, "3 warnings:"), not the mock's bordered box.
6. The mock's unresolved-airlines link and "2 to resolve" pill are not built (owner decision; the count shows as the tile's muted line and the existing row).
7. The mock's frames column on the phone is not part of the System page; the phone shows the existing chip switch above the title as today.
8. Warn/error border colour is scoped to `.fleet-tiles--system`: the frame Overview tiles keep their current look. The sketch findings use the status colours the same way (amber, rose) with the word beside them.
9. A tile jumps with a plain anchor and `scroll-margin-top` (no script); the mock scrolls its own pane in script.

Against the sketch findings: none known. Tokens only, 44 px minimum tile height (132 px), 2 x 2 at 320, 390 and 1440, no horizontal overflow, both themes, EN and FR.

## Deviations from Plan

None; no plan file existed. Gates: ruff, mypy (46 files), function size (1140, none over 80), comment history, `companion/app.py` 1493 lines. The render baseline was regenerated once (16 lines: the System captures and the stylesheet version hash).

## Tests

New: `companion/test_system_tiles.py` (tiles, labels, hrefs and block ids, warning state word, backup tile left out without a marker, no unresolved-airlines text, subtitle, French) and `companion/test_browser_system_tiles.py` (four equal tiles at least 44 px, no overflow at 320/390/1440, EN/FR, light/dark, state word present, a tile brings its block into view). Existing tests were not pinning the old page and needed no change. Full run: 28 existing files touching the System view (862 tests, browser required) green; companion, test-support, scripts and stub-server non-browser suite 7915 passed (the one render-baseline failure was fixed by the single regeneration); render baseline, phase 47 freeze and access tests green.

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p37/mock/` and `.../p37/built/`: `{mock,built}_{ph,dk}_{en,fr}_{light,dark}.png` (EN light, FR dark, desktop EN dark, plus a few extras on the built side).

## Open questions for the owner

1. Keep the section label of each detail block hidden (as today), or show it above each card as the mock draws?
2. Should the Overview frame tiles also get the coloured border for a warning (now System only)?
3. Server tile: should a later plan add real machine health (disk, uptime, deployed version)? It needs new data.

## Self-Check: PASSED

## Fidelity pass

The owner compared the build with `68-MOCKUP-system.html` and asked for the mock, including its short texts. The detail blocks and the warnings banner were rebuilt for the System page only; the frame Health page keeps its rows (`health_rows`) and its sentences untouched.

### What changed

- `companion/pages/system_cards.py` (new) builds the four detail cards and the banner from the same snapshot as the tiles. Each card is a header row (state icon with a hidden state word, small label, bold verdict, right-aligned short value or "N to resolve" pill), a hairline, then label/value rows with the value at the right ("Last run 40 s ago", "Last detection", "Last off-box backup").
- The section label above each card ("Flight data", "Data sources", "Identification", "Off-box backup", and their French forms) is visible again.
- Data sources: three outcome rows separated by hairlines (dot and name, count in bold at the right, one short sentence). New short sentences, EN and FR from the mock.
- Identification: header "92.4 % of flights identified" (non-breaking space before the percent sign, as the mock), sub line "Last 30 days: 148 flights" (the page computes 30 days, so the mock's "7" became the real number), "N to resolve" pill at the right, and a flat Source / Count / Description table with the mock's short descriptions in the mock's order. No unresolved-airlines link. The tile reads "92.4 % identified" as in the mock.
- Warnings banner: a bordered card, "N warnings:" in bold, one outlined pill per warning, then "Something needs attention — check the rows below." (`div.sys-banner.health-anomaly`).
- The fleet swap registry (`ui_nav.py`, `freshness.js`) gained `.sys-card__head` so the cards refresh like the rows did.
- Tests: `test_system_tiles.py` (cards, outcomes, identification header and table, banner, French), `test_browser_system_tiles.py` (labels visible, values right-aligned, no overflow at 320/390/1440); pins moved from the old blocks in `test_toasts.py`, `test_page_context.py`, `test_user_view_http.py`, `test_status_pages_04.py`. Render baseline regenerated once.
- Captures: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p37b/{mock,built}/`.

### Remaining divergences

1. Tile and card icons are the existing sprite glyphs (pipeline, corroboration, tag, upload), not the mock's server, radio and cloud: every page embeds the sprite and the render hashes and the sprite-count pin would move for the whole app.
2. Tiles stay the shared `.fleet-tile` (value 17 px against the mock's 19, icon 32 px against 36, padding 16 against 14, grid gap 8 against 12) so they match the frame Overview.
3. Relative ages come from the shared ladder ("39s ago", "il y a 11 min"), not the mock's "40 s ago" spelling; the numbers are live.
4. Three French verdicts keep their existing wording because the Health page shares them ("Les sources se sont contredites récemment" against the mock's "ont divergé"; banner pills such as "Sources en désaccord récemment" are the real anomaly labels).
5. Real data replaces sample data: counts, 30-day window, the number and labels of warnings (the page can carry the device-stale warning as well).
6. Font and spacing use tokens: 15 px for fact rows (mock 14), 12 px paddings as `calc(space-sm + space-xs)`.
7. The mock's frames column and phone chip row are the existing shell, unchanged.
