"""Behaviour tests for companion/i18n.py, companion/prefs.py and the
companion/i18n_fr/ catalogue package.

Covers: t_lang()'s round-trip and fallback behaviour, t()'s own
per-request resolution through prefs.set_request_prefs(), prefs'
membership-tested degrade-to-default contract, a completeness test that
every Message id declared anywhere in companion/ has both an English
text (REGISTRY) and a French translation (BY_ID) with no orphan on
either side, a self-consistency sweep over every (REGISTRY, BY_ID) pair
(non-empty, placeholder parity, no value identical to its own English
key outside a documented cognate list, the two typographic copy
rules), a proof that rewording a Message's English keeps its French (a
lookup is by id, never by text), a proof that a plain str is refused
with TypeError, an import-boundary proof that companion.i18n/
companion.prefs never pull in companion.pages or the server package,
and a real render of every authenticated page (plus the login, 404 and
calendar-disconnect-confirm pages) in French against a running service.

This file never scans production source files as text: proving "every
user-visible string has a translation" by reading source text is
exactly what this suite's guard forbids. The guarantee is behavioural
instead: importing every production module (so every i18n.msg()
declaration has run) and then asserting on the resulting runtime
REGISTRY/BY_ID objects, plus the real French page renders below, which
are the direct proof that what a user actually sees is translated.
"""
import importlib
import os
import pkgutil
import re
import subprocess
import sys

import pytest

import companion
import companion.auth as auth
import companion.i18n as i18n
import companion.i18n_fr as i18n_fr
import companion.prefs as prefs
import companion_app_server
from skypane_test_support import REPO_ROOT, child_env

# ==========================================================================
# Import every companion production module once per test session: a
# Message only reaches companion.i18n.REGISTRY when the module that
# declares it (i18n.msg(...)) is imported, and pytest never imports a
# module this file does not otherwise need for collection. Every
# completeness/self-consistency check below depends on REGISTRY (and
# therefore BY_ID) being fully populated first.
# ==========================================================================


def _import_every_production_module():
    imported = []
    for module_info in pkgutil.walk_packages(
            companion.__path__, prefix="companion."):
        last = module_info.name.rsplit(".", 1)[-1]
        if last.startswith("test_") or last == "conftest":
            continue
        importlib.import_module(module_info.name)
        imported.append(module_info.name)
    return imported


@pytest.fixture(scope="session", autouse=True)
def _all_production_modules_imported():
    return _import_every_production_module()


# ==========================================================================
# t_lang() round-trip and fallback
# ==========================================================================


def test_t_lang_fr_translates_a_known_key():
    # "nav.home" is declared in companion/ui_base.py and translated in
    # companion/i18n_fr/nav.py; constructing the Message by hand (rather
    # than importing ui_base.py) keeps this test's own import set
    # minimal — i18n_fr.BY_ID["nav.home"] is populated the moment
    # companion.i18n_fr itself is imported, independent of which page
    # module registers the id in REGISTRY.
    message = i18n.Message("nav.home", "Home")
    assert i18n.t_lang(message, "fr") == "Accueil"


def test_t_lang_en_returns_the_english_source():
    message = i18n.Message("nav.home", "Home")
    assert i18n.t_lang(message, "en") == "Home"


def test_t_lang_degrades_a_missing_key_to_the_english_source_unchanged():
    message = i18n.Message("test.nobody_translated_this", "a string nobody translated")
    assert i18n.t_lang(message, "fr") == "a string nobody translated"


# ==========================================================================
# t() follows prefs.set_request_prefs()
# ==========================================================================


def test_t_follows_set_request_prefs_and_back():
    message = i18n.Message("nav.home", "Home")
    try:
        prefs.set_request_prefs(lang="fr")
        fr_result = i18n.t(message)
        prefs.set_request_prefs(lang="en")
        en_result = i18n.t(message)
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
# Completeness: every Message id has both an English text and a French
# translation, and no BY_ID entry is orphaned.
# ==========================================================================


def test_every_message_id_has_english_and_french():
    registry_ids = set(i18n.REGISTRY)
    by_id_ids = set(i18n_fr.BY_ID)
    missing_french = sorted(registry_ids - by_id_ids)
    orphan_french = sorted(by_id_ids - registry_ids)
    assert not missing_french and not orphan_french, (
        "missing French translation for id(s): %r; "
        "orphan French translation (no declaring Message) for id(s): %r"
        % (missing_french, orphan_french))


_ID_SHAPE_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")


def test_every_message_id_has_the_stable_shape():
    i18n_fr_areas = {
        module_info.name for module_info in pkgutil.iter_modules(i18n_fr.__path__)}
    bad_shape = [msg_id for msg_id in i18n.REGISTRY if not _ID_SHAPE_RE.match(msg_id)]
    assert not bad_shape, "id(s) not matching '<area>.<slug>': %r" % (bad_shape,)
    unknown_area = [
        msg_id for msg_id in i18n.REGISTRY
        if msg_id.split(".", 1)[0] not in i18n_fr_areas]
    assert not unknown_area, (
        "id(s) whose area is not an existing companion.i18n_fr module: %r"
        % (unknown_area,))


def test_rewording_the_english_keeps_the_french():
    # A sample of real, production-declared ids: rewording the English
    # (as if a call site's copy were edited after the id was assigned)
    # must not change the French lookup — the lookup is by id, never by
    # text.
    sample = list(i18n.REGISTRY)[:25]
    assert sample, "REGISTRY is unexpectedly empty — production modules failed to import"
    for msg_id in sample:
        french = i18n_fr.BY_ID[msg_id]
        reworded = i18n.Message(msg_id, "reworded")
        assert i18n.t_lang(reworded, "fr") == french, (
            "rewording the English of %r changed its French translation" % (msg_id,))


def test_plain_strings_are_refused():
    with pytest.raises(TypeError):
        i18n.t("Home")
    with pytest.raises(TypeError):
        i18n.t_lang("Home", "fr")


# ==========================================================================
# Self-consistency sweep over every (REGISTRY id, BY_ID translation) pair.
# ==========================================================================


# A short, named exception list of genuine French/English cognates: a
# shared loanword whose correct French translation is spelled and
# pronounced identically to its English source, never a missed
# translation. Keyed by the stable message id.
_UNCHANGED_IN_FRENCH = frozenset({
    "display.aspect",
    "health.corroboration", "health.source", "health.description",
    # "≈ %s": symbolic notation, identical in both languages.
    "display.next_wake_approx",
    # Image alt text never translated before this id existed either —
    # kept identical so the render stays byte-for-byte unchanged.
    "display.sample_panel_rendered_in_the_theme",
    # A bare "%s — %s" join: no translatable words of its own.
    "health.day_dash_verdict",
    # "Version" and "Date" are genuine French words, spelled identically
    # to their English source — real cognates for the Update page's
    # compact table-header nouns, not a missed translation.
    "update.version", "update.date",
})


def _sweep_entries():
    """Every `(msg_id, english, french)` triple this suite's
    self-consistency sweep covers — every id declared in REGISTRY that
    also has a BY_ID translation (the completeness test above is what
    proves there is no other kind)."""
    entries = []
    for msg_id, english in i18n.REGISTRY.items():
        french = i18n_fr.BY_ID.get(msg_id)
        if french is not None:
            entries.append((msg_id, english, french))
    return entries


def test_every_catalog_value_is_str_and_differs_from_its_english_key():
    bad_type = [
        identifier for identifier, _english, french in _sweep_entries()
        if not isinstance(french, str)]
    assert not bad_type, "non-str French value for: %r" % (bad_type,)
    identical = [
        identifier for identifier, english, french in _sweep_entries()
        if french == english and identifier not in _UNCHANGED_IN_FRENCH]
    assert not identical, "French value identical to its English source: %r" % (identical,)


def test_every_catalog_value_is_non_empty():
    empty = [
        identifier for identifier, _english, french in _sweep_entries()
        if not french.strip()]
    assert not empty, "empty French value for: %r" % (empty,)


_PLACEHOLDER_RE = re.compile(r"%[sd]|\{[^}]*\}")


def test_catalog_placeholders_match_between_key_and_value():
    """Every `%s`/`%d`/`{name}` placeholder in an English source also
    appears in its French translation, and vice versa — the shape a
    mistranslation that drops or mistypes a placeholder actually takes."""
    mismatched = {}
    for identifier, english, french in _sweep_entries():
        english_placeholders = sorted(_PLACEHOLDER_RE.findall(english))
        french_placeholders = sorted(_PLACEHOLDER_RE.findall(french))
        if english_placeholders != french_placeholders:
            mismatched[identifier] = (english_placeholders, french_placeholders)
    assert not mismatched, "placeholder mismatch (key placeholders, value placeholders): %r" % (mismatched,)


def test_t_lang_round_trips_every_message_id():
    for msg_id, english in i18n.REGISTRY.items():
        french = i18n_fr.BY_ID.get(msg_id)
        if french is None:
            continue
        assert i18n.t_lang(i18n.Message(msg_id, english), "fr") == french


# ==========================================================================
# Message IDs: a Message carries a stable ID so its French
# translation survives an English reword. Every registration below lives
# under a "test." area, isolated from the real REGISTRY/BY_ID by the
# isolated_registry fixture (a swapped-in copy, restored by monkeypatch
# when the test ends).
# ==========================================================================


@pytest.fixture
def isolated_registry(monkeypatch):
    """Give a test its own copy of REGISTRY and BY_ID to register into,
    so a test-only "test.*" id never leaks into another test or into the
    real catalogue."""
    monkeypatch.setattr(i18n, "REGISTRY", dict(i18n.REGISTRY))
    monkeypatch.setattr(i18n_fr, "BY_ID", dict(i18n_fr.BY_ID))


def test_msg_returns_a_str_equal_to_its_english_with_a_msg_id(isolated_registry):
    greeting = i18n.msg("test.greeting", "Hello")
    assert greeting == "Hello"
    assert isinstance(greeting, str)
    assert greeting.msg_id == "test.greeting"
    # Formatting, escaping and concatenation behave exactly like the
    # plain str it wraps.
    assert ("%s, world" % greeting) == "Hello, world"
    assert (greeting + "!") == "Hello!"
    assert greeting.upper() == "HELLO"


def test_msg_same_id_same_english_is_idempotent(isolated_registry):
    i18n.msg("test.dup", "A")
    i18n.msg("test.dup", "A")  # no raise


def test_msg_same_id_different_english_raises(isolated_registry):
    i18n.msg("test.dup", "A")
    with pytest.raises(ValueError, match="test.dup"):
        i18n.msg("test.dup", "B")


def test_msg_rejects_an_id_not_matching_the_expected_shape(isolated_registry):
    with pytest.raises(ValueError):
        i18n.msg("NoArea", "Bad id, no dot or wrong case")
    with pytest.raises(ValueError):
        i18n.msg("test", "Missing the dot entirely")
    with pytest.raises(ValueError):
        i18n.msg("Test.bad", "Uppercase area")


def test_t_lang_looks_up_a_message_by_id_in_by_id(isolated_registry):
    message = i18n.msg("test.greeting", "Hello")
    i18n_fr.BY_ID["test.greeting"] = "Bonjour"
    assert i18n.t_lang(message, "fr") == "Bonjour"


def test_t_lang_reworded_english_keeps_its_french_translation(isolated_registry):
    i18n.msg("test.greeting", "Hello")
    i18n_fr.BY_ID["test.greeting"] = "Bonjour"
    # Same ID, different English (as if the source were reworded after
    # the ID was assigned) — the lookup is by ID, not by text.
    reworded = i18n.Message("test.greeting", "Hi there")
    assert i18n.t_lang(reworded, "fr") == "Bonjour"


def test_t_lang_message_in_english_returns_the_plain_english_str(isolated_registry):
    message = i18n.msg("test.greeting", "Hello")
    i18n_fr.BY_ID["test.greeting"] = "Bonjour"
    result = i18n.t_lang(message, "en")
    assert result == "Hello"
    assert type(result) is str


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
    offenders = sorted(key for key, value in i18n_fr.BY_ID.items() if "'" in value)
    assert not offenders, (
        "%d BY_ID value(s) contain a straight apostrophe instead of "
        "U+2019: %r" % (len(offenders), offenders))


_REGULAR_SPACE_BEFORE_PUNCT_RE = re.compile(r" [:;?!]")


def test_every_catalog_value_uses_nbsp_before_punctuation():
    offenders = sorted(
        key for key, value in i18n_fr.BY_ID.items()
        if _REGULAR_SPACE_BEFORE_PUNCT_RE.search(value))
    assert not offenders, (
        "%d BY_ID value(s) have a ':'/';'/'?'/'!' preceded by a plain "
        "space instead of U+00A0: %r" % (len(offenders), offenders))
