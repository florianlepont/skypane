"""companion/pages/config_page.py — CFG-01 (theme picker), CFG-12 (runway
picker), and CFG-07's "Trigger Poll Now" control (06-CONTEXT.md).

This plan (06-07) replaces plan 06-05's contract-complete stub. `render()`
is real and live as of this task: the Theme and Runway fieldsets render
from `server.device_config`'s own registries with the current values
pre-selected. `handle_post()` is still a stub here — Task 2 replaces it
with the real server-side-validated save path. The "Trigger Poll Now"
control below is unrelated plumbing owned by companion/app.py (plan
06-05): its POST /poll-now target, cooldown gate, and in-process
server.poll_loop.run_once() call all live there, not here — this module
only renders the button/copy for it.
"""
from companion.layout import escape_html
from server import device_config

THEME_HELPER_TEXT = (
    "More themes will be added once Phase 7 validates additional color "
    "options on real hardware.")
RUNWAY_HELPER_TEXT = (
    "Applies on the device's next scheduled poll — not immediately.")

# Matches 06-UI-SPEC.md's Copywriting Contract "Poll-trigger cooldown"
# row verbatim (D-17); "{n}" is filled in with a server-computed
# remaining-seconds figure, never anything client-supplied. This text is
# intentionally the *button-adjacent* copy shown while the trigger is
# disabled — a separate rendering site from companion/app.py's own
# FLASH_MESSAGES entry for the same event (the post-redirect flash
# banner), not a shared constant, since a page module must never import
# companion/app.py (that would be a cycle: app.py already imports this
# module).
POLL_COOLDOWN_HELPER_TEXT = "Poll triggered recently — try again in {n}s."

# Returned by handle_post() below — matches companion/app.py's
# FLASH_KEY_SAVE_FAILED string exactly (a plain string contract, not a
# shared import, so this module never has to import companion/app.py).
# Task 2 replaces this stub with the real save path and the module's
# full four-constant FLASH_* allowlist.
SAVE_FAILED_FLASH_KEY = "save_failed"


def theme_fieldset(current_theme_id):
    """One radio input per `device_config.THEMES` entry, in registry
    order, with `current_theme_id` marked selected — plus the D-11 helper
    text explaining today's single-option registry.
    """
    options = []
    for theme_id in device_config.THEME_IDS:
        checked = " checked" if theme_id == current_theme_id else ""
        options.append(
            "<label>"
            '<input type="radio" name="theme" value="%s"%s> %s'
            "</label>"
            % (
                escape_html(theme_id), checked,
                escape_html(device_config.theme_label(theme_id)),
            )
        )
    return (
        "<fieldset>"
        "<legend>Theme</legend>"
        "%s"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % ("".join(options), escape_html(THEME_HELPER_TEXT))


def runway_fieldset(current_runway_id):
    """One radio input per `device_config.RUNWAYS` entry (exactly three
    today), in registry order, with `current_runway_id` marked selected —
    plus the CFG-12 helper text stating the change applies on the
    device's next scheduled poll, not immediately (D-28).
    """
    options = []
    for runway_id in device_config.RUNWAY_IDS:
        checked = " checked" if runway_id == current_runway_id else ""
        options.append(
            "<label>"
            '<input type="radio" name="tracked_runway" value="%s"%s> %s'
            "</label>"
            % (
                escape_html(runway_id), checked,
                escape_html(device_config.runway_label(runway_id)),
            )
        )
    return (
        "<fieldset>"
        "<legend>Runway</legend>"
        "%s"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % ("".join(options), escape_html(RUNWAY_HELPER_TEXT))


def poll_trigger_section(cooldown_remaining):
    """The CFG-07 manual-trigger control: an enabled button when
    `cooldown_remaining` is zero, or a native-disabled button plus the
    D-17 remaining-seconds copy otherwise. No client-side JavaScript
    countdown — 06-UI-SPEC.md's Component Patterns table explicitly does
    not require a live timer, and this page ships with no script at all.
    """
    if cooldown_remaining:
        cooldown_text = POLL_COOLDOWN_HELPER_TEXT.format(n=cooldown_remaining)
        return (
            '<form method="post" action="/poll-now">'
            '<button type="submit" disabled>Trigger Poll Now</button>'
            "</form>"
            '<p class="text-body">%s</p>'
        ) % escape_html(cooldown_text)
    return (
        '<form method="post" action="/poll-now">'
        '<button type="submit">Trigger Poll Now</button>'
        "</form>"
    )


def render(ctx):
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)

    return (
        '<h1 class="text-heading">Config</h1>'
        '<form method="post" action="/config">'
        "%s"
        "%s"
        '<button type="submit">Save Settings</button>'
        "</form>"
        '<section class="page-section">'
        '<h2 class="text-heading">Poll</h2>'
        "%s"
        "</section>"
    ) % (
        theme_fieldset(current_theme_id),
        runway_fieldset(current_runway_id),
        poll_trigger_section(cooldown_remaining),
    )


def handle_post(form, ctx):
    """Not yet wired (Task 2 replaces this) — always reports the
    save-failure flash key without validating `form` or writing
    device_config.json. `ctx` is accepted for contract-signature parity
    with Task 2's real implementation but is unused here.
    """
    return SAVE_FAILED_FLASH_KEY
