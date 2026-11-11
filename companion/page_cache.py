"""Cache headers of a rendered HTML page.

Every page is session-gated, so the default answer is `no-store`: nothing may
replay it after sign-out or to another account. Two exceptions:

* The response to the page script's own prefetch of a navigation destination
  (a GET sent by prefetch.js with the `X-Requested-With: prefetch` header,
  which a cross-site page cannot add without a CORS preflight the server
  never answers) may sit in the browser's private cache for ten seconds so
  the tap that follows is served locally.
* A plain navigation to a 200 page that carries session-guard.js, from a
  browser that already ran its restore code (it left the `sp_restore` cookie), is
  `private, no-cache`: it may enter the back/forward cache, which `no-store`
  forbids, because the script checks the session of every page restored from
  there before showing it. `no-cache` makes every ordinary load revalidate,
  and nothing here answers a conditional request with 304 for a navigation.
  A history navigation that does not use the back/forward cache may still be
  answered from the HTTP cache without a request; `Vary: Cookie` keys that
  entry by the full cookie header, so a sign-out (the session cookie is
  cleared), a new session or another account never matches it.

`Vary: Cookie` keys the prefetch entry too: another account, a sign-out, a
new session and any change the user made in this browser (prefetch.js
rewrites a marker cookie on every form post and quick switch) all miss it. A
response that sets a cookie is never cached.
"""
from companion.ui_base import SESSION_GUARD_SCRIPT_SRC

PREFETCH_HEADER_VALUE = "prefetch"
PREFETCH_MAX_AGE_S = 10
RESTORE_CAPABLE_COOKIE = "sp_restore"


def _restore_capable(request_headers):
    """Whether the browser sent the marker session-guard.js leaves."""
    for part in (request_headers.get("Cookie") or "").split(";"):
        if part.strip() == RESTORE_CAPABLE_COOKIE + "=1":
            return True
    return False


def html_cache_headers(request_headers, status, sets_cookie, html=""):
    """The (name, value) cache headers for an HTML response."""
    requested_with = request_headers.get("X-Requested-With")
    if status == 200 and not sets_cookie:
        if requested_with == PREFETCH_HEADER_VALUE:
            return (
                ("Cache-Control", "private, max-age=%d" % PREFETCH_MAX_AGE_S),
                ("Vary", "Cookie"),
            )
        if (requested_with is None and _restore_capable(request_headers)
                and SESSION_GUARD_SCRIPT_SRC in html):
            return (("Cache-Control", "private, no-cache"), ("Vary", "Cookie"))
    return (("Cache-Control", "no-store"),)
