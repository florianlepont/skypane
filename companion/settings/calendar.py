"""The Calendar settings group: the one-line connection status row on the
Personalisation page, the connection page that holds every control (paste or
replace the link, disconnect), the two-step disconnect confirmation page,
and the calendar row of the Special looks list (built here so
`companion.settings.theme` stays independent of this module — see that
module's own docstring for why).

The list keeps one compact row and one button that opens the connection page
(a page of its own, at `DISPLAY_CALENDAR_CONNECT_ROUTE`); the disconnect
confirmation is a dialog on that page, with the server-rendered
confirmation page behind it for a bare POST.
`companion/static/calendar-connect.js` only labels the pending connect.
"""
from urllib.parse import urlsplit

from companion import device_scope, i18n
from companion import ui_components
from companion import ui_modal
import companion.layout as layout
from companion.layout import csrf_field, escape_html
import companion.page_context as page_context
from server import device_config
from server.plane import calendar_rules

from companion import theme_preview
from companion.settings import layout_picker
from companion.settings.form import SETTINGS_FORM_ID, _submitted_or_current
from companion.settings.theme import (
    COLOUR_USAGE_CALENDAR, FRAME_COLOURS_ROW_LABELS, LOOK_CHANGE_ARIA_TEMPLATE,
    LOOK_CHANGE_LABEL, LOOK_SHEET_TITLES, SAME_AS_DEPARTURES_LABEL, look_frame_html,
    look_sheet_html)


# An immediate, session-gated POST outside SETTINGS_ROUTE and the
# settings form's dirty bar: a one-step act, not a pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"
CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"

CONNECT_FORM_ID = "calendar-connect-form"
# The look table's radios belong to the settings form by id, so the page's form is that form.
LOOK_FORM_ID = SETTINGS_FORM_ID
# The route the settings form posts to (config_page.SETTINGS_ROUTE).
SETTINGS_POST_ROUTE = "/settings"
DISCONNECT_DIALOG_ID = "disconnect-calendar"


# --- Status row copy -------------------------------------------------------

CALENDAR_STATUS_CONNECTED_VERDICT = i18n.msg("calendar_group.connected", "Connected")
CALENDAR_STATUS_NOT_CONNECTED_VERDICT = i18n.msg(
    "calendar_group.not_connected", "Not connected")
CALENDAR_PILL_STALE = i18n.msg("calendar_group.pill_out_of_date", "Out of date")
CALENDAR_PILL_ERROR = i18n.msg("calendar_group.pill_error", "Error")
CALENDAR_PILL_WAITING = i18n.msg("calendar_group.pill_waiting", "Waiting")
CALENDAR_PILL_IGNORED = i18n.msg("calendar_group.pill_ignored", "Ignored")
CALENDAR_PILL_CHECK = i18n.msg("calendar_group.pill_check", "Check")

# The detail line always says the window ("48 h") because that is what the
# count is: the poll keeps flights up to 48 hours ahead.
CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE = i18n.msg(
    "calendar_group.1_flight_in_the_next_48_h_checked",
    "1 flight in the next 48 h · checked %s")
CALENDAR_STATUS_DETAIL_TEMPLATE = i18n.msg(
    "calendar_group.flights_in_the_next_48_h_checked",
    "%d flights in the next 48 h · checked %s")
CALENDAR_STATUS_ZERO_TEMPLATE = i18n.msg(
    "calendar_group.0_flights_found_check_it_s_the_right_calendar",
    "0 flights found — check it's the right calendar · checked %s")
CALENDAR_STATUS_PENDING_DETAIL = i18n.msg(
    "calendar_group.first_read_at_the_frame_s_next_check",
    "First read at the frame's next check")
CALENDAR_STATUS_STALE_TEMPLATE = i18n.msg(
    "calendar_group.last_read_the_frame_keeps_the_last_flights",
    "Last read %s · the frame keeps the last flights it read")
CALENDAR_STATUS_FAILED_TEMPLATE = i18n.msg(
    "calendar_group.couldn_t_read_the_calendar_last_read",
    "Couldn't read the calendar · last read %s")
CALENDAR_STATUS_FETCH_FAILED_DETAIL = i18n.msg(
    "calendar_group.couldn_t_read_the_calendar", "Couldn't read the calendar")
CALENDAR_STATUS_PERMISSION_UNSAFE = i18n.msg(
    "calendar_group.saved_link_ignored_it_was_readable_by_others",
    "Saved link ignored — it was readable by others on the server. "
    "Paste it again to store it safely.")

CALENDAR_NONE_LEAD = i18n.msg(
    "calendar_group.colour_the_flights_from_your_calendar_on_screen",
    "Colour the flights from your calendar on screen.")
CALENDAR_CHOOSE_TEXT = i18n.msg("display.choose_calendar", "Choose calendar")
CALENDAR_CONNECT_ADD_TEXT = i18n.msg("display.connect_a_calendar", "Connect a calendar")
CALENDAR_FLIGHTS_ON_TEXT = i18n.msg(
    "display.calendar_flights_on", "Flights in your calendar: on")
CALENDAR_FLIGHTS_OFF_TEXT = i18n.msg(
    "display.calendar_flights_off", "Flights in your calendar: off")
CALENDAR_EMPTY_HEADING = i18n.msg("display.calendar_not_connected", "No calendar connected")
CALENDAR_CONNECT_BUTTON_TEXT = i18n.msg("calendar_group.connect", "Connect")
CALENDAR_REPLACE_BUTTON_TEXT = i18n.msg("calendar_group.replace", "Replace")
CALENDAR_CHECKING_TEXT = i18n.msg("calendar_group.checking", "Checking…")


# --- Sheet copy ------------------------------------------------------------

CALENDAR_SHEET_TITLE_TEMPLATE = i18n.msg("calendar_group.sheet_title_template", "%s calendar")
CALENDAR_SHEET_CONNECT_TITLE = i18n.msg(
    "calendar_group.connect_a_calendar", "Connect a calendar")
CALENDAR_LINK_LABEL = i18n.msg("calendar_group.calendar_link", "Calendar link")
CALENDAR_NEW_LINK_LABEL = i18n.msg("calendar_group.new_link", "New link")
CALENDAR_PRIVATE_NOTE = i18n.msg(
    "calendar_group.private_link_never_shown_again", "Private link, never shown again")
CALENDAR_URL_PLACEHOLDER = i18n.msg(
    "calendar_group.https_or_webcal", "https:// or webcal://…")
CALENDAR_URL_HINT = i18n.msg(
    "calendar_group.the_private_ical_link_it_stays_on_the_server",
    "The private iCal link. It stays on the server and is never shown again.")
CALENDAR_REPLACE_HINT = i18n.msg(
    "calendar_group.the_old_link_stays_active_until_the_new_one",
    "The old link stays active until the new one has answered.")
# Shown in the connect sheet only. Shares its "no surveillance verb"
# discipline with companion.settings.form's vocabulary note.
CALENDAR_HOW_IT_WORKS_BODY = i18n.msg(
    "calendar_group.only_colours_a_flight_already_on_screen",
    "Only colours a flight already on screen; does not track or announce "
    "anything. Applies at the frame's next wake.")
CALENDAR_ERROR_INVALID = i18n.msg(
    "calendar_group.that_isn_t_a_calendar_link",
    "That isn't a calendar link: it must start with https:// or webcal://.")
CALENDAR_ERROR_UNREACHABLE = i18n.msg(
    "calendar_group.that_link_doesn_t_answer_nothing_was_changed",
    "That link doesn't answer. Nothing was changed.")
CALENDAR_CLOSE_LABEL = i18n.msg("calendar_group.close", "Close")
CALENDAR_DISCONNECT_BUTTON_TEXT = i18n.msg("calendar_group.disconnect", "Disconnect")
CALENDAR_CONFIRM_HEADING_TEMPLATE = i18n.msg(
    "calendar_group.disconnect_provider", "Disconnect %s?")
CALENDAR_CONFIRM_BODY = i18n.msg(
    "calendar_group.the_link_and_the_flights_it_supplied_are_deleted",
    "The link and the flights it supplied are deleted from the server. "
    "To reconnect, paste the link again.")

CALENDAR_DISCONNECT_FORM_ID = "calendar-disconnect-form"

# The dedicated disconnect route's own confirm gate — the single
# definition site the markup, the sheet script and the handler all read.
# Deliberately a different field name from calendar_disconnect: this
# field means "the confirmation step passed", that one meant "the
# checkbox was ticked".
CALENDAR_DISCONNECT_CONFIRM_FIELD = "confirm"
CALENDAR_DISCONNECT_CONFIRM_VALUE = "yes"


# What a no-JS browser sees instead of the in-sheet confirmation, on the
# server-rendered two-step confirmation page. Owned by
# companion/i18n_fr/display.py.
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


# A shape bound against an absurd paste, not a definition of an
# acceptable URL. The arbiter of whether a URL is acceptable stays the
# server-side safety gate and the fetch itself.
CALENDAR_URL_MAX_LEN = 2048

# The age past which a connected feed reads "Out of date": the server's
# own constant, shared so the page and the poll can never disagree.
CALENDAR_STALE_AFTER_S = calendar_rules.CALENDAR_STALE_AFTER_S

# A failed fetch records its attempt before the fetch runs, and a
# successful one stamps `last_synced_at` at second precision, so the two
# differ by up to the fetch deadline on success. Beyond this slack an
# attempt newer than the last success means the last fetch failed.
_ATTEMPT_SLACK_S = 60

# Hosts whose provider name reads better than the host itself, matched on
# the registrable suffix. Anything else shows its own host.
_PROVIDER_SUFFIXES = (
    ("icloud.com", "iCloud"),
    ("google.com", "Google Calendar"),
    ("outlook.com", "Outlook"),
    ("office365.com", "Outlook"),
    ("live.com", "Outlook"),
)

_CALENDAR_ICON_SVG = (
    '<svg class="calendar-status__icon" width="22" height="22" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<rect x="3.5" y="5" width="17" height="15" rx="2.5"></rect>'
    '<path d="M3.5 10h17M8 3.2v3.6M16 3.2v3.6"></path></svg>')


def _host_of(url):
    """The host of a stored feed URL, or "" on any failure — never the
    path, query, fragment or userinfo. A real `urlsplit()` parse rather
    than a byte-offset truncation: a naive `url[:20]` could leak leading
    path or token characters from a short host."""
    if not url:
        return ""
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def _masked_calendar_url(url):
    """host + "…" — never the path, query, fragment or userinfo of the
    stored calendar feed URL. "" on any failure (falsy url, unparsable,
    empty host); the caller omits the line entirely rather than
    fabricate one. This and `_provider_name()` are the only places in
    the module that read a stored secret URL back for display.
    """
    try:
        netloc = urlsplit(url).netloc if url else ""
    except ValueError:
        return ""
    return "%s…" % netloc if netloc else ""


def _provider_name(url):
    """"iCloud" for an iCloud feed, the host itself for one this module
    does not recognise, "" when no host can be read."""
    host = _host_of(url).lower()
    for suffix, name in _PROVIDER_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return name
    return _host_of(url)


# status keys -> (pill text, dot state). The dot is never green beside a
# failing or stale verdict: only "ok" uses the ok tone.
_STATE_PILLS = {
    "ok": (CALENDAR_STATUS_CONNECTED_VERDICT, "ok"),
    "zero": (CALENDAR_PILL_CHECK, "warn"),
    "pending": (CALENDAR_PILL_WAITING, "warn"),
    "stale": (CALENDAR_PILL_STALE, "warn"),
    "failed": (CALENDAR_PILL_ERROR, "error"),
    "ignored": (CALENDAR_PILL_IGNORED, "error"),
    "none": (CALENDAR_STATUS_NOT_CONNECTED_VERDICT, "off"),
    # A stored read time that cannot be parsed: connected, but nothing
    # honest to say about it, so a neutral dot and no detail.
    "unknown": (CALENDAR_STATUS_CONNECTED_VERDICT, "off"),
}


def calendar_state(configured, drift, last_synced_at, last_attempt_at, now, entry_count):
    """The one state key the status row renders: "none", "ignored"
    (drifted secret file), "pending" (saved, never read), "unknown"
    (an unparseable stored read time), "failed", "stale", "zero" or "ok". Derived from fields the registry already
    persists; the same value drives the pill, the detail line and the
    page's `data-calendar-state`.

    Drift is checked before `configured`, since a drifted link already
    forces it False. A last success older than `CALENDAR_STALE_AFTER_S`
    is "stale" whatever the attempts say; a newer failed attempt inside
    that window is "failed"; a clean read with no flights is "zero" and
    never reads as plain connected.
    """
    if drift:
        return "ignored"
    if not configured:
        return "none"
    age = layout.age_seconds(last_synced_at, now) if last_synced_at else None
    synced = layout.parse_iso(last_synced_at) if age is not None else None
    if synced is None:
        if last_attempt_at is not None:
            return "failed"
        return "unknown" if last_synced_at else "pending"
    if age > CALENDAR_STALE_AFTER_S:
        return "stale"
    if last_attempt_at is not None and last_attempt_at - synced.timestamp() > _ATTEMPT_SLACK_S:
        return "failed"
    return "zero" if not entry_count else "ok"


def _status_detail_html(state, last_synced_at, now, entry_count):
    """The one-line detail for `state`, escaped, with the age as a live
    `<time data-relative>` where the line has one."""
    age_html = layout.relative_time_html(last_synced_at, now) if last_synced_at else ""
    if state == "ok":
        if entry_count == 1:
            return escape_html(i18n.t(CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE)) % (age_html,)
        return escape_html(i18n.t(CALENDAR_STATUS_DETAIL_TEMPLATE)) % (entry_count, age_html)
    if state == "zero":
        return escape_html(i18n.t(CALENDAR_STATUS_ZERO_TEMPLATE)) % (age_html,)
    if state == "stale":
        return escape_html(i18n.t(CALENDAR_STATUS_STALE_TEMPLATE)) % (age_html,)
    if state == "failed":
        if age_html and layout.parse_iso(last_synced_at) is not None:
            return escape_html(i18n.t(CALENDAR_STATUS_FAILED_TEMPLATE)) % (age_html,)
        return escape_html(i18n.t(CALENDAR_STATUS_FETCH_FAILED_DETAIL))
    if state == "pending":
        return escape_html(i18n.t(CALENDAR_STATUS_PENDING_DETAIL))
    if state == "ignored":
        return escape_html(i18n.t(CALENDAR_STATUS_PERMISSION_UNSAFE))
    if state == "unknown":
        return ""
    return escape_html(i18n.t(CALENDAR_NONE_LEAD))


def _status_title_html(state, title):
    """The one status line: whether the calendar's flights are shown, then
    the calendar's name when one is connected, then the verdict pill for any
    state that is not simply on or off."""
    pill_text, tone = _STATE_PILLS[state]
    dot_class = layout._STATUS_DOT_CLASSES.get(tone, layout._DEFAULT_STATUS_DOT_CLASS)
    is_on = state not in ("none", "ignored")
    lead = i18n.t(CALENDAR_FLIGHTS_ON_TEXT if is_on else CALENDAR_FLIGHTS_OFF_TEXT)
    name_html = " <b>%s</b>" % escape_html(title) if is_on else ""
    pill_html = "" if state == "none" else (
        '<span class="banner__pill calendar-status__pill"><span class="dot %s" '
        'aria-hidden="true"></span>%s</span>') % (dot_class, escape_html(i18n.t(pill_text)))
    return '<p class="calendar-status__title"><span class="calendar-status__lead">%s%s</span>%s%s</p>' % (
        escape_html(lead), "," if is_on else "", name_html, pill_html)


def _status_row_html(state, title, detail_html):
    """The page's whole calendar connection UI: tile, the status line, one
    detail line and the one "Choose calendar" button opening the sheet. The
    pill carries the verdict in words (never the dot's colour alone). With
    nothing connected the detail is the empty state's body instead."""
    not_connected = state == "none"
    button_class = "calendar-manage" + (" calendar-manage--primary" if not_connected else "")
    tile_class = "calendar-status__tile" + (" calendar-status__tile--empty" if not_connected else "")
    detail = "" if not_connected else '<p class="calendar-status__detail">%s</p>' % detail_html
    return (
        '<div class="calendar-status" data-calendar-state="%s">'
        '<span class="%s">%s</span>'
        '<div class="calendar-status__main">%s%s</div>'
        '<a class="%s" href="%s">%s</a>'
        "</div>"
    ) % (
        state, tile_class, _CALENDAR_ICON_SVG, _status_title_html(state, title), detail,
        button_class, escape_html(device_scope.scoped(layout.DISPLAY_CALENDAR_CONNECT_ROUTE)),
        escape_html(i18n.t(CALENDAR_CONNECT_ADD_TEXT if not_connected else CALENDAR_CHOOSE_TEXT)))


def _url_form_html(connected, error_message):
    """The paste-or-replace form: write-only field (never a `value`
    attribute), its hint and its inline error. Its submit button is in the
    page's floating bar (`form=`). The pending label travels as a data
    attribute on that button so the script carries no copy."""
    hint_id = "calendar-url-hint"
    error_id = "calendar-connect-url-error"
    describedby = hint_id + (" " + error_id if error_message else "")
    invalid = ' aria-invalid="true"' if error_message else ""
    error_html = (
        '<p class="field-error text-label" id="%s" role="alert">%s</p>'
        % (error_id, escape_html(i18n.t(error_message)))) if error_message else ""
    label = CALENDAR_NEW_LINK_LABEL if connected else CALENDAR_LINK_LABEL
    hint = CALENDAR_REPLACE_HINT if connected else CALENDAR_URL_HINT
    how_html = "" if connected else (
        '<p class="text-label form-page__note">%s</p>'
        % escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)))
    return (
        '<form class="form-page__section" id="%s" method="post" action="%s" data-calendar-connect>'
        '<label for="calendar-connect-url" class="form-page__label">%s</label>'
        '<input type="text" id="calendar-connect-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%d" placeholder="%s" '
        'aria-describedby="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>%s%s</form>'
    ) % (
        CONNECT_FORM_ID, device_scope.scoped(CALENDAR_CONNECT_ROUTE, "POST"),
        escape_html(i18n.t(label)), CALENDAR_URL_MAX_LEN,
        escape_html(i18n.t(CALENDAR_URL_PLACEHOLDER)), describedby, invalid,
        hint_id, escape_html(i18n.t(hint)), error_html, how_html)


def _disconnect_html(provider):
    """The quiet red Disconnect link and its confirmation dialog. The dialog
    posts the confirm value the route requires; a browser without scripts
    reaches the same dialog through the link's hash, and a bare POST still
    lands on the server's own confirmation page. The server stays the gate
    either way."""
    heading = (
        i18n.t(CALENDAR_CONFIRM_HEADING_TEMPLATE) % provider if provider
        else i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING))
    body = '<p>%s</p><input type="hidden" name="%s" value="%s">' % (
        escape_html(i18n.t(CALENDAR_CONFIRM_BODY)), CALENDAR_DISCONNECT_CONFIRM_FIELD,
        escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE))
    return (
        '<div class="form-page__section form-page__section--danger">%s%s</div>'
    ) % (
        ui_modal.trigger_html(
            DISCONNECT_DIALOG_ID, escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT)),
            "form-page__danger"),
        ui_modal.dialog_html(
            DISCONNECT_DIALOG_ID, heading,
            device_scope.scoped(CALENDAR_DISCONNECT_ROUTE, "POST"), csrf_field(), body,
            i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT), i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT),
            device_scope.scoped(layout.DISPLAY_CALENDAR_CONNECT_ROUTE),
            destructive=True, confirm_only=True))


def _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """Calendar's connection block inside the Calendar row: the empty state
    while nothing is connected, then the one status row whose button opens
    the connection page. Returns the block's HTML."""
    secret_url = (
        calendar_rules.configured_calendar_url(state_dir) if (configured and state_dir) else "")
    provider = _provider_name(secret_url)
    masked_url = _masked_calendar_url(secret_url)
    state = calendar_state(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count)
    title = provider or masked_url or i18n.t(CALENDAR_LINK_LABEL)
    empty_html = ui_components.empty_state(
        i18n.t(CALENDAR_EMPTY_HEADING), i18n.t(CALENDAR_NONE_LEAD), compact=True
    ) if state == "none" else ""
    return empty_html + _status_row_html(state, title, _status_detail_html(
        state, last_synced_at, now, entry_count))


def connect_page_html(configured, drift, state_dir, error_message):
    """The calendar connection page body: one card titled for the task
    (Connect a calendar). Returns (markup, title, submit label); the page's
    floating bar carries the submit. The full feed URL is never in this markup: only the masked host."""
    secret_url = (
        calendar_rules.configured_calendar_url(state_dir) if (configured and state_dir) else "")
    provider = _provider_name(secret_url)
    masked_url = _masked_calendar_url(secret_url)
    title = (
        i18n.t(CALENDAR_SHEET_TITLE_TEMPLATE) % provider if configured and provider
        else i18n.t(CALENDAR_SHEET_CONNECT_TITLE))
    link_html = ""
    if configured and masked_url:
        link_html = (
            '<div class="form-page__section"><p class="form-page__label">%s</p>'
            '<p class="calendar-masked-url">%s</p>'
            '<p class="text-label section-caption">%s</p></div>'
        ) % (escape_html(i18n.t(CALENDAR_LINK_LABEL)), escape_html(masked_url),
             escape_html(i18n.t(CALENDAR_PRIVATE_NOTE)))
    disconnect_html = _disconnect_html(provider) if (configured or drift) else ""
    markup = (
        '<div class="form-page"><div class="form-page__card">'
        '<h2 class="form-page__title">%s</h2>%s%s%s</div></div>'
    ) % (escape_html(title), link_html,
         _url_form_html(configured, error_message), disconnect_html)
    return markup, title, i18n.t(
        CALENDAR_REPLACE_BUTTON_TEXT if configured else CALENDAR_CONNECT_BUTTON_TEXT)


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
        '<input type="hidden" name="%s" value="%s">%s'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_SENTENCE)),
        device_scope.scoped(CALENDAR_DISCONNECT_ROUTE, "POST"),
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        csrf_field(), escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT)),
        device_scope.scoped(layout.DISPLAY_CALENDAR_ROUTE),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
    )


CALENDAR_TAG = i18n.msg("look.calendar", "Calendar")
CALENDAR_ROW_TITLE = i18n.msg("look.flights_in_your_calendar", "Look of calendar flights")


def special_mini_html(theme_id, opener_label=None, layout_id=None):
    """The small framed render every Special looks row leads with. With
    `opener_label`, a script-revealed button over it opens the look
    sheet for that row. `layout_id` makes the picture the frame's layout.
    """
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_SMALL]
    opener_html = ""
    if opener_label is not None:
        opener_html = (
            '<button type="button" class="look-frame__open" data-look-open hidden '
            'aria-haspopup="dialog" aria-label="%s"></button>' % escape_html(opener_label))
    return (
        '<span class="special-row__mini">'
        '<img class="special-row__image" data-look-image src="%s" width="%d" height="%d" alt="">'
        "%s</span>"
    ) % (
        escape_html(theme_preview.frame_preview_src(
            theme_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
            theme_preview.FRAME_PREVIEW_SIZE_SMALL, layout=layout_id)),
        width, height, opener_html)


def calendar_special_row_html(
        departures_safe_id, current_calendar_theme_id, configured, drift,
        last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None, layout_id=None):
    """The calendar row of the Calendar list: a mini render of the look
    calendar flights get, its read-back and a "Change" link to the page that
    edits that look, preceded by the one-line connection status with its
    "Choose calendar" link. Returns the row's HTML; the connection verdict
    lives in that status line only, never repeated in the row's meta. On a
    giant layout the look is named by its pairing and pictured in that layout.
    """
    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    same_checked = not effective_calendar
    picture_id = (
        departures_safe_id if same_checked or effective_calendar not in device_config.THEMES
        else effective_calendar)
    sentence = i18n.t(SAME_AS_DEPARTURES_LABEL) if same_checked else layout_picker.look_label(picture_id, layout_id)
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_CALENDAR])
    connection_html = _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=errors, submitted=submitted, state_dir=state_dir)
    change_html = (
        '<a class="special-row__edit" href="%s" aria-label="%s">%s</a>'
    ) % (
        escape_html(device_scope.scoped(layout.DISPLAY_CALENDAR_LOOK_ROUTE)),
        escape_html(i18n.t(LOOK_CHANGE_ARIA_TEMPLATE) % usage_label),
        escape_html(i18n.t(LOOK_CHANGE_LABEL)))
    return (
        '<li class="special-row special-row--calendar" id="calendar-row">'
        "%s"
        '<div class="special-row__main">%s'
        '<div class="special-row__text">'
        '<p class="special-row__title"><span class="special-row__tag">%s</span>%s</p>'
        '<p class="special-row__meta"><span>%s</span></p>'
        '</div><div class="special-row__actions">%s</div></div>'
        "</li>"
    ) % (
        connection_html, special_mini_html(picture_id, layout_id=layout_picker.preview_layout(layout_id)),
        escape_html(i18n.t(CALENDAR_TAG)), escape_html(i18n.t(CALENDAR_ROW_TITLE)),
        escape_html(sentence), change_html)


def look_page_html(
        calendar_value, departures_id, errors, form_id, post_route, hidden_html, layout_id=None,
        submitted=None):
    """The page that edits the calendar's look: the live picture and the
    picker (with a script) or the colour x style table of native radios
    (without), plus a "Same as departures" choice. One form posting to the
    settings route with the `calendar_theme_id` field only. On a giant layout
    the picker is "Same as departures" and the five pairing cards instead.
    Returns (markup, title)."""
    title = i18n.t(LOOK_SHEET_TITLES[COLOUR_USAGE_CALENDAR])
    if layout_picker.offers_pairings(layout_id):
        return (
            '<form class="look-page look-pairing-view" id="%s" method="post" action="%s" '
            'data-calendar-look>%s%s</form>'
        ) % (
            escape_html(form_id), escape_html(device_scope.scoped(post_route, "POST")),
            hidden_html,
            layout_picker.calendar_look_html(layout_id, calendar_value, errors, submitted)), title
    frame = look_frame_html(
        COLOUR_USAGE_CALENDAR, calendar_value, departures_id, errors,
        theme_preview.FRAME_PREVIEW_STATE_DEPARTING, carries_departures=True)
    markup = (
        '<form class="look-page" id="%s" method="post" action="%s" data-calendar-look>%s'
        '<div class="look-view" data-look-initial="%s"><div class="look-stage">'
        '<div class="look-panel" data-look-panel="%s">%s</div></div>'
        '<div class="look-picker js-gate">%s</div></div></form>'
    ) % (
        escape_html(form_id), escape_html(device_scope.scoped(post_route, "POST")),
        hidden_html, COLOUR_USAGE_CALENDAR, COLOUR_USAGE_CALENDAR, frame,
        look_sheet_html(inline=True))
    return markup, title
