"""The Rename frame dialog: one name field, Save and Cancel.

Pure markup: it takes the frame's id and current name and reads the request's
query only to reopen itself after a refused name. The name is typed text,
escaped into the input's value; it never reaches a path or an attribute other
than that value.
"""
from urllib.parse import parse_qsl, quote

from companion import i18n, layout, prefs, ui_components, ui_modal, ui_save_bar
from companion.ui_base import escape_html, validation_attrs

RENAME_ROUTE = "/frame/name"
NAME_FIELD = "name"
RETURN_FIELD = "return_to"
MAX_NAME_CHARS = 40

FLASH_FRAME_RENAMED = "frame_renamed"
FLASH_FRAME_RENAMED_TEXT = i18n.msg(
    "frame_name.flash_renamed", "Frame renamed — the new name shows everywhere.")

TITLE = i18n.msg("frame_name.title", "Rename frame")
LABEL = i18n.msg("frame_name.label", "Frame name")
NAME_ERROR = i18n.msg("frame_name.error", "Enter a name of 1 to 40 characters.")
SAVE_FAILED = i18n.msg(
    "frame_name.failed", "The name could not be saved. Try again in a moment.")
ACTION_TEXT = i18n.msg("frame_name.action", "Rename")
ACTION_ARIA = i18n.msg("frame_name.action_aria", "Rename %s")


# The query a refused name comes back with: the frame whose dialog reopens,
# why it was refused and the value that was typed.
REOPEN_FRAME = "rename"
REOPEN_ERROR = "rename_error"
REOPEN_VALUE = "rename_value"
ERROR_INVALID = "invalid"
ERROR_FAILED = "failed"


def device_route(device_id, return_to=None):
    """The frame's own rename route. A GET there sends the person to the page
    they come from (`return_to`, a caller-built, allow-listed path) with the
    dialog open; the form of that dialog posts to it."""
    route = "/devices/%s%s" % (device_id, RENAME_ROUTE)
    if return_to:
        route += "?%s=%s" % (RETURN_FIELD, quote(return_to, safe=""))
    return route


def normalise_name(raw):
    """The typed name tidied (surrounding and repeated blanks collapsed), or
    None when it is empty, too long or holds a control character."""
    if not isinstance(raw, str):
        return None
    name = " ".join(raw.split())
    if not name or len(name) > MAX_NAME_CHARS:
        return None
    if any(not char.isprintable() for char in name):
        return None
    return name


def dialog_id(device_id):
    """The dialog's slug: device ids carry underscores a slug does not allow."""
    return "dlg-rename-%s" % str(device_id).lower().replace("_", "-")


def opener_href(device_id):
    return "#" + dialog_id(device_id)


def opener_html(device_id, label_html, extra_class="", aria_label=""):
    """The link that opens the frame's Rename dialog (a hash link, so it works
    without script too). `label_html` is already escaped."""
    return ui_modal.trigger_html(dialog_id(device_id), label_html, extra_class, aria_label)


def reopen_query(error, value):
    """The query parameters a refused rename comes back with."""
    return "%s=%s&%s=%s" % (
        REOPEN_ERROR, error, REOPEN_VALUE, quote(value, safe=""))


def _reopened(device_id):
    """(error message, typed value) when this request comes back from a refused
    rename of `device_id`, else None."""
    query = dict(parse_qsl(prefs.current_request_query() or "", keep_blank_values=True))
    if query.get(REOPEN_FRAME) != str(device_id):
        return None
    message = SAVE_FAILED if query.get(REOPEN_ERROR) == ERROR_FAILED else NAME_ERROR
    return i18n.t(message), query.get(REOPEN_VALUE, "")[:MAX_NAME_CHARS]


def dialog_html(device_id, name, return_to):
    """The Rename dialog of one frame currently called `name` ("" when it has
    none): a title, the name field, Save and Cancel; a bottom sheet on a phone.
    `return_to` is the page the dialog sits on (a caller-built path): Cancel and
    the close cross go there and the POST sends the person back there. The
    dialog renders open, with the error and the typed value, when the request
    comes back from a refused name."""
    slug = dialog_id(device_id)
    error = _reopened(device_id)
    value = name if error is None else error[1]
    attrs, error_html = "", ""
    if error is not None:
        attrs = ' aria-invalid="true" aria-describedby="%s"' % escape_html(
            ui_modal.error_id(slug, NAME_FIELD))
        error_html = ui_modal.field_error_html(slug, NAME_FIELD, error[0])
    field = ui_components.text_field_html(
        slug + "-name", NAME_FIELD, i18n.t(LABEL), value, "", error_html,
        ' maxlength="%d" required autocomplete="off" spellcheck="false"%s%s' % (
            MAX_NAME_CHARS, attrs, validation_attrs("text")))
    carried = '<input type="hidden" name="%s" value="%s">' % (
        RETURN_FIELD, escape_html(return_to))
    return ui_modal.dialog_html(
        slug, i18n.t(TITLE), device_route(device_id), layout.csrf_field() + carried, field,
        i18n.t(ui_save_bar.SAVE_TEXT), i18n.t(ui_save_bar.CANCEL_TEXT), return_to,
        open_=error is not None, return_on_close=True, variant="compact-top",
        scrim_close=True)
