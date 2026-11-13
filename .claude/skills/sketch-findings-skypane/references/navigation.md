# Navigation

Code: `companion/ui_nav.py` (bars, More panel, sidebar), `ui_base.py` (routes, labels),
`ui_shell.py` (shell, sidebar footer, space switch), `console_routes.py` (Console entries),
`static/motion.js` (sliding pill), `static/modal.js` (More panel behaviour),
`companion/i18n_fr/nav.py` (French). Below 960px the bottom tab bar is the navigation; from
960px the glass sidebar is. Exactly one is in the accessibility tree (CSS hides the other),
both named "Primary navigation".

There is no hamburger, no gear toggle, no `.nav-status` strip and no space-switch cell. The
earlier hamburger design lives only in `sources/002-mobile-hamburger-nav.html`
(superseded). `nav-dropdown.js` is a 15-line file that only adds the `js` class.

## Phone: one floating tab bar for everyone

An opaque pill (`--glass-solid`, no blur), `position: fixed`, `left/right: max(8px, safe)`, `bottom: 6px + safe-bottom`,
68px high (`--tab-bar-h`), `--radius-pill`, z-index 20. Its edge shadow sits on a `.tab-bar::before`
layer behind the cells so the More sheet inside never inherits it. `view-transition-name: skypane-tab-bar` carries the bar across a page change as
one image. The cells are `flex: 1 1 auto; min-width: 44px` (unequal widths, fit measured at
360 and 320px), 56px high, icon over an 11px sentence-case label (no uppercase). The active
cell is an inner pill; one `.tab-bar__slider` moved by `motion.js` (view-transition-name
`skypane-tab-slider`) slides under the current or pressed cell. A tab press navigates with
no script too: the bar is plain links plus one native `<details>`.

| Space | Cells (left to right) |
|-------|-----------------------|
| Personal (administrator and user alike) | Home, Flights, Airlines, Style, Place, More |
| Console (administrator only) | Fleet (carries the severity dot), Users, Editor, Audit, More |

A page that belongs to no cell (Credits, Components, error pages) marks More as current, so
the pill is on every page. A bar with no cells (a frame's not-found page) renders More alone.
`<body class="has-tab-bar">` reserves the page clearance; `#tab-bar-end` makes the first
paint wait for the whole bar.

## More panel (`<details class="tab-bar__more">`)

Native `<details>`, so it works with scripts blocked. Content, top to bottom:
1. Grab handle.
2. Account row (`.mobile-nav__link.tab-bar__account`): avatar circle with the e-mail's
   initial, "Account" over the signed-in e-mail, chevron.
3. Administrators only: the Console card (`link_card_html`, subtitle "Fleet, users, audit")
   leading to the Console; inside the Console the same slot is the "My frame" card leading back.
4. "Settings" group: Theme and Language rows with a segmented control each (plain POST forms,
   one tap).
5. Sign out (soft-error button, POST form with CSRF).

On the Account page the panel holds the links only (that page already carries Language,
Theme and Sign out). While open: the page behind is dimmed and blurred by a fixed scrim
(`body:has(.tab-bar__more[open])::after`, on every page, including the Place map), the bar is
raised above the scrim, and `modal.js` rewrites the `theme-color` tags to the dimmed ground.
Tests: `test_browser_more_sheet.py`, `test_browser_more_scrim_cover.py`,
`test_browser_tab_bar_float.py`.

## Desktop sidebar (from 960px)

A floating glass panel (16px margin, `view-transition-name: skypane-sidebar`), full names,
44px links, current item a solid graphite (ivory in Dark) pill.
- Personal: Home, Flight history, Location and detection, Style, Airlines, then an Account
  group. Administrators also get a space switch (`space_switch_html`: Console / My frame) at
  the top of the sidebar.
- Console: eyebrow "Administration" over Fleet, Users; then Editor, Audit; then Account.
- Footer: Sign out only. Language and Theme live on the Account page; the desktop sidebar has
  no theme or language control.
Health, Device and Releases have no navigation entry: their pages mark Fleet as current
(`_FLEET_FOLDED_SLUGS`). `nav.frame_tools` ("Frame tools") is a dead string.

## Page names (EN / FR)

One full name per page for the title, document title and sidebar; the tab bar shows a
shorter word where the full name would not fit (about 52px wide at 11px at 360px).

| Page | Full name | Tab bar |
|------|-----------|---------|
| Home | Home / Accueil | Home / Accueil |
| Flights | Flight history / Historique des vols | Flights / Vols |
| Airlines | Airlines / Compagnies | Airlines / Compagnies |
| Style | Style / Style | Style / Style |
| Location | Location and detection / Lieu et détection | Place / Lieu |
| More | | More / Plus |
| Account | Account / Compte | (More) |
| Console: Fleet | Fleet / Flotte | Fleet / Flotte |
| Console: Users | Users / Utilisateurs | Users / Équipe |
| Console: Airline editor | Airline editor / Éditeur de compagnies | Editor / Éditeur |
| Console: Audit | Audit log / Journal d’audit | Audit / Journal |

Concept words: frame / cadre, look / allure ("special look" is "allure spéciale"), airline /
compagnie. Style is never called "Personalisation". A new page picks its full name and, only
if it must fit the bar, a word of it. French strings: `i18n_fr/nav.py`, `i18n_fr/admin_shell.py`, `i18n_fr/account.py`.

## Rules

- A change to a bar cell, a label or the More panel updates this file and
  `page-patterns.md` in the same PR.
- Every nav entry carries `aria-current="page"` when current; the More `<summary>` is current
  on pages no cell owns.
- Router stability: `console_routes.CONSOLE_NAV_ENTRIES` still lists Health, Device and
  Releases for routing; the renderer filters them out of the bars.
- Tests: `test_nav_personal_console.py`, `test_nav_spaces.py`, `test_browser_nav_spaces.py`,
  `test_browser_nav_alignment.py`, `test_browser_navigation_assist.py`.
- Coming: draft PR #378 (v1.3 photo milestone) makes a frame have a type, plane or photo. A
  photo frame's menu would be Home, Photos, Style, Account; the plane frame stays as above.
  That changes the personal bar per frame type. Rewrite this file before it lands.
