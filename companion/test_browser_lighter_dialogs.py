# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the lighter console dialogs at 360x800, English and French, Light and
Dark: Retire, Re-activate and Reassign (Fleet), Manage access, Leave and Remove this frame
(Account), Delete user (Users).

Each asks one question in one sentence; the rest sits behind a closed native disclosure whose
summary is at least 44px high. The safety of the destructive ones does not change: the safe
button has the default focus, the confirm button names the action in the danger style, there are
exactly two actions and no text input (no typed confirmation exists or is added). The French
Manage access dialog fits the phone without an inner scroll for an owner and two co-managers.
Escape closes a dialog and gives the focus back to its opener. Nothing animates under reduced
motion and the texts keep 4.5:1.
"""
import re

import pytest

import animation_settle
import fleet_console_support as fx
import skypane_contrast_check
from co_manager_browser_support import SECOND_CO, Rig
from companion import auth
from companion.test_browser_ux_helpers import _login, _set_ui_theme
from server import fleet_db

pytestmark = pytest.mark.browser

PHONE = {"width": 360, "height": 800}
LANGS = ("en", "fr")
THEMES = ("light", "dark")

_FACTS = """sel => {
  const d = document.querySelector(sel);
  const body = d.querySelector('.modal__body').cloneNode(true);
  body.querySelectorAll('details, .modal__field, [hidden], .visually-hidden').forEach(e => e.remove());
  const more = [...d.querySelectorAll('details')].map(x => ({
    open: x.open, cls: x.className,
    summary: x.querySelector('summary').getBoundingClientRect().height,
    summaryText: x.querySelector('summary').textContent.trim()}));
  const r = d.getBoundingClientRect();
  const ink = el => getComputedStyle(el).color;
  const visible = [...body.querySelectorAll('p, li')].length;
  return {
    text: body.textContent.replace(/\\s+/g, ' ').trim(), more: more, height: r.height,
    vh: innerHeight, innerScroll: d.scrollHeight > d.clientHeight + 1,
    bodyScroll: (d.querySelector('.modal__body').scrollHeight
                 > d.querySelector('.modal__body').clientHeight + 1),
    sideways: d.scrollWidth > d.clientWidth + 1, blocks: visible,
    inputs: d.querySelectorAll('input:not([type="hidden"]), textarea').length,
    actions: d.querySelectorAll('.modal__actions button, .modal__actions a').length,
    submitText: (d.querySelector('.modal__actions button[type="submit"]') || {textContent: ''})
      .textContent.trim(),
    submitDanger: !!d.querySelector('.modal__actions button.btn--danger'),
    focusOnDismiss: document.activeElement === d.querySelector('.modal__actions a.modal__dismiss'),
    running: d.getAnimations({subtree: true}).filter(
      a => a.playState === 'running' && a.effect.getTiming().duration > 1).length,
    domText: d.innerText,
  };
}"""

# One text block's colour over the dialog's own fill, as drawn.
_PAIRS = """sel => {
  const d = document.querySelector(sel);
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const hex = (under, ink) => {
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = under; ctx.fillRect(0, 0, 1, 1);
    ctx.fillStyle = ink; ctx.fillRect(0, 0, 1, 1);
    const p = ctx.getImageData(0, 0, 1, 1).data;
    return '#' + [p[0], p[1], p[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
  const fill = getComputedStyle(d).backgroundColor;
  const flat = hex('#ffffff', fill);
  return [...d.querySelectorAll('.modal__body p, .modal__body li, .modal__more-summary')]
    .filter(e => e.offsetParent !== null && e.textContent.trim())
    .map(e => [hex(flat, getComputedStyle(e).color), flat, e.className]);
}"""


class _Case:
    """One dialog: how to reach the page, open it, and find its opener."""

    def __init__(self, name, page_of, open_dialog, opener, safe=False):
        self.name = name
        self.page_of = page_of
        self.open_dialog = open_dialog
        self.opener = opener
        self.safe = safe


def _context(new_context, server, lang, theme, **kwargs):
    if theme:
        kwargs["color_scheme"] = theme
    context = new_context(viewport=PHONE, **kwargs)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    return context


def _settle(page, dialog):
    animation_settle.wait_settled(page, target=dialog)


def _fleet_page(new_context, server, lang, theme, **kwargs):
    seed = fx.seed_fleet(server.state_dir)
    context = _context(new_context, server, lang, theme, **kwargs)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=access&frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    return context, page, seed


def _slug(frame_id):
    return frame_id.lower().replace("_", "-")


def _open_via(page, opener, dialog):
    opener.click()
    page.locator(dialog + "[open]").wait_for(state="visible")
    _settle(page, dialog)
    return dialog


def _retire(new_context, server, lang, theme, **kwargs):
    context, page, seed = _fleet_page(new_context, server, lang, theme, **kwargs)
    dialog = "#dlg-retire-" + _slug(seed.owned_id)
    return context, page, dialog, lambda: page.locator("a.fleet-retire__link")


def _reassign(new_context, server, lang, theme, **kwargs):
    context, page, seed = _fleet_page(new_context, server, lang, theme, **kwargs)
    dialog = "#dlg-reassign-" + _slug(seed.owned_id)
    return context, page, dialog, lambda: page.locator(
        ".fleet-block--access li.row", has_text=fx.OWNER_EMAIL).first.locator("a.row-action")


def _reactivate(new_context, server, lang, theme, **kwargs):
    seed = fx.seed_fleet(server.state_dir)
    context = _context(new_context, server, lang, theme, **kwargs)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.retired_id)
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    dialog = "#dlg-reactivate-" + _slug(seed.retired_id)
    return context, page, dialog, lambda: page.locator(".fleet-other a.fleet-action-button")


def _account_rig(server):
    rig = Rig(server)
    conn = fleet_db.connect(server.state_dir)
    try:
        second = fleet_db.add_user(conn, SECOND_CO, "user")
        fleet_db.add_co_manager(conn, rig.seed.owned_id, second, None)
    finally:
        conn.close()
    return rig


def _account_page(new_context, server, lang, theme, who, **kwargs):
    rig = _account_rig(server)
    context = _context(new_context, server, lang, theme, **kwargs)
    context.add_cookies([rig.cookie(who)])
    page = context.new_page()
    page.goto(server.base_url() + "/account")
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    return context, page, _slug(rig.seed.owned_id)


def _manage_access(new_context, server, lang, theme, **kwargs):
    context, page, slug = _account_page(new_context, server, lang, theme, "owner", **kwargs)
    return context, page, "#dlg-access-" + slug, lambda: page.locator(
        'a[href="#dlg-access-%s"]' % slug)


def _leave(new_context, server, lang, theme, **kwargs):
    context, page, slug = _account_page(new_context, server, lang, theme, "co", **kwargs)
    return context, page, "#dlg-leave-" + slug, lambda: page.locator(
        'a[href="#dlg-leave-%s"]' % slug)


def _remove_frame(new_context, server, lang, theme, **kwargs):
    context, page, slug = _account_page(new_context, server, lang, theme, "owner", **kwargs)
    access = "#dlg-access-" + slug
    page.locator('a[href="%s"]' % access).click()
    page.locator(access + "[open]").wait_for(state="visible")
    return context, page, "#dlg-remove-frame-" + slug, lambda: page.locator(
        access + " a.access-remove-frame__link")


def _delete_user(new_context, server, lang, theme, **kwargs):
    seed = fx.seed_fleet(server.state_dir)
    context = _context(new_context, server, lang, theme, **kwargs)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    page.wait_for_function("() => document.readyState === 'complete'")
    row = page.locator("#user-%d" % seed.user_id)
    row.locator("summary").click()
    item = row.locator("a.row-menu__item[href^='#dlg-delete-user']")
    item.wait_for(state="visible")
    return context, page, "#dlg-delete-user-%d" % seed.user_id, lambda: item


CASES = {
    "retire": _retire, "reactivate": _reactivate, "reassign": _reassign,
    "manage-access": _manage_access, "leave": _leave, "remove-frame": _remove_frame,
    "delete-user": _delete_user,
}
# The dialogs whose confirm button destroys something: two actions, safe default focus, the
# danger style and no text input.
GUARDED = ("retire", "reactivate", "leave", "remove-frame", "delete-user")
SENTENCE_BREAK = re.compile(r"[.!?…]\s+\S")


@pytest.fixture
def server(app_server_in_process):
    return app_server_in_process


def _opened(new_context, server, case, lang, theme, **kwargs):
    context, page, dialog, opener = CASES[case](new_context, server, lang, theme, **kwargs)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    _open_via(page, opener(), dialog)
    return context, page, dialog, opener


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_a_dialog_asks_one_question_in_one_sentence_with_detail_behind_a_44px_disclosure(
        new_context, server, case, lang, theme):
    context, page, dialog, _opener = _opened(new_context, server, case, lang, theme)
    where = (case, lang, theme)
    try:
        facts = page.evaluate(_FACTS, dialog)
        assert not SENTENCE_BREAK.search(facts["text"]), (where, facts["text"])
        assert facts["height"] <= facts["vh"] * 0.85 + 1, (where, facts)
        assert not facts["sideways"], (where, facts)
        for more in facts["more"]:
            assert not more["open"], (where, more)
            assert more["summary"] >= 44, (where, more)
        if case != "manage-access":
            assert len(facts["more"]) == 1, (where, facts["more"])
        for ink, flat, name in page.evaluate(_PAIRS, dialog):
            assert skypane_contrast_check.contrast_ratio(ink, flat) >= 4.5, (where, name, ink)
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("case", GUARDED)
def test_a_destructive_dialog_keeps_two_actions_the_safe_default_focus_and_no_text_input(
        new_context, server, case, lang):
    context, page, dialog, _opener = _opened(new_context, server, case, lang, "light")
    try:
        facts = page.evaluate(_FACTS, dialog)
        assert facts["actions"] == 2, (case, lang, facts)
        assert facts["inputs"] == 0, (case, lang, facts)
        assert facts["submitDanger"], (case, lang, facts)
        assert facts["submitText"], (case, lang, facts)
        assert facts["focusOnDismiss"] is True, (case, lang, facts)
    finally:
        context.close()


@pytest.mark.parametrize("case,words", [
    ("retire", ("Retire", "Retirer")), ("reactivate", ("Re-activate", "Réactiver")),
    ("leave", ("Leave this frame", "Quitter ce cadre")),
    ("remove-frame", ("Remove this frame", "Retirer ce cadre")),
    ("delete-user", ("Delete user", "Supprimer l’utilisateur"))])
@pytest.mark.parametrize("lang", LANGS)
def test_the_confirm_button_names_the_action(new_context, server, case, words, lang):
    context, page, dialog, _opener = _opened(new_context, server, case, lang, "light")
    try:
        text = page.evaluate(_FACTS, dialog)["submitText"]
        assert words[0 if lang == "en" else 1] in text, (case, lang, text)
    finally:
        context.close()


@pytest.mark.parametrize("case", ["retire", "reactivate", "reassign", "leave", "remove-frame",
                                  "manage-access"])
def test_escape_closes_the_dialog_and_returns_the_focus_to_its_opener(
        new_context, server, case):
    context, page, dialog, opener = _opened(new_context, server, case, "en", "light")
    try:
        page.keyboard.press("Escape")
        page.wait_for_function("s => !document.querySelector(s).open", arg=dialog)
        page.wait_for_function(
            "el => document.activeElement === el", arg=opener().element_handle(), timeout=5000)
    finally:
        context.close()


def test_escape_closes_the_delete_user_dialog(new_context, server):
    context, page, dialog, _opener = _opened(new_context, server, "delete-user", "en", "light")
    try:
        page.keyboard.press("Escape")
        page.wait_for_function("s => !document.querySelector(s).open", arg=dialog)
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
def test_manage_access_fits_the_phone_without_an_inner_scroll(new_context, server, lang, theme):
    context, page, dialog, _opener = _opened(new_context, server, "manage-access", lang, theme)
    try:
        facts = page.evaluate(_FACTS, dialog)
        assert facts["height"] <= facts["vh"] * 0.85 + 1, (lang, facts)
        assert not facts["innerScroll"] and not facts["bodyScroll"], (lang, facts)
        assert not facts["sideways"], (lang, facts)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        if lang == "fr":
            english = re.findall(
                r"\b(Remove|Owner|Add|Done|Co-manager|Invited|Manage access)\b",
                facts["domText"])
            assert not english, english
    finally:
        context.close()


@pytest.mark.parametrize("case", sorted(CASES))
def test_under_reduced_motion_no_animation_runs_in_an_open_dialog(new_context, server, case):
    context, page, dialog, _opener = _opened(
        new_context, server, case, "en", None, reduced_motion="reduce")
    try:
        assert page.evaluate(_FACTS, dialog)["running"] == 0
        summary = page.locator(dialog + " details > summary")
        if summary.count():
            summary.first.click()
            assert page.evaluate(_FACTS, dialog)["running"] == 0
    finally:
        context.close()
