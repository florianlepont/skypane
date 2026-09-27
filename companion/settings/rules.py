"""The colour-rules settings group: the per-flight colour-rules editor
(add form, suggestion chips, per-row delete) and the manual "Trigger
poll now" control, plus the full Rules usage row of the Aspect card
(built here so `companion.settings.theme` stays independent of this
module — see that module's own docstring for why).
"""
from companion import i18n
from companion.layout import escape_html
from server import device_config, history_db
from server.plane import colour_rules

from companion.settings.form import (
    _field_error_attrs, _field_error_html, _submitted_or_current)
from companion.settings.theme import (
    COLOUR_USAGE_RULES, _palette_hex, _theme_chip_grid_html, _usage_row_html,
    _usage_row_summary_html)


POLL_SECTION_CAPTION = "Trigger an immediate poll cycle."



# "{n}" is filled in with a server-computed remaining-seconds figure,
# never anything client-supplied. This is the button-adjacent copy
# shown while the trigger is disabled — a separate rendering site from
# companion/app.py's own FLASH_MESSAGES entry for the same event, since
# a page module must never import companion/app.py.
POLL_COOLDOWN_HELPER_TEXT = "Poll triggered recently — try again in {n}s."

# DOM ids the live countdown script (poll-cooldown.js) hooks with
# document.getElementById(), shared with poll_trigger_section()'s
# markup so the two can never drift apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# The enabled (zero-cooldown) branch's button label while a submit is
# pending. Cosmetic only: companion/app.py's _POLL_LOCK is the actual
# correctness boundary.
POLL_SUBMIT_PENDING_TEXT = "Polling…"

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


RULES_SECTION_CAPTION = "Give one flight, one aircraft or one airline its own theme."
RULES_HOW_RULES_COMBINE_SUMMARY = "How rules combine"
RULES_HOW_RULES_COMBINE_BODY = (
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.")
RULE_KIND_FIELD_LABEL = "Match by"
RULE_VALUE_FIELD_LABEL = "Value"
RULE_ADD_BUTTON_TEXT = "Add rule"
# The plain-language segment labels, used by both the add form's
# segment text and the rule-row kind badge, so the two can never
# disagree.
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: "Flight",
    colour_rules.RULE_KIND_HEX: "Aircraft",
    colour_rules.RULE_KIND_PREFIX: "Airline",
}
# A separate mapping from RULE_KIND_LABELS above, read only for each
# segment's own title attribute, never shown as the visible label text.
RULE_KIND_TITLES = {
    colour_rules.RULE_KIND_CALLSIGN: "Callsign",
    colour_rules.RULE_KIND_HEX: "ICAO24 hex",
    colour_rules.RULE_KIND_PREFIX: "Callsign prefix",
}
RULE_VALUE_PLACEHOLDER = "AFR1234"
RULES_EMPTY_HEADING = "No flight colours yet."
RULES_EMPTY_BODY = (
    "Add one above to give a flight, aircraft or airline its own theme.")
RULE_REMOVE_BUTTON_TEXT = "Remove"
# The suggestion chips' own label prefix; the joined callsign list
# itself is data, never translated.
RULE_SUGGESTIONS_LABEL = "Recent:"
# aria-labelledby targets for the two radiogroups the add form carries.
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
RULE_REMOVE_CONFIRM_QUESTION = "Remove this rule?"


FRAME_COLOURS_RULES_COUNT_SINGULAR = "1 rule"
FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE = "%d rules"
FRAME_COLOURS_RULES_EMPTY_META = "No rules yet"


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
            escape_html(i18n.t("Trigger poll now")),
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
        escape_html(i18n.t("Trigger poll now")),
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


def _rule_add_form_html(errors=None, submitted=None):
    """The one-line add-rule form: a `role="radiogroup"` of native
    radios styled as a segmented control, a value input, a compact
    theme-chip grid and an "Add rule" button, one `<form>` targeting
    `RULES_ADD_ROUTE`.

    No per-segment placeholder swap on selection (no script wires it):
    one static placeholder covers the always-valid default kind only.
    Validation errors render under the field, keeping the typed value.
    """
    selected_kind = _submitted_or_current(
        submitted, "rule_kind", colour_rules.RULE_KIND_CALLSIGN)
    kind_radios = "".join(
        _rule_kind_radio_html(kind, kind == selected_kind)
        for kind in colour_rules.RULE_KINDS)
    kind_error_html = _field_error_html(errors, "rule_kind", "rule-kind")

    submitted_value = submitted.get("rule_key", "") if submitted is not None else ""
    value_error_attrs = _field_error_attrs(errors, "rule_key", "rule-key")
    value_error_html = _field_error_html(errors, "rule_key", "rule-key")

    selected_theme_id = _submitted_or_current(
        submitted, "rule_theme_id", device_config.THEME_IDS[0])
    theme_error_html = _field_error_html(errors, "rule_theme_id", "rule-theme")
    chip_grid_html = _theme_chip_grid_html(
        "rule_theme_id", selected_theme_id,
        extra_class="theme-chip-grid--compact", chip_extra_class="theme-chip--compact",
        extra_attr='role="radiogroup" aria-labelledby="%s"' % escape_html(RULE_THEME_HEADING_ID))

    return (
        '<form method="post" action="%s" class="rule-add-form rule-add-form--inline">'
        '<div class="rule-add-form__field rule-add-form__field--kind" role="radiogroup" '
        'aria-labelledby="%s">'
        '<span id="%s" class="visually-hidden">%s</span>'
        '<div class="theme-form">%s</div>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="rule-key" class="visually-hidden">%s</label>'
        '<input type="text" id="rule-key" name="rule_key" maxlength="8" '
        'required autocomplete="off" placeholder="%s" value="%s"%s>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<span id="%s" class="visually-hidden">%s</span>'
        "%s"
        "%s"
        "</div>"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        RULES_ADD_ROUTE,
        escape_html(RULE_KIND_HEADING_ID),
        escape_html(RULE_KIND_HEADING_ID), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        kind_radios,
        kind_error_html,
        escape_html(i18n.t(RULE_VALUE_FIELD_LABEL)),
        escape_html(RULE_VALUE_PLACEHOLDER), escape_html(submitted_value), value_error_attrs,
        value_error_html,
        escape_html(RULE_THEME_HEADING_ID), escape_html(i18n.t("Theme")),
        chip_grid_html,
        theme_error_html,
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
    )


def _rule_suggestion_chips_html(state_dir):
    """Up to five distinct recent callsigns as suggestion chips, from
    `history_db.recent_runway_events()` (a second, independent call to
    the same shared helper `home_page._recent_flights()` uses, since
    page modules never import each other directly). The `<button
    type="button">` chips ship with no script to wire them in this
    phase, so they degrade to inert, never to invisible.

    Returns "" when there are no recent events, or on any read failure
    — never raises.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(conn, limit=20)
    except Exception:
        return ""
    seen = []
    for row in rows:
        callsign = row.get("callsign")
        if callsign and callsign not in seen:
            seen.append(callsign)
        if len(seen) >= 5:
            break
    if not seen:
        return ""
    chips = " · ".join(
        '<button type="button" class="rule-suggestion-chip" data-kind="callsign" '
        'data-value="%s">%s</button>' % (escape_html(cs), escape_html(cs))
        for cs in seen)
    return '<p class="text-label rule-suggestions">%s %s</p>' % (
        escape_html(i18n.t(RULE_SUGGESTIONS_LABEL)), chips)


def _rule_row_html(kind, value, theme_id):
    """One `<li class="rule-row">`: the theme's two palette dots, the
    key, a kind badge, the theme's display name, and a Remove form.

    The Remove form's `data-confirm` is a misclick guard only: deleting
    a rule is immediately reversible (re-adding the same key restores
    it), and the server-side handler requires no confirm value.
    """
    departing_hex = _palette_hex(device_config.THEMES[theme_id]["departing_index"])
    arriving_hex = _palette_hex(device_config.THEMES[theme_id]["arriving_index"])
    swatch_html = (
        '<span class="rule-row__swatch theme-chip__swatches" aria-hidden="true">'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        "</span>"
    ) % (escape_html(departing_hex), escape_html(arriving_hex))
    delete_form = (
        '<form method="post" action="%s" data-confirm="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        _rule_delete_action(kind, value),
        escape_html(i18n.t(RULE_REMOVE_CONFIRM_QUESTION)),
        escape_html(i18n.t(RULE_REMOVE_BUTTON_TEXT)),
    )
    return (
        '<li class="rule-row">'
        "%s"
        '<span class="rule-row__key mono">%s</span>'
        '<span class="rule-row__kind banner__pill">%s</span>'
        '<span class="rule-row__theme">%s</span>'
        "%s"
        "</li>"
    ) % (
        swatch_html,
        escape_html(value),
        escape_html(i18n.t(RULE_KIND_LABELS.get(kind, kind))),
        escape_html(i18n.t(device_config.theme_label(theme_id))),
        delete_form,
    )


def _rule_list_html(rows):
    """`<ul class="rule-list">`, one `.rule-row` per row.
    `colour_rules.rule_rows()` already orders rows most-specific first
    (callsign, then hex, then prefix) and alphabetically within each
    kind, so no re-sort is needed here. Returns "" for an empty list;
    the caller renders its own empty state in that case.
    """
    if not rows:
        return ""
    items = "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)
    return '<ul class="rule-list">%s</ul>' % items


def rules_usage_row_html(ctx):
    """The complete Rules usage row for the Aspect card: the rule list
    (or empty state), the add form and suggestion chips inside a nested
    `<details class="rule-add">` disclosure, and "How rules combine"
    outside it, since it explains the list, not the form. Built here
    (not in `companion.settings.theme`) so that module stays independent
    of this one — see its own docstring for why.
    """
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    rule_rows = colour_rules.rule_rows(registry)
    rules_caption_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(RULES_SECTION_CAPTION))
    rules_how_combine_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_SUMMARY)),
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_BODY)),
    )
    if not rule_rows:
        rules_list_html = (
            '<div class="empty-state-plain"><p class="text-label">%s %s</p></div>'
        ) % (escape_html(i18n.t(RULES_EMPTY_HEADING)), escape_html(i18n.t(RULES_EMPTY_BODY)))
        rules_meta = i18n.t(FRAME_COLOURS_RULES_EMPTY_META)
    else:
        rules_list_html = _rule_list_html(rule_rows)
        rule_count = len(rule_rows)
        if rule_count == 1:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_SINGULAR)
        else:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE) % rule_count
    # The rule-add disclosure's <summary> reuses RULE_ADD_BUTTON_TEXT
    # rather than inventing a new summary string.
    rule_add_html = (
        '<details class="rule-add"><summary>%s</summary>%s%s</details>'
    ) % (
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
        _rule_add_form_html(),
        _rule_suggestion_chips_html(ctx.get("state_dir")),
    )
    return _usage_row_html(
        COLOUR_USAGE_RULES,
        _usage_row_summary_html(COLOUR_USAGE_RULES, None, meta_text=rules_meta),
        rules_caption_html + rules_list_html + rule_add_html + rules_how_combine_html,
        extra_class="usage-row--secondary")
