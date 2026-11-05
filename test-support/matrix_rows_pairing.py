"""Access-matrix rows for the pairing console routes: `ROWS` maps
(method, route template) to a policy kind name from
companion/test_access_matrix.py, `SAMPLES` maps each templated route to a
sample middle segment.
"""

ROWS = {
    ("GET", "/fleet"): "admin-only",
    ("POST", "/fleet/register"): "admin-only",
    ("POST", "/fleet/pair"): "admin-only",
    # The user-scope claim: any signed-in person pairs a frame for themselves.
    ("GET", "/pair-frame"): "signed-in",
    ("POST", "/pair-frame"): "signed-in",
}
SAMPLES = {}
