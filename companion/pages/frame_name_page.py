"""The Rename frame page: one text field and the common floating Save bar.

Pure markup: it takes the frame's current name and an optional error and
reads nothing else. The name is typed text, escaped into the input's value;
it never reaches a path or an attribute other than that value.
"""
from urllib.parse import quote

from companion import i18n, layout, ui_components, ui_save_bar
from companion.ui_base import escape_html, validation_attrs

RENAME_ROUTE = "/frame/name"
NAME_FIELD = "name"
RETURN_FIELD = "return_to"
FORM_ID = "frame-name-form"
MAX_NAME_CHARS = 40

FLASH_FRAME_RENAMED = "frame_renamed"
FLASH_FRAME_RENAMED_TEXT = i18n.msg(
    "frame_name.flash_renamed", "Frame renamed — the new name shows everywhere.")

TITLE = i18n.msg("frame_name.title", "Rename frame")
PURPOSE = i18n.msg(
    "frame_name.purpose",
    "The name you see in your frames list and in the console. It is not shown on the frame.")
_LABEL = i18n.msg("frame_name.label", "Frame name")
_HELP = i18n.msg("frame_name.help", "Up to 40 characters.")
NAME_ERROR = i18n.msg("frame_name.error", "Enter a name of 1 to 40 characters.")
SAVE_FAILED = i18n.msg(
    "frame_name.failed", "The name could not be saved. Try again in a moment.")
_BACK = i18n.msg("frame_name.back", "Back")
ACTION_TEXT = i18n.msg("frame_name.action", "Rename")
ACTION_ARIA = i18n.msg("frame_name.action_aria", "Rename %s")


def device_route(device_id, return_to=None):
    """The frame's own rename page path. `return_to` is the page the person
    comes from (a caller-built, allow-listed path); the page sends them back
    there when they leave it."""
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


def render(name, form_action, back_href, error="", return_to=None):
    """The page body for a frame currently called `name`; `form_action` is
    the frame's own rename route and `back_href` where Back and Cancel go;
    `return_to` (already validated) is carried by the form to the POST."""
    attrs, error_html = "", ""
    if error:
        attrs = ' aria-invalid="true" aria-describedby="frame-name-error"'
        error_html = '<p class="field-error" id="frame-name-error" role="alert">%s</p>' % (
            escape_html(error))
    field = ui_components.text_field_html(
        "frame-name", NAME_FIELD, i18n.t(_LABEL), name, i18n.t(_HELP), error_html,
        ' maxlength="%d" required autocomplete="off" spellcheck="false"%s%s' % (
            MAX_NAME_CHARS, attrs, validation_attrs("text")))
    carried = (
        '<input type="hidden" name="%s" value="%s">' % (RETURN_FIELD, escape_html(return_to))
        if return_to else "")
    form = (
        '<form id="%s" method="post" action="%s" data-dirty-form novalidate>%s%s%s</form>' % (
            FORM_ID, escape_html(form_action), layout.csrf_field() + carried, field, ""))
    return (
        layout.page_header(i18n.t(TITLE), purpose=i18n.t(PURPOSE))
        + '<a class="form-back" href="%s">%s<span>%s</span></a>' % (
            escape_html(back_href), layout.icon_html("icon-chevron-right", 18),
            escape_html(i18n.t(_BACK)))
        + '<section class="page-section">%s</section>' % form
        + ui_save_bar.save_bar_html(
            FORM_ID, cancel_href=back_href, title=i18n.t(TITLE)))
