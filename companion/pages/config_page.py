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
import json

from companion.layout import escape_html
import companion.layout as layout
from server import device_config, panel_format

# D-04: was "More themes will be added once Phase 7 validates additional
# color options on real hardware." — UXA-05 flagged that wording as a
# leaked internal planning reference (a phase number meaningless to an
# operator). Reused verbatim by both theme_fieldset() branches (the
# read-only status block and the >1-theme radio-group fallback) so the
# sentence exists in exactly one place.
THEME_HELPER_TEXT = (
    "Additional themes will appear here once more are validated on real "
    "hardware.")
RUNWAY_HELPER_TEXT = (
    "Applies on the device's next scheduled poll — not immediately.")

# The single definition of this route prefix in the repository (06.4).
# companion/app.py rebinds it (RUNWAY_IMAGE_ROUTE_PREFIX =
# config_page.RUNWAY_IMAGE_ROUTE_PREFIX) rather than re-typing the
# literal, exactly as it already does for the FLASH_KEY_* constants —
# app.py imports this module, so the reverse import would be a cycle.
RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = "Airport diagram for %s"

# The single definition of this route in the repository (06.6.4.1, D-05).
# companion/app.py still dispatches the OLD "/config" path (its own
# CONFIG_ROUTE literal) until plan 07 rebinds CONFIG_ROUTE to this
# constant, mirroring RUNWAY_IMAGE_ROUTE_PREFIX's own rebinding
# discipline above — app.py imports this module, so the reverse import
# would be a cycle. Do not delete companion/app.py's separate "/config"
# dispatch before that flip lands.
SETTINGS_ROUTE = "/settings"
LED_HELPER_TEXT = (
    "Controls the board's built-in diagnostic LED. It's lit only during "
    "the device's brief active wake window and isn't visible from the "
    "wall-facing side. Applies on the device's next scheduled poll — not "
    "immediately.")

# The sole accepted submitted value for the LED checkbox (D-01) — shared
# by led_fieldset()'s markup and handle_led_post()'s validator so the two
# can never drift apart.
LED_CHECKBOX_VALUE = "on"

# D-02 (06.6.4.1): one description sentence per settings group, rendered
# directly under each group's heading. Diagnostic LED needs no entry
# here — LED_HELPER_TEXT above already reads as a description sentence
# and already renders under its heading (UI-SPEC §5.1's table).
THEME_SECTION_DESCRIPTION = (
    "The color palette used for departing and arriving flights on the "
    "physical frame.")
RUNWAY_SECTION_DESCRIPTION = (
    "Which Orly runway the device watches for departures and arrivals.")
# D-05 (06.6.4.1): the LED group's new user-facing heading, once it moves
# from its own <fieldset>/<legend> into a sibling <h2>-headed group of
# the merged form — see led_group() below.
LED_SECTION_HEADING = "Diagnostic LED"

# Read elsewhere, not just here — this module's existing
# duplicated-not-imported must-equal discipline (matches
# OPEN_CLASS/MOBILE_NAV_OPEN_CLASS's own precedent): DIRTY_SECTION_ATTR
# is read by companion/static/dirty-state.js (the section-aware
# [data-dirty-count] copy walks every element carrying this attribute),
# and STATIC_SAVE_FALLBACK_ATTR is read by a `.js`-gated rule in
# companion/static/style.css (`.js [data-static-save-fallback] {
# display: none; }`, landed by 06.6.4.1-01). Neither file imports this
# module — the values must be kept equal by hand.
DIRTY_SECTION_ATTR = "data-dirty-section"
STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"
# D-03: the dirty-bar's seeded [data-dirty-count] text before
# dirty-state.js's own section-aware copy ever runs (a no-JS page, or
# the brief window before the script executes, would otherwise show
# this raw string).
DIRTY_BAR_INITIAL_TEXT = "Unsaved changes"

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

# DOM ids the D-01 live countdown script (_poll_cooldown_script(), below)
# hooks with document.getElementById() — shared between poll_trigger_
# section()'s markup and the script it emits so the two can never drift
# apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# UXA-15: the enabled (zero-cooldown) branch's button label while a
# submit is pending, swapped in by _poll_submit_script() below. Cosmetic
# only — companion/app.py's _POLL_LOCK is the actual correctness
# boundary, this is purely the immediate-feedback affordance.
POLL_SUBMIT_PENDING_TEXT = "Polling…"

# The placeholder the client substitutes the live second count into. The
# countdown reuses POLL_COOLDOWN_HELPER_TEXT with this token standing in
# for the "{n}" slot precisely so the ticking copy stays word-identical to
# the static, server-rendered copy above and to companion/app.py's
# FLASH_MESSAGES[FLASH_KEY_POLL_COOLDOWN] post-redirect banner. The copy
# exists in one place (this constant) and is formatted twice — once with
# a real integer for the no-JS render, once with this token for the
# script template — never rewritten or duplicated.
POLL_COOLDOWN_TEMPLATE_TOKEN = "__N__"

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
# Distinct from FLASH_POLL_COOLDOWN (UXA-15 fix): the cooldown key means
# "wait, you already triggered one recently" (a stale, seconds-old fact
# checked against history_db). This key means "a poll is executing on
# this exact request, right now, in another thread" — companion/app.py's
# non-blocking `_POLL_LOCK.acquire(blocking=False)` failing is the only
# thing that ever produces it, closing the TOCTOU window where two
# requests arriving before the first finishes could both observe zero
# cooldown and both call `poll_loop.run_once()`.
FLASH_POLL_ALREADY_RUNNING = "poll_already_running"


def _palette_hex(index):
    """`#RRGGBB`, computed from `server.panel_format.PALETTE_RGB`'s flat
    int list at palette index `index` — never a hardcoded hex literal, so
    a future re-tuning of the physical panel ink (07-01-PLAN.md's own
    real-glass Blue/Green correction precedent) automatically updates
    every swatch that calls this helper.
    """
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def theme_fieldset(current_theme_id):
    """D-04: a read-only theme status block when exactly one theme is
    registered (`len(device_config.THEME_IDS) == 1`, true today) — a
    one-option radio group has no real decision value. Falls back to the
    original editable radio-group markup automatically the moment a
    second theme is registered; this is a `len()` check, not a hardcoded
    single-theme assumption.
    """
    if len(device_config.THEME_IDS) == 1:
        theme_id = (
            current_theme_id if current_theme_id in device_config.THEMES
            else device_config.THEME_IDS[0])
        theme = device_config.THEMES[theme_id]
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        return (
            '<div class="theme-status" %s="%s">'
            '<h2 class="text-heading">Theme</h2>'
            '<p class="text-body">%s</p>'
            '<div class="theme-status__row">'
            '<span class="theme-swatch" aria-hidden="true">'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            "</span>"
            '<span class="text-body">%s · current</span>'
            "</div>"
            '<p class="text-label">%s</p>'
            "</div>"
        ) % (
            DIRTY_SECTION_ATTR, escape_html("Theme"),
            escape_html(THEME_SECTION_DESCRIPTION),
            departing_hex, arriving_hex,
            escape_html(device_config.theme_label(theme_id)),
            escape_html(THEME_HELPER_TEXT),
        )

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
        '<fieldset %s="%s">'
        "<legend>Theme</legend>"
        '<p class="text-body">%s</p>'
        "%s"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html("Theme"),
        escape_html(THEME_SECTION_DESCRIPTION),
        "".join(options), escape_html(THEME_HELPER_TEXT),
    )


def runway_fieldset(current_runway_id, images_available=()):
    """D-05: one selectable `.runway-card` per `device_config.RUNWAYS`
    entry (exactly three today), in registry order — the entire card
    (`<label>`) is the hit target, wrapping a visually-hidden (never
    `display:none`) native radio input so keyboard/no-JS selection still
    works natively. `current_runway_id` marks the matching card
    `runway-card--selected`, computed server-side from the same
    membership comparison the radio's own `checked` attribute uses —
    never a client-side `:has()` CSS trick.

    Each card also carries a `runway-card__check` icon-check glyph,
    present in every card's markup — CSS shows it only on the selected
    card via the `runway-card--selected` modifier, so no second
    server-side conditional is needed for the icon itself.

    When `runway_id` is a member of `images_available` (the
    `ctx["runway_images"]` set companion/app.py computes — this module
    never touches the filesystem itself), an `<img>` pointing at the
    session-gated `/runway-image/{id}.png` route is also rendered.
    `images_available` defaults to `()` — "no images available" — the
    safe D-03 fallback, which is also what every pre-06.4 single-argument
    call site still gets. The CFG-12 helper text (applies on the
    device's next scheduled poll, not immediately — D-28) renders once
    after the card list.

    The whole return value is wrapped in a single `<div class="theme-status"
    data-dirty-section="Runway">` — the same wrapping idiom
    `theme_fieldset()`'s read-only branch already uses, reused verbatim
    (D-01, 06.6.4.1): the group used to return five flat top-level
    siblings (an `<h2>`, N cards, a `<p>`) with no container at all, which
    was the actual root cause of Settings' broken Runway layout once it
    sat inside a two-column grid. That grid is now deleted, but the
    wrapper stays — it is what makes this group, like Theme and the new
    LED group, a single top-level element `dirty-state.js`'s
    `data-dirty-section` walk can address as one unit, and what carries
    the D-02 description paragraph (`RUNWAY_SECTION_DESCRIPTION`)
    directly under the `<h2 class="text-heading">Runway</h2>` heading.
    The group is named by that `<h2>`, not a `<legend>`, because D-04/D-05
    (06.6.3) already dropped the `<fieldset>` wrapper from both the Theme
    and Runway groups, and a `<legend>` outside a `<fieldset>` is invalid
    markup with no accessible group semantics — `<h2 class="text-heading">`
    is the role the Poll section and the new LED group both use too, so
    every group in this form reads at one consistent heading level.
    """
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == current_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        label = device_config.runway_label(runway_id)
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-card__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(RUNWAY_IMAGE_ALT_TEMPLATE % label),
                )
            )
        cards.append(
            '<label class="%s">'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">Selected</span></span>'
            "</label>"
            % (
                card_class, escaped_id, checked, escape_html(label),
                image_html, layout.icon_html("icon-check"),
            )
        )
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">Runway</h2>'
        '<p class="text-body">%s</p>'
        "%s"
        '<p class="text-label">%s</p>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html("Runway"),
        escape_html(RUNWAY_SECTION_DESCRIPTION),
        "".join(cards), escape_html(RUNWAY_HELPER_TEXT),
    )


# Left in place, unreferenced by render() as of 06.6.4.1 (D-05): render()
# now shows the LED checkbox via the new led_group() below instead, so
# neither this function nor its caller led_section() renders on any live
# page anymore. Both stay in the file anyway: companion/app.py's separate
# POST /config-led route still dispatches to handle_led_post() below
# (unaffected by this plan), and deleting either function two waves
# before that route itself is retired would be premature. Plan 07 deletes
# both, together with the route, once companion/app.py stops calling
# handle_led_post().
def led_fieldset(current_led_enabled):
    """A single checkbox controlling the CFG-LED diagnostic LED (D-01/D-02):
    a `<label>` wrapping `<input type="checkbox" name="led_enabled"
    value="on">`, carrying a bare `checked` attribute only when
    `current_led_enabled` is truthy, plus the helper text explaining what
    the control does.

    D-02: every user-facing string here reads "Diagnostic LED" — the
    internal identifiers (this function's own name, LED_HELPER_TEXT,
    LED_CHECKBOX_VALUE, LED_ROUTE) are unchanged by name; this is a
    copy-only rename.
    """
    checked = " checked" if current_led_enabled else ""
    return (
        "<fieldset>"
        "<legend>Diagnostic LED</legend>"
        "<label>"
        '<input type="checkbox" name="led_enabled" value="%s"%s> Enable diagnostic LED'
        "</label>"
        '<p class="text-label">%s</p>'
        "</fieldset>"
    ) % (escape_html(LED_CHECKBOX_VALUE), checked, escape_html(LED_HELPER_TEXT))


# Left in place, unreferenced by render() as of 06.6.4.1 (D-05) for the
# same reason stated above led_fieldset(): companion/app.py's POST
# /config-led route still calls handle_led_post() (which does not call
# this function or led_fieldset() at all — validation and rendering are
# already independent code paths), so removing this render-only function
# early is not required to keep that route working, but removing it out
# of step with led_fieldset() and handle_led_post() would be an
# inconsistent partial cleanup. Plan 07 removes it together with them.
def led_section(current_led_enabled):
    """Wraps led_fieldset() in its own dedicated, independently-submittable
    `<section>`/`<form>` (D-01) — mirroring poll_trigger_section()'s own
    "own dedicated form" precedent. See render()'s comment for why this is
    NOT folded into the Theme/Runway `<form action="/config">`.

    D-06: no independent `<h2>` here — led_fieldset()'s own
    `<legend>Diagnostic LED</legend>` is this section's sole accessible
    group name, matching the sibling Theme/Runway fieldsets inside
    `.config-form`, which already have no independent `<h2>` of their own.
    A prior revision duplicated the name via both an `<h2>` and the
    `<legend>` — do not reintroduce that `<h2>`.
    """
    return (
        '<section class="page-section">'
        '<form method="post" action="/config-led">'
        "%s"
        '<button type="submit">Save LED Setting</button>'
        "</form>"
        "</section>"
    ) % led_fieldset(current_led_enabled)


def led_group(current_led_enabled):
    """The Diagnostic LED settings group (D-05, 06.6.4.1): a sibling of the
    Theme and Runway groups inside the single merged `<form
    action="{SETTINGS_ROUTE}">`, wrapped in the same `.theme-status`
    container idiom those two groups use — the `theme-status` class name
    is reused verbatim, not a third wrapper class invented for this group.

    Deliberately carries no `<fieldset>`/`<legend>` of its own, unlike
    `led_fieldset()` above. The old `<fieldset>` existed because the LED
    control used to live in its own independently-submittable
    `<form>` (`led_section()`, pre-06.6.4.1), and a `<legend>` only has
    accessible-name semantics inside a `<fieldset>`. Now that this group
    is a sibling of two `<h2>`-headed groups in one single-column stack
    (Theme's and Runway's own `<fieldset>` wrappers were already dropped
    by D-04/D-05 in 06.6.3), it is named the same way they are — an `<h2
    class="text-heading">` — so all three groups read at one consistent
    heading level, matching the Poll section's own heading role.

    Per UI-SPEC §5.2's table, LED needs no new D-02 description
    sentence: `LED_HELPER_TEXT` already reads as one and renders directly
    under the heading here, the same position Theme's and Runway's new
    description paragraphs occupy in their own groups.
    """
    checked = " checked" if current_led_enabled else ""
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        "<label>"
        '<input type="checkbox" name="led_enabled" value="%s"%s> Enable diagnostic LED'
        "</label>"
        '<p class="text-label">%s</p>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(LED_SECTION_HEADING),
        escape_html(LED_SECTION_HEADING),
        escape_html(LED_CHECKBOX_VALUE), checked,
        escape_html(LED_HELPER_TEXT),
    )


def _js_literal(value):
    """The single, mandatory gate for every Python value crossing into
    `_poll_cooldown_script()`'s inline `<script>` body. Never interpolate
    a Python value into the script with `%` or an f-string — always route
    it through this function.

    Two reasons: `json.dumps()` of an `int` or `str` is, by construction,
    a syntactically valid, correctly-escaped JavaScript literal, which
    hand-rolled quoting is not; and rewriting every `</` occurrence in
    the result to `<\\/` means no future copy change containing a
    closing-tag-like sequence (e.g. `</script>`) can terminate the
    script element early. `json.dumps()` defaults to ASCII-only output,
    so the em dash in POLL_COOLDOWN_HELPER_TEXT is emitted as a `\\u...`
    escape sequence and the script body stays pure ASCII.
    """
    return json.dumps(value).replace("</", "<\\/")


def _poll_cooldown_script(cooldown_remaining):
    """A `<script>` element with no attributes, rendered only on
    `poll_trigger_section()`'s disabled branch (D-01). Its body is a
    single immediately-invoked function expression, written in an
    ES5-safe subset (`var`, `function`, no arrow functions, no
    `let`/`const`, no template literals) so no transpiler is ever
    needed — matching the convention 06.5-01-PLAN.md establishes for
    this codebase's first piece of client-side JavaScript
    (companion/static/battery-trend.js).

    Every value crossing the Python-to-JavaScript boundary goes through
    `_js_literal()` — never `%`/f-string interpolation. The script
    resolves both DOM elements with `document.getElementById` and
    returns immediately if either is absent or the seeded value is not
    greater than zero, so it is inert and harmless on any page whose
    markup has changed. It mutates the DOM only through the paragraph's
    `textContent` property and the button's `removeAttribute` — no
    HTML-writing sink, no dynamic code evaluation, no network call. It
    leaks no global (everything lives inside the IIFE) and holds no
    persistent state.
    """
    template = POLL_COOLDOWN_HELPER_TEXT.format(n=POLL_COOLDOWN_TEMPLATE_TOKEN)
    return (
        "<script>"
        '(function () {'
        '"use strict";'
        "var remaining = %s;"
        "var btn = document.getElementById(%s);"
        "var text = document.getElementById(%s);"
        "if (!btn || !text || remaining <= 0) { return; }"
        "var template = %s;"
        "var token = %s;"
        "var timer = setInterval(function () {"
        "remaining -= 1;"
        "if (remaining <= 0) {"
        "clearInterval(timer);"
        'btn.removeAttribute("disabled");'
        'text.textContent = "";'
        "return;"
        "}"
        "text.textContent = template.replace(token, String(remaining));"
        "}, 1000);"
        "})();"
        "</script>"
    ) % (
        _js_literal(cooldown_remaining),
        _js_literal(POLL_TRIGGER_BUTTON_ID),
        _js_literal(POLL_COOLDOWN_TEXT_ID),
        _js_literal(template),
        _js_literal(POLL_COOLDOWN_TEMPLATE_TOKEN),
    )


def _poll_submit_script():
    """A `<script>` element with no attributes, rendered only on
    `poll_trigger_section()`'s enabled (zero-cooldown) branch (UXA-15).
    Its body is a single immediately-invoked function expression,
    written in the same ES5-safe subset (`var`, `function`, no arrow
    functions, no `let`/`const`, no template literals) and
    `_js_literal()`-gated convention `_poll_cooldown_script()` above
    establishes — never `%`/f-string interpolation into the script body.

    On the button's owning form's `submit` event, disables the button
    and swaps its label to `POLL_SUBMIT_PENDING_TEXT` — immediate
    visible acknowledgement that the click registered, before the
    server round-trip completes. Guards with `if (!btn) { return; }` so
    it is inert and harmless on any page whose markup has changed. It
    mutates the DOM only through the button's `disabled` and
    `textContent` properties — no HTML-writing sink, no dynamic code
    evaluation, no network call.

    This is cosmetic only, never a trust boundary: companion/app.py's
    `_POLL_LOCK` (a process-global, non-blocking `threading.Lock()`
    guarding `_handle_poll_now()`'s entire check-run-mark sequence) is
    the actual correctness boundary that prevents two overlapping polls
    from ever executing concurrently. A user who re-enables this button
    by hand in devtools, or who submits the no-JS form from two tabs,
    still cannot trigger a second concurrent poll cycle — the
    server-side lock alone decides that, honestly reporting
    "already running" to whichever request loses the race.
    """
    return (
        "<script>"
        '(function () {'
        '"use strict";'
        "var btn = document.getElementById(%s);"
        "if (!btn) { return; }"
        "var form = btn.form;"
        "if (!form) { return; }"
        'form.addEventListener("submit", function () {'
        "btn.disabled = true;"
        "btn.textContent = %s;"
        "});"
        "})();"
        "</script>"
    ) % (
        _js_literal(POLL_TRIGGER_BUTTON_ID),
        _js_literal(POLL_SUBMIT_PENDING_TEXT),
    )


def poll_trigger_section(cooldown_remaining):
    """The CFG-07 manual-trigger control: an enabled button when
    `cooldown_remaining` is zero, or a native-disabled button plus the
    D-17 remaining-seconds copy otherwise.

    D-01: on the disabled branch, the button and paragraph also gain
    `id` attributes and a `_poll_cooldown_script()` is appended after
    the paragraph — a live, ticking countdown that decrements once per
    second and re-enables the button (and clears the copy) at zero,
    with no page reload. Its starting value is the server-computed,
    history_db-persisted figure that companion/app.py's
    `poll_cooldown_remaining()` puts in `ctx["poll_cooldown_remaining"]`,
    so it survives a service restart and stays correct across multiple
    tabs — the client never re-derives it from the cooldown duration
    constant (`POLL_COOLDOWN_S`). A browser with JavaScript disabled
    still sees exactly the same server-rendered copy and markup as
    before this change.

    The countdown script renders only on this disabled branch. The
    zero-cooldown (enabled) branch below carries its own, different
    script — `_poll_submit_script()`'s UXA-15 "Polling…" disable-on-
    submit affordance — never the countdown script. Both are UX
    affordances only, never a trust boundary: companion/app.py's
    `_handle_poll_now()` independently re-checks the cooldown
    server-side, and its `_POLL_LOCK` independently serializes
    execution, before it would ever call `poll_loop.run_once()` — so a
    user who re-enables either button by hand in devtools still cannot
    poll early or trigger two concurrent polls.
    """
    # `> 0`, not truthy: must agree with _poll_cooldown_script()'s own
    # `remaining <= 0` early-return, or a negative value would take this
    # branch (natively disabling the button) while the script inertly
    # no-ops, leaving no way to re-enable it client-side.
    if cooldown_remaining > 0:
        cooldown_text = POLL_COOLDOWN_HELPER_TEXT.format(n=cooldown_remaining)
        return (
            '<form method="post" action="/poll-now">'
            '<button type="submit" id="%s" disabled>Trigger Poll Now</button>'
            "</form>"
            '<p class="text-body" id="%s">%s</p>'
            "%s"
        ) % (
            POLL_TRIGGER_BUTTON_ID,
            POLL_COOLDOWN_TEXT_ID,
            escape_html(cooldown_text),
            _poll_cooldown_script(cooldown_remaining),
        )
    return (
        '<form method="post" action="/poll-now">'
        '<button type="submit" id="%s">Trigger Poll Now</button>'
        "</form>"
        "%s"
    ) % (
        POLL_TRIGGER_BUTTON_ID,
        _poll_submit_script(),
    )


def render(ctx):
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)

    # D-05 (06.6.4.1): the LED group used to be a sibling page-section,
    # appended AFTER the Poll section, rather than a third fieldset
    # inside this form — 06.3-UI-SPEC.md line 181 locked a 2-column grid
    # over this form's fieldsets at >=960px, and a third fieldset there
    # would have become a silent 2+1 orphan row. That grid is deleted
    # outright by 06.6.4.1-01 (D-01) — the premise this comment used to
    # describe no longer exists, so the LED group (led_group(), below) is
    # now a third sibling group inside this same <form>, after Runway,
    # before the bottom Save Settings button. Do not restore the
    # separate section by reading a stale rationale.
    #
    # D-03: data-dirty-form and the dirty-bar markup below are a JS-only
    # enhancement layered on top of this always-server-rendered form —
    # dirty-state.js reads these exact attributes. The dirty-bar is a
    # genuine descendant of this <form>, sitting between the three groups
    # and the always-visible bottom Save Settings button (the no-JS
    # fallback path, unchanged) — never a sibling, so its own <button
    # type="submit"> submits natively via normal DOM nesting, no form=
    # attribute needed.
    dirty_bar_html = (
        '<div class="dirty-bar" data-dirty-bar hidden role="status">'
        "<span data-dirty-count>%s</span>"
        '<button type="submit" class="dirty-bar__save">Save settings</button>'
        '<button type="button" class="dirty-bar__cancel" data-dirty-cancel>Cancel</button>'
        "</div>"
    ) % escape_html(DIRTY_BAR_INITIAL_TEXT)

    return (
        layout.page_header("Config")
        + '<form class="config-form" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        "%s"
        "%s"
        '<button type="submit" %s>Save Settings</button>'
        "</form>"
        '<section class="page-section">'
        '<h2 class="text-heading">Poll</h2>'
        "%s"
        "</section>"
    ) % (
        SETTINGS_ROUTE,
        theme_fieldset(current_theme_id),
        runway_fieldset(current_runway_id, ctx.get("runway_images") or ()),
        led_group(current_led_enabled),
        dirty_bar_html,
        STATIC_SAVE_FALLBACK_ATTR,
        poll_trigger_section(cooldown_remaining),
    )


def handle_post(form, ctx):
    """Validate the submitted theme/runway/LED state against
    `device_config`'s own registries — server-side, before any value is
    used anywhere — and persist all three in a single
    `save_device_config()` call (D-05, 06.6.4.1: this handler now absorbs
    what `handle_led_post()` used to do on its own separate route).

    Deliberately does NOT call any of `device_config`'s read-path
    normalising helpers (the ones an unrecognised on-disk value silently
    degrades through to the default): those implement the *read* path's
    forgiving behaviour, whereas a *write* of an unrecognised value is a
    real client error that must be reported back to the user, not
    silently coerced — the asymmetry is deliberate (06-CONTEXT.md
    D-06/D-07, 06-RESEARCH.md's V5 threat control). Instead, each
    submitted field is checked explicitly before it is ever used as a
    dict key or passed onward: `theme`/`tracked_runway` by membership
    test against `device_config.THEME_IDS`/`RUNWAY_IDS`, `led_enabled` by
    exact equality against `LED_CHECKBOX_VALUE`.

    Two properties are load-bearing here, not incidental:

    First, the LED field's absent-means-False semantics is deliberately
    different from theme's and runway's absent-means-unchanged semantics.
    A field absent from `form` for `theme`/`tracked_runway` means "leave
    unchanged" and is passed as `None`, which `save_device_config()`
    carries forward from the current on-disk value — because a radio
    group and a select always submit *some* value once one is selected,
    absence there only ever means "this page didn't render that control."
    An HTML checkbox is different: an *unchecked* checkbox is omitted
    from the POST body entirely, so `led_enabled`'s absence must resolve
    to `False`, never to "leave unchanged" — carrying it forward instead
    would silently re-enable a disabled LED on every save that happens to
    leave the box unchecked. Exactly three shapes are resolved for
    `led_enabled` and no others: absent -> `False`; equal to
    `LED_CHECKBOX_VALUE` -> `True`; anything else (a crafted/hostile
    value) -> reject the whole submission.

    Second, rejection stays all-or-nothing across all three fields, now
    more so than before the merge: because there is now one form and one
    `save_device_config()` call, a crafted or invalid value in ANY field
    aborts before that call, never persisting the valid remainder —
    applying only the valid half would leave the on-disk state out of
    sync with what the page would redisplay on the very next load.

    On success, the frame's next scheduled poll cycle (server/poll_loop.py,
    D-06/D-28) is the first place any of the three changes actually take
    effect — no push mechanism exists, and none is added here. The caller
    (companion/app.py) redirects back to `SETTINGS_ROUTE`, whose banner
    then renders the D-07 confirmation copy the FLASH_SAVED key maps to,
    telling the user their change was saved but has not yet reached the
    physical frame.
    """
    state_dir = ctx["state_dir"]
    submitted_theme = form.get("theme")
    submitted_runway = form.get("tracked_runway")
    submitted_led = form.get("led_enabled")

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        return FLASH_SAVE_FAILED
    if submitted_led is None:
        led_enabled = False
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        return FLASH_SAVE_FAILED

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, tracked_runway=submitted_runway,
            led_enabled=led_enabled)
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
