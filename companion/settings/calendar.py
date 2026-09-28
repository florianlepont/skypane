"""The Calendar settings group: the connection status block, the
connect/replace/disconnect forms, the two-step disconnect confirmation
page, and the full Calendar usage row of the Aspect card (built here so
`companion.settings.theme` stays independent of this module — see that
module's own docstring for why).
"""
from urllib.parse import urlsplit

from companion import i18n
import companion.layout as layout
from companion.layout import escape_html
import companion.page_context as page_context
from server import device_config
from server.plane import calendar_rules

from companion.settings.form import (
    CALENDAR_HOW_IT_WORKS_SUMMARY, SETTINGS_FORM_ID, _field_error_attrs, _field_error_html,
    _submitted_or_current)
from companion.settings.theme import (
    ASPECT_HEADING_ID, COLOUR_USAGE_CALENDAR, SAME_AS_DEPARTURES_LABEL,
    _palette_grid_html, _same_as_departures_chip_html, _theme_label_message,
    _usage_row_html, _usage_row_summary_html)


# An immediate, session-gated POST outside SETTINGS_ROUTE and the
# settings form's dirty bar: a one-step act, not a pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"


# Shares its "no surveillance verb" discipline with
# companion.settings.form.CALENDAR_HOW_IT_WORKS_SUMMARY (form.py's own
# docstring carries the full reasoning, since notifications_group()
# reuses that same summary label).
CALENDAR_HOW_IT_WORKS_BODY = i18n.msg(
    "calendar_group.it_can_only_colour_a_flight_that_happens_to_be",
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.")


# "Not connected" covers both the never-configured and the
# permission-drifted states — a drifted stored link is not usably
# connected either.
CALENDAR_STATUS_CONNECTED_VERDICT = i18n.msg("calendar_group.connected", "Connected")
CALENDAR_STATUS_NOT_CONNECTED_VERDICT = i18n.msg(
    "calendar_group.not_connected", "Not connected")
CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE = i18n.msg(
    "calendar_group.1_upcoming_flight_checked", "1 upcoming flight · checked %s")
CALENDAR_STATUS_DETAIL_TEMPLATE = i18n.msg(
    "calendar_group.upcoming_flights_checked", "%d upcoming flights · checked %s")


# A fixed dict keyed on a category derived from existing fields
# (last_attempt_at newer than any usable last_synced_at) — never the
# fetch's own caught exception text, which is not persisted anywhere
# this module could read it from.
CALENDAR_STATUS_FETCH_FAILED_DETAIL = i18n.msg(
    "calendar_group.the_feed_could_not_be_read", "The feed could not be read")


CALENDAR_CONNECT_BUTTON_TEXT = i18n.msg("calendar_group.connect_calendar", "Connect calendar")
CALENDAR_REPLACE_URL_SUMMARY = i18n.msg(
    "calendar_group.replace_the_feed_url", "Replace the feed URL")


# The same form/route posts the URL field in both states, but the
# button reads shorter once a feed is already stored — "Connect
# calendar" only ever applies to a first-time paste.
CALENDAR_REPLACE_BUTTON_TEXT = i18n.msg("calendar_group.replace", "Replace")


# Plain, honest wording: no surveillance verb, no promise the frame
# cannot keep. The file the URL is stored in is never named below.
# Owned by companion/i18n_fr/display.py, not this module's own
# calendar_group.py — the Display page's Calendar row shares this field
# label/hint with the rest of the Aspect card's own display.py copy.
CALENDAR_URL_FIELD_LABEL = i18n.msg("display.calendar_feed_url", "Calendar feed URL")
CALENDAR_URL_HINT = i18n.msg(
    "display.your_calendar_s_private_ical_link_stored_on_the",
    "Your calendar's private iCal link. Stored on the server and never "
    "shown back here — pasting a new one replaces the old.")
CALENDAR_URL_HINT_ID = "calendar-url-hint"


# A cross-DOM form= attribute (CALENDAR_DISCONNECT_FORM_ID) lets this
# button submit a <form> that is never its own DOM ancestor.
CALENDAR_DISCONNECT_BUTTON_TEXT = i18n.msg("calendar_group.disconnect", "Disconnect")
CALENDAR_DISCONNECT_FORM_ID = "calendar-disconnect-form"


# The dedicated disconnect route's own confirm gate — the single
# definition site the markup, the client-side misclick guard
# (confirm-submit.js) and the handler all read. Deliberately a
# different field name from calendar_disconnect above: this field means
# "the confirmation step passed", that one meant "the checkbox was
# ticked".
CALENDAR_DISCONNECT_CONFIRM_FIELD = "confirm"
CALENDAR_DISCONNECT_CONFIRM_VALUE = "yes"


# The question confirm-submit.js passes to window.confirm() (a
# misclick guard only), carried via the disconnect form's data-confirm
# attribute, never duplicated in the script itself. Owned by
# companion/i18n_fr/display.py, not calendar_group.py — these four
# confirmation-page strings belong to the Display-page-adjacent
# calendar_disconnect_confirm_page(), distinct from the merged card's
# own shorter calendar_group.* strings above.
CALENDAR_DISCONNECT_CONFIRM_QUESTION = i18n.msg(
    "display.disconnect_this_calendar_and_delete_the_flights",
    "Disconnect this calendar and delete the flights it supplied?")


# What a no-JS or CSP-blocked browser sees instead of the native dialog
# above, on the server-rendered two-step confirmation page.
CALENDAR_DISCONNECT_CONFIRM_HEADING = i18n.msg(
    "display.disconnect_calendar", "Disconnect calendar?")
CALENDAR_DISCONNECT_CONFIRM_SENTENCE = i18n.msg(
    "display.this_disconnects_your_calendar_and_deletes_the",
    "This disconnects your calendar and deletes the flights it "
    "supplied from the server. This can't be undone — you'd need to "
    "paste the feed URL again to reconnect.")
CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT = i18n.msg(
    "display.disconnect_calendar_2", "Disconnect calendar")
CALENDAR_DISCONNECT_CANCEL_TEXT = i18n.msg("display.cancel", "Cancel")


# The one string in this interface permitted to reference "the server",
# since this is the one case where the operator has to act there.
# Names no path, filename or part of the URL. Owned by display.py, like
# the confirmation strings above.
CALENDAR_STATUS_PERMISSION_UNSAFE = i18n.msg(
    "display.connected_but_ignored_its_saved_link_on_the",
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.")


# A shape bound against an absurd paste, not a definition of an
# acceptable URL. The arbiter of whether a URL is acceptable stays the
# server-side safety gate and the fetch itself.
CALENDAR_URL_MAX_LEN = 2048


def _masked_calendar_url(url):
    """host + "…" — never the path, query, fragment or userinfo of the
    stored calendar feed URL.

    Uses a real `urlsplit()` parse rather than a byte-offset truncation:
    a naive `url[:20] + "…"` would not be safe, since a short host could
    still leak leading path/query/token characters.

    Returns "" on any failure (falsy url, unparsable, empty netloc); the
    caller omits the masked-URL line entirely rather than fabricate one.
    This is the only place in the module that reads a stored secret URL
    back for display — every other secret-URL field stays write-only.
    """
    if not url:
        return ""
    try:
        netloc = urlsplit(url).netloc
    except ValueError:
        return ""
    if not netloc:
        return ""
    return "%s…" % netloc


def _status_row_with_html_detail(verdict, detail_html, state):
    """`layout.status_row()`'s exact markup for the label="" case, except
    `detail_html` is spliced verbatim instead of being escaped again —
    the one caller below (the "usable" branch of `_calendar_status_html()`)
    has already escaped its template text and glued in
    `layout.relative_time_html()`'s own pre-escaped `<time>` markup, so
    running it through `escape_html()` again would double-encode that
    markup. `verdict` is still escaped here, exactly like `status_row()`.
    Never call this for any other case — every other branch keeps calling
    `layout.status_row()` unchanged.
    """
    dot_class = layout._STATUS_DOT_CLASSES.get(state, layout._DEFAULT_STATUS_DOT_CLASS)
    modifier = layout.card_status_class("status-row", state)
    css_class = "status-row" + ((" " + modifier) if modifier else "")
    return (
        '<div class="%s">'
        '<span class="dot %s"></span>'
        '<span class="status-row__verdict">%s</span>'
        '<span class="status-row__detail">%s</span>'
        "</div>"
    ) % (css_class, dot_class, escape_html(verdict), detail_html)


def _calendar_status_html(configured, drift, last_synced_at, last_attempt_at, now, entry_count):
    """The Calendar connection row's status line: verdict + detail,
    already wrapped by `layout.status_row()` for every branch except the
    "usable" one below, which bypasses it via
    `_status_row_with_html_detail()` so the age can be a live
    `<time data-relative>` element instead of static text.
    Split out of `_calendar_connection_html()` so that function stays
    under this project's function-length ceiling.

    Drift is checked before `configured`, since a drifted link already
    forces it False.
    """
    # Drift first: it already forces `configured` False, so checking
    # `not configured` first would make this branch unreachable.
    if drift:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = i18n.t(CALENDAR_STATUS_PERMISSION_UNSAFE)
        state = "error"
    elif not configured:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = ""
        state = "warn"
    else:
        usable = (
            bool(last_synced_at)
            and layout.parse_iso(last_synced_at) is not None
            and layout.age_seconds(last_synced_at, now) is not None)
        verdict = i18n.t(CALENDAR_STATUS_CONNECTED_VERDICT)
        if usable:
            age_html = layout.relative_time_html(last_synced_at, now)
            if entry_count == 1:
                detail_html = escape_html(i18n.t(CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE)) % (
                    age_html,)
            else:
                detail_html = escape_html(i18n.t(CALENDAR_STATUS_DETAIL_TEMPLATE)) % (
                    entry_count, age_html)
            return _status_row_with_html_detail(verdict, detail_html, "ok")
        elif last_attempt_at is not None:
            detail = i18n.t(CALENDAR_STATUS_FETCH_FAILED_DETAIL)
            state = "error"
        else:
            detail = ""
            state = "warn"
    return layout.status_row("", verdict, detail, state)


def _calendar_url_field_html(errors=None):
    """The write-only feed-URL `<div class="rule-add-form__field">`,
    shared by the connect and replace forms below (its own `<form>`
    wrapper differs by the button text alone). Split out of
    `_calendar_connection_html()` for the same function-length reason as
    `_calendar_status_html()` above.
    """
    error_attrs = _field_error_attrs(
        errors, "calendar_url", "calendar-connect-url", hint_id=CALENDAR_URL_HINT_ID)
    error_html = _field_error_html(errors, "calendar_url", "calendar-connect-url")
    return (
        '<div class="rule-add-form__field">'
        '<label for="calendar-connect-url">%s</label>'
        '<input type="text" id="calendar-connect-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(CALENDAR_URL_FIELD_LABEL)),
        CALENDAR_URL_MAX_LEN, error_attrs,
        escape_html(CALENDAR_URL_HINT_ID), escape_html(i18n.t(CALENDAR_URL_HINT)),
        error_html,
    )


def _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """Calendar's connection block inside the Aspect card's Calendar
    row: status, connect/replace form or masked URL, and the cross-DOM
    Disconnect button. Returns `(row_body_html, disconnect_form_html)`
    separately, since HTML forbids nesting the disconnect form inside
    the row's own connect/replace form.

    The feed URL field is write-only: never a `value` attribute, only a
    masked `host + "…"` once connected.
    Disconnect posts an empty confirm field to a two-step, server-
    rendered confirm page; the client-side `data-confirm` dialog is a
    misclick guard only, never the real gate.
    """
    status_html = _calendar_status_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count)
    field_html = _calendar_url_field_html(errors)
    # Literal id/action text, not a %s interpolation: this module's
    # acceptance gate greps the attribute text directly.
    disconnect_button_html = (
        '<button type="submit" form="calendar-disconnect-form" class="calendar-disconnect-btn">%s</button>'
    ) % escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT))
    if configured:
        # configured=True here already means calendar_is_configured()'s
        # own drift guard passed upstream, so this second read is safe.
        masked_url = _masked_calendar_url(
            calendar_rules.configured_calendar_url(state_dir) if state_dir else "")
        masked_url_html = (
            '<p class="text-body calendar-masked-url">%s</p>' % escape_html(masked_url)
            if masked_url else "")
        replace_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_REPLACE_BUTTON_TEXT)),
        )
        disclosure_html = (
            '<details class="calendar-url-disclosure"><summary class="text-link">%s</summary>%s</details>'
        ) % (escape_html(i18n.t(CALENDAR_REPLACE_URL_SUMMARY)), replace_form_html)
        actions_html = (
            '<p class="calendar-actions">%s%s</p>' % (disclosure_html, disconnect_button_html))
        state_branch_html = masked_url_html + actions_html
    else:
        connect_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_CONNECT_BUTTON_TEXT)),
        )
        if drift:
            drift_actions_html = (
                '<p class="calendar-actions calendar-actions--solo">%s</p>'
                % disconnect_button_html)
        else:
            drift_actions_html = ""
        state_branch_html = connect_form_html + drift_actions_html

    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)),
    )

    # No wrapping element: the caller places this fragment directly
    # inside the Calendar <details> row.
    row_body_html = status_html + state_branch_html + how_it_works_html

    if configured or drift:
        disconnect_form_html = (
            '<form id="%s" method="post" action="%s" data-confirm="%s" '
            'data-confirm-value="%s">'
            '<input type="hidden" name="%s" value="" data-confirm-field>'
            "</form>"
        ) % (
            escape_html(CALENDAR_DISCONNECT_FORM_ID),
            CALENDAR_DISCONNECT_ROUTE,
            escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_QUESTION)),
            escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
            CALENDAR_DISCONNECT_CONFIRM_FIELD,
        )
    else:
        disconnect_form_html = ""

    return row_body_html, disconnect_form_html


def calendar_disconnect_confirm_page(ctx):
    """Two-step disconnect confirmation, rendered whenever the posted
    confirm field does not exactly match the expected value (including
    a bare POST with none). This page is the actual security control:
    it works with JavaScript disabled, blocked by CSP, or against a
    hand-crafted request that skips the client-side confirm dialog.

    The form re-posts to the same route with the confirm field
    pre-filled; cancel is a plain link back to Display, never a second
    form. `ctx` is accepted but unused today, matching every other
    scoped builder's signature - coerced anyway, so a typo'd test ctx
    still fails loudly rather than being silently accepted.
    """
    page_context.coerce(ctx)
    return (
        layout.page_header(i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING))
        + '<p class="text-body">%s</p>'
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_SENTENCE)),
        CALENDAR_DISCONNECT_ROUTE,
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT)),
        layout.DISPLAY_ROUTE, escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
    )


def calendar_usage_row_html(
        departures_safe_id, current_calendar_theme_id, configured, drift,
        last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """The complete Calendar usage row for the Aspect card: the
    theme-selection palette (falling back to `departures_safe_id` when
    unset, exactly like `_aspect_card_html()`'s own Arrivals row) plus
    the connection status block `_calendar_connection_html()` builds.
    Returns `(row_html, disconnect_form_html)` — the disconnect form is
    a sibling fragment of the whole Aspect card, never nested inside
    this row; `companion.settings.theme._aspect_card_html()` appends it
    after the card itself, unchanged from before this split.
    """
    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    calendar_same_checked = not effective_calendar
    calendar_leading = _same_as_departures_chip_html(
        "calendar_theme_id", calendar_same_checked, radio_form_id=SETTINGS_FORM_ID)
    if calendar_same_checked:
        calendar_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        calendar_swatch_id = departures_safe_id
    else:
        calendar_safe_id = (
            effective_calendar if effective_calendar in device_config.THEMES
            else departures_safe_id)
        calendar_meta = _theme_label_message(calendar_safe_id)
        calendar_swatch_id = calendar_safe_id
    # The calendar's connection block nests directly beneath this row's
    # palette and field error. The disconnect form returned alongside
    # it is not part of the row body: it is a sibling fragment of the
    # whole .aspect-card div, concatenated onto the caller's own return
    # value.
    calendar_connection_row_html, calendar_disconnect_form_html = _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=errors, submitted=submitted, state_dir=state_dir)
    calendar_row = _usage_row_html(
        COLOUR_USAGE_CALENDAR,
        _usage_row_summary_html(
            COLOUR_USAGE_CALENDAR, calendar_swatch_id, meta_text=calendar_meta),
        _palette_grid_html(
            "calendar_theme_id", effective_calendar, radio_form_id=SETTINGS_FORM_ID,
            leading_html=calendar_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "calendar_theme_id", "calendar-theme")
        + calendar_connection_row_html)
    return calendar_row, calendar_disconnect_form_html
