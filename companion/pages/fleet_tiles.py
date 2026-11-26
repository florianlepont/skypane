"""The State section of a frame's page: three tiles (connection, battery,
firmware). The connection tile states the last and the next connection
itself; the other two are links with a Details mark to the page that holds
the whole story (Battery, or Versions for the firmware).

Pure markup built from `health_page.FrameTiles` and `update_page.FirmwareSummary`.
Every dynamic part is escaped; the sparkline carries numbers only.
"""
import html
import re

from companion import i18n
from companion.ui_base import escape_html, icon_html

VIEW_BATTERY = "battery"
VIEW_VERSIONS = "versions"

SECTION_ID_PREFIX = "fleet-section-"
_SPARK_WIDTH = 300
_SPARK_HEIGHT = 44
_SPARK_PAD = 4

_STATE_HEADING = i18n.msg("admin_fleet.block_state", "State")
_DETAILS = i18n.msg("admin_fleet.tile_details", "Details")
_FIRMWARE = i18n.msg("admin_fleet.tile_firmware", "Software")
_NO_CHECK_IN = i18n.msg("health.row_no_check_in", "No check-in yet")
_LABEL_CONNECTION = i18n.msg("admin_fleet.tile_connection", "Last contact")
_LABEL_BATTERY = i18n.msg("health.row_battery", "Battery")

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


def _tile(href, state, icon_id, label, value_html, meta_html, extra_html="", compact=False,
          wide=False):
    """One tile: a link with a Details mark when `href` is given, else a plain
    block (the connection tile, which holds its whole story). A `compact` tile
    carries the mark as a chevron at the end of its label row and gives its
    muted line a plain-text `title`. A `wide` tile spans the grid and sets its
    text and its Details mark side by side once it is wide enough."""
    from companion import health_rows
    state = health_rows.resolved_state(state)
    details = escape_html(i18n.t(_DETAILS))
    more = chevron = title = ""
    if href and compact:
        chevron = (
            '<span class="fleet-tile__chevron">%s<span class="visually-hidden">%s</span></span>'
            % (icon_html("icon-chevron-right", 16), details))
        text = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", meta_html)).split())
        title = ' title="%s"' % escape_html(text) if text else ""
    elif href:
        more = '<span class="fleet-tile__more">%s%s</span>' % (
            details, icon_html("icon-chevron-right", 16))
    tile_class = "fleet-tile fleet-tile--wide" if wide else "fleet-tile"
    opening = (
        '<a class="%s" data-state="%s" href="%s">' % (tile_class, state, href) if href
        else '<div class="%s" data-state="%s">' % (tile_class, state))
    if wide:
        return (
            '<li class="fleet-tiles__span">%s<span class="fleet-tile__text">'
            '<span class="fleet-tile__head"><span class="fleet-tile__icon">%s'
            '<span class="visually-hidden">%s</span></span>'
            '<span class="fleet-tile__label">%s</span></span>'
            '<span class="fleet-tile__body"><span class="fleet-tile__value">%s</span>'
            '<span class="fleet-tile__meta">%s</span></span></span>%s%s</li>' % (
                opening, icon_html(icon_id, 20),
                escape_html(i18n.t(health_rows.STATE_WORDS[state])), escape_html(label),
                value_html, meta_html, more, "</a>" if href else "</div>"))
    return (
        '<li>%s'
        '<span class="fleet-tile__head"><span class="fleet-tile__icon">%s'
        '<span class="visually-hidden">%s</span></span>'
        '<span class="fleet-tile__label">%s</span>%s</span>'
        '<span class="fleet-tile__value">%s</span>'
        '<span class="fleet-tile__meta"%s>%s</span>%s%s%s</li>' % (
            opening, icon_html(icon_id, 20),
            escape_html(i18n.t(health_rows.STATE_WORDS[state])), escape_html(label),
            chevron, value_html, title, meta_html, extra_html, more,
            "</a>" if href else "</div>"))


def tiles_section_html(frame_id, tiles, firmware):
    """The State section: the label and the three tiles. `tiles` is a
    `health_page.FrameTiles` or None for a frame that never checked in;
    `firmware` a `update_page.FirmwareSummary`."""
    from companion import health_rows, ui_groups
    battery = view_href(frame_id, VIEW_BATTERY)
    versions = view_href(frame_id, VIEW_VERSIONS)
    if tiles is None:
        none = i18n.t(_NO_CHECK_IN)
        cells = (
            _tile(None, "off", "icon-info", i18n.t(_LABEL_CONNECTION), escape_html(none), ""),
            _tile(battery, "off", "icon-battery", i18n.t(_LABEL_BATTERY), "", ""))
    else:
        conn, batt = tiles.connection, tiles.battery
        cells = (
            _tile(None, conn.state, health_rows.STATE_ICON_IDS[
                health_rows.resolved_state(conn.state)], i18n.t(_LABEL_CONNECTION),
                escape_html(conn.verdict), conn.age_html),
            _tile(battery, batt.state, "icon-battery", i18n.t(_LABEL_BATTERY),
                  escape_html(batt.value or batt.verdict),
                  escape_html(batt.verdict if batt.value else ""),
                  _spark_html(tiles.battery_curve)))
    headline = escape_html(i18n.t(firmware.headline))
    version = '<span class="mono">%s</span>' % escape_html(firmware.version)
    firmware_cell = _tile(
        versions, _TONE_STATES.get(firmware.tone, "off"), "icon-nav-update",
        i18n.t(_FIRMWARE), version if firmware.version else headline,
        headline if firmware.version else "", wide=True)
    return (
        '<section class="group-block fleet-block" id="%sstate" '
        'aria-labelledby="fleet-block-state">%s<ul class="fleet-tiles fleet-tiles--rows">%s</ul></section>' % (
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
              escape_html(tile.value), tile.meta_html, compact=True)
        for tile in tiles)
    return '<ul class="fleet-tiles fleet-tiles--system">%s</ul>' % cells
