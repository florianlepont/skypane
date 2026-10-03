"""The colour-rules settings group: the per-flight rules shown as the
look card's "Special looks" list (rows, per-row delete, and the "Add a
special look" form with recent suggestions), plus the manual "Trigger
poll now" control. Built here so `companion.settings.theme` stays
independent of this module — see that module's own docstring for why.
"""
from companion import i18n
from companion import theme_preview
import companion.layout as layout
from companion.layout import escape_html
from server import device_config, history_db
from server.plane import colour_rules, enrich

from companion.settings import look
from companion.settings.calendar import special_mini_html
from companion.settings.form import (
    _field_error_attrs, _field_error_html, _submitted_or_current)
from companion.settings.theme import (
    COLOUR_USAGE_RULES, LOOK_CLOSE_LABEL, look_target_attrs)


# Owned by companion/i18n_fr/display.py, not this module's own rules.py
# catalogue — the Poll card's copy lives beside the rest of Device's
# own display.py strings.
POLL_SECTION_CAPTION = i18n.msg(
    "display.request_a_server_check_for_new_flight_data",
    "Ask the server to check for new flight data now.")



# "{n}" is filled in with a server-computed remaining-seconds figure,
# never anything client-supplied. This is the button-adjacent copy
# shown while the trigger is disabled — a separate rendering site from
# companion/app.py's own FLASH_MESSAGES entry for the same event, since
# a page module must never import companion/app.py.
POLL_COOLDOWN_HELPER_TEXT = i18n.msg(
    "display.poll_triggered_recently_try_again_in_n_s",
    "Poll triggered recently — try again in {n}s.")

# DOM ids the live countdown script (poll-cooldown.js) hooks with
# document.getElementById(), shared with poll_trigger_section()'s
# markup so the two can never drift apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# The enabled (zero-cooldown) branch's button label while a submit is
# pending. Cosmetic only: companion/app.py's _POLL_LOCK is the actual
# correctness boundary.
POLL_SUBMIT_PENDING_TEXT = i18n.msg("display.polling", "Polling…")

# The manual-poll button's own label, shared by both the enabled and
# cooldown branches of poll_trigger_section() below.
POLL_TRIGGER_BUTTON_TEXT = i18n.msg("display.refresh_now", "Refresh now")

# The placeholder the client substitutes the live second count into, so
# the ticking copy stays word-identical to the static, server-rendered
# copy and to the post-redirect flash banner.
POLL_COOLDOWN_TEMPLATE_TOKEN = "__N__"



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
    "Override the look for one airline, flight or aircraft.")
SPECIAL_LOOKS_ORDER = i18n.msg(
    "look.most_specific_wins",
    "Most specific wins: calendar, then flight, aircraft, airline. "
    "Adding a key already in the list replaces its look.")
ADD_SPECIAL_LOOK_LABEL = i18n.msg("look.add_a_special_look", "Add a special look")
NEW_SPECIAL_LOOK_HEADING = i18n.msg("look.new_special_look", "New special look")
RULE_PREVIEW_TEXT = i18n.msg(
    "look.matching_flights_will_look_like_this",
    "Matching flights will look like this, unless a more specific look applies.")
RULE_LOOK_LABEL = i18n.msg("look.look", "Look")
# Owned by companion/i18n_fr/display.py, not this module's own
# rules.py catalogue — shared segmented-control copy that predates the
# per-flight rules feature.
RULE_KIND_FIELD_LABEL = i18n.msg("display.match_by", "Applies to")
RULE_VALUE_FIELD_LABEL = i18n.msg("display.value", "Value")
RULE_ADD_BUTTON_TEXT = i18n.msg("display.add_rule", "Add special look")
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
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
RULE_REMOVE_CONFIRM_QUESTION = i18n.msg("rules.remove_this_rule", "Remove this rule?")
# Recent suggestions offered per kind, newest first.
RULE_SUGGESTIONS_PER_KIND = 5


def poll_trigger_section(cooldown_remaining):
    """The manual poll-trigger control: an enabled button, or a
    native-disabled button with remaining-seconds copy during a
    cooldown. Emits zero `<script>` elements: the countdown lives in
    `poll-cooldown.js`, driven by `data-*` attributes, UX only —
    `_handle_poll_now()` re-checks the cooldown server-side regardless.
    The caption is computed once, above both branches.
    """
    # `> 0`, not truthy: must agree with poll-cooldown.js's own
    # `remaining > 0` guard, or a negative value would disable the
    # button natively while the script no-ops, with no way to re-enable
    # it client-side.
    caption_html = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(i18n.t(POLL_SECTION_CAPTION)))
    if cooldown_remaining > 0:
        translated_helper_text = i18n.t(POLL_COOLDOWN_HELPER_TEXT)
        cooldown_text = translated_helper_text.format(n=cooldown_remaining)
        template = translated_helper_text.format(n=POLL_COOLDOWN_TEMPLATE_TOKEN)
        return (
            "%s"
            '<form method="post" action="/poll-now">'
            '<button type="submit" id="%s" disabled '
            'data-cooldown="%s" data-cooldown-text-id="%s" '
            'data-cooldown-template="%s" data-cooldown-token="%s">'
            "%s</button>"
            "</form>"
            '<p class="text-body" id="%s">%s</p>'
        ) % (
            caption_html,
            POLL_TRIGGER_BUTTON_ID,
            escape_html(str(cooldown_remaining)),
            escape_html(POLL_COOLDOWN_TEXT_ID),
            escape_html(template),
            escape_html(POLL_COOLDOWN_TEMPLATE_TOKEN),
            escape_html(i18n.t(POLL_TRIGGER_BUTTON_TEXT)),
            POLL_COOLDOWN_TEXT_ID,
            escape_html(cooldown_text),
        )
    return (
        "%s"
        '<form method="post" action="/poll-now">'
        '<button type="submit" id="%s" data-submit-pending="%s">'
        "%s</button>"
        "</form>"
    ) % (
        caption_html,
        POLL_TRIGGER_BUTTON_ID,
        escape_html(i18n.t(POLL_SUBMIT_PENDING_TEXT)),
        escape_html(i18n.t(POLL_TRIGGER_BUTTON_TEXT)),
    )


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
    return "%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, escape_html(kind), escape_html(value),
        RULES_DELETE_ROUTE_SUFFIX,
    )


def _rule_kind_radio_html(kind, checked):
    """One native radio + `<label>` pair for the "Match by" segmented
    control. The radio is visually hidden and styled via the adjacent
    label (`.theme-form input[type="radio"] + label`); the plain-
    language word is the visible label text, and the technical term is
    the label's own `title` attribute, so a hovering mouse user still
    finds the exact vocabulary without it cluttering the visible label.
    """
    radio_id = "rule-kind-%s" % kind
    return (
        '<input type="radio" name="rule_kind" id="%s" value="%s" '
        'class="visually-hidden"%s>'
        '<label for="%s" title="%s">%s</label>'
    ) % (
        escape_html(radio_id), escape_html(kind), " checked" if checked else "",
        escape_html(radio_id), escape_html(i18n.t(RULE_KIND_TITLES[kind])),
        escape_html(i18n.t(RULE_KIND_LABELS[kind])),
    )


def _rule_kind_segment_html(selected_kind, errors):
    """The "Applies to" segmented control: native radios styled as one
    control, labelled by its visible heading."""
    kind_radios = "".join(
        _rule_kind_radio_html(kind, kind == selected_kind)
        for kind in colour_rules.RULE_KINDS)
    return (
        '<p class="look-axis__label" id="%s">%s</p>'
        '<div class="rule-add-form__field rule-add-form__field--kind" role="radiogroup" '
        'aria-labelledby="%s"><div class="theme-form">%s</div>%s</div>'
    ) % (
        escape_html(RULE_KIND_HEADING_ID), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        escape_html(RULE_KIND_HEADING_ID), kind_radios,
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


def _rule_add_form_html(errors=None, submitted=None, suggestions_html=""):
    """The "New special look" form, one `<form>` posting to
    `RULES_ADD_ROUTE` with the unchanged `rule_kind`/`rule_key`/
    `rule_theme_id` fields. Its look is the same colour x style table of
    native radios the pictures use (scripts swap in the three-choice
    picker over it); a mini render shows the chosen look.

    Validation errors render under each field, keeping the typed value.
    """
    selected_kind = _submitted_or_current(
        submitted, "rule_kind", colour_rules.RULE_KIND_CALLSIGN)
    submitted_value = submitted.get("rule_key", "") if submitted is not None else ""
    selected_theme_id = _submitted_or_current(
        submitted, "rule_theme_id", device_config.THEME_IDS[0])
    picture_id = (
        selected_theme_id if selected_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    small = theme_preview.FRAME_PREVIEW_SIZE_SMALL
    table_html = look.look_table_html(
        "rule_theme_id", selected_theme_id, i18n.t(NEW_SPECIAL_LOOK_HEADING),
        lambda theme_id: theme_preview.frame_preview_src(
            theme_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING, small),
        form_id=None)
    return (
        '<form method="post" action="%s" class="rule-add-form special-add__form"%s>'
        '<div class="special-add__head">'
        '<h3 class="special-add__title" id="special-add-title">%s</h3>'
        '<button type="button" class="look-sheet__close" data-special-add-close hidden '
        'aria-label="%s">%s</button></div>'
        '<div class="special-add__cols"><div class="special-add__who">%s%s%s'
        '<div class="special-add__preview">%s<p class="text-label">%s</p></div></div>'
        '<div class="special-add__look">'
        '<p class="look-axis__label special-add__look-label" id="%s">%s</p>'
        '<div data-look-axes-host hidden>%s</div>'
        '<div data-look-table-host>%s</div>%s</div></div>'
        '<div class="special-add__foot">'
        '<button type="button" class="look-sheet__reset" data-special-add-cancel hidden>%s</button>'
        '<button type="submit">%s</button></div>'
        "</form>"
    ) % (
        RULES_ADD_ROUTE,
        look_target_attrs(
            COLOUR_USAGE_RULES, "rule_theme_id", theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
            small, False),
        escape_html(i18n.t(NEW_SPECIAL_LOOK_HEADING)),
        escape_html(i18n.t(LOOK_CLOSE_LABEL)), layout.icon_html("icon-close"),
        _rule_kind_segment_html(selected_kind, errors),
        _rule_value_field_html(submitted_value, errors),
        suggestions_html,
        special_mini_html(picture_id), escape_html(i18n.t(RULE_PREVIEW_TEXT)),
        escape_html(RULE_THEME_HEADING_ID), escape_html(i18n.t(RULE_LOOK_LABEL)),
        look.axes_html("rule_look"),
        table_html,
        _field_error_html(errors, "rule_theme_id", "rule-theme"),
        escape_html(i18n.t(RULE_CANCEL_TEXT)),
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
    )


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
            rows = history_db.recent_runway_events(conn, limit=50)
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


def _rule_row_html(kind, value, theme_id):
    """One `<li class="special-row rule-row">`: a mini render of the
    rule's look, its kind tag, key and read-back, and a Remove form.

    The Remove form's `data-confirm` is a misclick guard only: deleting
    a rule is immediately reversible (re-adding the same key restores
    it), and the server-side handler requires no confirm value.
    """
    delete_form = (
        '<form method="post" action="%s" data-confirm="%s">'
        '<button type="submit" class="special-row__remove">%s</button>'
        "</form>"
    ) % (
        _rule_delete_action(kind, value),
        escape_html(i18n.t(RULE_REMOVE_CONFIRM_QUESTION)),
        escape_html(i18n.t(RULE_REMOVE_BUTTON_TEXT)),
    )
    return (
        '<li class="special-row rule-row"><div class="special-row__main">%s'
        '<div class="special-row__text">'
        '<p class="special-row__title"><span class="special-row__tag rule-row__kind">%s</span>%s</p>'
        '<p class="special-row__meta rule-row__theme">%s</p></div>'
        "%s</div></li>"
    ) % (
        special_mini_html(theme_id),
        escape_html(_rule_kind_label_text(kind)),
        _rule_title_html(kind, value),
        escape_html(look.look_sentence(theme_id)),
        delete_form,
    )


def _rule_list_html(rows):
    """One `.rule-row` per rule. `colour_rules.rule_rows()` already
    orders rows most-specific first (callsign, then hex, then prefix)
    and alphabetically within each kind, so no re-sort is needed here.
    Returns "" for an empty list.
    """
    return "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)


def special_looks_html(ctx, calendar_row_html):
    """The look card's Special looks column: the calendar row, one row
    per per-flight rule, and the "Add a special look" disclosure holding
    the add form. `ctx` arrives already a `PageContext`.
    """
    registry = ctx.colour_rules
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    add_html = (
        '<li class="special-row special-row--add">'
        '<details class="special-add" data-special-add>'
        '<summary class="special-add__summary">'
        '<span class="special-add__plus">%s</span><span>%s</span></summary>'
        '<div class="special-add__panel" aria-labelledby="special-add-title">%s</div>'
        "</details></li>"
    ) % (
        layout.icon_html("icon-plus"), escape_html(i18n.t(ADD_SPECIAL_LOOK_LABEL)),
        _rule_add_form_html(suggestions_html=_rule_suggestion_chips_html(ctx.state_dir)))
    return (
        '<div class="special-looks">'
        '<h3 class="special-looks__title">%s</h3>'
        '<p class="text-label section-caption">%s</p>'
        '<ul class="special-list">%s%s%s</ul>'
        '<p class="text-label special-looks__order">%s</p>'
        "</div>"
    ) % (
        escape_html(i18n.t(SPECIAL_LOOKS_HEADING)), escape_html(i18n.t(RULES_SECTION_CAPTION)),
        calendar_row_html, _rule_list_html(colour_rules.rule_rows(registry)), add_html,
        escape_html(i18n.t(SPECIAL_LOOKS_ORDER)),
    )
