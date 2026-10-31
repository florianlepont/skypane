"""The Fleet page body: every frame with its owner and state, the "Pair a
frame" card and the "Register a frame" card.

Pure markup: it takes a `FleetView` and reads nothing else. A row carries
only display facts (names, ids, owner email, hardware label, last contact,
battery, firmware); no secret hash, token, pairing code or code expiry ever
reaches this module. The one submitted value it re-renders is the typed
pairing code, escaped into the input's `value` on the immediate response.
"""
import datetime
from typing import NamedTuple

from companion import i18n, ui_time
from companion.ui_base import escape_html

FLEET_PURPOSE = i18n.msg(
    "admin_fleet.every_frame_on_the_platform_with_its_owner_and_state",
    "Every frame on the platform, with its owner and state.")

KIND_LIVE = "live"
KIND_PENDING = "pending"
KIND_RETIRED = "retired"
_KIND_ORDER = {KIND_LIVE: 0, KIND_PENDING: 1, KIND_RETIRED: 2}

CODE_FIELD = "code"
OWNER_FIELD = "owner_user_id"
MAC_FIELD = "mac"
HASH_FIELD = "secret_sha256"
HARDWARE_FIELD = "hardware_type"
PAIR_QUERY_FLAG = "pair"

_FRAMES_TEXT = i18n.msg("admin_fleet.frames", "Frames")
_COUNT_MANY = i18n.msg("admin_fleet.n_frames", "%d frames")
_COUNT_ONE = i18n.msg("admin_fleet.one_frame", "1 frame")
_COL_FRAME = i18n.msg("admin_fleet.frame", "Frame")
_COL_OWNER = i18n.msg("admin_fleet.owner", "Owner")
_COL_HARDWARE = i18n.msg("admin_fleet.hardware", "Hardware")
_COL_LAST_SEEN = i18n.msg("admin_fleet.last_seen", "Last seen")
_COL_BATTERY = i18n.msg("admin_fleet.battery", "Battery")
_COL_FIRMWARE = i18n.msg("admin_fleet.firmware", "Firmware")
_COL_STATUS = i18n.msg("admin_fleet.status", "Status")
_COL_ACTIONS = i18n.msg("admin_fleet.actions", "Actions")
_UNNAMED_FRAME = i18n.msg("admin_fleet.unnamed_frame", "Unnamed frame")
_NOT_AVAILABLE = i18n.msg("admin_fleet.n_a", "n/a")
_NEVER_SEEN = i18n.msg("admin_fleet.never_seen", "Never")
_WAITING_FOR_PAIRING = i18n.msg("admin_fleet.waiting_for_pairing", "Waiting for pairing")
_FORMERLY = i18n.msg("admin_fleet.formerly", "formerly %s")
_UNASSIGNED = i18n.msg("admin_fleet.unassigned", "Unassigned")
_BADGE_LIVE = i18n.msg("admin_fleet.live", "Live")
_BADGE_PENDING = i18n.msg("admin_fleet.pending", "Pending")
_BADGE_RETIRED = i18n.msg("admin_fleet.retired", "Retired")
_BADGE_LOW_BATTERY = i18n.msg("admin_fleet.low_battery", "Low battery")
_BADGE_NO_CONTACT = i18n.msg("admin_fleet.no_recent_contact", "No recent contact")
_EMPTY_HEADING = i18n.msg("admin_fleet.no_frames_yet", "No frames yet")
_EMPTY_BODY = i18n.msg(
    "admin_fleet.register_a_frame_below_then_enter_the_code_shown_on",
    "Register a frame below, then enter the code shown on its screen.")

_ACTION_OPEN = i18n.msg("admin_fleet.open_frame", "Open frame")
_ACTION_REASSIGN = i18n.msg("admin_fleet.reassign", "Reassign")
_ACTION_RETIRE = i18n.msg("admin_fleet.retire", "Retire")
_ACTION_REACTIVATE = i18n.msg("admin_fleet.re_activate", "Re-activate")
_CONFIRM_REASSIGN = i18n.msg("admin_fleet.reassign_frame", "Reassign frame")
_CONFIRM_RETIRE = i18n.msg("admin_fleet.retire_frame", "Retire frame")
_CONFIRM_REACTIVATE = i18n.msg("admin_fleet.re_activate_frame", "Re-activate frame")
_KEEP_FRAME = i18n.msg("admin_fleet.keep_frame", "Keep frame")
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

_PAIR_TITLE = i18n.msg("admin_fleet.pair_a_frame", "Pair a frame")
_PAIR_PURPOSE = i18n.msg(
    "admin_fleet.enter_the_code_shown_on_the_frame_s_screen_and_choose",
    "Enter the code shown on the frame's screen and choose who it belongs to.")
_PAIR_CODE_LABEL = i18n.msg("admin_fleet.pairing_code", "Pairing code")
_PAIR_OWNER_LABEL = i18n.msg("admin_fleet.pair_owner", "Owner")
_PAIR_OWNER_CHOOSE = i18n.msg("admin_fleet.choose_an_owner_option", "Choose an owner")
_PAIR_SUBMIT = i18n.msg("admin_fleet.pair_frame", "Pair frame")
_PAIR_NONE_WAITING = i18n.msg(
    "admin_fleet.no_frame_is_waiting_for_a_code_register_one_first",
    "No frame is waiting for a code. Register one first.")
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

_REGISTER_TITLE = i18n.msg("admin_fleet.register_a_frame", "Register a frame")
_REGISTER_PURPOSE = i18n.msg(
    "admin_fleet.use_the_mac_and_secret_hash_printed_by_the_provisioning",
    "Use the MAC and secret hash printed by the provisioning script. The "
    "secret itself is never entered here.")
_REGISTER_MAC_LABEL = i18n.msg("admin_fleet.mac_address", "MAC address")
_REGISTER_HASH_LABEL = i18n.msg("admin_fleet.secret_hash_sha_256", "Secret hash (SHA-256)")
_REGISTER_HASH_PLACEHOLDER = i18n.msg("admin_fleet.64_hex_characters", "64 hex characters")
_REGISTER_HASH_HELP = i18n.msg(
    "admin_fleet.paste_the_sha_256_value_only",
    "Paste the SHA-256 value only. If you paste anything that is not 64 hex "
    "characters it is refused.")
_REGISTER_HARDWARE_LABEL = i18n.msg("admin_fleet.hardware_label", "Hardware")
_REGISTER_SUBMIT = i18n.msg("admin_fleet.register_frame", "Register frame")
REGISTER_MAC_ERROR = i18n.msg(
    "admin_fleet.enter_a_valid_mac_address", "Enter a valid MAC address.")
REGISTER_HASH_ERROR = i18n.msg(
    "admin_fleet.enter_the_64_character_hash", "Enter the 64-character hash.")
REGISTER_HARDWARE_ERROR = i18n.msg(
    "admin_fleet.choose_the_hardware_type", "Choose the hardware type.")

_HEX64_PATTERN = "[0-9A-Fa-f]{64}"


class FleetRow(NamedTuple):
    """One frame as the table shows it. `frame_id` is the device id (live
    and retired-from) or the pending id; `previous_owner` marks a retired
    frame's owner cell. `last_seen` is epoch seconds or None."""
    kind: str
    frame_id: str
    name: str
    mono_id: str
    owner_email: str | None
    previous_owner: bool
    hardware: str
    last_seen: float | None
    battery_percent: int | None
    firmware: str
    is_live_frame: bool
    offline: bool


class FleetView(NamedTuple):
    """Everything the page renders. `owners` and `hardware_choices` are
    (value, label) pairs; `code_value`, `owner_selected` and the error
    fields carry the state of a refused submission."""
    rows: tuple
    owners: tuple
    hardware_choices: tuple
    has_pending: bool
    now: datetime.datetime
    code_value: str = ""
    owner_selected: str = ""
    claim_toast_html: str = ""
    code_error: str = ""
    owner_error: str = ""
    autofocus_code: bool = False
    mac_value: str = ""
    hash_value: str = ""
    hardware_selected: str = ""
    mac_error: str = ""
    hash_error: str = ""
    hardware_error: str = ""


def sort_rows(rows):
    """Live first, then pending, then retired; most recently seen first
    inside each group, never-seen last."""
    return sorted(
        rows, key=lambda row: (
            _KIND_ORDER[row.kind], row.last_seen is None, -(row.last_seen or 0),
            row.frame_id))


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _routes():
    # Imported on use: companion.console_routes imports the route modules,
    # which import this page.
    from companion import console_routes
    return console_routes


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _badge(label):
    return '<span class="banner__pill">%s</span>' % _t(label)


def _badges_html(row):
    kind_label = {
        KIND_LIVE: _BADGE_LIVE, KIND_PENDING: _BADGE_PENDING,
        KIND_RETIRED: _BADGE_RETIRED}[row.kind]
    badges = [_badge(kind_label)]
    if row.kind == KIND_LIVE and row.offline:
        badges.append(_badge(_BADGE_NO_CONTACT))
    if (
            row.kind == KIND_LIVE and row.battery_percent is not None
            and row.battery_percent <= _low_battery_percent()):
        badges.append(_badge(_BADGE_LOW_BATTERY))
    return " ".join(badges)


def _low_battery_percent():
    from companion import battery
    return battery.LOW_BATTERY_DISPLAY_PERCENT


def _frame_cell_html(row):
    return (
        '<span class="cell-primary text-heading">%s</span>'
        '<span class="cell-secondary mono">%s</span>'
        % (_esc(row.name), _esc(row.mono_id)))


def _owner_cell_html(row):
    if row.kind == KIND_PENDING:
        return '<span class="text-label">%s</span>' % _t(_WAITING_FOR_PAIRING)
    if row.owner_email is None:
        return '<span class="text-label">%s</span>' % _t(_UNASSIGNED)
    if row.previous_owner:
        return _esc(i18n.t(_FORMERLY) % row.owner_email)
    return _esc(row.owner_email)


def _last_seen_html(row, now):
    if row.last_seen is None:
        return _t(_NEVER_SEEN)
    seen = datetime.datetime.fromtimestamp(row.last_seen, datetime.timezone.utc)
    return (
        '<span class="time-value">%s</span><span class="cell-inline-sep">·</span>'
        '<span class="time-value__age">(%s)</span>' % (
            _esc(ui_time.local_clock_text(seen, now_parsed=now)),
            ui_time.relative_time_html(seen.isoformat(), now.isoformat())))


def _battery_html(row):
    if row.battery_percent is None:
        return _t(_NOT_AVAILABLE)
    return '<span class="time-value">%d%%</span>' % row.battery_percent


def _firmware_html(row):
    return '<span class="mono">%s</span>' % _esc(row.firmware) if row.firmware else ""


def _action_path(frame_id, suffix):
    return _routes().FRAME_ACTION_PREFIX + frame_id + suffix


def _confirm_html(row, suffix, summary_message, button_message, sentence_html, extra_html):
    """The inline two-step confirm: a `<details>` whose summary is the
    quiet action, a consequence sentence, optional fields, the submit and a
    keep-as-is link back to the page. No script, no dialog."""
    return (
        '<details class="fleet-confirm"><summary>%s</summary>'
        '<form method="post" action="%s" class="fleet-confirm__form">%s'
        '<p class="text-body">%s%s</p>%s'
        '<button type="submit" class="calendar-disconnect-btn">%s</button> '
        '<a class="text-link" href="%s">%s</a></form></details>' % (
            _t(summary_message), _esc(_action_path(row.frame_id, suffix)),
            _ui().csrf_field(), _ui().toast_icon_html("warning"), sentence_html,
            extra_html, _t(button_message), _esc(_routes().FLEET_ROUTE),
            _t(_KEEP_FRAME)))


def _reassign_html(row, view, uid):
    if row.is_live_frame:
        sentence = _t(_REASSIGN_LIVE_SENTENCE)
    else:
        who = row.owner_email or i18n.t(_THIS_OWNER)
        sentence = _esc(i18n.t(_REASSIGN_SENTENCE) % who)
    select_id = "reassign-" + uid
    options = "".join(
        '<option value="%s">%s</option>' % (_esc(value), _esc(label))
        for value, label in view.owners)
    picker = (
        '<p><label for="%s">%s</label> <select id="%s" name="%s" required>%s'
        "</select></p>" % (select_id, _t(_NEW_OWNER), select_id, OWNER_FIELD, options))
    return _confirm_html(
        row, _routes().FRAME_REASSIGN_SUFFIX, _ACTION_REASSIGN, _CONFIRM_REASSIGN,
        sentence, picker)


def _actions_html(row, view, uid):
    """The row's actions by state: live frames open, reassign and retire
    (the live frame cannot be retired); pending rows have none; retired
    rows re-activate."""
    parts = []
    if row.kind == KIND_LIVE:
        parts.append('<a class="text-link" href="/devices/%s/">%s</a>' % (
            _esc(row.frame_id), _t(_ACTION_OPEN)))
        parts.append(_reassign_html(row, view, uid))
        if not row.is_live_frame:
            parts.append(_confirm_html(
                row, _routes().FRAME_RETIRE_SUFFIX, _ACTION_RETIRE, _CONFIRM_RETIRE,
                _t(_RETIRE_SENTENCE), ""))
    elif row.kind == KIND_RETIRED:
        parts.append(_confirm_html(
            row, _routes().FRAME_REACTIVATE_SUFFIX, _ACTION_REACTIVATE,
            _CONFIRM_REACTIVATE, _t(_REACTIVATE_SENTENCE), ""))
    return '<div class="fleet-actions">%s</div>' % "".join(parts) if parts else ""


def _table_row_html(row, view):
    return (
        '<tr data-frame="%s" data-kind="%s">'
        "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
        "<td>%s</td><td>%s</td></tr>" % (
            _esc(row.frame_id), row.kind, _frame_cell_html(row), _owner_cell_html(row),
            _esc(row.hardware), _last_seen_html(row, view.now), _battery_html(row),
            _firmware_html(row), _badges_html(row),
            _actions_html(row, view, "t-" + row.frame_id)))


def _pair_label(label, value_html):
    return (
        '<span class="data-card__label">%s</span> '
        '<span class="data-card__value">%s</span>' % (_t(label), value_html))


def _card_row_html(row, view):
    return (
        '<li class="data-card" data-frame="%s" data-kind="%s">'
        '<div class="data-card__primary"><span>%s</span><span>%s</span></div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__action">%s</div></li>' % (
            _esc(row.frame_id), row.kind, _frame_cell_html(row), _badges_html(row),
            _pair_label(_COL_OWNER, _owner_cell_html(row)),
            _pair_label(_COL_HARDWARE, _esc(row.hardware)),
            _pair_label(_COL_LAST_SEEN, _last_seen_html(row, view.now)),
            _pair_label(_COL_BATTERY, _battery_html(row)),
            _pair_label(_COL_FIRMWARE, _firmware_html(row)),
            _actions_html(row, view, "c-" + row.frame_id)))


def _table_html(view):
    heads = "".join("<th>%s</th>" % _t(label) for label in (
        _COL_FRAME, _COL_OWNER, _COL_HARDWARE, _COL_LAST_SEEN, _COL_BATTERY,
        _COL_FIRMWARE, _COL_STATUS, _COL_ACTIONS))
    body = "".join(_table_row_html(row, view) for row in view.rows)
    cards = "".join(_card_row_html(row, view) for row in view.rows)
    # The cards come first: style.css hides the table behind
    # `.data-cards ~ .data-table-wrap` below 960px by sibling order.
    return (
        '<ul class="data-cards">%s</ul>'
        '<div class="data-table-wrap"><table class="data-table data-table--fleet">'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (cards, heads, body))


def _count_html(count):
    text = i18n.t(_COUNT_ONE) if count == 1 else i18n.t(_COUNT_MANY) % count
    return '<p class="filter-bar__count" role="status">%s</p>' % _esc(text)


def _card(heading_id, heading, inner_html, purpose=None):
    purpose_html = (
        '<p class="text-body section-caption">%s</p>' % _t(purpose) if purpose else "")
    return (
        '<section class="page-section page-section--nested" '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s%s</section>'
        % (heading_id, heading_id, _t(heading), purpose_html, inner_html))


def _fleet_card(view):
    if not view.rows:
        inner = _ui().empty_state(
            i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_BODY), compact=True)
    else:
        inner = _count_html(len(view.rows)) + _table_html(view)
    return _card("fleet-frames", _FRAMES_TEXT, inner)


def _field_error(field_id, message):
    if not message:
        return "", ""
    return (
        ' aria-invalid="true" aria-describedby="%s-error"' % field_id,
        '<p class="field-error" id="%s-error">%s</p>' % (field_id, _esc(message)))


def _owner_options(view):
    options = ['<option value="">%s</option>' % _t(_PAIR_OWNER_CHOOSE)]
    for value, label in view.owners:
        selected = " selected" if value == view.owner_selected else ""
        options.append(
            '<option value="%s"%s>%s</option>' % (_esc(value), selected, _esc(label)))
    return "".join(options)


def _pair_card(view):
    code_attrs, code_error = _field_error("pair-code", view.code_error)
    owner_attrs, owner_error = _field_error("pair-owner", view.owner_error)
    form = (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s'
        '<p><label for="pair-code">%s</label>'
        '<input type="text" id="pair-code" name="%s" class="mono" '
        'autocomplete="off" autocapitalize="characters" spellcheck="false" '
        'inputmode="text" maxlength="12" placeholder="XXXX-XXXX" value="%s"%s%s>%s</p>'
        '<p><label for="pair-owner">%s</label>'
        '<select id="pair-owner" name="%s"%s>%s</select>%s</p>'
        '<p><button type="submit">%s</button></p></form>' % (
            _esc(_routes().FLEET_PAIR_ROUTE), _ui().csrf_field(),
            _t(_PAIR_CODE_LABEL), CODE_FIELD, _esc(view.code_value),
            " autofocus" if view.autofocus_code else "", code_attrs, code_error,
            _t(_PAIR_OWNER_LABEL), OWNER_FIELD, owner_attrs, _owner_options(view),
            owner_error, _t(_PAIR_SUBMIT)))
    none_waiting = (
        "" if view.has_pending
        else '<p class="text-label">%s</p>' % _t(_PAIR_NONE_WAITING))
    return _card(
        "fleet-pair", _PAIR_TITLE, view.claim_toast_html + form + none_waiting,
        _PAIR_PURPOSE)


def _hardware_options(view):
    options = ['<option value="">%s</option>' % _t(_PAIR_OWNER_CHOOSE_HARDWARE)]
    for value, label in view.hardware_choices:
        selected = " selected" if value == view.hardware_selected else ""
        options.append(
            '<option value="%s"%s>%s</option>' % (_esc(value), selected, _esc(label)))
    return "".join(options)


_PAIR_OWNER_CHOOSE_HARDWARE = i18n.msg(
    "admin_fleet.choose_the_hardware_option", "Choose the hardware type")


def _register_card(view):
    mac_attrs, mac_error = _field_error("register-mac", view.mac_error)
    hash_attrs, hash_error = _field_error("register-hash", view.hash_error)
    hw_attrs, hw_error = _field_error("register-hardware", view.hardware_error)
    form = (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s'
        '<p><label for="register-mac">%s</label>'
        '<input type="text" id="register-mac" name="%s" class="mono" '
        'autocomplete="off" spellcheck="false" placeholder="AA:BB:CC:DD:EE:FF" '
        'maxlength="17" value="%s"%s>%s</p>'
        '<p><label for="register-hash">%s</label>'
        '<input type="text" id="register-hash" name="%s" class="mono" '
        'autocomplete="off" spellcheck="false" placeholder="%s" maxlength="64" '
        'pattern="%s" value="%s"%s>%s'
        '<span class="text-label section-caption">%s</span></p>'
        '<p><label for="register-hardware">%s</label>'
        '<select id="register-hardware" name="%s"%s>%s</select>%s</p>'
        '<p><button type="submit" class="calendar-disconnect-btn">%s</button></p>'
        "</form>" % (
            _esc(_routes().FLEET_REGISTER_ROUTE), _ui().csrf_field(),
            _t(_REGISTER_MAC_LABEL), MAC_FIELD, _esc(view.mac_value), mac_attrs, mac_error,
            _t(_REGISTER_HASH_LABEL), HASH_FIELD, _t(_REGISTER_HASH_PLACEHOLDER),
            _HEX64_PATTERN, _esc(view.hash_value), hash_attrs, hash_error,
            _t(_REGISTER_HASH_HELP),
            _t(_REGISTER_HARDWARE_LABEL), HARDWARE_FIELD, hw_attrs,
            _hardware_options(view), hw_error, _t(_REGISTER_SUBMIT)))
    return _card("fleet-register", _REGISTER_TITLE, form, _REGISTER_PURPOSE)


def owner_label(email, role):
    """The Owner option text: the email, with "(admin)" for administrators."""
    if role == "admin":
        return "%s %s" % (email, i18n.t(_ADMIN_SUFFIX))
    return email


def unnamed_text():
    return i18n.t(_UNNAMED_FRAME)


def render(view):
    """The Fleet page body (the shell supplies the header and sub-nav)."""
    return _fleet_card(view) + _pair_card(view) + _register_card(view)
