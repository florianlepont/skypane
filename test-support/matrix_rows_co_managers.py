"""Access-matrix rows for the co-manager routes: `ROWS` maps (method, route
template) to a policy kind name from companion/test_access_matrix.py,
`SAMPLES` maps each templated route to a sample middle segment.

Adding and removing co-managers is owner-or-admin only; leaving a frame is
open to the owner, an admin and a co-manager of that frame. Removing a frame
is owner-or-admin at the gate and the owner alone in the handler.
"""

ROWS = {
    ("POST", "/co-managers/add"): "owner-only-device",
    ("POST", "/co-managers/remove"): "owner-only-device",
    ("POST", "/co-managers/leave"): "owner-device",
    ("POST", "/frame/remove"): "owner-only-device",
}
SAMPLES = {}
