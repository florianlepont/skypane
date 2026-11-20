"""The State section of a frame's page: four equal tiles (connection, battery,
flight data, firmware), each a link with a Details mark to the page that holds
the whole story (Health, or Versions for the firmware).

Pure markup built from `health_page.FrameTiles` and `update_page.FirmwareSummary`.
Every dynamic part is escaped; the sparkline carries numbers only.
"""
from companion import i18n
from companion.ui_base import escape_html, icon_html

VIEW_HEALTH = "health"
VIEW_VERSIONS = "versions"

SECTION_ID_PREFIX = "fleet-section-"
_SPARK_WIDTH = 300
_SPARK_HEIGHT = 44
_SPARK_PAD = 4

_STATE_HEADING = i18n.msg("admin_fleet.block_state", "State")
_DETAILS = i18n.msg("admin_fleet.tile_details", "Details")
_FIRMWARE = i18n.msg("admin_fleet.tile_firmware", "Firmware")
_NO_CHECK_IN = i18n.msg("health.row_no_check_in", "No check-in yet")
_LABEL_CONNECTION = i18n.msg("admin_fleet.tile_connection", "Connection")
_LABEL_BATTERY = i18n.msg("health.row_battery", "Battery")
_LABEL_FLIGHT = i18n.msg("health.row_flight_data", "Flight data")

_TONE_STATES = {"ok": "ok", "warn": "warn", "error": "error"}


def view_href(frame_id, view):
    """The address of one of a frame's detail pages, ready for an attribute."""
    return "/fleet?frame=%s&amp;view=%s" % (escape_html(frame_id), view)


def _spark_html(percents):
    """The battery's recent course as a line from the oldest value to the
    newest; "" below two values."""
    if len(percents) < 2:
        return ""
    step = _SPARK_WIDTH / (len(percents) - 1)
    span = _SPARK_HEIGHT - 2 * _SPARK_PAD
    points = " ".join(
        "%.1f,%.1f" % (i * step, _SPARK_HEIGHT - _SPARK_PAD - min(100, max(0, p)) / 100 * span)
        for i, p in enumerate(percents))
    return (
        '<svg class="fleet-tile__spark" viewBox="0 0 %d %d" preserveAspectRatio="none" '
        'aria-hidden="true" focusable="false"><polyline points="%s"></polyline></svg>'
        % (_SPARK_WIDTH, _SPARK_HEIGHT, points))


def _tile(href, state, icon_id, label, value_html, meta_html, extra_html="", marked=False):
    from companion import health_rows
    state = health_rows.resolved_state(state)
    return (
        '<li><a class="fleet-tile" data-state="%s" href="%s">'
        '<span class="fleet-tile__head"><span class="fleet-tile__icon">%s%s'
        '<span class="visually-hidden">%s</span></span>'
        '<span class="fleet-tile__label">%s</span></span>'
        '<span class="fleet-tile__value">%s</span>'
        '<span class="fleet-tile__meta">%s</span>%s'
        '<span class="fleet-tile__more">%s%s</span></a></li>' % (
            state, href, icon_html(icon_id, 20),
            health_rows.state_mark_html(state) if marked else "",
            escape_html(i18n.t(health_rows.STATE_WORDS[state])), escape_html(label),
            value_html, meta_html, extra_html,
            escape_html(i18n.t(_DETAILS)), icon_html("icon-chevron-right", 16)))


def tiles_section_html(frame_id, tiles, firmware):
    """The State section: the label and the four tiles. `tiles` is a
    `health_page.FrameTiles` or None for a frame that never checked in;
    `firmware` a `update_page.FirmwareSummary`."""
    from companion import health_rows, ui_groups
    health = view_href(frame_id, VIEW_HEALTH)
    versions = view_href(frame_id, VIEW_VERSIONS)
    if tiles is None:
        none = i18n.t(_NO_CHECK_IN)
        cells = (
            _tile(health, "off", "icon-info", i18n.t(_LABEL_CONNECTION), escape_html(none), ""),
            _tile(health, "off", "icon-battery", i18n.t(_LABEL_BATTERY), "", ""),
            _tile(health, "off", "icon-plane", i18n.t(_LABEL_FLIGHT), "", ""))
    else:
        conn, batt, flight = tiles.connection, tiles.battery, tiles.flight
        cells = (
            _tile(health, conn.state, health_rows.STATE_ICON_IDS[
                health_rows.resolved_state(conn.state)], i18n.t(_LABEL_CONNECTION),
                escape_html(conn.verdict), conn.age_html),
            _tile(health, batt.state, "icon-battery", i18n.t(_LABEL_BATTERY),
                  escape_html(batt.value or batt.verdict),
                  escape_html(batt.verdict if batt.value else ""),
                  _spark_html(tiles.battery_curve)),
            _tile(health, flight.state, "icon-plane", i18n.t(_LABEL_FLIGHT),
                  escape_html(flight.verdict), flight.age_html))
    headline = escape_html(i18n.t(firmware.headline))
    version = '<span class="mono">%s</span>' % escape_html(firmware.version)
    firmware_cell = _tile(
        versions, _TONE_STATES.get(firmware.tone, "off"), "icon-nav-update",
        i18n.t(_FIRMWARE), version if firmware.version else headline,
        headline if firmware.version else "")
    return (
        '<section class="group-block fleet-block" id="%sstate" '
        'aria-labelledby="fleet-block-state">%s<ul class="fleet-tiles">%s</ul></section>' % (
            SECTION_ID_PREFIX,
            ui_groups.section_label(i18n.t(_STATE_HEADING), "fleet-block-state"),
            "".join(cells) + firmware_cell))


SYSTEM_BLOCK_ID_PREFIX = "system-topic-"


def system_tiles_html(tiles):
    """The System page's tiles: one equal tile per topic (a
    `health_page.SystemTile`), each a link that jumps to its block on the same
    page. The state is spelled out (a visually hidden word and the headline),
    never colour alone."""
    cells = "".join(
        _tile("#" + SYSTEM_BLOCK_ID_PREFIX + tile.key, tile.state, tile.icon, tile.label,
              escape_html(tile.value), tile.meta_html, marked=True)
        for tile in tiles)
    return '<ul class="fleet-tiles fleet-tiles--system">%s</ul>' % cells
