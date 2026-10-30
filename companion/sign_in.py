"""The Auth0 sign-in handlers moved out of `companion/app.py`'s `Handler`:
the start route, the callback, and sign-out. Packaged as a `SignInMixin`
`Handler` inherits, like `SettingsActionsMixin`.

Never imports `companion.app` (that would be a cycle). The few facts it
needs from the handler (`self._fleet_conn()`, `self._principal()`,
`self._clock()`, `self._next_route_of()`, `self.redirect()`,
`self.send_html()`) are provided by `Handler`.

Logging prints reason codes and numeric user ids only: never a code, a
token, a claim value, an email, a response body or the client secret.
"""
import hmac
import os
import sqlite3
from urllib.parse import parse_qs, urlsplit

from companion import access, auth, login_page, oidc, prefs
from server import fleet_db, fleet_sessions

# Bounded in-memory record of started sign-ins; single process.
ATTEMPTS = oidc.AttemptTable()

_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)
_UNAVAILABLE_STATUS = 503
_STATUS_BY_KIND = {
    oidc.KIND_INCOMPLETE: 400,
    oidc.KIND_EXPIRED: 400,
    oidc.KIND_UNAVAILABLE: 503,
}


def _log(message):
    print("companion: " + message, flush=True)


class SignInMixin:
    # --- configuration and shared page helpers ------------------------

    def _auth0_config(self):
        """The Auth0 settings read from the environment now, or None when
        Auth0 is not configured. Raises oidc.Auth0ConfigError for a
        malformed configuration.
        """
        return oidc.Auth0Config.from_env(os.environ)

    def _auth0_enabled(self):
        try:
            return self._auth0_config() is not None
        except oidc.Auth0ConfigError:
            return False

    def _pre_session_theme(self):
        prefs.set_request_prefs(lang=self._lang_from_request())
        return self._resolved_ui_theme()

    def _config_unavailable(self, exc):
        _log("auth0 configuration error: %s" % exc)
        return self.send_html(_UNAVAILABLE_STATUS, self._unavailable_page())

    # --- start ---------------------------------------------------------

    def _handle_login_auth0_get(self):
        """GET /login/auth0: begin an authorization-code + PKCE flow. A
        GET navigation rather than a form, so the form-action CSP does not
        apply to the hop to the identity provider.
        """
        try:
            cfg = self._auth0_config()
        except oidc.Auth0ConfigError as exc:
            return self._config_unavailable(exc)
        if cfg is None:
            return self.send_html(404, self._not_found_page())
        query = parse_qs(urlsplit(self.path).query)
        next_route = self._next_route_of(query.get("next", [None])[0])
        attempt_id, attempt = ATTEMPTS.create(next_route)
        location = oidc.authorize_url(cfg, attempt.state, attempt.nonce, attempt.challenge)
        return self.redirect(
            location, set_cookie=auth.oidc_attempt_set_cookie_header(attempt_id))

    # --- callback ------------------------------------------------------

    def _handle_callback_get(self):
        """GET /callback. Order: attempt, provider error, state, token
        exchange, ID-token claims, invited-user resolution, and only then a
        session. Every failure is a generic page with no session cookie and
        no durable write; the attempt is consumed on first use and the
        pre-login cookie is always cleared.
        """
        try:
            cfg = self._auth0_config()
        except oidc.Auth0ConfigError as exc:
            return self._config_unavailable(exc)
        if cfg is None:
            return self.send_html(404, self._not_found_page())
        cookie_id = auth.parse_cookies(self.headers.get("Cookie")).get(auth.OIDC_COOKIE_NAME)
        attempt = ATTEMPTS.pop(cookie_id) if cookie_id else None
        try:
            claims = self._verified_claims(cfg, attempt, cookie_id is not None)
            user_id = self._resolve_invited(cfg, claims)
        except oidc.SignInError as exc:
            _log("sign-in failed: %s" % exc.reason)
            return self._sign_in_failed(exc.kind, attempt)
        except _STORE_ERRORS as exc:
            _log("sign-in store error: %s" % type(exc).__name__)
            return self._sign_in_failed(oidc.KIND_UNAVAILABLE, attempt)
        if user_id is None:
            return self.send_html(
                403, login_page.not_invited_page(self._pre_session_theme()),
                set_cookies=[auth.oidc_attempt_clear_cookie_header()])
        try:
            return self._land_signed_in(user_id, claims.email, attempt)
        except _STORE_ERRORS as exc:
            _log("sign-in store error: %s" % type(exc).__name__)
            return self._sign_in_failed(oidc.KIND_UNAVAILABLE, attempt)

    def _verified_claims(self, cfg, attempt, had_cookie):
        """Steps one to five: a live attempt, no provider error, a matching
        state, a token exchange and a token bound to this attempt.
        """
        if attempt is None:
            raise oidc.SignInError(
                "attempt_expired" if had_cookie else "attempt_missing",
                oidc.KIND_EXPIRED if had_cookie else oidc.KIND_INCOMPLETE)
        query = parse_qs(urlsplit(self.path).query)
        if "error" in query:
            raise oidc.SignInError("provider_error")
        code = (query.get("code") or [""])[0]
        state = (query.get("state") or [""])[0]
        if not code or not state:
            raise oidc.SignInError("callback_incomplete")
        if not hmac.compare_digest(state.encode("utf-8"), attempt.state.encode("utf-8")):
            raise oidc.SignInError("state_mismatch")
        token = oidc.exchange_code(cfg, code, attempt.verifier, oidc.requests_post)
        return oidc.validate_id_token(token, cfg, attempt.nonce, self._clock())

    def _resolve_invited(self, cfg, claims):
        """The id of the invited user these claims map to, or None."""
        outcome = fleet_sessions.resolve_login(
            self._fleet_conn(), cfg.issuer, claims.sub, claims.email,
            claims.email_verified, self._clock())
        if outcome.user_id is None:
            _log("sign-in refused: %s" % outcome.reason)
        return outcome.user_id

    def _sign_in_failed(self, kind, attempt):
        next_route = attempt.next_route if attempt is not None else None
        page = login_page.sign_in_error_page(
            kind, self._pre_session_theme(), auth0_enabled=True,
            legacy_enabled=self._legacy_login_on(),
            next_route=self._next_route_of(next_route))
        return self.send_html(
            _STATUS_BY_KIND.get(kind, 400), page,
            set_cookies=[auth.oidc_attempt_clear_cookie_header()])

    def _land_signed_in(self, user_id, email, attempt):
        """Create the session and answer with an interstitial. A 200 page
        with a meta refresh, not a 303: a redirect chain that began on
        another site makes the browser withhold a SameSite=Strict cookie,
        and the page also keeps the callback query out of the next
        request's Referer.
        """
        conn = self._fleet_conn()
        role = fleet_db.get_user_role(conn, user_id)
        if role is None:
            return self._sign_in_failed(oidc.KIND_INCOMPLETE, attempt)
        principal = access.Principal(access.KIND_USER, user_id, email, role)
        old = auth.parse_cookies(self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
        token = auth.new_session_token()
        fleet_sessions.create_session(
            conn, auth.hash_session_token(token), user_id=user_id,
            principal=fleet_sessions.PRINCIPAL_USER, now=self._clock(),
            replace_hash=auth.hash_session_token(old) if old else None)
        if role == access.USER:
            target, label = access.home_for(principal), login_page.CONTINUE_TARGET_ACCOUNT
        else:
            target = self._next_route_of(attempt.next_route) or "/"
            label = login_page.CONTINUE_TARGET_HOME
        _log("signed in: user %d" % user_id)
        page = login_page.interstitial_page(
            login_page.INTERSTITIAL_IN, target, label, self._pre_session_theme())
        return self.send_html(200, page, set_cookies=[
            auth.session_set_cookie_header(token),
            auth.oidc_attempt_clear_cookie_header()])

    # --- sign-out ------------------------------------------------------

    def _handle_logout_post(self):
        """POST /logout: delete the session row first, so replaying the old
        cookie stops working, and clear the cookie. A user principal with
        Auth0 configured is then sent on to Auth0's sign-out through a 200
        interstitial (never a 303 to a foreign origin after a POST); the
        hop failing cannot undo the local logout. A store error answers 503
        and leaves the cookie alone.
        """
        token = auth.parse_cookies(self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
        try:
            principal = self._principal()
            if token:
                fleet_sessions.delete_session(
                    self._fleet_conn(), auth.hash_session_token(token))
        except _STORE_ERRORS:
            return self.send_html(_UNAVAILABLE_STATUS, self._unavailable_page())
        cfg = None
        try:
            cfg = self._auth0_config()
        except oidc.Auth0ConfigError as exc:
            _log("auth0 configuration error: %s" % exc)
        clear = auth.logout_set_cookie_header()
        if cfg is None or principal is None or principal.kind != access.KIND_USER:
            return self.redirect(login_page.LOGIN_ROUTE, set_cookie=clear)
        page = login_page.interstitial_page(
            login_page.INTERSTITIAL_OUT, oidc.logout_url(cfg),
            login_page.CONTINUE_TARGET_SIGN_IN, self._pre_session_theme())
        return self.send_html(200, page, set_cookies=[clear])
