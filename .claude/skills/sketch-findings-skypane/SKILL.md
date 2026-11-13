---
name: sketch-findings-skypane
description: The companion web app's current design-system reference — colour and contrast, typography, spacing, cards, control density, navigation, and page patterns — maintained continuously across phases and auto-loaded during UI implementation on skypane.
---

# SkyPane companion design system

**As of:** commit `c9ce584` (origin/main), 2026-11-13, after Phase 61 round 39. Everything below
was checked against the code at that commit. `.planning/workstreams/v1-2/ROADMAP.md` and the
Phase 61 summaries are the live record of plan status.

**Keeping it current.** This skill is not updated automatically. Any PR that changes companion CSS
tokens, navigation, a component or a page layout (`companion/static/style*.css`, `companion/ui_*.py`,
`companion/pages/`) updates the matching file in `references/` and the "as of" line in the same PR.
Between that rule and review, the skill can be behind: when code and skill disagree, the code wins
and the skill gets fixed.

## Stack and boundaries

The companion is a stdlib-only Python HTTP service under `companion/` (`ThreadingHTTPServer`),
sign-in for administrators and users, English and French. Its look is hand-written CSS with no build
step: `companion/static/style.css` (tokens, shared components) plus per-area sheets
(`style-home|flights|place|airlines|display|admin|c-console|c-lists.css`) linked per page by
`page_styles.py`; the served CSS and JS are comment-stripped. Vanilla ES5 scripts in `companion/static/`,
all optional: every page works with scripts blocked. Vendored Leaflet 1.9.4 and OpenStreetMap tiles
serve the Place page only. The e-ink frame's own palette and fonts never cross into the companion.
Rendering helpers: `ui_base.py`, `ui_shell.py`, `ui_nav.py`, `ui_components.py`, `ui_groups.py`,
`ui_segmented.py`, `ui_modal.py`, `ui_save_bar.py`, `ui_filter.py`, `ui_entity_list.py`.

## Core rules at a glance

- **Direction:** a pale sky (Light) or ink (Dark) background painted on `<html>`, frosted glass
  groups and bars, system sans only, a neutral accent. No serif, no warm beige, no terracotta.
- **Colour:** Light canvas `#F1F3F6`, secondary `#E9EEF5`, border `#DAE1EB`, text `#17191F`, accent
  graphite `#1F2430` (hover `#343B4D`, on-accent white). Dark canvas `#161A24`, secondary `#1C222D`,
  border `#2A3040`, text `#F1F3F6`, accent ivory `#F2EFE9` (hover `#E2DED5`, on-accent `#14171F`).
  Status ok/warn/error `#16A34A/#D97706/#BE123C` (Dark `#4ADE80/#FBBF24/#FB7185`).
- **Sky + glass:** sky `#E7EEF7 > #F1F3F6 > #EDF1F6` (Dark `#12151D > #161A24 > #1A1F2B`);
  `--glass-bg` white .72 / .09, blur 22px (bars 26px), all blur inside one `@supports` block.
- **Radii:** control 14, card 22, sheet 28 (top corners), pill 32; portrait frame picture 5.
- **Type:** page title clamp 30-34px phone / 40-44px desktop, 700, tracking -0.03em; section/sub-page
  22px 600; card title 17px 600; body 16; secondary 15; caption and section label 13; tab 11, chart 10.
  No uppercase label voice. Mono only for identifiers.
- **Spacing:** 4, 8, 16, 24, 32, 48, 64px (`--space-xs..3xl`); sibling-card gap 24px.
- **Motion:** two durations plus a documented set of tokens (`--motion-fast` 180ms, `--motion-slow`
  2s, `--motion-enter` 400ms, stagger 60ms, spring, view-transition 260ms ...); no bare duration
  literal; budget enforced by `companion/test_companion_app_04.py`; reduced motion switches it off.
- **Targets:** every control is 44px. Minimum width 360px, no horizontal scroll (320px out of contract).
- **Bilingual:** every user-facing string is an `i18n.msg` with a French entry in `companion/i18n_fr/`;
  French must fit.
- **Dark / light:** Auto follows the OS; Light and Dark are explicit (`html[data-ui-theme]`);
  `theme-color` metas follow it. Every token lives in four blocks: edit all.
- **Navigation:** below 960px one floating bottom tab bar for everyone (Personal: Home, Flights,
  Airlines, Style, Place, More; Console: Fleet, Users, Editor, Audit, More); from 960px a glass sidebar.
- **Components:** use a catalogue helper (`.btn`, `ui_groups`, `ui_segmented`, `toast_html`, one Save
  bar); the admin `/components` page is the living catalogue.

## References

| File | Read when |
|------|-----------|
| `references/tokens-and-theming.md` | colours, sky and glass, radii, type, spacing, safe areas, dark/light, iOS Home Screen app |
| `references/components.md` | buttons, groups and rows, pills, segmented, switch, toast, dialogs, Save bar and leave dialog, app bar, frame menu |
| `references/navigation.md` | tab bar, More panel, sidebar, spaces, page names EN/FR, photo-frame change coming |
| `references/page-patterns.md` | Home, Flights, Place, Style, Airlines, Console and Device panel, Users, Account, Login, Components, splash |
| `references/motion.md` | motion tokens and budget test, page opening, view transitions, tab strip, splash, reduced motion |
| `references/accessibility.md` | 44px, focus, headings, contrast modules, HTTP 405 and CSRF, 360px |
| `references/i18n-bilingual.md` | EN/FR rules and tests |
| `sources/README.md` | the old sketches are history, not the design |

## What changed since 2026-11-10 (rounds 17-39, Phase 61; PR numbers in brackets)

Foundation and map (rounds 17-20, 26, 28)
- Round 17 (#330): Location map as document content; filter chips lost their counts. Round 18 (#331): compact Place sheet on phones.
- Round 20 (#336), 26 (#357), fix #363, fix #369: the Place map runs under the status bar and toolbar on iPhone (80px lead and tail, scroll lock, no added blur).
- Round 25 (#355): Airlines tabs and cards, smaller splash frame. #356: the Home Detection card names the active mode.
- Round 27 (#361): graphite logo with a night-mode favicon. Round 28 (#362): Account "Add your frame" button readable again.

Motion and loading (rounds 19, 24, 29, 32)
- Round 19 (#334): one page opening and one tab-strip animation everywhere (`data-page-open`, `data-tabs`).
- Round 24 (#342): the last audit-4 performance points. Round 29 (#364): thumbnails, page opening, motion, French fit.
- Round 32 (#368): one page-change motion (`html.page-crossfade`), Users table (option A).

Flights data (fixes)
- #358/#359: a thumbnail shows only a render that belongs to the flight (90s before, 10s after) and its name is stored per flight.

Robustness and forms (rounds 21, 22, 30, 31, 33, 37)
- Round 21 (#337), 22 (#338): audit-4 visual, workflow and performance findings.
- Round 30 (#365): toast, role confirmation, Save bar on Back, 500 page. Round 31 (#367): offline, session expiry
  (`session-guard.js`), Flights and Airlines speed.
- Round 33 (#370): HTTP 405 and HEAD, forms, headings, keyboard, upload messages.
- Round 37 (#375): refused pairing code kept for one showing, upload token out of the address.

Navigation and shell (rounds 34, 35, 38; fix #372)
- Round 34 (#371): one bottom tab bar for everyone; the Console switch moved into More.
- Round 35 (#373): More panel redesign (Account row, Console card, Settings group, scrim blur on every page).
- Fix #372: the app bar clears iOS's frost in the Home Screen app on every page (`--app-bar-drop`).
- Round 36 (#374): Style asks before leaving a sub-tab with an unsaved layout. Round 38 (#376): the unsaved-changes dialog on every
  page with a Save bar, also guarding the tab bar.
- Round 39 (#377): Device and version panel redesign.

Superseded by these: the hamburger and `.nav-status`, the space-switch cell, the terracotta/serif identity, the Flights
detail row, the Home greeting title, the old "two tokens, four keyframes" motion budget.

## Known gaps and design debt

- **In flight:** draft PR #378 (v1.3 photo milestone planning) gives a frame a type (planes or photos); a photo frame's menu
  would be Home, Photos, Style, Account. It changes the per-frame navigation and adds a Photos page; `navigation.md` and
  `page-patterns.md` must be rewritten before it lands. v1.3 phases 66-68 are not in the companion yet.
- **Pending validation:** owner iPhone checks (More-panel dim on every tab and every Save-bar page, Round 28 list) and the
  final validation plan 61-13.
- **Known test failure:** `companion/test_device_routes.py::TestPrefixCrawl::test_global_targets_are_never_prefixed` fails on the branch tip (3 `/display` variants).
- **CSS debt:** legacy bare `button { height: 30px }` and accent submit base; raw buttons outside `.btn` on a few pages; names
  `.runway-card` (Style look picker) and `.mobile-nav__link` (More Account row) reused; tokens repeated in four blocks of
  `style.css`; `style-place.css` copies the light palette for ink over the map; mixed breakpoints (`959px` vs `959.98px`,
  `699px` vs `699.98px`); duplicate `.history-cards ~ .data-table-wrap` rule; `/update` page keeps older markup than the Fleet panel.
- **Colour debt:** the toast `pending` tone is the one orange left; the accent-vs-status separation floors were made for terracotta.
- **Strings and code:** dead id `nav.frame_tools`; `CONSOLE_NAV_ENTRIES` still lists Health, Device, Releases (filtered at render);
  `ui_nav.py` comments still mention the hamburger.
- **Open decisions:** the desktop sidebar has no theme or language control (they live on Account); "at most six blurred
  elements" is no longer test-enforced; no web-app manifest (iOS Home Screen mode is detected by `navigator.standalone`).
