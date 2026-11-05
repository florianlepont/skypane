"""Access-matrix rows for the user landing behaviour. No route is added;
`ROWS` and `SAMPLES` stay empty so the module merges like the others.

`FRAME_PAGE_REDIRECTS` are the un-prefixed frame pages a user or an
administrator is moved from to the same page under their default frame (303);
a user without a frame goes to the account page (where adding a frame
is offered) and an administrator without
a frame goes to `ADMIN_FRAMELESS_TARGET` once the fleet has rows. `SIGNED_IN_LOGIN_ROLES` are the principals sent from /login to their
role landing.
"""

ROWS = {}
SAMPLES = {}

FRAME_PAGE_REDIRECTS = (
    "/", "/display", "/flights", "/airlines", "/detection")
ADMIN_FRAMELESS_TARGET = "/account"
SIGNED_IN_LOGIN_ROLES = ("admin", "owner", "other", "co-manager")
