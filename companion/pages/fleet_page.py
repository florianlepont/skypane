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

from companion import frame_status, i18n, ui_entity_list, ui_modal
from companion.ui_base import escape_html

FLEET_PURPOSE = i18n.msg(
    "admin_fleet.every_frame_on_the_platform_who_owns_it_and_whether_it",
    "Every frame on the platform: who owns it and whether it is up to date.")

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

ADD_DIALOG_ID = "dlg-add-frame"

_FRAMES_TEXT = i18n.msg("admin_fleet.frames", "Frames")
_COUNT_MANY = i18n.msg("admin_fleet.n_frames", "%d frames")
_COUNT_ONE = i18n.msg("admin_fleet.one_frame", "1 frame")
_ATTENTION_MANY = i18n.msg("admin_fleet.n_need_attention", "%d need attention")
_ATTENTION_ONE = i18n.msg("admin_fleet.one_needs_attention", "1 needs attention")
_UNNAMED_FRAME = i18n.msg("admin_fleet.unnamed_frame", "Unnamed frame")
_NEW_FRAME = i18n.msg("admin_fleet.new_frame", "New frame")
_WAITING_FOR_PAIRING = i18n.msg("admin_fleet.waiting_for_pairing", "Waiting for pairing")
_FORMERLY = i18n.msg("admin_fleet.formerly_owner", "Formerly %s")
_UNASSIGNED = i18n.msg("admin_fleet.unassigned", "Unassigned")
_RETIRED_GROUP = i18n.msg("admin_fleet.retired_frames_n", "Retired frames (%d)")
_ROW_MENU_ARIA = i18n.msg("admin_fleet.actions_for_frame", "Actions for %s")
_EMPTY_HEADING = i18n.msg("admin_fleet.no_frames_yet", "No frames yet")
_EMPTY_BODY = i18n.msg(
    "admin_fleet.switch_a_frame_on_when_its_pairing_code_appears_choose_add",
    "Switch a frame on. When its pairing code appears on its screen, choose "
    "Add a frame.")

_ACTION_OPEN = i18n.msg("admin_fleet.open_frame", "Open frame")
_ACTION_REASSIGN = i18n.msg("admin_fleet.reassign", "Reassign")
_ACTION_RETIRE = i18n.msg("admin_fleet.retire", "Retire")
_ACTION_REACTIVATE = i18n.msg("admin_fleet.re_activate", "Re-activate")
_CONFIRM_REASSIGN = i18n.msg("admin_fleet.reassign_frame", "Reassign frame")
_CONFIRM_RETIRE = i18n.msg("admin_fleet.retire_frame", "Retire frame")
_CONFIRM_REACTIVATE = i18n.msg("admin_fleet.re_activate_frame", "Re-activate frame")
_KEEP_FRAME = i18n.msg("admin_fleet.keep_frame", "Keep frame")
_KEEP_OWNER = i18n.msg("admin_fleet.keep_current_owner", "Keep current owner")
_KEEP_RETIRED = i18n.msg("admin_fleet.keep_retired", "Keep retired")
_TITLE_RETIRE = i18n.msg("admin_fleet.retire_frame_title", "Retire “%s”?")
_TITLE_REASSIGN = i18n.msg("admin_fleet.reassign_frame_title", "Reassign “%s”")
_TITLE_REACTIVATE = i18n.msg(
    "admin_fleet.re_activate_frame_title", "Re-activate “%s”?")
_NEW_OWNER = i18n.msg("admin_fleet.new_owner", "New owner")
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
    "Only the owner changes. Nothing is erased.")
_THIS_OWNER = i18n.msg("admin_fleet.the_current_owner", "The current owner")

_ADD_BUTTON = i18n.msg("admin_fleet.add_a_frame_button", "+ Add a frame")
_ADD_TITLE = i18n.msg("admin_fleet.add_a_frame", "Add a frame")
_BACK_TO_FLEET = i18n.msg("admin_fleet.back_to_fleet", "Back to Fleet")
_PAIR_PURPOSE = i18n.msg(
    "admin_fleet.enter_the_code_shown_on_the_frame_s_screen_and_choose",
    "Enter the code shown on the frame's screen and choose who it belongs to.")
_PAIR_CODE_LABEL = i18n.msg("admin_fleet.pairing_code", "Pairing code")
_PAIR_CODE_HELP = i18n.msg(
    "admin_fleet.the_code_stays_valid_for_about_35_minutes",
    "The code stays valid for about 35 minutes; a new one then appears on the frame.")
_PAIR_OWNER_LABEL = i18n.msg("admin_fleet.pair_owner", "Owner")
_PAIR_OWNER_CHOOSE = i18n.msg("admin_fleet.choose_an_owner_option", "Choose an owner")
_PAIR_SUBMIT = i18n.msg("admin_fleet.pair_frame", "Pair frame")
_PAIR_NONE_WAITING = i18n.msg(
    "admin_fleet.no_frame_is_showing_a_code_yet",
    "No frame is showing a code yet. Switch the frame on; its code appears on "
    "its screen.")
_ADMIN_SUFFIX = i18n.msg("admin_fleet.admin_suffix", "(admin)")
CLAIM_REFUSED_TITLE = i18n.msg("admin_fleet.code_not_recognised", "Code not recognised")
CLAIM_REFUSED_DETAIL = i18n.msg(
    "admin_fleet.the_code_is_wrong_expired_or_already_used",
    "The code is wrong, expired or already used. A new code appears on the "
    "frame within 35 minutes.")
CLAIM_CODE_ERROR = i18n.msg(
    "admin_fleet.check_the_code_and_try_again", "Check the code and try again.")
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
    frame's owner line. `last_seen` is epoch seconds or None."""
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


class FleetView(NamedTuple):
    """Everything the page renders. `owners` is a (value, label) sequence;
    `code_value`, `owner_selected`, the error fields and `open_add_dialog`
    carry the state of a refused submission; `register_errors` the messages
    of a refused scripted registration."""
    rows: tuple
    owners: tuple
    has_pending: bool
    now: datetime.datetime
    code_value: str = ""
    owner_selected: str = ""
    claim_toast_html: str = ""
    code_error: str = ""
    owner_error: str = ""
    open_add_dialog: bool = False
    register_errors: tuple = ()


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
    return row.name or i18n.t(_UNNAMED_FRAME)


def _owner_line(row):
    if row.kind == KIND_PENDING:
        return i18n.t(_WAITING_FOR_PAIRING)
    if row.owner_email is None:
        return i18n.t(_UNASSIGNED)
    if row.previous_owner:
        return i18n.t(_FORMERLY) % row.owner_email
    return row.owner_email


def _menu_items(row):
    """The row menu's (label, target, destructive) items by state: active
    frames open, reassign and retire (the served frame cannot be retired);
    retired frames re-activate; pending frames have no menu."""
    if row.kind == KIND_RETIRED:
        return [(i18n.t(_ACTION_REACTIVATE), _slug("dlg-reactivate", row.frame_id), True)]
    if row.kind != KIND_LIVE:
        return []
    items = [
        (i18n.t(_ACTION_OPEN), "/devices/%s/" % row.frame_id, False),
        (i18n.t(_ACTION_REASSIGN), _slug("dlg-reassign", row.frame_id),
         not row.is_live_frame)]
    if not row.is_live_frame:
        items.append(
            (i18n.t(_ACTION_RETIRE), _slug("dlg-retire", row.frame_id), True))
    return items


def _row_html(row):
    name = _display_name(row)
    items = _menu_items(row)
    menu = (
        ui_entity_list.row_menu_html(i18n.t(_ROW_MENU_ARIA) % name, items)
        if items else "")
    href = "/devices/%s/" % row.frame_id if row.kind == KIND_LIVE else None
    return ui_entity_list.entity_row_html(
        frame_status.status_dot_html(row), name, _owner_line(row), "", menu, href)


def _count_text(rows):
    shown = [row for row in rows if row.kind != KIND_RETIRED]
    text = i18n.t(_COUNT_ONE) if len(shown) == 1 else i18n.t(_COUNT_MANY) % len(shown)
    attention = sum(1 for row in shown if _problem_rank(row) < 2)
    if attention:
        text += " · " + (
            i18n.t(_ATTENTION_ONE) if attention == 1
            else i18n.t(_ATTENTION_MANY) % attention)
    return text


def _list_html(rows):
    active = [row for row in rows if row.kind != KIND_RETIRED]
    retired = [row for row in rows if row.kind == KIND_RETIRED]
    if active:
        main = ui_entity_list.entity_list_html(
            "".join(_row_html(row) for row in active),
            ui_entity_list.count_line_html(_count_text(rows)))
    else:
        main = _ui().empty_state(
            i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_BODY), compact=True)
    if not retired:
        return main
    return main + (
        '<details class="fleet-retired"><summary>%s</summary>%s</details>' % (
            _esc(i18n.t(_RETIRED_GROUP) % len(retired)),
            ui_entity_list.entity_list_html("".join(_row_html(row) for row in retired))))


def _owner_options(view, placeholder=True):
    options = (
        ['<option value="">%s</option>' % _t(_PAIR_OWNER_CHOOSE)] if placeholder else [])
    for value, label in view.owners:
        selected = " selected" if value == view.owner_selected else ""
        options.append(
            '<option value="%s"%s>%s</option>' % (_esc(value), selected, _esc(label)))
    return "".join(options)


def _field_error(dialog_id, field, message):
    """(attributes for the control, the error paragraph) of one field."""
    if not message:
        return "", ""
    return (
        ' aria-invalid="true" aria-describedby="%s"' % _esc(ui_modal.error_id(dialog_id, field)),
        ui_modal.field_error_html(dialog_id, field, message))


def _add_dialog(view):
    code_attrs, code_error = _field_error(ADD_DIALOG_ID, "code", view.code_error)
    owner_attrs, owner_error = _field_error(ADD_DIALOG_ID, "owner", view.owner_error)
    none_waiting = (
        "" if view.has_pending
        else '<p class="text-label">%s</p>' % _t(_PAIR_NONE_WAITING))
    body = (
        '%s<p class="text-body">%s</p>'
        '<div class="modal__field"><label for="pair-code">%s</label>'
        '<input type="text" id="pair-code" name="%s" class="mono" '
        'autocomplete="off" autocapitalize="characters" spellcheck="false" '
        'inputmode="text" maxlength="12" placeholder="XXXX-XXXX" value="%s"%s>%s'
        '<p class="text-label">%s</p></div>'
        '<div class="modal__field"><label for="pair-owner">%s</label>'
        '<select id="pair-owner" name="%s"%s>%s</select>%s</div>%s' % (
            view.claim_toast_html, _t(_PAIR_PURPOSE), _t(_PAIR_CODE_LABEL),
            CODE_FIELD, _esc(view.code_value), code_attrs, code_error,
            _t(_PAIR_CODE_HELP), _t(_PAIR_OWNER_LABEL), OWNER_FIELD, owner_attrs,
            _owner_options(view), owner_error, none_waiting))
    return ui_modal.dialog_html(
        ADD_DIALOG_ID, i18n.t(_ADD_TITLE), _routes().FLEET_PAIR_ROUTE,
        _ui().csrf_field(), body, i18n.t(_PAIR_SUBMIT), i18n.t(_BACK_TO_FLEET),
        _routes().FLEET_ROUTE, open_=view.open_add_dialog)


def _frame_dialog(
        row, dialog_id, suffix, title, sentence, body_extra, submit, dismiss, **flags):
    return ui_modal.dialog_html(
        dialog_id, title % _display_name(row),
        _routes().FRAME_ACTION_PREFIX + row.frame_id + suffix, _ui().csrf_field(),
        '<p class="text-body">%s</p>%s' % (_esc(sentence), body_extra),
        i18n.t(submit), i18n.t(dismiss), _routes().FLEET_ROUTE,
        subtitle="%s · %s" % (row.hardware, row.mono_id), **flags)


def _reassign_dialog(row, view):
    if row.is_live_frame:
        sentence = i18n.t(_REASSIGN_LIVE_SENTENCE)
    else:
        sentence = i18n.t(_REASSIGN_SENTENCE) % (
            row.owner_email or i18n.t(_THIS_OWNER))
    dialog_id = _slug("dlg-reassign", row.frame_id)
    picker = (
        '<div class="modal__field"><label for="%s-owner">%s</label>'
        '<select id="%s-owner" name="%s" required>%s</select></div>' % (
            dialog_id, _t(_NEW_OWNER), dialog_id, OWNER_FIELD,
            _owner_options(view._replace(owner_selected=""))))
    return _frame_dialog(
        row, dialog_id, _routes().FRAME_REASSIGN_SUFFIX, i18n.t(_TITLE_REASSIGN),
        sentence, picker, _CONFIRM_REASSIGN, _KEEP_OWNER,
        destructive=not row.is_live_frame)


def _row_dialogs(row, view):
    if row.kind == KIND_RETIRED:
        return _frame_dialog(
            row, _slug("dlg-reactivate", row.frame_id),
            _routes().FRAME_REACTIVATE_SUFFIX, i18n.t(_TITLE_REACTIVATE),
            i18n.t(_REACTIVATE_SENTENCE), "", _CONFIRM_REACTIVATE, _KEEP_RETIRED,
            destructive=True, confirm_only=True)
    if row.kind != KIND_LIVE:
        return ""
    dialogs = _reassign_dialog(row, view)
    if not row.is_live_frame:
        dialogs += _frame_dialog(
            row, _slug("dlg-retire", row.frame_id), _routes().FRAME_RETIRE_SUFFIX,
            i18n.t(_TITLE_RETIRE), i18n.t(_RETIRE_SENTENCE), "", _CONFIRM_RETIRE,
            _KEEP_FRAME, destructive=True, confirm_only=True)
    return dialogs


def _register_errors_html(view):
    return "".join(
        '<p class="field-error" role="alert">%s</p>' % _esc(message)
        for message in view.register_errors)


def header_action_html():
    """The page header's "+ Add a frame" trigger (opens the add dialog)."""
    return '<div class="page-header__actions">%s</div>' % ui_modal.trigger_html(
        ADD_DIALOG_ID, _t(_ADD_BUTTON), "page-header__action")


def owner_label(email, role):
    """The Owner option text: the email, with "(admin)" for administrators."""
    if role == "admin":
        return "%s %s" % (email, i18n.t(_ADMIN_SUFFIX))
    return email


def unnamed_text():
    return i18n.t(_UNNAMED_FRAME)


def render(view):
    """The Fleet page body (the shell supplies the header and nav)."""
    section = '<section class="page-section" aria-label="%s">%s</section>' % (
        _t(_FRAMES_TEXT), _list_html(view.rows))
    dialogs = _add_dialog(view) + "".join(
        _row_dialogs(row, view) for row in view.rows)
    return _register_errors_html(view) + section + dialogs
