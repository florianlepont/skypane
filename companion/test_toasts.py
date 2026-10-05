"""Behaviour tests for the toast family, against the HTML and assets a real
companion/app.py serves: every flash key's tone and ARIA role, the
title/detail split in both languages, the no-script dismiss link, the
sticky tones (warning, error, pending) that never auto-hide, the Undo
action's no-script round trip, the strict-CSP rule (no style attribute
anywhere), and toast.js's delivery contract.

Every read-only check shares one module-scoped server; the Undo round
trip writes device config, so it gets its own function-scoped one.
"""
import re
import urllib.parse

import pytest

import companion.app as app_module
from companion import flash, i18n, layout, prefs
from companion_app_server import get, http_request, login, served_asset
from companion_markup import flash_toast, parse_html, toast_title_detail
from server import device_config

_SUCCESS = layout.TOAST_TONE_SUCCESS
_INFO = layout.TOAST_TONE_INFO
_WARNING = layout.TOAST_TONE_WARNING
_ERROR = layout.TOAST_TONE_ERROR
_PENDING = layout.TOAST_TONE_PENDING

# One real flash per tone, on the page its producer redirects to.
_ONE_PER_TONE = (
    (_SUCCESS, layout.DISPLAY_ROUTE, flash.FLASH_KEY_CALENDAR_CONNECT_OK),
    (_INFO, layout.HOME_ROUTE, flash.FLASH_KEY_POLL_ALREADY_RUNNING),
    (_WARNING, layout.DISPLAY_ROUTE, flash.FLASH_KEY_CALENDAR_SYNC_FAILED),
    (_ERROR, layout.DISPLAY_ROUTE, flash.FLASH_KEY_SAVE_FAILED),
    (_PENDING, layout.HOME_ROUTE, flash.FLASH_KEY_QUIET_ON),
)
_EXPECTED_ROLE = {
    _SUCCESS: "status", _INFO: "status", _PENDING: "status",
    _WARNING: "alert", _ERROR: "alert",
}
_STICKY_TONES = (_WARNING, _ERROR)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(fake_providers=True)


@pytest.fixture(scope="module")
def session(server):
    return login(server)


def _page(server, session, path, lang="en"):
    cookie = session + "; %s=%s" % (app_module.auth.UI_LANG_COOKIE_NAME, lang)
    status, _headers, body = get(server, path, cookie=cookie)
    assert status == 200, "expected 200 from %s, got %d" % (path, status)
    return body.decode("utf-8")


def _classes(node):
    return node.attrs.get("class", "").split()


def _translated(message, lang):
    try:
        prefs.set_request_prefs(lang=lang)
        return i18n.t(message)
    finally:
        prefs.set_request_prefs(lang="en")


# ==========================================================================
# The tone table
# ==========================================================================


def test_every_flash_key_has_a_tone_and_its_role_follows_the_tone():
    """every FLASH_MESSAGES key has exactly one of the five tones, and its role is alert for
    a warning or error, status otherwise, so a failure and a success never look or sound the
    same"""
    assert set(flash.FLASH_TONES) == set(flash.FLASH_MESSAGES), (
        "keys without a tone: %r; tones without a message: %r" % (
            sorted(set(flash.FLASH_MESSAGES) - set(flash.FLASH_TONES)),
            sorted(set(flash.FLASH_TONES) - set(flash.FLASH_MESSAGES))))
    for key, tone in flash.FLASH_TONES.items():
        assert tone in layout.TOAST_TONES, "%s has unknown tone %r" % (key, tone)
        assert flash.FLASH_ROLES[key] == _EXPECTED_ROLE[tone], (
            "%s (%s) must carry role=%r, got %r"
            % (key, tone, _EXPECTED_ROLE[tone], flash.FLASH_ROLES[key]))
    for key in (flash.FLASH_KEY_SAVE_FAILED, flash.FLASH_KEY_POLL_FAILED,
                flash.FLASH_KEY_QUICK_FAILED, flash.FLASH_KEY_RULE_SAVE_FAILED):
        assert flash.FLASH_TONES[key] == _ERROR, "%s is a failure and must be an error" % key
    for key in (flash.FLASH_KEY_QUIET_ON, flash.FLASH_KEY_LED_OFF, flash.FLASH_KEY_SAVED,
                flash.FLASH_KEY_RULE_ADDED):
        assert flash.FLASH_TONES[key] == _PENDING, (
            "%s only reaches the frame on its next wake and must be pending" % key)


# ==========================================================================
# Served markup per tone
# ==========================================================================


@pytest.mark.parametrize("tone,route,key", _ONE_PER_TONE, ids=[t for t, _r, _k in _ONE_PER_TONE])
def test_served_flash_toast_carries_its_tone_role_glyph_and_dismiss_link(
        server, session, tone, route, key):
    """a real redirect target renders the flash as one toast in the flash region with its
    tone class, its role, its own tone glyph, a spoken tone prefix and a dismiss link back to
    the same page without the flash; success, info and pending are marked to auto-hide and carry
    the timer hairline, pending with the long dwell"""
    body = _page(server, session, "%s?flash=%s&keep=1" % (route, key))
    toast = flash_toast(body)
    assert toast is not None, "expected a flash toast for %s" % key
    assert "toast--%s" % tone in _classes(toast), (
        "expected the %s tone on %s, got %r" % (tone, key, _classes(toast)))
    assert toast.attrs.get("role") == _EXPECTED_ROLE[tone]
    glyph = toast.select_one(".toast__icon use").attrs.get("href")
    expected_glyph = "#icon-toast-trash" if key == flash.FLASH_KEY_CALENDAR_DISCONNECTED else (
        "#icon-toast-%s" % tone)
    assert glyph == expected_glyph, "expected %s's glyph %r, got %r" % (key, expected_glyph, glyph)
    prefix = toast.select_one(".toast__text > .visually-hidden").text()
    assert prefix == i18n.t(layout.TOAST_TONE_PREFIX_TEXT[tone]), (
        "expected the spoken tone prefix, got %r" % prefix)
    dismiss = toast.select_one("a.toast__dismiss")
    assert dismiss.attrs.get("href") == "%s?keep=1" % route, (
        "expected the dismiss link to reload %s without ?flash=, keeping every other "
        "parameter, got %r" % (route, dismiss.attrs.get("href")))
    assert dismiss.attrs.get("aria-label") == i18n.t(layout.TOAST_DISMISS_TEXT)
    autohide = layout.TOAST_AUTOHIDE_ATTR in toast.attrs
    has_timer = bool(toast.select(".toast__timer"))
    if tone in _STICKY_TONES:
        assert not autohide and not has_timer, (
            "a %s toast must never auto-hide: no %s and no timer hairline"
            % (tone, layout.TOAST_AUTOHIDE_ATTR))
    else:
        assert autohide and has_timer, (
            "a %s toast is marked to auto-hide and carries its timer hairline" % tone)
        expected = layout.TOAST_AUTOHIDE_LONG_VALUE if tone == _PENDING else ""
        assert (toast.attrs.get(layout.TOAST_AUTOHIDE_ATTR) or "") == expected, (
            "expected %s's dwell marker %r, got %r"
            % (tone, expected, toast.attrs.get(layout.TOAST_AUTOHIDE_ATTR)))


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_every_flash_key_splits_into_title_and_detail_in_both_languages(server, session, lang):
    """every flash key that has a dash in its translated copy renders that copy as a bold title
    and a separate detail, in English and in French; a dash-less copy is a title alone"""
    for key, message in sorted(flash.FLASH_MESSAGES.items()):
        if key == flash.FLASH_KEY_SAVED:
            # Its detail is computed from the device's state, covered below.
            continue
        body = _page(server, session, "%s?flash=%s" % (layout.DISPLAY_ROUTE, key), lang=lang)
        toast = flash_toast(body)
        assert toast is not None, "%s/%s: expected a flash toast" % (lang, key)
        text = _translated(message, lang)
        if "{" in text:
            title, detail = toast_title_detail(toast)
            assert title and "{" not in title and (detail is None or "{" not in detail), (
                "%s/%s: placeholder left unfilled: %r" % (lang, key, (title, detail)))
            continue
        assert toast_title_detail(toast) == layout.split_toast_message(text), (
            "%s/%s: expected %r, got %r"
            % (lang, key, layout.split_toast_message(text), toast_title_detail(toast)))


def test_saved_flash_shows_the_next_wake_sentence_as_its_detail(server, session):
    """the generic "Saved" flash is pending: its title is "Saved" and its detail is the
    computed next-wake sentence, capitalised as a sentence of its own"""
    toast = flash_toast(_page(
        server, session, "%s?flash=%s" % (layout.DISPLAY_ROUTE, flash.FLASH_KEY_SAVED)))
    title, detail = toast_title_detail(toast)
    assert title == "Saved", "expected the title 'Saved', got %r" % title
    assert detail and detail[0].isupper(), "expected a capitalised detail sentence, got %r" % detail
    assert "toast--pending" in _classes(toast)


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_pending_toasts_autohide_with_the_long_dwell_and_sticky_ones_do_not(
        server, session, lang):
    """in both languages every pending flash key renders data-toast-autohide="long" with a
    timer hairline, while every warning and error flash key renders neither"""
    for key, tone in sorted(flash.FLASH_TONES.items()):
        if tone not in (_PENDING, _WARNING, _ERROR):
            continue
        toast = flash_toast(_page(
            server, session, "%s?flash=%s" % (layout.DISPLAY_ROUTE, key), lang=lang))
        assert toast is not None, "%s/%s: expected a flash toast" % (lang, key)
        if tone == _PENDING:
            assert toast.attrs.get(layout.TOAST_AUTOHIDE_ATTR) == "long", (
                "%s/%s: expected the long dwell marker" % (lang, key))
            assert toast.select(".toast__timer"), "%s/%s: expected a timer hairline" % (lang, key)
        else:
            assert layout.TOAST_AUTOHIDE_ATTR not in toast.attrs, (
                "%s/%s: a %s toast must not auto-hide" % (lang, key, tone))
            assert not toast.select(".toast__timer")


def test_french_toast_speaks_its_tone_and_labels_its_controls_in_french(server, session):
    """a French page's toast carries the French spoken tone prefix, dismiss label and Undo"""
    body = _page(
        server, session, "%s?flash=%s" % (layout.HOME_ROUTE, flash.FLASH_KEY_QUIET_ON),
        lang="fr")
    toast = flash_toast(body)
    # French typography: a non-breaking space before the colon.
    assert '<span class="visually-hidden">En attente : </span>' in body
    assert toast.select_one(".toast__text > .visually-hidden").text() == "En attente :"
    assert toast.select_one("a.toast__dismiss").attrs.get("aria-label") == "Masquer ce message"
    assert toast.select_one("button.toast__action").text() == "Annuler"


def test_unknown_flash_key_renders_no_toast(server, session):
    """a flash value outside the fixed vocabulary renders nothing at all"""
    body = _page(server, session, "/display?flash=%3Cscript%3E")
    assert flash_toast(body) is None
    assert "<script>" not in body


def test_dismiss_link_reloads_the_page_without_the_toast(server, session):
    """following the dismiss link (the no-script path) lands on the same page with no toast,
    and drops `rule=` along with `flash=` while keeping `resolve=`"""
    body = _page(server, session, "/airlines?resolve=ABC&flash=%s&rule=AFR1"
                 % flash.FLASH_KEY_RULE_ADDED)
    href = flash_toast(body).select_one("a.toast__dismiss").attrs["href"]
    assert href == "/airlines?resolve=ABC", "expected only resolve= kept, got %r" % href
    assert flash_toast(_page(server, session, href)) is None


def test_no_toast_carries_a_style_attribute(server, session):
    """strict CSP: no toast, its region or the quick-switch toast template carries an inline
    style attribute; the timer hairline is drawn by classes and a CSS animation alone"""
    for _tone, route, key in _ONE_PER_TONE:
        tree = parse_html(_page(server, session, "%s?flash=%s" % (route, key)))
        roots = (tree.select(".toast-region") + tree.select(".toast")
                 + tree.select("template[%s]" % layout.QUICK_TOAST_TEMPLATE_ATTR))
        assert len(roots) >= 3, "%s: expected the flash region, its toast and the template" % key
        styled = [node for root in roots for node in [root] + root.select("[style]")
                  if "style" in node.attrs]
        assert not styled, "%s: toast elements with a style attribute: %r" % (key, styled)


def test_actions_are_real_controls_that_work_without_scripts(server, session):
    """the quick switches' Undo is a real POST form of the opposite state back to the same
    page, and a coverage gap that closed meanwhile links to Health"""
    for key, route, state in (
            (flash.FLASH_KEY_QUIET_ON, app_module.QUICK_QUIET_HOURS_ROUTE, "off"),
            (flash.FLASH_KEY_DISPLAY_OFF, app_module.QUICK_DISPLAY_ROUTE, "on"),
            (flash.FLASH_KEY_LED_ON, app_module.QUICK_LED_ROUTE, "off")):
        toast = flash_toast(_page(server, session, "/?flash=%s" % key))
        form = toast.select_one("form.toast__action-form")
        assert form.attrs.get("method") == "post" and form.attrs.get("action") == route
        fields = {node.attrs["name"]: node.attrs["value"] for node in form.select("input")}
        assert fields == {"state": state, "return_to": "/"}, "%s: got %r" % (key, fields)
    stale = flash_toast(_page(
        server, session, "/airlines?flash=%s" % flash.FLASH_KEY_MANUAL_PREFIX_STALE))
    assert stale.select_one("a.toast__action").attrs.get("href") == layout.HEALTH_ROUTE
    plain = flash_toast(_page(server, session, "/display?flash=%s" % flash.FLASH_KEY_SAVE_FAILED))
    assert not plain.select(".toast__action"), "a flash with no follow-up offers no action"


def test_undo_round_trip_without_scripts(make_app_server):
    """posting the Undo form a quiet-hours toast offers restores the previous state on disk
    and lands back on the same page with the opposite outcome's toast"""
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    status, headers, _ = http_request(
        server.base_url() + app_module.QUICK_QUIET_HOURS_ROUTE, method="POST", cookie=cookie,
        data=urllib.parse.urlencode({"state": "on", "return_to": "/"}).encode())
    assert status == 303
    _s, _h, body = get(server, headers["Location"], cookie=cookie)
    form = flash_toast(body.decode("utf-8")).select_one("form.toast__action-form")
    fields = {node.attrs["name"]: node.attrs["value"] for node in form.select("input")}
    status, headers, _ = http_request(
        server.base_url() + form.attrs["action"], method="POST", cookie=cookie,
        data=urllib.parse.urlencode(fields).encode())
    assert status == 303 and headers["Location"] == "/?flash=%s" % flash.FLASH_KEY_QUIET_OFF
    assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is False


def test_toast_hooks_render_only_on_the_flash_toast_not_on_persistent_states(server, session):
    """a persistent docked toast (Health's anomaly) carries neither the toast.js hook nor a
    dismiss control nor a timer, so it can never be hidden by script"""
    body = _page(server, session, layout.HEALTH_ROUTE)
    docked = parse_html(body).select(".toast--docked")
    assert docked, "expected the fresh install's Health page to show its anomaly state"
    for node in docked:
        assert layout.TOAST_ATTR not in node.attrs
        assert not node.select(".toast__dismiss") and not node.select(".toast__timer")


# ==========================================================================
# toast.js delivery contract
# ==========================================================================


def test_toast_script_public_es5_and_hook_names(server):
    """GET /static/toast.js is public and cacheable-with-revalidation, ES5-safe and sink-free,
    and names the exact hooks and dwell token the server renders"""
    status, headers, body = http_request(server.base_url() + layout.TOAST_SCRIPT_SRC)
    assert status == 200 and "text/javascript" in headers.get("Content-Type", "")
    assert "no-cache" in headers.get("Cache-Control", "")
    src = served_asset(server, layout.TOAST_SCRIPT_SRC)
    assert src.count('"use strict"') == 1
    for token in ("let ", "const ", "=>", "`", "innerHTML", "outerHTML", "insertAdjacentHTML",
                  "document.write", "eval(", "fetch(", "XMLHttpRequest", "location.href"):
        assert token not in src, "toast.js must not contain %r" % token
    for hook in (layout.TOAST_ATTR, layout.TOAST_AUTOHIDE_ATTR, layout.TOAST_DISMISS_ATTR,
                 "--motion-toast-dwell", "--motion-toast-dwell-long", layout.SKIP_LINK_TARGET_ID):
        assert re.search(r'"%s"' % re.escape(hook), src), "toast.js must name %r" % hook


def test_toast_script_route_src_agree():
    """layout.TOAST_SCRIPT_SRC equals companion.app.TOAST_SCRIPT_ROUTE"""
    assert layout.TOAST_SCRIPT_SRC == app_module.TOAST_SCRIPT_ROUTE
