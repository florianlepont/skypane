"""Shared fixture-seeding and formatting helpers for the `companion/
test_status_pages*.py` migration chain (33-25..33-31): `server/history_
db.py` writers, a `server/poll_loop.py` seeding wrapper, a `server/plane/
manual_resolutions.py` seeding wrapper, and a couple of small rendered-
markup helpers several parts of the chain reuse. Not a test module
itself — `__test__ = False` keeps pytest from ever collecting it
directly, and `companion/test_suite_guards.py`'s G9 rule enforces that
this marker is present.

Deliberately excludes the legacy subprocess-lifecycle plumbing (`Harness`,
`http_request`, `_NoRedirectHandler`) and any use of the standard-library
temp-directory module: a migrated test that needs a real `companion/
app.py` server gets one from `companion/conftest.py`'s `app_server`/
`make_app_server`/`module_app_server_factory` fixtures instead, and every
fixture below writes only into the `tmp_path` a test itself provides.
The legacy harness's own raw-disk stylesheet reader is not carried
forward either — `served_css_rules()` below is its TST-12 replacement,
fetching the stylesheet the app actually serves and parsing it
structurally instead.
"""
import re
from datetime import datetime, timedelta, timezone

from server import history_db
from server.plane import manual_resolutions
import server.poll_loop as poll_loop
from companion_app_server import served_stylesheet
from companion_markup import css_rules

__test__ = False


def iso(dt):
    return dt.isoformat(timespec="seconds")


def now():
    return datetime.now(timezone.utc)


def ago(seconds):
    return iso(now() - timedelta(seconds=seconds))


def ctx(state_dir, now_value=None):
    return {"state_dir": state_dir, "now": now_value or iso(now())}


def seed_device_health(state_dir, readings):
    """`readings`: an iterable of (ts, battery_mv) pairs."""
    with history_db.open_db(state_dir) as conn:
        for ts, battery_mv in readings:
            history_db.record_device_health(conn, ts, battery_mv=battery_mv)


def seed_meta(state_dir, **kv):
    with history_db.open_db(state_dir) as conn:
        for key, value in kv.items():
            history_db.set_meta(conn, key, value)


def seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for record_runway_event()."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def seed_unresolved_prefixes(state_dir, registry):
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def seed_manual_resolutions(state_dir, entries):
    """Seed `state_dir`'s manual-resolutions registry through the one
    sanctioned write path, `manual_resolutions.add_entry()` — never by
    writing a JSON literal. `entries` is an iterable of `(prefix,
    airline_name)` pairs, or `(prefix, airline_name, created_at)` triples
    when a fixture needs a pinned timestamp — passed straight through as
    `add_entry()`'s injectable `now`.

    Raises `AssertionError` naming the prefix and the returned code if
    `add_entry()` ever returns anything other than `ADD_OK`, so a fixture
    that would have seeded nothing fails loudly instead of producing a
    vacuously-passing check downstream.
    """
    for entry in entries:
        if len(entry) == 3:
            prefix, airline_name, created_at = entry
        else:
            prefix, airline_name = entry
            created_at = None
        code = manual_resolutions.add_entry(state_dir, prefix, airline_name, now=created_at)
        if code != manual_resolutions.ADD_OK:
            raise AssertionError(
                "seed_manual_resolutions: add_entry(%r, %r) returned %r, expected %r"
                % (prefix, airline_name, code, manual_resolutions.ADD_OK))


_DIV_TOKEN_RE = re.compile(r"<div\b[^>]*>|</div>")


def stat_tile_slices(rendered):
    """Every complete `<div class="stat-tile ...">...</div>` in
    `rendered`, in document order, each sliced on BALANCED div depth (a
    `.stat-tile` body may hold its own nested `<div>` wrappers, so a
    naive "up to the next `</div>`" slice would silently stop at the
    first nested close and read a partial tile).
    """
    slices = []
    for match in re.finditer(r'<div class="stat-tile[ "]', rendered):
        start = match.start()
        depth = 0
        for token in _DIV_TOKEN_RE.finditer(rendered, start):
            depth += 1 if token.group(0) != "</div>" else -1
            if depth == 0:
                slices.append(rendered[start:token.end()])
                break
        else:
            raise AssertionError("unbalanced .stat-tile markup at offset %d" % (start,))
    return slices


def served_css_rules(server):
    """The rules of the stylesheet `server` (a running `companion/app.py`)
    actually serves — a thin wrapper over `css_rules(served_stylesheet(
    server))` for the later parts of this chain that assert on the
    served stylesheet structurally instead of reading it from disk.
    """
    return css_rules(served_stylesheet(server))
