"""The Display page's look card: two large live pictures of the frame
(departures and arrivals), the "Special looks" column built by
`companion.settings.calendar` and `companion.settings.rules`, and the
shared look sheet the picker script opens over a picture.

`calendar` and `rules` import the shared builders from this module
rather than the reverse, so `look_card_html()` takes their column's
HTML already built; every settings-group module then has a single
direction of dependency and no import cycle.

Every value a person can save is a native radio carrying a real theme
id (`companion.settings.look`'s colour x style table), so the card works
with scripts blocked; the picture-first picker is an enhancement.
"""
from companion import i18n
from companion import theme_preview, ui_components
from companion.layout import escape_html
import companion.layout as layout
from server import device_config

from companion.settings import look
from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR, SELECTED_LABEL, SETTINGS_FORM_ID,
    _field_error_html, _submitted_or_current)


THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
FRAME_PREVIEW_ROUTE_PREFIX = theme_preview.FRAME_PREVIEW_ROUTE_PREFIX

ASPECT_HEADING = i18n.msg("display.aspect", "How your frame looks")
ASPECT_HEADING_ID = "aspect-heading"

# The three looks a person sets on this card. The usage names are
# presentational (a data attribute and this module's own keys); the
# saved field names are the values of LOOK_FIELDS.
COLOUR_USAGE_DEPARTURES = "departures"
COLOUR_USAGE_ARRIVALS = "arrivals"
COLOUR_USAGE_CALENDAR = "calendar"
COLOUR_USAGE_RULES = "rules"
LOOK_FIELDS = {
    COLOUR_USAGE_DEPARTURES: "theme",
    COLOUR_USAGE_ARRIVALS: "theme_arriving",
    COLOUR_USAGE_CALENDAR: "calendar_theme_id",
}
FRAME_COLOURS_ROW_LABELS = {
    COLOUR_USAGE_DEPARTURES: i18n.msg("display.departures", "Departures"),
    COLOUR_USAGE_ARRIVALS: i18n.msg("display.arrivals", "Arrivals"),
    COLOUR_USAGE_CALENDAR: i18n.msg("display.calendar_flights", "Calendar flights"),
}
LOOK_SHEET_TITLES = {
    COLOUR_USAGE_DEPARTURES: i18n.msg("look.departures_look", "Departures look"),
    COLOUR_USAGE_ARRIVALS: i18n.msg("look.arrivals_look", "Arrivals look"),
    COLOUR_USAGE_CALENDAR: i18n.msg("look.calendar_flights_look", "Calendar flights look"),
}
LOOK_CHANGE_LABEL = i18n.msg("look.change", "Change")
LOOK_CHANGE_ARIA_TEMPLATE = i18n.msg("look.change_the_look", "Change the look: %s")
LOOK_PREVIEW_ALT_TEMPLATE = i18n.msg("look.preview_alt", "Preview: %s, %s")
LOOK_RESET_LABEL = i18n.msg("look.reset", "Reset")
LOOK_DONE_LABEL = i18n.msg("look.done", "Done")
LOOK_CLOSE_LABEL = i18n.msg("look.close", "Close")
LOOK_SAVE_LABEL = i18n.msg("look.save", "Save")
LOOK_FOLLOWS_NOTE = i18n.msg(
    "look.follows_departures_note",
    "This look follows the departures look. Switch it off to choose its own.")

# The "Same as departures" option Arrivals and Calendar flights carry,
# submitting the empty string: the clear signal handle_post() maps to
# device_config.CLEAR_THEME_ARRIVING / no calendar override.
SAME_AS_DEPARTURES_LABEL = i18n.msg("display.same_as_departures", "Same as departures")

LOOK_SHEET_ID = "look-sheet"
LOOK_SHEET_TITLE_ID = "look-sheet-title"
# Replaced by the picker script with a registry theme id, and with a
# look's read-back in an alt text; never text either can contain.
PREVIEW_THEME_TOKEN = "__THEME__"
PREVIEW_SENTENCE_TOKEN = "__LOOK__"


def departures_safe_theme_id(current_theme_id, submitted):
    """The submitted-or-current departures theme when it is a real
    registry member, else `device_config.DEFAULT_THEME_ID`. Arrivals and
    Calendar flights fall back to it for their "same as departures"
    picture, so it is resolved once and shared.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    return (
        effective_theme_id if effective_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)


def look_target_attrs(
        usage, field_name, state, size, follows_departures, title=None, departures_id=None,
        layout_id=None):
    """The data attributes the picker script reads off one look target:
    which radio group it owns, the preview URL pattern, and (for
    Arrivals/Calendar) that an empty value means "same as departures".
    `departures_id` is the departures theme, for a page that holds no
    departures look of its own for the script to follow. `layout_id` makes the
    preview URL pattern layout-aware.
    """
    template = theme_preview.frame_preview_src(PREVIEW_THEME_TOKEN, state, size, layout=layout_id)
    attrs = (
        ' data-look-target data-look-usage="%s" data-look-field="%s"'
        ' data-preview-src-template="%s"'
    ) % (escape_html(usage), escape_html(field_name), escape_html(template))
    if title is not None:
        attrs += ' data-look-title="%s"' % escape_html(title)
    if follows_departures:
        attrs += ' data-look-follows="%s" data-look-same-label="%s"' % (
            COLOUR_USAGE_DEPARTURES, escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)))
        if departures_id is not None:
            attrs += ' data-look-follows-theme="%s"' % escape_html(departures_id)
    return attrs


def look_edit_html(usage, table_html, icon_only=False):
    """The "Change" disclosure every look carries. Without scripts it
    opens the native radio table in place; with scripts its summary
    opens the look sheet instead. `icon_only` gives a list row a compact
    chevron; the word stays in the accessible name.
    """
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    if icon_only:
        summary_class = "look-edit__summary look-edit__summary--icon"
        inner_html = '%s<span class="visually-hidden">%s</span>' % (
            layout.icon_html("icon-chevron-right"), escape_html(i18n.t(LOOK_CHANGE_LABEL)))
    else:
        summary_class = "look-edit__summary"
        inner_html = "%s<span>%s</span>" % (
            layout.icon_html("icon-pencil"), escape_html(i18n.t(LOOK_CHANGE_LABEL)))
    return (
        '<details class="look-edit">'
        '<summary class="%s" data-look-open aria-label="%s">%s</summary>'
        '<div class="look-edit__body">%s</div>'
        "</details>"
    ) % (
        summary_class, escape_html(i18n.t(LOOK_CHANGE_ARIA_TEMPLATE) % usage_label),
        inner_html, table_html)


def _value_and_picture(effective_value, departures_id, allow_same):
    """`(same_checked, picture_theme_id)` for one usage: an empty or
    unknown value shows the departures look (Arrivals/Calendar) or the
    default theme (Departures), never an unregistered id.
    """
    if allow_same and not effective_value:
        return True, departures_id
    if effective_value in device_config.THEMES:
        return False, effective_value
    return False, departures_id if allow_same else device_config.DEFAULT_THEME_ID


_LAZY_ATTRS = ' loading="lazy" decoding="async" fetchpriority="low"'


def look_frame_html(usage, effective_value, departures_id, errors, state, carries_departures=False,
                    lazy=False):
    """One large framed picture with its caption and "Change" control.
    The picture is the live full-frame preview of the saved (or, after a
    rejected save, submitted) look. `carries_departures` is for a page with no
    departures look of its own: the target carries the departures theme the
    "Same as departures" choice follows. `lazy` is for the picture of a panel the
    page keeps hidden: it loads only when shown.
    """
    field_name = LOOK_FIELDS[usage]
    allow_same = usage != COLOUR_USAGE_DEPARTURES
    same_checked, picture_id = _value_and_picture(effective_value, departures_id, allow_same)
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    sentence = i18n.t(SAME_AS_DEPARTURES_LABEL) if same_checked else look.look_sentence(picture_id)
    preview = lambda theme_id: theme_preview.frame_preview_src(  # noqa: E731
        theme_id, state, theme_preview.FRAME_PREVIEW_SIZE_LARGE)
    leading = (
        look.same_option_html(field_name, same_checked, i18n.t(SAME_AS_DEPARTURES_LABEL))
        if allow_same else "")
    table_html = look.look_table_html(
        field_name, "" if same_checked else effective_value, usage_label, preview,
        leading_html=leading)
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_LARGE]
    return (
        '<div class="look-frame"%s>'
        '<div class="look-frame__anchor" data-look-anchor>'
        '<div class="look-frame__picture">'
        '<img class="look-frame__image" data-look-image src="%s" width="%d" height="%d" '
        'alt="%s" data-look-alt-template="%s"%s>'
        '<button type="button" class="look-frame__open" data-look-open hidden '
        'aria-haspopup="dialog" aria-label="%s"></button>'
        "</div></div>"
        '<div class="look-frame__meta">%s</div>%s'
        "</div>"
    ) % (
        look_target_attrs(
            usage, field_name, state, theme_preview.FRAME_PREVIEW_SIZE_LARGE, allow_same,
            title=i18n.t(LOOK_SHEET_TITLES[usage]),
            departures_id=departures_id if carries_departures else None),
        escape_html(preview(picture_id)), width, height,
        escape_html(i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, sentence)),
        escape_html(i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, PREVIEW_SENTENCE_TOKEN)),
        _LAZY_ATTRS if lazy else "",
        escape_html(i18n.t(LOOK_CHANGE_ARIA_TEMPLATE) % usage_label),
        look_edit_html(usage, table_html),
        _field_error_html(errors, field_name, field_name.replace("_", "-")),
    )


def look_sheet_html(inline=False):
    """The one look sheet the script moves next to whichever picture
    opened it (a bottom sheet on phones). `hidden` until a script shows
    it, so a scripts-blocked page never renders an inert dialog. Its
    radios belong to no form and are never submitted: the script copies
    each choice into the opened look's own theme radio.

    `inline` is the Look page's picker: the same three choices sitting in
    the page (no dialog, no title, no Done, no buttons of its own: saving
    and cancelling belong to the page's save bar). Its wrapper is
    script-only: without a script the page offers the native radio tables
    instead.
    """
    inline_attrs = " data-look-inline" if inline else " hidden"
    role = "" if inline else ' role="dialog" aria-modal="true" aria-labelledby="%s"' % LOOK_SHEET_TITLE_ID
    foot = "" if inline else (
        '<div class="look-sheet__foot">'
        '<button type="button" class="look-sheet__reset" data-look-reset>%s</button>'
        '<button type="button" class="look-sheet__done" data-look-done>%s</button>'
        "</div>" % (escape_html(i18n.t(LOOK_RESET_LABEL)), escape_html(i18n.t(LOOK_DONE_LABEL))))
    return (
        '<div class="look-scrim" data-look-scrim hidden></div>'
        '<div class="look-sheet" id="%s"%s data-look-sheet data-look-model="%s"%s>'
        '<div class="look-sheet__head"%s>'
        '<h3 class="look-sheet__title" id="%s" data-look-sheet-title></h3>'
        '<button type="button" class="look-sheet__close" data-look-close aria-label="%s">%s</button>'
        "</div>"
        '<div class="look-sheet__same" data-look-same-row hidden>'
        '<span id="look-same-label">%s</span>'
        "%s</div>"
        '<p class="look-sheet__same-note text-label" data-look-same-note hidden>%s</p>'
        "%s%s"
        "</div>"
    ) % (
        LOOK_SHEET_ID, role, escape_html(look.look_model_json()), inline_attrs,
        " hidden" if inline else "",
        LOOK_SHEET_TITLE_ID,
        escape_html(i18n.t(LOOK_CLOSE_LABEL)), layout.icon_html("icon-close"),
        escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)),
        ui_components.switch_button_html(
            False, ' aria-labelledby="look-same-label" data-look-same', "button"),
        escape_html(i18n.t(LOOK_FOLLOWS_NOTE)),
        look.axes_html("look"), foot,
    )


def look_card_html(
        current_theme_id, current_theme_arriving, special_looks_html, after_card_html,
        errors=None, submitted=None):
    """The whole look card: heading, the Departures and Arrivals
    pictures, the Special looks column (already built) and the shared
    look sheet. `after_card_html` (the
    calendar disconnect form) is a sibling appended after the card,
    never nested in it.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    departures_id = departures_safe_theme_id(current_theme_id, submitted)
    effective_arriving = _submitted_or_current(submitted, "theme_arriving", current_theme_arriving)
    departures_html = look_frame_html(
        COLOUR_USAGE_DEPARTURES, effective_theme_id, departures_id, errors,
        theme_preview.FRAME_PREVIEW_STATE_DEPARTING)
    arrivals_html = look_frame_html(
        COLOUR_USAGE_ARRIVALS, effective_arriving, departures_id, errors,
        theme_preview.FRAME_PREVIEW_STATE_ARRIVING)
    card_html = (
        '<div class="page-section aspect-card look-card" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<div class="look-card__grid">%s%s%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(ASPECT_HEADING)),
        escape_html(ASPECT_HEADING_ID), escape_html(i18n.t(ASPECT_HEADING)),
        departures_html, arrivals_html, special_looks_html,
        look_sheet_html(),
    )
    return card_html + after_card_html



LOOK_GROUP_LABEL = i18n.msg("look.look", "Look")


def look_radio_card_html(theme_id, checked, saved, usage_label):
    """One look as a radio card: the look's small live picture, its name and,
    on the selected one, a check. The radio belongs to the settings form and
    posts the same theme id the look sheet writes. `saved` marks the look
    stored now, which keeps a quiet marker once another card is picked."""
    sentence = look.look_sentence(theme_id)
    preview = theme_preview.frame_preview_src(
        theme_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
        theme_preview.FRAME_PREVIEW_SIZE_SMALL)
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_SMALL]
    # The big picture this look shows once selected.
    picture = theme_preview.frame_preview_src(
        theme_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
        theme_preview.FRAME_PREVIEW_SIZE_LARGE)
    badge = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if saved else "")
    # The small picture is for a page without a script: with one, the inline
    # picker replaces these cards and they are never shown, so it must not be
    # fetched (27 of them are fetched otherwise).
    return (
        '<label class="runway-card look-pick__card%s"%s data-preview-src="%s">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden" form="%s"%s>'
        '<noscript><img class="look-pick__preview" src="%s" width="%d" height="%d" alt="%s" '
        'loading="lazy" decoding="async" fetchpriority="low"></noscript>'
        '<span class="runway-card__number look-pick__name">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        " runway-card--selected" if saved else "", badge, escape_html(picture),
        escape_html(LOOK_FIELDS[COLOUR_USAGE_DEPARTURES]), escape_html(theme_id),
        escape_html(SETTINGS_FORM_ID), " checked" if checked else "",
        escape_html(preview), width, height,
        escape_html(i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, sentence)),
        escape_html(sentence), layout.icon_html("icon-check"),
        escape_html(i18n.t(SELECTED_LABEL)))


def look_radio_cards_html(effective_id, saved_id, usage_label):
    """The grid of radio cards, one per look the frame's hardware can show,
    in registry order."""
    cards = "".join(
        look_radio_card_html(theme_id, theme_id == effective_id, theme_id == saved_id, usage_label)
        for theme_id in look.offered_theme_ids())
    return '<div class="look-pick__grid" role="radiogroup" aria-label="%s">%s</div>' % (
        escape_html(i18n.t(LOOK_GROUP_LABEL)), cards)


def look_pick_html(current_theme_id, submitted, errors, lazy=False):
    """The Look card's main block: the large live picture of the departures
    look and the radio cards that choose it (the inline picker replaces them
    when a script runs). Everything sits in one look target, so the look sheet and
    the live picture follow a card exactly as they follow the sheet."""
    departures_id = departures_safe_theme_id(current_theme_id, submitted)
    effective_id = _submitted_or_current(submitted, "theme", current_theme_id)
    state = theme_preview.FRAME_PREVIEW_STATE_DEPARTING
    size = theme_preview.FRAME_PREVIEW_SIZE_LARGE
    field_name = LOOK_FIELDS[COLOUR_USAGE_DEPARTURES]
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_DEPARTURES])
    sentence = look.look_sentence(departures_id)
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size]
    return (
        '<div class="look-frame look-pick"%s>'
        '<div class="look-frame__anchor" data-look-anchor>'
        '<div class="look-frame__picture">'
        '<img class="look-frame__image" data-look-image src="%s" width="%d" height="%d" '
        'alt="%s" data-look-alt-template="%s"%s>'
        '<button type="button" class="look-frame__open" data-look-open hidden '
        'aria-haspopup="dialog" aria-label="%s"></button>'
        "</div></div>"
        "%s%s"
        "</div>"
    ) % (
        look_target_attrs(
            COLOUR_USAGE_DEPARTURES, field_name, state, size, False,
            title=i18n.t(LOOK_SHEET_TITLES[COLOUR_USAGE_DEPARTURES])),
        escape_html(theme_preview.frame_preview_src(departures_id, state, size)), width, height,
        escape_html(i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, sentence)),
        escape_html(i18n.t(LOOK_PREVIEW_ALT_TEMPLATE) % (usage_label, PREVIEW_SENTENCE_TOKEN)),
        _LAZY_ATTRS if lazy else "",
        escape_html(i18n.t(LOOK_CHANGE_ARIA_TEMPLATE) % usage_label),
        look_radio_cards_html(
            effective_id if effective_id in device_config.THEMES else None,
            current_theme_id, usage_label),
        _field_error_html(errors, field_name, field_name.replace("_", "-")))


def look_card_body_html(
        current_theme_id, current_theme_arriving, errors=None, submitted=None, usage=None):
    """What a look view holds. With a script: the live picture of the chosen
    type and the inline picker (colour, background, diagonal band, Reset,
    Save). Without one: the picture and native radio table of the chosen
    type, exactly as before. `usage` (departures or arrivals) names the type
    shown; None shows both. The other type's picture and radios stay in the
    markup, hidden, so the form posts the same fields and the picker can
    resolve "Same as departures".
    """
    departures_id = departures_safe_theme_id(current_theme_id, submitted)
    effective_arriving = _submitted_or_current(submitted, "theme_arriving", current_theme_arriving)
    hidden = {name: " hidden" if usage not in (None, name) else ""
              for name in (COLOUR_USAGE_DEPARTURES, COLOUR_USAGE_ARRIVALS)}
    # The panel the page keeps hidden loads its picture only when shown.
    arrivals_html = look_frame_html(
        COLOUR_USAGE_ARRIVALS, effective_arriving, departures_id, errors,
        theme_preview.FRAME_PREVIEW_STATE_ARRIVING,
        lazy=bool(hidden[COLOUR_USAGE_ARRIVALS]))
    return (
        '<div class="look-view" data-look-initial="%s">'
        '<div class="look-stage">'
        '<div class="look-panel" data-look-panel="%s"%s>%s</div>'
        '<div class="look-panel look-pick__arrivals" data-look-panel="%s"%s>%s</div>'
        "</div>"
        '<div class="look-picker js-gate">%s</div>'
        "</div>"
    ) % (
        usage or COLOUR_USAGE_DEPARTURES,
        COLOUR_USAGE_DEPARTURES, hidden[COLOUR_USAGE_DEPARTURES],
        look_pick_html(
            current_theme_id, submitted, errors, lazy=bool(hidden[COLOUR_USAGE_DEPARTURES])),
        COLOUR_USAGE_ARRIVALS, hidden[COLOUR_USAGE_ARRIVALS], arrivals_html,
        look_sheet_html(inline=True))
