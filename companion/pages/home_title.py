"""The Home page title: the frame's name as the page's one `<h1>`.

Renaming a frame lives in Account (and the Fleet header), not on Home. The
document title and the navigation label stay the page's plain name ("Home" /
"Accueil"). The name is user-supplied and escaped by the shared component.
"""
import companion.i18n as i18n
import companion.ui_components as ui_components
from companion.ui_shell import device_display_name

# The same id as the navigation label and the document title.
_PAGE_NAME = i18n.msg("nav.home", "Home")


def title_html(device):
    """The hero's title row for `device`: its name as the `<h1>`. Without a
    device the title falls back to the page's plain name."""
    if device is None:
        return ui_components.title_action_html(i18n.t(_PAGE_NAME))
    return ui_components.title_action_html(device_display_name(device))
