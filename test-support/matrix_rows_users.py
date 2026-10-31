"""Access-matrix rows for the users console routes: `ROWS` maps
(method, route template) to a policy kind name from
companion/test_access_matrix.py, `SAMPLES` maps each templated route to a
sample middle segment.
"""

ROWS = {
    ("GET", "/users"): "admin-only",
    ("POST", "/users/invite"): "admin-only",
    ("POST", "/users/{}/role"): "admin-only",
    ("POST", "/users/{}/disable"): "admin-only",
    ("POST", "/users/{}/enable"): "admin-only",
    ("POST", "/users/{}/unlink"): "admin-only",
}
SAMPLES = {
    "/users/{}/role": "1",
    "/users/{}/disable": "1",
    "/users/{}/enable": "1",
    "/users/{}/unlink": "1",
}
