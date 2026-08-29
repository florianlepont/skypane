"""companion/pages/ — the SkyPane companion service's per-tab page-builder
contract (06-CONTEXT.md D-25's five-tab navigation structure).

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
          return value) — added by plan 06-09 so preview_page can build
          gallery tile URLs without importing companion/app.py itself
          (that would also be a cycle); every gallery URL preview_page
          builds is constructed only from a name in this list
        - runway_images: the set of `device_config.RUNWAY_IDS` members
          that currently have a real airport-diagram file on disk
          (companion/app.py's own `runway_images_available()`, computed
          once per request) — added by phase 06.4 so config_page can
          decide whether to emit an `<img>` tag for a given runway
          without ever performing filesystem access itself, matching this
          module's presentation-only contract
        - health_anomaly_active: a boolean, True when any of Health's
          four D-14 signals is currently unhealthy
          (companion/pages/health_page.py's own `anomaly_active()`,
          computed once per request) — added by plan 06.6.1-04 so
          companion/app.py can thread `health_alert=` into every
          ctx-bearing `layout.page_shell()` call and draw the Health
          nav-tab notification dot from every tab, without any nav
          renderer or other page module importing health_page.py
          directly (forbidden by this module's own contract)
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
