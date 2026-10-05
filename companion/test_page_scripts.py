"""Per-page script coverage: every authenticated page loads only the shell
scripts its own hooks need, with no build step.

Behaviour asserted against a REAL running companion/app.py, never against
source text: `layout.page_shell(scripts=...)`'s emitted `<script src>` set,
parsed from served HTML via `companion_markup.parse_html`. The hook -> script
map below (`HOOKS`) is the plan's own selector list, restated here as
selectors paired with `layout.*_SCRIPT_SRC` constants - never read from a
served or on-disk JS file (companion/test_suite_guards.py G2/G11).
"""
import pytest

import companion.app as app
from companion import layout
from companion.pages import health_page
from companion.test_browser_ux_helpers import seed_state_dir
from companion_app_server import get, login
from companion_markup import parse_html
from server.plane import calendar_rules

# Selector -> the one script whose own guard clause is keyed on it.
HOOKS = (
    ("#site-nav-toggle", layout.NAV_DROPDOWN_SCRIPT_SRC),
    ("form[data-dirty-form]", layout.DIRTY_STATE_SCRIPT_SRC),
    ("[data-filter-input]", layout.LIST_FILTER_SCRIPT_SRC),
    ("[data-copy-value]", layout.COPY_BUTTON_SCRIPT_SRC),
    ("[data-loaded-at]", layout.FRESHNESS_SCRIPT_SRC),
    ("#panel-lookup-dialog", layout.PANEL_LOOKUP_SCRIPT_SRC),
    (".toast-region--flash", layout.FLASH_CLEANUP_SCRIPT_SRC),
    ("[data-toast]", layout.TOAST_SCRIPT_SRC),
    ("#poll-trigger-btn", layout.POLL_COOLDOWN_SCRIPT_SRC),
    ("form[data-confirm]", layout.CONFIRM_SUBMIT_SCRIPT_SRC),
    (".theme-live-preview__image", layout.THEME_PREVIEW_SCRIPT_SRC),
    ("form", layout.SUBMIT_GUARD_SCRIPT_SRC),
    ("time[data-relative]", layout.RELATIVE_TIME_SCRIPT_SRC),
    ("form[data-quick-switch]", layout.QUICK_SWITCH_SCRIPT_SRC),
    ("[data-value-control]", layout.VALUE_CONTROLS_SCRIPT_SRC),
    ("[data-calendar-sheet]", layout.CALENDAR_SHEET_SCRIPT_SRC),
)

# A route's calendar-feed secret, saved directly (no network fetch - see
# save_calendar_url()'s own contract) so "calendar connected" is one of the
# states every per-route tuple must cover.
_SEEDED_CALENDAR_URL = "https://calendar.example/feed.ics?token=PAGESCRIPTSTEST"


def _seed_empty(state_dir):
    """A freshly-created, otherwise untouched state dir - the low end of
    the state range every per-route script tuple must still cover.
    """


def _seed_full(state_dir):
    """History, an unresolved-prefix registry, colour rules, a manual
    resolution, gallery renders (test_browser_ux_helpers.seed_state_dir),
    plus a connected calendar - the high end of the state range.
    """
    seed_state_dir(state_dir)
    assert calendar_rules.save_calendar_url(state_dir, _SEEDED_CALENDAR_URL), (
        "seeding a calendar URL for the 'seeded' state failed")


# name -> seeding function, one real AppServer per name (module-scoped: GET
# is read-only, so every parametrized case below shares these two servers).
_SERVER_SEEDS = (("empty", _seed_empty), ("seeded", _seed_full))

# (server name, extra query string) - the three states the plan's own
# behaviour list names: an empty state dir, a fully-seeded one, and a flash
# banner riding a query string on top of the empty one.
CASES = (
    ("empty", ""),
    ("seeded", ""),
    ("empty", "?flash=%s" % app.FLASH_KEY_SAVED),
)
CASE_IDS = ("empty", "seeded", "flash")

NAV_ROUTES = tuple(route for route, _label in layout.NAV_TABS)


@pytest.fixture(scope="module")
def servers(module_app_server_factory):
    return {name: module_app_server_factory(seed=seed) for name, seed in _SERVER_SEEDS}


def _page_body(servers, server_name, route, query=""):
    server = servers[server_name]
    session = login(server)
    status, _headers, body = get(server, route + query, cookie=session)
    assert status == 200, (
        "expected 200 from %s%s on the %r server, got %d"
        % (route, query, server_name, status))
    return body.decode("utf-8")


def _script_srcs(doc):
    return [node.attrs.get("src") for node in doc.select("script[src]")]


# ==========================================================================
# Hook coverage: every selector that actually matches on a rendered page has
# its script among that page's script[src] tags.
# ==========================================================================


@pytest.mark.parametrize("server_name,query", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("route", NAV_ROUTES)
def test_every_present_hook_has_its_script(servers, route, server_name, query):
    body = _page_body(servers, server_name, route, query)
    doc = parse_html(body)
    srcs = set(_script_srcs(doc))
    for selector, script_src in HOOKS:
        matched = doc.select(selector)
        if not matched:
            continue
        assert script_src in srcs, (
            "%s (%s state, query=%r): %d element(s) matched %r but %r is "
            "not among this page's script[src] tags %r"
            % (route, server_name, query, len(matched), selector, script_src,
               sorted(srcs)))


# ==========================================================================
# Exact set: the shell's own script srcs (battery-trend.js excluded - Health
# emits it inside its body, not through the shell) equal
# GLOBAL_PAGE_SCRIPTS | _PAGE_SCRIPTS[route], no repeats, in
# SHELL_SCRIPT_ORDER's relative order, and fewer than the pre-per-page-scripts
# baseline of 15.
# ==========================================================================


@pytest.mark.parametrize("server_name,query", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("route", NAV_ROUTES)
def test_shell_script_set_matches_global_and_route_tuple(servers, route, server_name, query):
    body = _page_body(servers, server_name, route, query)
    doc = parse_html(body)
    all_srcs = _script_srcs(doc)
    shell_srcs = [s for s in all_srcs if s != health_page.BATTERY_TREND_SCRIPT_SRC]

    assert len(shell_srcs) == len(set(shell_srcs)), (
        "%s (%s state, query=%r): a shell script src repeats: %r"
        % (route, server_name, query, shell_srcs))

    expected = set(layout.GLOBAL_PAGE_SCRIPTS) | set(app._PAGE_SCRIPTS[route])
    assert set(shell_srcs) == expected, (
        "%s (%s state, query=%r): shell script set %r does not equal "
        "GLOBAL_PAGE_SCRIPTS | _PAGE_SCRIPTS[route] %r"
        % (route, server_name, query, sorted(set(shell_srcs)), sorted(expected)))

    assert len(shell_srcs) < 15, (
        "%s (%s state, query=%r): still serves %d shell script tags, no "
        "fewer than the pre-per-page-scripts baseline of 15"
        % (route, server_name, query, len(shell_srcs)))

    order_positions = [layout.SHELL_SCRIPT_ORDER.index(s) for s in shell_srcs]
    assert order_positions == sorted(order_positions), (
        "%s (%s state, query=%r): shell scripts %r are not emitted in "
        "SHELL_SCRIPT_ORDER's relative order"
        % (route, server_name, query, shell_srcs))


# ==========================================================================
# A route with no declared tuple fails, naming the route.
# ==========================================================================


def test_every_nav_tab_route_has_a_page_scripts_tuple():
    missing = [route for route in NAV_ROUTES if route not in app._PAGE_SCRIPTS]
    assert not missing, (
        "layout.NAV_TABS route(s) %r have no app._PAGE_SCRIPTS entry - a "
        "tab landing without one would silently lose its scripts" % (missing,))


# ==========================================================================
# 404/login carry their own fixed sets, never a tab's.
# ==========================================================================


def test_authenticated_404_carries_exactly_the_global_set(servers):
    server = servers["empty"]
    session = login(server)
    status, _headers, body = get(server, "/no-such-page", cookie=session)
    assert status == 404, "expected 404 from /no-such-page, got %d" % status
    doc = parse_html(body.decode("utf-8"))
    srcs = _script_srcs(doc)
    assert len(srcs) == len(set(srcs)), "404 page repeats a script src: %r" % (srcs,)
    assert set(srcs) == set(layout.GLOBAL_PAGE_SCRIPTS), (
        "expected the authenticated 404 page to carry exactly "
        "GLOBAL_PAGE_SCRIPTS, got %r" % (sorted(set(srcs)),))


def test_login_page_carries_exactly_login_card_js(servers):
    server = servers["empty"]
    status, _headers, body = get(server, "/login")
    assert status == 200, "expected 200 from /login, got %d" % status
    doc = parse_html(body.decode("utf-8"))
    srcs = _script_srcs(doc)
    assert srcs == [layout.LOGIN_CARD_SCRIPT_SRC], (
        "expected /login to carry exactly [LOGIN_CARD_SCRIPT_SRC], got %r" % (srcs,))
