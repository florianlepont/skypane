"""Access-matrix rows for the place save and the quiet-hours window save.

The place save adds no route (POST /detection is already an owner-device
route). The quiet-hours dialog posts to its own route, which has a row in
`ROWS`: owner, co-manager and administrator of the frame are accepted, a
stranger gets the unknown-path 404 and an anonymous caller is sent to
sign-in.

`ACTION` is the form action that saves a frame's own place. `EXPECTED_STATUS`
is what each kind of caller gets when it posts a valid place for the owner's
frame: the owner, a co-manager of that frame and an administrator are accepted
(303), a stranger gets the unknown-path 404 and an anonymous caller is sent to
sign-in (303 to /login).
"""

ROWS = {
    ("POST", "/quick/quiet-hours/window"): "owner-device",
}
SAMPLES = {}

ACTION = "save_place"
EXPECTED_STATUS = {
    "owner": 303,
    "co-manager": 303,
    "admin": 303,
    "other": 404,
    "anonymous": 303,
}
