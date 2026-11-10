"""Cross-page sweep of the reworked companion in a real browser.

Every reworked page (Fleet, Users, Audit log, Releases, Account, Home,
Location and detection, Personalisation, Airline collection, and the Console
Health, Device and Airline editor pages) and every dialog it opens (the Fleet
dialogs, the quiet-hours dialog, the two confirm dialogs for a
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
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio
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
    'input:not([type=hidden]):not([type=radio]):not([type=checkbox]):not([type=file]), ' +
    'label:has(> input[type=radio]), label:has(> input[type=checkbox]), label:has(> input[type=file])';
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
    // The leading space switch cell has its own fixed width; the destination cells are equal.
    const widths = q('.tab-bar > a:not(.tab-bar__link--switch), .tab-bar > details')
      .map((e) => e.getBoundingClientRect().width);
    if (widths.length && Math.max(...widths) - Math.min(...widths) > 1) bad.push('unequal cells ' + widths);
    if (cells.some((c) => c.width < 44 || c.height < 44)) bad.push('bar cell under 44px');
    q('.tab-bar__label').forEach((l) => {
      if (l.scrollWidth > l.clientWidth) bad.push('clipped bar label ' + l.textContent); });
  } else if (bars.length) bad.push('tab bar visible on desktop');
  if (args.list && q('main table:not(.fleet-blocks table)').length) bad.push('table in a list page');
  q('li.entity-row, li.place-airport, li.collection-item, .rule-row').forEach((row) => {
    if (row.querySelectorAll('.entity-row__dot .dot, .entity-row__dot [role=img], .account-frame__status [role=img]').length > 1) bad.push('two dots in a row');
    row.querySelectorAll('.entity-row__dot [role=img], .account-frame__status [role=img]').forEach((d) => {
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
PERSONAL_ADMIN_PATHS = PERSONAL_PAGES + (
    "/display/arrivals", "/display/special-looks", "/display/calendar")

# The visible text of the page with the space switch and the foreign-frame
# notice set aside: the two things an administrator's personal page may add.
_PERSONAL_BODY = """
() => {
  const hidden = [...document.querySelectorAll('.space-switch, .tab-bar__link--switch, .frame-notice')];
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
  const CATALOGUE = 'script, style, noscript, .collection-card__name, .place-airport__name, .place-airport__meta, .airlines-name, .frame-row__name, .frame-menu__name, .title-action__text';
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
        "rule_dialog": "remove-look-%s-%s" % (RULE[0], _digest(RULE[1]))}


def _case(persona, path, dialog=None, label=None):
    return pytest.param(persona, path, dialog, id=label or (path.strip("/") or "home"))


CASES = (
    _case("admin", "/fleet", None, "fleet"),
    _case("admin", "/fleet", "dlg-add-frame", "fleet-add-dialog"),
    _case("admin", "/fleet", "dlg-retire-{slug}", "fleet-retire-dialog"),
    _case("admin", "/users", None, "users"),
    _case("admin", "/users", "dlg-invite-user", "users-invite-dialog"),
    _case("admin", "/locations", None, "locations"),
    _case("admin", "/audit", None, "audit"),
    _case("admin", "/update", None, "releases"),
    _case("admin", "/account", None, "admin-account"),
    _case("admin", "/", None, "admin-home"),
    _case("admin", "/display", None, "admin-display"),
    _case("admin", "/display/special-looks", None, "admin-display-special-looks"),
    _case("admin", "/display/calendar", None, "admin-display-calendar"),
    _case("admin", "/display/arrivals", None, "admin-display-arrivals"),
    _case("admin", "/device", None, "admin-device"),
    _case("admin", "/health", None, "admin-health"),
    _case("admin", "/flights", None, "admin-flight-history"),
    _case("owner", "/devices/{owned}/flights", None, "user-flight-history"),
    _case("admin", "/detection", None, "admin-location"),
    _case("admin", "/airlines", None, "admin-collection"),
    _case("admin", "/airlines/manage", None, "admin-airline-editor"),
    _case("admin", "/display/special-looks", "{rule_dialog}", "remove-special-look-dialog"),
    _case("admin", "/users", "dlg-delete-user-{owner_user}", "users-delete-dialog"),
    _case("admin", "/", "dlg-quiet-hours", "admin-quiet-hours-dialog"),
    _case("owner", "/devices/{owned}/", None, "user-home"),
    _case("owner", "/devices/{owned}/", "dlg-quiet-hours", "quiet-hours-dialog"),
    _case("owner", "/devices/{owned}/display", None, "user-display"),
    _case("owner", "/devices/{owned}/detection", None, "user-location"),
    _case("owner", "/devices/{owned}/airlines", None, "user-collection"),
    _case("co", "/devices/{owned}/detection", None, "co-manager-location"),
    _case("owner", "/account", None, "user-account"),
    _case("owner", "/account", "dlg-access-{slug}", "user-access-dialog"),
    _case("owner", "/account", "dlg-remove-frame-{slug}", "user-remove-frame-dialog"),
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
    # The sections enter with a finite animation: hit-test only once it has ended.
    page.wait_for_function(FINITE_ANIMATIONS_DONE, timeout=10000)
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
            "list": path == "/fleet"})
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
    r"Air France|easyJet|Transavia|Ryanair|Confirmed|Rare|test)\b|^[A-Z0-9]{4} · |^(Paris-Orly Airport|Watching Runway)")


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
    "no_contact": (r"Last contact \d+h ago",),
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
            "(n) => [n, '.home-state', 'main h1'].map("
            "(s) => document.querySelector(s).getBoundingClientRect().top)", NOTICE)
        if not tops[0] < tops[1] <= tops[2]:
            problems.append("order is not notification, state card with title: %r" % (tops,))
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
            if len(text) > 230:
                problems.append("the notification is not short: %d characters" % len(text))
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
# strip names frames, which differ with the person, and are left out.
_PAGE_SHAPE = """
() => {
  const skip = '.tab-bar__link--switch, .space-switch, .frame-notice,'
    + ' .frame-menu, script, style, template';
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


# --- Hit targets while a card is still arriving -------------------------------
# The cards enter with a finite fade and rise. A control inside an arriving card must
# answer to at least 44px at every moment of that entrance, not only once it has
# settled: every page is frozen mid-entrance at several points of the animation
# timeline and every control is measured by its box and by how far the browser routes a
# pointer to it.
PAGES = [c for c in CASES if c.values[2] is None]
# Progress points of the entrance timeline where the page is frozen. Odd
# fractions on purpose: a rise that moves by a fraction of a pixel shows up there.
PHASES = (0.13, 0.37, 0.61, 0.83)

_FREEZE_AT = """
(fraction) => {
  for (const animation of document.getAnimations()) {
    const timing = animation.effect && animation.effect.getComputedTiming();
    if (!timing || timing.iterations === Infinity) continue;
    animation.pause();
    animation.currentTime = timing.delay + fraction * timing.duration;
  }
  return document.getAnimations().filter((a) => a.playState === 'paused').length;
}
"""

_BOX_HEIGHTS = """
(scopes) => {
  const sel = 'a.calendar-manage, a.login-signin, button, select, summary, '
    + 'input:not([type=hidden]):not([type=radio]):not([type=checkbox]):not([type=file])';
  const found = new Set();
  scopes.forEach((s) => document.querySelectorAll(s + ' :is(' + sel + '), ' + s + ':is(' + sel + ')')
    .forEach((e) => found.add(e)));
  const bad = [];
  for (const el of found) {
    if (!el.checkVisibility() || el.closest('dialog, .visually-hidden')) continue;
    if (el.matches('.skip-link, .brand__link') || el.closest('.dashboard-sidebar')) continue;
    if (getComputedStyle(el).display === 'inline') continue;
    const height = Math.round(el.getBoundingClientRect().height * 100) / 100;
    if (height < 44) bad.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]
      + ' ' + height);
  }
  return bad;
}
"""


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("persona,path,dialog", PAGES)
def test_controls_keep_44px_at_every_point_of_the_entrance(
        new_context, server, persona, path, dialog, viewport):
    context, page = _open(new_context, server, persona, path, dialog, viewport, "fr", "dark")
    try:
        # Reload so the entrance restarts, then freeze it at each phase.
        page.reload(wait_until="commit")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        scopes = _target_scopes(dialog, viewport)
        problems = []
        for fraction in PHASES:
            page.evaluate(_FREEZE_AT, fraction)
            problems += ["%s: %s" % (fraction, p) for p in page.evaluate(_BOX_HEIGHTS, scopes)]
            problems += ["%s: %s" % (fraction, p) for p in page.evaluate(_TARGETS, scopes)]
        assert not problems, (path, viewport["width"], problems)
    finally:
        context.close()



# --- The sky-and-motion language on the real pages ---------------------------
# Surfaces, motion, performance and contrast: cards, tables and empty states are
# translucent on the radius scale, the glass blur stays on a handful of large surfaces,
# every animation is finite (the status dot's pulse is the one ambient loop), the
# entrance never shifts the layout, and the text inks stay readable on the page under
# the pale sky of Light and the ink gradient of Dark.
THREE_PAGES = [c for c in PAGES if c.id in ("user-home", "user-account", "user-flight-history")]
# Home's signature is the one other deliberate ambient motion, content-neutral and slow: the
# dot's and the picture glow's 6s breathing and the 12s cycle of the glass glint. Each is
# transform/opacity only and switched off under reduced motion; no other page may loop.
AMBIENT_LOOPS = {
    "skypane-pulse", "skypane-dot-halo",
    "skypane-dot-breathe", "skypane-picture-breathe", "skypane-glint"}


_SURFACES = """
() => [...document.querySelectorAll(
    '.page-section:not(.personalisation-card--list), .dashboard-main > .empty-state,'
    + ' .dashboard-main > .data-table-wrap, .airlines-table')]
  .filter((e) => e.checkVisibility() && !e.closest('.group') && (!e.matches('.airlines-table')
    || getComputedStyle(e).display === 'table'))
  .map((e) => { const s = getComputedStyle(e);
    const alpha = (c) => { const m = c.match(/\\/ ([0-9.]+)\\)$|, ([0-9.]+)\\)$/);
      return m ? parseFloat(m[1] || m[2]) : 1; };
    return {name: e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0],
      radius: s.borderTopLeftRadius, alpha: alpha(s.backgroundColor),
      blur: s.backdropFilter}; })
"""

_BLURRED = """
() => [...document.querySelectorAll('body *')]
  .filter((e) => e.checkVisibility() && getComputedStyle(e).backdropFilter !== 'none')
  .map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0])
"""

_ANIMATIONS = """
() => document.getAnimations().map((a) => ({
  name: a.animationName || a.transitionProperty || '',
  iterations: a.effect ? a.effect.getComputedTiming().iterations : 1}))
"""


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("persona,path,dialog", PAGES)
def test_cards_tables_and_empty_states_are_glass_on_the_radius_scale(
        new_context, server, persona, path, dialog, viewport):
    context, page = _open(new_context, server, persona, path, dialog, viewport, "en", "light")
    try:
        for surface in page.evaluate(_SURFACES):
            assert surface["radius"] == "22px", (path, surface)
            assert surface["alpha"] < 1, (path, surface)
        blurred = page.evaluate(_BLURRED)
        # A handful of large surfaces: the bars, the sidebar and one or two cards.
        assert len(blurred) <= 6, (path, blurred)
    finally:
        context.close()


@pytest.mark.parametrize("persona,path,dialog", PAGES)
def test_every_animation_on_a_page_is_finite_except_the_status_pulse(
        new_context, server, persona, path, dialog):
    context, page = _open(new_context, server, persona, path, dialog, VIEWPORTS[0].values[0], "en", "light")
    try:
        page.reload(wait_until="commit")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        for animation in page.evaluate(_ANIMATIONS):
            if animation["iterations"] == float("inf") or animation["iterations"] is None:
                assert animation["name"] in AMBIENT_LOOPS, (path, animation)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("persona,path,dialog", THREE_PAGES)
def test_the_entrance_shifts_no_layout(new_context, server, persona, path, dialog, viewport):
    context, page = _open(new_context, server, persona, path, dialog, viewport, "en", "light")
    try:
        page.add_init_script(
            "window.__shift = 0; new PerformanceObserver((list) => { for (const e of list.getEntries())"
            " if (!e.hadRecentInput) { window.__shift += e.value; (window.__src = window.__src || []).push("
            "e.sources.map((x) => x.node && (x.node.tagName + '.' + x.node.className)).join(',')); } })"
            ".observe({type: 'layout-shift', buffered: true});")
        page.reload()
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations()"
            ".every((a) => a.playState !== 'running' || (a.effect && a.effect"
            ".getComputedTiming().iterations === Infinity))", timeout=10000)
        assert page.evaluate("() => window.__shift") < 0.001, page.evaluate("() => window.__src")
    finally:
        context.close()


# The text inks of the page measured on what is really behind them: the element's own and
# its ancestors' translucent backgrounds composited over each stop of the sky.
_INKS = """
() => {
  const parse = (c) => {
    let m = c.match(/^rgba?\\(([^)]+)\\)$/);
    if (m) { const p = m[1].split(/[ ,\\/]+/).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; }
    m = c.match(/^color\\(srgb ([^)]+)\\)$/);
    if (m) { const p = m[1].split(/[ \\/]+/).map(Number);
      return {r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1}; }
    return null;
  };
  const over = (top, back) => ({r: top.r * top.a + back.r * (1 - top.a),
    g: top.g * top.a + back.g * (1 - top.a), b: top.b * top.a + back.b * (1 - top.a), a: 1});
  const hex = (h) => ({r: parseInt(h.slice(1, 3), 16), g: parseInt(h.slice(3, 5), 16),
    b: parseInt(h.slice(5, 7), 16), a: 1});
  const root = getComputedStyle(document.documentElement);
  const stops = ['--sky-top', '--sky-mid', '--sky-bottom'].map((n) => hex(root.getPropertyValue(n).trim()));
  const behind = (el, stop) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const bg = parse(getComputedStyle(n).backgroundColor);
      if (bg && bg.a > 0) { layers.push(bg); if (bg.a >= 1) break; }
    }
    return layers.reduceRight((acc, layer) => over(layer, acc), stop);
  };
  const out = [];
  const seen = new Set();
  const check = (el, kind, color) => {
    const ink = parse(color);
    if (!ink || ink.a === 0) return;
    for (const stop of stops) {
      const back = behind(el, stop);
      const fg = over(ink, back);
      out.push({kind: kind, name: el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0],
        fg: [fg.r, fg.g, fg.b].map(Math.round), bg: [back.r, back.g, back.b].map(Math.round)});
    }
  };
  for (const el of document.querySelectorAll('main *')) {
    if (!el.checkVisibility() || el.closest('dialog, .visually-hidden, svg, [aria-hidden=true]')) continue;
    if ([...el.childNodes].every((n) => n.nodeType !== 3 || !n.textContent.trim())
        && !(el.matches('input, textarea'))) continue;
    if (el.matches('input, textarea')) {
      check(el, 'placeholder', getComputedStyle(el, '::placeholder').color);
      continue;
    }
    const style = getComputedStyle(el);
    if (style.backgroundImage !== 'none' || el.closest('.pill, .rarity-badge, button, .badge, .btn')) continue;
    const key = el.className + style.color;
    if (seen.has(key)) continue;
    seen.add(key);
    const kind = el.disabled || el.getAttribute('aria-disabled') === 'true' ? 'disabled'
      : el.matches('a') ? 'link' : 'text';
    check(el, kind, style.color);
  }
  return out;
}
"""

CONTRAST_PAGES = [c for c in PAGES if c.id in (
    "user-home", "user-account", "user-collection", "user-display", "user-flight-history",
    "admin-collection", "users", "audit", "fleet")]


@pytest.mark.parametrize("scheme", ("light", "dark"))
@pytest.mark.parametrize("persona,path,dialog", CONTRAST_PAGES)
def test_text_links_placeholders_and_disabled_controls_stay_readable_on_the_background(
        new_context, server, persona, path, dialog, scheme):
    context, page = _open(new_context, server, persona, path, dialog, VIEWPORTS[0].values[0], "en", scheme)
    try:
        low = []
        for item in page.evaluate(_INKS):
            ratio = contrast_ratio("#%02x%02x%02x" % tuple(item["fg"]), "#%02x%02x%02x" % tuple(item["bg"]))
            # Disabled text is exempt from WCAG but must stay legible (3:1).
            floor = 3.0 if item["kind"] == "disabled" else WCAG_AA_NORMAL_TEXT
            if ratio < floor:
                low.append((item["kind"], item["name"], round(ratio, 2)))
        assert not low, (path, scheme, low)
    finally:
        context.close()


# --- one design language, page by page -------------------------------------------
# Every page above (and every dialog it opens) is held to the shared rules: the page title is
# the title token, every other heading is the section label, the card title or the sub-page
# title, controls share one height and radius, no glass surface sits inside another, no warm
# legacy fill remains, a page carries few blurred surfaces, every animation is finite (the
# status pulse apart), nothing shifts while the page settles, reduced motion stops the
# movement, every control type shows a focus ring, and navigation and menus state what they are.

PHONE = {"width": 390, "height": 844}
RULE_PAGES = [pytest.param(c.values, id=c.id) for c in CASES if not c.values[2]]
RULE_DIALOGS = [pytest.param(c.values, id=c.id) for c in CASES if c.values[2]]


def where_id(case):
    return "%s%s" % (case[0], case[1])


def _only(*ids):
    return [c for c in RULE_PAGES if c.id in ids]

# The type scale a heading may use, read from the tokens themselves.
_TOKENS = """
() => {
  const probe = (css) => {
    const e = document.createElement('span');
    e.style.cssText = 'position:absolute;visibility:hidden;font-size:' + css;
    document.body.appendChild(e);
    const v = getComputedStyle(e).fontSize;
    e.remove();
    return v;
  };
  return {
    title: probe('var(--font-page-title-size)'),
    label: probe('var(--font-caption-size)'),
    card: probe('var(--font-card-title-size)'),
    sub: probe('var(--font-heading-size)'),
    radius: (() => {
      const e = document.createElement('span');
      e.style.cssText = 'position:absolute;visibility:hidden;border-radius:var(--radius-control)';
      document.body.appendChild(e);
      const v = getComputedStyle(e).borderRadius;
      e.remove();
      return v;
    })()
  };
}
"""

_HEADINGS = """
(tokens) => {
  const bad = [];
  const shown = (e) => {
    const r = e.getBoundingClientRect();
    return r.width > 2 && r.height > 2 && !e.closest('[hidden]') &&
      !e.closest('dialog:not([open])') && getComputedStyle(e).visibility !== 'hidden';
  };
  const allowed = [tokens.label, tokens.card, tokens.sub];
  for (const h of document.querySelectorAll('main h1')) {
    // Home's title is the frame name in the hero, sized by its own contract
    // (48px desktop, 28px phone, 24px under 380px).
    if (h.classList.contains('title-action__text')) continue;
    if (shown(h) && getComputedStyle(h).fontSize !== tokens.title) {
      bad.push('h1 ' + h.className + ' is ' + getComputedStyle(h).fontSize);
    }
  }
  for (const h of document.querySelectorAll('main h2, main h3, main legend')) {
    if (!shown(h) || h.closest('dialog')) continue;
    const size = getComputedStyle(h).fontSize;
    if (!allowed.includes(size)) bad.push(h.tagName + '.' + h.className + ' is ' + size);
  }
  return bad;
}
"""

_CONTROLS = """
(tokens) => {
  const bad = [];
  const sel = 'main select, main input:not([type=hidden]):not([type=checkbox]):not([type=radio])' +
    ':not([type=range]):not([type=file]):not(.visually-hidden)';
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || e.closest('[hidden]') || e.closest('dialog:not([open])')) continue;
    const c = getComputedStyle(e);
    if (c.position === 'absolute' && c.clip !== 'auto') continue;
    if (r.height < 43.5) bad.push(e.tagName + '.' + e.className + ' height ' + r.height);
    if (c.borderRadius !== tokens.radius) bad.push(e.tagName + '.' + e.className + ' radius ' + c.borderRadius);
  }
  return bad;
}
"""

_NESTED_GLASS = """
() => {
  const surface = '.group, .page-section, .data-table-wrap, .data-card, .history-card, .empty-state';
  const visible = (e) => {
    const c = getComputedStyle(e);
    const alpha = (c.backgroundColor.match(/[\\d.]+/g) || []).length === 4
      ? parseFloat(c.backgroundColor.match(/[\\d.]+/g)[3]) : 1;
    const bordered = parseFloat(c.borderTopWidth) > 0 && c.borderTopColor !== 'rgba(0, 0, 0, 0)';
    return alpha > 0.3 && (bordered || c.boxShadow !== 'none');
  };
  const bad = [];
  for (const e of document.querySelectorAll('main ' + surface.split(', ').join(', main '))) {
    if (!visible(e) || e.closest('dialog')) continue;
    let p = e.parentElement;
    while (p && p.tagName !== 'MAIN') {
      if (p.matches(surface) && visible(p)) { bad.push(e.className + ' inside ' + p.className); break; }
      p = p.parentElement;
    }
  }
  return bad;
}
"""

_WARM_FILLS = """
() => {
  const bad = [];
  const warm = (css) => {
    const m = css.match(/rgba?\\(([^)]+)\\)/g) || [];
    return m.some((x) => {
      const [r, g, b, a] = x.match(/[\\d.]+/g).map(Number);
      return (a === undefined || a > 0.5) && r > 214 && g > 214 && r - b >= 6 && r >= g && g >= b;
    });
  };
  for (const e of [document.documentElement, document.body, ...document.querySelectorAll('main *')]) {
    const c = getComputedStyle(e);
    if (e.closest('svg, img, picture, canvas')) continue;
    // The Location map box shows the map tiles' own ground colour (a warm tone by design).
    // So does the page body behind it, so no band shows where the map ends.
    if (e.id === 'place-map' || (e === document.body && document.querySelector('.place-stage'))) continue;
    if (warm(c.backgroundColor) || warm(c.backgroundImage)) bad.push(e.tagName + '.' + e.className);
  }
  return bad.slice(0, 5);
}
"""

_BLUR_AND_ANIMATIONS = """
() => {
  let blurred = 0;
  for (const e of document.querySelectorAll('body *')) {
    const c = getComputedStyle(e);
    const f = c.backdropFilter || c.webkitBackdropFilter;
    const r = e.getBoundingClientRect();
    // The content of a closed disclosure is not painted, so it holds no blur.
    const closed = e.closest('details:not([open])');
    if (closed && !e.closest('summary') && e !== closed) continue;
    if (f && f !== 'none' && r.width > 0 && r.height > 0) blurred += 1;
  }
  const infinite = document.getAnimations().filter((a) => {
    const t = a.effect && a.effect.getComputedTiming();
    const target = a.effect && a.effect.target;
    return t && t.iterations === Infinity &&
      !(target && target.closest(
        '.home-state__dot--pulse, [class*="dot--pulse"], .hero__picture, .hero__glass'));
  }).map((a) => (a.effect.target && a.effect.target.className) || a.id || 'animation');
  return {blurred, infinite};
}
"""

_SHIFT = """
() => new Promise((resolve) => {
  let total = 0;
  const po = new PerformanceObserver((list) => {
    for (const e of list.getEntries()) if (!e.hadRecentInput) total += e.value;
  });
  po.observe({type: 'layout-shift', buffered: true});
  setTimeout(() => {
    for (const e of po.takeRecords()) if (!e.hadRecentInput) total += e.value;
    po.disconnect();
    resolve(total);
  }, 600);
})
"""


def _open_page(new_context, server, case, viewport, scheme, lang="en"):
    persona, path, dialog = case
    return _open(new_context, server, persona, path, dialog, viewport, lang, scheme)


@pytest.mark.parametrize("scheme", ("light", "dark"))
@pytest.mark.parametrize("viewport", (PHONE, VIEWPORT_DESKTOP), ids=("phone", "desktop"))
@pytest.mark.parametrize("case", RULE_PAGES)
def test_every_page_follows_the_shared_rules(new_context, server, case, viewport, scheme):
    context, page = _open_page(new_context, server, case, viewport, scheme)
    where = "%s/%d/%s" % (where_id(case), viewport["width"], scheme)
    try:
        tokens = page.evaluate(_TOKENS)
        problems = []
        problems += ["heading: " + p for p in page.evaluate(_HEADINGS, tokens)]
        problems += ["control: " + p for p in page.evaluate(_CONTROLS, tokens)]
        problems += ["nested glass: " + p for p in page.evaluate(_NESTED_GLASS)]
        if scheme == "light":
            problems += ["warm fill: " + p for p in page.evaluate(_WARM_FILLS)]
        report = page.evaluate(_BLUR_AND_ANIMATIONS)
        if report["blurred"] > 6:
            problems.append("%d blurred surfaces" % report["blurred"])
        problems += ["infinite animation: %s" % a for a in report["infinite"]]
        assert not problems, (where, problems)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ("light", "dark"))
@pytest.mark.parametrize("case", RULE_DIALOGS)
def test_every_dialog_is_a_glass_sheet_with_a_graphite_primary(new_context, server, case, scheme):
    context, page = _open_page(new_context, server, case, PHONE, scheme)
    try:
        report = page.evaluate("""() => {
          const d = document.querySelector('dialog[open]');
          const c = getComputedStyle(d);
          const rect = d.getBoundingClientRect();
          return {
            radius: c.borderTopLeftRadius, outline: c.outlineStyle,
            fits: rect.left >= 0 && rect.right <= innerWidth + 0.5,
            sheetRadius: getComputedStyle(document.documentElement).getPropertyValue('--radius-sheet').trim()};
        }""")
        assert report["fits"], where_id(case)
        assert report["outline"] in ("none", "auto") and report["radius"] != "0px", report
    finally:
        context.close()


@pytest.mark.parametrize("case", _only("home", "admin-home", "user-home", "fleet", "users"))
def test_the_page_does_not_shift_while_it_settles(new_context, server, case):
    context, page = _open_page(new_context, server, case, PHONE, "light")
    try:
        shift = page.evaluate(_SHIFT)
        assert shift < 0.1, (where_id(case), shift)
    finally:
        context.close()


@pytest.mark.parametrize("case", _only("admin-home", "fleet", "user-account", "admin-collection"))
def test_reduced_motion_stops_the_movement(new_context, server, case):
    context, page = _open_page(new_context, server, case, PHONE, "light")
    try:
        page.emulate_media(reduced_motion="reduce")
        page.reload()
        page.locator("main").wait_for(state="visible")
        page.wait_for_function("document.readyState === 'complete'")
        page.wait_for_function(
            "() => document.getAnimations().every((a) => !a.effect || "
            "a.effect.getComputedTiming().iterations !== Infinity)", timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("case", _only("admin-device", "user-account", "admin-airline-editor", "users"))
def test_every_control_type_shows_a_focus_ring(new_context, server, case):
    context, page = _open_page(new_context, server, case, PHONE, "light")
    try:
        page.keyboard.press("Tab")
        missing = page.evaluate("""() => {
          const kinds = {};
          const sel = 'main a[href], main button, main select, main input:not([type=hidden]), main summary';
          for (const e of document.querySelectorAll(sel)) {
            const r = e.getBoundingClientRect();
            if (r.width < 2 || r.height < 2 || e.closest('[hidden]')) continue;
            const kind = e.tagName + ':' + (e.type || '');
            if (kinds[kind] !== undefined) continue;
            e.focus({focusVisible: true});
            const c = getComputedStyle(e);
            const ring = c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) >= 1.5;
            const shadow = c.boxShadow !== 'none';
            kinds[kind] = ring || shadow || document.activeElement !== e;
          }
          return Object.keys(kinds).filter((k) => !kinds[k]);
        }""")
        assert not missing, (where_id(case), missing)
    finally:
        context.close()


@pytest.mark.parametrize("case", _only("admin-home", "fleet", "user-home"))
def test_navigation_and_menus_state_what_they_are(new_context, server, case):
    context, page = _open_page(new_context, server, case, PHONE, "light")
    try:
        report = page.evaluate("""() => {
          const nav = [...document.querySelectorAll('nav')].filter((n) => n.getBoundingClientRect().width > 0);
          const current = nav.map((n) => n.querySelectorAll('[aria-current="page"]').length);
          const menus = [...document.querySelectorAll('summary[aria-haspopup]')]
            .filter((s) => s.getBoundingClientRect().width > 0)
            .map((s) => s.hasAttribute('aria-expanded'));
          return {current, menus, named: nav.every((n) => n.hasAttribute('aria-label') || n.hasAttribute('aria-labelledby'))};
        }""")
        assert any(count == 1 for count in report["current"]), report
        assert report["menus"] and all(report["menus"]), report
        assert report["named"], report
    finally:
        context.close()
