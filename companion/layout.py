"""companion/layout.py — the escaped page shell and 06-UI-SPEC.md's
component library for the SkyPane companion service.

stdlib `html` only — no imports from server/, and nothing from
companion.auth beyond the UI-theme cookie name.

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

from companion.auth import UI_THEME_COOKIE_NAME

SITE_TITLE = "SkyPane"

# Ordered (route, label) pairs — 06-UI-SPEC.md's Page Inventory. Login is
# deliberately absent: it is shown instead of any page when unauthenticated,
# never as a nav tab.
NAV_TABS = (
    ("/config", "Config"),
    ("/health", "Health"),
    ("/airlines", "Airlines"),
    ("/history", "History"),
    ("/preview", "Preview"),
)

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
# that varies it.
NAV_TOGGLE_LABEL = "Open menu"

# Must equal companion/app.py's NAV_SCRIPT_ROUTE exactly. Duplicated
# rather than imported because companion/pages/__init__.py's boundary —
# and a plain import cycle, since app.py imports this module — forbids
# the reverse direction, exactly as health_page.BATTERY_TREND_SCRIPT_SRC's
# own comment already states for its own route pair. The Task 3 checks
# assert the equality.
NAV_DROPDOWN_SCRIPT_SRC = "/static/nav-dropdown.js"

UI_THEME_CHOICES = ("auto", "light", "dark")

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

# --- 06.6.1-04: icon sprite (D-02) -------------------------------------
#
# The whitelist. Capped at exactly five ids by 06.6.1-UI-SPEC.md's Design
# System contract — this is not an incomplete set to extend later, it is
# the whole set. The hamburger member is consumed by plan 06.6.1-05's
# mobile-nav toggle button; it is defined here anyway (rather than by
# that later plan) so the sprite in ICON_DEFS_HTML stays the single
# write site for every icon in the app, never two.
ICON_IDS = (
    "icon-device",
    "icon-pipeline",
    "icon-corroboration",
    "icon-battery",
    "icon-hamburger",
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

# The dot's own class, layered on top of the existing .dot/.dot--error
# classes (see _health_alert_markup()) rather than a new colour. Its
# counterpart is companion/static/style.css's `.nav-notification` rule
# — Task 3's test harness reads that stylesheet from disk and asserts
# this class name actually appears in it.
NAV_NOTIFICATION_CLASS = "nav-notification"

# 06.6.1-UI-SPEC.md's Copywriting Contract, verbatim: appended (not
# substituted) after the "Health" nav label text via a visually-hidden
# span, so assistive tech announces "Health — attention needed" rather
# than losing the word "Health" to an aria-label override.
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

    `aria-hidden="true"` is set unconditionally: every icon this phase
    renders sits beside its own visible text label (a tile caption, a
    section heading), so the icon is decorative and announcing it would
    duplicate the label. Do not "improve" this by adding a `<title>`.
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
    (hamburger dropdown, <960px, 06.6.1-05) both consume this instead of
    re-iterating NAV_TABS and re-implementing the same escaping/
    active-state logic twice — two renderers, one shared link-building
    helper, never a third independent iteration of NAV_TABS. The
    unescaped route `slug` (06.6.1-04) is now part of what this function
    single-sources too, so a renderer can identify a specific link (e.g.
    the Health nav-tab notification dot's target) without re-deriving
    "which link is Health" from an already-escaped route string.
    """
    links = []
    for route, label in NAV_TABS:
        slug = route.lstrip("/")
        is_active = slug == active
        links.append((is_active, escape_html(route), escape_html(label), slug))
    return links


# 06.6.1-05 (D-06, superseding D-00): the horizontally-scrollable nav
# strip's renderer used to live here. Real-device testing found the
# pattern hid most tabs behind an undiscoverable swipe even after its own
# flexbox sizing bug was fixed, so it was replaced rather than repaired a
# second time — see companion/static/style.css's own header comment for
# the full flexbox history. There are now exactly two live nav
# renderers, sidebar_nav() and _mobile_nav_html() below, both fed by
# _nav_links() above.


def _health_alert_markup():
    """The Health nav-tab notification dot plus its visually-hidden
    screen-reader suffix (06.6.1-UI-SPEC.md's Layout Contract / D-02),
    built once so both `_nav_html()`-style and `sidebar_nav()` renderers
    share exactly one markup source for it — today only `sidebar_nav()`
    calls this (the horizontal `_nav_html()` renderer is retired by plan
    06.6.1-05 rather than gaining this markup itself).

    Reuses the existing `dot`/`dot--error` classes — the same visual
    treatment the Battery/Device/Pipeline error state already uses —
    plus NAV_NOTIFICATION_CLASS to override size/spacing only, rather
    than introducing a fourth status colour.

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
    return (
        '<span class="dot dot--error %s"></span>'
        '<span class="visually-hidden">%s</span>'
    ) % (NAV_NOTIFICATION_CLASS, escape_html(HEALTH_ALERT_SUFFIX_TEXT))


def sidebar_nav(active, health_alert=False):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width.

    Renders the same NAV_TABS route set as _nav_html() — via the shared
    _nav_links() helper, so the two renderers can never drift — just in
    a vertical arrangement. companion/static/style.css's 960px media
    query decides which of the two copies is visible at a given
    viewport width; this function has no opinion on visibility.

    `health_alert` (06.6.1-04, keyword-with-default so no existing
    positional call site changes meaning) appends _health_alert_markup()
    after the label text of the link whose slug matches HEALTH_NAV_SLUG,
    and only that link. The markup is already-built safe HTML and is
    interpolated verbatim, exactly like status_dot()'s output is in
    other builders — it is not routed through escape_html() again.
    """
    links = []
    for is_active, route, label, slug in _nav_links(active):
        if is_active:
            css_class = "sidebar-link sidebar-link--active"
        else:
            css_class = "sidebar-link"
        alert_html = (
            _health_alert_markup()
            if health_alert and slug == HEALTH_NAV_SLUG else "")
        links.append(
            '<a class="%s" href="%s">%s%s</a>'
            % (css_class, route, label, alert_html))
    return (
        '<nav class="sidebar-nav" aria-label="Primary navigation">%s</nav>'
        % "".join(links))


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
    return (
        '<form class="theme-form" method="post" action="/ui-theme">%s</form>'
        % "".join(options))


def _mobile_nav_html(active, theme_form_html, health_alert=False):
    """The hamburger toggle button plus the dropdown panel it controls —
    the <960px nav renderer (D-06, 06.6.1-UI-SPEC.md's Layout Contract).

    Consumes _nav_links(), the module's single iteration-and-escaping
    site for NAV_TABS, exactly like sidebar_nav() does — this is that
    helper's second consumer, not a third independent implementation.

    `theme_form_html` is taken as a parameter rather than built here via
    _theme_form_html(), so page_shell() keeps building it exactly once
    and passing the same string to both copies — this is what makes the
    "both theme-form copies present" check meaningful rather than an
    accident.

    The panel is always rendered without MOBILE_NAV_OPEN_CLASS — the
    server never renders it open. A server-rendered open state would
    flash the menu open on every page load; companion/static/
    nav-dropdown.js is what adds/removes the class client-side, keyed off
    the toggle's own aria-expanded attribute (the single source of truth
    for the open state, never a second variable to keep in sync).
    """
    links = []
    for is_active, route, label, slug in _nav_links(active):
        css_class = (
            "mobile-nav__link mobile-nav__link--active"
            if is_active else "mobile-nav__link")
        alert_html = (
            _health_alert_markup()
            if health_alert and slug == HEALTH_NAV_SLUG else "")
        links.append(
            '<a class="%s" href="%s">%s%s</a>'
            % (css_class, route, label, alert_html))
    toggle_html = (
        '<button type="button" id="%s" class="site-nav-toggle" '
        'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
    ) % (
        NAV_TOGGLE_ID, escape_html(NAV_TOGGLE_LABEL), MOBILE_NAV_ID,
        icon_html("icon-hamburger", size=24))
    panel_html = (
        '<div id="%s" class="mobile-nav">'
        '<nav class="mobile-nav__nav" aria-label="Primary navigation">%s</nav>'
        "%s"
        "</div>"
    ) % (MOBILE_NAV_ID, "".join(links), theme_form_html)
    return toggle_html + panel_html


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=False):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and every nav label are escaped here. `body`, `flash` and
    `banner` are pre-built markup strings — the caller is responsible
    for having escaped their own dynamic parts (they are typically the
    output of this module's other builders, which already escape).

    `health_alert` (06.6.1-04, keyword-with-default, placed last so no
    positional call site shifts) is threaded through to sidebar_nav() and
    (06.6.1-05) _mobile_nav_html(). It is a display signal only,
    defaulting off, so any caller without a request context — login, 404,
    the preview-image error pages — draws no dot, which is correct rather
    than merely convenient.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    sidebar_html = sidebar_nav(active, health_alert=health_alert)
    theme_form_html = _theme_form_html(resolved_theme)
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert)
    flash_html = flash or ""
    banner_html = banner or ""

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
        '<html lang="en" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "</head>\n"
        "<body>\n"
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
        '<main class="page-content dashboard-main">\n'
        "%s\n%s\n%s\n"
        "</main>\n"
        "</div>\n"
        '<script src="%s" defer></script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_theme),
        escape_html(title), escape_html(SITE_TITLE),
        ICON_DEFS_HTML,
        escape_html(SITE_TITLE),
        sidebar_html,
        theme_form_html,
        escape_html(SITE_TITLE),
        mobile_nav_html,
        flash_html, banner_html, body,
        NAV_DROPDOWN_SCRIPT_SRC,
    )


def flash_banner(message):
    """An accent-bordered confirmation block (D-07's save confirmation)."""
    return '<div class="banner banner--flash">%s</div>' % escape_html(message)


def anomaly_banner(message):
    """A destructive/warning-bordered block for D-14's anomaly flagging."""
    return '<div class="banner banner--anomaly">%s</div>' % escape_html(message)


def status_dot(state, label):
    """A small coloured status indicator plus an escaped text label.

    `state` maps to exactly one of three fixed CSS class suffixes; an
    unrecognised state falls back to the warning class rather than
    emitting an arbitrary, attacker-influenceable class name.
    """
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    return (
        '<span class="dot %s"></span><span class="dot-label">%s</span>'
        % (css_class, escape_html(label)))


def stat_tile(caption, content_html, status=None, icon=None):
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
    """
    css_class = "stat-tile " + _STAT_TILE_BORDER_CLASSES.get(
        status, _DEFAULT_STAT_TILE_CLASS)
    icon_markup = icon_html(icon, extra_class=STAT_TILE_ICON_CLASS) if icon else ""
    if icon_markup:
        caption_html = icon_markup + "<span>%s</span>" % escape_html(caption)
    else:
        caption_html = escape_html(caption)
    return (
        '<div class="%s">'
        '<p class="text-label stat-tile__caption">%s</p>'
        "%s"
        "</div>"
    ) % (css_class, caption_html, content_html)


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


def data_table(headers, rows, mono_columns=()):
    """A header row plus alternating body rows, every value escaped.

    `mono_columns` names the zero-based column indices that get the
    monospace class (callsigns, hex codes, prefixes, timestamps, per
    06-UI-SPEC.md's Typography section). Returns empty_state()'s output
    instead of an empty table when `rows` is empty.
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
            cell_class = ' class="mono"' if column_index in mono_columns else ""
            cells.append("<td%s>%s</td>" % (cell_class, escape_html(cell)))
        body_rows.append('<tr class="%s">%s</tr>' % (row_class, "".join(cells)))

    return (
        '<div class="data-table-wrap">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))
