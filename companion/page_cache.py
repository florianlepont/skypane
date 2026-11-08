"""Cache headers of a rendered HTML page.

Every page is session-gated, so the answer is `no-store`: nothing may replay
it after sign-out or to another account. The one exception is the response to
the page script's own prefetch of a navigation destination (a GET sent by
prefetch.js with the `X-Requested-With: prefetch` header, which a cross-site
page cannot add without a CORS preflight the server never answers). That
answer may sit in the browser's private cache for ten seconds so the tap
that follows is served locally. `Vary: Cookie` keys the entry by the full
cookie header: another account, a sign-out, a new session and any change the
user made in this browser (prefetch.js rewrites a marker cookie on every
form post and quick switch) all miss it. A response that sets a cookie is
never cached.
"""

PREFETCH_HEADER_VALUE = "prefetch"
PREFETCH_MAX_AGE_S = 10


def html_cache_headers(request_headers, status, sets_cookie):
    """The (name, value) cache headers for an HTML response."""
    prefetched = request_headers.get("X-Requested-With") == PREFETCH_HEADER_VALUE
    if prefetched and status == 200 and not sets_cookie:
        return (
            ("Cache-Control", "private, max-age=%d" % PREFETCH_MAX_AGE_S),
            ("Vary", "Cookie"),
        )
    return (("Cache-Control", "no-store"),)
