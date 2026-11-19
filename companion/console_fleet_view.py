"""The Console Fleet page: the list of frames and the views it opens.

`/fleet` shows the list of frames (live, pending and retired, each a link to
`/fleet?frame=<id>`). A live frame opens one column of section cards: State,
Device and version (the model, the running firmware and the version history),
Settings and Access (owner, co-managers, reassign, retire). Each section reuses
the content of the page that used to hold it (Health, Update, Device, Manage
access) with the same forms and POST routes. A pending or retired frame opens
its own page with only its useful action and appears nowhere else. The System
view holds the platform-wide part of the Health page.

On a phone the list and a frame page are separate screens joined by the frame
switch (a chip row); from 960 px the list is a column beside the frame. With no
frame chosen the list shows, and a wide screen also shows the first frame.

Selection is read from the query only to pick one of the rows the request
scope already lists; a value matching none shows the list, so no request text
reaches a path, a query or a filesystem call.
"""
from companion import device_scope, i18n, ui_segmented
from companion.pages import co_managers_card
from companion.ui_base import escape_html
from server import history_db

FRAME_QUERY = "frame"
VIEW_QUERY = "view"
VIEW_SYSTEM = "system"
TAB_QUERY = "tab"
TAB_STATE = "state"
TAB_SETTINGS = "settings"
TAB_ACCESS = "access"
SYSTEM_HREF = "/fleet?%s=%s" % (VIEW_QUERY, VIEW_SYSTEM)
FRAME_HREF_PREFIX = "/fleet?%s=" % FRAME_QUERY



def page_scripts(system=False):
    """The scripts the embedded blocks need: the settings form's dirty bar, value
    controls and the Diagnostic LED quick switch, plus the Install and Roll back
    question dialog on a frame's page, or the Health registry table's copy, filter and
    lookup helpers on the System view."""
    from companion import ui_base
    base = (
        ui_base.DIRTY_STATE_SCRIPT_SRC, ui_base.FRESHNESS_SCRIPT_SRC,
        ui_base.QUICK_SWITCH_SCRIPT_SRC, ui_base.VALUE_CONTROLS_SCRIPT_SRC)
    if not system:
        return (ui_base.UPDATE_QUESTION_SCRIPT_SRC, ui_base.LIST_FILTER_SCRIPT_SRC) + base
    return (
        ui_base.COPY_BUTTON_SCRIPT_SRC, ui_base.LIST_FILTER_SCRIPT_SRC,
        ui_base.PANEL_LOOKUP_SCRIPT_SRC) + base


_SYSTEM_HEADING = i18n.msg("admin_fleet.system_heading", "System")
_STATE_HEADING = i18n.msg("admin_fleet.block_state", "State")
_DEVICE_HEADING = i18n.msg("admin_fleet.block_device_version", "Device and version")
_SETTINGS_HEADING = i18n.msg("admin_fleet.block_settings", "Settings")
_ACCESS_HEADING = i18n.msg("admin_fleet.block_access", "Access")
_TABS_LABEL = i18n.msg("admin_fleet.tabs_label", "Frame sections")
_SYSTEM_EMPTY = i18n.msg(
    "admin_fleet.system_unavailable",
    "No system information is available yet.")
_UNKNOWN_FRAME = i18n.msg("admin_fleet.unknown_frame", "That frame was not found.")

_ID_PREFIX_INLINE = "access-inline"


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def wanted_frame(query):
    """The frame id a query names (`frame=`, or an old `access=` link), or ""."""
    return (query.get(FRAME_QUERY) or query.get("access") or [""])[0]


def selection(query, devices):
    """(selected live device or None, is the System view) for a parsed query.
    The System view is chosen only by the exact `view=system`; a frame is
    chosen only when its id is one of `devices`; otherwise none (the list)."""
    if query.get(VIEW_QUERY) == [VIEW_SYSTEM]:
        return None, True
    wanted = wanted_frame(query)
    for device in devices:
        if device.id == wanted:
            return device, False
    return None, False


def tab_selection(query):
    """The phone sub-tab a query names: only the exact `tab=settings` or
    `tab=access` (an old `access=` link too) leave State, the default."""
    wanted = (query.get(TAB_QUERY) or [""])[0]
    if wanted in (TAB_SETTINGS, TAB_ACCESS):
        return wanted
    return TAB_ACCESS if query.get("access") else TAB_STATE


def tabs_html(frame_id, tab):
    """The State / Settings / Access segmented control (phone only, by the
    stylesheet): three plain links to `/fleet?frame=<id>&tab=<tab>`, the current
    one marked, so it works without script and can be linked to."""
    labels = (
        (TAB_STATE, _STATE_HEADING), (TAB_SETTINGS, _SETTINGS_HEADING),
        (TAB_ACCESS, _ACCESS_HEADING))
    links = [
        ("%s%s&amp;%s=%s" % (FRAME_HREF_PREFIX, _esc(frame_id), TAB_QUERY, key),
         "<span>%s</span>" % _t(label), key == tab, "")
        for key, label in labels]
    return ui_segmented.segmented_links_html(
        links, _t(_TABS_LABEL), "fleet-tabs", nav_attrs=' data-tabs="fleet"', carry=True)


def _block(heading_msg, items_html, extra_class="", slug="", heading=""):
    """One block of the selected frame as a grouped list: the section label
    above one glass group. `items_html` is a run of `<li>` items (value rows
    and flush or padded content items)."""
    if not items_html:
        return ""
    from companion import ui_groups
    return ui_groups.group(
        items_html, label=heading or i18n.t(heading_msg), label_id="fleet-block-" + slug,
        extra_class="fleet-block" + extra_class).replace(
            '<ul class="group">', '<ul class="group fleet-group">', 1)


def _item(content_html, flush=False):
    """Free content (forms, health rows, version cards) as one item of a
    block's group; the hairline above it is drawn by the group."""
    if not content_html:
        return ""
    return '<li class="fleet-group__item%s">%s</li>' % (
        " fleet-group__item--flush" if flush else "", content_html)


def _access_html(device, access_views, row, view):
    """The Access rows and the dialogs they open: the owner row carries the
    Reassign control and the Add co-manager row opens its own dialog."""
    from companion.pages import fleet_page
    access = dict(access_views).get(device.id)
    if access is None:
        return "", ""
    rows = co_managers_card.access_rows_html(
        access, device.id, co_managers_card.RETURN_FLEET, _ID_PREFIX_INLINE,
        owner_action_html=fleet_page.reassign_action_html(row) if row else "",
        add_as_dialog=True)
    dismiss = "%s%s&%s=%s" % (FRAME_HREF_PREFIX, device.id, TAB_QUERY, TAB_ACCESS)
    dialogs = co_managers_card.add_dialog_html(
        access, device.id, co_managers_card.RETURN_FLEET, dismiss)
    if row:
        dialogs += fleet_page.reassign_dialog_html(row, view)
    return rows, dialogs


def _access_block(device, access_views, view):
    """The Access section: the owner (with Reassign) and co-managers and, for
    a frame that can be retired, the Retire row whose link opens the one
    confirmation dialog."""
    from companion.pages import fleet_page
    row = next((r for r in view.rows if r.frame_id == device.id), None)
    rows, dialogs = _access_html(device, access_views, row, view)
    if row is not None:
        rows += fleet_page.retire_row_html(row)
    return _block(_ACCESS_HEADING, rows, " fleet-block--access", "access") + dialogs


def frame_html(ctx, device, view, header_html="", tab=TAB_STATE):
    """The selected frame's header and sections. `ctx` is the page context
    built for `device`, whose state directory the History reads must be scoped
    to; `view` is the page's `FleetView`."""
    from companion.pages import config_page, health_page, update_page
    with history_db.connection_scope(device.state_dir):
        device_html, versions_html, _parts = update_page.render_parts(
            ctx, device.hardware_type)
        settings_html = config_page.render(
            ctx, scope=config_page.SCOPE_DEVICE, embedded=True)
        blocks = (
            _block(
                _STATE_HEADING, _item(health_page.frame_state_html(ctx), True),
                " fleet-block--state", "state")
            + _block(
                _DEVICE_HEADING,
                _item(device_html) + _item(versions_html),
                " fleet-block--state fleet-block--device", "device")
            + _block(
                _SETTINGS_HEADING, _item(settings_html),
                " fleet-block--settings", "settings")
            + _access_block(device, view.access, view))
    return (
        '<div class="fleet-frame">' + header_html + tabs_html(device.id, tab)
        + '<div class="fleet-blocks" data-fleet-tab="%s">%s</div></div>' % (tab, blocks)
        + config_page.docked_dirty_bar_html())


def system_html(ctx):
    """The System view for `ctx` (the live frame's context)."""
    from companion.pages import health_page
    with history_db.connection_scope(ctx.state_dir):
        body = health_page.system_html(ctx)
    from companion.pages import components_page
    blocks = body or _block(
        _SYSTEM_HEADING, _item('<p class="text-label">%s</p>' % _t(_SYSTEM_EMPTY)),
        " fleet-block--wide", "system")
    return (
        '<div class="fleet-blocks fleet-blocks--system">%s</div>'
        '<p class="fleet-system-footer"><a class="text-link" href="%s">%s</a></p>'
    ) % (blocks, components_page.COMPONENTS_ROUTE, _t(components_page.LINK_TEXT))


def _unknown_frame_notice(query, found):
    """A docked warning when the address names a frame that does not exist;
    nothing otherwise. The list shows in its place."""
    wanted = wanted_frame(query)
    if not wanted or found:
        return ""
    from companion import ui_components
    return ui_components.anomaly_banner(i18n.t(_UNKNOWN_FRAME), "warn")


def _split(mode, list_html, main_html):
    """The list and the main column side by side (from 960 px; a phone shows
    one of them, by `mode`)."""
    return (
        '<div class="fleet-split" data-fleet-mode="%s"><div class="fleet-split__list">%s'
        '</div><div class="fleet-split__main">%s</div></div>') % (mode, list_html, main_html)


def page_html(h, query, view):
    """The selected view. Sets the request scope to the selected live frame
    (the embedded forms post to its own /devices/<id> routes), or to the
    first one when the list is shown."""
    from companion.pages import fleet_frames_list as frames_list
    root = h.args.state_dir
    principal = h._safe_principal()
    devices = device_scope.load_devices_for(root, principal)
    selected, is_system = selection(query, devices)
    row = frames_list.find_row(view, wanted_frame(query))
    if is_system:
        row = None
    watch = None if (selected or is_system or row) else frames_list.first_to_watch(view)
    scope_device = selected or next(
        (d for d in devices if watch is not None and d.id == watch.frame_id),
        devices[0] if devices else None)
    device_scope.set_request_scope(
        scope_device, devices, getattr(principal, "user_id", None), root)
    notice = _unknown_frame_notice(query, selected or row or is_system)
    if is_system:
        return notice + _split(
            "system", frames_list.list_panel_html(view, is_system=True),
            frames_list.switch_html(view) + frames_list.title_head_html(_t(_SYSTEM_HEADING))
            + system_html(h.page_context(device_scope.live_device(root))))
    if selected is not None:
        live = frames_list.find_row(view, selected.id)
        return notice + _split(
            "frame", frames_list.list_panel_html(view, selected.id),
            frames_list.switch_html(view, selected.id) + frame_html(
                h.page_context(selected), selected, view,
                frames_list.head_html(live, view) if live else frames_list.plain_head_html(selected),
                tab_selection(query)))
    if row is not None:
        return notice + _split(
            "other", frames_list.list_panel_html(view, row.frame_id),
            frames_list.switch_html(view) + frames_list.other_page_html(row, view))
    return notice + _split(
        "list", frames_list.list_panel_html(
            view, landing=True, with_frame=scope_device is not None),
        _auto_frame_html(h, view, watch, scope_device, frames_list))


def _auto_frame_html(h, view, watch, device, frames_list):
    """The first frame of the list, which a wide screen shows beside it when
    no frame is chosen; "" without a live frame. A frame the database does not
    list as a row (the legacy single frame) shows a header of its name only."""
    if device is None:
        return ""
    return frame_html(
        h.page_context(device), device, view,
        frames_list.head_html(watch, view) if watch else frames_list.plain_head_html(device),
        TAB_STATE)


def query_flash_html(h, query):
    """The toast of a `?flash=` result for the selected frame (the settings
    save and update install redirect here with one) or for the System view
    (a resolved airline prefix), or None. The text is resolved with the
    selected frame's own context, the live frame's for the System view."""
    from companion import flash
    devices = device_scope.load_devices_for(h.args.state_dir, h._safe_principal())
    selected, is_system = selection(query, devices)
    if not query.get("flash"):
        return None
    if is_system:
        selected = device_scope.live_device(h.args.state_dir)
    if selected is None:
        return None
    ctx = h.page_context(selected)
    return flash.flash_toast_html(ctx.flash_key, ctx.flash, h.path)
