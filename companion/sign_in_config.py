"""Startup validation of the sign-in environment: which login methods are
configured, and whether the combination is safe to serve."""
from companion import auth, oidc


class SignInConfigError(Exception):
    """The environment leaves no safe sign-in setup; names variables only."""


def validate_sign_in_config(environ):
    """Refuse a configuration that would silently enable, or silently lose,
    a login method. The shared password is required only while its switch
    is on; the Auth0 variables are all-or-nothing; at least one method must
    remain. Messages name variables, never values.
    """
    try:
        legacy_on = auth.legacy_login_enabled(environ)
    except ValueError as exc:
        raise SignInConfigError(str(exc)) from None
    if legacy_on:
        try:
            auth.configured_password(environ)
        except auth.AuthNotConfigured as exc:
            raise SignInConfigError(str(exc)) from None
    try:
        auth0 = oidc.Auth0Config.from_env(environ)
    except oidc.Auth0ConfigError as exc:
        raise SignInConfigError(str(exc)) from None
    if not legacy_on and auth0 is None:
        raise SignInConfigError(
            "no sign-in method is configured: set the SKYPANE_AUTH0_* "
            "variables or enable %s" % auth.LEGACY_LOGIN_ENV_VAR)
