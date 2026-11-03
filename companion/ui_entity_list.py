"""companion/ui_entity_list.py: the shared list of entities (frames, users).

One `ul.entity-list` of `li.entity-row` rows, each a dot (optional), a text
block (title, muted second line, optional pills) and one trailing action.
The same DOM is a single column on a phone and columns on a desktop (CSS
only). There is never a table, a monospace face or truncated text.

Plain text arguments (titles, subtitles, labels, hrefs) are escaped here.
The arguments named `*_html` are markup the caller has already built and
escaped (a status dot, pills, an action button).
"""
import companion.ui_modal as ui_modal
from companion.ui_base import escape_html, icon_html


def entity_list_html(rows_html, count_line_html=""):
    """The list wrapper. `rows_html` is the concatenated rows; the optional
    count line sits above the list."""
    return '%s<ul class="entity-list">%s</ul>' % (count_line_html, rows_html)


def count_line_html(text):
    """The compact count line above a list, in the 12px label voice."""
    return '<p class="entity-count text-label">%s</p>' % escape_html(text)


def entity_row_html(dot_html, title, subtitle, pills_html, action_html, href=None):
    """One row. `title` is a link when `href` is given, else plain text;
    `subtitle` is the muted second line (may be empty or None)."""
    title_text = escape_html(title)
    if href:
        title_markup = '<a class="entity-row__title" href="%s">%s</a>' % (
            escape_html(href), title_text)
    else:
        title_markup = '<span class="entity-row__title">%s</span>' % title_text
    subtitle_markup = (
        '<span class="entity-row__meta text-label">%s</span>' % escape_html(subtitle)
        if subtitle else "")
    dot_markup = dot_html or ""
    # Without a dot the text block takes the first grid track instead.
    css = "entity-row" if dot_markup else "entity-row entity-row--no-dot"
    pills_markup = (
        '<span class="entity-row__pills">%s</span>' % pills_html if pills_html else "")
    return (
        '<li class="%s">%s<div class="entity-row__text">%s%s%s</div>%s</li>'
    ) % (css, dot_markup, title_markup, subtitle_markup, pills_markup, action_html or "")


def _menu_item_html(label, target, destructive):
    """One 44px menu link. A lowercase-slug `target` is a dialog id and
    becomes a modal trigger; anything else is a server-built path."""
    css = "row-menu__item"
    if destructive:
        css += " row-menu__item--destructive"
    try:
        href = "#" + ui_modal.validated_slug(target)
        opener = " data-modal-open"
    except ValueError:
        href = escape_html(target)
        opener = ""
    return '<a class="%s" href="%s"%s>%s</a>' % (css, href, opener, escape_html(label))


def row_menu_html(aria_label, items):
    """A `<details class="row-menu">` actions menu. `items` is a sequence of
    (label, href-or-dialog-id, destructive). Works without script: details
    toggles natively and dialog items are hash links."""
    links = "".join(_menu_item_html(*item) for item in items)
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" '
        'aria-label="%s">%s</summary><div class="row-menu__panel">%s</div></details>'
    ) % (escape_html(aria_label), icon_html("icon-more-vertical", size=20), links)
