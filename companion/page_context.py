"""The typed `PageContext` every page module's `render()`/`handle_post()`
receives, and the builder that assembles one per request — moved out of
`companion/app.py`, replacing the `_LazyContext` dict subclass
that used to live there.

`PageContext` keeps `_LazyContext`'s laziness byte-for-byte: the cheap
eager fields are computed once, up front; the expensive ones — Health's
severity/markup, the gallery listing, the manual-resolutions/colour-rules/
calendar registries, and the poll cooldown — are lazy loaders, resolved at
most once, only if a route's own `render()` or the nav-dot read in
`Handler._page_shell_for()` actually touches them. Every tab still reads
`health_severity` (the nav dot), so every tab pays for one
`health_page.health_signals()` read; only Home and Health read
`health_state`, so only those two pay for the markup
`health_page.health_state_from_signals()` builds from that same snapshot.

Reading a field that was never declared raises `AttributeError` instead of
the god-dict's silent `None` — a typo in a page module or a test's ctx now
fails loudly. `coerce()` is the one place a plain `{key: value}` mapping
(built by several hundred existing unit tests, and by any future direct
call) becomes a real `PageContext`: every declared field it does not
mention defaults to `None` (the value `ctx.get()` used to return), an
unknown key raises `TypeError` naming it, and a `PageContext` already in
hand passes through unchanged. A coerced context never runs a loader — the
mapping's own values (or `None`) are final.

Only `companion.app` builds a real request `PageContext` (via
`build_page_context()`, which reads the handler's request state); this
module never imports `companion.app` — that would be a cycle. It imports
`companion.pages.{health_page,airlines_page,history_page}` and
`companion.flash` lazily, inside the functions that need them, rather
than at module level: those modules (via `companion.flash`, which imports
`companion.pages.config_page` and `companion.pages.airlines_page`) import
this module's own `coerce()` at THEIR module level, so importing them
here at module level would cycle back.
"""
import os
import sqlite3
from urllib.parse import parse_qs, urlsplit

import companion.prefs as prefs
import companion.wake as wake
from server import device_config, history_db
from server.plane import calendar_rules, colour_rules, manual_resolutions

_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_RUNWAY_IMAGE_DIR = os.path.join(_HERE, "static")

GALLERY_DIRNAME = "gallery"
GALLERY_DEFAULT_LIMIT = 30

# The 14 values every request needs regardless of which tab it renders (or
# a later eager value here depends on one) — computed once, eagerly, in
# build_page_context(). Order matches companion/pages/__init__.py's own
# contract docstring.
EAGER_FIELDS = (
    "state_dir", "ui_theme", "lang", "device_config", "screen_id",
    "last_checkin_ts", "battery_critical", "wake_interval_env_default",
    "flash", "flash_role", "runway_images", "now", "resolve_prefix",
    "flights_limit",
)

# The expensive values, resolved at most once, only if a route's own
# render() or the nav-dot read actually touches them. The two leading-
# underscore names are internal-only: shared inputs other lazy fields
# below read (through PageContext attribute access) without recomputing
# them, never read directly by a page module.
LAZY_FIELDS = (
    "_health_signals", "health_state", "health_severity", "gallery_entries",
    "manual_resolutions", "colour_rules", "calendar_configured",
    "_calendar_registry", "calendar_last_synced_at",
    "calendar_last_attempt_at", "calendar_entry_count", "calendar_drift",
    "poll_cooldown_remaining",
)

ALL_FIELDS = EAGER_FIELDS + LAZY_FIELDS


class PageContext:
    """A per-request `ctx` whose lazy fields resolve at most once, on
    first read, and only when a page actually reads them — every
    non-Health tab draws its nav-tab dot from `health_severity` alone, so
    paying for the full Health markup build (or the gallery listing, the
    manual-resolutions/colour-rules registries, or the calendar registry)
    on every request wasted most of that work.

    Constructed with the request's cheap `values` already computed
    eagerly (one per `EAGER_FIELDS` name, stored as a real `__slots__`
    attribute — always resolved), plus a `loaders` mapping of lazy field
    name -> zero-argument callable for everything in `LAZY_FIELDS`. A
    loader may itself read another lazy field through ordinary attribute
    access on `self` (a bound method / closure over the same `ctx`
    instance), the way `health_severity`'s loader reads the shared
    `_health_signals` snapshot without recomputing it.

    A loader that raises leaves its field exactly as pending as it found
    it — neither resolved nor forgotten — popped from `_loaders` only
    AFTER it returns, so a second read retries the SAME loader (and can
    raise the SAME original exception) instead of masking it.

    `coerce()` builds a `PageContext` a different way: every `LAZY_FIELDS`
    name is pre-resolved (to the mapping's own value, or `None`), with no
    loader at all — reading it never computes anything.
    """

    __slots__ = EAGER_FIELDS + ("_loaders", "_resolved")

    def __init__(self, values, loaders, resolved=None):
        for name in EAGER_FIELDS:
            setattr(self, name, values.get(name))
        self._loaders = dict(loaders)
        self._resolved = dict(resolved) if resolved else {}

    def __getattr__(self, name):
        # Only reached when ordinary attribute lookup (the __slots__
        # descriptors for EAGER_FIELDS, or an already-resolved lazy
        # field's own slot — there is none, lazy values live in
        # _resolved) fails: an eager field is always set in __init__, so
        # this is only ever reached for a lazy field name or a genuine
        # typo.
        resolved = self._resolved
        if name in resolved:
            return resolved[name]
        loaders = self._loaders
        if name in loaders:
            # Popped only AFTER loader() returns - a loader that raises
            # must leave its key exactly as it found it (still lazy, not
            # half-resolved), so a second read retries the loader.
            value = loaders[name]()
            del loaders[name]
            resolved[name] = value
            return value
        raise AttributeError(
            "PageContext has no field %r (declared fields: %s)"
            % (name, ", ".join(ALL_FIELDS)))

    def is_resolved(self, name):
        """`False` only for a lazy field whose loader has not run (and
        has not raised without being retried) yet; `True` for every
        eager field, always, and for a lazy field once resolved — via
        `coerce()`, every lazy field starts already resolved.
        """
        return name not in self._loaders

    def __repr__(self):
        resolved_names = list(EAGER_FIELDS) + [
            name for name in LAZY_FIELDS if name not in self._loaders]
        return "PageContext(%s)" % ", ".join(resolved_names)

    # --- mapping compatibility, for callers still written against the
    # old _LazyContext dict shape. Delegates to the attribute path above,
    # so `ctx["x"]`/`ctx.get("x")`/`"x" in ctx` see the same lazily
    # resolved value (and pay the same one-time cost) `ctx.x` would.
    # Deleted once no production reader uses them.

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __contains__(self, key):
        if key in EAGER_FIELDS:
            return True
        return key in self._loaders or key in self._resolved


def coerce(value):
    """`value` as a `PageContext`: unchanged if it already is one,
    otherwise built from a plain mapping (the shape several hundred
    existing unit tests, and any direct caller, still pass). Every
    declared field the mapping does not mention defaults to `None` — the
    value `ctx.get()` used to return for an absent key — and no loader
    ever runs: a mapping's own values (or `None`) are final. An unknown
    key raises `TypeError` naming it, so a typo in a test's ctx fails
    loudly instead of silently reading `None` forever.
    """
    if isinstance(value, PageContext):
        return value
    if not isinstance(value, dict):
        raise TypeError(
            "expected a PageContext or a plain mapping ctx, got %r"
            % type(value).__name__)
    unknown = sorted(set(value) - set(ALL_FIELDS))
    if unknown:
        raise TypeError(
            "coerce() received unknown PageContext field(s): %s"
            % ", ".join(unknown))
    eager_values = {name: value.get(name) for name in EAGER_FIELDS}
    lazy_resolved = {name: value.get(name) for name in LAZY_FIELDS}
    return PageContext(eager_values, {}, resolved=lazy_resolved)


def _safe_poll_cooldown_remaining(state_dir):
    """`build_page_context()`'s lazy "poll_cooldown_remaining" loader:
    degrades to 0 (cooldown elapsed) on `(sqlite3.Error, OSError)`
    instead of raising. Unlike the plain `flash.poll_cooldown_remaining()`
    — which `_handle_poll_now()` and `_resolve_flash_text()`'s
    FLASH_KEY_POLL_COOLDOWN branch both still call unguarded, since a
    database fault there means the poll trigger itself cannot be trusted
    either way — a page render's own cooldown display is decorative: the
    Device page's poll button just shows enabled rather than a wrong
    countdown, instead of 500ing every tab over one meta-table read.
    """
    from companion import flash
    try:
        return flash.poll_cooldown_remaining(state_dir)
    except (sqlite3.Error, OSError):
        return 0


def _lazy_health_state(ctx):
    """`build_page_context()`'s lazy "health_state" loader: the markup
    `health_page.health_state_from_signals()` builds from the shared
    `_health_signals` snapshot, or `None` when that snapshot itself
    failed (a fresh compute is skipped rather than opening a second,
    non-atomic set of reads at a different instant), or when building
    markup from a real snapshot raises — the same broad `except
    Exception` fail-closed contract `health_page.safe_health_state()`
    uses, since this loader replaces that direct call.
    """
    from companion.pages import health_page
    signals = ctx._health_signals
    if signals is None:
        return None
    try:
        return health_page.health_state_from_signals(signals)
    except Exception:
        return None


def _lazy_health_severity(ctx):
    """`build_page_context()`'s lazy "health_severity" loader: every tab
    reads this for its nav-tab dot, so this is the one loader every
    route pays for. Taken from "health_state" without recomputing
    anything when that markup was already built (Home, Health —
    `ctx.is_resolved("health_state")`, so checking is never itself what
    triggers the build); otherwise straight from the shared signals
    snapshot, so a route that never reads "health_state" still triggers
    only the one signals read `_health_signals`'s own loader already
    resolved. "ok" when the snapshot is `None` (a failure), the same
    fail-closed default `compute_health_state()`'s callers use.
    """
    if ctx.is_resolved("health_state"):
        health_state = ctx.health_state
        return health_state["severity"] if health_state else "ok"
    signals = ctx._health_signals
    return signals["severity"] if signals is not None else "ok"


def env_wake_interval_default():
    """Deployed SKYPANE_SLEEP_S as an int, or None. Read fresh each call,
    not captured at import time. Clamped to `[WAKE_INTERVAL_MIN_S,
    WAKE_INTERVAL_MAX_S]` only for this Settings form `min=` pre-fill —
    `wake.effective_wake_interval_s()` reads the unclamped value. Fail-open
    (None), unlike `configured_password()`'s fail-closed contract: a UI
    convenience, not an auth boundary.
    """
    value = wake.env_sleep_s()
    if value is None:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= value <= device_config.WAKE_INTERVAL_MAX_S:
        return value
    return None


def _safe_last_checkin_ts(state_dir):
    """The device's last real check-in, as the raw `device_health.ts`
    string `history_db.latest_device_health()` returns, or `None` on any
    failure — a missing/locked/unreadable database, or simply no reading
    recorded yet. Narrow `(sqlite3.Error, OSError)` catch, the same
    shape `companion.pages.health_page._safe_query()` uses so one
    section's data access never faults the whole page render.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            row = history_db.latest_device_health(conn)
    except (sqlite3.Error, OSError):
        return None
    return row["ts"] if row else None


def gallery_entries(state_dir, limit=GALLERY_DEFAULT_LIMIT):
    """The newest `limit` gallery filenames (name-descending; files are
    named by timestamp, so lexical order is chronological), filtered to
    files ending in the PNG extension. A missing gallery directory
    returns an empty list rather than raising.
    """
    gallery_dir = os.path.join(state_dir, GALLERY_DIRNAME)
    try:
        entries = sorted(
            (entry.name for entry in os.scandir(gallery_dir)
             if entry.is_file() and entry.name.endswith(".png")),
            reverse=True,
        )
    except OSError:
        return []
    return entries[:limit]


def _runway_image_filename(runway_id):
    """The single, mechanical place the on-disk naming convention is
    expressed: `runway-{runway_id}.png`.
    """
    return "runway-%s.png" % runway_id


def _runway_image_path(runway_id, image_dir=_RUNWAY_IMAGE_DIR):
    return os.path.join(image_dir, _runway_image_filename(runway_id))


def runway_images_available(image_dir=_RUNWAY_IMAGE_DIR):
    """The subset of `device_config.RUNWAY_IDS` that currently has a real
    `runway-{id}.png` file on disk. A missing `image_dir`, a missing
    individual file, or any other OS-level error while checking is a
    graceful-fallback state, not an error: `os.path.isfile()` already
    swallows `OSError`/`ValueError` and returns `False`. The result is
    bounded by the fixed `RUNWAY_IDS` registry (iterated, never
    `os.scandir()`-ed), so it can never report an image for an id that
    isn't a real runway.
    """
    available = set()
    for runway_id in device_config.RUNWAY_IDS:
        if os.path.isfile(_runway_image_path(runway_id, image_dir)):
            available.add(runway_id)
    return available


def build_page_context(handler):
    """Build the `PageContext` every page module's `render()`/
    `handle_post()` receives — documented in full in
    `companion/pages/__init__.py`. `handler` is the request's `Handler`
    instance, read for its path/args/headers/`_lang_from_request()`/
    `_resolved_ui_theme()` alone — this module owns no request state of
    its own.

    Returns a `PageContext`: the 14 `EAGER_FIELDS` values below are
    computed eagerly (every route needs them, or a later value here
    depends on one), but the expensive ones — Health's severity/markup,
    the gallery listing, the manual-resolutions/colour-rules/calendar
    registries, and the poll cooldown — are lazy loaders, resolved at
    most once, only if a route's own render() or `_page_shell_for()`'s
    nav-dot read actually touches them. Every tab still reads
    `health_severity` (the nav dot), so every tab pays for one
    `health_page.health_signals()` read; only Home and Health read
    `health_state`, so only those two pay for the markup
    `health_page.health_state_from_signals()` builds from that same
    snapshot — the invariant that keeps the nav dot and the Health
    page's own banner in agreement.
    """
    from companion import flash
    from companion.pages import airlines_page, health_page, history_page

    parsed = urlsplit(handler.path)
    params = parse_qs(parsed.query)
    flash_key = params.get("flash", [None])[0]
    # For FLASH_KEY_RULE_REPLACED's copy; re-normalised inside
    # resolve_flash_text() before ever being interpolated.
    rule_key = params.get("rule", [None])[0]
    state_dir = handler.args.state_dir
    now = history_db.utc_now_iso()
    # Must run before any Health work below: a fresh per-thread
    # ContextVar defaults to English, so setting the language late
    # would build health markup in the wrong language.
    prefs.set_request_prefs(lang=handler._lang_from_request())
    # Loaded once, reused for both "device_config" and "screen_id".
    device_cfg = device_config.load_device_config(state_dir)
    # Reused by resolve_flash_text()'s FLASH_KEY_SAVED special case.
    last_checkin_ts = _safe_last_checkin_ts(state_dir)
    # Reused by resolve_flash_text()'s delay-sentence computation.
    battery_critical = wake.read_battery_critical(state_dir)

    # Bound to a local name (not returned directly) because the loaders
    # dict below builds lambdas that close over `ctx` as a free variable
    # - e.g. "health_state": lambda: _lazy_health_state(ctx). Those
    # lambdas are stored, never called, while this dict literal is being
    # built, so `ctx` need not exist yet at that instant; Python resolves
    # a closure's free variable from the enclosing scope's cell at CALL
    # time, by which point this assignment has completed and the loader
    # can read the very instance it belongs to (the way one loader reads
    # another already-resolved lazy field, e.g. "health_severity" reading
    # "_health_signals").
    ctx = PageContext(
        {
            "state_dir": state_dir,
            "ui_theme": handler._resolved_ui_theme(),
            "lang": prefs.current_lang(),
            "device_config": device_cfg,
            # The persisted screen_id, read from the same
            # device_config dict already loaded above — consumed via
            # companion.screens.current_screen_id(ctx), which already
            # falls back to DEFAULT_SCREEN_ID for a missing/unknown
            # value.
            "screen_id": device_cfg.get("screen_id"),
            # Data only; the page module formats it, matching
            # wake.py's no-view-dependency rule.
            "last_checkin_ts": last_checkin_ts,
            "battery_critical": battery_critical,
            # An int in [WAKE_INTERVAL_MIN_S, MAX_S] or None. An
            # on-disk wake_interval_s always wins; this is only the
            # pre-fill for before the user ever sets one explicitly.
            "wake_interval_env_default": env_wake_interval_default(),
            "flash": flash.resolve_flash_text(
                flash_key, state_dir, rule_key=rule_key,
                last_checkin_ts=last_checkin_ts, device_cfg=device_cfg,
                battery_critical=battery_critical),
            "flash_role": flash.FLASH_ROLES.get(flash_key, "status"),
            "runway_images": runway_images_available(),
            "now": now,
            # Deliberately unvalidated: validation belongs to
            # airlines_page.unresolved_row_for_prefix(), the single
            # membership test shared by the render and write paths.
            "resolve_prefix": params.get(
                airlines_page.RESOLVE_QUERY_PARAM, [None])[0],
            # Deliberately unvalidated: validation belongs to
            # history_page.flights_limit(). Presentation-only.
            "flights_limit": params.get(
                history_page.FLIGHTS_LIMIT_QUERY_PARAM, [None])[0],
        },
        {
            # The severity/anomaly snapshot every tab's nav dot needs,
            # with zero markup built. Shared (never recomputed) by the
            # "health_state" and "health_severity" loaders below.
            "_health_signals": lambda: health_page.safe_health_signals(state_dir, now),
            # Only Home and Health read this — the markup step. `None`
            # both when the signals snapshot itself failed and when
            # building markup from a real snapshot raises: the same
            # fail-closed "None means ok, render() falls back to a
            # fresh compute" contract safe_health_state() has always
            # had.
            "health_state": lambda: _lazy_health_state(ctx),
            # "ok"/"warn"/"error". Taken from "health_state" without
            # recomputing it when a page already built the markup
            # (Home, Health); otherwise straight from the shared
            # signals snapshot, so a route that never reads
            # "health_state" still pays for exactly one signals read,
            # never a second one.
            "health_severity": lambda: _lazy_health_severity(ctx),
            "gallery_entries": lambda: gallery_entries(state_dir),
            # Read fresh per request, never through the poll cycle's
            # own process-scoped cache — this is a long-running
            # server.
            "manual_resolutions": lambda: manual_resolutions.load_manual_resolutions(
                state_dir),
            # Read fresh per request for the same reason.
            "colour_rules": lambda: colour_rules.load_colour_rules(state_dir),
            # A status line only needs presence, not the value: the
            # calendar URL is a subscription secret, never rendered.
            # A file-mode read, not the registry below — its own
            # loader, so a route that reads only "calendar_configured"
            # never pays for the registry's JSON parse.
            "calendar_configured": lambda: calendar_rules.calendar_is_configured(
                state_dir),
            # Loaded once, shared by the three calendar_* values below
            # so a route that reads more than one of them still pays
            # for a single registry read.
            "_calendar_registry": lambda: calendar_rules.load_calendar_registry(state_dir),
            # Read fresh from disk; a sync landing mid-session must be
            # visible on the very next request.
            "calendar_last_synced_at": lambda: ctx._calendar_registry["last_synced_at"],
            # Distinguishes "just connected, no sync yet" from "has
            # been failing", without a new server-side field.
            "calendar_last_attempt_at": lambda: ctx._calendar_registry["last_attempt_at"],
            "calendar_entry_count": lambda: len(ctx._calendar_registry["entries"]),
            # Consumed by config_page.calendar_group()'s status branch
            # alone; never widens calendar_configured's own bool
            # contract. Its own file-mode read, not the registry.
            "calendar_drift": lambda: calendar_rules.calendar_secret_mode_is_unsafe(
                state_dir),
            "poll_cooldown_remaining": lambda: _safe_poll_cooldown_remaining(state_dir),
        },
    )
    return ctx
