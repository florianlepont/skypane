"""Form validation sentences come from the page's own language, not from the browser's: the
invite email field says what is wrong in French on a French page and clears the message as
soon as the person edits it."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login

pytestmark = pytest.mark.browser

_CHECK = (
    "([sel, value]) => { const el = document.querySelector(sel); el.value = value;"
    " const ok = el.checkValidity(); return [ok, el.validationMessage]; }")
_EDIT = (
    "([sel, value]) => { const el = document.querySelector(sel); el.value = value;"
    " el.dispatchEvent(new Event('input', {bubbles: true}));"
    " return [el.checkValidity(), el.validationMessage]; }")
FIELD = "#invite-email"


def _open(new_context, server, lang):
    fx.seed_fleet(server.state_dir)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.wait_for_function("() => document.readyState === 'complete'")
    page.locator(FIELD).wait_for(state="attached")
    return context, page


@pytest.mark.parametrize("lang,missing,invalid", [
    ("fr", "Veuillez saisir une adresse e-mail.",
     "Veuillez saisir une adresse e-mail valide, par exemple nom@exemple.fr."),
    ("en", "Please enter an email address.",
     "Please enter a valid email address, such as name@example.com."),
])
def test_the_invite_email_field_reports_in_the_page_language(
        new_context, app_server_in_process, lang, missing, invalid):
    context, page = _open(new_context, app_server_in_process, lang)
    try:
        assert page.evaluate(_CHECK, [FIELD, ""]) == [False, missing]
        assert page.evaluate(_EDIT, [FIELD, "abc"]) == [False, invalid]
        assert page.evaluate(_EDIT, [FIELD, "a@example.test"]) == [True, ""]
    finally:
        context.close()
