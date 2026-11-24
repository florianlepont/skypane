# Navigation

Code: `companion/ui_nav.py` (bars, More panel, sidebar, space switch), `ui_base.py` (routes,
labels), `ui_shell.py` (shell, sidebar footer, foreign-frame marker), `console_routes.py`
(Console entries), `static/motion.js` (sliding pill, active-tab tap), `static/modal.js` (More
panel behaviour), `companion/i18n_fr/nav.py` (French). Below 960px the bottom tab bar is the
navigation; from 960px the glass sidebar is. Exactly one is in the accessibility tree (CSS hides
the other), both named "Primary navigation".

There is no hamburger, no gear toggle, no `.nav-status` strip and no space-switch cell in the
bar. The earlier hamburger design lives only in `sources/002-mobile-hamburger-nav.html`
(superseded). `nav-dropdown.js` is a 15-line file that only adds the `js` class.

## One page order

The personal pages are one table (`_PERSONAL_PAGES` in `ui_nav.py`) read by both the sidebar
and the bar, so the two can never disagree: **Home, Flights, Airlines, Style, Location**, then
Account. The Console pages are likewise one list: **Fleet, Users, Editor, Audit, System**, then
Account. A test pins that the bar labels equal the sidebar labels in the same order, in both
languages, for an administrator and an owner.

## Phone: one floating tab bar for everyone

An opaque pill (`--glass-solid`, no blur), `position: fixed`, `left/right: max(8px, safe)`,
`bottom: 6px + safe-bottom`, 68px high (`--tab-bar-h`), `--radius-pill`, z-index 20. On a tablet
the bar and its More sheet are capped at `--tab-bar-max` (460px) and centred; the cap is
deliberate and unchanged. Its edge shadow sits on a `.tab-bar::before` layer behind the cells so
the More sheet inside never inherits it. `view-transition-name: skypane-tab-bar` carries the bar
across a page change as one image. The cells are `flex: 1 1 auto; min-width: 44px` (unequal
widths, fit measured at 360 and 320px), 56px high, icon over an 11px sentence-case label (no
uppercase). The active cell is an inner pill; one `.tab-bar__slider` moved by `motion.js`
(view-transition-name `skypane-tab-slider`) slides under the current or pressed cell. A tab press
navigates with no script too: the bar is plain links plus one native `<details>`.

Tapping the tab you are already on scrolls the page to the top (smooth, instant under reduced
motion) without loading the page again; on a sub-page of that tab the link still navigates.

| Space | Cells (left to right) |
|-------|-----------------------|
| Personal (administrator and user alike) | Home, Flights, Airlines, Style, Location, More |
| Console (administrator only) | Fleet (carries the severity dot), Users, Editor, System, More (Account, Audit, back to My frames) |

A page that belongs to no cell (Credits, Components, error pages) marks More as current, so the
pill is on every page. A bar with no cells (a frame's not-found page) renders More alone.
`<body class="has-tab-bar">` reserves the page clearance; `#tab-bar-end` makes the first paint wait
for the whole bar.

## More panel (`<details class="tab-bar__more">`)

Native `<details>`, so it works with scripts blocked. Content, top to bottom:
1. Grab handle: a drawn 44x5 pill, decorative (`aria-hidden`). Keyboard close is Escape and the
   More cell; screen-reader close is the More summary.
2. Account row (`.mobile-nav__link.tab-bar__account`): avatar circle with the e-mail's initial,
   "Account" over the signed-in e-mail, chevron.
3. Console pages that live only in More (Audit).
4. Administrators only: the space card (`link_card_html`): in the personal space "Console"
   (subtitle "Fleet, users, audit"); inside the Console the same slot is the "My frames" card
   leading back.
5. "Settings" group: Theme and Language rows with a segmented control each (plain POST forms,
   one tap).
6. Sign out (soft-error button, POST form with CSRF).

At 320px the rows use 8px side padding, the label column is 6.25rem and the theme segments 2px
side padding, so French "Auto / Clair / Sombre" and English "Language" show whole. On the Account
page the panel holds the links only (that page already carries Language, Theme and Sign out).
While open: the page behind is dimmed and blurred by a fixed scrim
(`body:has(.tab-bar__more[open])::after`, on every page, including the Location map), the bar is
raised above the scrim, `modal.js` rewrites the `theme-color` tags to the dimmed ground, and the
Home loops stand still. Whether the dim also reads in Safari (versus the installed web app) is an
owner device check. Tests: `test_browser_more_sheet.py`, `test_browser_more_scrim_cover.py`,
`test_browser_tab_bar_tablet_cap.py`.

## Desktop sidebar (from 960px)

A floating glass panel (16px margin, `view-transition-name: skypane-sidebar`), full names, 44px
links, current item a solid graphite (ivory in Dark) pill.
- Personal: Home, Flights, Airlines, Style, Location, then an Account group.
- Console: eyebrow "Administration" over Fleet, Users, Editor, Audit log, System; then Account.
- Administrators also get the space switch (`space_switch_html`) above the sidebar navigation as
  its own landmark: a two-segment control reading **My frames | Console** in that order, the
  current segment marked with a check and `aria-current`.
- Footer: Sign out only. Language and Theme live on the Account page; the desktop sidebar has
  no theme or language control.
Health, Device and Releases have no navigation entry: their pages mark Fleet as current
(`_FLEET_FOLDED_SLUGS`), and their old addresses redirect (see `page-patterns.md`).
`nav.frame_tools` ("Frame tools") is a dead string.

## Foreign-frame marker and "Back to Fleet"

When an administrator opens a personal page of a frame they neither own nor co-manage, a strong
marker sits at the top of the page (`ui_components.frame_notice_markup`, shown by
`ui_shell.frame_notice_html`): see `components.md`. Its button returns to **the frame being
viewed** in Fleet (`/fleet?frame=<id>`), not to the first frame; a `frame` named in the request is
ignored and with no frame in scope it is plain `/fleet`.

## Page names (EN / FR)

One name per page, the same in the title, the document title, the sidebar and the tab bar (no
shorter bar word except the two Console ones noted).

| Page | Name | Tab bar |
|------|------|---------|
| Home | Home / Accueil | same |
| Flights | Flights / Vols | same |
| Airlines | Airlines / Airlines | same |
| Style | Style / Style | same |
| Location | Location / Lieu | same |
| More | More / Plus | |
| Account | Account / Compte | (More) |
| Console: Fleet | Fleet / Flotte | same |
| Console: Users | Users / Utilisateurs | Users / Équipe |
| Console: Airline editor | Airline editor / Éditeur de compagnies | Editor / Éditeur |
| Console: Audit | Audit log / Journal d’audit | (More) |
| Console: System | System / Système | same |
| Space switch and the Console's way back | My frames / Mes cadres | |

Concept words: frame / cadre, look / allure ("special look" is "allure spéciale"), airline /
compagnie (the French page and tab stay "Airlines" so the label fits the six-tab bar). Style is never called "Personalisation".
A new page picks its name and, only if it must fit the bar, a short word. French strings:
`i18n_fr/nav.py`, `i18n_fr/admin_shell.py`, `i18n_fr/account.py`.

## Rules

- A change to a bar cell, a label or the More panel updates this file and `page-patterns.md` in
  the same PR.
- Every nav entry carries `aria-current="page"` when current; the More `<summary>` is current on
  pages no cell owns.
- Router stability: `console_routes.CONSOLE_NAV_ENTRIES` still lists Health, Device and Releases
  for routing; the renderer filters them out of the bars.
- Opening a page from the Console More sheet leaves the bar where a direct load puts it and the
  scroll at the top (tested at 390px, both languages).
- Tests: `test_nav_personal_console.py`, `test_nav_spaces.py`, `test_browser_nav_spaces.py`,
  `test_browser_tab_bar_roles.py`, `test_browser_nav_alignment.py`,
  `test_browser_navigation_assist.py`.
- Planned: a photo-frame type would make the personal bar depend on the frame type (Home, Photos,
  Style, Account). Rewrite this file before it lands.
