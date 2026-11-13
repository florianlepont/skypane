"""The Update page: a call-to-action card (up to date, or the one newer
release to install), the full release list as compact one-line rows, and
the Install/Cancel action markup.

The running version, the update state, a rollback warning and the
release list are driven entirely by `server.firmware_registry.
update_view()` (`update_page()`/`render()`). `update_install_confirm_page()`
is the real, server-side install-confirmation gate -- `companion/app.py`'s
`_handle_update_install_post()`/`_handle_update_cancel_post()` are the
live POST handlers for the forms this module renders.
"""
import collections
import re

import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
from companion import ui_components, ui_segmented
from companion.layout import csrf_field, escape_html
import companion.page_context as page_context
import companion.wake as wake
from server import firmware_registry
from server import hardware
from server import history_db

# Named here once, so the per-row/Cancel forms below, companion/app.py's
# POST handlers and this module's own tests share one definition rather
# than retyping the literal path.
INSTALL_ROUTE = "/update/install"
CANCEL_ROUTE = "/update/cancel"

# Shares its id with companion/ui_base.py's own nav-label Message: msg() is
# idempotent for a repeat id/English pair, and this page's own <h1> heading
# must read exactly what the nav calls it.
_NAV_UPDATE_TEXT = i18n.msg("nav.update", "Releases")

# The query parameter that picks the hardware type on GET and the form
# field that carries it on POST. A POST without the field means the
# legacy type, so a form bookmarked before the chooser existed still works.
TYPE_QUERY_PARAM = "type"
TYPE_FORM_FIELD = "hardware_type"

# Names the group of type buttons (a form's accessible name).
TYPE_CHOOSER_LABEL_TEXT = i18n.msg("update.hardware_type", "Hardware type")
# "%s" is the hardware type's label, on the install confirmation page.
CONFIRM_TYPE_TEMPLATE = i18n.msg("update.for_hardware_type_s", "For %s")

HISTORY_HEADING_TEXT = i18n.msg("update.version_history", "Versions")
# The history's status chips: the newest release, and the one the frame runs.
STATE_NEWEST_TEXT = i18n.msg("update.state_newest", "Newest")
STATE_INSTALLED_TEXT = i18n.msg("update.state_installed", "Installed")
NOTES_TEXT = i18n.msg("update.notes_n", "Notes (%d)")
NO_VERSION_REPORTED_TEXT = i18n.msg(
    "update.no_version_reported_yet", "No version reported yet")

# The two state words a release row can show beside a schedule.
STATE_LABELS = {
    "scheduled": i18n.msg("update.scheduled", "Scheduled"),
    "in_progress": i18n.msg("update.in_progress", "In progress"),
}

# The summary that opens the Fleet panel: the label over the installed
# version, and the state chip beside it when no update is on offer.
ON_THE_FRAME_LABEL_TEXT = i18n.msg("update.on_the_frame", "On the frame")
UP_TO_DATE_CHIP_TEXT = i18n.msg("update.up_to_date", "Up to date")

# The call-to-action card's headline, one per situation.
CTA_UP_TO_DATE_TEXT = i18n.msg("update.cta_up_to_date", "The frame is up to date")
CTA_AVAILABLE_TEXT = i18n.msg("update.cta_available", "Update available")
CTA_SCHEDULED_TEXT = i18n.msg("update.cta_scheduled", "Update scheduled")
CTA_INSTALLING_TEXT = i18n.msg("update.cta_installing", "Installing")
CTA_FAILED_TEXT = i18n.msg("update.cta_failed", "Install failed")
# "%s" is a release version, rendered as its own monospace element.
CTA_INSTALLING_BODY_TEMPLATE = i18n.msg(
    "update.cta_installing_body",
    "%s is installing. The frame keeps it after one successful check-in; "
    "otherwise it rolls back.")
CTA_FAILED_BODY_TEMPLATE = i18n.msg(
    "update.cta_failed_body", "%s could not be installed.")
CTA_STAYS_ON_TEMPLATE = i18n.msg("update.cta_stays_on", "The frame stays on %s.")
# The card's footer while something other than "up to date" is shown:
# "%s" is the version the frame runs now.
ON_THE_FRAME_TEMPLATE = i18n.msg("update.on_the_frame_s", "On the frame: %s")
# "%s" is a relative age (`<time data-relative>`) or an absolute local
# date and time (`<time>`), each its own element.
INSTALLED_AGO_TEMPLATE = i18n.msg("update.installed_ago_s", "Installed %s")
INSTALLED_ON_TEMPLATE = i18n.msg("update.installed_on_s", "Installed %s")
RELEASED_AGO_TEMPLATE = i18n.msg("update.released_ago_s", "Released %s")
RELEASED_ON_TEMPLATE = i18n.msg("update.released_on_s", "Released %s")
# "%s" is a past OTA install time of a release the frame no longer runs.
LAST_INSTALLED_TEMPLATE = i18n.msg("update.last_installed_s", "Last installed %s")

# The same sentences without a clock time, for a frame whose next wake cannot
# be named (overdue, or never seen): no made-up or past time is shown.
SCHEDULED_SENTENCE_NO_TIME = i18n.msg(
    "update.scheduled_installs_at_the_next_wake",
    "Scheduled — installs at the next wake.")
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
# The rollback's docked toast, a persistent state rather than a flash.
ROLLBACK_TOAST_CLASS = "update-rollback"

CANCEL_BUTTON_TEXT = i18n.msg("update.cancel", "Cancel")
INSTALL_BUTTON_TEXT = i18n.msg("update.install", "Install")
# Visible wording of the call-to-action Install and of an Install on an
# older release, which is a rollback; "%s" is the release version.
INSTALL_VERSION_BUTTON_TEMPLATE = i18n.msg("update.install_version_s", "Install %s")
ROLLBACK_BUTTON_TEMPLATE = i18n.msg("update.roll_back_to_s", "Roll back to %s")
ROLLBACK_SHORT_TEXT = i18n.msg("update.roll_back", "Roll back")
NOT_INSTALLABLE_TEXT = i18n.msg("update.not_installable", "Not installable")
# publish_release(..., bench=True) admits a non-tag version such as
# fw-v1.2.0-bench1. It is never listed for installation; the badge
# marks it only when it is the release the frame currently runs. It
# composes .banner__pill (settings/rules.py's own
# "<scope>__kind banner__pill" pattern).
BENCH_BADGE_TEXT = i18n.msg("update.bench", "Bench")
# The running release's own badge.
RUNNING_BADGE_TEXT = i18n.msg("update.running_badge", "Running")
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
INSTALL_CONFIRM_SENTENCE_NO_TIME = i18n.msg(
    "update.the_frame_will_download_and_install_this_no_time",
    "The frame will download and install this version at its next "
    "wake. It will keep the update after one successful check-in — "
    "otherwise it rolls back automatically.")
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

EMPTY_RELEASES_HEADING_TEXT = i18n.msg("update.no_releases_yet", "No releases yet")
EMPTY_RELEASES_BODY_TEXT = i18n.msg(
    "update.publish_a_release",
    "Publish a release by pushing a fw-v* tag. It will appear here "
    "once CI finishes building and signing it.")

# The quiet/secondary button treatment companion/pages/history_page.py's
# Show-more control and the calendar-disconnect form already share --
# never the accent-styled primary. The accent primary is spent only on
# installing a release newer than the one the frame runs.
_QUIET_BUTTON_CLASS = "btn btn--secondary"
# The text-style variant of it for a rare action in a flat list row.
_TEXT_BUTTON_CLASS = "btn btn--ghost"

# Where a release sits against the running one (`view["releases"][n]
# ["direction"]`): only "older" is worded as a rollback.
_DIRECTION_NEWER = "newer"
_DIRECTION_OLDER = "older"


class TypeChoice(collections.namedtuple("TypeChoice", "selected relevant chooser")):
    """The hardware type a request acts on. `chooser` is True only when
    more than one type is relevant; `carries_field` adds the hidden
    `hardware_type` field to every form, which is also needed when the
    single relevant type is not the legacy one (a form without the field
    would act on the legacy type)."""

    @property
    def carries_field(self):
        return self.chooser or self.selected != hardware.LEGACY_KEY


def resolve_type_choice(state_dir, device_report, requested=None):
    """The `TypeChoice` for a GET: `requested` (the `type` query value) is
    honoured only when it names a relevant type and the chooser is shown;
    anything else falls back to the legacy type."""
    relevant = tuple(firmware_registry.relevant_types(state_dir, device_report))
    if len(relevant) > 1:
        default = hardware.LEGACY_KEY if hardware.LEGACY_KEY in relevant else relevant[0]
        return TypeChoice(requested if requested in relevant else default, relevant, True)
    return TypeChoice(relevant[0] if relevant else hardware.LEGACY_KEY, relevant, False)


def posted_type(value):
    """The validated hardware type of a POSTed `hardware_type` value, or
    None when it is not usable here. An absent field (None) is the legacy
    type; anything else must be an exact member of the available types
    before it reaches a path or a registry."""
    if value is None:
        return hardware.LEGACY_KEY
    if isinstance(value, str) and value in hardware.available_types():
        return value
    return None


def post_choice(state_dir, hardware_type):
    """The `TypeChoice` for a POST that already passed `posted_type()`."""
    relevant = tuple(firmware_registry.relevant_types(
        state_dir, firmware_registry.load_device_report(state_dir)))
    return TypeChoice(hardware_type, relevant, len(relevant) > 1)


def page_route(hardware_type):
    """The Update page's own route, pointing at `hardware_type` unless it
    is the legacy type (whose page is the bare route)."""
    if hardware_type == hardware.LEGACY_KEY:
        return layout.UPDATE_ROUTE
    return "%s?%s=%s" % (layout.UPDATE_ROUTE, TYPE_QUERY_PARAM, hardware_type)


def _type_field_html(hardware_type):
    return '<input type="hidden" name="%s" value="%s">' % (
        TYPE_FORM_FIELD, escape_html(hardware_type))


def _type_label(hardware_type):
    return hardware.get_profile(hardware_type).label


def _type_chooser_html(choice):
    """The type switch: the app's segmented control (`.theme-form`) as a
    GET form, so it works without script. The active type is marked with
    `aria-pressed`; the full label is also the button's `title`."""
    buttons = [
        (TYPE_QUERY_PARAM, key, _type_label(key), key == choice.selected, "", _type_label(key))
        for key in choice.relevant]
    return ui_segmented.segmented_buttons_html(
        'method="get" action="%s" aria-label="%s"' % (
            layout.UPDATE_ROUTE, escape_html(i18n.t(TYPE_CHOOSER_LABEL_TEXT))),
        buttons, "update-type-chooser")


def _mono_html(version):
    return '<span class="mono">%s</span>' % escape_html(version)


def _fill_html(template, *pieces_html):
    """`template` (an i18n Message with one "%s" per piece) with each
    placeholder replaced by an already-safe markup piece; the literal
    text around the placeholders is escaped here.
    """
    parts = i18n.t(template).split("%s")
    html = escape_html(parts[0])
    for piece_html, literal in zip(pieces_html, parts[1:]):
        html += piece_html + escape_html(literal)
    return html


def _ago_html(ts, now):
    """A relative age (`<time data-relative>`) whose `title` is the full
    local date and time, or "" when `ts` is missing."""
    return layout.relative_time_html(ts, now, fallback="", with_title=True) if ts else ""


def _owner_releases(view):
    """The releases the owner is shown: real releases only.

    Bench builds are a development aid and never an owner choice, so they
    are dropped here at the page boundary; a bench build that is running
    or scheduled still surfaces truthfully in the call-to-action card,
    which reads `running_version`/`target_version` rather than this list.
    The registry's own classification and installability are untouched.
    """
    return [release for release in (view.get("releases") or []) if not release.get("bench")]


def _install_form_html(
        version, label_template=None, quiet=False, type_html="", short_label=None,
        button_class=_QUIET_BUTTON_CLASS):
    """The Install form for `version`: `data-confirm` misclick guard, the
    hidden `version` field and no `confirm` field (the server
    confirmation page is the real gate).

    With no `label_template` the button reads "Install" and carries the
    version in its accessible name; otherwise the label template names
    the version itself, or `short_label` (a Message without the version) is
    the visible text while the accessible name still names it. `quiet`
    selects the secondary button treatment.
    """
    confirm_question = i18n.t(INSTALL_CONFIRM_QUESTION_TEMPLATE) % version
    if label_template is None:
        label = i18n.t(INSTALL_BUTTON_TEXT)
        aria_html = ' aria-label="%s"' % escape_html(
            i18n.t(INSTALL_VERSION_BUTTON_TEMPLATE) % version)
    else:
        label = i18n.t(label_template) % version
        aria_html = ""
        if short_label is not None:
            label = i18n.t(short_label)
            aria_html = ' aria-label="%s"' % escape_html(i18n.t(label_template) % version)
    class_html = ' class="%s"' % button_class if quiet else ""
    return (
        '<form method="post" action="%s" data-confirm="%s">'
        '<input type="hidden" name="version" value="%s">%s%s'
        '<button type="submit"%s%s>%s</button>'
        "</form>"
    ) % (
        INSTALL_ROUTE, escape_html(confirm_question), escape_html(version), type_html,
        csrf_field(), class_html, aria_html, escape_html(label),
    )


def _release_install_form_html(
        release, with_version_label=False, type_html="", compact=False):
    """The Install form for `release`, worded and styled by where it sits
    against the running release: a newer one is "Install" on the accent
    primary button; an older one is "Roll back to <version>" on the quiet
    button; an equal or incomparable one is a quiet "Install". `compact`
    words a rollback "Roll back" (the table row names the version).
    """
    version = release.get("version")
    direction = release.get("direction")
    if direction == _DIRECTION_OLDER:
        return _install_form_html(
            version, ROLLBACK_BUTTON_TEMPLATE, quiet=True, type_html=type_html,
            short_label=ROLLBACK_SHORT_TEXT if compact else None,
            button_class=_TEXT_BUTTON_CLASS if compact else _QUIET_BUTTON_CLASS)
    if direction == _DIRECTION_NEWER:
        return _install_form_html(
            version, INSTALL_VERSION_BUTTON_TEMPLATE if with_version_label else None,
            type_html=type_html)
    return _install_form_html(
        version, INSTALL_VERSION_BUTTON_TEMPLATE if with_version_label else None, quiet=True,
        type_html=type_html, button_class=_TEXT_BUTTON_CLASS if compact else _QUIET_BUTTON_CLASS)


def _cancel_form_html(view):
    if not view.get("cancellable"):
        return ""
    return (
        '<form method="post" action="%s">%s%s'
        '<button type="submit" class="%s">%s</button>'
        "</form>"
    ) % (CANCEL_ROUTE, view.get("type_field_html", ""), csrf_field(), _QUIET_BUTTON_CLASS,
         escape_html(i18n.t(CANCEL_BUTTON_TEXT)))


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
    title, detail = layout.split_toast_message(text)
    return layout.toast_html(
        title, detail, tone=layout.TOAST_TONE_WARNING, role="alert", docked=True,
        extra_class=ROLLBACK_TOAST_CLASS)


# --- the call-to-action card ---------------------------------------------

_CTA_TONE_OK = "ok"
_CTA_TONE_WARN = "warn"
_CTA_TONE_ERROR = "error"
_CTA_TONE_NEUTRAL = "neutral"
_STATES_WITH_A_TARGET_VERSION = ("scheduled", "in_progress", "failed")


def _newer_release_to_offer(view, releases):
    """The newest installable release newer than the running one, or None.
    Nothing is offered while a schedule is in flight or has failed: the
    card then reports that schedule instead."""
    if view.get("state") in _STATES_WITH_A_TARGET_VERSION:
        return None
    for release in releases:
        if release.get("direction") == _DIRECTION_NEWER and release.get("installable"):
            return release
    return None


def _first_note(release):
    notes = [str(note) for note in (release.get("notes") or []) if note]
    return notes[0] if notes else ""


def _running_line_html(view):
    """The running version, its bench badge when it is a bench build."""
    running_version = view.get("running_version")
    bench_html = ""
    if any(release.get("bench") and release.get("version") == running_version
           for release in view.get("releases") or []):
        # A bench build is hidden from the owner's release list but is
        # still what the frame runs, so the card names it plainly.
        bench_html = ' <span class="update-cta__bench banner__pill">%s</span>' % escape_html(
            i18n.t(BENCH_BADGE_TEXT))
    return _mono_html(running_version) + bench_html


def _cta_up_to_date(view, now):
    running_version = view.get("running_version")
    if not running_version:
        return (_CTA_TONE_NEUTRAL, "icon-info", NO_VERSION_REPORTED_TEXT, [], "")
    details = [_running_line_html(view)]
    running = next((release for release in view.get("releases") or []
                    if release.get("running")), {})
    installed_at = running.get("installed_now_at")
    if installed_at:
        details.append(_fill_html(INSTALLED_AGO_TEMPLATE, _ago_html(installed_at, now)))
    return (_CTA_TONE_OK, "icon-check", CTA_UP_TO_DATE_TEXT, details, "")


def _cta_available(release, now, type_html=""):
    details = [
        _mono_html(release["version"]) + " · "
        + _fill_html(RELEASED_AGO_TEMPLATE, _ago_html(release.get("released_at"), now))]
    note = _first_note(release)
    if note:
        details.append('<span class="update-cta__note">%s</span>' % escape_html(note))
    return (_CTA_TONE_NEUTRAL, "icon-upload", CTA_AVAILABLE_TEXT, details,
            _release_install_form_html(release, with_version_label=True, type_html=type_html))


def _cta_for_state(view, releases, now, next_wake_text, wake_held):
    """`(tone, icon id, headline Message, detail lines, action html)` for
    the one situation the frame is in."""
    state = view.get("state")
    target = view.get("target_version")
    state_ago = _ago_html(view.get("state_at"), now)
    type_html = view.get("type_field_html", "")
    if state == "scheduled" and target:
        template = SCHEDULED_SENTENCE_HELD_TEMPLATE if wake_held else SCHEDULED_SENTENCE_TEMPLATE
        sentence = (
            i18n.t(template) % next_wake_text if next_wake_text
            else i18n.t(SCHEDULED_SENTENCE_NO_TIME))
        return (_CTA_TONE_NEUTRAL, "icon-info", CTA_SCHEDULED_TEXT,
                [_mono_html(target), escape_html(sentence)], _cancel_form_html(view))
    if state == "in_progress" and target:
        details = [_fill_html(CTA_INSTALLING_BODY_TEMPLATE, _mono_html(target))]
        if state_ago:
            details.append(state_ago)
        return (_CTA_TONE_WARN, "icon-refresh", CTA_INSTALLING_TEXT, details, "")
    if state == "failed" and target:
        details = [_fill_html(CTA_FAILED_BODY_TEMPLATE, _mono_html(target))]
        if view.get("running_version"):
            details.append(_fill_html(CTA_STAYS_ON_TEMPLATE, _mono_html(view["running_version"])))
        if state_ago:
            details.append(state_ago)
        retry = next((release for release in releases
                      if release.get("version") == target and release.get("installable")), None)
        action_html = _release_install_form_html(
            retry, with_version_label=True, type_html=type_html) if retry else ""
        return (_CTA_TONE_ERROR, "icon-warning", CTA_FAILED_TEXT, details, action_html)
    newer = _newer_release_to_offer(view, releases)
    if newer is not None:
        return _cta_available(newer, now, type_html)
    return _cta_up_to_date(view, now)


def _on_the_frame_html(view, now):
    """The footer naming what the frame runs while the card is about
    something else (an update on offer, scheduled or installing)."""
    running = next((release for release in view.get("releases") or []
                    if release.get("running")), {})
    line = _fill_html(ON_THE_FRAME_TEMPLATE, _running_line_html(view))
    if running.get("installed_now_at"):
        line += " · " + _fill_html(
            INSTALLED_AGO_TEMPLATE, _ago_html(running["installed_now_at"], now))
    return '<p class="update-cta__on">%s</p>' % line


def _cta_card_html(ctx, view, releases, next_wake_text, wake_held=False, summarised=False):
    tone, icon_id, headline, details, action_html = _cta_for_state(
        view, releases, ctx.now, next_wake_text, wake_held)
    details_html = "".join('<p class="update-cta__detail">%s</p>' % line for line in details)
    action_block = '<div class="update-actions">%s</div>' % action_html if action_html else ""
    # "Up to date" and "failed" already name the running release.
    shows_running = not summarised and (
        view.get("running_version") and tone in (_CTA_TONE_NEUTRAL, _CTA_TONE_WARN))
    return (
        '<section class="page-section update-cta update-cta--%s" aria-labelledby="update-cta-title">'
        '<div class="update-cta__top">'
        '<span class="update-cta__icon">%s</span>'
        '<div class="update-cta__text">'
        '<h2 class="update-cta__title" id="update-cta-title">%s</h2>%s'
        "</div></div>%s%s</section>"
    ) % (tone, layout.icon_html(icon_id, size=22), escape_html(i18n.t(headline)),
         details_html, action_block,
         _on_the_frame_html(view, ctx.now) if shows_running else "")


# --- the Fleet panel's summary --------------------------------------------

def _summary_chip_html(view, releases):
    """The one state chip of the summary: what the frame is doing about an
    update, an update on offer, or a calm "Up to date". "" when no version
    has been reported."""
    state = view.get("state")
    if state in _STATES_WITH_A_TARGET_VERSION and view.get("target_version"):
        headline, tone = {
            "scheduled": (CTA_SCHEDULED_TEXT, "info"),
            "in_progress": (CTA_INSTALLING_TEXT, "info"),
            "failed": (CTA_FAILED_TEXT, "warn"),
        }[state]
    elif _newer_release_to_offer(view, releases) is not None:
        headline, tone = CTA_AVAILABLE_TEXT, "info"
    elif view.get("running_version"):
        headline, tone = UP_TO_DATE_CHIP_TEXT, "ok"
    else:
        return ""
    return ui_components.pill_html(i18n.t(headline), tone=tone)


def _summary_html(ctx, view, releases, model_text):
    """What is on the frame, large: the label, the installed version in
    monospace, when it was installed and the model, with the state chip on
    the right. `model_text` is the model line ("" when not known)."""
    running = next((release for release in view.get("releases") or []
                    if release.get("running")), {})
    meta = []
    if running.get("installed_now_at"):
        meta.append(_fill_html(INSTALLED_AGO_TEMPLATE, _ago_html(running["installed_now_at"], ctx.now)))
    if model_text:
        meta.append(escape_html(model_text))
    if view.get("running_version"):
        version_html = '<p class="update-sum__version">%s</p>' % _running_line_html(view)
    else:
        version_html = '<p class="update-sum__version">%s</p>' % escape_html(
            i18n.t(NO_VERSION_REPORTED_TEXT))
    meta_html = '<p class="update-sum__meta">%s</p>' % " · ".join(meta) if meta else ""
    return (
        '<section class="update-sum" aria-labelledby="update-sum-label">'
        '<div class="update-sum__text"><h3 class="update-sum__label" id="update-sum-label">%s</h3>'
        "%s%s</div>%s</section>"
    ) % (escape_html(i18n.t(ON_THE_FRAME_LABEL_TEXT)), version_html, meta_html,
         _summary_chip_html(view, releases))


_DRAFT_SUFFIX = re.compile(r"\s*\((?:draft|wip)\b[^)]*\)\s*$", re.IGNORECASE)


def _release_title(release):
    """The release's first note as a title: a trailing "(DRAFT ...)" tag that
    GitHub release text carries is dropped here; the notes keep the full text."""
    note = _first_note(release)
    return _DRAFT_SUFFIX.sub("", note) or note


def _offer_card_html(ctx, release, type_html):
    """The one update card: the offered version and its release age, the
    release title and the single primary Install button."""
    title = _release_title(release)
    note_html = '<p class="update-offer__note">%s</p>' % escape_html(title) if title else ""
    return (
        '<section class="update-offer" aria-labelledby="update-offer-title">'
        '<div class="update-offer__text"><h3 class="update-offer__title" id="update-offer-title">'
        "%s · %s</h3>%s</div>"
        '<div class="update-actions">%s</div></section>'
    ) % (_mono_html(release["version"]),
         _fill_html(RELEASED_AGO_TEMPLATE, _ago_html(release.get("released_at"), ctx.now)),
         note_html,
         _release_install_form_html(release, with_version_label=True, type_html=type_html))


def _embedded_cta_html(ctx, view, releases, next_wake_text, wake_held):
    """The card under the summary: only while something is going on (an
    update on offer, scheduled, installing or failed); "" when the frame is
    up to date, which the summary's chip already says."""
    in_flight = (view.get("state") in _STATES_WITH_A_TARGET_VERSION
                 and view.get("target_version"))
    offered = _newer_release_to_offer(view, releases)
    if not in_flight and offered is None:
        return ""
    if not in_flight:
        return _offer_card_html(ctx, offered, view.get("type_field_html", ""))
    return _cta_card_html(ctx, view, releases, next_wake_text, wake_held, summarised=True)


# --- the version list ----------------------------------------------------


def _row_action_html(release, view, compact=False, offered_version=None):
    """What a row's body offers: nothing for the running release or for the
    release the update card already offers, a quiet state label for the
    schedule's target or while any install runs, the Install form otherwise,
    and plain text below the firmware floor."""
    version = release.get("version")
    if version == offered_version:
        return ""
    is_target = bool(view.get("target_version")) and version == view.get("target_version")
    if release.get("running"):
        return ""
    if view.get("state") == "in_progress":
        # A different install is already running: no button, since
        # posting here can only ever come back "busy" too.
        if is_target:
            return '<span class="text-label">%s</span>' % escape_html(
                i18n.t(STATE_LABELS["in_progress"]))
        return ""
    if release.get("installable") and is_target:
        return '<span class="text-label">%s</span>' % escape_html(
            i18n.t(STATE_LABELS["scheduled"]))
    if release.get("installable"):
        return _release_install_form_html(
            release, type_html=view.get("type_field_html", ""), compact=compact)
    return '<span class="text-label">%s</span>' % escape_html(i18n.t(NOT_INSTALLABLE_TEXT))


def _row_meta_html(release):
    """The opened row's absolute dates: when it was released and when it
    was installed (the running release's OTA install time only while that
    is still honest, otherwise the last OTA install of a past release)."""
    lines = []
    if release.get("released_at"):
        lines.append(_fill_html(
            RELEASED_ON_TEMPLATE, layout.absolute_time_html(release["released_at"])))
    if release.get("running"):
        if release.get("installed_now_at"):
            lines.append(_fill_html(
                INSTALLED_ON_TEMPLATE, layout.absolute_time_html(release["installed_now_at"])))
    elif release.get("installed_at"):
        lines.append(_fill_html(
            LAST_INSTALLED_TEMPLATE, layout.absolute_time_html(release["installed_at"][-1])))
    return "".join('<p class="update-row__meta">%s</p>' % line for line in lines)


def _row_html(release, view, now):
    """One release: a native `<details>` whose summary is the one-line row
    (version, running badge, first note, relative date) and whose body
    holds every note, the absolute dates and the action -- all without
    script. Notes are untrusted CI text, escaped here."""
    version = release.get("version")
    notes = [str(note) for note in (release.get("notes") or []) if note]
    badge_html = (
        ' <span class="update-row__badge banner__pill">%s</span>'
        % escape_html(i18n.t(RUNNING_BADGE_TEXT))) if release.get("running") else ""
    notes_html = (
        '<ul class="update-row__notes">%s</ul>'
        % "".join("<li>%s</li>" % escape_html(note) for note in notes)) if notes else ""
    action_html = _row_action_html(release, view)
    action_block = '<div class="update-actions">%s</div>' % action_html if action_html else ""
    return (
        '<li><details class="update-row%s"><summary>'
        '<span class="update-row__version">%s%s</span>'
        '<span class="update-row__when">%s</span>'
        '<span class="update-row__note">%s</span>'
        "%s</summary>"
        '<div class="update-row__body">%s%s%s</div></details></li>'
    ) % (
        " update-row--running" if release.get("running") else "",
        _mono_html(version), badge_html, _ago_html(release.get("released_at"), now),
        escape_html(notes[0]) if notes else "",
        layout.icon_html("icon-chevron-right", size=16, extra_class="update-row__chevron"),
        notes_html, _row_meta_html(release), action_block)


def _versions_group_html(ctx, view, releases):
    """The standalone Releases page's version list: the section label above
    one glass group of version rows (an empty list is one panel)."""
    from companion import ui_groups
    heading = i18n.t(HISTORY_HEADING_TEXT)
    if not releases:
        return ui_groups.group_panel(
            layout.empty_state(
                i18n.t(EMPTY_RELEASES_HEADING_TEXT), i18n.t(EMPTY_RELEASES_BODY_TEXT),
                compact=True),
            label=heading, label_id="update-versions-title",
            extra_class="update-versions-group")
    rows = "".join(_row_html(release, view, ctx.now) for release in releases)
    block = ui_groups.group(
        rows, label=heading, label_id="update-versions-title",
        extra_class="update-versions-group")
    return block.replace(
        "%s</h2>" % escape_html(heading),
        '%s <span class="update-versions__count">%d</span></h2>' % (
            escape_html(heading), len(releases)), 1).replace(
        '<ul class="group">', '<ul class="group update-group">', 1)


def _versions_card_html(ctx, view, releases, embedded=False):
    if not embedded:
        return _versions_group_html(ctx, view, releases)
    heading = escape_html(i18n.t(HISTORY_HEADING_TEXT))
    if not releases:
        return (
            '<section class="page-section update-versions" '
            'aria-labelledby="update-versions-title"><div class="update-hist__head">'
            '<h3 class="update-hist__title" id="update-versions-title">%s</h3></div>%s</section>') % (
                heading,
                layout.empty_state(
                    i18n.t(EMPTY_RELEASES_HEADING_TEXT), i18n.t(EMPTY_RELEASES_BODY_TEXT),
                    compact=True))
    offered = _newer_release_to_offer(view, releases)
    offered_version = offered["version"] if offered else None
    return (
        '<section class="page-section update-versions" aria-labelledby="update-versions-title">'
        '<div class="update-hist__head"><h3 class="update-hist__title" id="update-versions-title">'
        "%s</h3>%s</div>"
        '<ul class="update-hist__list">%s</ul></section>'
    ) % (heading, ui_components.pill_html(str(len(releases))),
         "".join(_history_row_html(release, view, ctx.now, offered_version, index == 0)
                 for index, release in enumerate(releases)))


def _status_chip_html(release, newest):
    """The row's chip: "Installed" on the release the frame runs, "Newest" on
    the latest release otherwise, nothing for the rest."""
    if release.get("running"):
        return ui_components.pill_html(i18n.t(STATE_INSTALLED_TEXT), tone="ok")
    if newest:
        return ui_components.pill_html(i18n.t(STATE_NEWEST_TEXT), tone="info")
    return ""


def _history_row_html(release, view, now, offered_version, newest):
    """One release as a flat list row: a status dot, the version, a line with
    its date, age and notes count, a status chip and, for a rollback, the quiet
    action. Notes sit behind one disclosure; the action is always in view."""
    notes = [str(note) for note in (release.get("notes") or []) if note]
    released_at = release.get("released_at")
    facts = []
    if released_at:
        facts.append(layout.absolute_time_html(released_at))
        facts.append(_ago_html(released_at, now))
    if notes:
        facts.append(escape_html(i18n.t(NOTES_TEXT) % len(notes)))
    notes_html = (
        '<details class="update-item__notes"><summary>%s</summary><ul>%s</ul></details>'
        % (escape_html(i18n.t(NOTES_TEXT) % len(notes)),
           "".join("<li>%s</li>" % escape_html(note) for note in notes))) if notes else ""
    action_html = _row_action_html(
        release, view, compact=True, offered_version=offered_version)
    classes = "update-item"
    if release.get("running"):
        classes += " update-item--running"
    elif newest:
        classes += " update-item--newest"
    return (
        '<li class="%s"><span class="update-item__dot"></span>'
        '<div class="update-item__text"><span class="update-item__version mono">%s</span>'
        '<span class="update-item__meta">%s</span>%s</div>%s'
        '<div class="update-item__action">%s</div></li>'
    ) % (classes, escape_html(release.get("version")), " · ".join(facts), notes_html,
         _status_chip_html(release, newest), action_html)


def _install_confirm_form_html(version, type_html=""):
    return (
        '<form method="post" action="%s">'
        '<input type="hidden" name="version" value="%s">%s%s'
        '<input type="hidden" name="confirm" value="yes">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (INSTALL_ROUTE, escape_html(version), type_html, csrf_field(),
        escape_html(i18n.t(INSTALL_BUTTON_TEXT)))


def update_install_confirm_page(
        ctx, version, next_wake_text, wake_held=False, is_bench=False, type_choice=None,
        back_href=None):
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
    operator has to already know that convention. `type_choice` (a
    `TypeChoice`, None for the single-type page) adds the hidden type
    field to the confirming form and, when the chooser is shown, names
    the hardware type; with None the page is the one-type page. `back_href`
    is where the Cancel link goes (the Fleet view of the frame); without it,
    the Update page of the type.
    """
    ctx = page_context.coerce(ctx)
    heading = i18n.t(INSTALL_CONFIRM_HEADING_TEMPLATE) % version
    template = (
        INSTALL_CONFIRM_SENTENCE_HELD_TEMPLATE if wake_held
        else INSTALL_CONFIRM_SENTENCE_TEMPLATE)
    sentence = (
        i18n.t(template) % next_wake_text if next_wake_text
        else i18n.t(INSTALL_CONFIRM_SENTENCE_NO_TIME))
    bench_note_html = (
        '<p class="text-label">%s</p>' % escape_html(i18n.t(BENCH_CONFIRM_NOTE_TEXT))
    ) if is_bench else ""
    type_html = type_note_html = ""
    back_route = layout.UPDATE_ROUTE
    if type_choice is not None and type_choice.carries_field:
        type_html = _type_field_html(type_choice.selected)
        back_route = escape_html(page_route(type_choice.selected))
    if back_href is not None:
        back_route = escape_html(back_href)
    if type_choice is not None and type_choice.chooser:
        type_note_html = '<p class="text-label">%s</p>' % escape_html(
            i18n.t(CONFIRM_TYPE_TEMPLATE) % _type_label(type_choice.selected))
    return (
        layout.page_header(heading)
        + '<p class="text-body">%s</p>' % escape_html(sentence)
        + type_note_html
        + bench_note_html
        + _install_confirm_form_html(version, type_html)
        + '<p><a class="text-label" href="%s">%s</a></p>'
        % (back_route, escape_html(i18n.t(CANCEL_BUTTON_TEXT)))
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
    the sentences without a time -- instead of quietly formatting a time that has
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


def update_parts(
        ctx, view, next_wake_text, wake_held=False, type_choice=None, embedded=False,
        model_text=""):
    """(device section html, versions section html, summary) of the page: the
    type chooser, the rollback warning and the call-to-action card, then the
    Versions card. `summary` is (running version or None, number of releases
    shown)."""
    ctx = page_context.coerce(ctx)
    releases = _owner_releases(view)
    chooser_html = ""
    if type_choice is not None:
        if type_choice.carries_field:
            view = dict(view, type_field_html=_type_field_html(type_choice.selected))
        if type_choice.chooser:
            chooser_html = _type_chooser_html(type_choice)
    if embedded:
        cards_html = _summary_html(ctx, view, releases, model_text) + _embedded_cta_html(
            ctx, view, releases, next_wake_text, wake_held)
    else:
        cards_html = _cta_card_html(ctx, view, releases, next_wake_text, wake_held)
    device_html = chooser_html + _rollback_banner_html(view) + cards_html
    return (
        device_html, _versions_card_html(ctx, view, releases, embedded),
        (view.get("running_version"), len(releases)))


def update_page(
        ctx, view, next_wake_text, wake_held=False, type_choice=None, embedded=False):
    """The page body: `layout.page_header()`, then the rollback warning
    (when the last outcome was a rollback), the call-to-action card
    (running version and its install time, or the newer release to
    install, or the schedule in flight) and the Versions card holding
    every release, in that order.
    `view` is `server.firmware_registry.update_view()`'s own return
    value; `next_wake_text` is the caller's own formatted clock string
    (or "" when no next-wake time could be computed); `wake_held`
    selects the quiet-hours wording for that sentence. `type_choice` (a
    `TypeChoice`) adds the type chooser when it is shown and the hidden
    type field to every action form when needed; None renders the
    single-type page, byte for byte. `embedded` drops the page header (the
    Console Fleet view supplies its own block heading).
    """
    device_html, versions_html, _summary = update_parts(
        ctx, view, next_wake_text, wake_held, type_choice, embedded)
    return ("" if embedded else layout.page_header(i18n.t(_NAV_UPDATE_TEXT))) + (
        device_html + versions_html)


def _loaded_parts(ctx, requested_type, embedded, model_text=""):
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()
    device_report = firmware_registry.load_device_report(state_dir)
    choice = resolve_type_choice(state_dir, device_report, requested_type)
    registry = firmware_registry.load_registry(state_dir, choice.selected)
    view = firmware_registry.update_view(registry, device_report, now)
    next_wake_text, wake_held = compute_next_wake_text(ctx)
    return update_parts(ctx, view, next_wake_text, wake_held, choice, embedded, model_text)


def render_parts(ctx, requested_type=None, model_text=""):
    """The embedded page as (device html, versions html, summary): the Fleet
    page places the summary, the update card and the version history in one
    section. `model_text` is the model line the summary shows."""
    return _loaded_parts(ctx, requested_type, True, model_text)


def render(ctx, requested_type=None, embedded=False):
    """companion/routes.py's GET /update entry point: loads the registry
    and device report fresh from `ctx.state_dir`, derives the next-wake
    clock text via `compute_next_wake_text()`, and renders `update_page()`.
    `requested_type` is the untrusted `type` query value: it picks among
    the relevant hardware types only when more than one exists.
    """
    device_html, versions_html, _summary = _loaded_parts(ctx, requested_type, embedded)
    return ("" if embedded else layout.page_header(i18n.t(_NAV_UPDATE_TEXT))) + (
        device_html + versions_html)
