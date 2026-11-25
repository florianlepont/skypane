"""The Console Fleet page: the list of frames and the views it opens.

`/fleet` shows the list of frames (live, pending and retired, each a link to
`/fleet?frame=<id>`). A live frame opens one column of sections: State (four
equal tiles), Settings and Access (owner, co-managers, reassign, retire).
Each section reuses the content of the page that used to hold it (Device,
Manage access) with the same forms and POST routes. The connection tile states
the last and the next connection itself; the battery and firmware tiles lead to
two detail pages of the frame, `view=battery` (the level, the trend and the
readings) and `view=versions` (the installed version, the update and every
earlier version). A pending or retired frame opens its own page with only its
useful action and appears nowhere else. The System view holds the platform-wide
information.

On a phone the list and a frame page are separate screens joined by the frame
switch (a chip row); from 1200 px the list is a full-height column beside the
console sidebar and the frame fills the rest. The System view is reached from the
console navigation, not from the list. With no
frame chosen the list shows, and a wide screen shows a neutral "Select a
frame" pane beside it, never a frame's data.

Selection is read from the query only to pick one of the rows the request
scope already lists; a value matching none shows the list, so no request text
reaches a path, a query or a filesystem call.
"""
from companion import device_scope, i18n
from companion.pages import co_managers_card, fleet_tiles
from companion.ui_base import escape_html, icon_html
from server import history_db

FRAME_QUERY = "frame"
VIEW_QUERY = "view"
VIEW_SYSTEM = "system"
FOCUS_QUERY = "tab"
SECTION_STATE = "state"
SECTION_SETTINGS = "settings"
SECTION_ACCESS = "access"
VIEW_BATTERY = fleet_tiles.VIEW_BATTERY
VIEW_VERSIONS = fleet_tiles.VIEW_VERSIONS
DETAIL_VIEWS = (VIEW_BATTERY, VIEW_VERSIONS)
SYSTEM_HREF = "/fleet?%s=%s" % (VIEW_QUERY, VIEW_SYSTEM)
FRAME_HREF_PREFIX = "/fleet?%s=" % FRAME_QUERY



def page_scripts(system=False):
    """The scripts the embedded blocks need: the settings form's dirty bar, value
    controls and the Diagnostic LED quick switch, plus the Install and Revert
    question dialog on a frame's page, or the System view's registry table copy, filter and
    lookup helpers on the System view."""
    from companion import ui_base
    base = (
        ui_base.DIRTY_STATE_SCRIPT_SRC, ui_base.FRESHNESS_SCRIPT_SRC,
        ui_base.QUICK_SWITCH_SCRIPT_SRC, ui_base.VALUE_CONTROLS_SCRIPT_SRC)
    if not system:
        return (
            ui_base.UPDATE_QUESTION_SCRIPT_SRC, ui_base.LIST_FILTER_SCRIPT_SRC,
            ui_base.FLEET_ANCHORS_SCRIPT_SRC) + base
    return (
        ui_base.COPY_BUTTON_SCRIPT_SRC, ui_base.LIST_FILTER_SCRIPT_SRC,
        ui_base.PANEL_LOOKUP_SCRIPT_SRC) + base


_SYSTEM_HEADING = i18n.msg("admin_fleet.system_heading", "System")
_STATE_HEADING = i18n.msg("admin_fleet.block_state", "State")
_SETTINGS_HEADING = i18n.msg("admin_fleet.block_settings", "Settings")
_ACCESS_HEADING = i18n.msg("admin_fleet.block_access", "Access")
_SECTIONS_LABEL = i18n.msg("admin_fleet.tabs_label", "Frame sections")
_BACK_TO_FRAME = i18n.msg("admin_fleet.back_to_frame", "Back to %s")
_BATTERY_HEADING = i18n.msg("health.row_battery", "Battery")
_VERSIONS_HEADING = i18n.msg("update.version_history", "Versions")
SYSTEM_HEADING = _SYSTEM_HEADING
SYSTEM_SUB = i18n.msg(
    "admin_fleet.system_sub",
    "The server behind every frame. Visible to administrators.")
_SYSTEM_EMPTY = i18n.msg(
    "admin_fleet.system_unavailable",
    "No system information is available yet.")
_UNKNOWN_FRAME = i18n.msg("admin_fleet.unknown_frame", "That frame was not found.")
_EMPTY_TITLE = i18n.msg("admin_fleet.select_frame", "Select a frame")
_EMPTY_HINT = i18n.msg(
    "admin_fleet.select_frame_hint",
    "Choose a frame in the list to see its status and settings.")

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


def detail_view(query):
    """The detail page a query names for a chosen frame (`view=battery` or
    `view=versions`), or ""."""
    wanted = (query.get(VIEW_QUERY) or [""])[0]
    return wanted if wanted in DETAIL_VIEWS else ""


def section_focus(query):
    """The section a phone brings into view on load: only the exact
    `tab=settings` or `tab=access` (an old `access=` link too); "" otherwise."""
    wanted = (query.get(FOCUS_QUERY) or [""])[0]
    if wanted in (SECTION_SETTINGS, SECTION_ACCESS):
        return wanted
    return SECTION_ACCESS if query.get("access") else ""


def anchors_html():
    """The State / Settings / Access anchors (a phone only, by the stylesheet):
    in-page links to the three sections, the first marked current; a script
    marks the section in view as the page scrolls."""
    labels = (
        (SECTION_STATE, _STATE_HEADING), (SECTION_SETTINGS, _SETTINGS_HEADING),
        (SECTION_ACCESS, _ACCESS_HEADING))
    links = "".join(
        '<a class="fleet-anchor" href="#%s%s"%s>%s</a>' % (
            fleet_tiles.SECTION_ID_PREFIX, key,
            ' aria-current="true"' if key == SECTION_STATE else "", _t(label))
        for key, label in labels)
    return '<nav class="fleet-anchors" aria-label="%s" data-fleet-anchors>%s</nav>' % (
        _t(_SECTIONS_LABEL), links)


def _block(heading_msg, items_html, extra_class="", slug="", heading=""):
    """One block of the selected frame as a grouped list: the section label
    above one glass group. `items_html` is a run of `<li>` items (value rows
    and flush or padded content items)."""
    if not items_html:
        return ""
    from companion import ui_groups
    return ui_groups.group(
        items_html, label=heading or i18n.t(heading_msg), label_id="fleet-block-" + slug,
        extra_class="fleet-block" + extra_class,
        attrs='id="%s%s"' % (fleet_tiles.SECTION_ID_PREFIX, slug)).replace(
            '<ul class="group">', '<ul class="group fleet-group">', 1)


def _cards_block(heading, items_html, extra_class, slug):
    """One labelled block whose items are separate glass cards, one per item,
    stacked under the single label (the Health page: a card per topic)."""
    if not items_html:
        return ""
    from companion import ui_groups
    cards = "".join(
        '<ul class="group fleet-group">%s</ul>' % item for item in items_html)
    return '<section class="group-block fleet-block%s" id="%s%s" aria-labelledby="%s">%s%s</section>' % (
        extra_class, fleet_tiles.SECTION_ID_PREFIX, slug, "fleet-block-" + slug,
        ui_groups.section_label(heading, "fleet-block-" + slug),
        '<div class="fleet-cards">%s</div>' % cards)


def _tiles_block(heading_msg, content_html, extra_class, slug):
    """One labelled block whose content is its own run of tiles (the Settings
    form), with no glass group around it."""
    from companion import ui_groups
    return '<section class="group-block fleet-block%s" id="%s%s" aria-labelledby="%s">%s%s</section>' % (
        extra_class, fleet_tiles.SECTION_ID_PREFIX, slug, "fleet-block-" + slug,
        ui_groups.section_label(i18n.t(heading_msg), "fleet-block-" + slug), content_html)


def _item(content_html, flush=False):
    """Free content (forms, the battery row, version cards) as one item of a
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
        add_as_dialog=True, compact=True)
    dismiss = "%s%s&%s=%s" % (FRAME_HREF_PREFIX, device.id, FOCUS_QUERY, SECTION_ACCESS)
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


def frame_html(ctx, device, view, header_html="", focus=""):
    """The selected frame's header and sections. `ctx` is the page context
    built for `device`, whose state directory the History reads must be scoped
    to; `view` is the page's `FleetView`. `focus` names the section a phone
    brings into view (Settings or Access), "" for the top."""
    from companion.pages import config_page, health_page, update_page
    with history_db.connection_scope(device.state_dir):
        tiles = health_page.frame_tiles(ctx)
        firmware = update_page.firmware_summary(ctx, device.hardware_type)
        settings_html = config_page.render(
            ctx, scope=config_page.SCOPE_DEVICE, embedded=True)
        blocks = (
            fleet_tiles.tiles_section_html(device.id, tiles, firmware)
            + _tiles_block(
                _SETTINGS_HEADING, settings_html, " fleet-block--settings", "settings")
            + _access_block(device, view.access, view))
    return (
        '<div class="fleet-frame">' + header_html + anchors_html()
        + '<div class="fleet-blocks"%s>%s</div></div>' % (
            ' data-fleet-focus="%s"' % focus if focus else "", blocks)
        + config_page.docked_dirty_bar_html())


def detail_head_html(device, name):
    """The head of a detail page: the link back to the frame's page and the
    page's one `<h1>`."""
    from companion import ui_base
    return (
        '<a class="fleet-back" href="%s%s">%s<span>%s</span></a>' % (
            FRAME_HREF_PREFIX, _esc(device.id), ui_base.icon_html("icon-chevron-left", 20),
            _esc(i18n.t(_BACK_TO_FRAME) % name)))


def battery_html(ctx, device):
    """The Battery page of a frame: its level, the trend chart and the readings
    in one card whose header names it (the empty state when the frame never
    checked in). The page's `<h1>` already names it, so no section label
    repeats the word above the card."""
    from companion import health_rows
    from companion.pages import health_page
    with history_db.connection_scope(device.state_dir):
        parts = health_page.battery_view(ctx)
    if parts.empty_html:
        blocks = _block(
            _BATTERY_HEADING, _item(parts.empty_html, True), "", "battery")
    else:
        card = _item(health_rows.card_html(parts.row_html), True)
        blocks = (
            '<section class="group-block fleet-block" id="%sbattery" aria-label="%s">'
            '<div class="fleet-cards"><ul class="group fleet-group">%s</ul></div></section>' % (
                fleet_tiles.SECTION_ID_PREFIX, _t(_BATTERY_HEADING), card))
    return '<div class="fleet-blocks fleet-blocks--detail">%s</div>' % blocks


def versions_html(ctx, device):
    """The Versions page of a frame: the installed version and whether an
    update is available (with its install action), then every release with its
    Install or Revert action."""
    from companion.pages import update_page
    with history_db.connection_scope(device.state_dir):
        device_html, releases_html, _summary = update_page.render_parts(
            ctx, device.hardware_type)
    return '<div class="fleet-versions">%s%s</div>' % (device_html, releases_html)


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
    """The list and the main column side by side (from 1200 px; a phone shows
    one of them, by `mode`)."""
    return (
        '<div class="fleet-split" data-fleet-mode="%s"><div class="fleet-split__list">%s'
        '</div><div class="fleet-split__main">%s</div></div>') % (mode, list_html, main_html)


def page_html(h, query, view):
    """The selected view. Sets the request scope to the selected live frame
    (the embedded forms post to its own /devices/<id> routes), or to the
    first one when the list is shown (the page navigation needs a scope; no
    frame data is rendered then)."""
    from companion.pages import fleet_frames_list as frames_list
    root = h.args.state_dir
    principal = h._safe_principal()
    devices = device_scope.load_devices_for(root, principal)
    selected, is_system = selection(query, devices)
    row = frames_list.find_row(view, wanted_frame(query))
    if is_system:
        row = None
    scope_device = selected or (devices[0] if devices else None)
    device_scope.set_request_scope(
        scope_device, devices, getattr(principal, "user_id", None), root)
    notice = _unknown_frame_notice(query, selected or row)
    if is_system:
        return system_html(h.page_context(device_scope.live_device(root)))
    if selected is not None:
        live = frames_list.find_row(view, selected.id)
        detail = detail_view(query)
        if detail:
            return notice + _split(
                "detail", "", _detail_html(h, selected, live, detail, frames_list))
        return notice + _split(
            "frame", frames_list.list_panel_html(view, selected.id),
            frames_list.switch_html(view, selected.id) + frame_html(
                h.page_context(selected), selected, view,
                frames_list.head_html(live, view) if live else frames_list.plain_head_html(selected),
                section_focus(query)))
    if row is not None:
        return notice + _split(
            "other", frames_list.list_panel_html(view, row.frame_id),
            frames_list.switch_html(view) + frames_list.other_page_html(row, view))
    return notice + _split(
        "list", frames_list.list_panel_html(view, landing=True),
        empty_detail_html())


def _detail_html(h, device, row, detail, frames_list):
    """The Battery or Versions page of a frame: the way back to the frame, the
    page's `<h1>` and its content. The list column is not part of it."""
    from companion.pages import fleet_page
    name = fleet_page.display_name(row) if row else device.name
    ctx = h.page_context(device)
    if detail == VIEW_BATTERY:
        title, body = _t(_BATTERY_HEADING), battery_html(ctx, device)
    else:
        title, body = _t(_VERSIONS_HEADING), versions_html(ctx, device)
    return detail_head_html(device, name) + frames_list.title_head_html(title) + body


def empty_detail_html():
    """The neutral pane a wide screen shows beside the list while no frame is
    chosen: an icon, a short heading and one muted line, no frame data. A phone
    hides it (the list mode shows the list only). The list's title is the page's
    `<h1>`, so this heading is an `<h2>`."""
    return (
        '<div class="fleet-empty"><div class="empty-state__halo fleet-empty__halo">%s</div>'
        '<h2 class="fleet-empty__title">%s</h2><p class="fleet-empty__hint">%s</p></div>') % (
            icon_html("icon-device", 28), _t(_EMPTY_TITLE), _t(_EMPTY_HINT))


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
