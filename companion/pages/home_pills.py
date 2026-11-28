# SPDX-License-Identifier: AGPL-3.0-only
"""The row of pills under Home's flight card: the Screen switch, the Quiet
hours opener, the place link and the battery pill.

Every pill is a 44px glass capsule with an icon on its left. The Screen pill
holds the shared native-POST `role="switch"` form (it works with scripts
blocked and the whole capsule is the touch target); the Quiet hours pill opens
the dialog and the place pill goes to the Location page.
"""
import companion.detection_summary as detection_summary
import companion.i18n as i18n
import companion.layout as layout
import companion.ui_modal as ui_modal
from companion.layout import escape_html
from companion.settings import quiet_hours

QUICK_DISPLAY_ACTION = "/quick/display"
DETECTION_PATH = "/detection"
QUIET_OFF_TEXT = i18n.msg("home.pill_quiet_off", "Quiet hours · Off")
EDIT_QUIET_HOURS_LABEL = i18n.msg("home.edit_quiet_hours", "Edit quiet hours (%s)")
SECTION_LABEL = i18n.msg("home.switches", "Frame controls")
DEFAULT_QUIET_START = "23:00"
DEFAULT_QUIET_END = "07:00"


def _pill(icon_id, text_html, trailing_html=""):
    return '%s<span class="home-pill__text">%s</span>%s' % (
        layout.icon_html(icon_id, 20), text_html, trailing_html)


def screen_pill_html(is_on):
    """The Screen switch pill: its icon, its name and the shared switch."""
    label_id, state_id = "home-switch-screen-label", "home-switch-screen-state"
    state = layout.quick_switch_state_html(
        state_id, i18n.t(layout.QUICK_ACTION_ON_TEXT), i18n.t(layout.QUICK_ACTION_OFF_TEXT),
        is_on, extra_class="visually-hidden")
    return (
        '<div class="home-pill home-pill--switch home-switch--%s" %s data-quick-refresh>%s%s%s%s</div>'
    ) % (
        "on" if is_on else "off", layout.QUICK_SWITCH_REGION_ATTR,
        layout.icon_html("icon-nav-display", 20),
        '<span class="home-pill__text" id="%s">%s</span>' % (
            label_id, escape_html(i18n.t(layout.QUICK_ACTION_SCREEN_LABEL))),
        state,
        layout.quick_switch_html(QUICK_DISPLAY_ACTION, layout.HOME_ROUTE, is_on, label_id, state_id))


def quiet_window_text(cfg):
    """The configured window as "23:30 – 06:00"."""
    return "%s – %s" % (
        cfg.get("quiet_hours_start") or DEFAULT_QUIET_START,
        cfg.get("quiet_hours_end") or DEFAULT_QUIET_END)


def quiet_pill_html(cfg):
    """The Quiet hours pill: a link that opens the dialog, showing the window
    (behind the moon) while the schedule is on and "Quiet hours · Off"
    otherwise. Its accessible name always says "Quiet hours"."""
    window = quiet_window_text(cfg)
    on = cfg.get("quiet_hours_enabled") is True
    text = window if on else i18n.t(QUIET_OFF_TEXT)
    return ui_modal.trigger_html(
        quiet_hours.QUIET_DIALOG_ID,
        _pill("icon-moon", escape_html(text),
              layout.icon_html("icon-chevron-right", 16, "home-pill__chevron")),
        extra_class="home-pill home-pill--link home-pill--quiet",
        aria_label=i18n.t(EDIT_QUIET_HOURS_LABEL) % (window if on else i18n.t(QUIET_OFF_TEXT)))


def place_pill_html(cfg, place, href):
    """The place pill: a link to the Location page naming what the frame follows."""
    icon_id, text = detection_summary.home_place_text(cfg, place)
    return '<a class="home-pill home-pill--link home-pill--place" href="%s">%s</a>' % (
        escape_html(href),
        _pill(icon_id, escape_html(text),
              layout.icon_html("icon-chevron-right", 16, "home-pill__chevron")))


def pills_html(cfg, place, place_href, battery_html):
    """The pills section; `battery_html` is the battery pill or "" for a frame
    that never checked in."""
    return (
        '<section class="home-pills reveal" aria-labelledby="home-frame-controls">'
        '<h2 class="visually-hidden" id="home-frame-controls">%s</h2>'
        '<div class="home-pills__row">%s%s%s%s</div></section>'
    ) % (
        escape_html(i18n.t(SECTION_LABEL)),
        screen_pill_html(cfg.get("display_enabled") is not False),
        quiet_pill_html(cfg), place_pill_html(cfg, place, place_href), battery_html)
