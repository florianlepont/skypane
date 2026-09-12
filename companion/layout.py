"""companion/layout.py — the escaped page shell and 06-UI-SPEC.md's
component library for the SkyPane companion service.

stdlib `html` and `datetime` only — no imports from server/, and
nothing from companion.auth beyond the UI-theme cookie name.

06-RESEARCH.md's Pitfall 2: stdlib string formatting has no
autoescaping, so every interpolation site is a manual opt-in.
`escape_html()` is defined once, here, and every `companion/pages/*.py`
module (plans 06-05 through 06-09) must import and use it — no page
module may reach into the stdlib `html` module's escaping function
directly, and no page module may build markup without going through
this one helper. That single-helper discipline is what makes the
escaping obligation auditable with one grep across the whole package.
"""
import html
from datetime import datetime
from zoneinfo import ZoneInfo

from companion.auth import UI_THEME_COOKIE_NAME
# 20-01-PLAN.md Task 2/3 (D-01..D-09): companion.i18n/companion.prefs
# are both shared, page-independent modules (like companion.auth
# above) — layout.py importing them carries no cycle, since neither
# imports anything from this module or from companion.app
# (companion.app is the one that imports layout.py, never the
# reverse).
import companion.i18n as i18n
import companion.prefs as prefs

SITE_TITLE = "SkyPane"

# Phase 18 (audit finding H-3/H-4): every timestamp used to render as a
# bare UTC clock ("21:50 UTC") with the date hidden in a tooltip. The
# household this frame hangs in lives on Paris time, so visible
# timestamps now render in LOCAL_TZ, and carry the day once the value
# is no longer "today" ("3 Sep 21:50"). The full ISO string stays in the
# `title` attribute for anyone who needs the exact instant.
LOCAL_TZ = ZoneInfo("Europe/Paris")
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# D-07, 20-03-PLAN.md Task 2: the French month-abbreviation table
# local_clock_text() selects instead of _MONTH_ABBR above under a
# French request — same twelve-entry shape, parallel index.
_MONTH_ABBR_FR = ("janv.", "févr.", "mars", "avr.", "mai", "juin",
                   "juil.", "août", "sept.", "oct.", "nov.", "déc.")

# Ordered (route, label) pairs — 06-UI-SPEC.md's Page Inventory. Login is
# deliberately absent: it is shown instead of any page when unauthenticated,
# never as a nav tab.
# Companion audit / UX refactor (phase 18): the flat four-tab set is
# replaced by two GROUPS of tabs — the everyday group (no label) that a
# household member uses without any technical background, and an
# "Advanced" group for setup, diagnostics and debugging. Each entry is
# (route, label). NAV_TABS below is DERIVED from this tuple so every
# existing consumer of the flat (route, label) sequence (the login
# `?next=` allowlist, `_referring_tab()`, the page-title map guard, both
# nav renderers) keeps working unchanged.
HOME_ROUTE = "/"
DISPLAY_ROUTE = "/display"
FLIGHTS_ROUTE = "/flights"
AIRLINES_ROUTE = "/airlines"
HEALTH_ROUTE = "/health"
DEVICE_ROUTE = "/device"

ADVANCED_GROUP_LABEL = "Advanced"

NAV_GROUPS = (
    ("", (
        (HOME_ROUTE, "Home"),
        (DISPLAY_ROUTE, "Display"),
        (FLIGHTS_ROUTE, "Flights"),
        (AIRLINES_ROUTE, "Airlines"),
    )),
    (ADVANCED_GROUP_LABEL, (
        (HEALTH_ROUTE, "Health"),
        (DEVICE_ROUTE, "Device"),
    )),
)

# Ordered (route, label) pairs, flattened from NAV_GROUPS in display
# order. Login is deliberately absent: it is shown instead of any page
# when unauthenticated, never as a nav tab. The old "/settings" and
# "/history" routes are not tabs any more — companion/app.py keeps both
# as fixed 303 redirects (to DISPLAY_ROUTE and FLIGHTS_ROUTE) so a stale
# bookmark still lands somewhere useful.
NAV_TABS = tuple(
    (route, label) for _group_label, entries in NAV_GROUPS for route, label in entries)

# The slug a route is identified by inside the nav renderers and by
# page_shell()'s `active` argument. The home route "/" has no path
# segment to strip, so it gets an explicit slug rather than "".
HOME_NAV_SLUG = "home"


def nav_slug(route):
    """The `active` slug for a NAV_TABS route: "home" for HOME_ROUTE,
    otherwise the route with its leading slash removed."""
    if route == HOME_ROUTE:
        return HOME_NAV_SLUG
    return route.lstrip("/")


# --- 06.6.1-05: hamburger nav DOM contract (D-06) -----------------------
#
# The exact literals companion/static/nav-dropdown.js looks up via
# getElementById()/classList. Duplicated here rather than imported from
# that JS file — there is no such import path, a Python module cannot
# import a JS file — so if any of these three drifts from the JS file's
# own literals, the menu silently stops opening on a phone with no
# automated signal from either file in isolation. The Task 3 three-file
# DOM contract guard (06.6.1-05-PLAN.md) reads the JS source and the
# stylesheet from disk and requires all three to appear in both AND in
# the rendered page.
NAV_TOGGLE_ID = "site-nav-toggle"
MOBILE_NAV_ID = "mobile-nav"
MOBILE_NAV_OPEN_CLASS = "mobile-nav--open"

# The fixed accessible name for the hamburger toggle button
# (06.6.1-UI-SPEC.md's Copywriting Contract). State is communicated
# entirely through aria-expanded, which is the correct ARIA disclosure
# pattern — swapping this label to a close verb on open would make the
# announced name change under the user mid-interaction. Do not add logic
# that varies it BY STATE — it is still translated through i18n.t() at
# its one render site (D-05, 20-12-PLAN.md Task 1: a real completeness
# gap this constant's own render site had left un-wrapped).
NAV_TOGGLE_LABEL = "Open menu"

# Must equal companion/app.py's NAV_SCRIPT_ROUTE exactly. Duplicated
# rather than imported because companion/pages/__init__.py's boundary —
# and a plain import cycle, since app.py imports this module — forbids
# the reverse direction, exactly as health_page.BATTERY_TREND_SCRIPT_SRC's
# own comment already states for its own route pair. The Task 3 checks
# assert the equality.
NAV_DROPDOWN_SCRIPT_SRC = "/static/nav-dropdown.js"

# 06.6.3: four more pre-auth static JS route constants, same
# duplicated-not-imported contract as NAV_DROPDOWN_SCRIPT_SRC above —
# each must equal companion/app.py's matching *_SCRIPT_ROUTE constant
# exactly (that module's own Task 2 checks assert the equality).
DIRTY_STATE_SCRIPT_SRC = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_SRC = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_SRC = "/static/copy-button.js"
FRESHNESS_SCRIPT_SRC = "/static/freshness.js"

# D-20 (06.6.4.1-02): must equal companion/app.py's PANEL_LOOKUP_SCRIPT_ROUTE
# exactly, same duplicated-not-imported contract as the four constants above.
PANEL_LOOKUP_SCRIPT_SRC = "/static/panel-lookup.js"

# Quick task 260903-peo (UIR-19): must equal companion/app.py's
# FLASH_CLEANUP_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above.
FLASH_CLEANUP_SCRIPT_SRC = "/static/flash-cleanup.js"

# 19-04-PLAN.md (D-18/A-35): must equal companion/app.py's
# POLL_COOLDOWN_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above.
POLL_COOLDOWN_SCRIPT_SRC = "/static/poll-cooldown.js"

# 19-11-PLAN.md Task 2 (D-08/A-26): must equal companion/app.py's
# CONFIRM_SUBMIT_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the ninth static script.
CONFIRM_SUBMIT_SCRIPT_SRC = "/static/confirm-submit.js"

# 20-08-PLAN.md Task 3 (D-22..D-24/D-32): must equal companion/app.py's
# THEME_PREVIEW_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the tenth static script.
THEME_PREVIEW_SCRIPT_SRC = "/static/theme-preview.js"

# 21-03-PLAN.md Task 2 (D-15/R-12): must equal companion/app.py's
# FLIGHT_ROWS_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the eleventh static script.
FLIGHT_ROWS_SCRIPT_SRC = "/static/flight-rows.js"

UI_THEME_CHOICES = ("auto", "light", "dark")

# D-16/D-19 (20-01-PLAN.md Task 2): the quick-action form protocol,
# moved here from companion/pages/home_page.py's own identical
# constants so both companion/app.py and, from 20-07, config_page.py
# can share one home for it — a page module may never import another
# page module. home_page.py keeps its own copies untouched until
# 20-06 deletes them with the rest of Home's quick-action code; the
# two definitions are byte-identical in the meantime.
QUICK_STATE_FIELD = "state"
QUICK_STATE_ON = "on"
QUICK_STATE_OFF = "off"

_STATUS_DOT_CLASSES = {
    "ok": "dot--ok",
    "warn": "dot--warn",
    "error": "dot--error",
}
_DEFAULT_STATUS_DOT_CLASS = _STATUS_DOT_CLASSES["warn"]

_STAT_TILE_BORDER_CLASSES = {
    "ok": "stat-tile--ok",
    "warn": "stat-tile--warn",
    "error": "stat-tile--error",
}
_DEFAULT_STAT_TILE_CLASS = "stat-tile--accent"

# quick task 260902-gjj (ISSUE 2): card_status_class()'s own whitelist,
# kept as bare suffixes (not full class names) so the caller's own base
# class never has to be typed twice.
_CARD_STATUS_SUFFIXES = {
    "ok": "--ok",
    "warn": "--warn",
    "error": "--error",
}

# --- 06.6.1-04: icon sprite (D-02) -------------------------------------
#
# The whitelist. Originally capped at exactly five ids by
# 06.6.1-UI-SPEC.md's Design System contract. 06.6.2-05 (D-17) supersedes
# that cap: five per-nav-label icons (`icon-nav-*`) are added below so
# every sidebar/mobile-nav label carries a small outline glyph — the
# whitelist grows from five to ten members, and this is now the current
# whole set again, not an incomplete one. The hamburger member is
# consumed by plan 06.6.1-05's mobile-nav toggle button; it is defined
# here anyway (rather than by that later plan) so the sprite in
# ICON_DEFS_HTML stays the single write site for every icon in the app,
# never two.
ICON_IDS = (
    "icon-device",
    "icon-pipeline",
    "icon-corroboration",
    # quick task 260902-j8w: as of this quick task, "icon-battery" has no
    # consumer anywhere in the app — companion/pages/health_page.py's
    # ICON_BATTERY constant and its one call site (the Battery-trend
    # section heading) were both removed at the developer's own
    # instruction. Retained here anyway, on purpose, not as an
    # oversight: pruning it would force a matching `<symbol>` deletion
    # below plus four assertion edits in test_companion_app.py's
    # `_icon_sprite_integrity()` (the fourteen-member count, the
    # duplicate check, the symbol-id/ICON_IDS set-equality check, and
    # the `<symbol` count) — a cross-page change to this shared
    # component, well outside a one-heading-glyph removal's scope. This
    # whitelist is an injection guard on icon_html()'s fragment
    # reference, not a usage index of what is currently rendered —
    # "icon-nav-preview" below is this file's existing precedent for
    # exactly that reading. The sprite is `display: none`
    # (companion/static/style.css's `.icon-defs` rule) and the retained
    # symbol costs roughly 200 bytes. Pruning `icon-battery` (and its
    # `<symbol>` below, and the four test_companion_app.py assertions)
    # is a real, optional follow-up the developer can take or decline —
    # not done here.
    "icon-battery",
    "icon-hamburger",
    "icon-nav-config",
    "icon-nav-health",
    "icon-nav-airlines",
    "icon-nav-history",
    # 06.6.4.1-08 (D-22): stays a whitelist member even though NAV_TABS/
    # NAV_ICON_IDS no longer reference a "preview" nav tab — its consumer
    # is now companion/pages/history_page.py's View-panel trigger button
    # (the eye glyph on each row's "View panel near this time" control),
    # not a nav tab. Do not remove this as apparently-orphaned: an id
    # outside this whitelist makes icon_html() silently return "" and the
    # trigger button would render an empty box with no error.
    "icon-nav-preview",
    "icon-nav-home",
    "icon-nav-flights",
    "icon-nav-device",
    "icon-nav-display",
    "icon-power",
    "icon-moon",
)

# 06.6.3: four more icons for the per-page redesign plans (D-05/D-23/
# D-12/D-20) grow the whitelist from ten to fourteen. Appended, not
# reordered, so ICON_DEFS_HTML's own symbol-id/ICON_IDS agreement check
# stays a straightforward set comparison.
ICON_IDS = ICON_IDS + (
    "icon-check",
    "icon-copy",
    "icon-refresh",
    "icon-search",
)

# quick task 260903-df3: one more icon for the Airlines lightbox replace
# zone (the framed action area's upload glyph). Appended, not merged into
# either tuple above, for the same "appended, not reordered" reason those
# tuples' own comments already state — grows the whitelist from fourteen
# to fifteen.
ICON_IDS = ICON_IDS + (
    "icon-upload",
)

# One shared inline sprite, emitted once per document by page_shell().
# `display: none` (companion/static/style.css's `.icon-defs` rule) still
# lets every <use href="#icon-..."> reference below resolve correctly —
# that is the entire technique. Because of that, this sprite must never
# be moved inside a conditionally-rendered region: a `<use>` referencing
# a symbol that isn't in the DOM at all (not merely hidden) resolves to
# nothing.
#
# Each symbol carries fill="none"/stroke="currentColor" so a single CSS
# `color` property drives the whole glyph — this is what lets
# .stat-tile__icon's per-status tint rules (companion/static/style.css)
# work with no second colour mapping to keep in sync. The four tile
# icons use a 20x20 viewBox; the hamburger (plan 06.6.1-05) uses 24x24
# and is three horizontal lines, per the UI-SPEC. Every glyph is built
# from plain <path>/<line>/<rect>/<circle> primitives — legible outline
# shapes, not detailed illustration.
ICON_DEFS_HTML = (
    '<svg class="icon-defs" aria-hidden="true" focusable="false">'
    "<defs>"
    '<symbol id="icon-device" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="5" y="2" width="10" height="16" rx="2"/>'
    '<path d="M7.5 10l2 2 4-4.5"/>'
    "</symbol>"
    '<symbol id="icon-pipeline" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 16v-3"/>'
    '<path d="M6.5 11.5a5 5 0 0 1 7 0"/>'
    '<path d="M4 8.5a9 9 0 0 1 12 0"/>'
    "</symbol>"
    '<symbol id="icon-corroboration" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="8" cy="10" r="5"/>'
    '<circle cx="12" cy="10" r="5"/>'
    "</symbol>"
    '<symbol id="icon-battery" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="2" y="6" width="14" height="8" rx="1.5"/>'
    '<path d="M18 8.5v3"/>'
    '<path d="M5 9v2"/>'
    "</symbol>"
    '<symbol id="icon-hamburger" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<line x1="4" y1="7" x2="20" y2="7"/>'
    '<line x1="4" y1="12" x2="20" y2="12"/>'
    '<line x1="4" y1="17" x2="20" y2="17"/>'
    "</symbol>"
    '<symbol id="icon-nav-config" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 5h8M15 5h2"/><circle cx="12" cy="5" r="2"/>'
    '<path d="M3 10h2M9 10h8"/><circle cx="7" cy="10" r="2"/>'
    '<path d="M3 15h8M15 15h2"/><circle cx="12" cy="15" r="2"/>'
    "</symbol>"
    '<symbol id="icon-nav-health" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M2 10h4l2-5 3 10 2-5h5"/>'
    "</symbol>"
    '<symbol id="icon-nav-airlines" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 3h7l7 7-7 7-7-7z"/><circle cx="7" cy="7" r="1.5"/>'
    "</symbol>"
    '<symbol id="icon-nav-history" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/>'
    "</symbol>"
    '<symbol id="icon-nav-preview" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M2 10s3-5 8-5 8 5 8 5-3 5-8 5-8-5-8-5z"/>'
    '<circle cx="10" cy="10" r="2.5"/>'
    "</symbol>"
    # 06.6.3: four more glyphs (D-05/D-23/D-12/D-20), same viewBox/stroke
    # language as the ten above.
    '<symbol id="icon-nav-home" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 9.5L10 3.5l7 6"/><path d="M5 8.5V16.5h4v-4h2v4h4V8.5"/>'
    "</symbol>"
    '<symbol id="icon-nav-flights" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M2.5 12l4-1.5L14 3.5a1.6 1.6 0 0 1 2.3 2.3L9.5 13.5 8 17.5l-1.5-3.5z"/>'
    '<path d="M6.5 14l-2 2"/>'
    "</symbol>"
    '<symbol id="icon-nav-device" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="5" y="5" width="10" height="10" rx="2"/><rect x="8" y="8" width="4" height="4"/>'
    '<path d="M8 2v3M12 2v3M8 15v3M12 15v3M2 8h3M2 12h3M15 8h3M15 12h3"/>'
    "</symbol>"
    '<symbol id="icon-nav-display" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="2.5" y="3.5" width="15" height="11" rx="1.5"/><path d="M7 17.5h6"/>'
    '<path d="M6 11l2.5-3 2 2.5 1.5-1.5 2 2"/>'
    "</symbol>"
    '<symbol id="icon-power" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 3v7"/><path d="M6 6a6 6 0 1 0 8 0"/>'
    "</symbol>"
    '<symbol id="icon-moon" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 12.5A7 7 0 0 1 7.5 4a7 7 0 1 0 8.5 8.5z"/>'
    "</symbol>"
    '<symbol id="icon-check" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M4 10.5l4 4 8-9"/>'
    "</symbol>"
    '<symbol id="icon-copy" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="3" y="3" width="10" height="10" rx="1.5"/>'
    '<path d="M7 17h8a2 2 0 0 0 2-2V7"/>'
    "</symbol>"
    '<symbol id="icon-refresh" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M16 10a6 6 0 1 1-2-4.5"/>'
    '<path d="M16 2.5v4h-4"/>'
    "</symbol>"
    '<symbol id="icon-search" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="8.5" cy="8.5" r="5.5"/>'
    '<path d="M13.5 13.5L17.5 17.5"/>'
    "</symbol>"
    # quick task 260903-df3: one more glyph, same viewBox/stroke language
    # as the fourteen above — the Airlines lightbox replace zone's upload
    # arrow-over-tray.
    '<symbol id="icon-upload" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 13V3"/>'
    '<path d="M6 7l4-4 4 4"/>'
    '<path d="M3.5 13v3a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5v-3"/>'
    "</symbol>"
    "</defs>"
    "</svg>"
)

# The tint class stat_tile() adds to its own icon instance. Its
# counterpart is companion/static/style.css's `.stat-tile__icon` (and
# the per-status `.stat-tile--* .stat-tile__icon` overrides) — Task 1's
# test harness reads that stylesheet from disk and asserts this class
# name actually appears in it, guarding against the two silently
# drifting apart.
STAT_TILE_ICON_CLASS = "stat-tile__icon"

# --- 06.6.1-04 Task 3: Health nav-tab notification dot (D-02) ---------
#
# The Health route's slug, matching what _nav_links() already computes
# (`route.lstrip("/")`) — named once so a renderer can identify the
# Health link without re-deriving it from an already-escaped route
# string.
HEALTH_NAV_SLUG = "health"

# 06.6.2-05 (D-17): slug -> icon-id, one per NAV_TABS entry. Consumed by
# sidebar_nav()/_mobile_nav_html() via _nav_links()'s already-computed
# `slug` (route.lstrip("/")) — a slug not present here (which cannot
# happen for a real NAV_TABS entry) falls through icon_html()'s own
# whitelist-fallback ("" for an unrecognised id), never a KeyError.
NAV_ICON_IDS = {
    # Phase 18: keyed by nav_slug(route). "flights" keeps the History
    # clock glyph; Home/Display/Device get their own symbols above.
    "home": "icon-nav-home",
    "display": "icon-nav-display",
    "flights": "icon-nav-history",
    "airlines": "icon-nav-airlines",
    "health": "icon-nav-health",
    "device": "icon-nav-device",
}

# 06.6.2-05 (UXA-10): the fragment id the skip-link's first-focusable
# <a href="#..."> points at and <main> carries as its own id. Named once
# so page_shell() never has the two literals drift apart.
SKIP_LINK_TARGET_ID = "main-content"

# 06.6.2-05 (UXA-10): a zero-external-dependency local favicon — a data
# URI needs neither a new static file nor a new route. #B13F16 is the
# light-mode --color-accent token (companion/static/style.css, plan
# 06.6.2-01). Held as its own module constant (rather than inlined
# directly in page_shell()'s format string) specifically so plan
# 06.6.2-07's new login_shell() function can reuse this exact literal
# later without duplicating it.
FAVICON_LINK_HTML = (
    '<link rel="icon" href="data:image/svg+xml,'
    '%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 20 20%27%3E'
    '%3Crect width=%2720%27 height=%2720%27 rx=%274%27 fill=%27%23B13F16%27/%3E'
    '%3Ctext x=%2710%27 y=%2714%27 text-anchor=%27middle%27 '
    'font-family=%27Georgia,serif%27 font-size=%2712%27 fill=%27%23FFFFFF%27'
    '%3ES%3C/text%3E%3C/svg%3E">'
)

# The dot's own class, layered on top of the existing .dot/.dot--error
# classes (see _health_alert_markup()) rather than a new colour. Its
# counterpart is companion/static/style.css's `.nav-notification` rule
# — Task 3's test harness reads that stylesheet from disk and asserts
# this class name actually appears in it.
NAV_NOTIFICATION_CLASS = "nav-notification"

# 06.6.1-UI-SPEC.md's Copywriting Contract, verbatim: appended (not
# substituted) after the "Health" nav label text via a visually-hidden
# span, so assistive tech announces "Health — attention needed" rather
# than losing the word "Health" to an aria-label override. Translated
# through i18n.t() at its one render site (D-05, 20-12-PLAN.md Task 1:
# a real completeness gap this constant's own render site had left
# un-wrapped).
HEALTH_ALERT_SUFFIX_TEXT = " — attention needed"


def icon_html(icon_id, size=20, extra_class=""):
    """A `<svg>` referencing one symbol from ICON_DEFS_HTML via `<use>`,
    or the empty string when `icon_id` is not a member of ICON_IDS.

    This is a whitelist, not a sanitiser — the same discipline
    status_dot() and stat_tile() already apply to their own state
    arguments. `icon_id` becomes a `#`-prefixed fragment identifier
    inside a `<use href="...">` attribute; an id that reached the output
    unchecked would be an attacker-influenceable fragment reference. An
    unrecognised id instead fails visibly-but-safely — a missing icon,
    not a dangling or injectable reference.

    The explicit `width`/`height` attributes are belt-and-braces against
    companion/static/style.css's `.icon` sizing rule being lost or
    overridden: an `<svg>` with neither an attribute nor a CSS size
    renders at the SVG default 300x150 and would blow the layout apart.
    This mirrors how the battery sparkline already carries both fixed
    attributes and a CSS override.

    `aria-hidden="true"` is set unconditionally: every icon in this app
    sits beside its own visible text label — a tile caption, a nav link
    label, a filter-bar/pill label — so the icon is decorative and
    announcing it would duplicate the label. Do not "improve" this by
    adding a `<title>`. (SUPERSEDED, quick task 260902-j8w: a section
    heading — Health's `Battery trend` — used to be named here too, as
    the one place a glyph sat beside a heading rather than a tile/control
    label. That heading's glyph was removed at the developer's own
    instruction; glyphs in this app are now a tile/control affordance
    only, never a heading one.)
    """
    if icon_id not in ICON_IDS:
        return ""
    css_class = "icon"
    if extra_class:
        css_class = "%s %s" % (css_class, extra_class)
    return (
        '<svg class="%s" width="%d" height="%d" aria-hidden="true" '
        'focusable="false"><use href="#%s"></use></svg>'
    ) % (css_class, size, size, icon_id)


def escape_html(value):
    """Coerce `value` to its escaped string form for safe HTML interpolation.

    None becomes an empty string; any other non-string is coerced via
    str() first. Never raises, so a malformed upstream value (an
    ADS-B/adsbdb-sourced airline name, callsign, or unresolved prefix)
    degrades to an escaped string instead of crashing a page render.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


# --- 06.6-01: shared "absolute + relative" timestamp helpers (D-02) ----
#
# Promoted verbatim (in logic) from companion/pages/health_page.py's own
# private copies, which is why this section exists here rather than in
# each page module: companion/pages/__init__.py forbids one page module
# importing another, so a helper every page module needs to reach must
# live in this shared layer instead. health_page.py's Device check-in
# and ADS-B pipeline rows already ship the "ISO (Nm ago)" format this
# promotes; 06.6-03 (History + Preview, wave 2) consumes these same four
# functions rather than duplicating the logic a third time.


def parse_iso(ts):
    """Parse `ts` as an ISO-8601 datetime, or return None.

    Never raises: a non-`str` input or a string `datetime.fromisoformat()`
    cannot parse both degrade to None rather than propagating a
    TypeError/ValueError into a page render.
    """
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def age_seconds(ts, now_ts):
    """The number of seconds between `ts` and `now_ts` (both parsed via
    parse_iso()), or None when either side fails to parse — including
    when one side is timezone-naive and the other timezone-aware, which
    parse_iso() alone cannot catch since each string parses fine on its
    own; only the subtraction raises.
    """
    parsed = parse_iso(ts)
    now_parsed = parse_iso(now_ts)
    if parsed is None or now_parsed is None:
        return None
    try:
        return (now_parsed - parsed).total_seconds()
    except TypeError:
        return None


# D-07, 20-03-PLAN.md Task 2: the French unit-suffix table
# relative_age_text()'s French branch consumes below, in the same
# "fixed dict, membership lookup, documented fallback" shape
# _STATUS_DOT_CLASSES already uses. Kept complete (all four English
# unit letters) even though the "s" entry is never actually reached
# (the seconds bucket always short-circuits to "à l'instant" before
# consulting this table) — the same audit-by-grep discipline every
# other fixed-vocabulary dict in this module follows.
_AGE_UNIT_SUFFIX_FR = {
    "s": "s",
    "m": "min",
    "h": "h",
    "d": "j",
}


def relative_age_text(age_seconds, lang=None):
    """"Ns ago"/"Nm ago"/"Nh ago"/"Nd ago" using the s/m/h/d threshold
    ladder this app already ships on the Device/Pipeline rows. A
    negative age (clock skew) is clamped to 0 rather than read as
    "in the future".

    `lang` (D-07, 20-03-PLAN.md Task 2) is a trailing keyword whose
    `None` resolves to `prefs.current_lang()` — every pre-existing call
    site passes only the positional `age_seconds` and keeps getting the
    identical English string this function has always returned; the
    English branch below is byte-for-byte unchanged. Only a French
    request (an explicit `lang="fr"`, or a request whose
    `prefs.current_lang()` resolves to `"fr"`) takes the French branch.

    French collapses the whole under-a-minute bucket into one
    "à l'instant" ("just now") regardless of the exact second count —
    the idiomatic French phrasing 20-CONTEXT.md's D-07 names, rather
    than a literal "il y a %d secondes". The minute/hour/day buckets
    read "il y a N <unit>" (a real U+00A0 non-breaking space
    between the number and the unit, per D-09), with the unit taken
    from `_AGE_UNIT_SUFFIX_FR` above and the connector taken from the
    `"%s ago"` catalogue entry — the copy for both lives in
    `companion/i18n_fr/health.py`, read here through `i18n.t_lang()`
    rather than duplicated as a module literal.
    """
    age_seconds = max(0, int(age_seconds))
    if lang is None:
        lang = prefs.current_lang()
    if lang == "fr":
        if age_seconds < 60:
            return i18n.t_lang("just now", "fr")
        if age_seconds < 3600:
            value, unit = age_seconds // 60, "m"
        elif age_seconds < 86400:
            value, unit = age_seconds // 3600, "h"
        else:
            value, unit = age_seconds // 86400, "d"
        quantity = "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
        return i18n.t_lang("%s ago", "fr") % quantity
    if age_seconds < 60:
        return "%ds ago" % age_seconds
    if age_seconds < 3600:
        return "%dm ago" % (age_seconds // 60)
    if age_seconds < 86400:
        return "%dh ago" % (age_seconds // 3600)
    return "%dd ago" % (age_seconds // 86400)


def absolute_and_relative(ts, now_ts, fallback="no reading yet", lang=None):
    """"<ts> (<relative age> ago)" — the house "absolute + relative"
    timestamp format (D-02), already shipped on this page's Device
    check-in and ADS-B pipeline rows and now shared for every caller.

    Returns `fallback` when `ts` is falsy (None or empty string); returns
    `ts` unchanged (absolute only, no relative suffix) when age_seconds()
    cannot parse either side — an unparseable or missing `now_ts` — never
    raising. This is a deliberate hardening over the pre-promotion
    health_page.py path, where an empty-string `ts` would have reached
    the relative-age helper as `None` and raised a TypeError mid-render.

    The return value is plain, unescaped text — the same contract
    status_dot()'s `label` parameter already carries. Every caller must
    keep escaping it: wrap it in escape_html() directly, or hand it to a
    builder such as data_table() that already escapes every cell it is
    given.

    Absolute-first ordering (the ISO string first, the relative age in
    parentheses) is this app's shipped, canonical convention and must
    not be reversed — 06.3-UI-SPEC.md's Typography section shows a
    relative-first example, but that is illustrative prose no 06.3 plan
    task implements or depends on (06.6-RESEARCH.md Open Question 1).

    `lang` (Polish fix 2, mirroring local_clock_text()'s own trailing
    keyword, D-07): `None` resolves via `relative_age_text()`'s own
    `prefs.current_lang()` default, so every pre-existing call site
    (passing only `ts`/`now_ts`) keeps its identical English output. An
    explicit `lang` is threaded straight through to `relative_age_text()`
    for a caller that needs a specific language regardless of the
    current request's own ContextVar-resolved language — e.g. a
    server-side notification body (D-28) rendered with no request
    context to read from at all.
    """
    if not ts:
        return fallback
    age = age_seconds(ts, now_ts)
    if age is None:
        return ts
    return "%s (%s)" % (ts, relative_age_text(age, lang=lang))


def concise_timestamp_html(ts, now_ts, fallback="no reading yet", lang=None):
    """"<span class="mono" title="<full ISO>"><HH:MM> UTC (<relative>)</span>"
    — D-09's concise-timestamp-by-default format (06.6.3-UI-SPEC.md's New
    Component Contracts). The full ISO string is demoted to the `title`
    attribute; the visible text is a concise clock time plus the existing
    relative_age_text() suffix, preserving absolute_and_relative()'s
    established absolute-first ordering convention (do not reverse to
    relative-first).

    THIS IS A RAW-MARKUP-PRODUCING FUNCTION: callers interpolate the
    return value verbatim — never re-escape it — and place it only in
    data_table()'s new raw_columns parameter, or directly in
    already-safe markup (never in a data_table() column outside
    raw_columns).

    Returns the escaped `fallback` (a bare string, no markup — matching
    absolute_and_relative()'s own no-markup fallback contract) when `ts`
    is falsy. When `ts` fails to parse (or age_seconds() cannot compute,
    e.g. a mismatched now_ts), returns a span with the raw value in both
    the title and visible-text slots rather than raising.

    absolute_and_relative() is not deleted by this function's addition —
    it remains the right choice for any plain-text-only call site (e.g.
    Preview's no-panel caption); do not replace those call sites with
    this function.

    `lang` (Polish fix 2, mirroring local_clock_text()'s own trailing
    keyword, D-07): `None` resolves via `local_clock_text()`'s/
    `relative_age_text()`'s own `prefs.current_lang()` default, so every
    pre-existing call site (passing only `ts`/`now_ts`) keeps its
    identical English output — the French month table/relative-age
    connector only apply when the CURRENT REQUEST's language is French
    (or an explicit `lang="fr"` is passed here), never unconditionally.
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return '<span class="mono" title="%s">%s</span>' % (
            escape_html(ts), escape_html(ts))
    return '<span class="mono" title="%s">%s (%s)</span>' % (
        escape_html(ts),
        escape_html(local_clock_text(parsed, parse_iso(now_ts), lang=lang)),
        escape_html(relative_age_text(age, lang=lang)))


def local_clock_text(parsed, now_parsed=None, lang=None):
    """`parsed` (an aware or naive datetime) rendered on LOCAL_TZ: "HH:MM"
    when it falls on the same local day as `now_parsed` (or when no `now`
    is supplied), otherwise "D Mon HH:MM". A naive datetime is taken as
    UTC, matching history_db.utc_now_iso()'s own output. Never raises.

    `lang` (D-07, 20-03-PLAN.md Task 2) is a trailing keyword whose
    `None` resolves to `prefs.current_lang()` — every pre-existing call
    site passes only `parsed` (and, at most, `now_parsed` by keyword),
    so the English month table (`_MONTH_ABBR`) and this function's
    English output are unchanged. Under a French request, the month
    abbreviation comes from `_MONTH_ABBR_FR` instead; the clock itself
    stays 24-hour Europe/Paris in both languages — no locale module,
    no `%p`, no change to the timezone handling.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        local = parsed.astimezone(LOCAL_TZ)
        clock = local.strftime("%H:%M")
        if now_parsed is not None:
            if now_parsed.tzinfo is None:
                now_parsed = now_parsed.replace(tzinfo=ZoneInfo("UTC"))
            if now_parsed.astimezone(LOCAL_TZ).date() == local.date():
                return clock
            if lang is None:
                lang = prefs.current_lang()
            month_abbr = _MONTH_ABBR_FR if lang == "fr" else _MONTH_ABBR
            return "%d %s %s" % (local.day, month_abbr[local.month - 1], clock)
        return clock
    except (ValueError, OverflowError, AttributeError):
        return parsed.strftime("%H:%M") if hasattr(parsed, "strftime") else ""


def ui_theme_from_cookie(cookies):
    """Return the CFG-09 UI theme named by `cookies`, or "auto" when the
    cookie is missing or holds a value outside UI_THEME_CHOICES.

    Membership test before use, mirroring the same discipline this
    codebase already applies to theme/runway ids elsewhere (ASVS V5) —
    a client-controlled cookie value is never trusted as-is.
    """
    if not isinstance(cookies, dict):
        return "auto"
    value = cookies.get(UI_THEME_COOKIE_NAME)
    return value if value in UI_THEME_CHOICES else "auto"


def _nav_links(active):
    """Return one (is_active, escaped_route, escaped_label, slug) tuple
    per NAV_TABS entry, in NAV_TABS order.

    This is the single place NAV_TABS is iterated and its route/label
    pair escaped; sidebar_nav() (vertical, >=960px) and _mobile_nav_html()
    (hamburger dropdown, <960px, 06.6.1-05) both consume this (via
    _nav_groups() below) instead of re-iterating NAV_TABS and
    re-implementing the same escaping/active-state logic twice. The
    unescaped route `slug` (06.6.1-04) is part of what this function
    single-sources too, so a renderer can identify a specific link (e.g.
    the Health nav-tab notification dot's target) without re-deriving
    "which link is Health" from an already-escaped route string.
    """
    links = []
    for route, label in NAV_TABS:
        slug = nav_slug(route)
        is_active = slug == active
        # D-05/D-09 (20-01-PLAN.md Task 3): the label is looked up
        # through i18n.t() at render time — NAV_TABS/NAV_GROUPS keep
        # their English values (D-01); escape_html() still wraps the
        # result, exactly like any other t() call site.
        links.append((is_active, escape_html(route), escape_html(i18n.t(label)), slug))
    return links


def _nav_groups(active):
    """NAV_GROUPS in display order, each as (escaped_group_label, links)
    where `links` is the slice of _nav_links(active) belonging to that
    group. Phase 18: the one place the group structure is walked, so the
    sidebar and the dropdown can never disagree about which tab sits
    under the "Advanced" label.

    D-17 (21-01-PLAN.md Task 1): the group whose label is
    ADVANCED_GROUP_LABEL (Health, Device) used to be omitted entirely
    in simple mode (D-30, 20-01-PLAN.md Task 3); that gate is deleted
    along with simple mode itself — the Advanced group now renders on
    every page for every request, like every other group. `/health`
    and `/device` were always reachable by URL and stay session-gated
    regardless (companion/pages/__init__.py's ctx contract).
    """
    links = _nav_links(active)
    groups = []
    offset = 0
    for group_label, entries in NAV_GROUPS:
        count = len(entries)
        group_links = links[offset:offset + count]
        offset += count
        groups.append((escape_html(i18n.t(group_label)), group_links))
    return groups


# 06.6.1-05 (D-06, superseding D-00): the horizontally-scrollable nav
# strip's renderer used to live here. Real-device testing found the
# pattern hid most tabs behind an undiscoverable swipe even after its own
# flexbox sizing bug was fixed, so it was replaced rather than repaired a
# second time — see companion/static/style.css's own header comment for
# the full flexbox history. There are now exactly two live nav
# renderers, sidebar_nav() and _mobile_nav_html() below, both fed by
# _nav_links() above.


def _health_alert_markup(severity):
    """The Health nav-tab notification dot plus its visually-hidden
    screen-reader suffix (06.6.1-UI-SPEC.md's Layout Contract / D-02),
    built once so both `_nav_html()`-style and `sidebar_nav()` renderers
    share exactly one markup source for it — today only `sidebar_nav()`
    calls this (the horizontal `_nav_html()` renderer is retired by plan
    06.6.1-05 rather than gaining this markup itself).

    `severity` is `"warn"` or `"error"` — this function is only ever
    called when the caller has already checked severity is not `"ok"`/
    falsy (06.6.2-06, UXA-14). The dot class is looked up via the same
    `_STATUS_DOT_CLASSES` dict `status_dot()` uses (reused, not
    duplicated), so a warning-only Health state draws `dot--warn` rather
    than always the maximal `dot--error` treatment.

    Appends a visually-hidden text suffix rather than an `aria-label` on
    the link: an `aria-label` would *replace* the link's accessible
    name, so the announced text would become only the alert phrasing and
    the word "Health" would be lost. An appended visually-hidden span
    leaves the existing "Health" name intact and adds to it — this is
    06.6.1-UI-SPEC.md's stated reason and a correctness point, not a
    style preference.

    The absence of this markup is deliberately the all-clear signal —
    the same precedent the anomaly banner and CFG-05's source-fault
    badge already set in this codebase: nothing is rendered when
    everything is fine, so there is no "all good" chrome to ignore.
    """
    dot_class = _STATUS_DOT_CLASSES.get(severity, _DEFAULT_STATUS_DOT_CLASS)
    return (
        '<span class="dot %s %s"></span>'
        '<span class="visually-hidden">%s</span>'
    ) % (dot_class, NAV_NOTIFICATION_CLASS, escape_html(i18n.t(HEALTH_ALERT_SUFFIX_TEXT)))


def sidebar_nav(active, health_alert=None):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width.

    Renders the same NAV_TABS route set as _nav_html() — via the shared
    _nav_links() helper, so the two renderers can never drift — just in
    a vertical arrangement. companion/static/style.css's 960px media
    query decides which of the two copies is visible at a given
    viewport width; this function has no opinion on visibility.

    `health_alert` (06.6.1-04, keyword-with-default so no existing
    positional call site changes meaning; 06.6.2-06/UXA-14 widened the
    contract from a boolean to a severity string) is `None`/`"ok"` for
    no dot, or `"warn"`/`"error"` to append `_health_alert_markup()`
    (drawn with that exact severity) after the label text of the link
    whose slug matches HEALTH_NAV_SLUG, and only that link. The markup
    is already-built safe HTML and is interpolated verbatim, exactly
    like status_dot()'s output is in other builders — it is not routed
    through escape_html() again.

    06.6.2-05 (D-17/UXA-10): each link is prefixed with its
    NAV_ICON_IDS-mapped icon (icon_html()'s own whitelist-fallback
    contract makes an unrecognised slug render no icon rather than
    raising — this cannot happen for a real NAV_TABS entry, but keeps
    the call safe). The active link's `<a>` carries `aria-current="page"`
    — never the inactive links — so exactly one link at a time announces
    "current page" to assistive tech. The active-pill *visual* treatment
    (background tint, radius) lives in companion/static/style.css's
    `.sidebar-link--active` rule, not here; the class names themselves
    are unchanged.
    """
    parts = []
    for group_label, group_links in _nav_groups(active):
        links = []
        for is_active, route, label, slug in group_links:
            if is_active:
                css_class = "sidebar-link sidebar-link--active"
                aria_current = ' aria-current="page"'
            else:
                css_class = "sidebar-link"
                aria_current = ""
            icon = icon_html(
                NAV_ICON_IDS.get(slug, ""), extra_class="sidebar-link__icon")
            alert_html = (
                _health_alert_markup(health_alert)
                if health_alert in ("warn", "error") and slug == HEALTH_NAV_SLUG else "")
            links.append(
                '<a class="%s" href="%s"%s>%s%s%s</a>'
                % (css_class, route, aria_current, icon, label, alert_html))
        # Phase 18: an unlabelled group renders its links bare; a labelled
        # group ("Advanced") wraps them in a .nav-group carrying a small
        # uppercase label so the split reads at a glance.
        if group_label:
            parts.append(
                '<div class="nav-group nav-group--advanced">'
                '<span class="nav-group__label text-label">%s</span>%s</div>'
                % (group_label, "".join(links)))
        else:
            parts.append("".join(links))
    return (
        '<nav class="sidebar-nav" aria-label="Primary navigation">%s</nav>'
        % "".join(parts))


def _theme_form_html(resolved_theme):
    options = []
    for choice in UI_THEME_CHOICES:
        is_active = choice == resolved_theme
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_theme" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               escape_html(choice.capitalize())))
    # D-02/D-29 (20-01-PLAN.md Task 3, 20-UI-SPEC.md §I): an aria-label
    # disambiguates this now-identical-looking segmented group from the
    # two new siblings below — the theme ids ("Auto"/"Light"/"Dark")
    # are identifiers already, so only the group label is translated.
    return (
        '<form class="theme-form" method="post" action="/ui-theme" aria-label="%s">%s</form>'
        % (escape_html(i18n.t("Theme")), "".join(options)))


def _lang_form_html(resolved_lang):
    """The FR/EN language switch (D-02, 20-01-PLAN.md Task 3) — a
    sibling of _theme_form_html() above, identical in shape. "FR"/"EN"
    are identifiers (D-05) and are never passed through i18n.t().
    """
    options = []
    for choice in prefs.LANG_CHOICES:
        is_active = choice == resolved_lang
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_lang" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               escape_html(choice.upper())))
    return (
        '<form class="theme-form" method="post" action="/ui-lang" aria-label="%s">%s</form>'
        % (escape_html(i18n.t("Language")), "".join(options)))


    # D-17 (21-01-PLAN.md Task 1): _mode_form_html() is deleted along
    # with the rest of the simple-mode mechanism it fed.


def _logout_form_html():
    """The POST `/logout` sign-out control (06.6.2-05, D-11/D-17), shared
    verbatim by both the sidebar footer and the mobile-nav dropdown
    footer built below — one write site for the Sign out control, never
    two independent copies.

    The literal `/logout` path is hard-coded here rather than imported
    from `companion.app` — the same precedent `_theme_form_html()`'s own
    hard-coded `action="/ui-theme"` literal already sets, documented
    there for the same reason: `companion/app.py` imports this module,
    so the reverse import would be a cycle.

    `method="post"` matters: D-11 moves `/logout` off GET specifically so
    a stray prefetch, crawler, or `<img src="/logout">`-shaped link can
    no longer end a session. A plain `<a href="/logout">` here would
    reopen exactly that hole.
    """
    return (
        '<form method="post" action="/logout" class="logout-form">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % escape_html(i18n.t("Sign out"))


def _mobile_nav_html(
        active, theme_form_html, health_alert=None, lang_form_html=""):
    """The hamburger toggle button plus the dropdown panel it controls —
    the <960px nav renderer (D-06, 06.6.1-UI-SPEC.md's Layout Contract).

    Consumes _nav_links(), the module's single iteration-and-escaping
    site for NAV_TABS, exactly like sidebar_nav() does — this is that
    helper's second consumer, not a third independent implementation.

    `theme_form_html` is taken as a parameter rather than built here via
    _theme_form_html(), so page_shell() keeps building it exactly once
    and passing the same string to both copies — this is what makes the
    "both theme-form copies present" check meaningful rather than an
    accident. `lang_form_html` (D-02, 20-01-PLAN.md Task 3) follows the
    identical discipline — page_shell() builds both exactly once and
    passes the same strings to both footer copies, so they can never
    drift. D-17 (21-01-PLAN.md Task 1): the sibling `mode_form_html`
    parameter is removed outright, not merely defaulted — the footer
    slot it fed no longer exists.

    The panel is always rendered without MOBILE_NAV_OPEN_CLASS — the
    server never renders it open. A server-rendered open state would
    flash the menu open on every page load; companion/static/
    nav-dropdown.js is what adds/removes the class client-side, keyed off
    the toggle's own aria-expanded attribute (the single source of truth
    for the open state, never a second variable to keep in sync).

    `health_alert` (06.6.2-06/UXA-14): `None`/`"ok"` draws no dot;
    `"warn"`/`"error"` draws `_health_alert_markup()` with that exact
    severity after the Health link's label, mirroring sidebar_nav()'s
    own contract exactly so the two nav renderers can never disagree.
    """
    parts = []
    for group_label, group_links in _nav_groups(active):
        links = []
        for is_active, route, label, slug in group_links:
            css_class = (
                "mobile-nav__link mobile-nav__link--active"
                if is_active else "mobile-nav__link")
            alert_html = (
                _health_alert_markup(health_alert)
                if health_alert in ("warn", "error") and slug == HEALTH_NAV_SLUG else "")
            links.append(
                '<a class="%s" href="%s">%s%s</a>'
                % (css_class, route, label, alert_html))
        if group_label:
            parts.append(
                '<div class="nav-group nav-group--advanced">'
                '<span class="nav-group__label text-label">%s</span>%s</div>'
                % (group_label, "".join(links)))
        else:
            parts.append("".join(links))
    links = parts
    toggle_html = (
        '<button type="button" id="%s" class="site-nav-toggle" '
        'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
    ) % (
        NAV_TOGGLE_ID, escape_html(i18n.t(NAV_TOGGLE_LABEL)), MOBILE_NAV_ID,
        icon_html("icon-hamburger", size=24))
    # D-02 (20-01-PLAN.md Task 3): resolved order — language, theme,
    # Sign out. D-17 (21-01-PLAN.md Task 1, 21-UI-SPEC.md §G): the
    # simple-mode switch that used to sit between theme and Sign out
    # is deleted; the footer now holds exactly two switches.
    footer_html = (
        '<div class="mobile-nav__footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))
    panel_html = (
        '<div id="%s" class="mobile-nav">'
        '<nav class="mobile-nav__nav" aria-label="Primary navigation">%s</nav>'
        "%s"
        "</div>"
    ) % (MOBILE_NAV_ID, "".join(links), footer_html)
    return toggle_html + panel_html


def login_shell(body, ui_theme="auto", lang=None):
    """A dedicated, minimal HTML5 document for the pre-authentication
    login page — 06.6.2-07 (UXA-03).

    This function exists specifically because page_shell() always
    renders the full authenticated sidebar/mobile-nav/theme-form-footer
    regardless of the `active=""` value login's old call site passed —
    that is UXA-03's root cause (a real, reproduced production defect:
    the login page visually implied the whole site's navigation was
    usable before signing in). login_shell() is a deliberately
    separate, smaller sibling of page_shell(), not a parameterized
    branch inside it — it shares page_shell()'s outer document
    structure (doctype, `<html lang="..." data-ui-theme="...">`,
    `<head>` with charset/viewport/title/stylesheet link/
    FAVICON_LINK_HTML, reusing that constant rather than duplicating
    the data-URI literal) but its `<body>` contains only the login
    card: no ICON_DEFS_HTML sprite (nothing on this page uses an
    icon), no skip link (there is no nav to skip past), no sidebar, no
    mobile-nav dropdown, no NAV_DROPDOWN_SCRIPT_SRC script tag.

    `body` is the caller's own already-built, already-escaped markup —
    the same "caller has escaped its own dynamic parts" contract every
    other body-accepting builder in this module follows (page_shell(),
    stat_tile(), etc.) — and is interpolated verbatim into
    `<div class="login-card">`.

    `lang` (D-03, 20-01-PLAN.md Task 3): defaults to `None`, resolved
    to `prefs.current_lang()` — always one of `prefs.LANG_CHOICES`, so
    the `<html lang="...">` attribute is never built from an
    unvalidated value. `companion/app.py`'s pre-session callers
    (login, 404) call `prefs.set_request_prefs(lang=...)` themselves
    before rendering, exactly like the login route already does for
    `ui_theme` via `_resolved_ui_theme()`.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Login - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body>\n"
        '<div class="login-shell">\n'
        '<div class="login-card">\n'
        "%s\n"
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body,
    )


# 06.6.4.1.1-04 (D-17): a substitution token, never markup that ships. It
# has exactly one definition site (here). page_header() emits it as the
# last thing in its returned string; page_shell() below is the only
# consumer — it swaps the token for the flash banner when the token is
# present (every page built on page_header()) and unconditionally strips
# any leftover occurrence before the response is returned, so it can
# never reach the browser on any path, flash or no-flash.
FLASH_SLOT_MARKER = "<!--flash-slot-->"


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and every nav label are escaped here. `body`, `flash` and
    `banner` are pre-built markup strings — the caller is responsible
    for having escaped their own dynamic parts (they are typically the
    output of this module's other builders, which already escape).

    `health_alert` (06.6.1-04, keyword-with-default, placed last so no
    positional call site shifts; 06.6.2-06/UXA-14 widened the contract
    from a boolean to a severity string) is threaded through to
    sidebar_nav() and (06.6.1-05) _mobile_nav_html(). It is `None`/`"ok"`
    (no dot) or `"warn"`/`"error"` (a dot with that class), a display
    signal only, defaulting to no dot, so any caller without a request
    context — login, 404, the preview-image error pages — draws no dot,
    which is correct rather than merely convenient.

    `lang` (D-03, 20-01-PLAN.md Task 3): defaults to `None`, resolved
    to `prefs.current_lang()` — always one of `prefs.LANG_CHOICES`. A
    `None` default is deliberate: no existing page-module call site
    (~40 of them) has to change, since `companion/app.py`'s
    `page_context()` already calls `prefs.set_request_prefs()` once
    per request before any page module renders.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    sidebar_html = sidebar_nav(active, health_alert=health_alert)
    theme_form_html = _theme_form_html(resolved_theme)
    lang_form_html = _lang_form_html(resolved_lang)
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert,
        lang_form_html=lang_form_html)
    flash_html = flash or ""
    banner_html = banner or ""

    # 06.6.4.1.1-04 (D-17): move the flash banner to directly below the
    # page header instead of above the page title, so saving no longer
    # shifts the title down. `body` is one opaque pre-built string by
    # the time it reaches this function, so there is no structural
    # handle on "just after the header" — page_header() instead leaves
    # FLASH_SLOT_MARKER as a literal handle at exactly that point.
    #   - A page built on page_header() (every authenticated page today)
    #     carries the marker in `body`; the flash banner is spliced in
    #     right there and `flash_html` is cleared so it is not also
    #     emitted in its old pre-body slot.
    #   - A page that does NOT use page_header() (login, 404, and any
    #     future bare page) has no marker in `body`; `flash_html` is left
    #     untouched and keeps rendering in today's before-body slot, so
    #     no such caller has to change and none silently loses its
    #     banner.
    #   - The unconditional second replace() below guarantees the marker
    #     itself never reaches the browser, including on the no-flash
    #     path where `flash_html` is "" (nothing to splice in, but a
    #     `page_header()` body still carries the marker literal).
    if FLASH_SLOT_MARKER in body:
        body = body.replace(FLASH_SLOT_MARKER, flash_html, 1)
        flash_html = ""
    body = body.replace(FLASH_SLOT_MARKER, "")

    # 06.6.2-05 (D-17): the sidebar's theme picker and Sign out control,
    # grouped into one footer region — the exact artifact Phase 06.6.3
    # was told to expect by name (a .sidebar-footer wrapper). Replaces
    # the previous bare theme_form_html-only slot. D-02 (20-01-PLAN.md
    # Task 3): resolved order — language, theme, Sign out; this and
    # _mobile_nav_html()'s own footer_html must change together.
    # D-17 (21-01-PLAN.md Task 1, 21-UI-SPEC.md §G): the simple-mode
    # switch that used to sit between theme and Sign out is deleted —
    # the footer now holds exactly two switches, language then theme.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))

    # 06.6.2-05 (UXA-10): the first focusable element in <body>, before
    # even ICON_DEFS_HTML — a keyboard/screen-reader user's very first
    # tab stop on every page.
    skip_link_html = (
        '<a class="skip-link" href="#%s">Skip to content</a>'
        % SKIP_LINK_TARGET_ID)

    # The <aside> deliberately precedes the <header> in source order: at
    # desktop width, where CSS hides the header entirely, a keyboard user
    # tabs into the visible sidebar navigation first, with no invisible
    # stops before it. Both nav copies (the sidebar and, 06.6.1-05, the
    # hamburger dropdown) are always present in the DOM —
    # companion/static/style.css's 960px media query is the only thing
    # that decides which copy is visible, never anything in this function
    # (no inline styles, no boolean-hidden attribute, no ARIA visibility
    # hint). Because the two nav landmarks share the same "Primary
    # navigation" label and are toggled by the same CSS rule (never by
    # this function), exactly one navigation landmark is exposed to the
    # accessibility tree at any given viewport width — the 960px rule
    # removes the losing copy with display:none, which takes it out of
    # the layout, the tab order and the accessibility tree together, not
    # merely out of view. 06.6.1-04: ICON_DEFS_HTML is emitted here
    # unconditionally, once per document, immediately inside <body> and
    # before the dashboard-shell div — the only definition site for every
    # icon in the app. 06.6.1-05: the theme form is now rendered once in
    # the sidebar and once inside the hamburger dropdown panel (built by
    # _mobile_nav_html() above from the same theme_form_html string) —
    # it is no longer rendered a third time directly in the header, which
    # is what removes D-00's crush-bug root cause instead of re-tuning it
    # a second time. A single deferred <script> tag, referencing
    # NAV_DROPDOWN_SCRIPT_SRC, is emitted immediately before </body>.
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body>\n"
        "%s\n"
        "%s\n"
        '<div class="dashboard-shell">\n'
        '<aside class="dashboard-sidebar">\n'
        '<span class="site-title sidebar-title">%s</span>\n'
        "%s\n"
        "%s\n"
        "</aside>\n"
        '<header class="site-header">\n'
        '<span class="site-title">%s</span>\n'
        "%s\n"
        "</header>\n"
        '<main class="page-content dashboard-main" id="%s" tabindex="-1">\n'
        "%s\n%s\n%s\n"
        "</main>\n"
        "</div>\n"
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        escape_html(title), escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        skip_link_html,
        ICON_DEFS_HTML,
        escape_html(SITE_TITLE),
        sidebar_html,
        sidebar_footer_html,
        escape_html(SITE_TITLE),
        mobile_nav_html,
        SKIP_LINK_TARGET_ID,
        flash_html, banner_html, body,
        NAV_DROPDOWN_SCRIPT_SRC,
        # 06.6.3: emitted unconditionally on every authenticated page,
        # matching nav-dropdown.js/battery-trend.js's own "served
        # everywhere, no-ops via guard clause" convention — never
        # conditionally included per page.
        DIRTY_STATE_SCRIPT_SRC,
        LIST_FILTER_SCRIPT_SRC,
        COPY_BUTTON_SCRIPT_SRC,
        FRESHNESS_SCRIPT_SRC,
        # 06.6.4.1-02 (D-20): sixth script, same unconditional/no-op-via-
        # guard-clause convention — served every page; since quick task
        # 260902-tli both History and the Airlines gallery render
        # #panel-lookup-dialog.
        PANEL_LOOKUP_SCRIPT_SRC,
        # Quick task 260903-peo (UIR-19): seventh script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since the flash banner it cleans up after is emitted by
        # this function for every authenticated page, not just one.
        FLASH_CLEANUP_SCRIPT_SRC,
        # 19-04-PLAN.md (D-18/A-35): eighth script, same unconditional/
        # no-op-via-guard-clause convention — served every page, since
        # only Settings renders #poll-trigger-btn.
        POLL_COOLDOWN_SCRIPT_SRC,
        # 19-11-PLAN.md Task 2 (D-08/A-26): ninth script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only the Device page renders a
        # form[data-confirm] (the calendar disconnect form).
        CONFIRM_SUBMIT_SCRIPT_SRC,
        # 20-08-PLAN.md Task 3 (D-22..D-24): tenth script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only Display (from 20-11) renders
        # .theme-live-preview img plus a .theme-chip-grid.
        THEME_PREVIEW_SCRIPT_SRC,
        # 21-03-PLAN.md Task 2 (D-15/R-12): eleventh script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only Flights renders .flight-detail-row/
        # [data-row-toggle].
        FLIGHT_ROWS_SCRIPT_SRC,
    )


_FLASH_ROLES = {"status", "alert"}


def flash_banner(message, role="status"):
    """An accent-bordered confirmation block (D-07's save confirmation).

    `role` (06.6.2-06, UXA-07) is validated against `_FLASH_ROLES`
    (falling back to `"status"` for anything else) — the same
    whitelist-with-safe-fallback discipline `status_dot()`'s `state`
    parameter already uses — and rendered as the `<div>`'s ARIA `role`
    attribute, so a save/poll failure announces as `role="alert"`
    (assertive) while every other outcome stays `role="status"`
    (polite), chosen by the caller's real severity rather than one role
    for every outcome.
    """
    resolved_role = role if role in _FLASH_ROLES else "status"
    return (
        '<div class="banner banner--flash" role="%s">%s</div>'
        % (resolved_role, escape_html(message)))


def anomaly_banner(message, severity="error"):
    """A warning/destructive-bordered block for D-14's anomaly flagging.

    `severity` (06.6.2-06, UXA-14) chooses both the CSS class and the
    ARIA role: `"error"` (the default, preserving every existing
    positional/no-keyword call site's prior meaning) renders
    `banner--anomaly`/`role="alert"`; anything else (in practice only
    `"warn"`) renders the new `banner--warn`/`role="status"` — a
    warning-only Health state is announced politely, not as an
    assertive interruption.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    return (
        '<div class="banner %s" role="%s">%s</div>'
        % (css_class, role, escape_html(message)))


def status_dot(state, label, title=None, visually_hide_label=False):
    """A small coloured status indicator plus an escaped text label.

    `state` maps to exactly one of three fixed CSS class suffixes; an
    unrecognised state falls back to the warning class rather than
    emitting an arbitrary, attacker-influenceable class name.

    `title` (quick task 260902-w4t, UIR-04) is optional and defaults to
    None for backward compatibility: every pre-existing call site passes
    exactly two positional arguments, and when `title` is falsy the
    returned markup is character-for-character what it was before this
    parameter existed — no `title` attribute is emitted at all. When
    `title` is truthy it is escaped through the same `escape_html()`
    call `label` already goes through (the identical single-escaping
    discipline `concise_timestamp_html()` uses for its own `title`) and
    added as a `title="..."` attribute on the `dot-label` span, giving a
    shortened visible label room to carry a longer form as a tooltip.

    `visually_hide_label` (21-03-PLAN.md Task 1, D-15) is a
    keyword-with-default, byte-identical-when-falsy parameter, matching
    `stat_tile()`'s own `caption_title` contract: every pre-existing call
    site (which never passes this keyword) gets a return value that is
    character-for-character what this function returned before this
    parameter existed. Only Flights' desktop Corroboration cell
    (`history_page._history_table_html()`) passes `True` — the dot stays
    visible, the accessible name and `title` tooltip are unchanged, but
    the label span's class becomes `"dot-label visually-hidden"` instead
    of `"dot-label"`, removing the visible word so the column can shrink
    to a dot-only width (21-UI-SPEC.md §F). Health's own call sites
    (`health_page.py`) never pass this keyword and are unaffected.
    """
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    title_attr = ' title="%s"' % escape_html(title) if title else ""
    label_class = "dot-label visually-hidden" if visually_hide_label else "dot-label"
    return (
        '<span class="dot %s"></span><span class="%s"%s>%s</span>'
        % (css_class, label_class, title_attr, escape_html(label)))


def stat_tile(caption, content_html, status=None, icon=None, caption_title=None):
    """A status-coloured dashboard card wrapping already-built markup.

    `caption` is escaped here. `content_html` is the caller's own
    already-safe markup (e.g. status_dot()'s raw <span> pair,
    data_table()'s table, empty_state()'s block, or a hand-built <p>
    string) and is interpolated verbatim, with no call to
    escape_html() and no other transformation — re-encoding it here
    would double-encode already-escaped tags and print them as visible
    text instead of rendering. `status` maps to one of three fixed
    CSS class suffixes ("ok"/"warn"/"error"); None or an unrecognised
    value falls back to the accent-neutral class rather than emitting
    an arbitrary, attacker-influenceable class name.

    `icon` (06.6.1-04, D-02) is a whitelisted id from ICON_IDS — not
    markup — passed straight to icon_html(), which is this function's
    only route to injecting raw HTML beyond `content_html`; that is
    deliberate, so stat_tile() never grows a second free-form raw-markup
    parameter. When falsy (the default) or not a member of ICON_IDS, the
    caption renders exactly as it did before this parameter existed —
    every pre-existing call site is byte-identical. When it names a
    valid icon, the caption element becomes the icon markup (tinted via
    STAT_TILE_ICON_CLASS) followed by the escaped caption text in a
    <span>, so companion/static/style.css's flex caption rule lays them
    out on one line.

    `caption_title` (19-06, D-06) is an ATTRIBUTE VALUE, not markup — it
    is escaped here through the same escape_html() call `caption` and
    status_dot()'s own `title` parameter already go through, and is
    never interpolated as raw HTML. That is why adding it does not
    violate the "never grow a second free-form raw-markup parameter"
    rule stated above for `icon`: an attribute value and a markup
    fragment are different trust levels, and this parameter is the
    former. When falsy (the default), the returned string is
    BYTE-IDENTICAL to what this function returned before this
    parameter existed, on both the icon and no-icon branches — no
    `title` attribute is emitted at all. When truthy, a
    `title="{escaped caption_title}"` attribute is added to the
    `<p class="text-label stat-tile__caption">` element (the label
    itself) and nothing else changes. D-06's purpose: a household
    reader sees a plain-language label; the technical term a developer
    needs to grep/diagnose by stays one hover away instead of being
    deleted outright.
    """
    css_class = "stat-tile " + _STAT_TILE_BORDER_CLASSES.get(
        status, _DEFAULT_STAT_TILE_CLASS)
    icon_markup = icon_html(icon, extra_class=STAT_TILE_ICON_CLASS) if icon else ""
    if icon_markup:
        caption_html = icon_markup + "<span>%s</span>" % escape_html(caption)
    else:
        caption_html = escape_html(caption)
    title_attr = ' title="%s"' % escape_html(caption_title) if caption_title else ""
    return (
        '<div class="%s">'
        '<p class="text-label stat-tile__caption"%s>%s</p>'
        "%s"
        "</div>"
    ) % (css_class, title_attr, caption_html, content_html)


def card_status_class(base_class, status):
    """`base_class + "--ok"/"--warn"/"--error"` for one of the three
    whitelisted statuses; the empty string for `None` or anything
    unrecognised.

    The one status->card-modifier mapping (quick task 260902-gjj, ISSUE
    2), living beside `_STATUS_DOT_CLASSES`/`_STAT_TILE_BORDER_CLASSES`
    so the vocabulary has exactly one home. `status` is looked up in a
    fixed three-key whitelist, the same discipline `status_dot()` and
    `stat_tile()` already document — an unrecognised value can never
    become an arbitrary, attacker-influenceable class name. `base_class`
    is expected to be a module constant or a call-site literal, never
    itself derived from data.

    The fallback deliberately differs from `stat_tile()`'s: `stat_tile()`
    falls back to `stat-tile--accent` because `.stat-tile`'s base rule
    already declares a 3px top border that has to be *some* colour. A
    page-level card's base rule (`.battery-trend-section`, `.page-section`)
    declares a plain 1px hairline, so "no status" correctly means "no
    modifier at all, keep the neutral edge" — the absence of a coloured
    edge is itself the signal that the card carries no verdict. Getting
    this backwards (defaulting to an accent modifier) would put a 3px
    accent border on the Resolution-statistics card, which carries no
    status field of any kind, and would require broadening style.css's
    exhaustive accent-reservation list a second time in two days, for no
    reported problem.
    """
    suffix = _CARD_STATUS_SUFFIXES.get(status)
    return base_class + suffix if suffix else ""


def status_row(label, verdict, detail, state):
    """<div class="status-row status-row--ok|warn|error"> — D-21's one
    shared row primitive (dot + optional label + verdict + detail),
    consumed by Home's status card (20-06) and the Calendar status row
    (20-07) alike (20-UI-SPEC.md Section Anatomy A).

    `label` is optional: a falsy value omits the `<span>` element
    entirely, not merely its text — Calendar's own status row passes
    "" because its surrounding `<h2>Calendar</h2>` already names the
    subject, and a repeated "CALENDAR" label would be redundant
    chrome. `verdict` and `detail` must carry two DIFFERENT pieces of
    information — a state word versus a freshness/detail clause — by
    contract: this primitive exists specifically to fix the Home
    Frame-tile defect where `DEVICE_STATE_TEXT`/`FRAME_STATE_TEXT`'s
    verdict sentence used to be rendered twice, once as the tile's own
    verdict paragraph and once again inside `health_state["device_
    html"]`'s own embedded verdict paragraph.

    `state` maps through the SAME `_STATUS_DOT_CLASSES`/
    `_DEFAULT_STATUS_DOT_CLASS` fallback `status_dot()`/`stat_tile()`
    already use for the dot, and through `card_status_class()`'s own
    three-key whitelist for the outer modifier class — never a second,
    bare `%s` interpolation of an unvalidated `state` (T-20-18): an
    unrecognised state degrades to the default (warn) dot and to NO
    outer modifier class at all, rather than emitting an arbitrary,
    attacker-influenceable class name. `verdict` and `detail` are both
    escaped here (T-20-03) — `label` is escaped too, inside the
    optional span.

    The caller is responsible for translating `label`/`verdict`/
    `detail` through `i18n.t()` BEFORE calling this — status_row()
    itself calls no `t()` and treats every argument as already-
    resolved display text.
    """
    dot_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    modifier = card_status_class("status-row", state)
    css_class = "status-row" + ((" " + modifier) if modifier else "")
    label_html = (
        '<span class="status-row__label text-label">%s</span>' % escape_html(label)
        if label else "")
    return (
        '<div class="%s">'
        '<span class="dot %s"></span>%s'
        '<span class="status-row__verdict">%s</span>'
        '<span class="status-row__detail">%s</span>'
        "</div>"
    ) % (css_class, dot_class, label_html, escape_html(verdict), escape_html(detail))


def section_intro_html(section_id, heading, description):
    """A `<div class="section-intro">` wrapping one id-anchored `<h2>`
    plus a muted one-sentence description on the same baseline.

    Promoted here, byte-identical (markup and CSS class unchanged),
    from `companion/pages/health_page.py`'s own former private copy,
    `_section_intro_html()` (20-UI-SPEC.md Section Anatomy C):
    `companion/pages/__init__.py` forbids one page module importing
    another, so a helper both `health_page.py` and `config_page.py`
    (20-07's Display supersections) need must live in this shared
    layer instead — the same reasoning D-21's `status_row()` above is
    added here for, in the same phase.

    The `<h2 id="..." class="text-heading">...</h2>` this emits keeps
    the same attribute order (`id` then `class`) and the same
    `escape_html()` call on the heading text health_page.py's own
    pinned structural checks already match literally — this builder
    must never drift from that shape. The description keeps the
    `text-label section-caption` pairing already established for this
    "muted one-sentence-under-a-heading" role.

    WR-03 fix (20-REVIEW.md): `section_id` is escaped too, like every
    other string this file interpolates into an HTML attribute or text
    node — this was the one exception to that "escape everything,
    unconditionally" invariant. Every current call site passes a fixed
    module-level string constant, so this was not exploitable today,
    but this helper is shared across page modules going forward and
    must not be the one place a caller is trusted.
    """
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (escape_html(section_id), escape_html(heading), escape_html(description))


def empty_state(heading, body):
    """The escaped two-part empty-state block (06-UI-SPEC.md's Copywriting
    Contract) used for the flight log, the gallery, and the unresolved-
    prefix list.
    """
    return (
        '<div class="empty-state">'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (escape_html(heading), escape_html(body))


def page_header(title, purpose=None, freshness_html=None, action_html=None):
    """The shared page-header component (06.6.2 D-16) every authenticated
    page's render() opens with, in place of an independent bare <h1>.

    THIS SIGNATURE IS A LITERAL CONTRACT: Phase 06.6.3's five per-page
    redesign plans call page_header(title, purpose=None,
    freshness_html=None, action_html=None) by this exact name and
    parameter order — do not rename or reorder these parameters after
    this plan ships. Every call site this plan adds passes only `title`
    (positional); those calls remain byte-compatible with later call
    sites that also pass `purpose`/`freshness_html`/`action_html`.

    `title` is escaped here and wrapped in an <h1 class="page-title">
    (06.6.2 D-15's distinct ~30px serif page-title role, separate from
    the existing 20px .text-heading section-heading role).

    `purpose` is escaped here too, when truthy, and rendered as a
    one-sentence <p class="page-header__purpose text-body">.

    `freshness_html` and `action_html`, when truthy, are each the
    caller's own already-safe markup and are interpolated verbatim —
    no call to escape_html(), no other transformation. This is the same
    "escape the caption, pass already-built content through verbatim"
    contract stat_tile()'s `content_html` parameter uses; re-encoding
    either of these two here would double-encode already-escaped tags
    and print them as visible text instead of rendering. Callers are
    responsible for escaping/composing any user-influenced data before
    passing it through either parameter.

    Quick task 260901-tsa: `freshness_block` and `action_block` are
    concatenated BEFORE `purpose_html` below — title, then the Refresh
    link/action row, then the purpose sentence last. That is the
    validated Health sketch's own header markup: the title and the
    Refresh anchor sit inside one `.page-header` element, with the
    purpose sentence following after it, not wedged between the title
    and its action link. The LITERAL CONTRACT paragraph above covers the
    signature — parameter names and their order — which this edit does
    not touch; the order the three optional blocks are concatenated into
    the returned string is a separate thing and was never part of that
    contract. Blast radius: Health is the only call site today passing
    both a purpose and a freshness block. For a caller passing exactly
    one of the three optional blocks (every other page, today), the
    concatenation produces the identical string either way — `"%s%s%s" %
    (p, "", "")` and `"%s%s%s" % ("", "", p)` are the same string — so
    Settings, Airlines and History are byte-identical before and after
    this reorder; this is a Health-only visual change. With the purpose
    paragraph now the last in-flow child of a block-level `.page-header`
    that has no padding and no border, its own bottom margin collapses
    with the parent's `margin-bottom`, so the gap below the header block
    is unchanged rather than doubled.

    06.6.4.1.1-04 (D-17): the returned string now ends with
    FLASH_SLOT_MARKER, appended after the closing `</div>`. This is NOT
    a signature change — the LITERAL CONTRACT above governs this
    function's parameter names and order, not the content of what it
    returns — but it is documented here explicitly so the next reader
    does not mistake it for one. `page_shell()` is the marker's only
    consumer: it splices the flash banner in at that exact point and
    strips the marker unconditionally before the response ships.
    """
    purpose_html = (
        '<p class="page-header__purpose text-body">%s</p>' % escape_html(purpose)
        if purpose else "")
    freshness_block = freshness_html if freshness_html else ""
    action_block = action_html if action_html else ""
    return (
        '<div class="page-header">'
        '<h1 class="page-title">%s</h1>'
        "%s%s%s"
        "</div>"
        "%s"
    ) % (
        escape_html(title), freshness_block, action_block, purpose_html,
        FLASH_SLOT_MARKER,
    )


def data_table(headers, rows, mono_columns=(), raw_columns=(), desc_columns=(), prose=False):
    """A header row plus alternating body rows, every value escaped.

    `mono_columns` names the zero-based column indices that get the
    monospace class (callsigns, hex codes, prefixes, timestamps, per
    06-UI-SPEC.md's Typography section). Returns empty_state()'s output
    instead of an empty table when `rows` is empty.

    `raw_columns` (06.6.3, D-09) names the zero-based column indices
    whose cell value is ALREADY-SAFE, pre-built HTML — the same
    "already-built content passed through verbatim" contract
    stat_tile()'s `content_html` parameter documents — and is
    interpolated without a call to escape_html(). Every other column
    (the default for all of them) is escaped exactly as before this
    parameter existed; every pre-existing call site passing no
    raw_columns argument is byte-identical. Only ever place the output
    of a builder that already escapes internally (concise_timestamp_html(),
    status_dot()) in a raw_columns cell — never a bare string; doing so
    would reopen the exact XSS-shaped defect this module's single-
    escaping-choke-point discipline otherwise closes (06.6.3-RESEARCH.md
    Pitfall 3). `mono_columns` and `raw_columns` are orthogonal (one
    controls a CSS class, the other controls escaping) and may safely
    name the same index, though concise_timestamp_html()'s own
    `<span class="mono">` makes a redundant mono_columns entry
    pointless for that specific case.

    `desc_columns` (quick task 260902-bl2) is `mono_columns`' direct
    sibling: the zero-based column indices that get the description
    role's class (`desc`) — a column holding descriptive prose rather
    than data, which the validated Health sketch renders in the muted
    secondary strength so the eye lands on the values beside it. Added
    because the Resolution-statistics table's Description column
    measured full-strength `--color-text` (`rgb(23, 25, 31)`) with an
    empty `classList`: before this keyword, `data_table()` had no
    column-role class hook for anything but the monospace role, so a
    column of prose had no class for a stylesheet rule to target at
    all. Changes no cell content and no escaping — the same boundary
    `mono_columns` already keeps. `mono_columns`, `raw_columns` and
    `desc_columns` are mutually orthogonal (one controls a class, one
    controls escaping, one controls a class) and may safely name the
    same index.

    `prose` (quick task 260901-uzi) adds the modifier class
    `data-table--prose` to the emitted `<table>` when true; the default,
    false, is byte-identical to this function's pre-existing output.
    `.data-table` carries `min-width: max-content` in style.css so that
    tables of short values (callsigns, hex codes, prefixes, timestamps)
    are never cropped — but a cell's max-content width is its text with
    no wrapping at all, which is correct for those short values and wrong
    for a column holding full sentences: the table then cannot fit any
    container narrower than the whole unwrapped sentence, and
    `.data-table-wrap`'s horizontal scroll becomes a permanent state
    rather than a safety net. Measured on the Resolution-statistics
    table: 1172px of content inside an 831px container. This keyword
    changes no cell's content or escaping — it only adds a class the
    stylesheet uses to release that one table from the shared no-crop
    floor.
    """
    if not rows:
        return empty_state("No data yet.", "Nothing to show here yet.")

    header_cells = "".join(
        "<th>%s</th>" % escape_html(header) for header in headers)

    body_rows = []
    for row_index, row in enumerate(rows):
        row_class = "row-alt" if row_index % 2 else "row"
        cells = []
        for column_index, cell in enumerate(row):
            # mono is joined first so a mono-only cell's attribute string
            # stays byte-identical to this loop's pre-desc_columns output
            # — test_view_pages.py::_mono_columns_present() asserts that
            # merged-cell mono output and must stay green unedited.
            cell_roles = []
            if column_index in mono_columns:
                cell_roles.append("mono")
            if column_index in desc_columns:
                cell_roles.append("desc")
            cell_class = ' class="%s"' % " ".join(cell_roles) if cell_roles else ""
            cell_html = cell if column_index in raw_columns else escape_html(cell)
            cells.append("<td%s>%s</td>" % (cell_class, cell_html))
        body_rows.append('<tr class="%s">%s</tr>' % (row_class, "".join(cells)))

    table_class = "data-table data-table--prose" if prose else "data-table"
    return (
        '<div class="data-table-wrap">'
        '<table class="%s">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (table_class, header_cells, "".join(body_rows))
