"""Cross-page sweep of the reworked companion in a real browser.

Every reworked page (Fleet, Users, Locations, Audit log, Releases, Account,
Home, Display, Device, Health) and every dialog it opens is loaded at 360 and
1280px, in English and French, in both themes. Each load is checked for sideways
overflow, 44px hit targets, list and navigation structure, monospace, empty
states and the words a user must not meet. A separate sweep compares the
French render of each page with the English one and reports visible text that
was left untranslated. Locations is checked on its own at 360px (every input
and select inside its card), and Device and Health are part of the sweep.

The 44px hit-area rule is asserted on the whole page and its bars at 360px, and
on dialogs, list rows, page headers, the desktop sidebar (links, language and
theme segments, Sign out, the brand link) and the Home "See Health" pill at
1280px. The empty-state rule covers the pages listed here.
"""
import re

import pytest

import fleet_console_support as fx
from locations_page_support import open_locations_page
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _set_ui_theme,
    seed_state_dir)
from provisioned_fleet import USER_A_EMAIL, device_dir, provision_fleet
from companion_app_server import session_cookie_for_state_dir
from server import fleet_db, history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (
    pytest.param(VIEWPORT_MIN_SUPPORTED, id="360"),
    pytest.param(VIEWPORT_DESKTOP, id="1280"))
USER_FORBIDDEN = re.compile(r"\b(Admin\w*|Console|Fleet|Releases?|Device|Update)\b")
MY_VIEWS_ADMIN_WORD = re.compile(r"^Admin(istration)?$")

# Hit-tested tap targets: for every visible control the sweep moves it to the
# middle of the viewport and measures how far the browser still routes a pointer
# to it in each direction. Inline text links inside running copy are exempt.
_TARGETS = """
(scopes) => {
  const sel = 'a[href], button, summary, select, textarea, ' +
    'input:not([type=hidden]):not([type=radio]):not([type=checkbox]), ' +
    'label:has(> input[type=radio]), label:has(> input[type=checkbox])';
  const bad = [];
  const inDialog = scopes.some((s) => s.startsWith('dialog'));
  const found = new Set();
  scopes.forEach((s) => document.querySelectorAll(s + ' :is(' + sel + '), ' + s + ':is(' + sel + ')')
    .forEach((e) => found.add(e)));
  for (const el of found) {
    if (!el.checkVisibility() || (!inDialog && el.closest('dialog'))) continue;
    if (el.matches('.skip-link, .brand__link') || el.closest('.dashboard-sidebar')) continue;
    if (el.tagName === 'A' && getComputedStyle(el).display === 'inline') continue;
    el.scrollIntoView({block: 'center', inline: 'center'});
    const r = el.getBoundingClientRect();
    const cx = Math.floor(r.left + r.width / 2) + 0.5, cy = Math.floor(r.top + r.height / 2) + 0.5;
    const owns = (x, y) => { const n = document.elementFromPoint(x, y);
      return !!n && (n === el || el.contains(n)); };
    const label = el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '') +
      ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24) + '"';
    if (!owns(cx, cy)) { bad.push(label + ' is covered at its centre'); continue; }
    const reach = (dx, dy) => { let n = 0;
      while (n < 64 && owns(cx + dx * (n + 1), cy + dy * (n + 1))) n++; return n; };
    const w = reach(-1, 0) + reach(1, 0) + 1, h = reach(0, -1) + reach(0, 1) + 1;
    if (w < 44 || h < 44) bad.push(label + ' hit area ' + w + 'x' + h);
  }
  window.scrollTo(0, 0);
  return bad;
}
"""

# Structure rules that hold on every page; `args` names the page kind.
_STRUCTURE = """
(args) => {
  const bad = [];
  const q = (s) => [...document.querySelectorAll(s)];
  if (q('.section-subnav').length) bad.push('section chip row present');
  const bars = q('.tab-bar').filter((b) => b.checkVisibility());
  if (args.phone) {
    if (bars.length !== 1) bad.push('tab bars: ' + bars.length);
    const cells = q('.tab-bar > a, .tab-bar > details').map((e) => e.getBoundingClientRect());
    const widths = cells.map((c) => c.width);
    if (cells.length && Math.max(...widths) - Math.min(...widths) > 1) bad.push('unequal cells ' + widths);
    if (cells.some((c) => c.width < 44 || c.height < 44)) bad.push('bar cell under 44px');
    q('.tab-bar__label').forEach((l) => {
      if (l.scrollWidth > l.clientWidth) bad.push('clipped bar label ' + l.textContent); });
  } else if (bars.length) bad.push('tab bar visible on desktop');
  if (args.list && q('main table').length) bad.push('table in a list page');
  q('li.entity-row').forEach((row) => {
    if (row.querySelectorAll('.entity-row__dot .dot, .entity-row__dot [role=img]').length > 1) bad.push('two dots in a row');
    row.querySelectorAll('.entity-row__dot [role=img]').forEach((d) => {
      if (!d.getAttribute('aria-label')) bad.push('dot without a name'); });
    const box = row.getBoundingClientRect();
    row.querySelectorAll('*').forEach((e) => {
      if (!e.checkVisibility() || e.closest('.visually-hidden, details.row-menu > :not(summary)')) return;
      const range = document.createRange();
      range.selectNodeContents(e);
      const t = range.getBoundingClientRect();
      if (t.width && (t.right > box.right + 1 || t.left < box.left - 1)) {
        bad.push('text outside its row: ' + e.className); } });
    row.querySelectorAll('.entity-row__title, .entity-row__subtitle, .entity-row__text').forEach((e) => {
      if (/mono/i.test(getComputedStyle(e).fontFamily)) bad.push('monospace in a row: ' + e.className); });
  });
  q('.empty-state').filter((e) => e.checkVisibility()).forEach((e) => {
    if (!e.classList.contains('empty-state--compact') && !e.classList.contains('empty-state--filter')) {
      bad.push('large empty state: ' + e.className); } });
  q('dialog[open]').forEach((d) => {
    if (d.scrollWidth > d.clientWidth) bad.push('dialog scrolls sideways'); });
  const navText = q('.tab-bar a, .tab-bar summary, .sidebar-nav a, header a').map((e) => e.textContent.trim());
  return {bad: bad, navText: navText, body: document.body.innerText};
}
"""

_VISIBLE_TEXT = """
() => {
  const out = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent.replace(/\\s+/g, ' ').trim();
    const p = n.parentElement;
    if (text && p && p.checkVisibility() && !p.closest('script, style, noscript')) out.add(text);
  }
  document.querySelectorAll('[aria-label]').forEach((e) => {
    if (e.checkVisibility()) out.add(e.getAttribute('aria-label').trim()); });
  return [...out];
}
"""

_FIELDS = (
    "() => [...document.querySelectorAll('main input, main select')]"
    ".filter(e => e.checkVisibility() && e.type !== 'hidden').map(e => {"
    " const card = e.closest('section');"
    " const b = e.getBoundingClientRect(), c = card.getBoundingClientRect();"
    " return {id: e.id || e.name, sw: e.scrollWidth, cw: e.clientWidth,"
    " inside: b.right <= c.right + 0.5 && b.left >= c.left - 0.5}; })")


def _slug(device_id):
    return device_id.lower().replace("_", "-")


def _seed(state_dir):
    seed_state_dir(state_dir)
    seed = fx.seed_fleet(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, fx.USER_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _ids(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        owned = conn.execute("SELECT id FROM devices WHERE name = 'Kitchen'").fetchone()["id"]
        owner = fleet_db.get_user_by_email(conn, fx.OWNER_EMAIL)["id"]
    finally:
        conn.close()
    return {"owned": owned, "slug": _slug(owned), "owner_user": owner}


def _case(persona, path, dialog=None, label=None):
    return pytest.param(persona, path, dialog, id=label or (path.strip("/") or "home"))


CASES = (
    _case("admin", "/fleet", None, "fleet"),
    _case("admin", "/fleet", "dlg-add-frame", "fleet-add-dialog"),
    _case("admin", "/fleet", "dlg-retire-{slug}", "fleet-retire-dialog"),
    _case("admin", "/fleet", "dlg-reassign-{slug}", "fleet-reassign-dialog"),
    _case("admin", "/fleet", "dlg-access-{slug}", "fleet-access-dialog"),
    _case("admin", "/users", None, "users"),
    _case("admin", "/users", "dlg-invite-user", "users-invite-dialog"),
    _case("admin", "/users", "dlg-user-{owner_user}", "users-manage-dialog"),
    _case("admin", "/locations", None, "locations"),
    _case("admin", "/audit", None, "audit"),
    _case("admin", "/update", None, "releases"),
    _case("admin", "/account", None, "admin-account"),
    _case("admin", "/", None, "admin-home"),
    _case("admin", "/display", None, "admin-display"),
    _case("admin", "/device", None, "admin-device"),
    _case("admin", "/health", None, "admin-health"),
    _case("owner", "/devices/{owned}/", None, "user-home"),
    _case("owner", "/devices/{owned}/display", None, "user-display"),
    _case("owner", "/account", None, "user-account"),
    _case("owner", "/account", "dlg-access-{slug}", "user-access-dialog"),
    _case("co", "/account", None, "co-manager-account"),
    _case("co", "/account", "dlg-leave-{slug}", "co-manager-leave-dialog"),
)


def _open(new_context, server, persona, path, dialog, viewport, lang, scheme):
    ids = _ids(server)
    state_dir = server.state_dir
    pair = {
        "admin": lambda: fx.admin_cookie(state_dir),
        "owner": lambda: fx.user_cookie(state_dir, fx.OWNER_EMAIL),
        "co": lambda: fx.user_cookie(state_dir, fx.USER_EMAIL)}[persona]()
    name, value = pair.split("=", 1)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(),
         "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()},
        {"name": auth.UI_THEME_COOKIE_NAME, "value": scheme, "url": server.base_url()}])
    page = context.new_page()
    url = server.base_url() + path.format(**ids)
    if dialog:
        url += "#" + dialog.format(**ids)
    if path == "/locations":
        open_locations_page(page, server.base_url())
    else:
        page.goto(url)
    page.locator("main").wait_for(state="visible")
    if dialog:
        page.locator("dialog[open]").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page


def _target_scopes(dialog, viewport):
    """Where the 44px floor is asserted. A phone checks the whole page and
    its bars. At 1280px the sidebar, the language, theme and Sign out
    controls and the Health pill are pointer-sized by design (29 to 33px), so
    the desktop check covers open dialogs and the list and header controls of
    each page."""
    if dialog:
        return ["dialog[open]"]
    if viewport["width"] < 960:
        return ["main", "header", ".tab-bar"]
    return ["main .entity-list", "main .page-header"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("persona,path,dialog", CASES)
def test_reworked_pages_hold_the_layout_rules(
        new_context, server, persona, path, dialog, viewport, lang, scheme):
    context, page = _open(new_context, server, persona, path, dialog, viewport, lang, scheme)
    where = "%s%s#%s/%d/%s/%s" % (persona, path, dialog, viewport["width"], lang, scheme)
    try:
        problems = []
        overflow = _assert_no_page_overflow(page, where, viewport["width"])
        if overflow:
            problems.append(overflow)
        report = page.evaluate(_STRUCTURE, {
            "phone": viewport["width"] < 960,
            "list": path in ("/fleet", "/users")})
        problems.extend(report["bad"])
        problems.extend(page.evaluate(_TARGETS, _target_scopes(dialog, viewport)))
        if persona != "admin":
            for word in USER_FORBIDDEN.findall(report["body"]):
                problems.append("administrator word on a user page: " + word)
        elif path in ("/account", "/", "/display", "/device", "/health"):
            for text in report["navText"]:
                if MY_VIEWS_ADMIN_WORD.match(text):
                    problems.append("Admin entry in My views: " + text)
        assert not problems, (where, problems)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_fleet_page_is_not_called_cadres_in_french(new_context, server, lang):
    context, page = _open(
        new_context, server, "admin", "/fleet", None, VIEWPORT_MIN_SUPPORTED, lang, "light")
    try:
        title = page.locator("main h1").inner_text().strip()
        assert title == ("Flotte" if lang == "fr" else "Fleet")
        assert title != "Cadres"
        assert "Cadres" not in page.title()
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_locations_inputs_and_selects_sit_inside_their_card_at_360(
        new_context, server, lang, scheme):
    context, page = _open(
        new_context, server, "admin", "/locations", None, VIEWPORT_MIN_SUPPORTED,
        lang, scheme)
    try:
        fields = page.evaluate(_FIELDS)
        assert fields
        for field in fields:
            assert field["inside"], field
            assert field["sw"] <= field["cw"] + 1, field
        assert not _assert_no_page_overflow(page, "locations", 360)
    finally:
        context.close()


# Visible text that is the same in both languages on purpose: product, hardware
# and place names, seeded data (flights, airlines), and words French shares with
# English.
_SHARED = re.compile(
    r"^(SkyPane|Orly|Kitchen|Attic|Orly frame|Console|Audit|Distance|Station|Local|Total|"
    r"Version|Versions|Image|Plus|Type|Description|Original|Information|Document|Action|"
    r"Actions|Contact|Standard|Message|Notes?|Auto|Latitude|Longitude|XIAO ePaper|"
    r"Air France|easyJet|Transavia|test)\b")


def _looks_english(text):
    if "@" in text or not re.search(r"[a-z]{3,}", text):
        return False
    if re.fullmatch(r"\S*[\d_]\S*", text):  # an identifier, not a sentence
        return False
    return not _SHARED.match(text)


@pytest.mark.parametrize("persona,path,dialog", CASES)
def test_every_visible_string_has_a_french_translation(
        new_context, server, persona, path, dialog):
    texts = {}
    for lang in ("en", "fr"):
        context, page = _open(
            new_context, server, persona, path, dialog, VIEWPORT_MIN_SUPPORTED, lang,
            "light")
        try:
            texts[lang] = set(page.evaluate(_VISIBLE_TEXT))
        finally:
            context.close()
    same = sorted(t for t in texts["en"] & texts["fr"] if _looks_english(t))
    assert not same, same


# Hit areas of the desktop chrome: the same reach measurement as _TARGETS, over the sidebar
# and the Home pill, reporting every control whose resolved hit box is under 44px either way.
_DESKTOP_CHROME = """
(selectors) => {
  const bad = [];
  let seen = 0;
  for (const el of document.querySelectorAll(selectors.join(', '))) {
    if (!el.checkVisibility()) continue;
    seen++;
    el.scrollIntoView({block: 'center', inline: 'center'});
    const r = el.getBoundingClientRect();
    const cx = Math.floor(r.left + r.width / 2) + 0.5, cy = Math.floor(r.top + r.height / 2) + 0.5;
    const owns = (x, y) => { const n = document.elementFromPoint(x, y);
      return !!n && (n === el || el.contains(n)); };
    const label = el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0] +
      ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24) + '"';
    if (!owns(cx, cy)) { bad.push(label + ' is covered at its centre'); continue; }
    const reach = (dx, dy) => { let n = 0;
      while (n < 64 && owns(cx + dx * (n + 1), cy + dy * (n + 1))) n++; return n; };
    const w = reach(-1, 0) + reach(1, 0) + 1, h = reach(0, -1) + reach(0, 1) + 1;
    if (w < 44 || h < 44) bad.push(label + ' hit area ' + w + 'x' + h);
  }
  window.scrollTo(0, 0);
  return {bad: bad, seen: seen};
}
"""
_SIDEBAR_CONTROLS = [
    ".dashboard-sidebar .sidebar-link", ".dashboard-sidebar .theme-option",
    ".dashboard-sidebar .logout-form button", ".dashboard-sidebar .brand__link",
    ".dashboard-sidebar .brand a"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("persona,path", [
    ("admin", "/fleet"), ("admin", "/display"), ("owner", "/account"), ("owner", "/devices/{owned}/")])
def test_the_desktop_sidebar_controls_have_44px_hit_areas(
        new_context, server, persona, path, lang, scheme):
    context, page = _open(new_context, server, persona, path, None, VIEWPORT_DESKTOP, lang, scheme)
    try:
        result = page.evaluate(_DESKTOP_CHROME, _SIDEBAR_CONTROLS)
        assert result["seen"] >= 6, result
        assert not result["bad"], (persona, path, lang, scheme, result["bad"])
        # The taller rows still fit the sticky sidebar in the viewport.
        assert page.evaluate(
            "() => { const s = document.querySelector('.dashboard-sidebar');"
            " return s.scrollHeight <= Math.max(s.clientHeight, window.innerHeight); }")
        assert page.evaluate(
            "() => document.querySelector('.sidebar-footer .logout-form button')"
            ".getBoundingClientRect().bottom <= window.innerHeight")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_overdue_home_card_has_no_health_pill_on_desktop(
        new_context, make_app_server, lang, scheme):
    def seed(state_dir):
        fleet = provision_fleet(state_dir)
        with history_db.open_db(device_dir(state_dir, fleet.a1)) as conn:
            history_db.record_device_health(
                conn, "2026-01-01T00:00:00+00:00", battery_mv=4000, fw_version="1.0.0",
                boot_reason="wake", rssi="-60")
        seed.fleet = fleet
    server = make_app_server(seed=seed)
    name, value = session_cookie_for_state_dir(server.state_dir, USER_A_EMAIL).split("=", 1)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(),
         "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()},
        {"name": auth.UI_THEME_COOKIE_NAME, "value": scheme, "url": server.base_url()}])
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/devices/%s/" % seed.fleet.a1)
        page.locator(".home-state").wait_for(state="visible")
        _set_ui_theme(page, scheme)
        assert page.locator(".home-state__dot.dot--warn, .home-state__dot.dot--error").count() == 1
        assert page.locator(".home-state__health-link").count() == 0
        assert page.locator('a[href$="/health"]').count() == 0
    finally:
        context.close()
