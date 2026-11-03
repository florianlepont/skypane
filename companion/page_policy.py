"""Content-Security-Policy and Permissions-Policy pairs for HTML responses.

Every response carries DEFAULT_PAGE_POLICY unless the handler that renders it
passes another pair explicitly. The only other pair belongs to the location
page: it adds the map tile host (images) and the place-search host
(connections) and lets that page ask the browser for its position. No policy
is ever derived from request text.
"""
import collections

PagePolicy = collections.namedtuple("PagePolicy", "content_security_policy permissions_policy")

# No 'unsafe-inline' on script-src (no inline <script> anywhere); style-src
# allows 'unsafe-inline' solely for theme-swatch `style="background:..."`
# attributes sourced from the fixed THEMES registry, never user input.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
PERMISSIONS_POLICY = "geolocation=()"

MAP_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; "
    "connect-src 'self' https://nominatim.openstreetmap.org; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
MAP_PERMISSIONS_POLICY = "geolocation=(self)"

DEFAULT_PAGE_POLICY = PagePolicy(CONTENT_SECURITY_POLICY, PERMISSIONS_POLICY)
MAP_PAGE_POLICY = PagePolicy(MAP_CONTENT_SECURITY_POLICY, MAP_PERMISSIONS_POLICY)
