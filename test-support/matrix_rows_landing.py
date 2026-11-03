"""Access-matrix rows for the user landing behaviour. No route is added;
`ROWS` and `SAMPLES` stay empty so the module merges like the others.

`FRAME_PAGE_REDIRECTS` are the un-prefixed frame pages a user is moved from
to the same page under their default frame (303) instead of the unknown-path
404. `SIGNED_IN_LOGIN_ROLES` are the principals sent from /login to their
role landing.
"""

ROWS = {}
SAMPLES = {}

FRAME_PAGE_REDIRECTS = (
    "/", "/display", "/flights", "/airlines", "/health", "/detection")
SIGNED_IN_LOGIN_ROLES = ("admin", "owner", "other", "co-manager")
