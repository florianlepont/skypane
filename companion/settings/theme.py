"""The theme/palette settings group: palette swatches and chips, the
Aspect card's live preview, and the accordion-row plumbing
(`_usage_row_html`/`_usage_row_summary_html`) every one of the Aspect
card's four rows (departures, arrivals, calendar, rules) is built from.

`companion.settings.calendar` and `companion.settings.rules` both
import from this module (for the shared chip/row builders their own
usage rows need) rather than the reverse, so `_aspect_card_html()`
below takes their two rows' HTML already built, as plain string
parameters — the only way to give every settings-group module a single
direction of dependency with no import cycle between calendar/rules and
theme.
"""
from companion import i18n
from companion import theme_preview
from companion.layout import escape_html
import companion.layout as layout
from server import device_config, history_db, panel_format

from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR,
    SELECTED_LABEL, SETTINGS_FORM_ID, _field_error_html, _submitted_or_current)


THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
THEME_PREVIEW_ALT_TEMPLATE = theme_preview.THEME_PREVIEW_ALT_TEMPLATE

# The live preview's `<img>` width/height come from the render
# pipeline's real served dimensions, never a CSS aspect-ratio guess. It
# shares the chip grid's crop/size; only the rendered scene differs
# (the last real runway event instead of the fixed fixture).
THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT = theme_preview.THEME_PREVIEW_SIZE
THEME_LIVE_PREVIEW_ALT_TEMPLATE = i18n.msg(
    "display.live_preview_of_the_theme", "Live preview of the %s theme")
THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE = i18n.msg(
    "display.preview_with_your_last_flight", "Preview with your last flight: %s")
THEME_LIVE_PREVIEW_CAPTION_SAMPLE = i18n.msg(
    "display.preview_with_a_sample_flight", "Preview with a sample flight")

# server.device_config.theme_label()'s registry text, wrapped as a
# stable-id Message at this display site (companion/i18n_fr/registry.py
# still carries these eighteen names as a legacy English-keyed CATALOG —
# unconverted until a later plan finishes that module). Every other
# call site that reads a theme's display name (companion.settings.calendar,
# companion.settings.rules) goes through `_theme_label_message()` below
# rather than re-declaring these ids a second time.
_THEME_LABEL_MESSAGES = {
    "White": i18n.msg("registry.white", "White"),
    "Black": i18n.msg("registry.black", "Black"),
    "Grey": i18n.msg("registry.grey", "Grey"),
    "Yellow": i18n.msg("registry.yellow", "Yellow"),
    "Yellow Light": i18n.msg("registry.yellow_light", "Yellow Light"),
    "Red": i18n.msg("registry.red", "Red"),
    "Red Light": i18n.msg("registry.red_light", "Red Light"),
    "Green": i18n.msg("registry.green", "Green"),
    "Green Light": i18n.msg("registry.green_light", "Green Light"),
    "Blue": i18n.msg("registry.blue", "Blue"),
    "Blue Light": i18n.msg("registry.blue_light", "Blue Light"),
    "Band Blue": i18n.msg("registry.band_blue", "Band Blue"),
    "Band Blue Light": i18n.msg("registry.band_blue_light", "Band Blue Light"),
    "Band Green Light": i18n.msg("registry.band_green_light", "Band Green Light"),
    "Band Red": i18n.msg("registry.band_red", "Band Red"),
    "Band Black": i18n.msg("registry.band_black", "Band Black"),
    "Band Blue Field": i18n.msg("registry.band_blue_field", "Band Blue Field"),
    "Band Red Field": i18n.msg("registry.band_red_field", "Band Red Field"),
}


def _theme_label_message(theme_id):
    """`device_config.theme_label(theme_id)`'s registry text, already
    translated when this table knows it. Falls back to the raw label
    unchanged for a theme id this table does not (yet) know — never
    raises, and never calls i18n.t() on the raw fallback (it was never
    in any catalogue, so it is not a Message).
    """
    label = device_config.theme_label(theme_id)
    message = _THEME_LABEL_MESSAGES.get(label)
    return i18n.t(message) if message is not None else label

# "Aspect": the one merged card, a native `<details name="aspect-rows">`
# accordion over four rows. No radiogroup selects which row is showing
# — a grouped `<details>` set is mutually exclusive by construction,
# with zero script. The COLOUR_USAGE_* values below are a purely
# presentational label (a `data-usage` attribute and this card's own
# branch keys), never submitted to handle_post() — distinct from the
# three saved field names (theme/theme_arriving/calendar_theme_id)
# each row's own palette posts through via form="settings-form".
ASPECT_HEADING = i18n.msg("display.aspect", "Choose an appearance")
ASPECT_HEADING_ID = "aspect-heading"
COLOUR_USAGE_DEPARTURES = "departures"
COLOUR_USAGE_ARRIVALS = "arrivals"
COLOUR_USAGE_CALENDAR = "calendar"
COLOUR_USAGE_RULES = "rules"
# Locked order: every row-building loop below walks this exact tuple,
# so the row order and the no-JS floor's stacked-panel order can never
# drift apart.
COLOUR_USAGES = (
    COLOUR_USAGE_DEPARTURES, COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_CALENDAR,
    COLOUR_USAGE_RULES)
FRAME_COLOURS_ROW_LABELS = {
    COLOUR_USAGE_DEPARTURES: i18n.msg("display.departures", "Departures"),
    COLOUR_USAGE_ARRIVALS: i18n.msg("display.arrivals", "Arrivals"),
    COLOUR_USAGE_CALENDAR: i18n.msg("display.calendar_flights", "Calendar flights"),
    COLOUR_USAGE_RULES: i18n.msg(
        "display.per_flight_rules", "Optional per-flight rules"),
}

ASPECT_ROWS_GROUP_NAME = "aspect-rows"

ASPECT_ROW_SUMMARY_TEMPLATE = "%s — %s"

THEME_CHIP_SWATCH_LEGEND = i18n.msg("display.departures_arrivals", "Departures & arrivals")

# The leading "Same as departures" chip Arrivals'/Calendar's own grids
# gain, submitting the empty string (the clear signal handle_post()
# maps to device_config.CLEAR_THEME_ARRIVING/None) — reused verbatim as
# both the chip's own label and the row's own "no override" meta text.
SAME_AS_DEPARTURES_LABEL = i18n.msg("display.same_as_departures", "Same as departures")


def _palette_hex(index):
    """`#RRGGBB`, computed from `panel_format.PALETTE_RGB`'s flat int
    list at palette index `index` — never a hardcoded hex literal, so a
    future re-tuning of the physical panel ink automatically updates
    every swatch that calls this helper.
    """
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def _palette_swatch_html(theme_id, extra_class=""):
    """A CSS-drawn, non-photographic themed swatch: one outer
    `<span class="palette-swatch">` filled with
    `_palette_hex(departing_index)`, plus an optional child band span
    carrying `_palette_hex(band_index)`.

    A dithered field or band is what the panel prints as a stipple of
    its colour on white, so it gets a `--dithered` class (the stylesheet
    draws the stipple over the same fill) rather than looking identical
    to its solid sibling. A band is emitted whenever it differs from the
    field in colour or in dithering. Geometry is a stylesheet rule; only
    the colours compute here.
    """
    theme = device_config.THEMES[theme_id]
    hex_fill = _palette_hex(theme["departing_index"])
    paper = _palette_hex(panel_format.IDX_WHITE)
    css_class = "palette-swatch"
    if extra_class:
        css_class += " " + extra_class
    if theme.get("dithered"):
        css_class += " palette-swatch--dithered"
    band_html = ""
    band_dithered = bool(theme.get("band_dithered"))
    if "band_index" in theme and (
            theme["band_index"] != theme["departing_index"]
            or band_dithered != bool(theme.get("dithered"))):
        band_class = "palette-swatch__band"
        if band_dithered:
            band_class += " palette-swatch--dithered"
        band_html = '<span class="%s" style="background-color:%s;--swatch-paper:%s"></span>' % (
            band_class, escape_html(_palette_hex(theme["band_index"])), escape_html(paper))
    return (
        '<span class="%s" aria-hidden="true" '
        'style="background-color:%s;--swatch-paper:%s">%s</span>'
    ) % (escape_html(css_class), escape_html(hex_fill), escape_html(paper), band_html)


def _palette_chip_html(field_name, theme_id, selected, radio_form_id=None):
    """One palette entry: a `<label class="palette-chip">` wrapping a
    visually-hidden native radio, this theme's own
    `_palette_swatch_html()` (no `<img>`, no per-chip preview route
    call), and a caption.

    `data-preview-src` on the `<label>` must not be dropped:
    `theme-preview.js` resolves the live preview source off the
    changed radio input's `parentNode`; dropping it silently stops the
    live preview from following selection.

    No `--selected` server class or "Current" badge here: this chip's
    selected state is the live `:has(input:checked)` treatment, so a
    second, server-rendered signal would be redundant.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    escaped_id = escape_html(theme_id)
    label = _theme_label_message(theme_id)
    check_html = ""
    if selected:
        check_html = (
            '<span class="palette-chip__check">%s'
            '<span class="visually-hidden">%s</span></span>'
        ) % (layout.icon_html("icon-check"), escape_html(i18n.t(SELECTED_LABEL)))
    return (
        '<label class="palette-chip" data-preview-src="%s%s.png?live=1">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
        "%s"
        '<span class="palette-chip__name">%s</span>'
        "%s"
        "</label>"
    ) % (
        THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
        escape_html(field_name), escaped_id, form_attr_html,
        " checked" if selected else "",
        _palette_swatch_html(theme_id, extra_class="palette-chip__swatch"),
        escape_html(label),
        check_html,
    )


def _palette_grid_html(
        field_name, selected_theme_id, radio_form_id=None, leading_html="",
        labelled_by=""):
    """The wrapping palette grid: `<div class="palette" role=
    "radiogroup">`, looping `device_config.THEME_IDS` in registry
    order and interpolating `leading_html` before the chips, so a
    caller can prepend `_same_as_departures_chip_html()`'s output
    unchanged.

    No `id` attribute: this function has three call sites on one page,
    and an `id` emitted inside a multi-call renderer would either
    collide or go un-controlled by anything.
    """
    labelled_by_html = ' aria-labelledby="%s"' % escape_html(labelled_by) if labelled_by else ""
    chips = [
        _palette_chip_html(
            field_name, theme_id, theme_id == selected_theme_id,
            radio_form_id=radio_form_id)
        for theme_id in device_config.THEME_IDS
    ]
    return '<div class="palette" role="radiogroup"%s>%s%s</div>' % (
        labelled_by_html, leading_html, "".join(chips))


def _usage_row_summary_html(usage, theme_id, meta_text=None):
    """One Aspect accordion row's `<summary>`: the row's swatch, then a
    name span wrapping a nested meta span, "{row label} — {meta}". The
    em-dash join is computed once from `ASPECT_ROW_SUMMARY_TEMPLATE`,
    then sliced back into the meta span's own tail, so the dash has one
    source. `meta_text`, when omitted, defaults to the saved theme name.
    """
    if meta_text is None:
        meta_text = _theme_label_message(theme_id)
    row_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    escaped_row_label = escape_html(row_label)
    escaped_meta = escape_html(meta_text)
    joined = ASPECT_ROW_SUMMARY_TEMPLATE % (escaped_row_label, escaped_meta)
    meta_suffix_html = joined[len(escaped_row_label):]
    swatch_html = (
        _palette_swatch_html(theme_id, extra_class="usage-row__swatch")
        if theme_id is not None else ""
    )
    return (
        "<summary>%s"
        '<span class="usage-row__name">%s'
        '<span class="usage-row__meta">%s</span>'
        "</span>"
        "</summary>"
    ) % (swatch_html, escaped_row_label, meta_suffix_html)


def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None, leading_chip_html=""):
    """The one chip-grid renderer, called once per usage panel
    (departures, arrivals, calendar, rule-add). Call sites differ only
    in the radio group's `name`, the checked chip, the wrapper
    class/attribute, and an optional `leading_chip_html` fragment
    (typically "Same as departures", submitting an empty string).

    `chip_extra_class` shrinks every chip to compact geometry; the
    grid-level `extra_class` alone has no chip-shrinking rule.
    `radio_form_id`, when given, adds `form=` to every radio, so the
    grid posts through the settings form even rendered as its sibling.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    chips = []
    for theme_id in device_config.THEME_IDS:
        selected = theme_id == selected_theme_id
        checked = " checked" if selected else ""
        chip_class = "theme-chip"
        current_attr_html = ""
        if selected:
            chip_class += " theme-chip--selected"
            # Emitted only on the saved chip: only
            # `.theme-chip--selected:not(:has(input:checked))::after`
            # ever reads it.
            current_attr_html = ' %s="%s"' % (
                CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if chip_extra_class:
            chip_class += " " + chip_extra_class
        theme = device_config.THEMES[theme_id]
        # device_config.theme_label()'s registry text is translated at
        # this display site; the theme id itself never changes.
        label = _theme_label_message(theme_id)
        escaped_id = escape_html(theme_id)
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        chips.append(
            '<label class="%s" data-preview-src="%s%s.png?live=1"%s>'
            '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
            # background-color, not the background shorthand: the
            # shorthand resets background-image to none, and an inline
            # style beats every author rule, making style.css's
            # skeleton sheen for this band unreachable otherwise.
            '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
            'width="320" height="120" loading="lazy" style="background-color:%s">'
            '<span class="theme-chip__body">'
            '<span class="theme-chip__name">%s</span>'
            '<span class="theme-chip__swatches" aria-hidden="true">'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            "</span>"
            "</span>"
            '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                chip_class, THEME_PREVIEW_ROUTE_PREFIX, escaped_id, current_attr_html,
                escape_html(field_name), escaped_id, form_attr_html, checked,
                THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
                escape_html(i18n.t(THEME_PREVIEW_ALT_TEMPLATE) % label),
                escape_html(departing_hex),
                escape_html(label),
                escape_html(departing_hex), escape_html(arriving_hex),
                layout.icon_html("icon-check"),
                escape_html(i18n.t(SELECTED_LABEL)),
            )
        )
    grid_class = "theme-chip-grid"
    if extra_class:
        grid_class = grid_class + " " + extra_class
    attr_html = (" %s" % extra_attr) if extra_attr else ""
    # The swatch legend is one line under the grid and outside it, so
    # it is not a child of the element carrying role="radiogroup",
    # where a stray non-radio child would be announced inside the group.
    legend_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(THEME_CHIP_SWATCH_LEGEND))
    return '<div class="%s"%s>%s%s</div>%s' % (
        grid_class, attr_html, leading_chip_html, "".join(chips), legend_html)


def _theme_live_preview_html(current_theme_id, state_dir, extra_class=""):
    """The Aspect card's live preview figure. The `<img src>` is the
    saved theme's live preview route (`current_theme_id`,
    membership-tested against `device_config.THEMES`), the one eagerly-
    loaded image on this page. Without JavaScript it never changes;
    `theme-preview.js` swaps it on chip selection.

    The caption reads the most recent runway event's callsign, using
    the same connection helper `_rule_suggestion_chips_html()` uses,
    degrading to the sample-flight wording on any exception or a falsy
    `state_dir` — never raising, never a 500.
    """
    live_theme_id = (
        current_theme_id if current_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    label = _theme_label_message(live_theme_id)
    callsign = None
    if state_dir:
        try:
            with history_db.open_db(state_dir) as conn:
                rows = history_db.recent_runway_events(conn, limit=1)
            if rows:
                callsign = rows[0].get("callsign")
        except Exception:
            callsign = None
    if callsign:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE) % callsign
    else:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_SAMPLE)
    figure_class = "theme-live-preview"
    if extra_class:
        figure_class = figure_class + " " + extra_class
    return (
        '<figure class="%s">'
        '<img class="theme-live-preview__image" src="%s%s.png?live=1" '
        'width="%d" height="%d" loading="eager" alt="%s">'
        '<figcaption class="text-label">%s</figcaption>'
        "</figure>"
    ) % (
        figure_class,
        THEME_PREVIEW_ROUTE_PREFIX, escape_html(live_theme_id),
        THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT,
        escape_html(i18n.t(THEME_LIVE_PREVIEW_ALT_TEMPLATE) % label),
        escape_html(caption_text),
    )


def _same_as_departures_chip_html(field_name, checked, radio_form_id=None):
    """The leading, non-theme chip Arrivals'/Calendar's own rows
    prepend to their palette grid via `_palette_grid_html()`'s
    `leading_html` seam — submits the empty string for `field_name`
    (the clear signal), never a real theme id.

    No "Current" badge here: the live `:has(input:checked)` treatment
    on `.leading-option` is the one selected-state signal this control
    needs; a second, server-rendered one would be two sources of truth.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    return (
        '<label class="leading-option">'
        '<input type="radio" name="%s" value="" class="visually-hidden"%s%s>'
        '<span class="leading-option__name">%s</span>'
        '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        escape_html(field_name), form_attr_html, " checked" if checked else "",
        escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)),
        layout.icon_html("icon-check"), escape_html(i18n.t(SELECTED_LABEL)),
    )


def _usage_row_html(usage, summary_html, body_html, is_open=False, extra_class=""):
    """One Aspect accordion row. The row is a container only:
    `summary_html` and `body_html` arrive already built by the caller,
    so `_aspect_card_html()` can show all four rows' shapes side by
    side rather than hiding them inside branches here.

    Grouped `<details name="...">` is native, mutually-exclusive-by-
    construction accordion behaviour — zero script, zero server-side
    "which row is open" state beyond `is_open` (Departures ships
    `open`; the other three never do).
    """
    row_class = "usage-row"
    if extra_class:
        row_class = row_class + " " + extra_class
    return (
        '<details class="%s" name="%s" data-usage="%s"%s>'
        "%s%s"
        "</details>"
    ) % (
        escape_html(row_class), escape_html(ASPECT_ROWS_GROUP_NAME), escape_html(usage),
        " open" if is_open else "",
        summary_html, body_html,
    )


def departures_safe_theme_id(current_theme_id, submitted):
    """The safe (registered) departures theme id: the submitted-or-
    current theme when it is a real registry member, else
    `device_config.DEFAULT_THEME_ID`. `_aspect_card_html()`'s own
    departures/arrivals rows use this same resolution; the Calendar and
    Rules usage rows (built in `companion.settings.calendar`/`.rules`)
    need it too, for their "same as departures" swatch fallback, so it
    is exposed here rather than recomputed with different rounding.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    return (
        effective_theme_id if effective_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)


def _aspect_card_html(
        current_theme_id, current_theme_arriving,
        calendar_row_html, calendar_disconnect_form_html, rules_row_html,
        errors=None, submitted=None, state_dir=None):
    """"Aspect": the one tile with a native accordion, one live preview
    above four grouped `_usage_row_html()` rows in `COLOUR_USAGES`'
    locked order. `calendar_row_html`/`rules_row_html` arrive already
    built (`companion.settings.calendar`/`.rules` own that construction
    now, to keep this module independent of theirs — the two settings
    modules import this one instead, breaking what would otherwise be
    an import cycle since `_rule_add_form_html()` and `_rule_row_html()`
    both call back into this module's own chip/palette builders).
    `calendar_disconnect_form_html` is a data-only sibling of the whole
    card, appended after it, never nested inside the Calendar row.
    `errors`/`submitted`/`state_dir` repopulate the theme palettes on a
    rejected save. `departures_safe_id` keeps an unregistered theme id
    from ever reaching `device_config.THEMES[...]`.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    # The live preview is keyed off effective_theme_id (the same
    # repopulation value every palette grid below uses), not the bare
    # saved current_theme_id, so a rejected save's re-render shows the
    # submitted theme, not the stored one.
    live_preview_html = _theme_live_preview_html(
        effective_theme_id, state_dir, extra_class="aspect-card__preview")

    # An unregistered stored/submitted theme id never reaches
    # device_config.THEMES[...] — it resolves to DEFAULT_THEME_ID
    # before any swatch or label is computed. Also the fallback
    # swatch/label source for Arrivals' own "Same as departures" state.
    departures_safe_id = departures_safe_theme_id(current_theme_id, submitted)
    departures_row = _usage_row_html(
        COLOUR_USAGE_DEPARTURES,
        _usage_row_summary_html(COLOUR_USAGE_DEPARTURES, departures_safe_id),
        _palette_grid_html(
            "theme", effective_theme_id, radio_form_id=SETTINGS_FORM_ID,
            labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme", "theme"),
        is_open=True)

    effective_arriving = _submitted_or_current(
        submitted, "theme_arriving", current_theme_arriving)
    arrivals_same_checked = not effective_arriving
    arrivals_leading = _same_as_departures_chip_html(
        "theme_arriving", arrivals_same_checked, radio_form_id=SETTINGS_FORM_ID)
    # Carried verbatim from `_frame_colours_card_html()`: "Same as
    # departures" falls back to the DEPARTURES theme's own swatch/label
    # for this row's summary, never a blank/neutral placeholder — a
    # scripts-blocked reader closing this row still sees which colour
    # it actually resolves to.
    if arrivals_same_checked:
        arrivals_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        arrivals_swatch_id = departures_safe_id
    else:
        arrivals_safe_id = (
            effective_arriving if effective_arriving in device_config.THEMES
            else departures_safe_id)
        arrivals_meta = _theme_label_message(arrivals_safe_id)
        arrivals_swatch_id = arrivals_safe_id
    arrivals_row = _usage_row_html(
        COLOUR_USAGE_ARRIVALS,
        _usage_row_summary_html(
            COLOUR_USAGE_ARRIVALS, arrivals_swatch_id, meta_text=arrivals_meta),
        _palette_grid_html(
            "theme_arriving", effective_arriving, radio_form_id=SETTINGS_FORM_ID,
            leading_html=arrivals_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme_arriving", "theme-arriving"))

    rows_html = departures_row + arrivals_row + calendar_row_html + rules_row_html
    card_html = (
        '<div class="page-section aspect-card" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        "%s"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(ASPECT_HEADING)),
        escape_html(ASPECT_HEADING_ID), escape_html(i18n.t(ASPECT_HEADING)),
        live_preview_html,
        rows_html,
    )
    # The disconnect form is a data-only sibling of the whole
    # .aspect-card div, never nested inside it or the Calendar row.
    return card_html + calendar_disconnect_form_html
