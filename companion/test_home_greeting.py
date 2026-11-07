"""The Home greeting's first name: read from the e-mail local part only when it has a
separator, title-cased, and never an address or a bare handle."""
import pytest

from companion import prefs
from companion.pages import home_greeting


@pytest.mark.parametrize("email, expected", [
    ("florian.lepont@example.com", "Florian"),
    ("JEAN_PIERRE@example.com", "Jean"),
    ("marie-claire@example.com", "Marie"),
    ("ana+frames@example.com", "Ana"),
    ("marcoalfinito@example.com", ""),
    ("owner@example.com", ""),
    ("x.y@example.com", ""),
    ("1234.name@example.com", ""),
    ("<b>.x@example.com", ""),
    (".@example.com", ""),
    ("", ""),
    (None, ""),
])
def test_first_name_needs_a_separator_and_letters(email, expected):
    assert home_greeting.first_name(email) == expected


@pytest.mark.parametrize("lang, email, default", [
    ("en", "florian.lepont@example.com", "Hello, Florian"),
    ("fr", "florian.lepont@example.com", "Bonjour Florian"),
    ("en", "marcoalfinito@example.com", "Hello"),
    ("fr", "", "Bonjour"),
])
def test_the_heading_names_the_page_and_the_greeting_is_a_quiet_line(lang, email, default):
    prefs.set_request_prefs(lang=lang)
    prefs.set_request_principal("admin", "admin", email)
    try:
        html = home_greeting.title_html()
    finally:
        prefs.set_request_principal(None)
        prefs.set_request_prefs(lang="en")
    assert "<span data-greeting-text>%s</span>" % default in html
    assert '<h1 class="page-title visually-hidden">%s</h1>' % (
        "Home" if lang == "en" else "Accueil") in html
    assert html.count("<h1") == 1
    assert "@" not in html
