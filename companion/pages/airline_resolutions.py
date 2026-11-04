"""The Airline editor's manual resolutions list: one row per hand-typed
prefix name, each with a Delete link that opens a confirm dialog.

Server-rendered only. The Delete link is a hash link to its dialog, so it
works without script; the dialog posts to the existing delete route with the
page's token, and its dismiss control ("Keep resolution") is the safe default
and takes the initial focus.
"""
import hashlib
from urllib.parse import quote

import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.ui_modal as ui_modal
from companion.layout import csrf_field, escape_html

DELETE_ROUTE_PREFIX = "/airlines/manual-resolutions/"
DELETE_ROUTE_SUFFIX = "/delete"

HEADING_TEXT = i18n.msg("airlines.manual_resolutions", "Manual resolutions")
CAPTION_TEXT = i18n.msg(
    "airlines.manual_resolutions_caption",
    "Names you gave to unidentified prefixes.")
DELETE_LINK_TEXT = i18n.msg("airlines.delete_resolution_link", "Delete")
DELETE_ARIA_TEMPLATE = i18n.msg(
    "airlines.delete_resolution_aria", "Delete the resolution %s")
DIALOG_TITLE_TEXT = i18n.msg("airlines.delete_this_resolution", "Delete this resolution?")
DIALOG_BODY_TEMPLATE = i18n.msg(
    "airlines.delete_resolution_body",
    "%s will no longer name flights with this prefix, so they become unidentified again. "
    "Your artwork stays.")
SUBMIT_TEXT = i18n.msg("airlines.delete_resolution", "Delete resolution")
DISMISS_TEXT = i18n.msg("airlines.keep_resolution", "Keep resolution")


def dialog_id(prefix):
    """A lowercase slug built from a short hash of `prefix`, so no stored text
    reaches an element id or a URL fragment."""
    digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()[:10]
    return ui_modal.validated_slug("delete-resolution-%s" % digest)


def delete_action(prefix):
    """The delete route for `prefix` under the current frame's prefix."""
    return device_scope.scoped(
        "%s%s%s" % (DELETE_ROUTE_PREFIX, quote(prefix, safe=""), DELETE_ROUTE_SUFFIX), "POST")


def _row_html(prefix, airline_name, back_href):
    slug = dialog_id(prefix)
    subject = "%s %s" % (airline_name, prefix)
    trigger = ui_modal.trigger_html(
        slug, escape_html(i18n.t(DELETE_LINK_TEXT)),
        "special-row__remove calendar-disconnect-btn", i18n.t(DELETE_ARIA_TEMPLATE) % subject)
    dialog = ui_modal.dialog_html(
        slug, i18n.t(DIALOG_TITLE_TEXT), delete_action(prefix), csrf_field(),
        "<p>%s</p>" % escape_html(i18n.t(DIALOG_BODY_TEMPLATE) % airline_name),
        i18n.t(SUBMIT_TEXT), i18n.t(DISMISS_TEXT), back_href,
        destructive=True, confirm_only=True)
    return (
        '<li class="special-row manual-resolution-row"><div class="special-row__main">'
        '<div class="special-row__text"><p class="special-row__title">'
        '<span class="special-row__tag mono">%s</span>%s</p></div>%s</div>%s</li>'
    ) % (escape_html(prefix), escape_html(airline_name), trigger, dialog)


def section_html(rows, back_href):
    """The list section for `rows`, `(prefix, airline_name)` pairs; `""` when
    there are none. `back_href` is where the dialog's dismiss and close links go."""
    items = "".join(_row_html(prefix, name, back_href) for prefix, name in rows)
    if not items:
        return ""
    return (
        '<section class="page-section manual-resolutions">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<ul class="special-list">%s</ul></section>'
    ) % (escape_html(i18n.t(HEADING_TEXT)), escape_html(i18n.t(CAPTION_TEXT)), items)
