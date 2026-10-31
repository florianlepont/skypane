"""The one per-request browser preference this package resolves:
language. Page-independent, stdlib-only (contextvars).

One set path (companion/app.py's page_context(), called once per
request), two read paths (page modules via ctx, layout.py via this
module directly), no other mutation path — same discipline auth.py's
own module-level mutable state is guarded by.
"""
import contextvars

LANG_CHOICES = ("fr", "en")
DEFAULT_LANG = "en"

_LANG_CTX = contextvars.ContextVar("skypane_lang", default=DEFAULT_LANG)


def set_request_prefs(lang=None):
    """Resolve and store this request's language preference.
    Membership-tested against LANG_CHOICES: anything unrecognised
    (including None, the "no preference known yet" case) degrades to
    the default rather than raising. This is the sole mutation path —
    call it exactly once per request.
    """
    _LANG_CTX.set(lang if lang in LANG_CHOICES else DEFAULT_LANG)


def current_lang():
    """The resolved language for the current request context — always
    a member of LANG_CHOICES ("fr" or "en"), never raises."""
    return _LANG_CTX.get()


# The signed-in principal's (kind, role) for this request, or None when no
# principal has been established (every pre-sign-in page, and any caller
# that never sets one). Shell rendering reads it to pick the user-role
# navigation.
_PRINCIPAL_CTX = contextvars.ContextVar("skypane_principal", default=None)

PRINCIPAL_KINDS = ("user", "admin")


def set_request_principal(kind=None, role=None):
    """Store this request's principal. Anything unrecognised (including
    None) clears it, so the shell falls back to the unchanged default
    rendering. Call it once per request, before any page is rendered.
    """
    if kind in PRINCIPAL_KINDS:
        _PRINCIPAL_CTX.set((kind, role))
    else:
        _PRINCIPAL_CTX.set(None)


def current_principal():
    """The request's (kind, role) pair, or None when unset."""
    return _PRINCIPAL_CTX.get()


# The anti-forgery token derived from this request's session, or "" when no
# session is in scope. Only forms read it (ui_components.csrf_field()).
_CSRF_CTX = contextvars.ContextVar("skypane_csrf", default="")


def set_request_csrf(token=""):
    """Store this request's anti-forgery token; anything but a non-empty
    string clears it. Call it once per request, after the principal.
    """
    _CSRF_CTX.set(token if isinstance(token, str) else "")


def current_csrf():
    """The request's anti-forgery token, or "" when none is in scope."""
    return _CSRF_CTX.get()
