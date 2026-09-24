"""Shared seeding/render helpers for the `companion/test_view_pages*.py`
migration chain (33-05..33-08). Not a test module itself — `__test__ =
False` keeps pytest from ever collecting it directly, and
`companion/test_suite_guards.py`'s G9 rule enforces that this marker is
present.

The original `companion/test_view_pages.py`'s subprocess-lifecycle
plumbing (its own harness class, HTTP client and non-redirect-following
opener) is deliberately NOT ported here: migrated tests get a real
`companion/app.py` server (when they need one at all) from
`companion/conftest.py`'s `app_server` / `module_app_server_factory`
fixtures instead.
"""
from server import history_db

__test__ = False


def seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for
    `server.history_db.record_runway_event()`."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def history_ctx(state_dir, now=None, gallery_entries=None, flights_limit=None):
    """The `ctx` dict `companion.pages.history_page.render()` expects,
    mirroring `companion/app.py`'s own ctx keys exactly."""
    return {
        "state_dir": str(state_dir),
        "now": now or history_db.utc_now_iso(),
        "gallery_entries": gallery_entries or [],
        "flights_limit": flights_limit,
    }


def row_block(rendered, tag, group_index):
    """The `<tag ... data-filter-group="<group_index>">` element from a
    rendered Flights/History page, as a `companion_markup.Node` — the
    desktop `<tr>` when `tag="tr"`, the mobile `<li>` when `tag="li"` —
    or `None` if no such element exists. Structural (parsed DOM), never a
    hand-rolled regex over the rendered string.
    """
    from companion_markup import parse_html

    doc = parse_html(rendered)
    matches = doc.select('%s[data-filter-group="%d"]' % (tag, group_index))
    return matches[0] if matches else None
