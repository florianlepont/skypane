"""The Update page: firmware release status, version history, and the
Install/Cancel action markup.

The running version, the update state, a rollback warning and the
version history are driven entirely by `server.firmware_registry.
update_view()` (`update_page()`/`render()`). `update_install_confirm_page()`
is the real, server-side install-confirmation gate -- `companion/app.py`'s
`_handle_update_install_post()`/`_handle_update_cancel_post()` are the
live POST handlers for the forms this module renders.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
import companion.page_context as page_context
import companion.wake as wake
from server import firmware_registry
from server import history_db

# Named here once, so the per-row/Cancel forms below, companion/app.py's
# POST handlers and this module's own tests share one definition rather
# than retyping the literal path.
INSTALL_ROUTE = "/update/install"
CANCEL_ROUTE = "/update/cancel"

# Shares its id with companion/ui_base.py's own nav-label Message, the
# same pattern companion/pages/health_page.py's _NAV_HEALTH_TEXT uses:
# msg() is idempotent for a repeat id/English pair, and this page's own
# <h1> heading must read exactly what the nav calls it.
_NAV_UPDATE_TEXT = i18n.msg("nav.update", "Update")

STATUS_HEADING_TEXT = i18n.msg("update.status", "Status")
HISTORY_HEADING_TEXT = i18n.msg("update.version_history", "Version history")

RUNNING_LABEL_TEMPLATE = i18n.msg("update.running_s", "Running %s")
NO_VERSION_REPORTED_TEXT = i18n.msg(
    "update.no_version_reported_yet", "No version reported yet")

# The five update-state words, mapped through layout._STATUS_DOT_CLASSES'
# own four tokens (ok/warn/error/off) -- no new colour, per the UI
# contract's own accent-reservation check.
STATE_LABELS = {
    "available": i18n.msg("update.available", "Available"),
    "scheduled": i18n.msg("update.scheduled", "Scheduled"),
    "in_progress": i18n.msg("update.in_progress", "In progress"),
    "installed": i18n.msg("update.installed", "Installed"),
    "failed": i18n.msg("update.failed", "Failed"),
}
_STATE_DOT_TOKENS = {
    "available": "off",
    "scheduled": "off",
    "in_progress": "warn",
    "installed": "ok",
    "failed": "error",
}

UNKNOWN_TIME_TEXT = i18n.msg("update.unknown_time", "an unknown time")
SCHEDULED_SENTENCE_TEMPLATE = i18n.msg(
    "update.scheduled_installs_at_the_next_wake_around_s",
    "Scheduled — installs at the next wake, around %s.")
ROLLBACK_SENTENCE_TEMPLATE = i18n.msg(
    "update.firmware_rolled_back",
    "Firmware rolled back — the update to %s failed on trial boot; "
    "the frame is back on %s.")

CANCEL_BUTTON_TEXT = i18n.msg("update.cancel", "Cancel")
INSTALL_BUTTON_TEXT = i18n.msg("update.install", "Install")
NOT_INSTALLABLE_TEXT = i18n.msg("update.not_installable", "Not installable")
INSTALL_CONFIRM_QUESTION_TEMPLATE = i18n.msg(
    "update.install_s_now",
    "Install %s now? It will apply at the next wake.")

# The server-side confirmation page's own copy (the real install gate,
# not the data-confirm misclick guard above) -- companion/app.py's
# _handle_update_install_post() interpolates the version/next-wake time.
INSTALL_CONFIRM_HEADING_TEMPLATE = i18n.msg(
    "update.install_firmware_s", "Install firmware %s?")
INSTALL_CONFIRM_SENTENCE_TEMPLATE = i18n.msg(
    "update.the_frame_will_download_and_install_this",
    "The frame will download and install this version at its next "
    "wake, around %s. It will keep the update after one successful "
    "check-in — otherwise it rolls back automatically.")

# The flash keys companion/app.py's install/cancel handlers redirect to
# on a non-"scheduled"/non-cancellable outcome or an exception -- the
# literal strings are defined here (this page's own module), matching
# companion/pages/config_page.py's/airlines_page.py's own FLASH_* keys;
# companion/flash.py re-exports them as FLASH_KEY_UPDATE_*.
FLASH_UPDATE_SCHEDULE_FAILED = "update_schedule_failed"
FLASH_UPDATE_CANCEL_FAILED = "update_cancel_failed"
# A distinct key for schedule_release()'s own "busy" outcome (an install
# is already in progress): the generic schedule-failed copy tells the
# operator to retry, which cannot succeed until the running install
# finishes -- a different failure needs different copy.
FLASH_UPDATE_BUSY = "update_busy"
FLASH_UPDATE_SCHEDULE_FAILED_TEXT = i18n.msg(
    "update.couldn_t_schedule_that_update_please_try_again",
    "Couldn't schedule that update — please try again.")
FLASH_UPDATE_CANCEL_FAILED_TEXT = i18n.msg(
    "update.couldn_t_cancel_the_frame_may_have_already",
    "Couldn't cancel — the frame may have already started.")
FLASH_UPDATE_BUSY_TEXT = i18n.msg(
    "update.an_update_is_already_installing_wait",
    "An update is already installing — wait for it to finish.")

TABLE_HEADER_VERSION_TEXT = i18n.msg("update.version", "Version")
TABLE_HEADER_DATE_TEXT = i18n.msg("update.date", "Date")
TABLE_HEADER_NOTES_TEXT = i18n.msg("update.notes", "Notes")
TABLE_HEADER_INSTALLED_TEXT = i18n.msg("update.installed_column", "Installed")

EMPTY_RELEASES_HEADING_TEXT = i18n.msg("update.no_releases_yet", "No releases yet")
EMPTY_RELEASES_BODY_TEXT = i18n.msg(
    "update.publish_a_release",
    "Publish a release by pushing a fw-v* tag. It will appear here "
    "once CI finishes building and signing it.")

# The quiet/secondary button treatment companion/pages/history_page.py's
# Show-more control and the calendar-disconnect form already share --
# never the accent-styled primary, so Cancel and Install can never both
# read as the primary action on the same row.
_QUIET_BUTTON_CLASS = "calendar-disconnect-btn"


def _status_verdict_block_html(ctx, view):
    """The running-version verdict/detail pair, the top half of Card 1.

    RUNNING_LABEL_TEMPLATE ("Running %s") carries its own placeholder;
    the version itself renders as a separate `<span class="mono">`
    element rather than baked into the escaped sentence, matching the
    rest of this app's "interpolate the templated value as its own
    element" convention (see e.g. health_page.py's headline builders).
    """
    running_version = view.get("running_version")
    if not running_version:
        return (
            '<p class="text-body widget-verdict text-label">%s</p>'
            % escape_html(i18n.t(NO_VERSION_REPORTED_TEXT)))
    prefix_text = i18n.t(RUNNING_LABEL_TEMPLATE).split("%s", 1)[0]
    verdict_html = (
        '<p class="text-body widget-verdict">%s<span class="mono">%s</span></p>'
    ) % (escape_html(prefix_text), escape_html(running_version))
    detail_html = _timestamp_detail_html(view.get("reported_at"), ctx.now)
    return verdict_html + detail_html


def _timestamp_detail_html(ts, now):
    """A `.widget-detail` div for `ts`, or "" when `ts` is falsy.

    `concise_timestamp_html()`'s own default fallback is the hard-coded
    English literal "no reading yet" (battery-reading vocabulary, not a
    translated Message) -- wrong under an update state and never
    translated under French. Passing `fallback=""` and dropping the div
    entirely when there is nothing to show avoids both: a fresh install
    with no release published yet, or an in_progress state with no
    matching event, renders no detail line rather than a leaked English
    string.
    """
    if not ts:
        return ""
    timestamp_html = layout.concise_timestamp_html(ts, now, fallback="")
    if not timestamp_html:
        return ""
    return '<div class="widget-detail">%s</div>' % timestamp_html


# The states where "target_version" names a real, in-flight schedule --
# "available"/"installed" carry no schedule, so view["target_version"]
# is always None for them (server.firmware_registry.update_view()'s own
# contract); this tuple exists only for readability at the call site.
_STATES_WITH_A_TARGET_VERSION = ("scheduled", "in_progress", "failed")


def _target_version_html(view):
    """A mono span naming the version `view["target_version"]` points at,
    or "" with no schedule -- so the Scheduled/In progress/Failed state
    always says WHICH release, never just the bare state word. Reads the
    view's own field; re-derives no schedule rule.
    """
    state = view.get("state")
    target_version = view.get("target_version")
    if not target_version or state not in _STATES_WITH_A_TARGET_VERSION:
        return ""
    return ' <span class="mono">%s</span>' % escape_html(target_version)


def _status_state_row_html(ctx, view):
    state = view.get("state")
    state_label = i18n.t(STATE_LABELS.get(state, STATE_LABELS["available"]))
    dot_token = _STATE_DOT_TOKENS.get(state, "off")
    label_html = layout.status_dot(dot_token, state_label) + _target_version_html(view)
    detail_html = _timestamp_detail_html(view.get("state_at"), ctx.now)
    return (
        '<p class="text-body widget-verdict">%s</p>'
        "%s"
    ) % (label_html, detail_html)


def _scheduled_sentence_html(view, next_wake_text):
    if view.get("state") != "scheduled":
        return ""
    resolved_text = next_wake_text or i18n.t(UNKNOWN_TIME_TEXT)
    sentence = i18n.t(SCHEDULED_SENTENCE_TEMPLATE) % resolved_text
    return '<p class="text-label section-caption">%s</p>' % escape_html(sentence)


def _cancel_form_html(view):
    if not view.get("cancellable"):
        return ""
    return (
        '<form method="post" action="%s">'
        '<button type="submit" class="%s">%s</button>'
        "</form>"
    ) % (CANCEL_ROUTE, _QUIET_BUTTON_CLASS, escape_html(i18n.t(CANCEL_BUTTON_TEXT)))


def _rollback_banner_html(view):
    """A warn-toned `role="alert"` banner when the frame's last reported
    outcome is a rollback -- never the error colour: a completed,
    automatic rollback is the system working as designed, not a fault.
    """
    rollback = view.get("rollback")
    if not rollback:
        return ""
    version = rollback.get("version") or "?"
    back_on = rollback.get("back_on") or "?"
    text = i18n.t(ROLLBACK_SENTENCE_TEMPLATE) % (version, back_on)
    return '<div class="banner banner--warn" role="alert">%s</div>' % escape_html(text)


def _status_card_html(ctx, view, next_wake_text):
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s%s%s%s%s"
        "</section>"
    ) % (
        escape_html(i18n.t(STATUS_HEADING_TEXT)),
        _rollback_banner_html(view),
        _status_verdict_block_html(ctx, view),
        _status_state_row_html(ctx, view),
        _scheduled_sentence_html(view, next_wake_text),
        _cancel_form_html(view),
    )


def _install_form_html(version):
    confirm_question = i18n.t(INSTALL_CONFIRM_QUESTION_TEMPLATE) % version
    return (
        '<form method="post" action="%s" data-confirm="%s">'
        '<input type="hidden" name="version" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        INSTALL_ROUTE, escape_html(confirm_question),
        escape_html(version), escape_html(i18n.t(INSTALL_BUTTON_TEXT)),
    )


def _release_row(release, running_version, target_version, installs_blocked, now):
    """One `layout.data_table()` row for `release`: version (mono, plain
    text), date/installed/action (raw, already-safe markup), notes
    (plain text, escaped by data_table() itself since it is not in
    raw_columns -- CI-generated commit summaries are untrusted input).

    `target_version` is `view["target_version"]` -- the release a
    schedule already targets renders a quiet "Scheduled" label instead
    of a second, identical-looking Install button: the Status card's
    own state row already names this schedule's outcome, so an Install
    button on this row would only offer to schedule it again.

    `installs_blocked` is `view["state"] == "in_progress"`: the device
    has already acknowledged an offer, so `schedule_release()` can only
    return "busy" for every row, the target's own included -- no row
    renders an Install form while that holds.
    """
    version = release.get("version")
    date_html = layout.concise_timestamp_html(release.get("released_at"), now)
    notes = release.get("notes") or []
    notes_text = "; ".join(notes)
    installed_at = release.get("installed_at") or []
    if installed_at:
        installed_html = (
            layout.icon_html("icon-check", size=16)
            + layout.concise_timestamp_html(installed_at[-1], now))
    else:
        installed_html = ""
    is_target = bool(target_version) and version == target_version
    if installs_blocked and is_target:
        action_html = (
            '<span class="text-label">%s</span>'
            % escape_html(i18n.t(STATE_LABELS["in_progress"])))
    elif installs_blocked:
        # A different install is already running: no button, since
        # posting here can only ever come back "busy" too.
        action_html = ""
    elif release.get("installable") and is_target:
        action_html = (
            '<span class="text-label">%s</span>'
            % escape_html(i18n.t(STATE_LABELS["scheduled"])))
    elif release.get("installable"):
        action_html = _install_form_html(version)
    elif version == running_version:
        # The row for the currently running release: no button, no
        # "Not installable" text -- being the running version is not a
        # structural fact about the floor, it is simply not offered
        # since it is already installed.
        action_html = ""
    else:
        action_html = (
            '<span class="text-label">%s</span>'
            % escape_html(i18n.t(NOT_INSTALLABLE_TEXT)))
    return (version, date_html, notes_text, installed_html, action_html)


def _history_card_html(ctx, view):
    releases = view.get("releases") or []
    if not releases:
        body_html = layout.empty_state(
            i18n.t(EMPTY_RELEASES_HEADING_TEXT), i18n.t(EMPTY_RELEASES_BODY_TEXT))
    else:
        installs_blocked = view.get("state") == "in_progress"
        rows = [
            _release_row(
                release, view.get("running_version"), view.get("target_version"),
                installs_blocked, ctx.now)
            for release in releases]
        headers = (
            i18n.t(TABLE_HEADER_VERSION_TEXT), i18n.t(TABLE_HEADER_DATE_TEXT),
            i18n.t(TABLE_HEADER_NOTES_TEXT), i18n.t(TABLE_HEADER_INSTALLED_TEXT), "")
        body_html = layout.data_table(
            headers, rows, mono_columns=(0,), raw_columns=(1, 3, 4),
            desc_columns=(2,), prose=True, modifier="firmware-history")
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>"
    ) % (escape_html(i18n.t(HISTORY_HEADING_TEXT)), body_html)


def _install_confirm_form_html(version):
    return (
        '<form method="post" action="%s">'
        '<input type="hidden" name="version" value="%s">'
        '<input type="hidden" name="confirm" value="yes">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (INSTALL_ROUTE, escape_html(version), escape_html(i18n.t(INSTALL_BUTTON_TEXT)))


def update_install_confirm_page(ctx, version, next_wake_text):
    """Two-step install confirmation: rendered whenever the posted
    `confirm` field is not exactly "yes", including a bare POST with
    none. This page is the actual security control -- it works with
    JavaScript disabled, blocked by CSP, or against a hand-crafted
    request that skips the client-side `data-confirm` dialog -- the same
    control-flow shape as
    `companion/settings/calendar.py`'s `calendar_disconnect_confirm_page()`.

    `version` has already been validated (the registry's own version
    pattern and length cap) by the caller before this page is ever
    reached; still escaped here, defence in depth. `ctx` is accepted but
    unused, matching every other confirm-page builder's signature.
    """
    ctx = page_context.coerce(ctx)
    resolved_wake_text = next_wake_text or i18n.t(UNKNOWN_TIME_TEXT)
    heading = i18n.t(INSTALL_CONFIRM_HEADING_TEMPLATE) % version
    sentence = i18n.t(INSTALL_CONFIRM_SENTENCE_TEMPLATE) % resolved_wake_text
    return (
        layout.page_header(heading)
        + '<p class="text-body">%s</p>' % escape_html(sentence)
        + _install_confirm_form_html(version)
        + '<p><a class="text-label" href="%s">%s</a></p>'
        % (layout.UPDATE_ROUTE, escape_html(i18n.t(CANCEL_BUTTON_TEXT)))
    )


def compute_next_wake_text(ctx):
    """The Update page's own next-wake clock text: shared by the live GET
    `render()` below and the install-confirmation page's sentence
    (`companion/app.py`'s `_handle_update_install_post()`), so both ever
    name the exact same wake time.
    """
    ctx = page_context.coerce(ctx)
    device_cfg = ctx.device_config or {}
    battery_critical = ctx.battery_critical if ctx.battery_critical is not None else False
    next_wake_iso = wake.next_wake_at_iso(
        ctx.last_checkin_ts, device_cfg, battery_critical=battery_critical)
    if not next_wake_iso:
        return ""
    next_wake_parsed = layout.parse_iso(next_wake_iso)
    if next_wake_parsed is None:
        return ""
    now = ctx.now or history_db.utc_now_iso()
    return layout.local_clock_text(next_wake_parsed, now_parsed=layout.parse_iso(now))


def update_page(ctx, view, next_wake_text):
    """The page body: `layout.page_header()`, then the Status card
    (running version, update state, rollback warning, scheduled
    sentence, Cancel) and the Version history card, in that order.
    `view` is `server.firmware_registry.update_view()`'s own return
    value; `next_wake_text` is the caller's own formatted clock string
    (or "" when no next-wake time could be computed).
    """
    ctx = page_context.coerce(ctx)
    return (
        layout.page_header(i18n.t(_NAV_UPDATE_TEXT))
        + _status_card_html(ctx, view, next_wake_text)
        + _history_card_html(ctx, view)
    )


def render(ctx):
    """companion/routes.py's GET /update entry point: loads the registry
    and device report fresh from `ctx.state_dir`, derives the next-wake
    clock text via `compute_next_wake_text()`, and renders `update_page()`.
    """
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()
    registry = firmware_registry.load_registry(state_dir)
    device_report = firmware_registry.load_device_report(state_dir)
    view = firmware_registry.update_view(registry, device_report, now)
    return update_page(ctx, view, compute_next_wake_text(ctx))
