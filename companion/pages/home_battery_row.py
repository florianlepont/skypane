"""The Battery row of Home's Frame group, shown to every signed-in person.

One quiet row under the screen and quiet-hours switches: the icon tile, the
charge with a level word (never colour alone), a thin level bar and, only
when the observed history supports an honest figure, the estimated
autonomy. With no reading it says so and draws no bar. The figure comes
from `battery.battery_life_estimate()`, never computed here; a charging
frame shows the shared "Probably charging" wording instead of a figure
because a rising voltage says nothing about how long a full charge lasts.
"""

import companion.battery as battery
import companion.i18n as i18n
import companion.layout as layout
import companion.ui_groups as ui_groups
from companion.layout import escape_html
from companion.settings import wake_interval

LABEL = i18n.msg("home.battery_label", "Battery")
NORMAL_TEXT = i18n.msg("home.battery_row_normal", "Normal level")
LOW_TEXT = i18n.msg("home.battery_low", "Low")
CRITICAL_TEXT = i18n.msg("home.battery_critical", "Very low")
PERCENT_TEXT = i18n.msg("home.battery_row_percent", "%d%%")
NONE_TEXT = i18n.msg("home.battery_row_none", "No reading yet")
AUTONOMY_TEMPLATE = i18n.msg(
    "home.battery_row_autonomy", "Estimated battery life: %s")
AUTONOMY_SHORT_TEXT = i18n.msg("home.battery_row_autonomy_short", "less than 2 days")
AUTONOMY_DAYS_TEXT = i18n.msg("home.battery_row_autonomy_days", "about %d days")
AUTONOMY_WEEKS_TEXT = i18n.msg("home.battery_row_autonomy_weeks", "about %d weeks")

# Below this many days the figure is quoted in days, above it in weeks.
_WEEKS_FROM_DAYS = 14
_LEVEL_WORDS = {"ok": NORMAL_TEXT, "low": LOW_TEXT, "critical": CRITICAL_TEXT}


def autonomy_text(state_dir, now, interval_s, curve):
    """The honest autonomy phrase ("about 3 weeks"), or "" when the history
    supports no figure (too little history, a flat or rising series)."""
    rows = wake_interval.wake_battery_rows(state_dir, now)
    estimate = battery.battery_life_estimate(
        rows, interval_s, interval_s, curve=curve)
    days = estimate["days_remaining"]
    if (estimate["trend"] != battery.LIFE_TREND_FALLING
            or isinstance(days, bool) or not isinstance(days, int)):
        return ""
    if days < 2:
        return i18n.t(AUTONOMY_SHORT_TEXT)
    if days < _WEEKS_FROM_DAYS:
        return i18n.t(AUTONOMY_DAYS_TEXT) % days
    return i18n.t(AUTONOMY_WEEKS_TEXT) % round(days / 7.0)


def _bar_html(percent):
    """The level bar as an SVG whose widths are percentage attributes, so no
    inline style is needed."""
    return (
        '<svg class="frame-battery__bar" aria-hidden="true" focusable="false">'
        '<rect class="frame-battery__track" x="0" y="0" width="100%"/>'
        '<rect class="frame-battery__fill" x="0" y="0" width="{}%"/></svg>'
    ).format(max(0, min(100, int(percent))))


def row_html(percent, level, charging, autonomy):
    """The row. `percent` is None without a reading; `level` is "ok", "low"
    or "critical"; `autonomy` is `autonomy_text()`'s phrase or ""."""
    if percent is None:
        detail = '<span class="frame-battery__state">%s</span>' % escape_html(
            i18n.t(NONE_TEXT))
        tone, bar, note = "none", "", ""
    else:
        word = layout.BATTERY_CHARGING_TEXT if charging else _LEVEL_WORDS[level]
        detail = (
            '<span class="frame-battery__state">%s</span>'
            ' \u00b7 <span class="frame-battery__word">%s</span>'
        ) % (escape_html(i18n.t(PERCENT_TEXT) % percent), escape_html(i18n.t(word)))
        tone, bar = level, _bar_html(percent)
        note = (
            '<span class="frame-battery__note">%s</span>' % escape_html(
                i18n.t(AUTONOMY_TEMPLATE) % autonomy)
            if autonomy and not charging else "")
    return ui_groups.row(
        i18n.t(LABEL), icon="icon-battery", label_id="frame-battery-label",
        detail_html=detail + bar + note,
        extra_class="frame-battery frame-battery--%s" % tone)
