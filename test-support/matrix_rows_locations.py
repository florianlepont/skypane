"""Access-matrix rows for the locations console routes: `ROWS` maps
(method, route template) to a policy kind name from
companion/test_access_matrix.py, `SAMPLES` maps each templated route to a
sample middle segment.
"""

ROWS = {
    ("GET", "/locations"): "signed-in",
    ("POST", "/locations/add"): "signed-in",
    ("POST", "/locations/{}/edit"): "signed-in",
    ("POST", "/locations/{}/delete"): "signed-in",
}
SAMPLES = {
    "/locations/{}/edit": "1",
    "/locations/{}/delete": "1",
}
