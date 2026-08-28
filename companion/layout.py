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

UI_THEME_CHOICES = ("auto", "light", "dark")

_STATUS_DOT_CLASSES = {
    "ok": "dot--ok",
    "warn": "dot--warn",
    "error": "dot--error",
}
_DEFAULT_STATUS_DOT_CLASS = _STATUS_DOT_CLASSES["warn"]


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


def _nav_html(active):
    links = []
    for route, label in NAV_TABS:
        slug = route.lstrip("/")
        css_class = "nav-tab nav-tab--active" if slug == active else "nav-tab"
        links.append(
            '<a class="%s" href="%s">%s</a>'
            % (css_class, escape_html(route), escape_html(label)))
    return "\n".join(links)


def _theme_form_html(resolved_theme):
    options = []
    for choice in UI_THEME_CHOICES:
        css_class = (
            "theme-option theme-option--active"
            if choice == resolved_theme else "theme-option")
        options.append(
            '<button type="submit" name="ui_theme" value="%s" class="%s">%s</button>'
            % (escape_html(choice), css_class, escape_html(choice.capitalize())))
    return (
        '<form class="theme-form" method="post" action="/ui-theme">%s</form>'
        % "".join(options))


def page_shell(title, active, body, ui_theme="auto", flash=None, banner=None):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and every nav label are escaped here. `body`, `flash` and
    `banner` are pre-built markup strings — the caller is responsible
    for having escaped their own dynamic parts (they are typically the
    output of this module's other builders, which already escape).
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    nav_html = _nav_html(active)
    theme_form_html = _theme_form_html(resolved_theme)
    flash_html = flash or ""
    banner_html = banner or ""

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
        '<header class="site-header">\n'
        '<span class="site-title">%s</span>\n'
        '<nav class="nav-bar">%s</nav>\n'
        "%s\n"
        "</header>\n"
        '<main class="page-content">\n'
        "%s\n%s\n%s\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_theme),
        escape_html(title), escape_html(SITE_TITLE),
        escape_html(SITE_TITLE),
        nav_html,
        theme_form_html,
        flash_html, banner_html, body,
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
