"""companion/pages/ — the SkyPane companion service's per-tab page-builder
contract (06-CONTEXT.md D-25's original five-tab navigation structure,
shrunk to four by 06.6.4.1-08/D-22 once Preview's page route was retired
and its content absorbed into History, 06.6.4.1-05).

Every page module in this package exposes:

    render(ctx) -> str
        Returns the page's *body* markup only — never a full HTML
        document. companion/app.py wraps every render(ctx) return value
        with companion.layout.page_shell(), which supplies the
        <html>/<head>/nav/theme-toggle shell exactly once, in one place.

    ctx (the dict every render()/handle_post() receives, built by
    companion/app.py's Handler.page_context()):
        - state_dir: the on-disk state directory (server/state by default)
        - ui_theme: the resolved CFG-09 theme ("auto"/"light"/"dark")
        - device_config: server.device_config.load_device_config()'s
          already-normalised {"theme": ..., "tracked_runway": ...} dict
        - flash: the resolved flash-banner text (already looked up
          through app.py's own fixed flash-key dictionary), or None
        - poll_cooldown_remaining: seconds remaining before another
          POST /poll-now is allowed (0 when the cooldown has elapsed) —
          added by plan 06-07 so config_page can render the CFG-07
          trigger button's enabled/disabled state without importing
          companion/app.py itself (that would be a cycle)
        - gallery_entries: the newest gallery filenames
          (companion/app.py's own gallery_entries() listing helper's
          return value) — added by plan 06-09 so companion/pages/
          history_page.py (which absorbed this key's live-panel/gallery
          consumer role from the now-retired preview_page.py in
          06.6.4.1-05/06.6.4.1-08) can build gallery tile URLs without
          importing companion/app.py itself (that would also be a
          cycle); every gallery URL history_page.py builds from this key
          is constructed only from a name in this list
        - runway_images: the set of `device_config.RUNWAY_IDS` members
          that currently have a real airport-diagram file on disk
          (companion/app.py's own `runway_images_available()`, computed
          once per request) — added by phase 06.4 so config_page can
          decide whether to emit an `<img>` tag for a given runway
          without ever performing filesystem access itself, matching this
          module's presentation-only contract
        - health_severity: "ok"/"warn"/"error", the current severity
          derived from Health's four D-14 signals
          (companion/pages/health_page.py's own `health_severity()`,
          computed once per request) — originally added by plan
          06.6.1-04 as a boolean, then widened by plan 06.6.2-06
          (UXA-14) to a real severity string, so companion/app.py can
          thread `health_alert=` into every ctx-bearing
          `layout.page_shell()` call and draw the Health nav-tab
          notification dot (and the page's own anomaly banner) from one
          value, without any nav renderer or other page module importing
          health_page.py directly (forbidden by this module's own
          contract)
        - flash_role: "status"/"alert", the ARIA role the resolved
          `flash` text should render with (companion/app.py's own
          `FLASH_ROLES` dict, resolved once per request from the
          request's flash key) — added by plan 06.6.2-06 (UXA-07) so
          `layout.flash_banner(role=...)` announces a save/poll failure
          assertively and every other outcome politely, instead of one
          role for every outcome
        - wake_interval_env_default: an int in
          [device_config.WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] or
          None — companion/app.py's own env_wake_interval_default(),
          read fresh from this process's SKYPANE_SLEEP_S environment
          variable on every request (added by plan 11-04, D-07). Its
          only consumer is companion/pages/config_page.py's render(),
          which falls back to it for the Wake interval field's pre-fill
          only when the on-disk wake_interval_s is None; a stored value
          always wins
        - now: a UTC ISO-8601 timestamp string for this request

    handle_post(form, ctx) -> str
        Only modules that accept a form (today: config_page) additionally
        expose this. `form` is the plain {field: value} dict
        Handler.read_form() builds. The return value is a flash key drawn
        from companion/app.py's fixed FLASH_MESSAGES allowlist — never an
        arbitrary string rendered later without going through that lookup.

Every dynamic value any page module renders passes through
companion.layout.escape_html() (directly, or indirectly via one of
layout's own escaping component builders such as empty_state()/
data_table()/status_dot()). No page module imports the stdlib `html`
module directly, and no page module reimplements escaping.

CFG-02 (view switching) is deliberately absent from every page in this
phase (D-08, 06-CONTEXT.md): there is still nothing to switch to until a
second device view (RER or otherwise) exists, so no page renders a
view-switcher control. Do not mistake this absence for an oversight —
CFG-02 lives in REQUIREMENTS.md's v2 "View Switching" section, revisited
only once a second view actually exists.
"""
