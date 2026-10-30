"""Startup validation of the sign-in environment: Auth0 is the only way to
sign in, so a complete Auth0 configuration is required to serve at all."""
from companion import oidc


class SignInConfigError(Exception):
    """The environment leaves no safe sign-in setup; names variables only."""


def validate_sign_in_config(environ):
    """Refuse to start without a complete Auth0 configuration. The Auth0
    variables are all-or-nothing, and an absent set is as fatal as a partial
    one. Messages name variables, never values; unrelated variables
    are never read.
    """
    try:
        auth0 = oidc.Auth0Config.from_env(environ)
    except oidc.Auth0ConfigError as exc:
        raise SignInConfigError(str(exc)) from None
    if auth0 is None:
        raise SignInConfigError(
            "sign-in is not configured: set SKYPANE_AUTH0_DOMAIN, "
            "SKYPANE_AUTH0_CLIENT_ID and SKYPANE_AUTH0_CLIENT_SECRET")
