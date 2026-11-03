"""Access-matrix rows for the routes only an administrator reaches, on the
served frame and, under a `/devices/<id>` prefix, on any frame: Health, the
Airline editor and the airline write routes. An owner user and a co-manager
are refused with the unknown-path 404; anonymous is sent to sign-in.
`ROWS` maps (method, route template) to the policy kind name from
companion/test_access_matrix.py, `SAMPLES` the middle of each templated route.
"""

KIND = "admin-only-device"

ROWS = {
    ("GET", "/health"): KIND,
    ("GET", "/airlines/manage"): KIND,
    ("POST", "/airlines/resolve"): KIND,
    ("POST", "/airlines/rename"): KIND,
    ("POST", "/airlines/rename/reset"): KIND,
    ("POST", "/airlines/manual-resolutions/{}/delete"): KIND,
    ("POST", "/illustration/{}.png"): KIND,
}
SAMPLES = {}
