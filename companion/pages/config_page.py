"""companion/pages/config_page.py — CFG-01 (theme picker), CFG-12 (runway
picker), and CFG-07's "Trigger Poll Now" control (06-CONTEXT.md).

This plan (06-05) ships a contract-complete stub: the Theme and Runway
sections render with 06-UI-SPEC.md's own helper copy in place, but
neither setting is actually saved yet — handle_post() always returns the
save-failure flash key without touching device_config.json. Plan 06-07
replaces this stub with the real theme/runway save path. The "Trigger
Poll Now" button below is real and live now — its POST /poll-now target,
cooldown gate, and in-process server.poll_loop.run_once() call are all
owned and wired by companion/app.py (plan 06-05), not this module.
"""
from companion.layout import escape_html

THEME_HELPER_TEXT = (
    "More themes will be added once Phase 7 validates additional color "
    "options on real hardware.")
RUNWAY_HELPER_TEXT = (
    "Applies on the device's next scheduled poll — not immediately.")

# Returned by handle_post() below — matches companion/app.py's
# FLASH_KEY_SAVE_FAILED string exactly (a plain string contract, not a
# shared import, so this module never has to import companion/app.py).
SAVE_FAILED_FLASH_KEY = "save_failed"


def render(ctx):
    return (
        '<h1 class="text-heading">Config</h1>'
        '<section class="page-section">'
        '<h2 class="text-heading">Theme</h2>'
        '<p class="text-body">Theme picker not yet wired.</p>'
        '<p class="text-label">%s</p>'
        "</section>"
        '<section class="page-section">'
        '<h2 class="text-heading">Runway</h2>'
        '<p class="text-body">Runway picker not yet wired.</p>'
        '<p class="text-label">%s</p>'
        "</section>"
        '<section class="page-section">'
        '<h2 class="text-heading">Poll</h2>'
        '<form method="post" action="/poll-now">'
        '<button type="submit">Trigger Poll Now</button>'
        "</form>"
        "</section>"
    ) % (escape_html(THEME_HELPER_TEXT), escape_html(RUNWAY_HELPER_TEXT))


def handle_post(form, ctx):
    """Not yet wired (plan 06-07 replaces this) — always reports the
    save-failure flash key without validating `form` or writing
    device_config.json. `ctx` is accepted for contract-signature parity
    with every later plan's real implementation but is unused here.
    """
    return SAVE_FAILED_FLASH_KEY
