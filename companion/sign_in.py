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
import datetime
import hmac
import os
import sqlite3
from urllib.parse import parse_qs, urlsplit

from companion import (
    access, auth, battery, co_managers, console_pairing, device_scope, flash, i18n,
    layout, login_page, oidc, prefs, ui_shell)
from companion.pages import account_page, co_managers_card, frame_name_page
from server import fleet_db, fleet_sessions, hardware, state_store

# Shown as the Email value when the principal carries no address.
_NO_EMAIL = "\u2014"
ACCOUNT_ROUTE = "/account"

# Bounded in-memory record of started sign-ins; single process.
ATTEMPTS = oidc.AttemptTable()
# Per-client cap on starting a sign-in, so one client cannot evict others'
# pending attempts from ATTEMPTS.
START_THROTTLE = oidc.StartThrottle()
_THROTTLED_STATUS = 429

_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)
_UNAVAILABLE_STATUS = 503
_STATUS_BY_KIND = {
    oidc.KIND_INCOMPLETE: 400,
    oidc.KIND_EXPIRED: 400,
    oidc.KIND_PROVIDER_ERROR: 400,
    oidc.KIND_UNAVAILABLE: 503,
}
# Reasons fleet_sessions reports for a refusal; the unverified one gets its
# own page, every other one the same not-invited page.
_REASON_UNVERIFIED = "unverified_email"
_REASON_LINKED = "linked"

# The flash tokens a landing page may carry after a first sign-in. Each
# names fixed wording: the Home of a frame, the Account page, or a
# destination-neutral line.
WELCOME_HOME = "welcome"
WELCOME_ACCOUNT = "welcome_account"
WELCOME_NEUTRAL = "welcome_neutral"


# The co-manager results an Account toast may show after a Manage access or
# Leave frame form.
_ACCOUNT_FLASH_KEYS = (
    co_managers_card.FLASH_ADDED, co_managers_card.FLASH_REMOVED,
    co_managers_card.FLASH_LEFT, co_managers_card.FLASH_ADD_REFUSED,
    co_managers_card.FLASH_FAILED, co_managers_card.FLASH_LEAVE_NOOP,
    co_managers_card.FLASH_FRAME_REMOVED, co_managers_card.FLASH_FRAME_REMOVE_REFUSED,
    co_managers_card.FLASH_FRAME_REMOVE_LIVE, frame_name_page.FLASH_FRAME_RENAMED)


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
        if not START_THROTTLE.allow(self._login_throttle_key()):
            _log("sign-in start throttled")
            return self.send_html(_THROTTLED_STATUS, login_page.sign_in_error_page(
                login_page.SIGN_IN_ERROR_THROTTLED, self._pre_session_theme(),
                auth0_enabled=True))
        query = parse_qs(urlsplit(self.path).query)
        next_route = self._next_route_of(query.get("next", [None])[0])
        prompt = query.get("prompt", [None])[0]
        attempt_id, attempt = ATTEMPTS.create(next_route)
        location = oidc.authorize_url(
            cfg, attempt.state, attempt.nonce, attempt.challenge,
            prompt=prompt if prompt == login_page.PROMPT_LOGIN else None)
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
            token = auth.new_session_token()
            outcome = self._resolve_invited(cfg, claims, token)
        except oidc.SignInError as exc:
            _log("sign-in failed: %s" % exc.reason)
            return self._sign_in_failed(exc.kind, attempt)
        except _STORE_ERRORS as exc:
            _log("sign-in store error: %s" % type(exc).__name__)
            return self._sign_in_failed(oidc.KIND_UNAVAILABLE, attempt)
        if outcome.user_id is None:
            return self.send_html(
                403, self._refusal_page(outcome.reason),
                set_cookies=[auth.oidc_attempt_clear_cookie_header()])
        try:
            return self._land_signed_in(
                outcome.user_id, claims.email, attempt, token,
                first_link=outcome.reason == _REASON_LINKED)
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
            raise oidc.SignInError("provider_error", oidc.KIND_PROVIDER_ERROR)
        code = (query.get("code") or [""])[0]
        state = (query.get("state") or [""])[0]
        if not code or not state:
            raise oidc.SignInError("callback_incomplete")
        if not hmac.compare_digest(state.encode("utf-8"), attempt.state.encode("utf-8")):
            raise oidc.SignInError("state_mismatch")
        token = oidc.exchange_code(cfg, code, attempt.verifier, oidc.requests_post)
        return oidc.validate_id_token(token, cfg, attempt.nonce, self._clock())

    def _resolve_invited(self, cfg, claims, token):
        """The `fleet_sessions.LoginOutcome` for these claims: the invited
        user's id (None when refused) and the reason. For an invited user
        the session for `token` is stored in the same transaction as any
        first-time identity link, so a failure leaves neither behind.
        """
        old = auth.parse_cookies(self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
        outcome = fleet_sessions.sign_in_user(
            self._fleet_conn(), cfg.issuer, claims.sub, claims.email,
            claims.email_verified, self._clock(), auth.hash_session_token(token),
            replace_hash=auth.hash_session_token(old) if old else None)
        if outcome.user_id is None:
            _log("sign-in refused: %s" % outcome.reason)
        return outcome

    def _refusal_page(self, reason):
        """The page for a refused sign-in. Only an unconfirmed email gets
        its own page; the reason was decided by the sign-in outcome itself,
        before any lookup of who is invited."""
        theme = self._pre_session_theme()
        if reason == _REASON_UNVERIFIED:
            return login_page.unverified_email_page(theme)
        return login_page.not_invited_page(theme)

    def _sign_in_failed(self, kind, attempt):
        next_route = attempt.next_route if attempt is not None else None
        page = login_page.sign_in_error_page(
            kind, self._pre_session_theme(), auth0_enabled=True,
            next_route=self._next_route_of(next_route))
        return self.send_html(
            _STATUS_BY_KIND.get(kind, 400), page,
            set_cookies=[auth.oidc_attempt_clear_cookie_header()])

    def _land_signed_in(self, user_id, email, attempt, token, first_link=False):
        """Answer with an interstitial for the session already stored for
        `token`. A 200 page with a meta refresh, not a 303: a redirect
        chain that began on another site makes the browser withhold a
        SameSite=Strict cookie, and the page also keeps the callback query
        out of the next request's Referer. The first sign-in that links an
        identity adds a welcome flash token to the destination.
        """
        conn = self._fleet_conn()
        role = fleet_db.get_user_role(conn, user_id)
        if role is None:
            return self._sign_in_failed(oidc.KIND_INCOMPLETE, attempt)
        principal = access.Principal(access.KIND_USER, user_id, email, role)
        target, label = self._landing_target(principal, attempt)
        if first_link:
            target = self._with_welcome(target)
        _log("signed in: user %d" % user_id)
        page = login_page.interstitial_page(
            login_page.INTERSTITIAL_IN, target, label, self._pre_session_theme())
        return self.send_html(200, page, set_cookies=[
            auth.session_set_cookie_header(token),
            auth.oidc_attempt_clear_cookie_header()])

    @staticmethod
    def _with_welcome(target):
        """`target` plus the welcome flash token fitting where it leads."""
        if target == ACCOUNT_ROUTE:
            token = WELCOME_ACCOUNT
        elif target.startswith("/devices/") and target.count("/") == 3:
            token = WELCOME_HOME
        else:
            token = WELCOME_NEUTRAL
        return target + ("&" if "?" in target else "?") + "flash=" + token

    def _landing_target(self, principal, attempt):
        """(path, label) the sign-in interstitial continues to: a validated
        `next` route when the caller can use it, else the role landing."""
        landing = self._landing_for(principal)
        next_route = self._next_route_of(attempt.next_route)
        if next_route and landing != ACCOUNT_ROUTE:
            return next_route, login_page.CONTINUE_TARGET_HOME
        if principal.role == access.ADMIN:
            return landing, login_page.CONTINUE_TARGET_FLEET
        if landing == ACCOUNT_ROUTE:
            return landing, login_page.CONTINUE_TARGET_ACCOUNT
        return landing, login_page.CONTINUE_TARGET_HOME

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

    # --- account -------------------------------------------------------

    def _shared_frame_facts(self, principal):
        """(ids of the frames the caller co-manages, a user-id -> e-mail
        lookup) read from the fleet store; empty on any store problem, so the
        caller's own frames are listed regardless."""
        if principal.user_id is None:
            return set(), (lambda user_id: "")
        try:
            conn = self._fleet_conn()
            shared = fleet_db.co_managed_device_ids(conn, principal.user_id)
        except _STORE_ERRORS:
            return set(), (lambda user_id: "")

        def email_of(user_id):
            try:
                row = conn.execute(
                    "SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
            except _STORE_ERRORS:
                return ""
            return "" if row is None else str(row["email"])
        return shared, email_of

    def _own_frame_summaries(self, principal):
        """The frames the caller owns or co-manages as `FrameSummary` values,
        whatever the role: an admin sees here only those, not every frame. A
        co-managed frame is marked shared and carries its owner's address; an
        owned frame carries its Manage access view. The address is always the
        prefixed Home, never the live frame's bare root."""
        frames = []
        shared_ids, email_of = self._shared_frame_facts(principal)
        now = datetime.datetime.now(datetime.timezone.utc)
        for device in device_scope.load_devices_for(self.args.state_dir, principal):
            owned = principal.user_id is not None and device.owner_user_id == principal.user_id
            shared = not owned and device.id in shared_ids
            if not owned and not shared:
                continue
            frames.append(self._frame_summary(
                device, now, shared, email_of(device.owner_user_id) if shared else "",
                self._access_view(device, principal) if owned else None))
        return frames

    def _access_view(self, device, principal):
        """The Manage access view of a frame the caller owns, None when the
        store cannot be read."""
        try:
            return co_managers.access_view(self._fleet_conn(), device, principal)
        except _STORE_ERRORS:
            return None

    def _frame_summary(self, device, now, shared, owner_email, access_view):
        profile = hardware.REGISTRY.get(device.hardware_type)
        millivolts = state_store.load_battery_state(device.state_dir)
        state, screen_off, critical = console_pairing.frame_signals(
            device, now.isoformat(timespec="seconds"))
        status = device_scope.device_status(device, now.timestamp())
        return account_page.FrameSummary(
            # An unnamed frame is listed under its id by the device
            # scope; the id is not shown on this page.
            name=(
                i18n.t(account_page.UNNAMED_FRAME_TEXT)
                if device.name == device.id else ui_shell.device_display_name(device)),
            hardware=profile.label if profile is not None else device.hardware_type,
            href="/devices/%s/" % device.id,
            device_id=device.id,
            last_seen=device_scope.last_check_in_epoch(device.state_dir),
            battery_percent=0 if critical else (
                None if millivolts is None else battery.battery_percent(millivolts)),
            offline=status == device_scope.STATUS_OFFLINE,
            state=state, screen_off=screen_off,
            shared=shared, owner_email=owner_email, access=access_view)

    def _account_flash_html(self):
        """The co-manager or welcome toast when the request carries exactly
        one of those flash keys; any other value renders nothing."""
        key = parse_qs(urlsplit(self.path).query).get("flash", [None])[0]
        if key not in _ACCOUNT_FLASH_KEYS and key not in flash.WELCOME_KEYS:
            return None
        text = flash.resolve_flash_text(key, self.args.state_dir)
        return flash.flash_toast_html(key, text, self.path)

    def _welcome_flash_html(self):
        """The welcome toast when the request carries one of its tokens;
        any other flash value renders nothing here."""
        key = parse_qs(urlsplit(self.path).query).get("flash", [None])[0]
        if key not in flash.WELCOME_KEYS:
            return None
        text = flash.resolve_flash_text(key, self.args.state_dir)
        return flash.flash_toast_html(key, text, self.path)

    def _handle_account_get(self):
        """GET /account: who is signed in, the browser preferences and the
        caller's own frames. Reads the principal, the preference cookies and
        the frames the principal owns; never another account's data.
        """
        principal = self._principal()
        identity = account_page.Identity(principal.email or _NO_EMAIL, principal.role)
        prefs.set_request_prefs(lang=self._lang_from_request())
        theme = self._resolved_ui_theme()
        query = parse_qs(urlsplit(self.path).query)
        body = account_page.render(
            identity, ui_theme=theme, frames=self._own_frame_summaries(principal),
            open_access=(query.get(co_managers_card.ACCESS_QUERY) or [""])[0])
        page = layout.page_shell(
            title=i18n.t(account_page.ACCOUNT_TITLE), active=layout.nav_slug(ACCOUNT_ROUTE),
            body=body, ui_theme=theme, health_alert=None, flash=self._account_flash_html())
        return self.send_html(200, page)
