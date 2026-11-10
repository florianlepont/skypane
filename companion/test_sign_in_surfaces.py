"""Rendering tests for the sign-in surfaces: the login card in each
presence of Auth0, the not-invited refusal,
the generic sign-in errors, the interstitial, the Account page and the
user-role shell. Every assertion parses the served markup.
"""
import hashlib

import pytest

import companion_markup
from companion import i18n, layout, login_page, prefs


@pytest.fixture(autouse=True)
def _reset_request_state():
    prefs.set_request_prefs("en")
    prefs.set_request_principal(None)
    yield
    prefs.set_request_prefs("en")
    prefs.set_request_principal(None)


def _doc(html):
    return companion_markup.parse_html(html)


def _has_form_ancestor(node):
    parent = node.parent
    while parent is not None:
        if parent.tag == "form":
            return True
        parent = parent.parent
    return False


def _autofocus_count(doc):
    return len([n for n in doc._descendants() if "autofocus" in n.attrs])


# --- Login card -----------------------------------------------------------

def test_auth0_only_shows_a_plain_get_link_and_no_password_control():
    doc = _doc(login_page.render_login_page(
        "auto", auth0_enabled=True))
    link = doc.select_one("a.login-signin")
    assert link.attrs["href"] == "/login/auth0"
    assert link.text() == "Sign in"
    assert not _has_form_ancestor(link)
    assert not doc.select("input[type=\"password\"]")
    assert not doc.select("details")
    assert _autofocus_count(doc) == 1


def test_sign_in_link_carries_next_only_for_a_same_site_path():
    doc = _doc(login_page.render_login_page(
        "auto", next_route="/flights?x=1", auth0_enabled=True))
    href = doc.select_one("a.login-signin").attrs["href"]
    assert href.startswith("/login/auth0?next=/flights")
    for hostile in ("//evil.example/x", "https://evil.example/", "javascript:1"):
        doc = _doc(login_page.render_login_page(
            "auto", next_route=hostile, auth0_enabled=True))
        assert doc.select_one("a.login-signin").attrs["href"] == "/login/auth0"


def test_without_auth0_the_card_shows_a_not_configured_toast_and_no_control():
    doc = _doc(login_page.render_login_page(
        "auto", auth0_enabled=False))
    toast = doc.select_one(".toast--docked")
    title, detail = companion_markup.toast_title_detail(toast)
    assert title == "Sign-in is not configured"
    assert not doc.select("a.login-signin")
    assert not doc.select("input")
    assert not doc.select("button")


# --- Refusal, errors, interstitial --------------------------------------

def test_not_invited_page_is_a_generic_warning_with_two_ways_on():
    doc = _doc(login_page.not_invited_page("auto"))
    toast = doc.select_one(".toast--docked")
    assert "toast--warning" in toast.attrs["class"]
    assert toast.attrs["role"] == "alert"
    title, detail = companion_markup.toast_title_detail(toast)
    assert title == "This account can't sign in"
    assert detail == (
        "It has not been invited to SkyPane, or its access was turned off. "
        "Ask the administrator, or sign in with the address you were invited "
        "with.")
    other = doc.select_one("a.login-signin")
    assert other.attrs["href"] == "/login/auth0?prompt=login"
    assert other.text() == "Use another account"
    back = doc.select_one("a.text-link")
    assert back.attrs["href"] == "/login"
    assert back.text() == "Back to sign in"
    assert _autofocus_count(doc) == 1
    assert not doc.select("input")
    assert not doc.select("button")


def test_unverified_email_page_is_its_own_warning_with_a_retry():
    doc = _doc(login_page.unverified_email_page("auto"))
    toast = doc.select_one(".toast--docked")
    assert "toast--warning" in toast.attrs["class"]
    assert toast.attrs["role"] == "alert"
    assert companion_markup.toast_title_detail(toast) == (
        "Confirm your email address",
        "Your sign-in account has not confirmed its email address yet. Open "
        "the confirmation message in your inbox, then sign in again.")
    again = doc.select_one("a.login-signin")
    assert again.attrs["href"] == "/login/auth0"
    assert again.text() == "Sign in again"
    assert "Ask the administrator to resend it." in doc.text()
    assert "invited" not in doc.text()
    assert _autofocus_count(doc) == 1


@pytest.mark.parametrize("kind,tone,title,detail", [
    (login_page.SIGN_IN_ERROR_INCOMPLETE, "error", "Sign-in could not be completed",
     "Press Sign in to try again. If it keeps happening, check that cookies "
     "are enabled."),
    (login_page.SIGN_IN_ERROR_EXPIRED, "error", "Sign-in took too long",
     "Press Sign in to start again."),
    (login_page.SIGN_IN_ERROR_PROVIDER, "info", "Sign-in was cancelled",
     "Press Sign in whenever you are ready."),
    (login_page.SIGN_IN_ERROR_UNAVAILABLE, "error", "Sign-in is not available right now",
     "Try again in a few minutes. If it lasts, tell the administrator."),
    (login_page.SIGN_IN_ERROR_THROTTLED, "warning", "Too many attempts",
     "Wait a minute, then press Sign in."),
])
def test_sign_in_error_pages_render_the_approved_wording(kind, tone, title, detail):
    doc = _doc(login_page.sign_in_error_page(
        kind, "auto", auth0_enabled=True))
    toasts = doc.select(".toast--docked")
    assert len(toasts) == 1
    assert "toast--%s" % tone in toasts[0].attrs["class"]
    assert companion_markup.toast_title_detail(toasts[0]) == (title, detail)
    assert doc.select_one("a.login-signin").attrs["href"] == "/login/auth0"


def test_first_visit_hint_shows_on_the_plain_card_only():
    hint = "First visit? Use the email address you were invited with."
    plain = _doc(login_page.render_login_page("auto", auth0_enabled=True))
    assert hint in plain.text()
    for kind in (login_page.SIGN_IN_ERROR_INCOMPLETE, login_page.SIGN_IN_ERROR_THROTTLED):
        assert hint not in _doc(login_page.sign_in_error_page(kind, "auto")).text()
    assert hint not in _doc(login_page.not_invited_page("auto")).text()
    assert hint not in _doc(login_page.render_login_page("auto")).text()


def test_unknown_error_kind_falls_back_to_the_incomplete_wording():
    doc = _doc(login_page.sign_in_error_page("<script>x</script>", "auto"))
    toast = doc.select_one(".toast--docked")
    assert companion_markup.toast_title_detail(toast)[0] == (
        "Sign-in could not be completed")
    assert "<script>x" not in login_page.sign_in_error_page(
        "<script>x</script>", "auto")


@pytest.mark.parametrize("kind,title,line", [
    ("in", "Signing in", "Signing you in…"),
    ("out", "Signing out", "Signing you out…"),
])
def test_interstitial_is_a_script_free_meta_refresh_with_a_fallback_link(
        kind, title, line):
    html = login_page.interstitial_page(
        kind, "/account?a=1&b=2", login_page.CONTINUE_TARGET_ACCOUNT)
    doc = _doc(html)
    refresh = doc.select_one("meta[http-equiv=\"refresh\"]")
    assert refresh.attrs["content"] == "0;url=/account?a=1&b=2"
    assert "&amp;" in html
    assert doc.select_one("meta[name=\"referrer\"]").attrs["content"] == "no-referrer"
    assert not doc.select("script")
    assert doc.select_one("title").text().startswith(title)
    status = doc.select_one("[role=\"status\"]")
    assert line in status.text()
    fallback = status.select_one("a.text-link")
    assert fallback.attrs["href"] == "/account?a=1&b=2"
    assert fallback.text() == "Continue to Account"


def test_interstitial_escapes_the_target_and_refuses_unsafe_schemes():
    html = login_page.interstitial_page(
        "out", 'https://x.example/v2/logout?a="><b>',
        login_page.CONTINUE_TARGET_SIGN_IN)
    assert '"><b>' not in html
    for bad in ("javascript:alert(1)", "//evil.example", "data:text/html,x", ""):
        with pytest.raises(ValueError):
            login_page.interstitial_page("in", bad, login_page.CONTINUE_TARGET_HOME)


# --- French --------------------------------------------------------------

def test_new_login_surfaces_render_the_approved_french():
    prefs.set_request_prefs("fr")
    card = _doc(login_page.render_login_page("auto", auth0_enabled=True))
    assert "Connectez-vous pour gérer vos cadres SkyPane." in card.text()
    assert card.select_one("a.login-signin").text() == "Se connecter"
    assert not card.select("input")
    refusal = _doc(login_page.not_invited_page("auto"))
    title, detail = companion_markup.toast_title_detail(
        refusal.select_one(".toast--docked"))
    assert title == "Ce compte ne peut pas se connecter"
    assert detail.startswith("Il n’a pas été invité sur SkyPane")
    assert refusal.select_one("a.login-signin").text() == "Utiliser un autre compte"
    assert refusal.select_one("a.text-link").text() == "Retour à la connexion"
    unverified = _doc(login_page.unverified_email_page("auto"))
    assert companion_markup.toast_title_detail(
        unverified.select_one(".toast--docked"))[0] == "Confirmez votre adresse e-mail"
    assert unverified.select_one("a.login-signin").text() == "Se reconnecter"
    assert "Première visite ?" in card.text()
    error = _doc(login_page.sign_in_error_page("expired", "auto"))
    assert companion_markup.toast_title_detail(
        error.select_one(".toast--docked")) == (
            "La connexion a pris trop de temps",
            "Appuyez sur Se connecter pour recommencer.")
    inter = _doc(login_page.interstitial_page(
        "in", "/", login_page.CONTINUE_TARGET_HOME))
    assert "Connexion en cours…" in inter.text()
    assert inter.select_one("a.text-link").text() == "Continuer vers Accueil"


# --- Defaults are unchanged -------------------------------------------

_LOGIN_BASELINE = {
    "en": {
        "nf": "231fc4a0e5745609e4fb267e56b90ff706fac8b7101b72ebf1d4ae9e0981eb7c",
        "nf2": "231fc4a0e5745609e4fb267e56b90ff706fac8b7101b72ebf1d4ae9e0981eb7c",
        "forb": "45ec3da162c07fa8de7f7dc84539e8ae113968e07594b64895125273fd644ac8",
    },
}


def test_error_pages_render_byte_identical_output():
    outputs = {
        "nf": login_page.not_found_page("auto", None),
        "nf2": login_page.not_found_page("auto", "warn"),
        "forb": login_page.forbidden_page("dark", None),
    }
    for name, html in outputs.items():
        digest = hashlib.sha256(html.encode()).hexdigest()
        assert digest == _LOGIN_BASELINE["en"][name], name


def test_every_new_message_has_a_french_translation():
    import companion.i18n_fr as i18n_fr
    account_ids = [m for m in i18n.REGISTRY if m.startswith("account.")]
    assert account_ids
    assert all(m in i18n_fr.BY_ID for m in account_ids)


# --- Account page -----------------------------------------------------

def test_account_page_shows_identity_preferences_frames_and_sign_out():
    from companion.pages import account_page
    html = account_page.render(account_page.Identity("ada@example.com", "user"))
    doc = _doc(html)
    assert doc.select_one("h1.page-title").text() == "Account"
    cards = [c for c in doc.select("section.group-block") if c.select("h2")]
    assert [c.select_one("h2").text() for c in cards] == [
        "My frames", "Identity", "Preferences"]
    identity = cards[1].text()
    assert "ada@example.com" in identity
    assert "User" in identity
    prefs_card = cards[2]
    assert prefs_card.select_one("form[action=\"/ui-lang\"]") is not None
    assert prefs_card.select_one("form[action=\"/ui-theme\"]") is not None
    frames = cards[0]
    assert frames.select_one(".empty-state__heading").text() == (
        "Your frames will appear here")
    assert frames.select_one(".empty-state__body").text() == (
        "The pairing code is shown on your frame's screen.")
    add = frames.select("a")
    assert [(a.text(), a.attrs["href"]) for a in add] == [
        ("Add your frame", "/pair-frame")]
    logout = doc.select_one("form[action=\"/logout\"]")
    assert logout.attrs["method"] == "post"
    assert logout.select_one("button").text() == "Sign out"
    assert [a.attrs["href"] for a in doc.select("a")] == ["/pair-frame"]


def test_account_page_role_labels_and_escaping():
    from companion.pages import account_page
    admin = _doc(account_page.render(
        account_page.Identity("root@example.com", "admin")))
    assert "Administrator" in admin.select_one("#account-identity").parent.text()
    hostile = account_page.render(
        account_page.Identity("<img src=x onerror=1>@e.com", "user"))
    assert "<img" not in hostile


def test_account_page_renders_in_french():
    from companion.pages import account_page
    prefs.set_request_prefs("fr")
    doc = _doc(account_page.render(account_page.Identity("a@b.fr", "user")))
    assert doc.select_one("h1.page-title").text() == "Compte"
    assert [c.select_one("h2").text() for c in doc.select("section.group-block") if c.select("h2")] == [
        "Mes cadres", "Identité", "Préférences"]
    assert "Vos cadres apparaîtront ici" in doc.text()
    assert "Ajouter votre cadre" in doc.text()
    assert "Utilisateur" in doc.text()


# --- Shell ---------------------------------------------------------------

def _shell(active="account", **kwargs):
    return layout.page_shell(
        "Account", active, "<p>body</p>", ui_theme="dark",
        health_alert="warn", device_config={"a": 1}, **kwargs)


def test_user_principal_shell_has_only_the_account_link_and_no_tab_bar():
    prefs.set_request_principal(kind="user", role="user")
    doc = _doc(_shell())
    links = doc.select("nav.sidebar-nav a")
    assert [(a.attrs["href"], a.text()) for a in links] == [("/account", "Account")]
    assert links[0].attrs["aria-current"] == "page"
    assert not doc.select(".nav-group__label")
    assert not doc.select(".nav-notification")
    assert not doc.select("nav.tab-bar")
    assert "has-tab-bar" not in doc.select_one("body").attrs.get("class", "")
    header = doc.select_one("header.site-header")
    assert not header.select("form")
    assert not header.select("button")
    assert not doc.select("div.mobile-nav")
    assert doc.select(".brand__link")
    for brand in doc.select(".brand__link"):
        assert brand.attrs["href"] == "/account"


def test_user_principal_shell_links_only_to_reachable_destinations():
    prefs.set_request_principal(kind="user", role="user")
    doc = _doc(_shell(active=""))
    hrefs = {a.attrs["href"] for a in doc.select("a") if "href" in a.attrs}
    assert all(h == "/account" or h.startswith("#") for h in hrefs), hrefs
    assert not doc.select("a[href=\"/\"]")
    inactive = doc.select_one("nav.sidebar-nav a")
    assert "aria-current" not in inactive.attrs


def test_unrecognised_principal_clears_to_default():
    prefs.set_request_principal(kind="user", role="user")
    prefs.set_request_principal(kind="bogus", role="user")
    assert prefs.current_principal() is None


_SHELL_BASELINE_DIGEST = (
    "edb344a5d1df0fc77690af55a137f74df95113f32ec0c1ba6f9b913d8b93ddcd")


def test_shell_without_a_principal_is_byte_identical_to_before():
    digests = []
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang)
        for active in (
                "home", "display", "flights", "airlines", "health", "device",
                "update", ""):
            for device_config in (None, {"a": 1}):
                for alert in (None, "warn"):
                    html = layout.page_shell(
                        "T", active, "<p>b</p>", ui_theme="dark",
                        health_alert=alert, device_config=device_config)
                    digests.append(hashlib.sha256(html.encode()).hexdigest())
    assert hashlib.sha256("".join(digests).encode()).hexdigest() == (
        _SHELL_BASELINE_DIGEST)
