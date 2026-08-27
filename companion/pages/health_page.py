"""companion/pages/health_page.py — CFG-03 (health status + trend) and
CFG-05's landing context (the on-device fault icon's redirect target),
06-CONTEXT.md.

This plan (06-05) ships a contract-complete stub: all four Health
subsections render with 06-UI-SPEC.md's "health data unavailable" copy,
since no server.history_db query runs yet. Plan 06-08 replaces this with
the real device check-in / ADS-B pipeline / battery trend / corroboration
reads and D-14's anomaly banner.
"""
from companion.layout import escape_html

HEALTH_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")

_SECTIONS = (
    "Device check-in",
    "ADS-B pipeline",
    "Battery trend",
    "Corroboration",
)


def render(ctx):
    sections = "".join(
        (
            '<section class="page-section">'
            '<h2 class="text-heading">%s</h2>'
            '<p class="text-body">%s</p>'
            "</section>"
        )
        % (escape_html(name), escape_html(HEALTH_UNAVAILABLE_TEXT))
        for name in _SECTIONS
    )
    return '<h1 class="text-heading">Health</h1>' + sections
