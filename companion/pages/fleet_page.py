"""The Fleet page body: every frame as one list row (a status dot, the
frame name, its owner and an actions menu) plus the dialogs the header
button and the row menus open.

Pure markup: it takes a `FleetView` and reads nothing else. A row carries
only display facts (names, ids, owner email, hardware label, last contact,
battery); no secret hash, token, pairing code or code expiry ever reaches
this module. The one submitted value it re-renders is the typed pairing
code, escaped into the input's `value` on the immediate response.
"""
import datetime
from typing import NamedTuple

from companion import device_scope, frame_status, i18n, ui_modal
from companion.ui_base import escape_html, icon_html, validation_attrs

KIND_LIVE = frame_status.KIND_LIVE
KIND_PENDING = frame_status.KIND_PENDING
KIND_RETIRED = frame_status.KIND_RETIRED
_KIND_ORDER = {KIND_LIVE: 0, KIND_PENDING: 1, KIND_RETIRED: 2}
_PROBLEM_STATES = (frame_status.STATUS_ERROR, frame_status.STATUS_WARN)

CODE_FIELD = "code"
OWNER_FIELD = "owner_user_id"
MAC_FIELD = "mac"
HASH_FIELD = "secret_sha256"
HARDWARE_FIELD = "hardware_type"
PAIR_QUERY_FLAG = "pair"

_FRAMES_TEXT = i18n.msg("admin_fleet.frames", "Frames")
# Same id and English as the frame button's, so one name reads one way.
_LIVE_FRAME_NAME = i18n.msg("nav.device_default_name", "Orly frame")
_UNNAMED_FRAME = i18n.msg("admin_fleet.unnamed_frame", "Unnamed frame")
_NEW_FRAME = i18n.msg("admin_fleet.new_frame", "New frame")
_WAITING_FOR_PAIRING = i18n.msg("admin_fleet.waiting_for_pairing", "Waiting for pairing")
_FORMERLY = i18n.msg("admin_fleet.formerly_owner", "Formerly %s")
_UNASSIGNED = i18n.msg("admin_fleet.unassigned", "Unassigned")
_EMPTY_HEADING = i18n.msg("admin_fleet.no_frames_yet", "No frames yet")
_EMPTY_BODY = i18n.msg(
    "admin_fleet.switch_a_frame_on_when_its_pairing_code_appears_choose_add",
    "Switch a frame on. When its pairing code appears on its screen, choose "
    "Add a frame.")

_ACTION_PERSONAL_VIEW = i18n.msg(
    "admin_fleet.open_personal_view", "Open personal view")
_OPEN_PERSONAL_ARIA = i18n.msg(
    "admin_fleet.open_personal_view_aria", "Open the personal view of %s")
_ACTION_REASSIGN = i18n.msg("admin_fleet.reassign", "Reassign")
_ACTION_REACTIVATE = i18n.msg("admin_fleet.re_activate", "Re-activate")
_CONFIRM_RETIRE = i18n.msg("admin_fleet.retire_frame", "Retire frame")
_CONFIRM_REACTIVATE = i18n.msg("admin_fleet.re_activate_frame", "Re-activate frame")
_KEEP_FRAME = i18n.msg("admin_fleet.keep_frame", "Keep frame")
_KEEP_RETIRED = i18n.msg("admin_fleet.keep_retired", "Keep retired")
_TITLE_RETIRE = i18n.msg("admin_fleet.retire_frame_title", "Retire “%s”?")
_TITLE_REACTIVATE = i18n.msg(
    "admin_fleet.re_activate_frame_title", "Re-activate “%s”?")
_NEW_OWNER = i18n.msg("admin_fleet.new_owner", "New owner")
_TITLE_REASSIGN = i18n.msg("admin_fleet.reassign_frame_title", "Reassign “%s”?")
_CANCEL = i18n.msg("admin_fleet.cancel", "Cancel")
_REASSIGN_CHOOSE_HINT = i18n.msg(
    "admin_fleet.reassign_choose_owner_hint", "Choose an owner to continue.")
_REASSIGN_CO_MANAGERS = i18n.msg(
    "admin_fleet.reassign_co_managers_lose_access",
    "Co-managers lose their access to this frame.")
_REASSIGN_ARIA = i18n.msg("admin_fleet.reassign_aria", "Reassign %s to another owner")
_RETIRE_SENTENCE = i18n.msg(
    "admin_fleet.this_frame_will_show_a_retired_screen_and_stop_updating",
    "This frame will show a retired screen and stop updating. Its data is kept "
    "and you can re-activate it later.")
_REACTIVATE_SENTENCE = i18n.msg(
    "admin_fleet.its_settings_and_history_are_erased_it_returns_to_pairing",
    "Its settings and history are erased. It returns to pairing and shows a new code.")
_REASSIGN_SENTENCE = i18n.msg(
    "admin_fleet.settings_history_and_gallery_on_this_frame_are_erased",
    "%s's settings, history and gallery on this frame are erased. The frame "
    "restarts like a new one.")
_REASSIGN_LIVE_SENTENCE = i18n.msg(
    "admin_fleet.only_the_owner_changes_nothing_is_erased",
    "Nothing is erased.")
_THIS_OWNER = i18n.msg("admin_fleet.the_current_owner", "The current owner")
_RETIRE_THIS_FRAME = i18n.msg("admin_fleet.retire_this_frame", "Retire this frame…")
_RETIRE_HINT = i18n.msg(
    "admin_fleet.retire_this_frame_hint",
    "The frame stops showing anything and its owner is released.")
_RETIRE_ACTION = i18n.msg("admin_fleet.retire_this_frame_action", "Retire…")

_ADD_TITLE = i18n.msg("admin_fleet.add_a_frame", "Add a frame")
PAIR_OWNER_LABEL = i18n.msg("admin_fleet.pair_owner", "Owner")
_PAIR_OWNER_CHOOSE = i18n.msg("admin_fleet.choose_an_owner_option", "Choose an owner")
_PAIR_SUBMIT = i18n.msg("admin_fleet.pair_frame", "Pair frame")
_ADMIN_SUFFIX = i18n.msg("admin_fleet.admin_suffix", "(admin)")
CLAIM_REFUSED_TITLE = i18n.msg("admin_fleet.code_not_recognised", "Code not recognised")
CLAIM_REFUSED_DETAIL = i18n.msg(
    "admin_fleet.the_code_is_wrong_expired_or_already_used",
    "The code is wrong, expired or already used. A new code appears on the "
    "frame within 35 minutes.")
CLAIM_CODE_ERROR = i18n.msg(
    "admin_fleet.check_the_code_and_try_again", "Check the code and try again.")


def claim_refused_error():
    """The one message shown, once, beside the code field after a refused
    code: what happened and what to do."""
    return "%s. %s" % (i18n.t(CLAIM_REFUSED_TITLE), i18n.t(CLAIM_CODE_ERROR))


CLAIM_THROTTLED_TITLE = i18n.msg("admin_fleet.too_many_attempts", "Too many attempts")
CLAIM_THROTTLED_DETAIL = i18n.msg(
    "admin_fleet.wait_a_few_minutes_before_trying_again",
    "Wait a few minutes before trying again.")
CLAIM_EMPTY_CODE = i18n.msg("admin_fleet.enter_the_pairing_code", "Enter the pairing code.")
CLAIM_EMPTY_OWNER = i18n.msg("admin_fleet.choose_an_owner", "Choose an owner.")
CLAIM_OWNER_GONE = i18n.msg(
    "admin_fleet.that_user_is_no_longer_available", "That user is no longer available.")

REGISTER_MAC_ERROR = i18n.msg(
    "admin_fleet.enter_a_valid_mac_address", "Enter a valid MAC address.")
REGISTER_HASH_ERROR = i18n.msg(
    "admin_fleet.enter_the_64_character_hash", "Enter the 64-character hash.")
REGISTER_HARDWARE_ERROR = i18n.msg(
    "admin_fleet.choose_the_hardware_type", "Choose the hardware type.")


class FleetRow(NamedTuple):
    """One frame as the list shows it. `frame_id` is the device id (live
    and retired-from) or the pending id; `previous_owner` marks a retired
    frame's owner line. `last_seen` is epoch seconds or None; `retired_at`
    (a retired frame) and `code_issued_at` (a pending frame showing a code) are
    epoch seconds or None when the database holds no such moment."""
    kind: str
    frame_id: str
    name: str
    mono_id: str
    owner_email: str | None
    previous_owner: bool
    hardware: str
    last_seen: float | None
    battery_percent: int | None
    is_live_frame: bool
    offline: bool
    state: str | None = None
    screen_off: bool = False
    retired_at: int | None = None
    code_issued_at: int | None = None


class FleetView(NamedTuple):
    """Everything the page renders. `owners` is a (value, label) sequence;
    `register_errors` holds the messages of a refused scripted registration.
    `access` is a tuple of (frame id, co_managers_card.CardView) for the
    frames whose Manage access dialog is offered; `open_access` is the frame
    id whose dialog renders open."""
    rows: tuple
    owners: tuple
    now: datetime.datetime
    register_errors: tuple = ()
    access: tuple = ()
    open_access: str = ""


def _problem_rank(row):
    if row.kind != KIND_LIVE:
        return 2
    state = frame_status.frame_status(row).dot_state
    return _PROBLEM_STATES.index(state) if state in _PROBLEM_STATES else 2


def sort_rows(rows):
    """Live frames first (errors, then warnings, then the rest by name),
    then pending, then retired; ties by id."""
    return sorted(
        rows, key=lambda row: (
            _KIND_ORDER[row.kind], _problem_rank(row), row.name.casefold(),
            row.frame_id))


def _routes():
    # Imported on use: companion.console_routes imports the route modules,
    # which import this page.
    from companion import console_routes
    return console_routes


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _slug(prefix, frame_id):
    """A dialog id for a frame: device and pending ids carry an underscore
    that a dialog slug does not allow."""
    return "%s-%s" % (prefix, frame_id.lower().replace("_", "-"))


def _display_name(row):
    if row.kind == KIND_PENDING:
        return i18n.t(_NEW_FRAME)
    if row.is_live_frame and row.name == device_scope.LIVE_NAME:
        return i18n.t(_LIVE_FRAME_NAME)
    return row.name or i18n.t(_UNNAMED_FRAME)


def _owner_line(row):
    if row.kind == KIND_PENDING:
        return i18n.t(_WAITING_FOR_PAIRING)
    if row.owner_email is None:
        return i18n.t(_UNASSIGNED)
    if row.previous_owner:
        return i18n.t(_FORMERLY) % row.owner_email
    return row.owner_email


def _owner_options(view, placeholder=True):
    options = (
        ['<option value="">%s</option>' % _t(_PAIR_OWNER_CHOOSE)] if placeholder else [])
    for value, label in view.owners:
        options.append('<option value="%s">%s</option>' % (_esc(value), _esc(label)))
    return "".join(options)


def _frame_dialog(
        row, dialog_id, suffix, title, sentence, body_extra, submit, dismiss,
        with_hardware=True, sentence_class="text-body", **flags):
    return ui_modal.dialog_html(
        dialog_id, title % _display_name(row),
        _routes().FRAME_ACTION_PREFIX + row.frame_id + suffix, _ui().csrf_field(),
        '<p class="%s">%s</p>%s' % (sentence_class, _esc(sentence), body_extra),
        i18n.t(submit), i18n.t(dismiss),
        _routes().FLEET_ROUTE if row.kind != KIND_LIVE else "%s?frame=%s&tab=access" % (
            _routes().FLEET_ROUTE, row.frame_id),
        subtitle="%s · %s" % (row.hardware, row.mono_id) if with_hardware else None,
        **flags)


def reassign_action_html(row):
    """The Reassign control beside the owner: the link that opens the
    confirmation dialog. Offered for a live frame only."""
    if row.kind != KIND_LIVE:
        return ""
    return ui_modal.trigger_html(
        _slug("dlg-reassign", row.frame_id), _t(_ACTION_REASSIGN),
        "row-action", i18n.t(_REASSIGN_ARIA) % _display_name(row))


def reassign_dialog_html(row, view):
    """The Reassign confirmation of a live frame: the new owner's picker and
    the sentence saying what the change does."""
    if row.kind != KIND_LIVE:
        return ""
    if row.is_live_frame:
        sentence = i18n.t(_REASSIGN_LIVE_SENTENCE)
    else:
        sentence = i18n.t(_REASSIGN_SENTENCE) % (
            row.owner_email or i18n.t(_THIS_OWNER))
    field_id = _slug("fleet-reassign", row.frame_id) + "-owner"
    field = (
        '<div class="modal__field"><label for="%s">%s</label>'
        '<select id="%s" name="%s" required data-gate-select%s>%s</select>'
        '<p class="text-label" data-gate-hint hidden>%s</p></div>' % (
            field_id, _t(_NEW_OWNER), field_id, OWNER_FIELD,
            validation_attrs("select"), _owner_options(view),
            _t(_REASSIGN_CHOOSE_HINT)))
    # What the change does, in two lines: a tick when nothing is lost, a
    # warning mark when something is.
    checks = (
        '<ul class="modal__effects">%s%s</ul>' % (
            _check_item(sentence, ok=row.is_live_frame),
            _check_item(i18n.t(_REASSIGN_CO_MANAGERS), ok=False)))
    return ui_modal.dialog_html(
        _slug("dlg-reassign", row.frame_id),
        i18n.t(_TITLE_REASSIGN) % _display_name(row),
        _routes().FRAME_ACTION_PREFIX + row.frame_id + _routes().FRAME_REASSIGN_SUFFIX,
        _ui().csrf_field(), field + checks, i18n.t(_ACTION_REASSIGN), i18n.t(_CANCEL),
        _routes().FLEET_ROUTE if row.kind != KIND_LIVE else "%s?frame=%s&tab=access" % (
            _routes().FLEET_ROUTE, row.frame_id),
        secondary_dismiss=True, destructive=not row.is_live_frame,
        submit_attrs=" data-needs-choice")


def _check_item(text, ok):
    icon = icon_html("icon-check" if ok else "icon-warning", size=20)
    return '<li class="modal__effect modal__effect--%s">%s<span>%s</span></li>' % (
        "ok" if ok else "warn", icon, _esc(text))


def retire_row_html(row):
    """The Retire row of a live frame that can be retired: the warning in the
    danger colour and the link that opens the one confirmation dialog. Empty
    for the served frame, which cannot be retired."""
    if row.kind != KIND_LIVE or row.is_live_frame:
        return ""
    return (
        '<li class="row fleet-retire"><div class="row__main"><span class="row__text">'
        '<span class="row__label">%s</span><span class="row__detail">%s</span></span></div>'
        '%s</li>' % (
            _t(_RETIRE_THIS_FRAME), _t(_RETIRE_HINT),
            ui_modal.trigger_html(
                _slug("dlg-retire", row.frame_id), _t(_RETIRE_ACTION), "fleet-retire__link")))


def _row_dialogs(row):
    if row.kind == KIND_RETIRED:
        return _frame_dialog(
            row, _slug("dlg-reactivate", row.frame_id),
            _routes().FRAME_REACTIVATE_SUFFIX, i18n.t(_TITLE_REACTIVATE),
            i18n.t(_REACTIVATE_SENTENCE), "", _CONFIRM_REACTIVATE, _KEEP_RETIRED,
            destructive=True, confirm_only=True, sentence_class="text-body modal__question")
    if row.kind != KIND_LIVE or row.is_live_frame:
        return ""
    return _frame_dialog(
        row, _slug("dlg-retire", row.frame_id), _routes().FRAME_RETIRE_SUFFIX,
        i18n.t(_TITLE_RETIRE), i18n.t(_RETIRE_SENTENCE), "", _CONFIRM_RETIRE,
        _KEEP_FRAME, destructive=True, confirm_only=True)


def _register_errors_html(view):
    return "".join(
        '<p class="field-error" role="alert">%s</p>' % _esc(message)
        for message in view.register_errors)


def owner_label(email, role):
    """The Owner option text: the email, with "(admin)" for administrators."""
    if role == "admin":
        return "%s %s" % (email, i18n.t(_ADMIN_SUFFIX))
    return email


def unnamed_text():
    return i18n.t(_UNNAMED_FRAME)


def render(view):
    """The Fleet page's frame-independent part: the empty state of a fleet
    without frames and every dialog the page opens (the retire and
    re-activate confirmations)."""
    empty = "" if view.rows else _ui().empty_state(
        i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_BODY), compact=True)
    section = (
        '<section class="page-section" aria-label="%s">%s</section>' % (
            _t(_FRAMES_TEXT), empty) if empty else "")
    dialogs = "".join(_row_dialogs(row) for row in view.rows)
    return _register_errors_html(view) + section + dialogs


# The names the list of frames (fleet_frames_list) shares.
ACTION_PERSONAL_VIEW = _ACTION_PERSONAL_VIEW
OPEN_PERSONAL_ARIA = _OPEN_PERSONAL_ARIA
ACTION_REACTIVATE = _ACTION_REACTIVATE
PAIR_SUBMIT = _PAIR_SUBMIT
WAITING_FOR_PAIRING = _WAITING_FOR_PAIRING
ADD_TITLE = _ADD_TITLE
slug = _slug
display_name = _display_name
owner_line = _owner_line
