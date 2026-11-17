"""Real-browser flows of the phone More sheet and the tab bar around it: theme and language set
with one tap inside the sheet (and kept after a reload), Sign out two taps from any page, the
sheet's other rows, French tab labels that never touch at 360px, and the administrator's Account
page carrying a single Sign out control and a neutral space switch."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

_MORE_OWNS_CENTRE = """() => {
  const e = document.querySelector('.tab-bar__more > summary'); if (!e) return false;
  const r = e.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return hit === e || e.contains(hit); }"""

_LABELS = """() => [...document.querySelectorAll('.tab-bar__label')].map((el) => {
  const range = document.createRange(); range.selectNodeContents(el);
  const box = range.getBoundingClientRect();
  return {text: el.textContent, left: box.left, right: box.right,
          clipped: el.scrollWidth > el.clientWidth + 0.5,
          size: parseFloat(getComputedStyle(el).fontSize)}; })"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, viewport, lang="en", scheme="light", bar=True, cookie=None,
          **context_args):
    context = new_context(viewport=viewport, color_scheme=scheme, **context_args)
    base = app.server.base_url()
    name, value = (cookie or app.cookie).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    if bar:
        page.locator(".tab-bar").wait_for(state="visible")
    else:
        page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        _settle(page, bar)
    return context, page


def _settle(page, bar=True):
    page.wait_for_function(_SETTLED)
    if bar:
        page.wait_for_function(_MORE_OWNS_CENTRE, timeout=10000)


def _home(app):
    return "/devices/%s/" % app.fleet.live.id


def _open_sheet(page):
    if not page.locator(".tab-bar__more").evaluate("el => el.open"):
        page.locator(".tab-bar__more > summary").click()
    page.locator(".tab-bar__more-panel").wait_for(state="visible")


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_theme_is_one_tap_in_the_sheet_and_survives_a_reload(new_context, app, viewport):
    context, page = _open(new_context, app, _home(app), viewport)
    try:
        for choice in ("dark", "light"):
            _open_sheet(page)
            page.locator(
                ".tab-bar__more-panel button[name=ui_theme][value=%s]" % choice).click()
            page.wait_for_function(
                "t => document.documentElement.getAttribute('data-ui-theme') === t", arg=choice)
            _settle(page)
            page.reload()
            _settle(page)
            assert page.evaluate(
                "() => document.documentElement.getAttribute('data-ui-theme')") == choice
            _open_sheet(page)
            pressed = page.locator(
                ".tab-bar__more-panel button[name=ui_theme][aria-pressed=true]")
            assert pressed.get_attribute("value") == choice
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_language_is_one_tap_in_the_sheet_and_survives_a_reload(new_context, app, viewport):
    context, page = _open(new_context, app, _home(app), viewport, lang="en")
    try:
        _open_sheet(page)
        page.locator(".tab-bar__more-panel button[name=ui_lang][value=fr]").click()
        page.wait_for_function("() => document.documentElement.lang === 'fr'")
        _settle(page)
        assert page.locator(".tab-bar__more > summary .tab-bar__label").inner_text() == "Plus"
        page.reload()
        _settle(page)
        assert page.evaluate("() => document.documentElement.lang") == "fr"
        _open_sheet(page)
        assert page.locator(
            ".tab-bar__more-panel button[name=ui_lang][aria-pressed=true]"
        ).get_attribute("value") == "fr"
        assert page.locator(".tab-bar__pref .row__label").first.inner_text() == "Thème"
        page.locator(".tab-bar__more-panel button[name=ui_lang][value=en]").click()
        page.wait_for_function("() => document.documentElement.lang === 'en'")
    finally:
        context.close()


def test_the_sheet_works_with_scripts_blocked(new_context, app):
    context, page = _open(
        new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel button[name=ui_theme][value=dark]").click()
        page.wait_for_selector("html[data-ui-theme=dark]")
        assert page.locator("html").get_attribute("data-ui-theme") == "dark"
    finally:
        context.close()


def test_sign_out_is_two_taps_from_a_page(new_context, app):
    # Signing out ends the session, so this test signs in with a session of its own.
    own_session = session_cookie_for_state_dir(app.server.state_dir, OWNER_EMAIL)
    context, page = _open(
        new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, cookie=own_session)
    # The sign-in provider's own logout address is answered here, never fetched.
    context.route(
        "https://tenant.example.test/**",
        lambda route: route.fulfill(status=200, content_type="text/html", body="<p>out</p>"))
    try:
        _open_sheet(page)
        box = page.locator(".tab-bar__sign-out button").bounding_box()
        assert box["height"] >= 44
        with page.expect_request(
                lambda request: request.method == "POST" and request.url.endswith("/logout")):
            page.locator(".tab-bar__sign-out button").click()
        page.wait_for_function("() => location.hostname === 'tenant.example.test'")
    finally:
        context.close()


def test_the_sheet_holds_the_other_rows_and_the_account_row_names_the_person(
        new_context, app):
    context, page = _open(new_context, app, "/fleet", VIEWPORT_MIN_SUPPORTED)
    try:
        _open_sheet(page)
        assert page.eval_on_selector_all(
            ".tab-bar__more-panel a",
            "els => els.map(e => (e.querySelector('.link-card__title, .tab-bar__account-name') || e).textContent.trim())") == [
            "Account", "My frame"]
        assert page.locator(".tab-bar__account-email").inner_text() == OWNER_EMAIL
        for selector in (".tab-bar__more-panel a", ".tab-bar__sign-out button",
                         ".tab-bar__more-panel .theme-option"):
            for index in range(page.locator(selector).count()):
                assert page.locator(selector).nth(index).bounding_box()["height"] >= 44
        panel = page.locator(".tab-bar__more-panel").bounding_box()
        bar = page.locator(".tab-bar").bounding_box()
        assert panel["x"] >= 0 and panel["x"] + panel["width"] <= VIEWPORT_MIN_SUPPORTED["width"]
        assert panel["y"] + panel["height"] <= bar["y"] and panel["y"] >= 0
    finally:
        context.close()


@pytest.mark.parametrize("path", ["/users", "/fleet", "/audit"])
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_tab_labels_are_eleven_pixels_whole_and_never_touch_at_360(
        new_context, app, path, lang):
    context, page = _open(new_context, app, path, VIEWPORT_MIN_SUPPORTED, lang=lang)
    try:
        labels = page.evaluate(_LABELS)
        assert len(labels) == 5
        for label in labels:
            assert label["size"] == 11 and not label["clipped"], label
        for left, right in zip(labels, labels[1:]):
            assert right["left"] - left["right"] >= 4, (left["text"], right["text"])
        cells = page.evaluate(
            "() => [...document.querySelectorAll('.tab-bar > :not(.tab-bar__slider)')]"
            ".map((c) => c.getBoundingClientRect().toJSON())")
        assert all(c["width"] >= 44 and c["height"] >= 44 for c in cells)
        assert abs(sum(c["width"] for c in cells) - (page.locator(".tab-bar").bounding_box()["width"] - 6)) <= 2
    finally:
        context.close()


def test_the_console_bar_cells_share_one_height_and_none_is_a_switch(new_context, app):
    context, page = _open(new_context, app, "/users", VIEWPORT_MIN_SUPPORTED, lang="fr")
    try:
        boxes = page.evaluate(
            "() => [...document.querySelectorAll('.tab-bar > :not(.tab-bar__slider)')]"
            ".map((c) => c.getBoundingClientRect().toJSON())")
        assert len(boxes) == 5
        assert len({box["height"] for box in boxes}) == 1, boxes
        assert page.locator(".tab-bar > .tab-bar__link--switch").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("viewport,name", [
    ({"width": 1280, "height": 900}, "desktop"), (VIEWPORT_MIN_SUPPORTED, "phone")])
def test_the_admin_account_page_has_one_sign_out_and_a_neutral_space_switch(
        new_context, app, viewport, name):
    context, page = _open(new_context, app, "/account", viewport, bar=name == "phone")
    try:
        shown = page.evaluate(
            """() => [...document.querySelectorAll("form[action='/logout'] button")]
                .filter((b) => b.checkVisibility()).length""")
        assert shown == 1
        if name == "phone":
            assert page.locator(".tab-bar__sign-out").count() == 0
        assert page.locator(".space-switch__segment--current").count() == 0
        assert page.locator("[aria-current=page]").count() >= 1
    finally:
        context.close()


def test_other_pages_keep_their_sign_out_in_the_sidebar_and_the_sheet(new_context, app):
    context, page = _open(
        new_context, app, "/fleet", {"width": 1280, "height": 900}, bar=False)
    try:
        assert page.locator(".sidebar-footer form[action='/logout']").count() == 1
        assert page.locator(".tab-bar__sign-out").count() == 1
        assert page.locator(".sidebar-footer .logout-form button").evaluate(
            "el => el.checkVisibility()")
    finally:
        context.close()


_ORDER = """() => {
  const top = (sel) => { const el = document.querySelector(sel);
    return el ? el.getBoundingClientRect().top : null; };
  const panel = document.querySelector('.tab-bar__more-panel');
  return {pages: top('.tab-bar__pages'), separator: top('.tab-bar__separator'),
          theme: top('.tab-bar__pref'), account: top('.tab-bar__account'),
          language: (document.querySelectorAll('.tab-bar__pref')[1]
            || document.body).getBoundingClientRect().top,
          signOut: top('.tab-bar__sign-out'),
          firstChild: panel.firstElementChild.className,
          secondChild: panel.children[1].className,
          icons: [...document.querySelectorAll('.tab-bar__pages a')].map(
            (a) => !!a.querySelector('svg.icon')),
          labels: [...document.querySelectorAll('.tab-bar__pages a')].map((a) => a.textContent.trim())}; }"""


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_console_sheet_starts_with_account_then_theme_language_and_sign_out(
        new_context, app, viewport):
    """every Console page is in the bar, so the sheet holds no page rows: Account first, then
    Theme, Language and Sign out in the owner's order"""
    context, page = _open(new_context, app, "/fleet", viewport)
    try:
        _open_sheet(page)
        order = page.evaluate(_ORDER)
        assert order["firstChild"] == "tab-bar__grab", order
        assert order["secondChild"] == "tab-bar__settings", order
        assert order["labels"] == [] and order["separator"] is None, order
        assert (order["account"] < order["theme"] < order["language"]
                < order["signOut"]), order
    finally:
        context.close()


def test_a_personal_page_sheet_starts_with_account_and_lists_no_page_rows(new_context, app):
    """Airlines and Place are bar tabs, so the sheet holds no page rows: Account and the space
    switch first, then Theme, Language and Sign out"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_PHONE)
    try:
        _open_sheet(page)
        order = page.evaluate(_ORDER)
        assert order["firstChild"] == "tab-bar__grab", order
        assert order["secondChild"] == "tab-bar__settings", order
        assert order["labels"] == [] and order["separator"] is None, order
        assert order["account"] < order["theme"] < order["language"] < order["signOut"], order
        assert page.eval_on_selector_all(
            ".tab-bar__more-panel a",
            "els => els.map(e => (e.querySelector('.link-card__title, .tab-bar__account-name') || e).textContent.trim())") == ["Account", "Console"]
    finally:
        context.close()


_SCRIM_HITS = """() => {
  const w = window.innerWidth, h = window.innerHeight;
  // One pixel of slack: a sheet's box at a fractional offset is painted on whole pixels.
  const covered = (r, x, y) => x >= r.left - 1 && x <= r.right + 1 && y >= r.top - 1 && y <= r.bottom + 1;
  const panel = document.querySelector('.tab-bar__more-panel').getBoundingClientRect();
  const bar = document.querySelector('.tab-bar').getBoundingClientRect();
  const misses = [];
  for (let x = 2; x < w; x += 24) {
    for (let y = 2; y < h; y += 24) {
      if (covered(panel, x, y) || covered(bar, x, y)) continue;
      const hit = document.elementFromPoint(x, y);
      if (hit !== document.body) misses.push([x, y, hit && (hit.className || hit.tagName)]);
    }
  }
  const scrim = getComputedStyle(document.body, '::after');
  const base = scrim.backgroundColor.match(/[\\d.]+/g).map(Number);
  return {misses: misses.slice(0, 5), count: misses.length,
          alpha: base.length > 3 ? base[3] : 1, blur: scrim.backdropFilter,
          position: scrim.position, size: [scrim.width, scrim.height], vw: w, vh: h}; }"""


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("path", ["/fleet", "/airlines"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_page_behind_the_open_sheet_is_dimmed_blurred_and_fully_covered(
        new_context, app, viewport, path, scheme):
    context, page = _open(new_context, app, path, viewport, scheme=scheme)
    try:
        _open_sheet(page)
        probe = page.evaluate(_SCRIM_HITS)
        assert probe["count"] == 0, probe
        assert probe["alpha"] >= 0.4 and "blur" in probe["blur"], probe
        assert probe["position"] == "fixed", probe
        assert abs(float(probe["size"][0][:-2]) - probe["vw"]) <= 1, probe
        assert abs(float(probe["size"][1][:-2]) - probe["vh"]) <= 1, probe
        # A tap on the dimmed page closes the sheet.
        page.mouse.click(8, 8)
        page.wait_for_function(
            "() => !document.querySelector('.tab-bar__more').open", timeout=10000)
    finally:
        context.close()


_IN_SHEET = "() => !!document.activeElement && !!document.activeElement.closest('.tab-bar__more')"


@pytest.mark.parametrize("backwards", [False, True], ids=["tab", "shift-tab"])
def test_keyboard_focus_stays_inside_the_open_sheet(new_context, app, backwards):
    """Tab and Shift+Tab cycle through the sheet's own controls: the focus never reaches the page
    behind the dimmed scrim while the sheet is open"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED)
    try:
        _open_sheet(page)
        page.locator(".tab-bar__more-panel a, .tab-bar__more-panel button").first.focus()
        stops = page.locator(
            ".tab-bar__more-panel a, .tab-bar__more-panel button, .tab-bar__more > summary").count()
        for _ in range(stops + 3):
            page.keyboard.press("Shift+Tab" if backwards else "Tab")
            page.wait_for_function(_IN_SHEET, timeout=5000)
        assert page.locator(".tab-bar__more").evaluate("el => el.open")
    finally:
        context.close()


def test_closing_the_sheet_by_escape_or_a_second_tap_returns_the_focus_to_the_more_cell(
        new_context, app):
    context, page = _open(new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED)
    try:
        for how in ("escape", "toggle"):
            _open_sheet(page)
            page.locator(".tab-bar__more-panel a, .tab-bar__more-panel button").first.focus()
            if how == "escape":
                page.keyboard.press("Escape")
            else:
                page.locator(".tab-bar__more > summary").click()
            page.wait_for_function("() => !document.querySelector('.tab-bar__more').open")
            page.wait_for_function(
                "() => document.activeElement === document.querySelector('.tab-bar__more > summary')",
                timeout=5000)
    finally:
        context.close()


_GLYPH_BOXES = """() => [...document.querySelectorAll('.tab-bar__label')].map((el) => {
  const range = document.createRange(); range.selectNodeContents(el);
  const glyphs = range.getBoundingClientRect();
  const clip = el.getBoundingClientRect();
  return {text: el.textContent, glyphTop: glyphs.top, glyphBottom: glyphs.bottom,
          clipTop: clip.top, clipBottom: clip.bottom, cell: el.closest('.tab-bar__link,summary')
            .getBoundingClientRect().height}; })"""


@pytest.mark.parametrize("path", ["/users", "/fleet"])
def test_no_french_tab_label_loses_its_accent_or_its_descender_to_the_clip(
        new_context, app, path):
    """the glyph box of every label (a capital accent above the cap height, the tail of p and q
    below the baseline) lies inside the box that clips it, and the bar keeps its cell height"""
    context, page = _open(new_context, app, path, VIEWPORT_MIN_SUPPORTED, lang="fr")
    try:
        labels = page.evaluate(_GLYPH_BOXES)
        assert {label["text"] for label in labels} >= {"Équipe", "Éditeur"}, labels
        for label in labels:
            assert label["glyphTop"] >= label["clipTop"] - 0.5, label
            assert label["glyphBottom"] <= label["clipBottom"] + 0.5, label
            assert label["cell"] == 56, label
    finally:
        context.close()


def _listener_count(cdp):
    cdp.send("HeapProfiler.collectGarbage")
    metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    return int(metrics["JSEventListeners"])


@pytest.mark.parametrize("how", ["toggle", "escape"])
def test_opening_and_closing_the_sheet_leaves_no_event_listener_behind(new_context, app, how):
    """fifty open and close cycles add no event listener to the page, whichever way the sheet
    closes: the sheet's scripts bind once, not on every open"""
    context, page = _open(new_context, app, _home(app) + "flights", VIEWPORT_MIN_SUPPORTED)
    try:
        cdp = context.new_cdp_session(page)
        cdp.send("Performance.enable")
        page.wait_for_timeout(1000)
        before = _listener_count(cdp)
        for _ in range(50):
            page.locator(".tab-bar__more > summary").click()
            page.locator(".tab-bar__more-panel").wait_for(state="visible")
            if how == "escape":
                page.keyboard.press("Escape")
            else:
                page.locator(".tab-bar__more > summary").click()
            page.wait_for_function("() => !document.querySelector('.tab-bar__more').open")
        assert _listener_count(cdp) <= before, (before, _listener_count(cdp))
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_more_cell_is_one_glyph_like_every_other_cell(new_context, app, scheme):
    """the More cell draws its three dots alone, open or closed: no second chevron glyph sits
    over them close to the pill's edge"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, scheme=scheme)
    try:
        glyphs = "() => getComputedStyle(document.querySelector('.tab-bar__more > summary'), '::before').content"
        assert page.evaluate(glyphs) in ("none", "normal")
        _open_sheet(page)
        assert page.evaluate(glyphs) in ("none", "normal")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_theme_and_language_controls_share_one_left_and_right_edge(
        new_context, app, viewport, lang):
    context, page = _open(new_context, app, _home(app), viewport, lang=lang)
    try:
        _open_sheet(page)
        page.wait_for_function(_SETTLED)
        edges = page.evaluate("""() => [...document.querySelectorAll(
          '.tab-bar__pref .theme-form')].map((f) => {
            const r = f.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })""")
        assert len(edges) == 2 and edges[0] == edges[1], edges
        fits = page.evaluate("""() => [...document.querySelectorAll(
          '.tab-bar__pref .row__label, .tab-bar__pref .theme-option')].filter(
            (e) => e.classList.contains('row__label')
              ? e.getClientRects()[0].height > 24 : e.scrollWidth > e.clientWidth + 0.5)
            .map((e) => e.textContent)""")
        assert fits == [], fits
    finally:
        context.close()


def test_the_dim_behind_the_sheet_and_behind_a_dialog_fades_in_with_what_opens(new_context, app):
    """the scrim and a dialog's backdrop start transparent and reach full strength: the page
    does not snap to dimmed in one frame while the panel fades in"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED)
    try:
        first = page.evaluate("""() => {
          document.querySelector('.tab-bar__more').open = true;
          return getComputedStyle(document.body, '::after').opacity; }""")
        assert float(first) < 0.5, first
        page.wait_for_function(
            "() => getComputedStyle(document.body, '::after').opacity === '1'", timeout=5000)
        page.evaluate("() => { document.querySelector('.tab-bar__more').open = false; }")
        page.wait_for_function(
            "() => !document.querySelector('.tab-bar__more').open", timeout=5000)
        backdrop = page.evaluate("""() => {
          const d = document.querySelector('dialog.modal');
          d.showModal();
          return getComputedStyle(d, '::backdrop').opacity; }""")
        assert float(backdrop) < 0.5, backdrop
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('dialog.modal'), '::backdrop')"
            ".opacity === '1'", timeout=5000)
    finally:
        context.close()


_AMBIENT = """(want) => {
  const read = [
    getComputedStyle(document.querySelector('.home-state__dot--pulse')).animationIterationCount,
    getComputedStyle(
      document.querySelector('.home-state__dot--pulse'), '::after').animationIterationCount,
    getComputedStyle(
      document.querySelector('.hero__picture'), '::before').animationIterationCount];
  return read.every((v) => v === want); }"""


def test_the_home_loops_stand_still_while_the_sheet_is_open_and_resume_after(new_context, app):
    """nothing animates endlessly under the dimmed, blurred page of an open sheet"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED)
    try:
        page.wait_for_function(_AMBIENT, arg="infinite", timeout=5000)
        _open_sheet(page)
        page.wait_for_function(_AMBIENT, arg="0", timeout=5000)
        page.locator(".tab-bar__more > summary").click()
        page.wait_for_function(
            "() => !document.querySelector('.tab-bar__more').open", timeout=5000)
        page.wait_for_function(_AMBIENT, arg="infinite", timeout=5000)
    finally:
        context.close()
