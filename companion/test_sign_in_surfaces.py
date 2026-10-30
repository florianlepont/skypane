"""Rendering tests for the sign-in surfaces: the login card in each
combination of Auth0 and the shared password, the not-invited refusal,
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
        "auto", auth0_enabled=True, legacy_enabled=False))
    link = doc.select_one("a.login-signin")
    assert link.attrs["href"] == "/login/auth0"
    assert link.text() == "Sign in"
    assert not _has_form_ancestor(link)
    assert not doc.select("input[type=\"password\"]")
    assert not doc.select("details")
    assert _autofocus_count(doc) == 1


def test_sign_in_link_carries_next_only_for_a_same_site_path():
    doc = _doc(login_page.render_login_page(
        "auto", next_route="/flights?x=1", auth0_enabled=True,
        legacy_enabled=False))
    href = doc.select_one("a.login-signin").attrs["href"]
    assert href.startswith("/login/auth0?next=/flights")
    for hostile in ("//evil.example/x", "https://evil.example/", "javascript:1"):
        doc = _doc(login_page.render_login_page(
            "auto", next_route=hostile, auth0_enabled=True,
            legacy_enabled=False))
        assert doc.select_one("a.login-signin").attrs["href"] == "/login/auth0"


def test_both_methods_collapse_the_password_form_into_a_legacy_disclosure():
    doc = _doc(login_page.render_login_page(
        "auto", auth0_enabled=True, legacy_enabled=True))
    details = doc.select_one("details.login-legacy")
    assert "open" not in details.attrs
    assert details.select_one("input[type=\"password\"]") is not None
    assert details.select_one(".banner__pill").text() == "Legacy"
    assert "Use the shared password (legacy)" in details.select_one("summary").text()
    assert details.select_one("button[type=\"submit\"]").text() == "Sign in with password"
    assert "Temporary access for the administrator" in details.text()
    assert not _has_form_ancestor(doc.select_one("a.login-signin"))
    assert _autofocus_count(doc) == 1
    assert "autofocus" in doc.select_one("a.login-signin").attrs


def test_legacy_disclosure_opens_itself_to_show_a_password_error():
    doc = _doc(login_page.render_login_page(
        "auto", error="Incorrect password. Try again.", auth0_enabled=True,
        legacy_enabled=True))
    assert "open" in doc.select_one("details.login-legacy").attrs
    assert doc.select_one(".field-error").text() == "Incorrect password. Try again."
    assert _autofocus_count(doc) == 1


def test_legacy_only_shows_the_open_password_form_as_the_single_action():
    doc = _doc(login_page.render_login_page(
        "auto", auth0_enabled=False, legacy_enabled=True))
    assert not doc.select("a.login-signin")
    assert not doc.select("details")
    assert doc.select_one("input[type=\"password\"]") is not None
    assert not doc.select("button.login-form__submit--quiet")
    assert _autofocus_count(doc) == 1


def test_neither_method_shows_a_not_configured_toast_and_no_control():
    doc = _doc(login_page.render_login_page(
        "auto", auth0_enabled=False, legacy_enabled=False))
    toast = doc.select_one(".toast--docked")
    title, detail = companion_markup.toast_title_detail(toast)
    assert title == "Sign-in is not configured"
    assert not doc.select("a.login-signin")
    assert not doc.select("input")
    assert not doc.select("button")


# --- Refusal, errors, interstitial --------------------------------------

def test_not_invited_page_is_a_generic_warning_with_one_way_back():
    doc = _doc(login_page.not_invited_page("auto"))
    toast = doc.select_one(".toast--docked")
    assert "toast--warning" in toast.attrs["class"]
    assert toast.attrs["role"] == "alert"
    title, detail = companion_markup.toast_title_detail(toast)
    assert title == "No invitation found"
    assert detail == (
        "This account has not been invited to SkyPane. Ask the "
        "administrator for an invitation.")
    back = doc.select_one("a.text-link")
    assert back.attrs["href"] == "/login"
    assert back.text() == "Back to sign in"
    assert not doc.select("a.login-signin")
    assert not doc.select("input")
    assert not doc.select("button")


@pytest.mark.parametrize("kind,title,detail", [
    (login_page.SIGN_IN_ERROR_INCOMPLETE, "Sign-in could not be completed",
     "Start again from this page. If it keeps happening, check that cookies "
     "are enabled."),
    (login_page.SIGN_IN_ERROR_EXPIRED, "Sign-in took too long",
     "Start again from this page."),
    (login_page.SIGN_IN_ERROR_UNAVAILABLE, "Sign-in is not available right now",
     "Try again in a few minutes."),
    (login_page.SIGN_IN_ERROR_PASSWORD_OFF, "Password sign-in is turned off",
     "Use the Sign in button above."),
])
def test_sign_in_error_pages_render_the_approved_wording(kind, title, detail):
    doc = _doc(login_page.sign_in_error_page(
        kind, "auto", auth0_enabled=True, legacy_enabled=False))
    toasts = doc.select(".toast--docked")
    assert len(toasts) == 1
    assert "toast--error" in toasts[0].attrs["class"]
    assert toasts[0].attrs["role"] == "alert"
    assert companion_markup.toast_title_detail(toasts[0]) == (title, detail)
    assert doc.select_one("a.login-signin").attrs["href"] == "/login/auth0"


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
    both = _doc(login_page.render_login_page(
        "auto", auth0_enabled=True, legacy_enabled=True))
    assert "Connectez-vous pour gérer vos cadres SkyPane." in both.text()
    assert both.select_one("a.login-signin").text() == "Se connecter"
    assert both.select_one(".banner__pill").text() == "Ancien accès"
    assert "Utiliser le mot de passe partagé (ancien accès)" in both.text()
    assert "Se connecter avec le mot de passe" in both.text()
    refusal = _doc(login_page.not_invited_page("auto"))
    title, detail = companion_markup.toast_title_detail(
        refusal.select_one(".toast--docked"))
    assert title == "Aucune invitation trouvée"
    assert detail.startswith("Ce compte n’a pas été invité sur SkyPane.")
    assert refusal.select_one("a.text-link").text() == "Retour à la connexion"
    error = _doc(login_page.sign_in_error_page("expired", "auto"))
    assert companion_markup.toast_title_detail(
        error.select_one(".toast--docked")) == (
            "La connexion a pris trop de temps",
            "Recommencez depuis cette page.")
    inter = _doc(login_page.interstitial_page(
        "in", "/", login_page.CONTINUE_TARGET_HOME))
    assert "Connexion en cours…" in inter.text()
    assert inter.select_one("a.text-link").text() == "Continuer vers Accueil"


# --- Defaults are unchanged -------------------------------------------

_LOGIN_BASELINE = {
    "en": {
        "plain": "151f46dcc124274a0485b1ee56e177b8a4aeacb542bfefbfa17abb84d596a8fd",
        "err": "004aacbf2d7f2838a0c049e3dac98dd6e78ea6650308fc0d72f3701d6a72c8cd",
        "lock": "f65e31a9492b9ef0a32f4f6d98d7f1d5b686e1e6fa819ca3cdcd3d434ce1af58",
        "nf": "c569146c8324cd5e3c2c25b49dd567ed7a8f3442008da607cf276651617ab300",
        "nf2": "7afb1cdcdeca413afcf9cdee6a6241c5e3be1434841f179a2bac06349caa48d1",
        "forb": "9f474dfc188f5290489ce64ffae5af6d2357e70b4b35c82efba17fe771804323",
    },
}


def test_original_call_signatures_render_byte_identical_output():
    outputs = {
        "plain": login_page.render_login_page("auto"),
        "err": login_page.render_login_page(
            "dark", error="Bad", next_route="/flights"),
        "lock": login_page.render_login_page(
            "light", lockout_seconds=42, next_route="/x"),
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
    cards = doc.select("section.page-section")
    assert [c.select_one("h2").text() for c in cards] == [
        "Identity", "Preferences", "Frames"]
    identity = cards[0].text()
    assert "ada@example.com" in identity
    assert "User" in identity
    prefs_card = cards[1]
    assert prefs_card.select_one("form[action=\"/ui-lang\"]") is not None
    assert prefs_card.select_one("form[action=\"/ui-theme\"]") is not None
    frames = cards[2]
    assert frames.select_one(".empty-state__heading").text() == (
        "Your frames will appear here")
    assert frames.select_one(".empty-state__body").text() == (
        "Once an administrator pairs a frame to your account it will show up "
        "on this page.")
    logout = doc.select_one("form[action=\"/logout\"]")
    assert logout.attrs["method"] == "post"
    assert logout.select_one("button").text() == "Sign out"
    assert not doc.select("a")


def test_account_page_role_labels_and_escaping():
    from companion.pages import account_page
    admin = _doc(account_page.render(
        account_page.Identity("root@example.com", "admin")))
    assert "Administrator" in admin.select_one("#account-identity").parent.text()
    legacy = _doc(account_page.render(
        account_page.Identity("shared", "admin", legacy=True)))
    assert "Administrator (legacy access)" in legacy.text()
    hostile = account_page.render(
        account_page.Identity("<img src=x onerror=1>@e.com", "user"))
    assert "<img" not in hostile


def test_account_page_renders_in_french():
    from companion.pages import account_page
    prefs.set_request_prefs("fr")
    doc = _doc(account_page.render(account_page.Identity("a@b.fr", "user")))
    assert doc.select_one("h1.page-title").text() == "Compte"
    assert [c.select_one("h2").text() for c in doc.select("section.page-section")] == [
        "Identité", "Préférences", "Cadres"]
    assert "Vos cadres apparaîtront ici" in doc.text()
    assert "Utilisateur" in doc.text()


# --- Shell ---------------------------------------------------------------

def _shell(active="account", **kwargs):
    return layout.page_shell(
        "Account", active, "<p>body</p>", ui_theme="dark",
        health_alert="warn", device_config={"a": 1}, **kwargs)


def test_user_principal_shell_has_one_account_link_and_no_tab_bar():
    prefs.set_request_principal(kind="user", role="user")
    doc = _doc(_shell())
    links = doc.select("nav.sidebar-nav a")
    assert [(a.attrs["href"], a.text()) for a in links] == [("/account", "Account")]
    assert links[0].attrs["aria-current"] == "page"
    assert not doc.select(".nav-group__label")
    assert not doc.select(".nav-notification")
    assert not doc.select("nav.tab-bar")
    assert "has-tab-bar" not in doc.select_one("body").attrs.get("class", "")
    panel = doc.select_one("div.mobile-nav")
    assert panel.select_one("form[action=\"/ui-lang\"]") is not None
    assert panel.select_one("form[action=\"/ui-theme\"]") is not None
    assert panel.select_one("form[action=\"/logout\"]") is not None
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


@pytest.mark.parametrize("surface", [
    ".sidebar-footer form.logout-form", ".mobile-nav__footer form.logout-form"])
def test_legacy_admin_gets_a_neutral_pill_before_sign_out(surface):
    prefs.set_request_principal(kind="legacy-admin", role="admin")
    doc = _doc(_shell(active="home"))
    form = doc.select_one(surface)
    first, second = [c for c in form.children if hasattr(c, "tag")][:2]
    assert "banner__pill" in first.attrs["class"].split()
    assert first.text() == "Legacy access"
    assert first.attrs["title"] == "Signed in with the shared password"
    assert second.tag == "button"
    assert doc.select("nav.sidebar-nav a")[0].attrs["href"] == "/"
    assert doc.select("nav.tab-bar")


@pytest.mark.parametrize("principal", [
    None, ("user", "user"), ("admin", "admin")])
def test_other_principals_get_no_legacy_pill(principal):
    if principal:
        prefs.set_request_principal(kind=principal[0], role=principal[1])
    assert not _doc(_shell(active="home")).select(".logout-form .banner__pill")


def test_legacy_pill_is_translated():
    prefs.set_request_principal(kind="legacy-admin", role="admin")
    prefs.set_request_prefs("fr")
    pill = _doc(_shell(active="home")).select_one(".logout-form .banner__pill")
    assert pill.text() == "Ancien accès"
    assert pill.attrs["title"] == "Connecté avec le mot de passe partagé"


def test_unrecognised_principal_clears_to_default():
    prefs.set_request_principal(kind="user", role="user")
    prefs.set_request_principal(kind="bogus", role="user")
    assert prefs.current_principal() is None


_SHELL_BASELINE_DIGEST = (
    "3602249591834cf4e1870e61219342ed411ef258dd75114fbab67d5cc282b675")


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
