"""Real-browser proof of the phone tab bar's content. The personal bar is Home,
Flights, Airlines, Style, Place and then, for an administrator, More (Accueil,
Vols, Compagnies, Style, Lieu, Plus) or, for a plain user, Account (Compte): a
direct link to the Account page, which carries theme, language and Sign out
itself, so a user has no More sheet. An administrator's space switch has no
cell of its own: it is a row of the More panel beside Account, theme, language
and Sign out. Airlines and Place are bar tabs, so the panel no longer lists
them. At 1280px the bar is not shown."""
import pytest

from nav_spaces_support import (
    MIN_TAP_PX, admin_page as _admin_page, own_frame_home as _own_frame_home,
    user_page as _user_page)
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED

pytestmark = pytest.mark.browser

_BAR_LABELS = {
    "en": ["Home", "Flights", "Airlines", "Style", "Location", "More"],
    "fr": ["Accueil", "Vols", "Compagnies", "Style", "Lieu", "Plus"],
}
_USER_BAR_LABELS = {
    "en": ["Home", "Flights", "Airlines", "Style", "Location", "Account"],
    "fr": ["Accueil", "Vols", "Compagnies", "Style", "Lieu", "Compte"],
}


def _bar_labels(role, lang):
    return (_USER_BAR_LABELS if role == "user" else _BAR_LABELS)[lang]

_SWITCH_LABEL = {
    "personal": {"en": "Console", "fr": "Console"},
    "console": {"en": "My frames", "fr": "Mes cadres"},
}
_ACCOUNT_LABEL = {"en": "Account", "fr": "Compte"}
_CELLS = (
    "() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')].map(e => ({"
    " label: e.querySelector('.tab-bar__label').textContent.trim(),"
    " active: !!e.querySelector('.tab-bar__link--active') || e.classList.contains('tab-bar__link--active'),"
    " switchCell: e.classList.contains('tab-bar__link--switch')}))")
_PANEL = (
    "() => { const panel = document.querySelector('.tab-bar__more-panel');"
    " const links = [...panel.querySelectorAll('a')].map(a => {"
    " const b = a.getBoundingClientRect();"
    " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
    " return {text: (a.querySelector('.link-card__title, .tab-bar__account-name') || a).textContent.trim(),"
    " href: a.getAttribute('href'), aria: a.getAttribute('aria-label'),"
    " h: b.height, hit: !!hit && a.contains(hit),"
    " space: a.classList.contains('tab-bar__space-link')}; });"
    " return {links, forms: [...panel.querySelectorAll('form')].map(f => f.getAttribute('action')),"
    " signOut: !!panel.querySelector('form[action=\"/logout\"] button[type=submit]'),"
    " open: panel.closest('details').open}; }")
_OWN_CELL_AT_CENTRE = (
    "() => { if (document.readyState !== 'complete') return false;"
    " if (document.getAnimations().some((x) => x.playState === 'running'"
    " && x.effect.getComputedTiming().iterations !== Infinity)) return false;"
    " const a = document.querySelector('.tab-bar > a, .tab-bar > details > summary');"
    " if (!a) return false; const b = a.getBoundingClientRect();"
    " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
    " return !!hit && a.contains(hit); }")


def _page(role, new_context, server, space, viewport, lang, scheme):
    if role == "user":
        return _user_page(new_context, server, viewport, lang, scheme)
    path = "/fleet" if space == "console" else _own_frame_home
    return _admin_page(new_context, server, path, viewport, lang, scheme)


def _settled_cells(page):
    page.wait_for_function(_OWN_CELL_AT_CENTRE)
    return page.evaluate(_CELLS)


def _open_panel(page):
    page.locator(".tab-bar__more > summary").click()
    page.wait_for_function(
        "() => { const d = document.querySelector('.tab-bar__more'); if (!d || !d.open) return false;"
        " if (document.getAnimations().some((x) => x.playState === 'running'"
        " && x.effect.getComputedTiming().iterations !== Infinity)) return false;"
        " return [...d.querySelectorAll('.tab-bar__more-panel a')].every((a) => {"
        " const b = a.getBoundingClientRect();"
        " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
        " return !!hit && a.contains(hit); }); }")
    return page.evaluate(_PANEL)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("role", ["admin", "user"])
def test_the_personal_bar_is_six_cells_ending_in_more_or_account(
        new_context, app_server_in_process, role, lang, scheme):
    context, page = _page(
        role, new_context, app_server_in_process, "personal", VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        cells = _settled_cells(page)
        assert [cell["label"] for cell in cells] == _bar_labels(role, lang), cells
        assert not any(cell["switchCell"] for cell in cells), cells
        assert [cell["active"] for cell in cells] == [True, False, False, False, False, False], cells
        assert page.locator(".tab-bar__link--switch").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_console_bar_has_no_switch_cell_either(new_context, app_server_in_process, lang):
    context, page = _page(
        "admin", new_context, app_server_in_process, "console", VIEWPORT_MIN_SUPPORTED, lang, "light")
    try:
        cells = _settled_cells(page)
        assert len(cells) == 5, cells
        assert not any(cell["switchCell"] for cell in cells), cells
        assert cells[-1]["label"] == _BAR_LABELS[lang][-1], cells
        assert cells[0]["active"] and cells[0]["label"] not in _BAR_LABELS[lang], cells
    finally:
        context.close()


@pytest.mark.parametrize("role", ["admin", "user"])
def test_at_1280_the_bar_is_not_shown_and_the_sidebar_carries_the_pages(
        new_context, app_server_in_process, role):
    context, page = _page(
        role, new_context, app_server_in_process, "personal", VIEWPORT_DESKTOP, "en", "light")
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        assert not page.locator(".tab-bar").is_visible()
        names = page.locator(".dashboard-sidebar .sidebar-link").all_inner_texts()
        assert [n.strip() for n in names[:5]] == [
            "Home", "Flights", "Airlines", "Style", "Location"], names
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("space", ["personal", "console"])
def test_an_administrators_plus_panel_holds_the_space_switch_beside_account(
        new_context, app_server_in_process, space, lang, scheme):
    context, page = _page(
        "admin", new_context, app_server_in_process, space, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        _settled_cells(page)
        panel = _open_panel(page)
        texts = [link["text"] for link in panel["links"]]
        assert texts == [_ACCOUNT_LABEL[lang], _SWITCH_LABEL[space][lang]], panel
        switch = panel["links"][1]
        assert switch["space"] and switch["href"] == ("/fleet" if space == "personal" else "/"), panel
        assert switch["aria"], panel
        assert all(link["h"] >= MIN_TAP_PX and link["hit"] for link in panel["links"]), panel
        assert "/ui-theme" in panel["forms"] and "/ui-lang" in panel["forms"], panel
        assert panel["signOut"], panel
        assert not any(link["href"].rstrip("/").endswith(("/airlines", "/detection"))
                       for link in panel["links"]), panel
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_users_last_tab_is_account_and_opens_the_account_page_directly(
        new_context, app_server_in_process, lang):
    context, page = _page(
        "user", new_context, app_server_in_process, "personal", VIEWPORT_MIN_SUPPORTED, lang, "dark")
    try:
        _settled_cells(page)
        assert page.locator(".tab-bar__more").count() == 0
        last = page.locator(".tab-bar > a").last
        assert last.locator(".tab-bar__label").inner_text().strip() == _ACCOUNT_LABEL[lang]
        last.click()
        page.wait_for_function("() => location.pathname.endsWith('/account')")
        cells = _settled_cells(page)
        assert [cell["active"] for cell in cells] == [False] * 5 + [True], cells
        assert page.locator(".tab-bar > a").last.get_attribute("aria-current") == "page"
        assert page.locator(".tab-bar__more").count() == 0
        # What the old sheet held stays reachable from the page itself.
        main = page.locator("main")
        assert main.locator('form[action="/ui-theme"]').count() == 1
        assert main.locator('form[action="/ui-lang"]').count() == 1
        assert main.locator('form[action="/logout"] button[type=submit]').is_visible()
    finally:
        context.close()


def test_the_switch_row_in_the_panel_moves_between_the_spaces(
        new_context, app_server_in_process):
    context, page = _page(
        "admin", new_context, app_server_in_process, "personal", VIEWPORT_MIN_SUPPORTED, "en", "light")
    try:
        _settled_cells(page)
        _open_panel(page)
        page.locator(".tab-bar__space-link").click()
        page.wait_for_function("() => location.pathname === '/fleet'")
        _settled_cells(page)
        panel = _open_panel(page)
        assert panel["links"][1]["text"] == "My frames", panel
        page.locator(".tab-bar__space-link").click()
        page.wait_for_function("() => location.pathname !== '/fleet'")
    finally:
        context.close()


_FIT = (
    "() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')].map(e => {"
    " const cell = e.getBoundingClientRect(); const label = e.querySelector('.tab-bar__label');"
    " const pill = label.closest('.tab-bar__pill').getBoundingClientRect();"
    " const range = document.createRange(); range.selectNodeContents(label);"
    " const text = range.getBoundingClientRect();"
    " return {label: label.textContent.trim(), w: cell.width, h: cell.height, right: cell.right,"
    " clipped: label.scrollWidth > label.clientWidth,"
    " slack: Math.min(text.left - pill.left, pill.right - text.right),"
    " lines: new Set([...range.getClientRects()].map(r => Math.round(r.top))).size,"
    " font: parseFloat(getComputedStyle(label).fontSize)}; })")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [320, 360, 390])
@pytest.mark.parametrize("role", ["admin", "user"])
def test_every_bar_label_is_whole_and_every_cell_a_44px_target(
        new_context, app_server_in_process, role, width, lang, scheme):
    """No label is cut or wrapped, each keeps room inside its pill, and the six
    cells stay 44px targets inside the viewport, "Airlines" included."""
    context, page = _page(
        role, new_context, app_server_in_process, "personal",
        {"width": width, "height": 800}, lang, scheme)
    try:
        page.wait_for_function(_OWN_CELL_AT_CENTRE)
        cells = page.evaluate(_FIT)
        assert [cell["label"] for cell in cells] == _bar_labels(role, lang), cells
        for cell in cells:
            where = (role, width, lang, scheme, cell)
            assert not cell["clipped"] and cell["lines"] <= 1, where
            assert cell["slack"] >= 3, where
            assert cell["w"] >= MIN_TAP_PX and cell["h"] >= MIN_TAP_PX, where
            assert cell["right"] <= width + 0.5, where
            assert cell["font"] >= 10, where
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 0.5")
    finally:
        context.close()


_BAR_EDGES = (
    "() => { const b = document.querySelector('.tab-bar').getBoundingClientRect();"
    " return {left: b.left, right: b.right, width: window.innerWidth}; }")
_PAGE_TITLE = "() => document.querySelector('h1').textContent.trim()"


@pytest.mark.parametrize("width", [320, 360, 390])
def test_french_airlines_tab_and_page_title_agree_with_a_visible_bar_margin(
        new_context, app_server_in_process, width):
    """The French nav entry and the airline page title agree: the tab reads
    "Compagnies", the page is titled the same, and the floating bar keeps a
    visible gap to both viewport edges with no clipped label."""
    context, page = _admin_page(
        new_context, app_server_in_process, "/airlines",
        {"width": width, "height": 800}, "fr", "light")
    try:
        page.wait_for_function(_OWN_CELL_AT_CENTRE)
        tab = page.locator(".tab-bar__link--active .tab-bar__label").inner_text().strip()
        assert tab == "Compagnies"
        assert page.evaluate(_PAGE_TITLE) == tab
        edges = page.evaluate(_BAR_EDGES)
        assert edges["left"] >= 4 and edges["width"] - edges["right"] >= 4, edges
        assert not any(cell["clipped"] for cell in page.evaluate(_FIT))
    finally:
        context.close()
