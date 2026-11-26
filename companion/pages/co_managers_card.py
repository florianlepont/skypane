"""Frame co-management: the three POST route paths, the form field names, the
flash keys and their texts, and the pure markup of the Manage access and Leave
this frame dialogs, so the handlers, the dialogs and the flash registry all
read one definition.

The Manage access dialog takes a `CardView` and reads nothing else. It is for
an owner or an administrator only (`can_manage`); the invited-user list reaches
it only through `candidates`, which the view builder fills for an
administrator alone. Its forms post to the frame's own `/devices/<id>/...`
routes, so the host page (Fleet or Account) need not be device-scoped, and
carry the host page path as `return_to` so the dialog reopens after a change.
"""
from typing import NamedTuple

from companion import i18n
from companion.ui_base import escape_html, validation_attrs

ADD_ROUTE = "/co-managers/add"
REMOVE_ROUTE = "/co-managers/remove"
LEAVE_ROUTE = "/co-managers/leave"
REMOVE_FRAME_ROUTE = "/frame/remove"

FIELD_EMAIL = "email"
FIELD_USER_ID = "user_id"
FIELD_RETURN_TO = "return_to"

# The only pages a co-manager form may return to: exact paths, nothing else.
RETURN_FLEET = "/fleet"
RETURN_ACCOUNT = "/account"
RETURN_PATHS = (RETURN_FLEET, RETURN_ACCOUNT)
ACCESS_QUERY = "access"

FLASH_ADDED = "co_manager_added"
FLASH_REMOVED = "co_manager_removed"
FLASH_LEFT = "co_manager_left"
FLASH_ADD_REFUSED = "co_manager_add_refused"
FLASH_FAILED = "co_manager_failed"
FLASH_LEAVE_NOOP = "co_manager_leave_noop"
FLASH_FRAME_REMOVED = "frame_removed"
FLASH_FRAME_REMOVE_REFUSED = "frame_remove_refused"
FLASH_FRAME_REMOVE_LIVE = "frame_remove_live"

# None of these texts carries a placeholder: the typed address, an id or a
# frame name never reaches a flash.
FLASH_ADDED_TEXT = i18n.msg(
    "co_managers.flash_added",
    "Co-manager added — they can now manage this frame.")
FLASH_REMOVED_TEXT = i18n.msg(
    "co_managers.flash_removed",
    "Co-manager removed — they no longer have access to this frame.")
FLASH_LEFT_TEXT = i18n.msg(
    "co_managers.flash_left",
    "You left the frame — it no longer appears in your account.")
FLASH_ADD_REFUSED_TEXT = i18n.msg(
    "co_managers.flash_add_refused",
    "That address can't be added — check the spelling, or ask an "
    "administrator to invite this person first.")
FLASH_FAILED_TEXT = i18n.msg(
    "co_managers.flash_failed",
    "Couldn't update co-managers — try again in a moment.")
FLASH_LEAVE_NOOP_TEXT = i18n.msg(
    "co_managers.flash_leave_noop",
    "Nothing changed — only co-managers can leave a frame.")

FLASH_FRAME_REMOVED_TEXT = i18n.msg(
    "co_managers.flash_frame_removed",
    "Frame removed — it no longer appears in your account.")
FLASH_FRAME_REMOVE_REFUSED_TEXT = i18n.msg(
    "co_managers.flash_frame_remove_refused",
    "Nothing changed — only the owner of a frame can remove it.")
FLASH_FRAME_REMOVE_LIVE_TEXT = i18n.msg(
    "co_managers.flash_frame_remove_live",
    "This frame cannot be removed. Ask an administrator.")

_HEADING = i18n.msg("co_managers.heading", "Co-managers")
_DIALOG_TITLE = i18n.msg("co_managers.dialog_title", "Manage access")
MENU_LABEL = i18n.msg("co_managers.menu_label", "Manage access")
_DONE = i18n.msg("co_managers.done", "Done")
_CANCEL = i18n.msg("co_managers.cancel", "Cancel")
# Same id and English as the Rename frame page's action.
_LEAVE_TITLE = i18n.msg("co_managers.leave_title", "Leave this frame?")
_PILL_OWNER = i18n.msg("co_managers.pill_owner", "Owner")
_PILL_YOU = i18n.msg("co_managers.pill_you", "You")
_PILL_DISABLED = i18n.msg("co_managers.pill_disabled", "Disabled")
_EMPTY_HEADING = i18n.msg("co_managers.empty_heading", "No co-managers yet")
_EMPTY_BODY_OWNER = i18n.msg(
    "co_managers.empty_body_owner",
    "Add someone by e-mail address so they can manage this frame too.")
_EMPTY_BODY_ADMIN = i18n.msg(
    "co_managers.empty_body_admin",
    "Choose an invited person to let them manage this frame too.")
_LABEL_EMAIL = i18n.msg("co_managers.label_email", "E-mail address")
_HELPER_EMAIL = i18n.msg(
    "co_managers.helper_email", "The person must already be invited to SkyPane.")
_LABEL_PERSON = i18n.msg("co_managers.label_person", "Invited person")
_CHOOSE_PERSON = i18n.msg("co_managers.choose_person", "Choose a person")
_NO_CANDIDATES = i18n.msg(
    "co_managers.no_candidates",
    "Everyone who is invited is already on this frame.")
_ADD_BUTTON = i18n.msg("co_managers.add_button", "Add a co-manager")
_ADD_SHORT = i18n.msg("co_managers.add_short", "Add")
_SECTION_OWNER = i18n.msg("co_managers.section_owner", "Owner")
_REMOVE_BUTTON = i18n.msg("co_managers.remove_button", "Remove")
_REMOVE_ARIA = i18n.msg("co_managers.remove_aria", "Remove %s from this frame")
_LEAVE_TEXT = i18n.msg("co_managers.leave", "Leave this frame")
_LEAVE_CONSEQUENCE = i18n.msg(
    "co_managers.leave_loses_access", "You lose access to this frame and its settings.")
_LEAVE_DETAIL = i18n.msg(
    "co_managers.leave_can_be_added_again",
    "The owner or an administrator can add you again.")
_LEAVE_KEEP = i18n.msg("co_managers.leave_keep", "Stay on this frame")

_REMOVE_FRAME_TEXT = i18n.msg("co_managers.remove_frame", "Remove this frame")
_REMOVE_FRAME_TITLE = i18n.msg("co_managers.remove_frame_title", "Remove this frame?")
_REMOVE_FRAME_KEEP = i18n.msg("co_managers.remove_frame_keep", "Keep this frame")
_REMOVE_FRAME_CONSEQUENCE = i18n.msg(
    "co_managers.remove_frame_leaves_your_account",
    "This frame leaves your account and its co-managers lose access.")
_REMOVE_FRAME_DETAIL = i18n.msg(
    "co_managers.remove_frame_can_be_assigned_again",
    "An administrator can assign it to someone again later; its history is kept.")

_MAX_EMAIL_CHARS = 254


class CardView(NamedTuple):
    """What the Manage access dialog shows. `members` is a tuple of
    (user_id, email, disabled); `candidates` is a tuple of e-mails, empty for
    anyone who is not an administrator."""
    owner_email: str
    members: tuple
    candidates: tuple
    viewer_user_id: int | None
    is_admin_viewer: bool
    can_remove_frame: bool = False


def safe_return_to(value):
    """`value` when it is exactly one of the pages a form may return to,
    else None. No prefix, query or look-alike path passes."""
    return value if isinstance(value, str) and value in RETURN_PATHS else None


def dialog_id(prefix, device_id):
    """A dialog slug for a frame: device ids carry underscores that a dialog
    slug does not allow."""
    return "%s-%s" % (prefix, str(device_id).lower().replace("_", "-"))


def access_dialog_id(device_id):
    return dialog_id("dlg-access", device_id)


def leave_dialog_id(device_id):
    return dialog_id("dlg-leave", device_id)


def remove_frame_dialog_id(device_id):
    return dialog_id("dlg-remove-frame", device_id)


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _csrf_field():
    # Imported on use: this module loads while the page registry is importing.
    from companion import layout
    return layout.csrf_field()


def _warning_icon():
    from companion import layout
    return layout.toast_icon_html("warning")


def _frame_route(device_id, route):
    return "/devices/%s%s" % (device_id, route)


def _return_field(return_to):
    return '<input type="hidden" name="%s" value="%s">' % (
        FIELD_RETURN_TO, _esc(return_to))


def _pill(message):
    from companion import ui_components
    return ui_components.pill_html(i18n.t(message))


def _remove_form_html(device_id, user_id, email, return_to):
    return (
        '<form method="post" action="%s" class="co-manager__remove">%s%s'
        '<input type="hidden" name="%s" value="%d">'
        '<button type="submit" class="btn btn--ghost co-manager__remove-btn" aria-label="%s">%s</button>'
        "</form>" % (
            _esc(_frame_route(device_id, REMOVE_ROUTE)), _csrf_field(),
            _return_field(return_to), FIELD_USER_ID, int(user_id),
            _esc(i18n.t(_REMOVE_ARIA) % email), _t(_REMOVE_BUTTON)))


def _empty_html(view):
    from companion import layout
    body = _EMPTY_BODY_ADMIN if view.is_admin_viewer else _EMPTY_BODY_OWNER
    return layout.empty_state(
        i18n.t(_EMPTY_HEADING), i18n.t(body), compact=True)


def _field_ids(device_id, prefix="co-manager"):
    slug = dialog_id(prefix, device_id)
    return slug + "-email", slug + "-person", slug + "-email-help"


def _typed_field_html(device_id, prefix="co-manager", helper=True):
    """The typed e-mail field, with the line saying the person must already be
    invited when `helper`."""
    input_id, _person_id, help_id = _field_ids(device_id, prefix)
    described = ' aria-describedby="%s"' % help_id if helper else ""
    caption = (
        '<p class="text-label section-caption" id="%s">%s</p>' % (help_id, _t(_HELPER_EMAIL))
        if helper else "")
    return (
        '<p><label for="%s">%s</label>'
        '<input type="email" id="%s" name="%s" autocomplete="off" '
        'data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" '
        'autocapitalize="none" spellcheck="false" required maxlength="%d"%s%s></p>%s' % (
            input_id, _t(_LABEL_EMAIL), input_id, FIELD_EMAIL,
            _MAX_EMAIL_CHARS, described, validation_attrs("email"), caption))


def _select_field_html(device_id, candidates, prefix="co-manager"):
    _input_id, person_id, _help_id = _field_ids(device_id, prefix)
    options = '<option value="">%s</option>' % _t(_CHOOSE_PERSON) + "".join(
        '<option value="%s">%s</option>' % (_esc(email), _esc(email))
        for email in candidates)
    return (
        '<p><label for="%s">%s</label>'
        '<select id="%s" name="%s" required%s>%s</select></p>' % (
            person_id, _t(_LABEL_PERSON), person_id, FIELD_EMAIL,
            validation_attrs("select"), options))


def _inline_remove_html(device_id, user_id, email, return_to):
    return _remove_form_html(device_id, user_id, email, return_to).replace(
        'class="co-manager__remove"', 'class="co-manager__remove row__trailing"', 1)


def _pills_html(pills):
    return "".join(_pill(p) for p in pills)


def _inline_add_row(view, device_id, return_to, prefix, in_dialog=False):
    """The Add control as one row: the field, then the primary Add button.
    `in_dialog` is the Manage access dialog's form: the button reads "Add",
    and the picker of an administrator shares one line with it."""
    if view.is_admin_viewer and not view.candidates:
        return '<li class="fleet-group__item"><p class="text-label">%s</p></li>' % (
            _t(_NO_CANDIDATES))
    if view.is_admin_viewer:
        field = _select_field_html(device_id, view.candidates, prefix)
    else:
        field = _typed_field_html(device_id, prefix)
    submit = '<button type="submit">%s</button>' % _t(_ADD_SHORT if in_dialog else _ADD_BUTTON)
    form_class = "row__form row__form--inline" if in_dialog else "row__form"
    return (
        '<li class="row row--form"><form method="post" action="%s" '
        'class="%s" autocomplete="off">%s%s<div class="row__form-field">%s</div>%s'
        "</form></li>" % (
            _esc(_frame_route(device_id, ADD_ROUTE)), form_class, _csrf_field(),
            _return_field(return_to), field, submit))


def add_dialog_id(device_id):
    return dialog_id("dlg-add-co-manager", device_id)


def _add_row_html(view, device_id, return_to, prefix, as_dialog):
    """The Add control: the inline form row, or (`as_dialog`) one row that
    opens the Add co-manager dialog."""
    if not as_dialog or (view.is_admin_viewer and not view.candidates):
        return _inline_add_row(view, device_id, return_to, prefix)
    from companion import ui_groups
    row = ui_groups.row(
        i18n.t(_ADD_BUTTON), icon="icon-plus", href="#" + add_dialog_id(device_id),
        chevron=False, extra_class="access-add")
    return row.replace('<a class="row__main"', '<a class="row__main" data-modal-open', 1)


def add_dialog_html(view, device_id, return_to, dismiss_href, frame_name=""):
    """The Add co-manager dialog of one frame (the picker of invited people
    for an administrator, the typed address for an owner); "" when an
    administrator has nobody left to add."""
    from companion import ui_modal
    if view.is_admin_viewer and not view.candidates:
        return ""
    prefix = "co-manager-dialog"
    field = (
        _select_field_html(device_id, view.candidates, prefix) if view.is_admin_viewer
        else _typed_field_html(device_id, prefix, helper=False))
    return ui_modal.dialog_html(
        add_dialog_id(device_id), i18n.t(_ADD_BUTTON),
        _frame_route(device_id, ADD_ROUTE), _csrf_field(),
        _return_field(return_to) + '<div class="modal__field">%s</div>' % field,
        i18n.t(_ADD_BUTTON), i18n.t(_CANCEL), dismiss_href, subtitle=frame_name or None)


def _email_html(email):
    """An address as one ellipsised line whose title holds the full value."""
    return '<span class="co-manager__email" title="%s">%s</span>' % (_esc(email), _esc(email))


def access_rows_html(
        view, device_id, return_to, id_prefix="co-manager", compact=False,
        owner_action_html="", add_as_dialog=False):
    """The access content of one frame as the rows of a glass group: the owner
    (with `owner_action_html`, such as Reassign, as its trailing control), each
    co-manager with its Remove action as a trailing control, and the Add control
    as a last row (the inline form, or one row opening the Add co-manager dialog
    when `add_as_dialog`). `compact` is the Fleet page's Access section: the
    people and the actions only, with no empty-state text."""
    from companion import ui_groups
    rows = []
    rows.append(ui_groups.row(
        label_html=_email_html(view.owner_email),
        value_html=_pills_html((_PILL_OWNER,)), trailing_html=owner_action_html,
        extra_class="access-person" if owner_action_html else ""))
    for user_id, email, disabled in view.members:
        pills = []
        if view.viewer_user_id is not None and user_id == view.viewer_user_id:
            pills.append(_PILL_YOU)
        if disabled:
            pills.append(_PILL_DISABLED)
        rows.append(ui_groups.row(
            label_html=_email_html(email),
            value_html=_pills_html(pills),
            trailing_html=_inline_remove_html(device_id, user_id, email, return_to),
            extra_class="access-person"))
    if not view.members and not compact:
        rows.append('<li class="fleet-group__item">%s</li>' % _empty_html(view))
    rows.append(_add_row_html(view, device_id, return_to, id_prefix, add_as_dialog))
    return "".join(rows)


def _initials(email):
    """One or two capital letters standing for an address: the first letters of
    the parts of its name (`lea.bernard@x` is LB), else its first letter."""
    local = (email or "").split("@", 1)[0]
    parts = [p for p in local.replace("_", ".").replace("-", ".").split(".") if p]
    letters = "".join(p[0] for p in parts[:2]) or "?"
    return letters.upper()


def _avatar_html(email, owner=False):
    return '<span class="access-avatar%s" aria-hidden="true">%s</span>' % (
        " access-avatar--owner" if owner else "", _esc(_initials(email)))


def _owner_group_html(view, device_id):
    from companion import ui_groups
    row = ui_groups.row(
        label_html=_email_html(view.owner_email), value_html=_pills_html((_PILL_OWNER,)),
        lead_html=_avatar_html(view.owner_email, owner=True), extra_class="access-person")
    return ui_groups.group(
        row, label=i18n.t(_SECTION_OWNER),
        label_id=access_dialog_id(device_id) + "-owner", extra_class="access-section")


def _members_group_html(view, device_id, return_to):
    """The co-managers: one row each with its Remove action, or a dashed
    empty card saying nobody has been added."""
    from companion import ui_groups
    label_id = access_dialog_id(device_id) + "-people"
    if not view.members:
        return ui_groups.group_panel(
            _empty_html(view), label=i18n.t(_HEADING), label_id=label_id,
            extra_class="access-section access-section--empty")
    rows = []
    for user_id, email, disabled in view.members:
        pills = []
        if view.viewer_user_id is not None and user_id == view.viewer_user_id:
            pills.append(_PILL_YOU)
        if disabled:
            pills.append(_PILL_DISABLED)
        rows.append(ui_groups.row(
            label_html=_email_html(email), value_html=_pills_html(pills),
            lead_html=_avatar_html(email),
            trailing_html=_inline_remove_html(device_id, user_id, email, return_to),
            extra_class="access-person"))
    return ui_groups.group(
        "".join(rows), label=i18n.t(_HEADING), label_id=label_id,
        extra_class="access-section")


def _add_group_html(view, device_id, return_to):
    from companion import ui_groups
    row = _inline_add_row(view, device_id, return_to, "co-manager", in_dialog=True)
    return ui_groups.group(
        row, label=i18n.t(_ADD_BUTTON),
        label_id=access_dialog_id(device_id) + "-add", extra_class="access-section")


def manage_access_dialog_html(view, device_id, frame_name, return_to, open_=False):
    """The Manage access dialog of one frame, a bottom sheet on a phone: the
    title with the frame name and a close button, then three labelled glass
    sections (the owner, the co-managers with a Remove action each, the Add
    form), and an action row with the "Remove this frame" danger link at the
    left (owners only) and Done at the right.
    `return_to` is a whitelisted host
    page path (see `safe_return_to`); the forms send it back so the dialog
    reopens there after a change. `open_` renders it open."""
    from companion import ui_modal
    body = (
        _owner_group_html(view, device_id)
        + _members_group_html(view, device_id, return_to)
        + _add_group_html(view, device_id, return_to))
    leading = _remove_frame_link_html(device_id) if view.can_remove_frame else ""
    dialog = ui_modal.sections_dialog_html(
        access_dialog_id(device_id), i18n.t(_DIALOG_TITLE), frame_name,
        body, i18n.t(_DONE), return_to, open_=open_,
        extra_class="access-sheet", leading_action_html=leading)
    if view.can_remove_frame:
        dialog += remove_frame_dialog_html(device_id, frame_name)
    return dialog


def _remove_frame_link_html(device_id):
    """The danger link at the left of the action row: a link of its own
    rather than a second surface. It opens the removal confirmation, which
    stacks over the Manage access dialog."""
    from companion import ui_modal
    return ui_modal.trigger_html(
        remove_frame_dialog_id(device_id), _t(_REMOVE_FRAME_TEXT),
        "access-remove-frame__link")


def remove_frame_dialog_html(device_id, frame_name):
    """The confirmation of an owner removing their frame. The form posts no
    id; the server acts on the frame in the path, for its owner only."""
    from companion import ui_modal
    body = '<p class="text-body">%s%s</p>%s' % (
        _warning_icon(), _t(_REMOVE_FRAME_CONSEQUENCE),
        ui_modal.more_html('<p class="text-body">%s</p>' % _t(_REMOVE_FRAME_DETAIL)))
    return ui_modal.dialog_html(
        remove_frame_dialog_id(device_id), i18n.t(_REMOVE_FRAME_TITLE),
        _frame_route(device_id, REMOVE_FRAME_ROUTE), _csrf_field(), body,
        i18n.t(_REMOVE_FRAME_TEXT), i18n.t(_REMOVE_FRAME_KEEP), RETURN_ACCOUNT,
        destructive=True, confirm_only=True, subtitle=frame_name)


def leave_dialog_html(device_id, frame_name, return_to=RETURN_ACCOUNT):
    """The confirm-only Leave this frame dialog. The form posts no id; the
    server acts on the caller's own membership."""
    from companion import ui_modal
    body = '<p class="text-body">%s%s</p>%s' % (
        _warning_icon(), _t(_LEAVE_CONSEQUENCE),
        ui_modal.more_html('<p class="text-body">%s</p>' % _t(_LEAVE_DETAIL)))
    return ui_modal.dialog_html(
        leave_dialog_id(device_id), i18n.t(_LEAVE_TITLE),
        _frame_route(device_id, LEAVE_ROUTE), _csrf_field(), body,
        i18n.t(_LEAVE_TEXT), i18n.t(_LEAVE_KEEP), return_to,
        destructive=True, confirm_only=True, subtitle=frame_name)
