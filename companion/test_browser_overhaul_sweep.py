"""Cross-page sweep of the reworked companion in a real browser.

Every reworked page (Fleet, Users, Audit log, Releases, Account, Home,
Location and detection, Personalisation, Airline collection, and the Console
Health, Device and Airline editor pages) and every dialog it opens (the Fleet
dialogs, the frame sheet, the quiet-hours dialog, the two confirm dialogs for a
special look and a manual resolution) is loaded at 360 and 1280px, in English
and French, in both themes. Each load is checked for sideways overflow, 44px
hit targets, list and navigation structure, monospace, empty states and the
words a user must not meet. A separate sweep compares the French render of each
page with the English one and reports visible text that was left untranslated.
The Home notification for an amber or red dot is swept for an owner, a
co-manager and an administrator in every state it covers, and an
administrator's personal pages are compared with a user's. The map's tile host
and the place search host are answered by the test; nothing leaves the machine.

The 44px hit-area rule is asserted on the whole page and its bars at 360px,
and on the page content, dialogs, list rows and page headers at 1280px (the
desktop sidebar has its own test). The empty-state rule covers the pages
listed here.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone

import pytest

import fleet_console_support as fx
from locations_page_support import open_locations_page
from place_map_support import Hosts
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _set_ui_theme,
    seed_state_dir)
from provisioned_fleet import (
    ADMIN_EMAIL, USER_A_EMAIL, USER_B_EMAIL, device_dir, provision_fleet)
from companion_app_server import session_cookie_for_state_dir
from server import fleet_db, hardware, history_db
from server.plane import colour_rules, manual_resolutions

pytestmark = pytest.mark.browser

VIEWPORTS = (
    pytest.param(VIEWPORT_MIN_SUPPORTED, id="360"),
    pytest.param(VIEWPORT_DESKTOP, id="1280"))
USER_FORBIDDEN = re.compile(
    r"\b(Admin\w*|Console|Fleet|Releases?|Device|Update(?! overdue)|Health|Airline editor)\b")
# Words an administrator's personal pages must not carry either, once the space
# switch and the foreign-frame notice are set aside.
PERSONAL_FORBIDDEN = re.compile(
    r"\b(Admin\w*|Console|Fleet|Releases?|Device|Update(?! overdue)|Health|Airline editor)\b")
RULE = ("prefix", "TVF")

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
  q('li.entity-row, li.place-airport, li.collection-item, .rule-row, .manual-resolution-row').forEach((row) => {
    if (row.querySelectorAll('.entity-row__dot .dot, .entity-row__dot [role=img]').length > 1) bad.push('two dots in a row');
    row.querySelectorAll('.entity-row__dot [role=img]').forEach((d) => {
      if (!d.getAttribute('aria-label')) bad.push('dot without a name'); });
    const box = row.getBoundingClientRect();
    row.querySelectorAll('*').forEach((e) => {
      if (!e.checkVisibility() || e.closest('dialog, .visually-hidden, details.row-menu > :not(summary)')) return;
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

PERSONAL_PAGES = ("/", "/flights", "/detection", "/display", "/airlines")
PERSONAL_ADMIN_PATHS = PERSONAL_PAGES

# The visible text of the page with the space switch and the foreign-frame
# notice set aside: the two things an administrator's personal page may add.
_PERSONAL_BODY = """
() => {
  const hidden = [...document.querySelectorAll('.space-switch, .space-strip, .frame-notice')];
  const was = hidden.map((e) => e.style.display);
  hidden.forEach((e) => { e.style.display = 'none'; });
  const text = document.body.innerText;
  hidden.forEach((e, i) => { e.style.display = was[i]; });
  return text;
}
"""

# Airline and airport names are catalogue data, spelled the same in both languages.
_VISIBLE_TEXT = """
() => {
  const CATALOGUE = 'script, style, noscript, .collection-card__name, .place-airport__name, .place-airport__meta, .airline-row__name';
  const out = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent.replace(/\\s+/g, ' ').trim();
    const p = n.parentElement;
    if (text && p && p.checkVisibility() && !p.closest(CATALOGUE)) out.add(text);
  }
  document.querySelectorAll('[aria-label]').forEach((e) => {
    if (e.checkVisibility()) out.add(e.getAttribute('aria-label').trim()); });
  return [...out];
}
"""



def _slug(device_id):
    return device_id.lower().replace("_", "-")


def _seed(state_dir):
    seed_state_dir(state_dir)
    seed = fx.seed_fleet(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, fx.USER_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY,
            seed.owner_id, name="Attic office", state_path="auto")
    finally:
        conn.close()
    assert colour_rules.add_rule(state_dir, *RULE, "white") == colour_rules.ADD_OK_NEW
    manual_resolutions.add_entry(state_dir, "ZZZ", "Zed Air")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _digest(text):
    """The short hash the pages put in a confirm dialog's id, so stored text never reaches it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _ids(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        owned = conn.execute("SELECT id FROM devices WHERE name = 'Kitchen'").fetchone()["id"]
        owner = fleet_db.get_user_by_email(conn, fx.OWNER_EMAIL)["id"]
    finally:
        conn.close()
    return {
        "owned": owned, "slug": _slug(owned), "owner_user": owner,
        "rule_dialog": "remove-look-%s-%s" % (RULE[0], _digest(RULE[1])),
        "resolution_dialog": "delete-resolution-" + _digest("ZZZ")}


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
    _case("admin", "/flights", None, "admin-flight-history"),
    _case("owner", "/devices/{owned}/flights", None, "user-flight-history"),
    _case("admin", "/detection", None, "admin-location"),
    _case("admin", "/airlines", None, "admin-collection"),
    _case("admin", "/airlines/manage", None, "admin-airline-editor"),
    _case("admin", "/display", "{rule_dialog}", "remove-special-look-dialog"),
    _case("admin", "/airlines/manage", "{resolution_dialog}", "delete-resolution-dialog"),
    _case("admin", "/", "dlg-quiet-hours", "admin-quiet-hours-dialog"),
    _case("owner", "/devices/{owned}/", None, "user-home"),
    _case("owner", "/devices/{owned}/", "dlg-frames", "frame-sheet"),
    _case("owner", "/devices/{owned}/", "dlg-quiet-hours", "quiet-hours-dialog"),
    _case("owner", "/devices/{owned}/display", None, "user-display"),
    _case("owner", "/devices/{owned}/detection", None, "user-location"),
    _case("owner", "/devices/{owned}/airlines", None, "user-collection"),
    _case("co", "/devices/{owned}/detection", None, "co-manager-location"),
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
    Hosts(context)
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
    controls are pointer-sized by design (29 to 33px) and have their own test,
    so the desktop check covers open dialogs and the page content."""
    if dialog:
        return ["dialog[open]"]
    if viewport["width"] < 960:
        return ["main", "header", ".tab-bar"]
    return ["main"]


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
        elif path in PERSONAL_ADMIN_PATHS:
            for word in PERSONAL_FORBIDDEN.findall(page.evaluate(_PERSONAL_BODY)):
                problems.append("console word on a personal page: " + word)
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


# Visible text that is the same in both languages on purpose: product, hardware
# and place names, seeded data (flights, airlines), and words French shares with
# English. The frame's own heading ("Watching Runway 3") and an airport's name and codes are
# data the frame and the catalogue spell one way, and the seeded history's pass state
# ("confirmed", a value the detector never writes).
_SHARED = re.compile(
    r"^(SkyPane|Orly|Kitchen|Attic|Orly frame|Console|Audit|Distance|Station|Local|Total|"
    r"Version|Versions|Image|Plus|Type|Description|Original|Information|Document|Action|"
    r"Actions|Style|Contact|Standard|Message|Notes?|Auto|Latitude|Longitude|XIAO ePaper|"
    r"Air France|easyJet|Transavia|Ryanair|Confirmed|test)\b|^[A-Z0-9]{4} · |^(Paris-Orly Airport|Watching Runway)")


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


# --- Home notification for an amber or red dot ------------------------------

NOTICE = ".home-facts .home-notice"
FINITE_ANIMATIONS_DONE = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => (a.effect && a.effect.getComputedTiming().iterations === Infinity)"
    " || a.playState !== 'running')")

_NOTICE_FITS = """
(selector) => {
  const doc = document.documentElement;
  const notice = document.querySelector(selector);
  const box = notice.getBoundingClientRect();
  const clipped = [...notice.querySelectorAll('*')].filter((e) =>
    e.checkVisibility() && !e.closest('.visually-hidden')
    && getComputedStyle(e).display !== 'inline'
    && getComputedStyle(e).overflow !== 'visible' && e.scrollWidth > e.clientWidth + 1);
  return {page: doc.scrollWidth - doc.clientWidth, right: box.right,
          left: box.left, viewport: doc.clientWidth, height: box.height,
          clipped: clipped.map((e) => e.className.toString())};
}
"""


def _record_check_in(directory, minutes_ago, millivolts=4000):
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with history_db.open_db(directory) as conn:
        history_db.record_device_health(
            conn, stamp.isoformat(), battery_mv=millivolts, fw_version="1.0.0",
            boot_reason="wake", rssi="-60")


def _seed_notice_fleet(state_dir, state, administrator):
    """A provisioned fleet whose first frame is in `state` (not_seen, low_battery or
    no_contact) or whose live frame is overdue, user B co-managing the first frame; with
    `administrator` false every administrator is disabled, so no contact address exists."""
    fleet = provision_fleet(state_dir)
    directory = device_dir(state_dir, fleet.a1)
    if state == "low_battery":
        _record_check_in(directory, 0, millivolts=3381)
    elif state == "no_contact":
        _record_check_in(directory, 320)
    elif state == "overdue":
        _record_check_in(state_dir, 50)
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.add_co_manager(conn, fleet.a1, fleet.b_id, fleet.a_id)
        if not administrator:
            fleet_db.set_user_disabled(conn, ADMIN_EMAIL, True)
    finally:
        conn.close()
    return fleet


# state, an administrator exists, the people who see it. An overdue frame is the live
# frame (a frame without a live feed that is overdue already reads as no contact).
NOTICE_STATES = (
    ("not_seen", True, ("owner", "co", "admin")),
    ("low_battery", True, ("owner", "co", "admin")),
    ("no_contact", True, ("owner", "co", "admin")),
    ("no_contact", False, ("owner", "co")),
    ("overdue", True, ("admin",)),
)
NOTICE_CASES = [
    pytest.param(state, with_admin, who, id="%s%s-%s" % (
        state, "" if with_admin else "-no-admin", who))
    for state, with_admin, people in NOTICE_STATES for who in people]
# Figures the notification must carry for each state, by the English wording.
NOTICE_FIGURES = {
    "not_seen": (),
    "low_battery": (r"Frame battery at \d+%",),
    "no_contact": (r"Last contact \d+h ago", "Wi-Fi, an internet or a server problem"),
    "overdue": (r"Last check-in \d+",),
}
NOTICE_PEOPLE = {
    "owner": USER_A_EMAIL, "co": USER_B_EMAIL, "admin": ADMIN_EMAIL}


@pytest.fixture(scope="module")
def notice_servers(module_app_server_factory):
    servers = {}
    for state, with_admin, _ in NOTICE_STATES:
        held = {}

        def seed(state_dir, state=state, with_admin=with_admin, held=held):
            held["fleet"] = _seed_notice_fleet(state_dir, state, with_admin)

        servers[(state, with_admin)] = (module_app_server_factory(seed=seed), held)
    return servers


def _open_notice(new_context, notice_servers, state, with_admin, who, viewport, lang, scheme):
    server, held = notice_servers[(state, with_admin)]
    base = server.base_url()
    name, value = session_cookie_for_state_dir(
        server.state_dir, NOTICE_PEOPLE[who]).split("=", 1)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base},
        {"name": auth.UI_THEME_COOKIE_NAME, "value": scheme, "url": base}])
    page = context.new_page()
    page.goto(base + ("/" if state == "overdue" else "/devices/%s/" % held["fleet"].a1))
    page.locator(NOTICE).wait_for(state="visible")
    _set_ui_theme(page, scheme)
    page.wait_for_function(FINITE_ANIMATIONS_DONE, timeout=10000)
    return context, page


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("state,with_admin,who", NOTICE_CASES)
def test_the_home_notification_holds_the_layout_rules(
        new_context, notice_servers, state, with_admin, who, viewport, lang, scheme):
    context, page = _open_notice(
        new_context, notice_servers, state, with_admin, who, viewport, lang, scheme)
    where = "%s/%s/%s/%d/%s/%s" % (state, with_admin, who, viewport["width"], lang, scheme)
    try:
        problems = []
        overflow = _assert_no_page_overflow(page, where, viewport["width"])
        if overflow:
            problems.append(overflow)
        tops = page.evaluate(
            "(n) => ['h1.page-title', n, '.home-state'].map("
            "(s) => document.querySelector(s).getBoundingClientRect().top)", NOTICE)
        if not tops[0] < tops[1] < tops[2]:
            problems.append("order is not title, notification, state card: %r" % (tops,))
        fit = page.evaluate(_NOTICE_FITS, NOTICE)
        if fit["page"] > 0 or fit["clipped"]:
            problems.append("notification overflows or clips text: %r" % (fit,))
        if fit["left"] < -0.5 or fit["right"] > fit["viewport"] + 0.5:
            problems.append("notification outside the viewport: %r" % (fit,))
        problems.extend(page.evaluate(_TARGETS, [NOTICE]))
        link = page.locator(NOTICE + " a")
        if with_admin:
            if link.count() != 1 or not link.get_attribute("href").startswith("mailto:"):
                problems.append("the contact link is not one mailto anchor")
        elif link.count():
            problems.append("a contact link without an administrator")
        if lang == "en":
            text = page.inner_text(NOTICE)
            for word in PERSONAL_FORBIDDEN.findall(text):
                problems.append("console word in the notification: " + word)
            for figure in NOTICE_FIGURES[state]:
                if not re.search(figure, text):
                    problems.append("missing figure: " + figure)
            if state != "no_contact" and "Wi-Fi, an internet" in text:
                problems.append("the no-contact sentence outside no contact")
            if not with_admin and "@" in text:
                problems.append("an address in a notification without a contact")
        assert not problems, (where, problems)
    finally:
        context.close()


@pytest.mark.parametrize("state,with_admin,who", NOTICE_CASES)
def test_the_home_notification_has_a_french_translation(
        new_context, notice_servers, state, with_admin, who):
    texts = {}
    for lang in ("en", "fr"):
        context, page = _open_notice(
            new_context, notice_servers, state, with_admin, who, VIEWPORT_MIN_SUPPORTED, lang,
            "light")
        try:
            texts[lang] = set(page.evaluate(_VISIBLE_TEXT))
        finally:
            context.close()
    same = sorted(t for t in texts["en"] & texts["fr"] if _looks_english(t))
    assert not same, same


# --- An administrator's personal pages equal a user's ------------------------

# What a person can find on a page, set apart from the data of the frame: headings, the
# navigation entries (outside the space switch), and the names of the controls. The frame
# chip and its sheet name frames, which differ with the person, and are left out.
_PAGE_SHAPE = """
() => {
  const skip = '.space-strip, .space-switch, .mobile-nav__link--space, .frame-notice,'
    + ' .frame-chip, .frame-sheet, script, style, template';
  const keep = (e) => !e.closest(skip);
  const q = (s) => [...document.querySelectorAll(s)].filter(keep);
  return {
    headings: q('main h1, main h2, main h3').map((e) => e.textContent.trim().replace(/\\s+/g, ' ')),
    nav: q('.tab-bar a, .tab-bar summary, .dashboard-sidebar a, header a').map(
      (e) => e.textContent.trim().replace(/\\s+/g, ' ') + ' ' + (e.getAttribute('href') || '')),
    controls: q('main input:not([type=hidden]), main select, main textarea, main button').map(
      (e) => e.tagName.toLowerCase() + ':' + (e.name || e.id || e.textContent.trim().slice(0, 30))),
    notice: document.querySelectorAll('.frame-notice').length,
    switchControls: document.querySelectorAll('.space-switch').length,
  };
}
"""


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("page_path", PERSONAL_PAGES)
def test_an_administrators_personal_page_equals_a_users(
        new_context, server, page_path, viewport):
    path = "/devices/{owned}" + (page_path if page_path != "/" else "/")
    shapes = {}
    for persona in ("owner", "admin"):
        context, page = _open(
            new_context, server, persona, path, None, viewport, "en", "light")
        try:
            page.wait_for_function(FINITE_ANIMATIONS_DONE, timeout=10000)
            shapes[persona] = page.evaluate(_PAGE_SHAPE)
        finally:
            context.close()
    user, admin = shapes["owner"], shapes["admin"]
    assert user["headings"] and user["nav"]
    for part in ("headings", "nav", "controls"):
        assert admin[part] == user[part], (page_path, viewport["width"], part)
    # The switch and the foreign-frame notice are the whole difference.
    assert user["switchControls"] == 0 and user["notice"] == 0
    assert admin["switchControls"] >= 1 and admin["notice"] == 1
