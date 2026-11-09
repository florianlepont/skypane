"""Home's Rename row: the frame's name as a link row of the Frame group, shown
only to the people who may rename it (its owner and administrators)."""
import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.ui_groups as ui_groups
from companion.layout import escape_html
from companion.pages import frame_name_page
from companion.ui_shell import device_display_name

LABEL = i18n.msg("home.rename_frame_label", "Frame name")


def row_html():
    """The link row to the Rename page of this request's frame, or "" when the
    viewer may not rename it."""
    device = device_scope.current_device()
    if device is None or not device_scope.viewer_may_rename_current():
        return ""
    return ui_groups.row(
        i18n.t(LABEL), icon="icon-pencil", href=frame_name_page.device_route(device.id),
        value_html=escape_html(device_display_name(device)),
        extra_class="frame-rename")
