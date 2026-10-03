"""The Update page: firmware release status, version history, and the
Install/Cancel action markup.

The running version, the update state, a rollback warning and the
version history are driven entirely by `server.firmware_registry.
update_view()` (`update_page()`/`render()`). `update_install_confirm_page()`
is the real, server-side install-confirmation gate -- `companion/app.py`'s
`_handle_update_install_post()`/`_handle_update_cancel_post()` are the
live POST handlers for the forms this module renders.
"""
import collections

import companion.frame_state as frame_state
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

STATUS_HEADING_TEXT = i18n.msg("update.installed_software", "Installed software")
HISTORY_HEADING_TEXT = i18n.msg("update.version_history", "Available versions")

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
# The quiet-hours variant of the sentence above: frame_state.STATE_HELD
# means the computed wake time already accounts for the frame deferring
# through quiet hours (wake.next_wake_status()'s own hold_reason), so
# "at the next wake" would misdescribe why it is later than the base
# interval.
SCHEDULED_SENTENCE_HELD_TEMPLATE = i18n.msg(
    "update.scheduled_installs_when_quiet_hours_end_around_s",
    "Scheduled — installs when quiet hours end, around %s.")
ROLLBACK_SENTENCE_TEMPLATE = i18n.msg(
    "update.firmware_rolled_back",
    "Firmware rolled back — the update to %s failed on trial boot; "
    "the frame is back on %s.")

CANCEL_BUTTON_TEXT = i18n.msg("update.cancel", "Cancel")
INSTALL_BUTTON_TEXT = i18n.msg("update.install", "Install")
NOT_INSTALLABLE_TEXT = i18n.msg("update.not_installable", "Not installable")
# publish_release(..., bench=True) admits a non-tag version such as
# fw-v1.2.0-bench1. It is never listed for installation; the badge
# marks it only when it is the release the frame currently runs. It
# composes .banner__pill (settings/rules.py's own
# "<scope>__kind banner__pill" pattern).
BENCH_BADGE_TEXT = i18n.msg("update.bench", "Bench")
# The running release's own badge, and the same word as the
# visually-hidden label beside the Installed check mark, so the two can
# never name the running release differently.
RUNNING_BADGE_TEXT = i18n.msg("update.running_badge", "Running")
# "%s" is the concise timestamp of an over-the-air install of a release
# the frame no longer runs; split around "%s" so the timestamp stays its
# own <time> element rather than baked into an escaped sentence.
LAST_INSTALLED_TEMPLATE = i18n.msg("update.last_installed_s", "Last installed %s")
SHOW_NOTES_TEXT = i18n.msg("update.show_notes", "Show notes")
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
# The quiet-hours variant, matching SCHEDULED_SENTENCE_HELD_TEMPLATE's
# own reasoning above.
INSTALL_CONFIRM_SENTENCE_HELD_TEMPLATE = i18n.msg(
    "update.the_frame_will_download_and_install_this_held",
    "The frame will download and install this version when quiet "
    "hours end, around %s. It will keep the update after one "
    "successful check-in — otherwise it rolls back automatically.")
BENCH_CONFIRM_NOTE_TEXT = i18n.msg(
    "update.this_is_a_bench_build", "This is a bench build.")

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


def _status_verdict_block_html(view):
    """The running-version line, the headline of the installed-software
    summary.

    RUNNING_LABEL_TEMPLATE ("Running %s") carries its own placeholder;
    the version itself renders as a separate `<span class="mono">`
    element rather than baked into the escaped sentence, matching the
    rest of this app's "interpolate the templated value as its own
    element" convention (see e.g. health_page.py's headline builders).
    The summary's single time is rendered by `_status_state_row_html()`.
    """
    icon_html = layout.icon_html("icon-nav-update", size=24)
    running_version = view.get("running_version")
    if not running_version:
        return (
            '<p class="text-body widget-verdict text-label update-summary__headline">'
            "%s%s</p>"
        ) % (icon_html, escape_html(i18n.t(NO_VERSION_REPORTED_TEXT)))
    prefix_text = i18n.t(RUNNING_LABEL_TEMPLATE).split("%s", 1)[0]
    running_is_bench = any(
        release.get("bench") and release.get("version") == running_version
        for release in view.get("releases") or [])
    # A bench build is hidden from the owner's release list but is still
    # what the frame runs, so the summary names it plainly.
    bench_html = (
        ' <span class="update-summary__bench banner__pill">%s</span>'
        % escape_html(i18n.t(BENCH_BADGE_TEXT))) if running_is_bench else ""
    return (
        '<p class="text-body widget-verdict update-summary__headline">'
        '%s<span>%s<span class="mono">%s</span>%s</span></p>'
    ) % (icon_html, escape_html(prefix_text), escape_html(running_version), bench_html)


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
    """The state and its one relevant time.

    Nothing is in flight while the state is "available", so the row is
    just the time the frame last reported; every other state names itself
    (and the release it concerns) beside the time that state began. The
    summary therefore never carries two competing timestamps.
    """
    state = view.get("state")
    if state == "available":
        return _timestamp_detail_html(view.get("reported_at"), ctx.now)
    state_label = i18n.t(STATE_LABELS.get(state, STATE_LABELS["available"]))
    dot_token = _STATE_DOT_TOKENS.get(state, "off")
    label_html = layout.status_dot(dot_token, state_label) + _target_version_html(view)
    detail_html = _timestamp_detail_html(view.get("state_at"), ctx.now)
    return (
        '<p class="text-body widget-verdict">%s</p>'
        "%s"
    ) % (label_html, detail_html)


def _scheduled_sentence_html(view, next_wake_text, wake_held=False):
    if view.get("state") != "scheduled":
        return ""
    resolved_text = next_wake_text or i18n.t(UNKNOWN_TIME_TEXT)
    template = SCHEDULED_SENTENCE_HELD_TEMPLATE if wake_held else SCHEDULED_SENTENCE_TEMPLATE
    sentence = i18n.t(template) % resolved_text
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


def _status_card_html(ctx, view, next_wake_text, wake_held=False):
    return (
        '<section class="page-section update-summary">'
        '<h2 class="text-heading">%s</h2>'
        "%s%s%s%s%s"
        "</section>"
    ) % (
        escape_html(i18n.t(STATUS_HEADING_TEXT)),
        _rollback_banner_html(view),
        _status_verdict_block_html(view),
        _status_state_row_html(ctx, view),
        _scheduled_sentence_html(view, next_wake_text, wake_held),
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


# Release notes are CI-generated commit summaries. A single note this
# short reads fine in place; anything longer or more numerous collapses
# to an excerpt (about two lines in the desktop Notes column) plus a
# native <details> holding the full list, so a release with dozens of
# notes cannot turn the version history into a wall of text.
NOTES_EXCERPT_LIMIT = 120

# What the Installed cell carries, so the desktop cell and the phone
# card's Installed line render from one decision.
_INSTALLED_RUNNING = "running"
_INSTALLED_PAST = "past"

# One release, built once and rendered twice (desktop table cell tuple,
# phone card), so the two can never disagree about what a release offers.
#   notes_excerpt_html / notes_details_html: escaped excerpt and the
#     closed <details> ("" when the notes fit in place / are absent).
#   installed_kind: _INSTALLED_RUNNING, _INSTALLED_PAST or None.
_ReleaseRow = collections.namedtuple("_ReleaseRow", (
    "version_html", "date_html", "notes_excerpt_html", "notes_details_html",
    "installed_html", "installed_kind", "action_html"))


def _notes_excerpt(text, limit=NOTES_EXCERPT_LIMIT):
    """`text` cut on a word boundary within `limit` characters and ended
    with an ellipsis, or `text` itself when it already fits.
    """
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut and text[limit] != " ":
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.-") + "\u2026"


def _notes_html(notes):
    """`(excerpt_html, details_html)` for a release's notes.

    Every note is HTML-escaped here: notes are untrusted CI output, and
    the Notes column is a raw column of `layout.data_table()`, which
    interpolates it unescaped. A lone note that fits renders in place
    with no toggle; otherwise the excerpt is followed by a closed
    <details> listing every note, which works with scripts blocked.
    """
    notes = [str(note) for note in notes if note]
    if not notes:
        return "", ""
    joined = "; ".join(notes)
    if len(notes) == 1 and len(joined) <= NOTES_EXCERPT_LIMIT:
        return escape_html(joined), ""
    items_html = "".join("<li>%s</li>" % escape_html(note) for note in notes)
    details_html = (
        '<details class="update-history__notes">'
        "<summary>%s</summary>"
        '<ul class="update-history__notes-list">%s</ul>'
        "</details>"
    ) % (escape_html(i18n.t(SHOW_NOTES_TEXT)), items_html)
    return escape_html(_notes_excerpt(joined)), details_html


def _installed_cell(release, now):
    """`(installed_html, installed_kind)` for the Installed column.

    The check mark means "this is the release the frame runs", never
    "this was once installed": only the running row carries it, with its
    over-the-air install time beside it when that install is still the
    newest one (`installed_now_at`; a release reached again by USB flash
    shows the check alone). A release installed over the air earlier but
    no longer running shows quiet "Last installed" history text instead.
    """
    if release.get("running"):
        html = (
            layout.icon_html("icon-check", size=16)
            + '<span class="visually-hidden">%s</span>'
            % escape_html(i18n.t(RUNNING_BADGE_TEXT)))
        if release.get("installed_now_at"):
            html += layout.concise_timestamp_html(release["installed_now_at"], now)
        return html, _INSTALLED_RUNNING
    installed_at = release.get("installed_at") or []
    if not installed_at:
        return "", None
    prefix, _, suffix = i18n.t(LAST_INSTALLED_TEMPLATE).partition("%s")
    html = '<span class="text-label">%s%s%s</span>' % (
        escape_html(prefix), layout.concise_timestamp_html(installed_at[-1], now),
        escape_html(suffix))
    return html, _INSTALLED_PAST


def _release_row(release, running_version, target_version, installs_blocked, now):
    """One `_ReleaseRow` for `release`: version (mono, plain text),
    date/installed/action (already-safe markup) and notes (escaped
    excerpt plus an optional closed <details>; see `_notes_html()`).

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
    version_html = (
        layout.icon_html("icon-nav-update", size=16)
        + '<span class="mono">%s</span>' % escape_html(version))
    if release.get("running"):
        version_html += (
            ' <span class="update-history__running-badge banner__pill">%s</span>'
            % escape_html(i18n.t(RUNNING_BADGE_TEXT)))
    date_html = layout.concise_timestamp_html(release.get("released_at"), now)
    excerpt_html, details_html = _notes_html(release.get("notes") or [])
    installed_html, installed_kind = _installed_cell(release, now)
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
    return _ReleaseRow(
        version_html, date_html, excerpt_html, details_html,
        installed_html, installed_kind, action_html)


def _table_cells(row):
    """The five cells `layout.data_table()` renders for `row`; notes
    (column 2) and every other cell are already-safe markup.
    """
    return (
        row.version_html, row.date_html, row.notes_excerpt_html + row.notes_details_html,
        row.installed_html, row.action_html)


def _release_card_html(row):
    """The mobile stacked-card representation of one `_release_row()`
    result: version/date on one line, the notes excerpt as wrapping
    prose with its toggle right after it, the Installed line (a
    labelled cell for the running release, the bare "Last installed"
    text for a past install, nothing otherwise) and the same action
    markup the desktop row already built -- built from the identical
    row, so the two representations can never disagree about what a
    release is offering. Matches `health_sections.py`'s own
    `.data-card` pattern (`_registry_cards_html()`/`_stats_cards_html()`)
    rather than a new one: a `<ul class="data-cards">` sibling toggled
    against the table below it purely by `companion/static/style.css`'s
    existing `.data-cards ~ .data-table-wrap` rule -- no table-specific
    CSS is needed for the toggle itself.
    """
    primary_html = (
        '<div class="data-card__primary">'
        '<span class="cell-primary">%s</span>'
        '<span class="data-card__value">'
        '<span class="data-card__label">%s</span> %s'
        "</span>"
        "</div>"
    ) % (row.version_html, escape_html(i18n.t(TABLE_HEADER_DATE_TEXT)), row.date_html)
    # The toggle sits after the excerpt paragraph, never inside it: a
    # <details> is block content and cannot be a child of <p>.
    desc_html = (
        '<p class="data-card__desc">%s</p>' % row.notes_excerpt_html
    ) if row.notes_excerpt_html else ""
    installed_row_html = ""
    if row.installed_kind == _INSTALLED_RUNNING:
        installed_row_html = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span> %s'
            "</div>"
        ) % (escape_html(i18n.t(TABLE_HEADER_INSTALLED_TEXT)), row.installed_html)
    elif row.installed_kind == _INSTALLED_PAST:
        installed_row_html = '<div class="data-card__secondary">%s</div>' % row.installed_html
    action_row_html = (
        '<div class="data-card__action">%s</div>' % row.action_html) if row.action_html else ""
    return "<li class=\"data-card\">%s%s%s%s%s</li>" % (
        primary_html, desc_html, row.notes_details_html, installed_row_html, action_row_html)


def _history_cards_html(rows):
    if not rows:
        return ""
    return '<ul class="data-cards">%s</ul>' % "".join(_release_card_html(row) for row in rows)


def _owner_releases(view):
    """The releases the owner is shown: real releases only.

    Bench builds are a development aid and never an owner choice, so they
    are dropped here at the page boundary; a bench build that is running
    or scheduled still surfaces truthfully in the summary above, which
    reads `running_version`/`target_version` rather than this list. The
    registry's own classification and installability are untouched.
    """
    return [release for release in (view.get("releases") or []) if not release.get("bench")]


def _history_card_html(ctx, view):
    releases = _owner_releases(view)
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
        table_html = layout.data_table(
            headers, [_table_cells(row) for row in rows], raw_columns=(0, 1, 2, 3, 4),
            desc_columns=(2,), prose=True, modifier="firmware-history")
        # Cards must render before the table: style.css's
        # `.data-cards ~ .data-table-wrap` sibling-combinator toggle
        # depends on this DOM order (matching health_sections.py's own
        # "do not reorder" contract for the identical mechanism).
        body_html = _history_cards_html(rows) + table_html
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


def update_install_confirm_page(ctx, version, next_wake_text, wake_held=False, is_bench=False):
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
    `wake_held` selects the quiet-hours wording, matching
    `compute_next_wake_text()`'s own resolved state. `is_bench` adds one
    extra sentence naming the release as a bench build -- the version
    tag alone (e.g. "fw-v1.2.0-bench1") is the only other hint, and an
    operator has to already know that convention.
    """
    ctx = page_context.coerce(ctx)
    resolved_wake_text = next_wake_text or i18n.t(UNKNOWN_TIME_TEXT)
    heading = i18n.t(INSTALL_CONFIRM_HEADING_TEMPLATE) % version
    template = (
        INSTALL_CONFIRM_SENTENCE_HELD_TEMPLATE if wake_held
        else INSTALL_CONFIRM_SENTENCE_TEMPLATE)
    sentence = i18n.t(template) % resolved_wake_text
    bench_note_html = (
        '<p class="text-label">%s</p>' % escape_html(i18n.t(BENCH_CONFIRM_NOTE_TEXT))
    ) if is_bench else ""
    return (
        layout.page_header(heading)
        + '<p class="text-body">%s</p>' % escape_html(sentence)
        + bench_note_html
        + _install_confirm_form_html(version)
        + '<p><a class="text-label" href="%s">%s</a></p>'
        % (layout.UPDATE_ROUTE, escape_html(i18n.t(CANCEL_BUTTON_TEXT)))
    )


def compute_next_wake_text(ctx):
    """The Update page's own `(next_wake_text, wake_held)` pair: shared
    by the live GET `render()` below and the install-confirmation page's
    sentence (`companion/app.py`'s `_handle_update_install_post()`), so
    both ever name the exact same wake time -- or agree that there is
    none to name.

    Resolves through the same `wake.next_wake_status()` /
    `frame_state.resolve_state()` triple every other next-wake consumer
    uses (`frame_state.py`'s own "so they can never disagree" contract,
    and the arguments Home's Frame tile passes -- `home_page.py`'s
    `_status_tiles_html()`), rather than a bare
    `wake.next_wake_at_iso()` call: a wake already overdue
    (`frame_state.STATE_LATE`) or unresolvable
    (`frame_state.STATE_UNKNOWN`) returns "" -- callers fall back to
    `UNKNOWN_TIME_TEXT` -- instead of quietly formatting a time that has
    already passed. `wake_held` is `frame_state.STATE_HELD`: the frame is
    deferring into or through quiet hours, so callers can swap in that
    wording instead of "at the next wake".
    """
    ctx = page_context.coerce(ctx)
    device_cfg = ctx.device_config or {}
    now = ctx.now or history_db.utc_now_iso()
    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.last_checkin_ts, device_cfg)
    state = frame_state.resolve_state(next_wake_iso, effective_interval_s, hold_reason, now)
    if state in (frame_state.STATE_LATE, frame_state.STATE_UNKNOWN):
        return "", False
    next_wake_parsed = layout.parse_iso(next_wake_iso)
    if next_wake_parsed is None:
        return "", False
    text = layout.local_clock_text(next_wake_parsed, now_parsed=layout.parse_iso(now))
    return text, state == frame_state.STATE_HELD


def update_page(ctx, view, next_wake_text, wake_held=False):
    """The page body: `layout.page_header()`, then the Status card
    (running version, update state, rollback warning, scheduled
    sentence, Cancel) and the Version history card, in that order.
    `view` is `server.firmware_registry.update_view()`'s own return
    value; `next_wake_text` is the caller's own formatted clock string
    (or "" when no next-wake time could be computed); `wake_held`
    selects the quiet-hours wording for that sentence.
    """
    ctx = page_context.coerce(ctx)
    return (
        layout.page_header(i18n.t(_NAV_UPDATE_TEXT))
        + _status_card_html(ctx, view, next_wake_text, wake_held)
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
    next_wake_text, wake_held = compute_next_wake_text(ctx)
    return update_page(ctx, view, next_wake_text, wake_held)
