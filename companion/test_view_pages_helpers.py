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
import os
import re

from server import history_db
from server.plane import render as panel_render

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


def detail_row_block(rendered, index):
    """The inner markup slice of the sibling detail `<tr>` for row
    `index` (a raw string, not a `Node`) — several 33-06+ checks need a
    plain substring/`in` test over the row's own markup (e.g. "this
    value appears in the detail row and NOT in the summary row"), which
    a parsed `Node` has no equivalent for. `None` if no such row exists.
    This still operates on RENDERED text (a production function's
    return value), never on a file opened from disk.
    """
    match = re.search(
        r'<tr class="flight-detail-row" id="flight-detail-%d"[^>]*>(.*?)</tr>' % index,
        rendered, re.S)
    return match.group(1) if match else None


def table_markup(rendered):
    """The `<table>...</table>` slice of a rendered Flights page, or
    `None`. Several checks are about the TABLE specifically and would
    false-positive against the mobile card list rendered beside it.
    """
    match = re.search(r"<table[^>]*>.*?</table>", rendered, re.S)
    return match.group(0) if match else None


def seed_gallery(state_dir, names):
    """Writes a real, tiny PNG for each of `names` into `state_dir`'s
    `gallery/` subdirectory (mirrors the legacy harness's own
    `_seed_gallery()`/`_write_gallery_png()` pair)."""
    from PIL import Image

    gallery_dir = os.path.join(str(state_dir), "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    for name in names:
        Image.new("RGB", (4, 4), color=(200, 200, 200)).save(
            os.path.join(gallery_dir, name), format="PNG")


def seed_unresolved_prefixes(state_dir, registry):
    """The one sanctioned write path for a real `poll_state.json`'s
    `unresolved_prefixes` dict, never a hand-written JSON literal —
    mirrors `companion/test_status_pages.py`'s own helper of the same
    name."""
    import server.poll_loop as poll_loop

    poll_loop.save_poll_state(str(state_dir), {"unresolved_prefixes": registry})


def write_panel_file(state_dir):
    """A real, production-produced panel.bin — the same bytes
    `server.poll_loop.write_panel_atomic()` would write."""
    os.makedirs(str(state_dir), exist_ok=True)
    packed = panel_render.render_panel(None, "empty")
    with open(os.path.join(str(state_dir), "panel.bin"), "wb") as fh:
        fh.write(packed)


def strip_js_line_and_block_comments(js):
    """Strips `//` line comments and `/* */` block comments from `js`
    WITHOUT touching string/template literals — unlike
    `companion_markup.strip_js_comments_and_strings()`, which a check
    asserting on the literal content of a string (e.g. `image.src =
    ""`) cannot use, since that would also erase the empty-string
    literal the check is looking for. Operates on served JS text
    (fetched over HTTP), never a file opened from disk.
    """
    without_block = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)
