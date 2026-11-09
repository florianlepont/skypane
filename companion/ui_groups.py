"""The grouped-list components every page is built from: a section label, a
group (one glass surface holding rows), a row, and a hero (no surface).

Pure markup, no script: a row is a link or a button when it acts, a plain
block when it only shows a value, and a trailing control (a switch, a
select) sits beside the row's own link so a control is never nested in a
link. The wording passed in is already translated; this module escapes it.
Its `*_html` arguments are the caller's own already-safe markup.
"""

from companion.layout import escape_html, icon_html

CHEVRON_ICON_ID = "icon-chevron-right"
CHIP_ICON_SIZE = 18
CHEVRON_ICON_SIZE = 16


def _attr(name, value):
    return ' %s="%s"' % (name, escape_html(value)) if value else ""


def section_label(text, label_id="", extra_class=""):
    """The small heading above a group: 13px, secondary ink, weight 600.
    It is the group's `<h2>`, so the page outline keeps it."""
    css = "section-label" + (" " + extra_class if extra_class else "")
    return '<h2 class="%s"%s>%s</h2>' % (css, _attr("id", label_id), escape_html(text))


def chip_html(icon_id):
    """The 32px icon chip: the accent colour with the on-accent glyph."""
    return '<span class="row__chip" aria-hidden="true">%s</span>' % icon_html(
        icon_id, CHIP_ICON_SIZE)


def row(label="", *, label_html="", icon="", detail="", detail_html="",
        value_html="", href="", button_attrs="", chevron=None, trailing_html="",
        extra_class="", label_id="", attrs="", lead_html=""):
    """One `<li class="row">`.

    The main area is an `<a>` when `href` is given, a `<button type="button">`
    when `button_attrs` (extra attributes, already safe) is given, else a
    `<div>`. A link or button row shows a chevron unless `chevron` is False.
    `value_html` is the right-aligned secondary text; `trailing_html` is a
    control placed after the main area (a switch, a select).
    """
    actionable = bool(href or button_attrs)
    if chevron is None:
        chevron = actionable
    text = label_html or escape_html(label)
    sub = detail_html or (escape_html(detail) if detail else "")
    inner = (
        (lead_html or (chip_html(icon) if icon else ""))
        + '<span class="row__text"><span class="row__label"%s>%s</span>%s</span>' % (
            _attr("id", label_id), text,
            ('<span class="row__detail">%s</span>' % sub) if sub else "")
        + (('<span class="row__value">%s</span>' % value_html) if value_html else "")
        + (icon_html(CHEVRON_ICON_ID, CHEVRON_ICON_SIZE, "row__chevron")
           if chevron else ""))
    if href:
        main = '<a class="row__main"%s>%s</a>' % (_attr("href", href), inner)
    elif button_attrs:
        main = '<button type="button" class="row__main" %s>%s</button>' % (
            button_attrs, inner)
    else:
        main = '<div class="row__main">%s</div>' % inner
    css = "row" + (" row--action" if actionable else "") + (
        " " + extra_class if extra_class else "")
    return '<li class="%s"%s>%s%s</li>' % (css, attrs and " " + attrs, main, trailing_html)


def group(rows_html, label="", label_id="", extra_class="", attrs=""):
    """A section label (when `label` is given) above one glass surface that
    holds `rows_html` (a run of `row()` items). A group never contains
    another group."""
    heading = section_label(label, label_id) if label else ""
    css = "group-block" + (" " + extra_class if extra_class else "")
    labelled = ' aria-labelledby="%s"' % escape_html(label_id) if label and label_id else ""
    return '<section class="%s"%s%s>%s<ul class="group">%s</ul></section>' % (
        css, labelled, attrs and " " + attrs, heading, rows_html)


def group_panel(content_html, label="", label_id="", extra_class=""):
    """A group whose body is free content (a picture, an empty state) rather
    than rows: still exactly one glass surface."""
    heading = section_label(label, label_id) if label else ""
    css = "group-block" + (" " + extra_class if extra_class else "")
    labelled = ' aria-labelledby="%s"' % escape_html(label_id) if label and label_id else ""
    return '<section class="%s"%s>%s<div class="group group--panel">%s</div></section>' % (
        css, labelled, heading, content_html)


def hero(status_line_html, *, picture_html="", lines_html="", extra_class="",
         attrs="", status_class="", heading_html="", title_html=""):
    """The hero: no surface. A picture (optional) beside an optional title
    row, the status line (a pill with its status dot) and secondary lines
    underneath. `heading_html` is an optional visually hidden heading
    that names the section for assistive technology. `title_html` is an
    optional already-safe title row rendered first in the text column."""
    css = "hero" + (" " + extra_class if extra_class else "")
    picture = ('<div class="hero__picture">%s</div>' % picture_html) if picture_html else ""
    return (
        '<section class="%s"%s>%s%s<div class="hero__body">'
        '%s<p class="hero__status%s">%s</p>%s</div></section>'
    ) % (css, attrs and " " + attrs, picture, heading_html, title_html,
         " " + status_class if status_class else "", status_line_html, lines_html)
