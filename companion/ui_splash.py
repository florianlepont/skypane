"""The opening splash's server-rendered overlay.

The "Cadre" splash: a blank frame outline draws itself, the e-paper refresh
runs inside it (one inversion, colour sweeps, a scan line that reveals the
logo), the preload progress thickens the outline, and the page opens from the
frame's rectangle. The markup is part of every authenticated document but
stays `display: none` until `splash-boot.js` puts `splash-on` on `<html>`;
without scripts it is never shown. All dynamic values are driven by
`splash.js` through attributes and the Web Animations API, so no inline style
is needed. Only the two spoken words are translated here; the percentage is
drawn, not announced, and the script makes the label a live status only
while the splash runs.
"""

import companion.i18n as i18n
from companion.ui_base import escape_html, icon_html

SPLASH_LOADING_TEXT = i18n.msg("common.splash_loading", "Loading…")
SPLASH_READY_TEXT = i18n.msg("common.splash_ready", "Ready")

# The outline's corner radius in CSS pixels: the panel's 18px plus the 9px
# the outline sits outside it.
OUTLINE_RADIUS = 27
LOGO_CLASS = "splash__logo"
BAND_COUNT = 4


def splash_html():
    """The hidden overlay: the frame (panel with ink layer, four colour
    bands, the ghosted logo, the sharp logo and the scan line; the outline
    with its track and its progress bar) and the caption. `data-splash-ready`
    carries the translated word the script writes when the preload ends."""
    bands = "".join(
        '<i class="splash__band splash__band--%d"></i>' % number
        for number in range(1, BAND_COUNT + 1))
    outline = (
        '<svg class="splash__outline" aria-hidden="true" focusable="false">'
        '<rect class="splash__track" x="0" y="0" width="100%%" height="100%%" '
        'rx="%(r)d" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/>'
        '<rect class="splash__bar" x="0" y="0" width="100%%" height="100%%" '
        'rx="%(r)d" pathLength="100" stroke-dasharray="100 100" stroke-dashoffset="100"/></svg>') % {"r": OUTLINE_RADIUS}
    return (
        '<div class="splash" data-splash data-splash-ready="%s">'
        '<div class="splash__frame"><div class="splash__panel">'
        '<span class="splash__ink"></span>%s%s%s<span class="splash__scan"></span>'
        "</div>%s</div>"
        '<p class="splash__caption"><span class="splash__label">%s</span> '
        '<span class="splash__percent" aria-hidden="true"></span></p>'
        "</div>"
    ) % (
        escape_html(i18n.t(SPLASH_READY_TEXT)), bands,
        icon_html("icon-logo", 30, LOGO_CLASS + " " + LOGO_CLASS + "--ghost"),
        icon_html("icon-logo", 30, LOGO_CLASS + " " + LOGO_CLASS + "--sharp"),
        outline, escape_html(i18n.t(SPLASH_LOADING_TEXT)))
