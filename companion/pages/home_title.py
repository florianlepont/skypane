"""The Home page title: the frame's name as the page's one `<h1>`, with a
round pencil beside it that opens the Rename page.

The pencil is shown only to the people who may rename the frame (its owner and
administrators); the Rename route keeps its own server-side check. The
document title and the navigation label stay the page's plain name ("Home" /
"Accueil"). The name is user-supplied and escaped by the shared component.
"""
import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.ui_components as ui_components
from companion.pages import frame_name_page
from companion.ui_shell import device_display_name

# The same id as the navigation label and the document title.
_PAGE_NAME = i18n.msg("nav.home", "Home")
RENAME_ACTION_LABEL = i18n.msg("home.rename_frame_action", "Rename frame")


def title_html(device):
    """The hero's title row for `device`: its name as the `<h1>` and, when
    this viewer may rename it, the rename pencil. Without a device the title
    falls back to the page's plain name."""
    if device is None:
        return ui_components.title_action_html(i18n.t(_PAGE_NAME))
    action = ""
    if device_scope.viewer_may_rename_current():
        action = ui_components.icon_link_html(
            "icon-pencil", i18n.t(RENAME_ACTION_LABEL),
            frame_name_page.device_route(device.id), variant="secondary")
    return ui_components.title_action_html(device_display_name(device), action)
