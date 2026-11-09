"""The colour-rules settings group: the per-flight rules shown as the
Special looks list (rows with Edit and Remove, and the Add link) and the page
that creates or edits one rule (kind, key, the look, recent suggestions).
Built here so `companion.settings.theme` stays independent of this module —
see that module's own docstring for why.
"""
import hashlib
from urllib.parse import urlencode

from companion import device_scope, i18n
from companion import theme_preview
import companion.layout as layout
from companion import ui_components
from companion import ui_modal, ui_segmented
from companion.layout import csrf_field, escape_html
from server import device_config, history_db
from server.plane import colour_rules, enrich, name_overrides

from companion.settings import look
from companion.settings.calendar import special_mini_html
from companion.settings.form import (
    _field_error_attrs, _field_error_html, _submitted_or_current)
from companion.settings.theme import (
    COLOUR_USAGE_RULES, LOOK_SAVE_LABEL, look_target_attrs)


# The per-flight colour-rules editor's routes. Add and delete are
# immediate POSTs on their own routes, outside SETTINGS_ROUTE and the
# settings form's dirty bar — a rule is a one-step immediate act, not a
# pending edit.
RULES_ADD_ROUTE = "/settings/rules/add"
RULES_DELETE_ROUTE_PREFIX = "/settings/rules/"
RULES_DELETE_ROUTE_SUFFIX = "/delete"


SPECIAL_LOOKS_HEADING = i18n.msg("look.special_looks", "Special looks")
RULES_SECTION_CAPTION = i18n.msg(
    "look.override_the_look_for_one_airline_flight_or_aircraft",
    "A different look for one airline, flight or plane.")
SPECIAL_LOOKS_ORDER = i18n.msg(
    "look.most_specific_wins",
    "Most specific wins: calendar, then flight, aircraft, airline.")
NEW_SPECIAL_LOOK_HEADING = i18n.msg("look.new_special_look", "New special look")
EDIT_SPECIAL_LOOK_HEADING = i18n.msg("look.edit_special_look", "Edit special look")
ADD_SPECIAL_LOOK_LABEL = NEW_SPECIAL_LOOK_HEADING
RULE_CREATE_BUTTON_TEXT = i18n.msg("look.create_look", "Create look")
RULE_EDIT_BUTTON_TEXT = i18n.msg("rules.edit", "Edit")
RULE_EDIT_ARIA = i18n.msg("rules.edit_rule_aria", "Edit the special look for %s")
SPECIAL_LOOKS_BACK_LABEL = SPECIAL_LOOKS_HEADING
SPECIAL_LOOKS_EMPTY_HEADING = i18n.msg(
    "display.special_looks_none", "No special looks yet.")
RULE_PREVIEW_TEXT = i18n.msg(
    "look.matching_flights_will_look_like_this",
    "Matching flights will look like this.")
RULE_LOOK_LABEL = i18n.msg("look.look", "Look")
# Owned by companion/i18n_fr/display.py, not this module's own
# rules.py catalogue — shared segmented-control copy that predates the
# per-flight rules feature.
RULE_KIND_FIELD_LABEL = i18n.msg("display.match_by", "Applies to")
RULE_VALUE_FIELD_LABEL = i18n.msg("display.value", "Value")
RULE_CANCEL_TEXT = i18n.msg("display.cancel", "Cancel")
# The plain-language segment labels, used by both the add form's
# segment text and the rule-row kind badge, so the two can never
# disagree.
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: i18n.msg("rules.flight", "Flight"),
    colour_rules.RULE_KIND_HEX: i18n.msg("rules.aircraft", "Aircraft"),
    colour_rules.RULE_KIND_PREFIX: i18n.msg("rules.airline", "Airline"),
}


def _rule_kind_label_text(kind):
    """RULE_KIND_LABELS[kind], translated; an unrecognised kind (a
    stale/foreign value on an old row) degrades to the raw kind
    unchanged rather than raising — never passed to i18n.t(), which
    only accepts a Message."""
    message = RULE_KIND_LABELS.get(kind)
    return i18n.t(message) if message is not None else kind
# A separate mapping from RULE_KIND_LABELS above, read only for each
# segment's own title attribute, never shown as the visible label text.
# Owned by display.py, like RULE_KIND_FIELD_LABEL above.
RULE_KIND_TITLES = {
    colour_rules.RULE_KIND_CALLSIGN: i18n.msg("display.callsign", "Callsign"),
    colour_rules.RULE_KIND_HEX: i18n.msg("display.icao24_hex", "ICAO24 hex"),
    colour_rules.RULE_KIND_PREFIX: i18n.msg("display.callsign_prefix", "Callsign prefix"),
}
RULE_VALUE_PLACEHOLDER = "AFR1234"
RULE_REMOVE_BUTTON_TEXT = i18n.msg("rules.remove", "Remove")
# The suggestion chips' own label prefix; the joined callsign list
# itself is data, never translated.
RULE_SUGGESTIONS_LABEL = i18n.msg("rules.recent", "Recent:")
# aria-labelledby targets for the two radiogroups the add form carries.
RULE_FORM_ID = "special-look-form"
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
RULE_REMOVE_DIALOG_TITLE = i18n.msg(
    "rules.remove_this_special_look", "Remove this special look?")
RULE_REMOVE_DIALOG_BODY = i18n.msg(
    "rules.remove_special_look_body",
    "%s goes back to your normal look. You can add the special look again at any time.")
RULE_REMOVE_SUBMIT_TEXT = i18n.msg("rules.remove_special_look", "Remove special look")
RULE_REMOVE_DISMISS_TEXT = i18n.msg("rules.keep_special_look", "Keep special look")
RULE_REMOVE_ARIA = i18n.msg("rules.remove_rule_aria", "Remove the special look for %s")
SPECIAL_LOOKS_ANCHOR = "personalisation-special-looks"
# Recent suggestions offered per kind, newest first.
RULE_SUGGESTIONS_PER_KIND = 5


# The per-flight colour-rules editor: an add form (its own immediate
# POST route) plus an always-present list with a plain per-row Delete
# button (its own immediate POST route).


def _rule_delete_action(kind, value):
    """The delete form's `action` for `(kind, value)`:
    `/settings/rules/{kind}/{value}/delete` — both segments are already
    normalised, allowlisted uppercase alphanumerics by the time a row
    reaches here, so `escape_html()` is the only encoding needed. One
    builder for both the desktop and mobile row renderers, so they can
    never diverge into building two different strings for the same row.
    """
    return escape_html(device_scope.scoped("%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, kind, value, RULES_DELETE_ROUTE_SUFFIX), "POST"))


def _rule_kind_segment_html(selected_kind, errors):
    """The "Applies to" segmented control: native radios styled as one
    control, labelled by its visible heading. The plain-language word is the
    visible label text, and the technical term is the label's own `title`
    attribute, so a hovering mouse user still finds the exact vocabulary
    without it cluttering the visible label."""
    options = [
        ("rule-kind-%s" % kind, "rule_kind", kind, i18n.t(RULE_KIND_LABELS[kind]),
         i18n.t(RULE_KIND_TITLES[kind]), kind == selected_kind)
        for kind in colour_rules.RULE_KINDS]
    return (
        '<p class="look-axis__label" id="%s">%s</p>'
        '<div class="rule-add-form__field rule-add-form__field--kind" role="radiogroup" '
        'aria-labelledby="%s">%s%s</div>'
    ) % (
        escape_html(RULE_KIND_HEADING_ID), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        escape_html(RULE_KIND_HEADING_ID), ui_segmented.segmented_radios_html(options),
        _field_error_html(errors, "rule_kind", "rule-kind"))


def _rule_value_field_html(submitted_value, errors):
    return (
        '<div class="rule-add-form__field">'
        '<label for="rule-key" class="visually-hidden">%s</label>'
        '<input type="text" id="rule-key" name="rule_key" maxlength="8" '
        'required autocomplete="off" spellcheck="false" placeholder="%s" value="%s"%s>'
        "%s</div>"
    ) % (
        escape_html(i18n.t(RULE_VALUE_FIELD_LABEL)),
        escape_html(RULE_VALUE_PLACEHOLDER), escape_html(submitted_value),
        _field_error_attrs(errors, "rule_key", "rule-key"),
        _field_error_html(errors, "rule_key", "rule-key"))


def _rule_for(registry, kind, value):
    """The theme id stored for (kind, value), or None."""
    for row_kind, row_value, theme_id, _created_at in colour_rules.rule_rows(registry):
        if (row_kind, row_value) == (kind, value):
            return theme_id
    return None


def _rule_fixed_key_html(kind, value):
    """The key an edit keeps: shown as text and posted as hidden fields, so
    saving replaces that rule and cannot make another."""
    return (
        '<input type="hidden" name="rule_kind" value="%s">'
        '<input type="hidden" name="rule_key" value="%s">'
        '<div class="form-page__section"><p class="form-page__label">%s</p>'
        '<p class="form-page__fixed"><span class="special-row__tag">%s</span> '
        '<span class="mono">%s</span></p></div>'
    ) % (
        escape_html(kind), escape_html(value), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        escape_html(_rule_kind_label_text(kind)), escape_html(value))


def rule_form_html(ctx, edit=None, errors=None, submitted=None):
    """The page that creates or edits one rule: the picture on the left, the
    options on the right, one `<form>` posting to `RULES_ADD_ROUTE` with the
    unchanged `rule_kind`/`rule_key`/`rule_theme_id` fields (the route replaces
    a rule that already exists). `edit` is (kind, key, theme_id) of the rule
    being edited, or None for a new one. Its look is the same colour x style
    table of native radios the pictures use (scripts swap in the three-choice
    picker over it); the picture follows the choice.

    Validation errors render under each field, keeping the typed value.
    Returns (form markup, title, submit label).
    """
    if edit is not None:
        selected_kind, submitted_value, selected_theme_id = edit
        title, submit_text = EDIT_SPECIAL_LOOK_HEADING, LOOK_SAVE_LABEL
        who_html = _rule_fixed_key_html(selected_kind, submitted_value)
    else:
        selected_kind = _submitted_or_current(
            submitted, "rule_kind", colour_rules.RULE_KIND_CALLSIGN)
        submitted_value = submitted.get("rule_key", "") if submitted is not None else ""
        selected_theme_id = _submitted_or_current(
            submitted, "rule_theme_id", device_config.THEME_IDS[0])
        title, submit_text = NEW_SPECIAL_LOOK_HEADING, RULE_CREATE_BUTTON_TEXT
        who_html = '<div class="form-page__section">%s%s%s</div>' % (
            _rule_kind_segment_html(selected_kind, errors),
            _rule_value_field_html(submitted_value, errors),
            _rule_suggestion_chips_html(ctx.state_dir))
    picture_id = (
        selected_theme_id if selected_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    state = theme_preview.FRAME_PREVIEW_STATE_DEPARTING
    small = theme_preview.FRAME_PREVIEW_SIZE_SMALL
    large = theme_preview.FRAME_PREVIEW_SIZE_LARGE
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[large]
    table_html = look.look_table_html(
        "rule_theme_id", selected_theme_id, i18n.t(title),
        lambda theme_id: theme_preview.frame_preview_src(theme_id, state, small),
        form_id=None)
    form_html = (
        '<form method="post" action="%s" id="%s" class="form-page rule-add-form" '
        'data-special-form%s>'
        '<div class="form-page__preview"><div class="look-frame__anchor">'
        '<div class="look-frame__picture"><img class="look-frame__image" data-look-image '
        'src="%s" width="%d" height="%d" alt=""></div></div>'
        '<p class="form-page__caption"><span class="form-page__name">%s</span>'
        '<span class="form-page__sentence">%s</span></p></div>'
        '<div class="form-page__card">%s'
        '<div class="form-page__section">'
        '<p class="look-axis__label" id="%s">%s</p>'
        '<div data-look-axes-host hidden>%s</div>'
        '<div data-look-table-host>%s</div>%s</div></div>'
        "</form>"
    ) % (
        escape_html(device_scope.scoped(RULES_ADD_ROUTE, "POST")), RULE_FORM_ID,
        look_target_attrs(COLOUR_USAGE_RULES, "rule_theme_id", state, large, False),
        escape_html(theme_preview.frame_preview_src(picture_id, state, large)), width, height,
        escape_html(i18n.t(title)), escape_html(i18n.t(RULE_PREVIEW_TEXT)),
        who_html,
        escape_html(RULE_THEME_HEADING_ID), escape_html(i18n.t(RULE_LOOK_LABEL)),
        look.axes_html("rule_look"),
        table_html,
        _field_error_html(errors, "rule_theme_id", "rule-theme"),
    )
    return form_html, i18n.t(title), i18n.t(submit_text)


def edit_target(ctx):
    """(kind, key, theme_id) of the rule the request names (`ctx.rule_edit`),
    or None when it names nothing that exists."""
    named = ctx.rule_edit
    registry = ctx.colour_rules
    if not named or not isinstance(registry, dict):
        return None
    theme_id = _rule_for(registry, named[0], named[1])
    return (named[0], named[1], theme_id) if theme_id else None


def edit_href(kind, value):
    """The address of the page that edits one rule."""
    return device_scope.scoped(
        "%s?%s" % (layout.DISPLAY_SPECIAL_LOOK_EDIT_ROUTE,
                   urlencode((("rule_kind", kind), ("rule_key", value)))))


def _recent_rule_keys(rows):
    """Up to `RULE_SUGGESTIONS_PER_KIND` distinct recent keys per rule
    kind, as `{kind: [(value, label), ...]}`: callsigns, aircraft hex
    codes, and airline prefixes labelled with the airline's name when
    the built-in table knows it. Every value is re-normalised by the
    rule normaliser, so only a key the add route would accept is offered.
    """
    keys = {kind: [] for kind in colour_rules.RULE_KINDS}
    for row in rows:
        callsign = row.get("callsign")
        candidates = (
            (colour_rules.RULE_KIND_CALLSIGN, callsign, None),
            (colour_rules.RULE_KIND_HEX, row.get("hex"), None),
            (colour_rules.RULE_KIND_PREFIX, (callsign or "")[:3], row.get("airline")),
        )
        for kind, raw, airline in candidates:
            value = colour_rules.normalise_rule_value(kind, raw)
            if not value or len(keys[kind]) >= RULE_SUGGESTIONS_PER_KIND:
                continue
            if value in [existing for existing, _label in keys[kind]]:
                continue
            name = airline or enrich.static_airline_name_for_prefix(value)
            label = "%s · %s" % (value, name) if kind == colour_rules.RULE_KIND_PREFIX and name else value
            keys[kind].append((value, label))
    return keys


def _rule_suggestion_chips_html(state_dir):
    """Recent keys as suggestion chips, one group per rule kind, from
    `history_db.recent_runway_events()`. The chips only fill in the form,
    so the whole block ships `hidden` and the script reveals the group
    matching the selected kind; without scripts nothing inert shows.

    Returns "" when there are no recent events, or on any read failure
    — never raises.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(
                conn, limit=50,
                airline_names=name_overrides.names_by_prefix(
                    name_overrides.load_name_overrides(state_dir)))
    except Exception:
        return ""
    keys = _recent_rule_keys(rows)
    if not any(keys.values()):
        return ""
    groups = "".join(
        '<div class="rule-suggestions__group" data-kind="%s">%s</div>' % (
            escape_html(kind), "".join(
                '<button type="button" class="rule-suggestion-chip" data-kind="%s" '
                'data-value="%s">%s</button>' % (
                    escape_html(kind), escape_html(value), escape_html(label))
                for value, label in keys[kind]))
        for kind in colour_rules.RULE_KINDS if keys[kind])
    return '<div class="rule-suggestions" data-rule-suggestions hidden><p class="text-label">%s</p>%s</div>' % (
        escape_html(i18n.t(RULE_SUGGESTIONS_LABEL)), groups)


def _rule_title_html(kind, value):
    """A rule's key, led by the airline's name for an airline rule when
    the built-in table knows it ("Transavia TVF")."""
    name = enrich.static_airline_name_for_prefix(value) if kind == colour_rules.RULE_KIND_PREFIX else None
    key_html = '<span class="rule-row__key mono">%s</span>' % escape_html(value)
    return "%s %s" % (escape_html(name), key_html) if name else key_html


def _rule_remove_dialog_id(kind, value):
    """The remove dialog's id: a lowercase slug of the kind and a short hash of
    the value, so no stored text ever reaches an id or a fragment."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return ui_modal.validated_slug("remove-look-%s-%s" % (kind, digest))


def _rule_remove_html(kind, value):
    """The row's Remove link and its confirm dialog. The dialog posts to the
    delete route with the page's token; its dismiss control is the safe
    default and takes the initial focus."""
    dialog_id = _rule_remove_dialog_id(kind, value)
    subject = "%s %s" % (_rule_kind_label_text(kind), value)
    trigger = ui_modal.trigger_html(
        dialog_id, escape_html(i18n.t(RULE_REMOVE_BUTTON_TEXT)),
        "btn btn--secondary special-row__remove",
        i18n.t(RULE_REMOVE_ARIA) % subject)
    dialog = ui_modal.dialog_html(
        dialog_id, i18n.t(RULE_REMOVE_DIALOG_TITLE), _rule_delete_action(kind, value),
        csrf_field(), "<p>%s</p>" % escape_html(i18n.t(RULE_REMOVE_DIALOG_BODY) % subject),
        i18n.t(RULE_REMOVE_SUBMIT_TEXT), i18n.t(RULE_REMOVE_DISMISS_TEXT),
        device_scope.scoped(layout.DISPLAY_SPECIAL_LOOKS_ROUTE) + "#" + SPECIAL_LOOKS_ANCHOR,
        destructive=True, confirm_only=True)
    return trigger, dialog


def _rule_row_html(kind, value, theme_id):
    """One `<li class="special-row rule-row">`: a mini render of the
    rule's look, its kind tag, key and read-back, and a Remove link that
    opens the confirm dialog (a hash link, so it works without script).
    """
    trigger, dialog = _rule_remove_html(kind, value)
    subject = "%s %s" % (_rule_kind_label_text(kind), value)
    edit_html = '<a class="special-row__edit" href="%s" aria-label="%s">%s</a>' % (
        escape_html(edit_href(kind, value)), escape_html(i18n.t(RULE_EDIT_ARIA) % subject),
        escape_html(i18n.t(RULE_EDIT_BUTTON_TEXT)))
    return (
        '<li class="special-row rule-row"><div class="special-row__main">%s'
        '<div class="special-row__text">'
        '<p class="special-row__title"><span class="special-row__tag rule-row__kind">%s</span>%s</p>'
        '<p class="special-row__meta rule-row__theme">%s</p></div>'
        '<div class="special-row__actions">%s%s</div></div>%s</li>'
    ) % (
        special_mini_html(theme_id),
        escape_html(_rule_kind_label_text(kind)),
        _rule_title_html(kind, value),
        escape_html(look.look_sentence(theme_id)),
        edit_html, trigger, dialog,
    )


def _rule_list_html(rows):
    """One `.rule-row` per rule. `colour_rules.rule_rows()` already
    orders rows most-specific first (callsign, then hex, then prefix)
    and alphabetically within each kind, so no re-sort is needed here.
    Returns "" for an empty list.
    """
    return "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows
        if kind in colour_rules.RULE_KINDS
        and colour_rules.normalise_rule_value(kind, value) == value)


def special_looks_html(ctx, calendar_row_html):
    """The Special looks list: the calendar row, one row per per-flight
    rule, and the link to the page that adds one. `ctx` arrives already a
    `PageContext`.
    """
    registry = ctx.colour_rules
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    add_html = (
        '<li class="special-row special-row--add">'
        '<a class="special-add__summary" href="%s">'
        '<span class="special-add__plus">%s</span><span>%s</span></a></li>'
    ) % (
        escape_html(device_scope.scoped(layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE)),
        layout.icon_html("icon-plus"), escape_html(i18n.t(ADD_SPECIAL_LOOK_LABEL)))
    rows_html = _rule_list_html(colour_rules.rule_rows(registry))
    empty_html = "" if rows_html else ui_components.empty_state(
        i18n.t(SPECIAL_LOOKS_EMPTY_HEADING), "", compact=True)
    return (
        '<div class="special-looks">'
        '<h3 class="special-looks__title">%s</h3>'
        '<p class="text-label section-caption">%s</p>'
        '%s%s<ul class="special-list special-list--add">%s</ul>'
        '<p class="text-label special-looks__order">%s</p>'
        "</div>"
    ) % (
        escape_html(i18n.t(SPECIAL_LOOKS_HEADING)), escape_html(i18n.t(RULES_SECTION_CAPTION)),
        empty_html,
        '<ul class="special-list">%s%s</ul>' % (calendar_row_html, rows_html)
        if (calendar_row_html or rows_html) else "",
        add_html, escape_html(i18n.t(SPECIAL_LOOKS_ORDER)),
    )
