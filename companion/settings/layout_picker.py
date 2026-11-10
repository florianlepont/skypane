"""The Personalisation page's layout and pairing pickers.

Two pieces of markup, both native radios that belong to the settings form,
so they save with scripts blocked:

  * the Layout view: one radio card per screen layout a frame can show,
    each with a small picture of that layout;
  * the pairing picker: for a frame on a giant-lettering layout, the five
    field / lettering pairings replace the eighteen-theme picker for
    departures and for "theme when arriving".

A pairing is stored as the theme id it shares its name with, so every
validator that accepts a theme id still accepts it and nothing stored is
rewritten. A stored theme that is not a pairing (green, black, a band
theme) is read as the pairing it maps to and shown selected; the stored
value changes only when the owner saves a different card.
"""
from companion import i18n
from companion import theme_preview
from companion.layout import escape_html
import companion.layout as layout
from server import pairings, screen_layouts

from companion.settings import look
from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, SELECTED_LABEL, SETTINGS_FORM_ID,
    _field_error_html, _submitted_or_current)
from companion.settings.theme import (
    COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_DEPARTURES, FRAME_COLOURS_ROW_LABELS, LOOK_FIELDS,
    LOOK_PREVIEW_ALT_TEMPLATE, SAME_AS_DEPARTURES_LABEL, departures_safe_theme_id)

LAYOUT_FIELD = "layout"

LAYOUT_TITLE = i18n.msg("look.layout", "Layout")
LAYOUT_GROUP_LABEL = i18n.msg("look.layout_group", "Screen layout")
LAYOUT_HELP = i18n.msg(
    "look.layout_help",
    "The picture repaints at the next flight or transition.")
LAYOUT_NAMES = {
    "classic": i18n.msg("look.layout_classic", "Classic"),
    "a": i18n.msg("look.layout_a", "A: nose and tail"),
    "b": i18n.msg("look.layout_b", "B: whole aircraft"),
    "c": i18n.msg("look.layout_c", "C: lettering on top, aircraft at the bottom"),
    "a_diagonal": i18n.msg("look.layout_a_diagonal", "A with diagonal band"),
}
LAYOUT_PREVIEW_ALT_TEMPLATE = i18n.msg("look.layout_preview_alt", "Layout preview: %s")

PAIRING_GROUP_LABEL = i18n.msg("look.pairing_group", "Colour")
PAIRING_HELP = i18n.msg(
    "look.pairing_help",
    "Pick the field colour. It repaints at the next flight or transition.")
ARRIVING_NUDGE = i18n.msg(
    "look.pairing_arriving_nudge",
    "Pick an arrivals colour, or landings look like take-offs.")
PAIRING_NAMES = {
    "grey": i18n.msg("look.pairing_grey", "Grey"),
    "blue_light": i18n.msg("look.pairing_blue", "Light blue"),
    "red_light": i18n.msg("look.pairing_red", "Light red"),
    "yellow_light": i18n.msg("look.pairing_yellow", "Light yellow"),
    "white": i18n.msg("look.pairing_white", "White"),
}


def _radio_card_html(field, value, checked, saved, name, preview_src, alt):
    """One radio card: the small picture, the name and, on the selected one,
    a check. `saved` marks the value stored now, which keeps a quiet marker
    once another card is picked."""
    badge = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if saved else "")
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_SMALL]
    return (
        '<label class="runway-card look-pick__card%s"%s>'
        '<input type="radio" name="%s" value="%s" class="visually-hidden" form="%s"%s>'
        '<img class="look-pick__preview" src="%s" width="%d" height="%d" alt="%s" '
        'loading="lazy" decoding="async">'
        '<span class="runway-card__number look-pick__name">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        " runway-card--selected" if saved else "", badge,
        escape_html(field), escape_html(value), escape_html(SETTINGS_FORM_ID),
        " checked" if checked else "",
        escape_html(preview_src), width, height, escape_html(alt),
        escape_html(name), layout.icon_html("icon-check"),
        escape_html(i18n.t(SELECTED_LABEL)))


def _help_html(message):
    return '<p class="text-label section-caption">%s</p>' % escape_html(i18n.t(message))


def layout_view_html(current_layout, current_theme_id, errors=None, submitted=None):
    """The Layout view's body: the help line, then one card per layout. A
    rejected submitted value never reaches the markup: the saved layout is
    shown instead."""
    saved = screen_layouts.normalise_layout_id(current_layout)
    chosen = _submitted_or_current(submitted, LAYOUT_FIELD, saved)
    if chosen not in screen_layouts.LAYOUT_IDS:
        chosen = saved
    picture_theme = departures_safe_theme_id(current_theme_id, None)
    cards = "".join(
        _radio_card_html(
            LAYOUT_FIELD, layout_id, layout_id == chosen, layout_id == saved,
            i18n.t(LAYOUT_NAMES[layout_id]),
            theme_preview.frame_preview_src(
                picture_theme, theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
                theme_preview.FRAME_PREVIEW_SIZE_SMALL, layout=layout_id),
            i18n.t(LAYOUT_PREVIEW_ALT_TEMPLATE) % i18n.t(LAYOUT_NAMES[layout_id]))
        for layout_id in screen_layouts.LAYOUT_IDS)
    return '%s<div class="look-pick__grid layout-pick__grid" role="radiogroup" aria-label="%s">%s</div>%s' % (
        _help_html(LAYOUT_HELP), escape_html(i18n.t(LAYOUT_GROUP_LABEL)), cards,
        _field_error_html(errors, LAYOUT_FIELD, LAYOUT_FIELD))


def pairing_id_for(theme_id):
    """The pairing id a stored theme id is shown as. Pure: nothing stored
    changes."""
    return pairings.pairing_for_theme(theme_id).id


def _pairing_cards_html(field, selected, saved, usage, layout_id, state):
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    return "".join(
        _radio_card_html(
            field, pairing_id, pairing_id == selected, pairing_id == saved,
            i18n.t(PAIRING_NAMES[pairing_id]),
            theme_preview.frame_preview_src(
                pairing_id, state, theme_preview.FRAME_PREVIEW_SIZE_SMALL, layout=layout_id),
            i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, i18n.t(PAIRING_NAMES[pairing_id])))
        for pairing_id in look.offered_pairing_ids())


def _departures_panel_html(layout_id, current_theme_id, errors, submitted):
    field = LOOK_FIELDS[COLOUR_USAGE_DEPARTURES]
    chosen = _submitted_or_current(submitted, field, current_theme_id)
    cards = _pairing_cards_html(
        field, pairing_id_for(chosen), pairing_id_for(current_theme_id),
        COLOUR_USAGE_DEPARTURES, layout_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING)
    return (
        '<div class="look-pairings" data-look-panel="%s">%s'
        '<div class="look-pick__grid" role="radiogroup" aria-label="%s">%s</div>%s</div>'
    ) % (
        COLOUR_USAGE_DEPARTURES, _help_html(PAIRING_HELP),
        escape_html(i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_DEPARTURES])), cards,
        _field_error_html(errors, field, field.replace("_", "-")))


def _arrivals_panel_html(layout_id, current_arriving, errors, submitted):
    field = LOOK_FIELDS[COLOUR_USAGE_ARRIVALS]
    chosen = _submitted_or_current(submitted, field, current_arriving)
    saved_follows = not current_arriving
    follows = not chosen
    cards = _pairing_cards_html(
        field, None if follows else pairing_id_for(chosen),
        None if saved_follows else pairing_id_for(current_arriving),
        COLOUR_USAGE_ARRIVALS, layout_id, theme_preview.FRAME_PREVIEW_STATE_ARRIVING)
    same = look.same_option_html(field, follows, i18n.t(SAME_AS_DEPARTURES_LABEL))
    return (
        '<div class="look-pairings" data-look-panel="%s">%s<div class="look-table__options">%s</div>'
        '<div class="look-pick__grid" role="radiogroup" aria-label="%s">%s</div>%s</div>'
    ) % (
        COLOUR_USAGE_ARRIVALS, _help_html(ARRIVING_NUDGE), same,
        escape_html(i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_ARRIVALS])), cards,
        _field_error_html(errors, field, field.replace("_", "-")))


def pairing_view_html(
        layout_id, current_theme_id, current_arriving, errors=None, submitted=None, usage=None):
    """What a look view holds for a frame on a giant-lettering layout: the
    pairing cards of the type `usage` names (departures or arrivals), or of
    both when `usage` is None. Only the shown type's field is posted."""
    parts = []
    if usage in (None, COLOUR_USAGE_DEPARTURES):
        parts.append(_departures_panel_html(layout_id, current_theme_id, errors, submitted))
    if usage in (None, COLOUR_USAGE_ARRIVALS):
        parts.append(_arrivals_panel_html(layout_id, current_arriving, errors, submitted))
    return '<div class="look-pairing-view">%s</div>' % "".join(parts)
