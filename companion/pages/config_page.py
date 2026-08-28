"""companion/pages/config_page.py — CFG-01 (theme picker), CFG-12 (runway
picker), and CFG-07's "Trigger Poll Now" control (06-CONTEXT.md).

Both `render()` and `handle_post()` are real and live as of this plan
(06-07): the Theme and Runway fieldsets render from `server.device_config`'s
own registries with the current values pre-selected, and a POST validates
both fields against those same registries — server-side — before ever
calling `device_config.save_device_config()`. The "Trigger Poll Now"
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

# The four flash keys this module's handle_post() can return, defined
# here — the single source of truth companion/app.py's own flash-key
# constants and FLASH_MESSAGES dict reference, per this plan's Task 2
# ("the key strings exist in exactly one place"). Values match
# companion/app.py's pre-existing FLASH_KEY_* string literals exactly, so
# a redirect's ?flash= query parameter round-trips through
# app.py's FLASH_MESSAGES lookup unchanged.
FLASH_SAVED = "saved"
FLASH_SAVE_FAILED = "save_failed"
FLASH_POLL_TRIGGERED = "poll_triggered"
FLASH_POLL_COOLDOWN = "poll_cooldown"
# Distinct from FLASH_SAVE_FAILED (2026-08-28 fix): a run_once() exception
# inside POST /poll-now used to redirect with FLASH_SAVE_FAILED, showing
# "Couldn't save settings" for a failure that has nothing to do with
# saving settings — confusing and actively misleading about what broke.
FLASH_POLL_FAILED = "poll_failed"


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
    """Validate the submitted theme/runway against `device_config`'s own
    registries — server-side, before either value is used anywhere — and
    persist a valid pair.

    Deliberately does NOT call either of `device_config`'s two read-path
    normalising helpers (the ones an unrecognised on-disk value silently
    degrades through to the default): those implement the *read* path's
    forgiving behaviour, whereas a *write* of an unrecognised value is a
    real client error that must be reported back to the user, not
    silently coerced — the asymmetry is deliberate (06-CONTEXT.md
    D-06/D-07, 06-RESEARCH.md's V5 threat control). Instead, each
    submitted field is checked with an explicit membership test against
    `device_config.THEME_IDS` / `RUNWAY_IDS` before it is ever used as a
    dict key or passed onward.

    A field absent from `form` means "leave unchanged" and is passed as
    `None`, which `save_device_config()` carries forward from the current
    on-disk value. A field that IS present but fails the membership test
    rejects the *entire* submission (never a partial save) — applying
    only the valid half would leave the on-disk state out of sync with
    what the page would redisplay on the very next load.

    On success, the frame's next scheduled poll cycle (server/poll_loop.py,
    D-06/D-28) is the first place either the new theme or the new runway
    actually take effect — no push mechanism exists, and none is added
    here. The caller (companion/app.py) redirects back to /config, whose
    banner then renders the D-07 confirmation copy the FLASH_SAVED key
    maps to, telling the user their change was saved but has not yet
    reached the physical frame.
    """
    state_dir = ctx["state_dir"]
    submitted_theme = form.get("theme")
    submitted_runway = form.get("tracked_runway")

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        return FLASH_SAVE_FAILED

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, tracked_runway=submitted_runway)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED
    return FLASH_SAVED
