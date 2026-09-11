"""companion/pages/ — the SkyPane companion service's per-tab page-builder
contract.

Phase 18 (companion audit / UX refactor) reorganised the tabs into two
groups, declared once in companion/layout.py's NAV_GROUPS:

    Everyday   — Home (home_page.py), Display (config_page.py, scope
                 "display"), Flights (history_page.py), Airlines
                 (airlines_page.py)
    Advanced   — Health (health_page.py), Device (config_page.py, scope
                 "device")

The old single "/settings" page and the "/history" route survive only as
fixed redirects. Which settings groups land on Display versus Device is
declared per screen type in companion/screens.py — the seam for the
several screen kinds SkyPane will eventually drive.

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
        - resolve_prefix: the raw `?resolve=` query value, or None —
          added by plan 13-06 (D-11/D-12), deliberately unvalidated at
          this point. companion/pages/airlines_page.py's render() is the
          sole consumer; it re-validates this value on every use via
          `unresolved_row_for_prefix()`, the same D-11 membership test
          companion/app.py's `Handler._handle_manual_resolve_post()`
          re-runs on the write path, so the two can never diverge
        - manual_resolutions: `server.plane.manual_resolutions.load_
          manual_resolutions(state_dir)`'s return value — the full
          `{prefix: {"airline_name": ..., "created_at": ...}}` registry,
          read fresh per request (added by plan 13-06, D-09/D-11).
          companion/pages/airlines_page.py's render() is the sole
          consumer, for both the resolve section's Step A/B state
          machine and the always-rendered manual-resolutions management
          list. Never the process-scoped cache `manual_resolutions.
          set_manual_registry_state_dir()`/`airline_name_for_prefix()`
          expose — that cache exists only for the poll cycle's own
          once-per-cycle read, and this service is a long-running
          `ThreadingHTTPServer`
        - colour_rules: `server.plane.colour_rules.load_colour_rules(
          state_dir)`'s return value - the full `{kind: {value: {"theme_
          id": ..., "created_at": ...}}}` registry, read fresh per
          request (added by plan 14-05, D-10/D-11). companion/pages/
          config_page.py's render() is the sole consumer, for the
          per-flight colour-rules editor's list. Never the process-
          scoped cache `colour_rules.set_colour_rules_state_dir()`/
          `resolve_effective_theme_id()` expose - that cache exists only
          for the poll cycle's own once-per-cycle read, and this service
          is a long-running `ThreadingHTTPServer`; a companion-side save
          landing mid-request must always be visible on the very next
          request, not just the next poll cycle
        - screen_id: the persisted `device_config.json` `screen_id` value
          (added by 19-12-PLAN.md Task 2, D-23), read from the SAME
          `device_config` dict already loaded above — companion/app.py
          never calls `device_config.load_device_config()` twice per
          request for this. May be `None`, an unknown string, or a real
          `companion.screens.SCREEN_IDS` member; every consumer reaches
          this value through `companion.screens.current_screen_id(ctx)`,
          which already membership-tests it and falls back to
          `DEFAULT_SCREEN_ID` — no second validation is needed at this
          layer. companion/pages/config_page.py's render()/handle_post()
          are the two consumers today.
        - edit_mode: a bool, `True` only for an exact `?edit=1` query
          value (added by 19-08-PLAN.md Task 3, D-22) — computed by
          companion/app.py's `page_context()` as
          `params.get(airlines_page.EDIT_QUERY_PARAM, [None])[0] ==
          "1"`, a strict membership test, never a truthiness check or a
          substring/case-insensitive match. companion/pages/
          airlines_page.py's render() is the sole consumer: it decides
          whether the shared lightbox's artwork-editing affordances
          (replace/upload/delete) render at all. This is a
          **presentation-only** flag and must NEVER be treated as
          authorisation — the POST routes those forms target
          (`ILLUSTRATION_IMAGE_ROUTE_PREFIX`, `MANUAL_DELETE_ROUTE_
          PREFIX`) keep their own `require_session()` gate in `do_POST()`
          regardless of this key's value. Hiding a form changes what is
          offered to render, not what is permitted to execute.

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
