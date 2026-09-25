"""Behaviour tests for companion/i18n.py, companion/prefs.py and the
companion/i18n_fr/ catalogue package.

Covers: t_lang()'s round-trip and fallback behaviour, t()'s own
per-request resolution through prefs.set_request_prefs(), prefs'
membership-tested degrade-to-default contract, the catalogue's
completeness against its own sibling modules, a self-consistency sweep
over every catalogue entry (non-empty, placeholder parity, no value
identical to its own English key outside a documented cognate list, the
two typographic copy rules), an import-boundary proof that
companion.i18n/companion.prefs never pull in companion.pages or the
server package, and a real render of every authenticated page (plus the
login, 404 and calendar-disconnect-confirm pages) in French against a
running service.

This file never scans production source files as text: proving "every
user-visible string has a translation" by reading source text is
exactly what this suite's guard forbids. The guarantee is behavioural
instead: the catalogue's own internal
consistency (no empty value, matching %s/%d/{...} placeholders between a
key and its translation, a working round trip through t_lang()) plus the
real French page renders below, which are the direct proof that what a
user actually sees is translated.
"""
import os
import re
import subprocess
import sys

import pytest

import companion.auth as auth
import companion.i18n as i18n
import companion.i18n_fr as i18n_fr
import companion.i18n_fr.common as i18n_fr_common
import companion.i18n_fr.nav as i18n_fr_nav
import companion.prefs as prefs
import companion_app_server
from skypane_test_support import REPO_ROOT, child_env

# ==========================================================================
# t_lang() round-trip and fallback
# ==========================================================================


def test_t_lang_fr_translates_a_known_key():
    assert i18n.t_lang("Home", "fr") == "Accueil"


def test_t_lang_en_returns_the_english_source():
    assert i18n.t_lang("Home", "en") == "Home"


def test_t_lang_degrades_a_missing_key_to_the_english_source_unchanged():
    text = "a string nobody translated"
    assert i18n.t_lang(text, "fr") == text


# ==========================================================================
# t() follows prefs.set_request_prefs()
# ==========================================================================


def test_t_follows_set_request_prefs_and_back():
    try:
        prefs.set_request_prefs(lang="fr")
        fr_result = i18n.t("Home")
        prefs.set_request_prefs(lang="en")
        en_result = i18n.t("Home")
    finally:
        prefs.set_request_prefs(lang="en")
    assert fr_result == "Accueil"
    assert en_result == "Home"


# ==========================================================================
# prefs: membership-tested degrade-to-default contract
# ==========================================================================


def test_prefs_unknown_lang_degrades_to_en():
    try:
        prefs.set_request_prefs(lang="de")
        got = prefs.current_lang()
    finally:
        prefs.set_request_prefs(lang="en")
    assert got == "en"


# ==========================================================================
# Catalogue completeness against its own sibling modules
# ==========================================================================


def test_catalog_contains_every_key_defined_in_common():
    missing = [k for k in i18n_fr_common.CATALOG if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from merged CATALOG: %r" % (missing,)


def test_catalog_contains_every_key_defined_in_nav():
    missing = [k for k in i18n_fr_nav.CATALOG if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from merged CATALOG: %r" % (missing,)


# A short, named exception list of genuine French/English cognates: a
# shared loanword whose correct French translation is spelled and
# pronounced identically to its English key, never a missed translation.
_UNCHANGED_IN_FRENCH = frozenset(
    {"Corroboration", "Source", "Description", "Notifications", "Aspect"})


def test_every_catalog_value_is_str_and_differs_from_its_english_key():
    bad_type = [k for k, v in i18n_fr.CATALOG.items() if not isinstance(v, str)]
    assert not bad_type, "non-str CATALOG values for keys: %r" % (bad_type,)
    identical = [
        k for k, v in i18n_fr.CATALOG.items()
        if v == k and k not in _UNCHANGED_IN_FRENCH]
    assert not identical, "CATALOG values identical to their English key: %r" % (identical,)


def test_every_catalog_value_is_non_empty():
    empty = [k for k, v in i18n_fr.CATALOG.items() if not v.strip()]
    assert not empty, "CATALOG value(s) empty for keys: %r" % (empty,)


_PLACEHOLDER_RE = re.compile(r"%[sd]|\{[^}]*\}")


def test_catalog_placeholders_match_between_key_and_value():
    """Every `%s`/`%d`/`{name}` placeholder in an English catalogue key
    also appears in its French translation, and vice versa — the shape a
    mistranslation that drops or mistypes a placeholder actually takes."""
    mismatched = {}
    for key, value in i18n_fr.CATALOG.items():
        key_placeholders = sorted(_PLACEHOLDER_RE.findall(key))
        value_placeholders = sorted(_PLACEHOLDER_RE.findall(value))
        if key_placeholders != value_placeholders:
            mismatched[key] = (key_placeholders, value_placeholders)
    assert not mismatched, "placeholder mismatch (key placeholders, value placeholders): %r" % (mismatched,)


def test_t_lang_round_trips_every_catalog_key():
    for key, value in i18n_fr.CATALOG.items():
        assert i18n.t_lang(key, "fr") == value


# ==========================================================================
# Source-level import-boundary check: companion.i18n/companion.prefs stay
# leaf modules, never reaching into companion.pages or the server tree.
# Proven by importing them in a fresh interpreter and inspecting the
# resulting sys.modules — not by reading either module's own source text.
# ==========================================================================


def test_i18n_and_prefs_import_neither_pages_nor_server():
    script = (
        "import sys\n"
        "import companion.i18n\n"
        "import companion.prefs\n"
        "bad = [n for n in sys.modules "
        "if n == 'companion.pages' or n.startswith('companion.pages.')]\n"
        "assert not bad, bad\n"
        "bad = [n for n in sys.modules "
        "if n == 'server' or n.startswith('server.')]\n"
        "assert not bad, bad\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        env=child_env(dict(os.environ)), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# ==========================================================================
# Real French renders, over a running service. This is the direct
# behavioural proof that a real user sees translated copy — the thing the
# retired source scans could only infer indirectly.
# ==========================================================================


@pytest.fixture(scope="module")
def french_render_server(tmp_path_factory):
    server = companion_app_server.InProcessAppServer(
        str(tmp_path_factory.mktemp("i18n-render") / "state"))
    yield server
    server.stop()


@pytest.fixture(scope="module")
def french_session(french_render_server):
    """A logged-in session cookie, and the same cookie with the French
    UI-language cookie appended — shared read-only across every render
    check in this module."""
    session_cookie = companion_app_server.login(french_render_server)
    lang_cookie = "%s; %s=fr" % (session_cookie, auth.UI_LANG_COOKIE_NAME)
    return session_cookie, lang_cookie


_FORMAT_ARTEFACT_RE = re.compile(r"%s|%d|\{\}")


def _no_format_artefact(body_text):
    return not _FORMAT_ARTEFACT_RE.search(body_text)


_FRENCH_PAGE_CASES = (
    ("/", "Accueil", "Home"),
    ("/display", "Affichage", "Display"),
    ("/device", "Appareil", "Device"),
    ("/flights", "Vols", "Flights"),
    ("/airlines", "Compagnies", "Airlines"),
    ("/health", "État", "Health"),
)


@pytest.mark.parametrize(
    "route, needle, label", _FRENCH_PAGE_CASES,
    ids=[label for _route, _needle, label in _FRENCH_PAGE_CASES])
def test_authenticated_page_renders_in_french(route, needle, label, french_render_server, french_session):
    _session_cookie, lang_cookie = french_session
    status, _headers, body = companion_app_server.http_request(
        french_render_server.base_url() + route, cookie=lang_cookie)
    text = body.decode("utf-8", "replace")
    assert status == 200, "GET %s under lang=fr returned %d, expected 200" % (route, status)
    assert needle in text, "GET %s under lang=fr did not contain %r" % (route, needle)
    assert _no_format_artefact(text), "GET %s under lang=fr contains a stray %%s/%%d/{} artefact" % (route,)


def test_login_page_renders_in_french(french_render_server):
    status, _headers, body = companion_app_server.http_request(
        french_render_server.base_url() + "/login",
        cookie="%s=fr" % auth.UI_LANG_COOKIE_NAME)
    text = body.decode("utf-8", "replace")
    assert status == 200
    needle = "Connectez-vous pour gérer les réglages de cet appareil."
    assert needle in text
    assert _no_format_artefact(text)


def test_404_page_renders_in_french(french_render_server, french_session):
    _session_cookie, lang_cookie = french_session
    status, _headers, body = companion_app_server.http_request(
        french_render_server.base_url() + "/this-route-does-not-exist", cookie=lang_cookie)
    text = body.decode("utf-8", "replace")
    assert status == 404
    needle = "Page introuvable."
    assert needle in text
    assert _no_format_artefact(text)


def test_calendar_disconnect_confirm_page_renders_in_french(french_render_server, french_session):
    _session_cookie, lang_cookie = french_session
    status, _headers, body = companion_app_server.http_request(
        french_render_server.base_url() + "/settings/calendar/disconnect",
        method="POST", cookie=lang_cookie, data=b"")
    text = body.decode("utf-8", "replace")
    assert status == 200, (
        "a bare POST /settings/calendar/disconnect under lang=fr returned "
        "%d, expected 200 (the confirm page)" % status)
    needle = "Déconnecter le calendrier ?"
    assert needle in text
    assert _no_format_artefact(text)


# ==========================================================================
# Two mechanical copy rules, checked over every catalogue value
# directly (the imported dict, never source text).
# ==========================================================================


def test_every_catalog_value_uses_the_typographic_apostrophe():
    offenders = sorted(key for key, value in i18n_fr.CATALOG.items() if "'" in value)
    assert not offenders, (
        "%d CATALOG value(s) contain a straight apostrophe instead of "
        "U+2019: %r" % (len(offenders), offenders))


_REGULAR_SPACE_BEFORE_PUNCT_RE = re.compile(r" [:;?!]")


def test_every_catalog_value_uses_nbsp_before_punctuation():
    offenders = sorted(
        key for key, value in i18n_fr.CATALOG.items()
        if _REGULAR_SPACE_BEFORE_PUNCT_RE.search(value))
    assert not offenders, (
        "%d CATALOG value(s) have a ':'/';'/'?'/'!' preceded by a plain "
        "space instead of U+00A0: %r" % (len(offenders), offenders))
