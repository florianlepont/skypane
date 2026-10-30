"""Default-deny access decision and the device ownership gate.

Pure functions over plain values: no sqlite3, no server imports, no I/O.
The only external fact, who owns a device, is injected as `owner_lookup`.

Interface contract: a device-scoped handler receives a device id that this
gate has already authorised and must never query devices directly.

Outcomes:
- ALLOW: run the handler.
- LOGIN: anonymous caller on a non-public route (303 to the login page).
- NOT_FOUND: an authenticated caller who may not reach the route or the
  device; deliberately the same answer as an unknown path.
"""
import collections
import re

ANONYMOUS = "anonymous"
USER = "user"
ADMIN = "admin"

RANK = {ANONYMOUS: 0, USER: 1, ADMIN: 2}

ALLOW = "allow"
LOGIN = "login"
NOT_FOUND = "not-found"

KIND_USER = "user"

Principal = collections.namedtuple("Principal", "kind user_id email role")

# The id format fleet_db.add_device generates. Applied before any lookup so
# a captured path segment never reaches the database layer unvalidated.
DEVICE_ID_RE = re.compile(r"^d_[0-9a-f]{8}$")


def _valid_device_id(value):
    return isinstance(value, str) and DEVICE_ID_RE.fullmatch(value) is not None


def authorized_device_id(principal, device_id, owner_lookup):
    """The validated device id when `principal` may reach it, else None.

    An admin reaches any existing device; a user only one they own. A
    malformed id is refused without calling `owner_lookup`.
    """
    if principal is None or not _valid_device_id(device_id):
        return None
    owner = owner_lookup(device_id)
    if owner is None:
        return None
    if principal.role == ADMIN:
        return device_id
    if principal.user_id is not None and owner == principal.user_id:
        return device_id
    return None


def decide(principal, access, captured, owner_lookup):
    """ALLOW, LOGIN or NOT_FOUND for one request. Never raises on hostile
    input: an unknown role ranks below every requirement.
    """
    if access.min_role == ANONYMOUS:
        return ALLOW
    if principal is None:
        return LOGIN
    if RANK.get(principal.role, -1) < RANK[access.min_role]:
        return NOT_FOUND
    if access.device_arg is None:
        return ALLOW
    if authorized_device_id(principal, captured, owner_lookup) is None:
        return NOT_FOUND
    return ALLOW


def home_for(principal):
    """Where a signed-in principal lands: the account page for a user, the
    dashboard for an admin.
    """
    if principal is not None and principal.role == USER:
        return "/account"
    return "/"
