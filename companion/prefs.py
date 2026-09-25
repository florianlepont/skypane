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
