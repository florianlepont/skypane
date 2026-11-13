"""The one segmented control: a track of equal segments with one selected.

Three forms share one look (the stylesheet's `--seg-*` tokens) and one set of
classes: radios (a choice inside a form), buttons (a choice that posts or
submits on its own) and links (a choice that is a page). Every segment is a
44px target on a phone, its label centred; the selected segment is a solid
pill. Wording passed in is already translated; this module escapes it.
"""
from companion.ui_base import escape_html


# A strip of links that is the page's own section strip carries its selection
# across the page change (the stylesheet names the selected segment for the
# page transition). The marker is the strip's last child: the shell holds the
# page's first frame until it is parsed, so the transition always finds the
# strip. A page shows one such strip at most.
CARRY_ATTR = " data-tabs-carry"
CARRY_END_ID = "tabs-carry-end"
CARRY_END_HTML = '<span id="%s" hidden></span>' % CARRY_END_ID


def _classes(base, extra_class):
    return base + (" " + extra_class if extra_class else "")


def segmented_radios_html(options, extra_class=""):
    """Native radios styled as one control. `options` is a sequence of
    `(radio_id, name, value, label, title, selected)`; the radio is visually
    hidden and its `<label>` is the segment (`title` is the label's tooltip)."""
    parts = []
    for radio_id, name, value, label, title, selected in options:
        parts.append(
            '<input type="radio" name="%s" id="%s" value="%s" class="visually-hidden"%s>'
            '<label for="%s" title="%s">%s</label>' % (
                escape_html(name), escape_html(radio_id), escape_html(value),
                " checked" if selected else "", escape_html(radio_id),
                escape_html(title), escape_html(label)))
    return '<div class="%s">%s</div>' % (_classes("theme-form", extra_class), "".join(parts))


def segmented_buttons_html(form_attrs, buttons, extra_class="", hidden_html=""):
    """A form whose segments are submit buttons. `form_attrs` is the form's own
    already-escaped attribute text (method, action, aria-label); `buttons` is a
    sequence of `(name, value, label, selected, button_attrs, title)` where
    `button_attrs` is already-escaped extra attribute text ("" for none) and
    `title` the optional tooltip ("" for none). `hidden_html` is markup placed
    before the buttons (a hidden anti-forgery input)."""
    parts = []
    for name, value, label, selected, button_attrs, title in buttons:
        parts.append(
            '<button type="submit" name="%s" value="%s" class="%s" aria-pressed="%s"%s%s>%s</button>' % (
                escape_html(name), escape_html(value),
                "theme-option theme-option--active" if selected else "theme-option",
                "true" if selected else "false",
                (' title="%s"' % escape_html(title)) if title else "", button_attrs,
                escape_html(label)))
    return '<form class="%s" %s>%s</form>' % (
        _classes("theme-form", extra_class), form_attrs, hidden_html + "".join(parts))


def segmented_links_html(links, aria_label, extra_class="", nav_attrs="", lead_html="",
                         carry=False):
    """A navigation whose segments are links. `links` is a sequence of
    `(href, inner_html, current, link_attrs)`: `href` and `link_attrs` are
    already escaped, `inner_html` is the segment's own already-safe markup
    (a `<span>` carrying the label). `lead_html` sits first in the track.
    `carry` marks the page's own section strip (see `CARRY_ATTR`)."""
    parts = []
    for href, inner_html, current, link_attrs in links:
        parts.append(
            '<a class="personalisation-nav__link" href="%s"%s%s>%s</a>' % (
                href, link_attrs, ' aria-current="page"' if current else "", inner_html))
    return '<nav class="%s" aria-label="%s"%s%s>%s%s%s</nav>' % (
        _classes("personalisation-nav", extra_class), escape_html(aria_label), nav_attrs,
        CARRY_ATTR if carry else "", lead_html, "".join(parts),
        CARRY_END_HTML if carry else "")
