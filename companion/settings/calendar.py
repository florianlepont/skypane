"""The Calendar settings group: the one-line connection status row on the
Display page, the "Manage" sheet that holds every control (paste or
replace the link, disconnect), the two-step disconnect confirmation page,
and the calendar row of the look card's Special looks list (built here so
`companion.settings.theme` stays independent of this module — see that
module's own docstring for why).

The page keeps one compact row and one button; the sheet is a single
`<dialog>`. Scripts-blocked, the same markup renders open in the page
(`?calendar=manage#calendar-sheet`); `companion/static/calendar-sheet.js`
upgrades it to a modal and adds the pending label and the in-sheet
disconnect confirmation.
"""
from urllib.parse import urlsplit

from companion import i18n
import companion.layout as layout
from companion.layout import escape_html
import companion.page_context as page_context
from server import device_config
from server.plane import calendar_rules

from companion import theme_preview
from companion.settings import look
from companion.settings.form import _field_error_html, _submitted_or_current
from companion.settings.theme import (
    COLOUR_USAGE_CALENDAR, FRAME_COLOURS_ROW_LABELS, LOOK_CHANGE_ARIA_TEMPLATE,
    LOOK_SHEET_TITLES, SAME_AS_DEPARTURES_LABEL, look_edit_html, look_target_attrs)


# An immediate, session-gated POST outside SETTINGS_ROUTE and the
# settings form's dirty bar: a one-step act, not a pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"
CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"

# The sheet's no-script address and anchor; companion/pages/config_page.py
# owns the same strings for the redirect side.
SHEET_ID = "calendar-sheet"
SHEET_PARAM = "calendar"
SHEET_MANAGE = "manage"
ROW_ID = "calendar-row"


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

CALENDAR_NONE_TITLE = i18n.msg("calendar_group.no_calendar", "No calendar")
CALENDAR_NONE_LEAD = i18n.msg(
    "calendar_group.colour_the_flights_from_your_calendar_on_screen",
    "Colour the flights from your calendar on screen.")
CALENDAR_MANAGE_TEXT = i18n.msg("calendar_group.manage", "Manage")
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


def _sheet_href(fragment=SHEET_ID):
    """The no-script address of the sheet (the page with the sheet open)."""
    return "%s?%s=%s#%s" % (layout.DISPLAY_ROUTE, SHEET_PARAM, SHEET_MANAGE, fragment)


def _status_row_html(state, title, detail_html):
    """The page's whole calendar connection UI: tile, provider, status
    pill, one-line detail and one button. The pill carries the verdict in
    words (never the dot's colour alone)."""
    pill_text, tone = _STATE_PILLS[state]
    dot_class = layout._STATUS_DOT_CLASSES.get(tone, layout._DEFAULT_STATUS_DOT_CLASS)
    connecting = state == "none"
    button_class = "calendar-manage" + (" calendar-manage--primary" if connecting else "")
    button_text = CALENDAR_CONNECT_BUTTON_TEXT if connecting else CALENDAR_MANAGE_TEXT
    tile_class = "calendar-status__tile" + (" calendar-status__tile--empty" if connecting else "")
    return (
        '<div class="calendar-status" data-calendar-state="%s">'
        '<span class="%s">%s</span>'
        '<div class="calendar-status__main">'
        '<p class="calendar-status__title"><b>%s</b>'
        '<span class="banner__pill calendar-status__pill"><span class="dot %s" aria-hidden="true">'
        "</span>%s</span></p>"
        '<p class="calendar-status__detail">%s</p></div>'
        '<a class="%s" href="%s" data-calendar-open aria-haspopup="dialog">%s</a>'
        "</div>"
    ) % (
        state, tile_class, _CALENDAR_ICON_SVG, escape_html(title), dot_class,
        escape_html(i18n.t(pill_text)), detail_html, button_class, escape_html(_sheet_href()),
        escape_html(i18n.t(button_text)))


def _url_form_html(connected, error_message):
    """The paste-or-replace form: write-only field (never a `value`
    attribute), its hint, its inline error and the submit. The pending
    label travels as a data attribute so the script carries no copy."""
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
        '<p class="text-label calendar-sheet__note">%s</p>'
        % escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)))
    return (
        '<form class="calendar-sheet__form" method="post" action="%s" data-calendar-connect>'
        '<div class="calendar-sheet__field">'
        '<label for="calendar-connect-url">%s</label>'
        '<input type="text" id="calendar-connect-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%d" placeholder="%s" '
        'aria-describedby="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>%s%s</div>'
        '<div class="calendar-sheet__foot">'
        '<a class="calendar-sheet__cancel" href="%s" data-calendar-close>%s</a>'
        '<button type="submit" data-pending-label="%s">%s</button></div>'
        "</form>"
    ) % (
        CALENDAR_CONNECT_ROUTE, escape_html(i18n.t(label)), CALENDAR_URL_MAX_LEN,
        escape_html(i18n.t(CALENDAR_URL_PLACEHOLDER)), describedby, invalid,
        hint_id, escape_html(i18n.t(hint)), error_html, how_html,
        escape_html("%s#%s" % (layout.DISPLAY_ROUTE, ROW_ID)),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
        escape_html(i18n.t(CALENDAR_CHECKING_TEXT)),
        escape_html(i18n.t(CALENDAR_REPLACE_BUTTON_TEXT if connected
                           else CALENDAR_CONNECT_BUTTON_TEXT)))


def _disconnect_html(provider):
    """The quiet red Disconnect action and its in-sheet confirmation. The
    form posts an empty confirm field: scripts-blocked, the server renders
    its own confirmation page; the script instead reveals the (hidden)
    confirmation inside the sheet and only a click there posts the real
    confirm value. The server stays the gate either way."""
    return (
        '<div class="calendar-sheet__disconnect">'
        '<form id="%s" method="post" action="%s" data-calendar-disconnect '
        'data-confirm-value="%s">'
        '<input type="hidden" name="%s" value="" data-confirm-field>'
        '<button type="submit" class="calendar-danger">%s</button></form>'
        '<div class="calendar-sheet__confirm" data-calendar-confirm role="alertdialog" '
        'aria-labelledby="calendar-confirm-heading" hidden>'
        '<p class="calendar-sheet__confirm-heading" id="calendar-confirm-heading">%s</p>'
        '<p class="text-body">%s</p>'
        '<div class="calendar-sheet__foot">'
        '<button type="button" data-calendar-confirm-cancel>%s</button>'
        '<button type="button" class="calendar-danger calendar-danger--solid" '
        'data-calendar-confirm-yes>%s</button></div></div></div>'
    ) % (
        CALENDAR_DISCONNECT_FORM_ID, CALENDAR_DISCONNECT_ROUTE,
        escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE), CALENDAR_DISCONNECT_CONFIRM_FIELD,
        escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT)),
        escape_html(
            i18n.t(CALENDAR_CONFIRM_HEADING_TEMPLATE) % provider if provider
            else i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING)),
        escape_html(i18n.t(CALENDAR_CONFIRM_BODY)),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
        escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT)))


def _sheet_html(configured, drift, provider, masked_url, is_open, error_message):
    """The "Manage" dialog. Closed it renders nothing; open (the no-script
    `?calendar=manage` address, or a refused paste) it is an in-page card
    that the script promotes to a modal. The full feed URL is never in
    this markup: only the masked host."""
    title = (
        i18n.t(CALENDAR_SHEET_TITLE_TEMPLATE) % provider if configured and provider
        else i18n.t(CALENDAR_SHEET_CONNECT_TITLE))
    link_html = ""
    if configured and masked_url:
        link_html = (
            '<div class="calendar-sheet__link"><p class="calendar-sheet__label">%s</p>'
            '<p class="calendar-masked-url">%s</p>'
            '<p class="text-label section-caption">%s</p></div>'
        ) % (escape_html(i18n.t(CALENDAR_LINK_LABEL)), escape_html(masked_url),
             escape_html(i18n.t(CALENDAR_PRIVATE_NOTE)))
    disconnect_html = _disconnect_html(provider) if (configured or drift) else ""
    return (
        '<dialog class="calendar-sheet" id="%s" aria-labelledby="calendar-sheet-title" '
        'data-calendar-sheet%s%s>'
        '<div class="calendar-sheet__head">'
        '<p class="calendar-sheet__title" id="calendar-sheet-title">%s</p>'
        '<a class="calendar-sheet__close" href="%s" data-calendar-close aria-label="%s">'
        '<span aria-hidden="true">×</span></a></div>'
        "%s%s%s</dialog>"
    ) % (
        SHEET_ID, " open" if is_open else "",
        ' data-calendar-error="1"' if error_message else "",
        escape_html(title), escape_html("%s#%s" % (layout.DISPLAY_ROUTE, ROW_ID)),
        escape_html(i18n.t(CALENDAR_CLOSE_LABEL)),
        link_html, _url_form_html(configured, error_message), disconnect_html)


def _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None, sheet_open=False, sheet_error=None):
    """Calendar's connection block inside the look card's Calendar row:
    the one status row and the Manage dialog. Returns the block's HTML.

    The feed URL is write-only: never a `value` attribute, never a
    reveal or copy control; the sheet shows only `host…`. `sheet_error`
    is one of the redirect side's fixed codes ("invalid"/"unreachable"),
    `errors` the settings POST's own field errors.
    """
    secret_url = (
        calendar_rules.configured_calendar_url(state_dir) if (configured and state_dir) else "")
    provider = _provider_name(secret_url)
    masked_url = _masked_calendar_url(secret_url)
    state = calendar_state(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count)
    if state == "none":
        title = i18n.t(CALENDAR_NONE_TITLE)
    else:
        title = provider or masked_url or i18n.t(CALENDAR_LINK_LABEL)
    error_message = (errors or {}).get("calendar_url")
    if not error_message:
        error_message = {
            "invalid": CALENDAR_ERROR_INVALID, "unreachable": CALENDAR_ERROR_UNREACHABLE,
        }.get(sheet_error)
    return (
        _status_row_html(state, title, _status_detail_html(
            state, last_synced_at, now, entry_count))
        + _sheet_html(
            configured, drift, provider, masked_url,
            sheet_open or bool(error_message), error_message))


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


CALENDAR_TAG = i18n.msg("look.calendar", "Calendar")
CALENDAR_ROW_TITLE = i18n.msg("look.flights_in_your_calendar", "Flights in your calendar")


def special_mini_html(theme_id, opener_label=None):
    """The small framed render every Special looks row leads with. With
    `opener_label`, a script-revealed button over it opens the look
    sheet for that row.
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
            theme_preview.FRAME_PREVIEW_SIZE_SMALL)),
        width, height, opener_html)


def calendar_special_row_html(
        departures_safe_id, current_calendar_theme_id, configured, drift,
        last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None, sheet_open=False, sheet_error=None):
    """The calendar row of the Special looks list: a mini render of the
    look calendar flights get, its read-back, the "Change" control (the
    colour x style table, with "Same as departures" first), and below it
    the one-line connection status with its Manage sheet. Returns the
    row's HTML; the connection verdict lives in that status line only,
    never repeated in the row's meta.
    """
    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    same_checked = not effective_calendar
    picture_id = (
        departures_safe_id if same_checked or effective_calendar not in device_config.THEMES
        else effective_calendar)
    sentence = i18n.t(SAME_AS_DEPARTURES_LABEL) if same_checked else look.look_sentence(picture_id)
    usage_label = i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_CALENDAR])
    small = theme_preview.FRAME_PREVIEW_SIZE_SMALL
    table_html = look.look_table_html(
        "calendar_theme_id", "" if same_checked else effective_calendar, usage_label,
        lambda theme_id: theme_preview.frame_preview_src(
            theme_id, theme_preview.FRAME_PREVIEW_STATE_DEPARTING, small),
        leading_html=look.same_option_html(
            "calendar_theme_id", same_checked, i18n.t(SAME_AS_DEPARTURES_LABEL)))
    connection_html = _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=errors, submitted=submitted, state_dir=state_dir,
        sheet_open=sheet_open, sheet_error=sheet_error)
    row_html = (
        '<li class="special-row special-row--calendar" id="calendar-row" data-look-anchor%s>'
        '<div class="special-row__main">%s'
        '<div class="special-row__text">'
        '<p class="special-row__title"><span class="special-row__tag">%s</span>%s</p>'
        '<p class="special-row__meta"><span data-look-sentence>%s</span></p>'
        "</div>%s</div>%s%s"
        "</li>"
    ) % (
        look_target_attrs(
            COLOUR_USAGE_CALENDAR, "calendar_theme_id", theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
            small, True, title=i18n.t(LOOK_SHEET_TITLES[COLOUR_USAGE_CALENDAR])),
        special_mini_html(picture_id, opener_label=i18n.t(LOOK_CHANGE_ARIA_TEMPLATE) % usage_label),
        escape_html(i18n.t(CALENDAR_TAG)), escape_html(i18n.t(CALENDAR_ROW_TITLE)),
        escape_html(sentence),
        look_edit_html(COLOUR_USAGE_CALENDAR, table_html, icon_only=True),
        _field_error_html(errors, "calendar_theme_id", "calendar-theme"),
        connection_html,
    )
    return row_html
