"""The Personalisation page's layout and pairing pickers.

Two pieces of markup, both native radios that belong to the settings form,
so they save with scripts blocked:

  * the Layout card above the style tabs: one radio card per screen layout a
    frame can show, each with a small picture of that layout;
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
from companion import ui_modal
from companion.layout import escape_html
import companion.layout as layout
from server import pairings, screen_layouts

from companion.settings import look
from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR, SELECTED_LABEL,
    SETTINGS_FORM_ID,
    _field_error_html, _submitted_or_current)
from companion.settings.theme import (
    COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_CALENDAR, COLOUR_USAGE_DEPARTURES,
    COLOUR_USAGE_RULES, FRAME_COLOURS_ROW_LABELS, LOOK_CHANGE_LABEL, LOOK_FIELDS, LOOK_PREVIEW_ALT_TEMPLATE, SAME_AS_DEPARTURES_LABEL, departures_safe_theme_id)

LAYOUT_FIELD = "layout"

LAYOUT_TITLE = i18n.msg("look.layout", "Layout")
LAYOUT_GROUP_LABEL = i18n.msg("look.layout_group", "Screen layout")
LAYOUT_HELP = i18n.msg(
    "look.layout_help",
    "The picture repaints at the next flight or transition.")
LAYOUT_CAPTION = i18n.msg("look.layout_caption", "Applies to the whole frame.")
LAYOUT_WHOLE_FRAME = i18n.msg("look.layout_whole_frame", "Whole frame")
LAYOUT_CHANGE_ARIA = i18n.msg("look.layout_change", "Change the layout")
LAYOUT_NAMES = {
    "classic": i18n.msg("look.layout_classic", "Classic"),
    "a": i18n.msg("look.layout_a", "A: nose and tail"),
    "b": i18n.msg("look.layout_b", "B: whole aircraft"),
    "c": i18n.msg("look.layout_c", "C: lettering on top, aircraft at the bottom"),
    "a_diagonal": i18n.msg("look.layout_a_diagonal", "A with diagonal band"),
}
LAYOUT_PREVIEW_ALT_TEMPLATE = i18n.msg("look.layout_preview_alt", "Layout preview: %s")

STYLE_LEAVE_DIALOG_ID = "style-leave"
STYLE_LEAVE_HOOK = "style-leave"
# The attribute the dialog lists the save's allowed return addresses in.
STYLE_LEAVE_RETURNS_ATTR = "style-leave-returns"
STYLE_LEAVE_TITLE = i18n.msg("look.style_leave_title", "Unsaved changes")
STYLE_LEAVE_TEXT = i18n.msg(
    "look.style_leave_text", "You have changes that are not saved. What do you want to do?")
STYLE_LEAVE_SAVE = i18n.msg("look.style_leave_save", "Save and continue")
STYLE_LEAVE_DISCARD = i18n.msg("look.style_leave_discard", "Discard")
STYLE_LEAVE_STAY = i18n.msg("look.style_leave_stay", "Stay here")

PAIRING_GROUP_LABEL = i18n.msg("look.pairing_group", "Colour")
PAIRING_HELP = i18n.msg(
    "look.pairing_help",
    "Pick the field colour. It repaints at the next flight or transition.")
ARRIVING_NUDGE = i18n.msg(
    "look.pairing_arriving_nudge",
    "Pick an arrivals colour, or landings look like take-offs.")
# The group label of each picker: the Departures, Arrivals and Calendar names,
# and "Look" for a special look.
USAGE_LABELS = dict(FRAME_COLOURS_ROW_LABELS)
USAGE_LABELS[COLOUR_USAGE_RULES] = i18n.msg("look.look", "Look")
PAIRING_NAMES = {
    "grey": i18n.msg("look.pairing_grey", "Grey"),
    "blue_light": i18n.msg("look.pairing_blue", "Light blue"),
    "red_light": i18n.msg("look.pairing_red", "Light red"),
    "yellow_light": i18n.msg("look.pairing_yellow", "Light yellow"),
    "white": i18n.msg("look.pairing_white", "White"),
}


def _radio_card_html(field, value, checked, saved, name, preview_src, alt, form_id=SETTINGS_FORM_ID):
    """One radio card: the small picture, the name and, on the selected one,
    a check. `saved` marks the value stored now, which keeps a quiet marker
    once another card is picked. `form_id` associates the radio with a form it
    is not nested in; `None` leaves it to its enclosing form."""
    badge = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if saved else "")
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_SMALL]
    return (
        '<label class="runway-card look-pick__card%s"%s>'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
        '<img class="look-pick__preview" src="%s" width="%d" height="%d" alt="%s" '
        'loading="lazy" decoding="async" fetchpriority="low">'
        '<span class="runway-card__number look-pick__name">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        " runway-card--selected" if saved else "", badge,
        escape_html(field), escape_html(value),
        ' form="%s"' % escape_html(form_id) if form_id else "",
        " checked" if checked else "",
        escape_html(preview_src), width, height, escape_html(alt),
        escape_html(name), layout.icon_html("icon-check"),
        escape_html(i18n.t(SELECTED_LABEL)))


def _help_html(message):
    return '<p class="text-label section-caption">%s</p>' % escape_html(i18n.t(message))


def layout_card_html(current_layout, current_theme_id, errors=None, submitted=None):
    """The frame-level Layout card shown above the style tabs of every
    Personalisation view. One set of radios serves both presentations: a row
    of thumbnails on a wide screen; on a phone a summary row (thumbnail, the
    current layout, a "Change" button) that reveals the same radios. A rejected
    submitted value never reaches the markup: the saved layout is shown
    instead."""
    saved = screen_layouts.normalise_layout_id(current_layout)
    chosen = _submitted_or_current(submitted, LAYOUT_FIELD, saved)
    if chosen not in screen_layouts.LAYOUT_IDS:
        chosen = saved
    picture_theme = departures_safe_theme_id(current_theme_id, None)

    def preview_src(layout_id):
        return theme_preview.frame_preview_src(
            picture_theme, theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
            theme_preview.FRAME_PREVIEW_SIZE_SMALL, layout=layout_id)

    cards = "".join(
        _radio_card_html(
            LAYOUT_FIELD, layout_id, layout_id == chosen, layout_id == saved,
            i18n.t(LAYOUT_NAMES[layout_id]), preview_src(layout_id),
            i18n.t(LAYOUT_PREVIEW_ALT_TEMPLATE) % i18n.t(LAYOUT_NAMES[layout_id]))
        for layout_id in screen_layouts.LAYOUT_IDS)
    title = escape_html(i18n.t(LAYOUT_TITLE))
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_SMALL]
    return (
        '<section class="layout-card" id="personalisation-layout" '
        'aria-labelledby="personalisation-layout-title" %s="%s" data-layout-card>'
        '<div class="layout-card__row">'
        '<img class="layout-card__thumb" src="%s" width="%d" height="%d" alt="" '
        'data-layout-thumb decoding="async">'
        '<div class="layout-card__text">'
        '<h2 class="text-heading layout-card__title" id="personalisation-layout-title">%s</h2>'
        '<p class="text-label section-caption layout-card__caption">%s</p>'
        '<p class="layout-card__meta"><span data-layout-name>%s</span> '
        '<span aria-hidden="true">&middot;</span> %s</p>'
        "</div>"
        '<button type="button" class="layout-card__change" data-layout-toggle '
        'aria-expanded="false" aria-controls="personalisation-layout-picker" '
        'aria-label="%s" hidden>%s</button>'
        "</div>"
        '<div class="layout-card__picker" id="personalisation-layout-picker" data-layout-picker>'
        '<div class="look-pick__grid layout-pick__grid" role="radiogroup" aria-label="%s">%s</div>'
        "%s%s</div></section>"
    ) % (
        DIRTY_SECTION_ATTR, title, escape_html(preview_src(chosen)), width, height,
        title, escape_html(i18n.t(LAYOUT_CAPTION)),
        escape_html(i18n.t(LAYOUT_NAMES[chosen])), escape_html(i18n.t(LAYOUT_WHOLE_FRAME)),
        escape_html(i18n.t(LAYOUT_CHANGE_ARIA)), escape_html(i18n.t(LOOK_CHANGE_LABEL)),
        escape_html(i18n.t(LAYOUT_GROUP_LABEL)), cards,
        _field_error_html(errors, LAYOUT_FIELD, LAYOUT_FIELD), _help_html(LAYOUT_HELP))


def style_leave_dialog_html(return_routes=()):
    """The closed dialog a script opens when the person leaves a Style page
    through an in-app link while any value on it differs from its stored one:
    save and continue, discard, or stay.

    `return_routes` are the addresses the server accepts as the save's return
    target, so the script only names one of those and a save that ends
    anywhere else simply stays on the page."""
    return ui_modal.choice_dialog_html(
        STYLE_LEAVE_DIALOG_ID, i18n.t(STYLE_LEAVE_TITLE), i18n.t(STYLE_LEAVE_TEXT),
        i18n.t(STYLE_LEAVE_SAVE), i18n.t(STYLE_LEAVE_DISCARD), i18n.t(STYLE_LEAVE_STAY),
        STYLE_LEAVE_HOOK, STYLE_LEAVE_RETURNS_ATTR, " ".join(return_routes))


def pairing_id_for(theme_id):
    """The pairing id a stored theme id is shown as. Pure: nothing stored
    changes."""
    return pairings.pairing_for_theme(theme_id).id


def frame_layout_id(device_cfg):
    """The screen layout a frame's stored configuration names; a missing or
    unknown value is the default layout."""
    return screen_layouts.normalise_layout_id((device_cfg or {}).get("layout"))


def offers_pairings(layout_id):
    """True when a frame on `layout_id` picks colours from the five pairings
    rather than the eighteen themes."""
    return layout_id is not None and screen_layouts.is_giant_layout(layout_id)


def preview_layout(layout_id):
    """The `layout` a preview URL carries: the giant layout's id, or None on
    the classic layout so its preview URLs stay as they always were."""
    return layout_id if offers_pairings(layout_id) else None


def look_label(theme_id, layout_id):
    """How a stored look is named in a list row: the mapped pairing's name on
    a giant layout (whatever theme is stored), the theme's own read-back
    otherwise."""
    if offers_pairings(layout_id):
        return i18n.t(PAIRING_NAMES[pairing_id_for(theme_id)])
    return look.look_sentence(theme_id)


def _pairing_cards_html(field, selected, saved, usage, layout_id, state, form_id=SETTINGS_FORM_ID):
    usage_label = i18n.t(USAGE_LABELS[usage])
    return "".join(
        _radio_card_html(
            field, pairing_id, pairing_id == selected, pairing_id == saved,
            i18n.t(PAIRING_NAMES[pairing_id]),
            theme_preview.frame_preview_src(
                pairing_id, state, theme_preview.FRAME_PREVIEW_SIZE_SMALL, layout=layout_id),
            i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, i18n.t(PAIRING_NAMES[pairing_id])),
            form_id)
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


def pairing_group_html(
        field, chosen_theme_id, saved_theme_id, usage, layout_id, state, form_id, errors,
        leading_html=""):
    """The five pairing cards for one posted field, as a radio group with
    `leading_html` (a "Same as departures" radio) above it and the field's
    error below. The stored theme ids are read as the pairings they map to; a
    falsy id selects no card. Used where a theme is picked outside the
    Departures and Arrivals views (a special look, the Calendar look)."""
    cards = _pairing_cards_html(
        field, pairing_id_for(chosen_theme_id) if chosen_theme_id else None,
        pairing_id_for(saved_theme_id) if saved_theme_id else None,
        usage, layout_id, state, form_id)
    lead = '<div class="look-table__options">%s</div>' % leading_html if leading_html else ""
    return (
        '<div class="look-pairings">%s<div class="look-pick__grid" role="radiogroup" '
        'aria-label="%s">%s</div>%s</div>'
    ) % (
        lead, escape_html(i18n.t(USAGE_LABELS[usage])), cards,
        _field_error_html(errors, field, field.replace("_", "-")))


def theme_group_html(field, chosen_theme_id, saved_theme_id, usage, state, form_id, errors):
    """One look card per theme the hardware can show, as a radio group posting
    `field`, for a frame on the classic layout where a look is a theme rather
    than a pairing. The same cards as the pairing group; a theme the hardware
    cannot show selects no card."""
    usage_label = i18n.t(USAGE_LABELS[usage])
    cards = "".join(
        _radio_card_html(
            field, theme_id, theme_id == chosen_theme_id, theme_id == saved_theme_id,
            look.look_sentence(theme_id),
            theme_preview.frame_preview_src(
                theme_id, state, theme_preview.FRAME_PREVIEW_SIZE_SMALL),
            i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, look.look_sentence(theme_id)),
            form_id)
        for theme_id in look.offered_theme_ids())
    return (
        '<div class="look-pairings"><div class="look-pick__grid" role="radiogroup" '
        'aria-label="%s">%s</div>%s</div>'
    ) % (escape_html(usage_label), cards,
         _field_error_html(errors, field, field.replace("_", "-")))


def calendar_look_html(layout_id, calendar_theme_id, errors=None, submitted=None):
    """The Calendar look's picker for a frame on a giant layout: "Same as
    departures" and the five pairing cards, all posting `calendar_theme_id`
    to the settings form."""
    field = LOOK_FIELDS[COLOUR_USAGE_CALENDAR]
    chosen = _submitted_or_current(submitted, field, calendar_theme_id)
    same = look.same_option_html(field, not chosen, i18n.t(SAME_AS_DEPARTURES_LABEL))
    return '%s%s' % (_help_html(PAIRING_HELP), pairing_group_html(
        field, chosen, calendar_theme_id, COLOUR_USAGE_CALENDAR, layout_id,
        theme_preview.FRAME_PREVIEW_STATE_DEPARTING, SETTINGS_FORM_ID, errors, same))
