---
name: sketch-findings-skypane
description: The companion web app's current design system — colour and contrast, typography, spacing, cards, control density, navigation, and page patterns — maintained continuously across phases and auto-loaded during UI implementation on skypane.
---

# SkyPane companion design system

**As of:** 2026-11-25, checked against the code of origin/main `ef229d21` plus the spacing and radius tokens (`--space-6/10/12/14`, `--radius-8/10/12`).
`.planning/workstreams/v1-2/ROADMAP.md` is the live record of plan status.

**Keeping it current.** This skill is not updated automatically. Any PR that changes companion CSS
tokens, navigation, a component or a page layout (`companion/static/style*.css`, `companion/ui_*.py`,
`companion/pages/`) updates the matching file in `references/` and the "as of" line in the same PR.
Between that rule and review, the skill can be behind: when code and skill disagree, the code wins
and the skill gets fixed.

The numbers of this skill (colour tokens in Light and Dark, radii, spacing, type sizes, motion
tokens, the 44px target, the 4.5:1 pairs) are checked against the served site by
`companion/test_browser_design_system_drift.py`, using `companion/testdata/design_system_tokens.json`
as the one comparison point. A PR that changes a token updates that manifest, this skill and its
"as of" line together; the manifest is a hand-copied transcript, so skill = manifest holds by review only.

## Stack and boundaries

The companion is a stdlib-only Python HTTP service under `companion/` (`ThreadingHTTPServer`),
sign-in for administrators and users, English and French. Its look is hand-written CSS with no build
step: `companion/static/style.css` (tokens, shared components) plus per-area sheets
(`style-home|flights|place|airlines|display|admin|c-console|c-lists.css`) linked per page by
`page_styles.py`; the served CSS and JS are comment-stripped. Vanilla ES5 scripts in `companion/static/`,
all optional: every page works with scripts blocked. Vendored Leaflet 1.9.4 and OpenStreetMap tiles
serve the Location page only. The e-ink frame's own palette and fonts never cross into the companion.
Rendering helpers: `ui_base.py`, `ui_shell.py`, `ui_nav.py`, `ui_components.py`, `ui_groups.py`,
`ui_segmented.py`, `ui_modal.py`, `ui_save_bar.py`, `ui_filter.py`, `ui_entity_list.py`.
Size limits that shape the code: `companion/app.py` at most 1500 lines, a script file at most 1500
lines, a function at most 80 lines.

## Core rules at a glance

- **Direction:** a pale sky (Light) or ink (Dark) background painted on `<html>`, frosted glass
  groups and bars, system sans only, a neutral accent. No serif, no warm beige, no terracotta.
- **Colour:** Light canvas `#F1F3F6`, secondary `#E9EEF5`, border `#DAE1EB`, text `#17191F`, accent
  graphite `#1F2430` (hover `#343B4D`, on-accent white). Dark canvas `#161A24`, secondary `#1C222D`,
  border `#2A3040`, text `#F1F3F6`, accent ivory `#F2EFE9` (hover `#E2DED5`, on-accent `#14171F`).
  Status ok/warn/error `#16A34A/#D97706/#BE123C` (Dark `#4ADE80/#FBBF24/#FB7185`).
- **Secondary ink:** the text colour at 70% (`color-mix(in srgb, var(--color-text) 70%, transparent)`),
  used for every muted line, the first-visit hint, the 404 caption and the idle segment label. On a
  tinted panel (the opened Audit event) a label uses 80% so it still reaches 4.5:1.
- **Sky + glass:** sky `#E7EEF7 > #F1F3F6 > #EDF1F6` (Dark `#12151D > #161A24 > #1A1F2B`);
  `--glass-bg` white .72 / .09, blur 22px (tab bar and More sheet are opaque; only the More scrim blurs, 8px); the glass blur sits in one `@supports` block, and the
  exceptions outside it are the More scrim and two Location scrims (8px) and the Location sidebar (26px).
- **Radii:** control 14, card 22, sheet 28 (top corners), pill 32; portrait frame picture 5.
- **Type:** page title clamp 30-34px phone / 40-44px desktop, 700, tracking -0.03em; section/sub-page
  22px 600; card title 17px 600; body 16; secondary 15; caption and section label 13 (the caption size
  also sets the first-visit hint, tile meta lines and hints under controls); tab label 11, chart axis 12
  (Home statistics hours and bars 11). Headings carry -0.01em and display numerals -0.02em to -0.04em.
  No uppercase label voice (two exceptions in `tokens-and-theming.md`). Mono only for identifiers.
- **Spacing:** 4, 8, 16, 24, 32, 48, 64px (`--space-xs..3xl`); sibling-card gap 24px.
- **Motion:** two durations plus a documented set of tokens (`--motion-fast` 180ms, `--motion-slow`
  2s, `--motion-enter` 400ms, stagger 60ms, spring, view-transition 260ms ...); no bare duration
  literal; budget enforced by `companion/test_companion_app_04.py`; reduced motion switches it off.
  Ambient loops (the Home dot halo) stop under an open dialog or sheet.
- **Targets:** every control is 44px (an icon-only control draws a 44px hit area). Minimum width
  360px, no horizontal scroll (320px is the floor the More sheet and tab bar are still measured at).
- **Names:** an icon-only control has an accessible name (`aria-label` and a tooltip), always.
- **Bilingual:** every user-facing string is an `i18n.msg` with a French entry in `companion/i18n_fr/`;
  French must fit.
- **Dark / light:** Auto follows the OS; Light and Dark are explicit (`html[data-ui-theme]`);
  `theme-color` metas follow it. Every token lives in four blocks: edit all. The Location map is a
  dark map in Dark and in Auto-dark.
- **Navigation:** below 960px one floating bottom tab bar (Personal: Home, Flights,
  Airlines, Style, Location, More, but a plain user's last cell is Account; Console: Fleet, Users, Editor, System, More with Audit inside);
  from 960px a glass sidebar. The same page order everywhere.
- **Sheets and dialogs:** a bottom sheet with a field lifts above the on-screen keyboard
  (`--keyboard-inset`, set by `modal.js`); a short dialog uses the compact modifier; a question
  dialog has two equal answers and a cross.
- **Components:** use a catalogue helper (`.btn`, `ui_groups`, `ui_segmented`, `pill_html`,
  `toast_html`, one Save bar); the admin `/components` page is the living catalogue.

## References

| File | Read when |
|------|-----------|
| `references/tokens-and-theming.md` | colours, secondary ink, sky and glass, radii, type, spacing, safe areas, dark/light, the dark map, iOS Home Screen app |
| `references/components.md` | buttons, groups and rows, pills, segmented, switch, toast, foreign-frame marker, dialogs (compact, result, question), Save bar and leave dialog, app bar, frame menu, tiles |
| `references/navigation.md` | tab bar, More panel, sidebar, spaces, the single page order and names EN/FR |
| `references/page-patterns.md` | Home, Flights, Location, Style, Airlines by role, Fleet (list, frame page, Battery, Versions, System), Editor, Users, Audit, Account, sign-in, 404, retired frames, Components, splash |
| `references/motion.md` | motion tokens and budget test, page opening, view transitions, tab strip, splash, reduced motion |
| `references/accessibility.md` | 44px, focus, headings, icon-only names, contrast modules, HTTP 405 and CSRF, 360px |
| `references/i18n-bilingual.md` | EN/FR rules, the shared page words, tests |
| `sources/README.md` | the old sketches are history, not the design |

## The shape of the app today

- **Home** is a column of blocks: title block, flight card, pills, statistics card, recent-flights strip.
- **Fleet** opens on the list of frames; a frame page is an overview of three tiles, then Settings
  and Access; Battery and Versions are their own pages; System is a full page of compact tiles.
- **Airlines** is a read-only collection of what a frame has seen for a user; for an administrator
  the Editor is fleet-wide, with names and artwork shared by every frame.
- **Users** is one card of rows on a phone and a table on a wide screen; invitations go through
  the identity provider and show their link once.
- **Account** lists frames with icon actions and an About group; the sign-in card and the 404
  page share the same quiet voice.
- A retired or waiting frame is reachable from the Fleet list only, and says what to do next.

## Known gaps and design debt

- **Pending validation:** owner iPhone checks (More-panel dim in Safari versus the installed web
  app, the Location map in iPhone standalone, the yellow tile on a real panel).
- **Planned change:** a frame type for photo frames would change the per-frame navigation and add a
  Photos page; `navigation.md` and `page-patterns.md` must be rewritten before it lands.
- **CSS debt:** legacy bare `button { height: 30px }` and accent submit base; raw buttons outside `.btn` on a few pages
  (`airlines_page.py`, `co_managers_card.py`, `pair_frame_page.py`, `update_page.py`); names `.runway-card`
  (Style look picker) and `.mobile-nav__link` (More Account row) reused; tokens repeated in four blocks of
  `style.css`; `style-place.css` copies the light palette for ink over the light map; mixed breakpoints
  (`959px` vs `959.98px`, `699px` vs `699.98px`); `layout.data_table(prose=, desc_columns=)` and its CSS are unused.
- **Colour debt:** the toast `pending` tone is the one orange left; the accent-vs-status separation floors were made for terracotta.
- **Strings and code:** dead id `nav.frame_tools`; `CONSOLE_NAV_ENTRIES` still lists Health, Device, Releases
  (filtered at render, their old addresses redirect); `ui_nav.py` comments still mention the hamburger.
- **To delete in a later release:** the frozen per-frame airline name files and per-frame artwork
  directories kept for rollback after names and artwork became fleet-wide.
- **Open decisions:** the desktop sidebar has no theme or language control (they live on Account); "at most six blurred
  elements" is no longer test-enforced; no web-app manifest (iOS Home Screen mode is detected by `navigator.standalone`).
