"""Access-matrix rows for the lifecycle console routes: `ROWS` maps
(method, route template) to a policy kind name from
companion/test_access_matrix.py, `SAMPLES` maps each templated route to a
sample middle segment.
"""

ROWS = {
    ("POST", "/fleet/frames/{}/retire"): "admin-only",
    ("POST", "/fleet/frames/{}/reactivate"): "admin-only",
    ("POST", "/fleet/frames/{}/reassign"): "admin-only",
}
SAMPLES = {
    "/fleet/frames/{}/retire": "d_00000000",
    "/fleet/frames/{}/reactivate": "p_00000000",
    "/fleet/frames/{}/reassign": "d_00000000",
}
