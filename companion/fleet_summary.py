"""The Fleet page's desktop summary rows and the dialogs they open.

From 960px the selected frame's detail groups (device and version, the
versions list, the settings form, the access list, the other frames) are
collapsed into one list of summary rows: a title, the current value and a
chevron. A row is a plain `#id` link to a `<dialog class="modal">`; with
script the shared modal script opens it as a modal, without it the `:target`
styles show the same dialog as an in-page card.

Below 960px the same dialogs render as plain blocks (the stylesheet gives
`.fleet-dialog--inline` `display: contents`), so the phone page and its
sub-tabs hold exactly the groups they always did. Every interpolated value is
escaped here; callers pass pre-escaped markup only for `inner_html` and
`actions_html`.
"""
from companion import i18n, ui_modal
from companion.ui_base import escape_html, icon_html

_CLOSE_TEXT = i18n.msg("common.close", "Close")
_SUMMARY_LABEL = i18n.msg("admin_fleet.summary_label", "Device and settings")
WAKE_LABEL = i18n.msg("admin_fleet.sum_wake", "Wake interval")
_WAKE_DEFAULT = i18n.msg("admin_fleet.sum_wake_default", "Server default")
_WAKE_MINUTES = i18n.msg("admin_fleet.sum_wake_minutes", "Every %d min")
_WAKE_SECONDS = i18n.msg("admin_fleet.sum_wake_seconds", "Every %d s")
VERSIONS_LABEL = i18n.msg("admin_fleet.sum_versions", "Version history")
_VERSIONS_NONE = i18n.msg("admin_fleet.sum_versions_none", "No releases yet")
_VERSIONS_ONE = i18n.msg("admin_fleet.sum_versions_one", "1 release")
_VERSIONS_MANY = i18n.msg("admin_fleet.sum_versions_many", "%d releases")
_VERSION_INSTALLED = i18n.msg("admin_fleet.sum_installed", "%s installed")
_NO_VERSION = i18n.msg("admin_fleet.sum_no_version", "No version reported yet")
_ACCESS_ONE = i18n.msg("admin_fleet.sum_access_one", "%s + 1 co-manager")
_ACCESS_MANY = i18n.msg("admin_fleet.sum_access_many", "%s + %d co-managers")
OTHERS_LABEL = i18n.msg("admin_fleet.sum_other_label", "Other frames")
_OTHERS_VALUE = i18n.msg("admin_fleet.sum_other_value", "%d pending or retired")
_SAVE = i18n.msg("admin_fleet.sum_save", "Save")
_CANCEL = i18n.msg("admin_fleet.sum_cancel", "Cancel")
_DONE = i18n.msg("admin_fleet.sum_done", "Done")

DEVICE_DIALOG = "dlg-fleet-device"
VERSIONS_DIALOG = "dlg-fleet-versions"
SETTINGS_DIALOG = "dlg-fleet-settings"
OTHERS_DIALOG = "dlg-fleet-others"


def wake_value(seconds):
    """The wake interval as the row quotes it."""
    if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds <= 0:
        return i18n.t(_WAKE_DEFAULT)
    if seconds % 60 == 0:
        return i18n.t(_WAKE_MINUTES) % (seconds // 60)
    return i18n.t(_WAKE_SECONDS) % seconds


def versions_value(running, count):
    """The Versions row's value: the number of releases, then the installed one."""
    if not count:
        text = i18n.t(_VERSIONS_NONE)
    elif count == 1:
        text = i18n.t(_VERSIONS_ONE)
    else:
        text = i18n.t(_VERSIONS_MANY) % count
    if running:
        text += " · " + i18n.t(_VERSION_INSTALLED) % running
    return text


def device_value(model, running):
    return "%s · %s" % (model, running or i18n.t(_NO_VERSION))


def access_value(owner_email, co_managers):
    if co_managers == 1:
        return i18n.t(_ACCESS_ONE) % owner_email
    if co_managers > 1:
        return i18n.t(_ACCESS_MANY) % (owner_email, co_managers)
    return owner_email


def others_value(count):
    return i18n.t(_OTHERS_VALUE) % count


def row(icon_id, label, value, dialog_id):
    """One summary row: a link to `dialog_id` with the icon, the label over the
    value and a chevron. `label` and `value` are plain text."""
    return (
        '<li class="fleet-sum__item"><a class="fleet-sum" href="#%s" data-modal-open '
        'aria-haspopup="dialog">%s<span class="fleet-sum__text">'
        '<span class="fleet-sum__label">%s</span><span class="fleet-sum__value">%s</span>'
        '</span>%s</a></li>'
    ) % (ui_modal.validated_slug(dialog_id), icon_html(icon_id, 20, "fleet-sum__icon"),
         escape_html(label), escape_html(value),
         icon_html("icon-chevron-right", 16, "fleet-sum__chevron"))


def rows_group(rows_html):
    """The one block of summary rows (shown from 960px only)."""
    return (
        '<section class="group-block fleet-block fleet-block--sums" aria-labelledby="fleet-block-sums">'
        '<h2 class="section-label" id="fleet-block-sums">%s</h2>'
        '<ul class="group fleet-sum-list">%s</ul></section>'
    ) % (escape_html(i18n.t(_SUMMARY_LABEL)), rows_html)


def dialog(dialog_id, title, return_href, inner_html, actions_html="", inline=True):
    """A summary row's dialog. `inline` marks one that is also the phone
    page's own block (it renders as plain content below 960px); an
    `inline=False` dialog is closed and hidden there."""
    slug = ui_modal.validated_slug(dialog_id)
    classes = "modal fleet-dialog" + (" fleet-dialog--inline" if inline else "")
    href = escape_html(return_href)
    if not actions_html:
        actions_html = (
            '<a class="modal__dismiss" href="%s" data-modal-close>%s</a>' % (
                href, escape_html(i18n.t(_DONE))))
    return (
        '<dialog class="%s" id="%s" aria-labelledby="%s-title">'
        '<header class="modal__head"><div>'
        '<h2 class="modal__title text-heading" id="%s-title">%s</h2></div>'
        '<a class="modal__close" href="%s" data-modal-close aria-label="%s">%s</a></header>'
        '<div class="modal__body">%s</div>'
        '<div class="modal__actions">%s</div></dialog>\n'
    ) % (classes, slug, slug, slug, escape_html(title), href,
         escape_html(i18n.t(_CLOSE_TEXT)), icon_html("icon-close", size=20),
         inner_html, actions_html)


def settings_actions(form_id):
    """Save and Cancel for the settings form that lives in the dialog. Save is
    a plain button that makes the shared modal script submit the form (the page
    keeps a single submit control per form: its own Save bar, which is also the
    way to save without script); Cancel resets the form and the script then
    closes the dialog."""
    return (
        '<button type="button" form="%s" class="fleet-dialog__save" data-modal-submit="%s">%s</button>'
        '<button type="reset" form="%s" class="modal__dismiss" data-modal-reset-close>%s</button>'
    ) % (escape_html(form_id), escape_html(form_id), escape_html(i18n.t(_SAVE)),
         escape_html(form_id), escape_html(i18n.t(_CANCEL)))
