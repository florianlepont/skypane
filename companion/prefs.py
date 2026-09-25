"""The one per-request browser preference this package resolves:
language.

Sits beside auth.py, battery.py, layout.py, screens.py and wake.py in
this same package — a shared, page-independent module, never living
inside the per-tab pages sub-package itself (that sub-package's own
"pages/__init__.py" states the rule: no page module imports another
page module). Stdlib-only (the contextvars module); this file must
never import anything under the pages sub-package, and must never
import anything under the top-level "server" tree.

ctx["lang"] is still published for page modules, per the pages
sub-package's own documented ctx contract — this module is the layout
layer's own read path for the same single per-request resolution,
never a second one: companion/app.py's page_context() (and the
pre-session login/404 render paths) call set_request_prefs() exactly
once per request, and every reader (page modules via ctx, layout.py
via this module directly) sees the identical resolved value.

One set path, two read paths, no other mutation path — the same
discipline auth.py's own module-level mutable state
(LoginThrottle/_REVOKED) is guarded by.
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
