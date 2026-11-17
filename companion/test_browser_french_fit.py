"""Real-browser checks that French wording, which runs longer than English, is never cut:
the owner row of a frame's Access tab on a phone, the role select of the Users table on a
desktop, and the "Applies to" segments of the special-look form on a phone."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    seed_state_dir)

pytestmark = pytest.mark.browser

PHONES = (
    pytest.param(VIEWPORT_MIN_SUPPORTED, id="360"),
    pytest.param(VIEWPORT_PHONE, id="390"))

_READY = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")


class _Rig:
    def __init__(self, server, seed):
        self.server = server
        self.seed = seed


@pytest.fixture(scope="module")
def rig(module_app_server_factory):
    seeds = []

    def seed(state_dir):
        seed_state_dir(state_dir)
        seeds.append(fx.seed_fleet(state_dir))

    server = module_app_server_factory(seed=seed, fake_providers=True)
    return _Rig(server, seeds[0])


def _french_admin(new_context, rig, viewport, path):
    name, value = fx.admin_cookie(rig.server.state_dir).split("=", 1)
    base = rig.server.base_url()
    context = new_context(viewport=viewport, reduced_motion="reduce")
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "fr", "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_READY, timeout=15000)
    return context, page


_OWNER_ROW = """() => {
  const row = document.querySelector('.group > .row.access-person');
  const box = (e) => { const r = e.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            width: r.width, height: r.height}; };
  const email = row.querySelector('.co-manager__email');
  const pill = row.querySelector('.banner__pill');
  const value = row.querySelector('.row__value');
  const action = row.querySelector('a.row-action');
  return {row: box(row), email: box(email), pill: box(pill), value: box(value),
          action: box(action), emailText: email.textContent, emailTitle: email.title,
          emailCut: email.scrollWidth > email.clientWidth,
          pillText: pill.textContent, pillCut: pill.scrollWidth > pill.clientWidth,
          valueCut: value.scrollWidth > value.clientWidth,
          valueOverflow: getComputedStyle(value).overflowX,
          actionText: action.textContent.trim(),
          actionCut: action.scrollWidth > action.clientWidth};
}"""


def _apart(a, b):
    """Whether two boxes share no pixel."""
    return (a["right"] <= b["left"] or b["right"] <= a["left"]
            or a["bottom"] <= b["top"] or b["bottom"] <= a["top"])


@pytest.mark.parametrize("viewport", PHONES)
def test_the_owner_row_of_access_shows_the_address_and_the_whole_pill(
        new_context, rig, viewport):
    """Fleet > a frame > Access, in French on a phone: the owner's address keeps most of the
    row and is whole at 360px and 390px (its title holds the full value too), the Owner pill
    is whole under or beside it, the Reassign action keeps a 44px target
    on the row's line, none of them covers another and the page does not scroll sideways."""
    context, page = _french_admin(
        new_context, rig, viewport, "/fleet?tab=access&frame=" + rig.seed.live_id)
    try:
        seen = page.evaluate(_OWNER_ROW)
        assert seen["emailText"] == fx.ADMIN_EMAIL and seen["emailTitle"] == fx.ADMIN_EMAIL
        assert not seen["emailCut"], seen
        # The address is no longer squeezed by the pill: it has the row less the action.
        assert seen["email"]["width"] >= 0.45 * seen["row"]["width"], seen
        assert seen["email"]["height"] < 30, seen
        assert seen["pillText"] == "Propriétaire", seen
        assert not seen["pillCut"] and not seen["valueCut"], seen
        for part in ("email", "pill", "action"):
            assert seen[part]["left"] >= seen["row"]["left"] - 0.5, (part, seen)
            assert seen[part]["right"] <= seen["row"]["right"] + 0.5, (part, seen)
        assert seen["pill"]["left"] >= seen["value"]["left"] - 0.5, seen
        assert seen["pill"]["right"] <= seen["value"]["right"] + 0.5, seen
        assert seen["actionText"] == "Réattribuer" and not seen["actionCut"], seen
        assert seen["action"]["height"] >= 44 and seen["action"]["width"] >= 44, seen
        assert _apart(seen["email"], seen["pill"]), seen
        assert _apart(seen["email"], seen["action"]), seen
        assert _apart(seen["pill"], seen["action"]), seen
        assert not _assert_no_page_overflow(page, "Fleet access", viewport["width"])
    finally:
        context.close()


def test_a_long_address_in_access_gives_way_with_an_ellipsis_and_a_title(new_context, rig):
    """An address wider than the row is cut with an ellipsis on one line, its full value stays
    in the title, and the pill beside or under it is still whole."""
    context, page = _french_admin(
        new_context, rig, VIEWPORT_MIN_SUPPORTED, "/fleet?tab=access&frame=" + rig.seed.live_id)
    try:
        long_address = "prenom.nom-compose.avec-un-tres-long-nom@sous-domaine.example.test"
        page.evaluate(
            "(text) => { const e = document.querySelector('.access-person .co-manager__email');"
            " e.textContent = text; e.title = text; }", long_address)
        seen = page.evaluate(_OWNER_ROW)
        assert seen["emailCut"] and seen["emailTitle"] == long_address, seen
        assert seen["email"]["height"] < 30, seen
        assert seen["email"]["right"] <= seen["row"]["right"] + 0.5, seen
        style = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'.access-person .co-manager__email')).textOverflow")
        assert style == "ellipsis"
        assert not seen["pillCut"] and not seen["valueCut"], seen
        assert _apart(seen["email"], seen["pill"]) and _apart(seen["pill"], seen["action"]), seen
        assert not _assert_no_page_overflow(page, "Fleet access, long address", 360)
    finally:
        context.close()


# The width a select takes when nothing constrains it: its longest option, its padding and
# the arrow the browser draws. A select narrower than that cuts its text.
_ROLE_SELECTS = """() => [...document.querySelectorAll('.users-table select[name=role]')]
  .filter((s) => s.getClientRects().length).map((s) => {
    const shown = s.getBoundingClientRect().width;
    const cell = s.closest('.users-cell').getBoundingClientRect();
    const box = s.getBoundingClientRect();
    const before = s.getAttribute('style');
    s.style.width = 'auto'; s.style.maxWidth = 'none'; s.style.flex = 'none';
    const natural = s.getBoundingClientRect().width;
    if (before === null) { s.removeAttribute('style'); } else { s.setAttribute('style', before); }
    return {shown: shown, natural: natural, height: box.height,
            options: [...s.options].map((o) => o.textContent),
            inside: box.left >= cell.left - 0.5 && box.right <= cell.right + 0.5};
  })"""


def test_the_role_select_of_the_users_table_shows_its_longest_role(new_context, rig):
    """Users, in French on a desktop: every role select is at least as wide as its longest
    option needs ("Administrateur"), stays inside its cell and keeps a 44px target."""
    context, page = _french_admin(new_context, rig, VIEWPORT_DESKTOP, "/users")
    try:
        assert page.evaluate(
            "() => getComputedStyle(document.querySelector('.users-table')).display") == "table"
        selects = page.evaluate(_ROLE_SELECTS)
        assert selects
        for select in selects:
            assert "Administrateur" in select["options"], select
            assert select["shown"] >= select["natural"] - 0.5, select
            assert select["inside"] and select["height"] >= 44, select
        assert not _assert_no_page_overflow(page, "Users", 1280)
    finally:
        context.close()


_SEGMENTS = """() => [...document.querySelectorAll(
    '.theme-form input[name=rule_kind] + label')].map((label) => {
  const box = label.getBoundingClientRect();
  const range = document.createRange();
  range.selectNodeContents(label);
  const lines = new Set([...range.getClientRects()].map((r) => Math.round(r.top)));
  const text = range.getBoundingClientRect();
  return {text: label.textContent, width: box.width, height: box.height, lines: lines.size,
          inside: text.left >= box.left - 0.5 && text.right <= box.right + 0.5,
          cut: label.scrollWidth > label.clientWidth};
})"""


@pytest.mark.parametrize("viewport", PHONES)
def test_the_applies_to_segments_keep_each_word_whole(new_context, rig, viewport):
    """Style > Special looks > New, in French on a phone: each "Applies to" segment shows its
    word on one line inside its own box ("Compagnie" is not broken), keeps a 44px target, and
    the track stays inside the page."""
    context, page = _french_admin(
        new_context, rig, viewport,
        "/devices/%s/display/special-looks/new" % rig.seed.live_id)
    try:
        segments = page.evaluate(_SEGMENTS)
        assert [segment["text"] for segment in segments] == ["Vol", "Avion", "Compagnie"]
        for segment in segments:
            assert segment["lines"] == 1, segment
            assert segment["inside"] and not segment["cut"], segment
            assert segment["height"] >= 44 and segment["width"] >= 44, segment
        track = page.evaluate(
            "() => { const t = document.querySelector('.theme-form:has(input[name=rule_kind])')"
            ".getBoundingClientRect(); return [t.left, t.right]; }")
        assert track[0] >= 0 and track[1] <= viewport["width"], track
        assert not _assert_no_page_overflow(page, "Special look form", viewport["width"])
    finally:
        context.close()
