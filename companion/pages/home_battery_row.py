"""The battery pill of Home's pills row, shown to every signed-in person.

A quiet static pill: the battery icon, the word and the charge. A low or very
low level adds its word, and a probable charge adds the shared hedged "Probably
charging" pill (never colour alone). With no reading it says so. The pill is a plain element today so it can become a
control later without moving.
"""

import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html

LABEL = i18n.msg("home.battery_label", "Battery")
LOW_TEXT = i18n.msg("home.battery_low", "Low")
CRITICAL_TEXT = i18n.msg("home.battery_critical", "Very low")
PERCENT_TEXT = i18n.msg("home.battery_row_percent", "%d%%")
NONE_TEXT = i18n.msg("home.battery_row_none", "No reading yet")

# The healthy level has no word: the percentage says it.
_LEVEL_WORDS = {"ok": None, "low": LOW_TEXT, "critical": CRITICAL_TEXT}


def pill_html(percent, level, charging):
    """The pill. `percent` is None without a reading; `level` is "ok", "low"
    or "critical"; `charging` marks a probable charge."""
    if percent is None:
        text, tone = "%s · %s" % (i18n.t(LABEL), i18n.t(NONE_TEXT)), "none"
    else:
        word = None if charging else _LEVEL_WORDS[level]
        text = "%s %s" % (i18n.t(LABEL), i18n.t(PERCENT_TEXT) % percent)
        if word is not None:
            text += " · %s" % i18n.t(word)
        tone = level
    return (
        '<span class="home-pill home-pill--static home-battery-pill '
        'home-battery-pill--%s">%s<span class="home-pill__text">%s</span>%s</span>'
    ) % (tone, layout.icon_html("icon-battery", 20), escape_html(text),
         layout.battery_charging_pill_html("home-battery-pill__charging")
         if charging and percent is not None else "")
