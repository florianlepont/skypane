"""The per-tab page-builder contract every module in this package follows.

Tabs are grouped into Everyday (Home, Display, Flights, Airlines) and
Advanced (Health, Device), declared once in companion/layout.py's
NAV_GROUPS. Which settings land on Display versus Device is declared per
screen type in companion/screens.py.

Every page module exposes:

    render(ctx) -> str
        Returns the page's body markup only, never a full HTML document.
        companion/app.py wraps the result with
        companion.layout.page_shell(), which supplies the
        <html>/<head>/nav/theme-toggle shell exactly once.

    ctx (built by companion/app.py's Handler.page_context()):
        - state_dir: the on-disk state directory
        - ui_theme: the resolved theme ("auto"/"light"/"dark")
        - lang: the resolved language ("fr"/"en"); presentation only, no
          POST handler consults it
        - device_config: the already-normalised device-config dict
        - flash: the resolved flash-banner text, or None
        - flash_role: "status"/"alert", the ARIA role for that text
        - poll_cooldown_remaining: seconds before another POST /poll-now
          is allowed (0 once elapsed)
        - gallery_entries: the newest gallery filenames; every gallery
          URL a page builds must come from a name in this list
        - runway_images: runway ids that currently have a real diagram
          file on disk, so a page can decide whether to emit an <img>
          without touching the filesystem itself
        - health_severity: "ok"/"warn"/"error", computed once per
          request; lets app.py draw the Health nav-tab notification dot
          without any page importing health_page.py directly
        - wake_interval_env_default: env-derived fallback for the Wake
          interval field's pre-fill, used only when the stored value is
          None (a stored value always wins)
        - now: a UTC ISO-8601 timestamp string for this request
        - resolve_prefix: the raw `?resolve=` query value, or None,
          deliberately unvalidated — airlines_page.py re-validates it on
          every use via `unresolved_row_for_prefix()`, the same
          membership test the write path re-runs, so the two can never
          diverge
        - flights_limit: the raw `?limit=` query value, or None,
          deliberately unvalidated — history_page.py clamps it on every
          use via `flights_limit(ctx)`, shared by every representation
        - manual_resolutions: the full manual-resolutions registry, read
          fresh per request — never the process-scoped cache, which
          exists only for the poll cycle's own once-per-cycle read
        - colour_rules: the full colour-rules registry, read fresh per
          request for the same reason; a companion-side save must be
          visible on the very next request, not just the next poll cycle
        - screen_id: the persisted screen id, read from the same
          device_config dict already loaded above; every consumer reads
          it through `companion.screens.current_screen_id(ctx)`, which
          membership-tests it and falls back to a default
        - last_checkin_ts: the device's last check-in timestamp, or
          None; read fresh per request as data only, never formatted
          here — each consumer formats it itself via
          `wake.next_wake_at_iso()` and `layout.local_clock_text()`

    handle_post(form, ctx) -> str
        Only modules that accept a form additionally expose this. `form`
        is the plain {field: value} dict Handler.read_form() builds. The
        return value is a flash key drawn from companion/app.py's fixed
        FLASH_MESSAGES allowlist.

Every dynamic value any page module renders passes through
companion.layout.escape_html(), directly or through one of layout's own
escaping component builders. No page module imports the stdlib `html`
module directly or reimplements escaping.
"""
