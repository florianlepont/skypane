"""The Update page: firmware release status and version history.

The read side of OTA-08: the running version, the update state, a
rollback warning and the version history, driven entirely by
`server.firmware_registry.update_view()`. Install/Cancel POST handlers
and their confirmation flow are a later plan's own routes; this module
renders their forms as static markup targeting /update/install and
/update/cancel, which are not live routes yet.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
import companion.page_context as page_context
import companion.wake as wake
from server import firmware_registry
from server import history_db

# Not live routes yet (a later plan implements the handlers); named here
# once so the per-row/Cancel forms below and this module's own tests
# share one definition.
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
    detail_html = (
        '<div class="widget-detail">%s</div>'
        % layout.concise_timestamp_html(view.get("reported_at"), ctx.now))
    return verdict_html + detail_html


def _status_state_row_html(ctx, view):
    state = view.get("state")
    state_label = i18n.t(STATE_LABELS.get(state, STATE_LABELS["available"]))
    dot_token = _STATE_DOT_TOKENS.get(state, "off")
    timestamp_html = layout.concise_timestamp_html(view.get("state_at"), ctx.now)
    return (
        '<p class="text-body widget-verdict">%s</p>'
        '<div class="widget-detail">%s</div>'
    ) % (layout.status_dot(dot_token, state_label), timestamp_html)


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


def _release_row(release, running_version, now):
    """One `layout.data_table()` row for `release`: version (mono, plain
    text), date/installed/action (raw, already-safe markup), notes
    (plain text, escaped by data_table() itself since it is not in
    raw_columns -- CI-generated commit summaries are untrusted input).
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
    if release.get("installable"):
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
        rows = [
            _release_row(release, view.get("running_version"), ctx.now)
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
    clock text the same way companion/pages/health_page.py's Device tile
    does, and renders `update_page()`.
    """
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()
    registry = firmware_registry.load_registry(state_dir)
    device_report = firmware_registry.load_device_report(state_dir)
    view = firmware_registry.update_view(registry, device_report, now)

    device_cfg = ctx.device_config or {}
    battery_critical = ctx.battery_critical if ctx.battery_critical is not None else False
    next_wake_iso = wake.next_wake_at_iso(
        ctx.last_checkin_ts, device_cfg, battery_critical=battery_critical)
    next_wake_text = ""
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_text = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(now))

    return update_page(ctx, view, next_wake_text)
