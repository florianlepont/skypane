"""Health page rows: the one card that lists every subsystem as a row.

A row is a native `<details>`: its `<summary>` carries a state icon, the
subsystem name, a one-line verdict and a right-aligned value, and its body
carries the evidence (facts, a chart, a table). A row in a warn or error
state renders already open, so the page shows what needs attention without
a click; every other row is one tap away. Everything works with scripts
blocked, because the disclosure is the browser's own.

This module holds only the generic components. What each row says is
decided in companion/pages/health_page.py, which owns the state wording
and the data reads; nothing here imports a page module.

The state is never carried by colour alone: each of the four states has
its own icon shape, and a visually hidden word names it for a screen
reader.
"""

from companion.layout import escape_html
import companion.draw as draw
import companion.i18n as i18n
import companion.layout as layout

# One glyph per state, all members of layout.ICON_IDS. The shapes differ
# (tick, triangle, cross, circled i), which is what keeps the state
# readable without its colour.
STATE_ICON_IDS = {
    "ok": "icon-check",
    "warn": "icon-warning",
    "error": "icon-toast-error",
    "off": "icon-info",
}

# "off" is the neutral state: a fact with no verdict on it (a held frame,
# a pipeline that has not run yet, a rate with no pass mark). It is never
# a problem, which is why it opens nothing and carries no status colour.
STATE_WORDS = {
    "ok": i18n.msg("health.row_state_ok", "Healthy"),
    "warn": i18n.msg("health.row_state_warn", "Needs attention"),
    "error": i18n.msg("health.row_state_error", "Problem"),
    "off": i18n.msg("health.row_state_off", "Neutral"),
}

# The states whose row opens itself.
OPEN_STATES = ("warn", "error")

ROWS_CLASS = "health-rows"
GROUP_CLASS = "health-rows__group"
ROW_CLASS = "health-row"
SUMMARY_CLASS = "health-row__summary"
ROW_ID_PREFIX = "health-row-"

# The ring beside the identification value is the same drawing as the
# battery ring, at a size that sits on a row's text line.
RING_SIZE_PX = 24


def resolved_state(state):
    """`state` when it is one of the four known states, else "off": the
    state reaches a class name and an icon id, so it is looked up, never
    interpolated."""
    return state if state in STATE_ICON_IDS else "off"


def row_html(row_id, state, name, verdict, value_html, body_html):
    """One row. `name` and `verdict` are already-translated plain text and
    are escaped here; `value_html` and `body_html` are the caller's own
    already-safe markup, interpolated verbatim. `row_id` is a module
    constant, never data."""
    state = resolved_state(state)
    open_attr = " open" if state in OPEN_STATES else ""
    icon = layout.icon_html(STATE_ICON_IDS[state], size=16)
    return (
        '<details class="%s" data-state="%s" id="%s%s"%s>'
        '<summary class="%s">'
        '<span class="health-row__icon">%s'
        '<span class="visually-hidden">%s</span></span>'
        '<span class="health-row__name">%s</span>'
        '<span class="health-row__verdict">%s</span>'
        '<span class="health-row__value">%s</span>'
        "</summary>"
        '<div class="health-row__body">%s</div>'
        "</details>"
    ) % (
        ROW_CLASS, state, ROW_ID_PREFIX, escape_html(row_id), open_attr,
        SUMMARY_CLASS, icon, escape_html(i18n.t(STATE_WORDS[state])),
        escape_html(name), escape_html(verdict), value_html, body_html)


def group_html(group_id, heading, rows_html):
    """A group band (an `<h2>`, so the page outline keeps its two
    sections and the id stays a link target) followed by its rows."""
    return '<h2 id="%s" class="%s">%s</h2>%s' % (
        escape_html(group_id), GROUP_CLASS, escape_html(heading), rows_html)


def card_html(groups_html):
    """The single card holding every group and row."""
    return '<div class="%s">%s</div>' % (ROWS_CLASS, groups_html)


def facts_html(facts):
    """A label/value list. `facts` is an iterable of `(label_html,
    value_html)` pairs, both already safe."""
    items = "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (label_html, value_html)
        for label_html, value_html in facts)
    return '<dl class="health-row__facts">%s</dl>' % items if items else ""


def note_html(text):
    """A muted explanatory sentence under the facts. `text` is plain."""
    return '<p class="health-row__note">%s</p>' % escape_html(text)


def ring_html(fraction):
    """The small neutral ring: ink-coloured, because the figure it draws
    is a rate with no pass mark, not a verdict."""
    return '<span class="health-row__ring">%s</span>' % draw.ring_gauge(
        fraction, RING_SIZE_PX)
