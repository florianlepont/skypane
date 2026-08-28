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

# The single definition of this route prefix in the repository (06.4).
# companion/app.py rebinds it (RUNWAY_IMAGE_ROUTE_PREFIX =
# config_page.RUNWAY_IMAGE_ROUTE_PREFIX) rather than re-typing the
# literal, exactly as it already does for the FLASH_KEY_* constants —
# app.py imports this module, so the reverse import would be a cycle.
RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = "Airport diagram for %s"
LED_HELPER_TEXT = (
    "Controls the board's built-in bring-up LED. It's lit only during the "
    "device's brief active wake window and isn't visible from the "
    "wall-facing side. Applies on the device's next scheduled poll — not "
    "immediately.")

# The sole accepted submitted value for the LED checkbox (D-01) — shared
# by led_fieldset()'s markup and handle_led_post()'s validator so the two
# can never drift apart.
LED_CHECKBOX_VALUE = "on"

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


def runway_fieldset(current_runway_id, images_available=()):
    """One radio input per `device_config.RUNWAYS` entry (exactly three
    today), in registry order, with `current_runway_id` marked selected —
    plus the CFG-12 helper text stating the change applies on the
    device's next scheduled poll, not immediately (D-28).

    Each option's number/heading label is promoted into a Display-size
    `<span>` (D-01). When `runway_id` is a member of `images_available`
    (the `ctx["runway_images"]` set companion/app.py computes — this
    module never touches the filesystem itself), an `<img>` pointing at
    the session-gated `/runway-image/{id}.png` route is also rendered.
    `images_available` defaults to `()` — "no images available" — the
    safe D-03 fallback, which is also what every pre-06.4 single-argument
    call site still gets.
    """
    options = []
    for runway_id in device_config.RUNWAY_IDS:
        checked = " checked" if runway_id == current_runway_id else ""
        label = device_config.runway_label(runway_id)
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-option__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(RUNWAY_IMAGE_ALT_TEMPLATE % label),
                )
            )
        options.append(
            '<label class="runway-option">'
            '<input type="radio" name="tracked_runway" value="%s"%s>'
            '<span class="runway-option__number">%s</span>'
            "%s"
            "</label>"
            % (escaped_id, checked, escape_html(label), image_html)
        )
    return (
        "<fieldset>"
        "<legend>Runway</legend>"
        "%s"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % ("".join(options), escape_html(RUNWAY_HELPER_TEXT))


def led_fieldset(current_led_enabled):
    """A single checkbox controlling the CFG-LED bring-up LED (D-01/D-02):
    a `<label>` wrapping `<input type="checkbox" name="led_enabled"
    value="on">`, carrying a bare `checked` attribute only when
    `current_led_enabled` is truthy, plus the helper text explaining what
    the control does.
    """
    checked = " checked" if current_led_enabled else ""
    return (
        "<fieldset>"
        "<legend>Bring-up LED</legend>"
        "<label>"
        '<input type="checkbox" name="led_enabled" value="%s"%s> Enable bring-up LED'
        "</label>"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % (escape_html(LED_CHECKBOX_VALUE), checked, escape_html(LED_HELPER_TEXT))


def led_section(current_led_enabled):
    """Wraps led_fieldset() in its own dedicated, independently-submittable
    `<section>`/`<form>` (D-01) — mirroring poll_trigger_section()'s own
    "own dedicated form" precedent. See render()'s comment for why this is
    NOT folded into the Theme/Runway `<form action="/config">`.
    """
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">Bring-up LED</h2>'
        '<form method="post" action="/config-led">'
        "%s"
        '<button type="submit">Save LED Setting</button>'
        "</form>"
        "</section>"
    ) % led_fieldset(current_led_enabled)


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
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)

    # The LED section is deliberately a sibling page-section, appended
    # AFTER the Poll section, rather than a third fieldset inside the
    # `<form action="/config">` block above: 06.3-UI-SPEC.md line 181
    # locks a 2-column grid over that form's fieldsets at >=960px, and a
    # third fieldset there would become a silent 2+1 orphan row. As its
    # own sibling page-section it stacks below like the Poll section
    # instead, leaving that grid rule untouched. Do not "fix" this by
    # moving it into the fieldset grid (06.2-01-PLAN.md Task 2, step 5).
    return (
        '<h1 class="text-heading">Config</h1>'
        '<form class="config-form" method="post" action="/config">'
        "%s"
        "%s"
        '<button type="submit">Save Settings</button>'
        "</form>"
        '<section class="page-section">'
        '<h2 class="text-heading">Poll</h2>'
        "%s"
        "</section>"
        "%s"
    ) % (
        theme_fieldset(current_theme_id),
        runway_fieldset(current_runway_id, ctx.get("runway_images") or ()),
        poll_trigger_section(cooldown_remaining),
        led_section(current_led_enabled),
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


def handle_led_post(form, ctx):
    """Validate and persist the LED checkbox submission (D-01, T-06.2-02).

    Same asymmetric-validation discipline handle_post()'s own docstring
    states: the read path forgives via `device_config.normalise_led_enabled()`,
    this write path rejects the whole submission and never silently
    coerces. Exactly three shapes are resolved and no others:
      - the field is absent from `form` (an unchecked HTML checkbox is
        omitted from the POST body entirely) -> `led_enabled=False`;
      - the field equals `LED_CHECKBOX_VALUE` -> `led_enabled=True`;
      - anything else (a crafted/hostile value) -> reject the whole
        submission with FLASH_SAVE_FAILED, before any write.

    Reuses FLASH_SAVED/FLASH_SAVE_FAILED rather than adding new flash
    keys — this action's user-facing outcome is exactly what those keys
    already say.
    """
    state_dir = ctx["state_dir"]
    submitted = form.get("led_enabled")

    if submitted is None:
        led_enabled = False
    elif submitted == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        return FLASH_SAVE_FAILED

    try:
        device_config.save_device_config(state_dir, led_enabled=led_enabled)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED
    return FLASH_SAVED
