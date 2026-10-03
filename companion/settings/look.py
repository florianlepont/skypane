"""The Display page's "look" vocabulary: every registry theme read as
three independent choices (Colour, Background, Diagonal stripe), and the
markup built on that reading.

The axes are derived from `server.themes.THEMES` itself, never from a
hand-written table, so a theme added to the registry lands in its cell
automatically. A combination with no theme is a *gap*: it is shown
disabled with a reason, never hidden and never invented.

The posted values do not change: every control that is submitted is a
native radio carrying a real theme id (or the empty "same as
departures" signal). The three-axis picker is a script-only layer that
checks one of those radios.
"""
import json

from companion import i18n
from companion.layout import escape_html
from server import device_config, panel_format

from companion.settings.form import SETTINGS_FORM_ID


COLOUR_BLACK = "black"
COLOUR_YELLOW = "yellow"
COLOUR_RED = "red"
COLOUR_GREEN = "green"
COLOUR_BLUE = "blue"
# Display order of the colour dots and the table rows.
COLOURS = (COLOUR_BLACK, COLOUR_YELLOW, COLOUR_RED, COLOUR_GREEN, COLOUR_BLUE)
_COLOUR_INDEXES = {
    COLOUR_BLACK: panel_format.IDX_BLACK,
    COLOUR_YELLOW: panel_format.IDX_YELLOW,
    COLOUR_RED: panel_format.IDX_RED,
    COLOUR_GREEN: panel_format.IDX_GREEN,
    COLOUR_BLUE: panel_format.IDX_BLUE,
}
_COLOUR_BY_INDEX = {index: colour for colour, index in _COLOUR_INDEXES.items()}

BACKGROUND_PAPER = "paper"
BACKGROUND_FULL = "full"
BACKGROUND_SOFT = "soft"
BACKGROUNDS = (BACKGROUND_PAPER, BACKGROUND_FULL, BACKGROUND_SOFT)

STRIPE_NONE = "none"
STRIPE_SOLID = "solid"
STRIPE_SOFT = "soft"
STRIPES = (STRIPE_NONE, STRIPE_SOLID, STRIPE_SOFT)

# The table's columns, as (background, stripe) pairs. Plain paper (paper,
# none) is the one colourless look and sits outside the table.
STYLE_COLUMNS = (
    (BACKGROUND_FULL, STRIPE_NONE),
    (BACKGROUND_SOFT, STRIPE_NONE),
    (BACKGROUND_PAPER, STRIPE_SOLID),
    (BACKGROUND_PAPER, STRIPE_SOFT),
    (BACKGROUND_SOFT, STRIPE_SOLID),
)

COLOUR_LABELS = {
    COLOUR_BLACK: i18n.msg("look.black", "Black"),
    COLOUR_YELLOW: i18n.msg("look.yellow", "Yellow"),
    COLOUR_RED: i18n.msg("look.red", "Red"),
    COLOUR_GREEN: i18n.msg("look.green", "Green"),
    COLOUR_BLUE: i18n.msg("look.blue", "Blue"),
}
# "Soft" rather than the registry's "Light", so the frame's look is never
# confused with the companion's own light and dark modes.
BACKGROUND_LABELS = {
    BACKGROUND_PAPER: i18n.msg("look.background_paper", "Paper"),
    BACKGROUND_FULL: i18n.msg("look.background_full", "Full"),
    BACKGROUND_SOFT: i18n.msg("look.background_soft", "Soft"),
}
STRIPE_LABELS = {
    STRIPE_NONE: i18n.msg("look.stripe_none", "None"),
    STRIPE_SOLID: i18n.msg("look.stripe_solid", "Solid"),
    STRIPE_SOFT: i18n.msg("look.stripe_soft", "Soft"),
}
STYLE_LABELS = {
    (BACKGROUND_FULL, STRIPE_NONE): i18n.msg("look.style_solid", "Solid"),
    (BACKGROUND_SOFT, STRIPE_NONE): i18n.msg("look.style_soft", "Soft"),
    (BACKGROUND_PAPER, STRIPE_SOLID): i18n.msg("look.style_stripe", "Stripe"),
    (BACKGROUND_PAPER, STRIPE_SOFT): i18n.msg("look.style_soft_stripe", "Soft stripe"),
    (BACKGROUND_SOFT, STRIPE_SOLID): i18n.msg("look.style_stripe_on_soft", "Stripe on soft"),
}
PLAIN_PAPER_LABEL = i18n.msg("look.plain_paper", "Plain paper")
COLOUR_AXIS_LABEL = i18n.msg("look.colour", "Colour")
BACKGROUND_AXIS_LABEL = i18n.msg("look.background", "Background")
STRIPE_AXIS_LABEL = i18n.msg("look.diagonal_stripe", "Diagonal stripe")

REASON_STRIPE_ON_FULL = "stripe_on_full"
REASON_SOFT_ON_SOFT = "soft_on_soft"
REASON_YELLOW_STRIPE = "yellow_stripe"
REASON_NO_THEME = "no_theme"
REASON_MESSAGES = {
    REASON_STRIPE_ON_FULL: i18n.msg(
        "look.a_stripe_would_vanish_on_a_full_background",
        "A stripe would vanish on a full background."),
    REASON_SOFT_ON_SOFT: i18n.msg(
        "look.a_soft_stripe_would_vanish_on_a_soft_background",
        "A soft stripe would vanish on a soft background."),
    REASON_YELLOW_STRIPE: i18n.msg(
        "look.text_on_a_stripe_is_white_unreadable_on_yellow",
        "Text on a stripe is white, and white on yellow is unreadable."),
    REASON_NO_THEME: i18n.msg(
        "look.the_frame_has_no_theme_for_this_combination",
        "The frame has no theme for this combination yet."),
}
GAP_CELL_TEMPLATE = i18n.msg("look.not_available", "%s: not available")
TABLE_CAPTION_TEMPLATE = i18n.msg("look.colour_and_style", "%s: colour and style")
NOTES_HEADING = i18n.msg("look.why_some_cells_are_empty", "Why some cells are empty")

# Field names of the three script-only axis radio groups. They are
# never associated with the settings form; inside the rule form they
# are posted but ignored by the rule-add handler.
AXIS_COLOUR = "colour"
AXIS_BACKGROUND = "background"
AXIS_STRIPE = "stripe"

# How strongly a soft (dithered) ink tints white paper in a swatch: the
# panel dithers a soft field roughly halfway toward white, which reads as
# this flat tint at swatch size, where a literal stipple would only moire.
SOFT_INK_OPACITY = "0.45"


def theme_axes(theme_id):
    """`(colour, background, stripe)` for one registry theme. `colour` is
    `None` for the colourless plain-paper theme. A band theme takes its
    colour from the band; a field theme from its field.
    """
    theme = device_config.THEMES[theme_id]
    field_index = theme["departing_index"]
    if field_index == panel_format.IDX_WHITE:
        background = BACKGROUND_PAPER
    else:
        background = BACKGROUND_SOFT if theme.get("dithered") else BACKGROUND_FULL
    if "band_index" in theme:
        stripe = STRIPE_SOFT if theme.get("band_dithered") else STRIPE_SOLID
        colour = _COLOUR_BY_INDEX[theme["band_index"]]
    else:
        stripe = STRIPE_NONE
        colour = None if background == BACKGROUND_PAPER else _COLOUR_BY_INDEX[field_index]
    return colour, background, stripe


def _cells():
    """`{(colour, background, stripe): theme_id}` for every real theme;
    plain paper fills its cell under every colour, since a page with no
    background colour and no stripe looks the same whatever was picked.
    """
    cells = {}
    for theme_id in device_config.THEME_IDS:
        colour, background, stripe = theme_axes(theme_id)
        if colour is None:
            for any_colour in COLOURS:
                cells[(any_colour, background, stripe)] = theme_id
        else:
            cells[(colour, background, stripe)] = theme_id
    return cells


def resolve(colour, background, stripe):
    """The theme id for three choices, or `None` for a gap."""
    return _cells().get((colour, background, stripe))


def gap_reason(colour, background, stripe):
    """Why `(colour, background, stripe)` has no theme: one of the
    REASON_* keys, or `None` when it does have one.
    """
    if resolve(colour, background, stripe) is not None:
        return None
    if background == BACKGROUND_FULL and stripe != STRIPE_NONE:
        return REASON_STRIPE_ON_FULL
    if background == BACKGROUND_SOFT and stripe == STRIPE_SOFT:
        return REASON_SOFT_ON_SOFT
    if colour == COLOUR_YELLOW and stripe != STRIPE_NONE:
        return REASON_YELLOW_STRIPE
    return REASON_NO_THEME


def look_sentence(theme_id):
    """The read-back for one theme: "Red, stripe on soft", "Black, soft",
    or "Plain paper". The comma is punctuation, not a translatable word.
    """
    colour, background, stripe = theme_axes(theme_id)
    if colour is None:
        return i18n.t(PLAIN_PAPER_LABEL)
    style = i18n.t(STYLE_LABELS[(background, stripe)])
    return "%s, %s" % (i18n.t(COLOUR_LABELS[colour]), style.lower())


def colour_hex(colour):
    return _palette_hex(_COLOUR_INDEXES[colour])


def _palette_hex(index):
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def _paint_attrs(index, dithered):
    """SVG presentation attributes for one ink: its flat colour, made
    translucent over the white paper underneath when the panel dithers it.
    """
    attrs = 'fill="%s"' % escape_html(_palette_hex(index))
    if dithered and index != panel_format.IDX_WHITE:
        attrs += ' fill-opacity="%s"' % SOFT_INK_OPACITY
    return attrs


def swatch_svg(theme_id, extra_class=""):
    """A small portrait swatch of one theme: the field, plus the diagonal
    band for a band theme. Colours are SVG presentation attributes
    computed from the panel palette, never a style attribute.
    """
    theme = device_config.THEMES[theme_id]
    band_html = ""
    if "band_index" in theme:
        band_html = '<polygon points="3,32 11,32 21,0 13,0" %s></polygon>' % _paint_attrs(
            theme["band_index"], theme.get("band_dithered"))
    css_class = "look-swatch" + (" " + extra_class if extra_class else "")
    return (
        '<svg class="%s" viewBox="0 0 24 32" width="24" height="32" aria-hidden="true" '
        'focusable="false"><rect width="24" height="32" fill="%s"></rect>'
        '<rect width="24" height="32" %s></rect>%s</svg>'
    ) % (
        escape_html(css_class), escape_html(_palette_hex(panel_format.IDX_WHITE)),
        _paint_attrs(theme["departing_index"], theme.get("dithered")), band_html)


def _gap_notes(gaps):
    """The ordered, de-duplicated reasons behind a table's gaps, each
    with its footnote number."""
    numbers = {}
    for reason in gaps:
        if reason not in numbers:
            numbers[reason] = len(numbers) + 1
    return numbers


def _table_cell_html(field_name, colour, background, stripe, selected_theme_id, preview_src, notes, form_id):
    theme_id = resolve(colour, background, stripe)
    style_label = i18n.t(STYLE_LABELS[(background, stripe)])
    name = "%s, %s" % (i18n.t(COLOUR_LABELS[colour]), style_label.lower())
    if theme_id is None:
        reason = gap_reason(colour, background, stripe)
        return (
            '<td class="look-table__gap"><span class="look-table__gap-mark" aria-hidden="true">'
            "<sup>%d</sup></span>"
            '<span class="visually-hidden">%s. %s</span></td>'
        ) % (
            notes[reason], escape_html(i18n.t(GAP_CELL_TEMPLATE) % name),
            escape_html(i18n.t(REASON_MESSAGES[reason])))
    return '<td>%s</td>' % _option_html(
        field_name, theme_id, theme_id == selected_theme_id, name, preview_src(theme_id),
        form_id, extra_class="look-cell")


def _option_html(field_name, value, checked, label_text, preview_src, form_id, extra_class="", swatch=True):
    """One native radio wrapped in its label. `data-preview-src` is the
    frame preview the script shows when this radio is checked; `form_id`
    (or `None`) associates the radio with a form it is not nested in. The
    option checked at render time (the saved look) carries a `--saved`
    modifier, which keeps a quiet marker once another option is picked.
    """
    form_attr = ' form="%s"' % escape_html(form_id) if form_id else ""
    css_class = extra_class or "look-option"
    if checked:
        css_class += " %s--saved" % css_class
    swatch_html = swatch_svg(value) if swatch and value else ""
    visible = ' class="visually-hidden"' if extra_class == "look-cell" else ' class="look-option__name"'
    return (
        '<label class="%s" data-preview-src="%s">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
        "%s<span%s>%s</span></label>"
    ) % (
        escape_html(css_class), escape_html(preview_src),
        escape_html(field_name), escape_html(value), form_attr,
        " checked" if checked else "",
        swatch_html, visible, escape_html(label_text))


def look_table_html(field_name, selected_theme_id, caption, preview_src, leading_html="", form_id=SETTINGS_FORM_ID):
    """The no-script picker for one usage: a colour x style table of
    native radios, one per real theme id, with every gap marked and
    explained under the table. Plain paper (and `leading_html`, e.g.
    "Same as departures") sit above it in the same radio group.

    `preview_src(theme_id)` gives each option's frame-preview URL.
    """
    gaps = [
        gap_reason(colour, background, stripe)
        for colour in COLOURS for background, stripe in STYLE_COLUMNS
        if resolve(colour, background, stripe) is None]
    notes = _gap_notes(gaps)
    head = "".join(
        '<th scope="col">%s</th>' % escape_html(i18n.t(STYLE_LABELS[pair]))
        for pair in STYLE_COLUMNS)
    rows = []
    for colour in COLOURS:
        cells = "".join(
            _table_cell_html(
                field_name, colour, background, stripe, selected_theme_id, preview_src, notes, form_id)
            for background, stripe in STYLE_COLUMNS)
        rows.append(
            '<tr><th scope="row"><svg class="look-table__ink" viewBox="0 0 12 12" width="12" '
            'height="12" aria-hidden="true" focusable="false"><circle cx="6" cy="6" r="6" '
            'fill="%s"></circle></svg><span class="look-table__colour">%s</span></th>%s</tr>' % (
                escape_html(colour_hex(colour)), escape_html(i18n.t(COLOUR_LABELS[colour])),
                cells))
    paper_id = resolve(COLOURS[0], BACKGROUND_PAPER, STRIPE_NONE)
    paper_html = _option_html(
        field_name, paper_id, paper_id == selected_theme_id, i18n.t(PLAIN_PAPER_LABEL),
        preview_src(paper_id), form_id)
    notes_html = "".join(
        '<li><sup>%d</sup> %s</li>' % (number, escape_html(i18n.t(REASON_MESSAGES[reason])))
        for reason, number in notes.items())
    return (
        '<div class="look-table-block">'
        '<div class="look-table__options">%s%s</div>'
        '<div class="look-table__scroll">'
        '<table class="look-table"><caption class="visually-hidden">%s</caption>'
        '<thead><tr><td></td>%s</tr></thead><tbody>%s</tbody></table></div>'
        '<p class="visually-hidden">%s</p><ul class="look-table__notes">%s</ul>'
        "</div>"
    ) % (
        leading_html, paper_html,
        escape_html(i18n.t(TABLE_CAPTION_TEMPLATE) % caption), head, "".join(rows),
        escape_html(i18n.t(NOTES_HEADING)), notes_html)


def same_option_html(field_name, checked, label_text, form_id=SETTINGS_FORM_ID):
    """The leading "Same as departures" radio: posts the empty string,
    the clear signal `handle_post()` already understands."""
    return _option_html(field_name, "", checked, label_text, "", form_id, swatch=False)


def look_model_json():
    """Everything the picker script needs, computed here so the script
    holds no theme knowledge of its own: the valid cells, the reason
    for every gap, each theme's axes and read-back, and the ink colours.
    """
    cells = {}
    reasons = {}
    for colour in COLOURS:
        for background in BACKGROUNDS:
            for stripe in STRIPES:
                key = "%s|%s|%s" % (colour, background, stripe)
                theme_id = resolve(colour, background, stripe)
                if theme_id is None:
                    reasons[key] = i18n.t(REASON_MESSAGES[gap_reason(colour, background, stripe)])
                else:
                    cells[key] = theme_id
    axes = {}
    sentences = {}
    for theme_id in device_config.THEME_IDS:
        colour, background, stripe = theme_axes(theme_id)
        axes[theme_id] = [colour or "", background, stripe]
        sentences[theme_id] = look_sentence(theme_id)
    return json.dumps({
        "cells": cells, "reasons": reasons, "axes": axes, "sentences": sentences,
        "colours": {colour: colour_hex(colour) for colour in COLOURS},
        "colourNames": {colour: i18n.t(COLOUR_LABELS[colour]) for colour in COLOURS},
        "paper": _palette_hex(panel_format.IDX_WHITE),
        "softOpacity": SOFT_INK_OPACITY,
    }, sort_keys=True, ensure_ascii=False)


def _axis_option_html(prefix, axis, value, label_html, extra_class):
    return (
        '<label class="%s"><input type="radio" name="%s_%s" value="%s" '
        'class="visually-hidden" data-look-axis="%s">%s</label>'
    ) % (extra_class, escape_html(prefix), axis, value, axis, label_html)


def axes_html(prefix):
    """The three script-only choices: five colour dots, then the
    Background and Diagonal stripe segmented controls. The script fills
    in which options are checked or disabled, and why.
    """
    dots = "".join(
        _axis_option_html(
            prefix, AXIS_COLOUR, colour,
            '<svg class="look-dot__ink" viewBox="0 0 34 34" width="34" height="34" aria-hidden="true" '
            'focusable="false"><circle cx="17" cy="17" r="16" fill="%s"></circle></svg>'
            '<span class="visually-hidden">%s</span>' % (
                escape_html(colour_hex(colour)), escape_html(i18n.t(COLOUR_LABELS[colour]))),
            "look-dot")
        for colour in COLOURS)
    backgrounds = "".join(
        _axis_option_html(
            prefix, AXIS_BACKGROUND, background,
            '<svg class="look-seg__icon" viewBox="0 0 18 18" width="18" height="18" aria-hidden="true" '
            'focusable="false"><rect width="18" height="18" rx="3" fill="%s"></rect>'
            '<rect width="18" height="18" rx="3" fill="%s" data-look-bg-icon="%s"></rect>'
            "</svg><span>%s</span>" % (
                escape_html(_palette_hex(panel_format.IDX_WHITE)),
                escape_html(_palette_hex(panel_format.IDX_WHITE)), background,
                escape_html(i18n.t(BACKGROUND_LABELS[background]))),
            "look-seg__option")
        for background in BACKGROUNDS)
    why_id = "%s-why" % prefix
    stripes = "".join(
        _axis_option_html(
            prefix, AXIS_STRIPE, stripe,
            "<span>%s</span>" % escape_html(i18n.t(STRIPE_LABELS[stripe])),
            "look-seg__option")
        for stripe in STRIPES)
    return (
        '<div class="look-axes" data-look-axes>'
        '<fieldset class="look-axis"><legend class="look-axis__label">%s'
        ' <span class="look-axis__value" data-look-colour-name></span></legend>'
        '<div class="look-dots">%s</div></fieldset>'
        '<fieldset class="look-axis"><legend class="look-axis__label">%s</legend>'
        '<div class="look-seg">%s</div></fieldset>'
        '<fieldset class="look-axis" aria-describedby="%s"><legend class="look-axis__label">%s</legend>'
        '<div class="look-seg">%s</div>'
        '<p class="look-axis__why" id="%s" data-look-why aria-live="polite"></p></fieldset>'
        "</div>"
    ) % (
        escape_html(i18n.t(COLOUR_AXIS_LABEL)), dots,
        escape_html(i18n.t(BACKGROUND_AXIS_LABEL)), backgrounds,
        escape_html(why_id), escape_html(i18n.t(STRIPE_AXIS_LABEL)), stripes, escape_html(why_id))

