"""Pure-function tests for the default-deny decision and ownership gate."""
import itertools

import pytest

from companion import access, routes

_MIN_ROLES = (access.ANONYMOUS, access.USER, access.ADMIN)
_USER = access.Principal("user", 7, "u@example.com", "user")
_ADMIN = access.Principal("user", 1, "a@example.com", "admin")

OWNERS = {"d_00000001": 7, "d_00000002": 9}


def _lookup(device_id):
    return OWNERS.get(device_id)


def _acc(min_role, device_arg=None):
    return routes.Access(min_role, device_arg)


@pytest.mark.parametrize(
    "principal,min_role",
    list(itertools.product([None, _USER, _ADMIN], _MIN_ROLES)))
def test_decide_table(principal, min_role):
    outcome = access.decide(principal, _acc(min_role), None, _lookup)
    if min_role == access.ANONYMOUS:
        assert outcome == access.ALLOW
    elif principal is None:
        assert outcome == access.LOGIN
    elif principal.role == access.ADMIN:
        assert outcome == access.ALLOW
    else:
        expected = access.ALLOW if min_role == access.USER else access.NOT_FOUND
        assert outcome == expected


def test_unknown_principal_role_is_denied():
    odd = access.Principal("user", 1, "x@example.com", "root")
    assert access.decide(odd, _acc(access.USER), None, _lookup) == access.NOT_FOUND


def test_device_scope_owner_allowed_other_user_denied():
    scoped = _acc(access.USER, "device")
    assert access.decide(_USER, scoped, "d_00000001", _lookup) == access.ALLOW
    assert access.decide(_USER, scoped, "d_00000002", _lookup) == access.NOT_FOUND


def test_device_scope_admin_reaches_only_existing_devices():
    scoped = _acc(access.USER, "device")
    assert access.decide(_ADMIN, scoped, "d_00000002", _lookup) == access.ALLOW
    assert access.decide(_ADMIN, scoped, "d_0000ffff", _lookup) == access.NOT_FOUND


def test_device_scope_anonymous_goes_to_login():
    scoped = _acc(access.USER, "device")
    assert access.decide(None, scoped, "d_00000001", _lookup) == access.LOGIN


@pytest.mark.parametrize(
    "bad", ["d_ZZZZZZZZ", "../x", "", "d_" + "0" * 40, "d_0000/001", "D_00000001",
            "d_00000001\n", None, 5, b"d_00000001", ["d_00000001"]])
def test_malformed_ids_are_denied_without_a_lookup(bad):
    calls = []

    def lookup(device_id):
        calls.append(device_id)
        return 7

    scoped = _acc(access.USER, "device")
    for principal in (_USER, _ADMIN):
        assert access.decide(principal, scoped, bad, lookup) == access.NOT_FOUND
        assert access.authorized_device_id(principal, bad, lookup) is None
    assert calls == []


def test_authorized_device_id_returns_the_id_or_none():
    assert access.authorized_device_id(_USER, "d_00000001", _lookup) == "d_00000001"
    assert access.authorized_device_id(_USER, "d_00000002", _lookup) is None
    assert access.authorized_device_id(_ADMIN, "d_00000002", _lookup) == "d_00000002"
    assert access.authorized_device_id(_ADMIN, "d_0000ffff", _lookup) is None
    assert access.authorized_device_id(None, "d_00000001", _lookup) is None


_COMANAGED = {("d_00000001", 7)}
_OWNER_ONLY = "device-owner"


def _recording_membership():
    calls = []

    def is_co_manager(device_id, user_id):
        calls.append((device_id, user_id))
        return (device_id, user_id) in _COMANAGED

    return is_co_manager, calls


def test_a_co_manager_reaches_only_the_frames_they_co_manage():
    scoped = _acc(access.USER, "device")
    member, _calls = _recording_membership()
    stranger_owned = {"d_00000001": 9, "d_00000002": 9}.get
    assert access.decide(_USER, scoped, "d_00000001", stranger_owned, member) == access.ALLOW
    assert access.decide(_USER, scoped, "d_00000002", stranger_owned, member) == access.NOT_FOUND


def test_a_stranger_and_an_unknown_frame_are_not_found():
    scoped = _acc(access.USER, "device")
    member, calls = _recording_membership()
    nobody = access.Principal("user", 11, "n@example.com", "user")
    assert access.decide(nobody, scoped, "d_00000001", _lookup, member) == access.NOT_FOUND
    assert access.decide(_USER, scoped, "d_0000ffff", lambda _d: None, member) == access.NOT_FOUND
    assert ("d_0000ffff", 7) not in calls


@pytest.mark.parametrize(
    "bad", ["d_ZZZZZZZZ", "../x", "", "d_" + "0" * 40, "D_00000001", None, 5,
            b"d_00000001"])
def test_a_malformed_id_reaches_neither_lookup(bad):
    owner_calls = []

    def owner(device_id):
        owner_calls.append(device_id)
        return 9

    member, member_calls = _recording_membership()
    for scoped in (_acc(access.USER, "device"), _acc(access.USER, _OWNER_ONLY)):
        assert access.decide(_USER, scoped, bad, owner, member) == access.NOT_FOUND
    assert owner_calls == [] and member_calls == []


def test_the_owner_only_kind_admits_owner_and_admin_but_not_a_co_manager():
    scoped = _acc(access.USER, _OWNER_ONLY)
    member, calls = _recording_membership()
    owned_by_other = {"d_00000001": 9}.get
    assert access.decide(_USER, scoped, "d_00000001", _lookup, member) == access.ALLOW
    assert access.decide(_ADMIN, scoped, "d_00000001", owned_by_other, member) == access.ALLOW
    assert access.decide(_USER, scoped, "d_00000001", owned_by_other, member) == access.NOT_FOUND
    other = access.Principal("user", 11, "n@example.com", "user")
    assert access.decide(other, scoped, "d_00000001", owned_by_other, member) == access.NOT_FOUND
    assert access.decide(None, scoped, "d_00000001", owned_by_other, member) == access.LOGIN
    assert calls == []


def test_the_four_argument_form_never_admits_a_co_manager():
    scoped = _acc(access.USER, "device")
    assert access.decide(_USER, scoped, "d_00000002", _lookup) == access.NOT_FOUND
    assert access.authorized_device_id(_USER, "d_00000002", _lookup) is None


def test_no_user_id_is_never_a_co_manager_and_an_admin_skips_membership():
    scoped = _acc(access.USER, "device")
    member, calls = _recording_membership()
    anonymous_id = access.Principal("user", None, "x@example.com", "user")
    assert access.decide(anonymous_id, scoped, "d_00000002", _lookup, member) == access.NOT_FOUND
    assert access.decide(_ADMIN, scoped, "d_00000002", _lookup, member) == access.ALLOW
    assert calls == []


@pytest.mark.parametrize("principal,frame_id,expected", [
    (_ADMIN, None, "/fleet"),
    (_ADMIN, "d_00000001", "/fleet"),
    (_USER, "d_00000001", "/devices/d_00000001/"),
    (_USER, None, "/account"),
    (_USER, "../evil", "/account"),
    (None, None, "/"),
])
def test_home_for(principal, frame_id, expected):
    assert access.home_for(principal, frame_id) == expected


# --- the manager kind: owner and co-manager, no admin shortcut ----------------

_MANAGER = "device-manager"
_OWNED_BY_OTHER = {"d_00000001": 9}.get


def test_the_manager_kind_is_exported_with_the_user_floor():
    assert routes.MANAGER_DEVICE == routes.Access(access.USER, _MANAGER)


def test_allow_admin_false_refuses_a_pure_admin_but_keeps_managers():
    member, _calls = _recording_membership()
    assert access.authorized_device_id(
        _ADMIN, "d_00000002", _lookup, member, allow_admin=False) is None
    assert access.authorized_device_id(
        _USER, "d_00000001", _lookup, member, allow_admin=False) == "d_00000001"
    assert access.authorized_device_id(
        _USER, "d_00000001", _OWNED_BY_OTHER, member,
        allow_admin=False) == "d_00000001"
    assert access.authorized_device_id(
        _USER, "d_00000002", _lookup, member, allow_admin=False) is None


def test_an_admin_who_owns_or_co_manages_a_frame_is_admitted_as_manager():
    owner_admin = access.Principal("user", 9, "oa@example.com", "admin")
    assert access.authorized_device_id(
        owner_admin, "d_00000002", _lookup, allow_admin=False) == "d_00000002"
    comanager_admin = access.Principal("user", 7, "ca@example.com", "admin")
    member, _calls = _recording_membership()
    assert access.authorized_device_id(
        comanager_admin, "d_00000001", _OWNED_BY_OTHER, member,
        allow_admin=False) == "d_00000001"


def test_allow_admin_false_rejects_unknown_malformed_and_missing_principals():
    owner_calls = []
    member, member_calls = _recording_membership()

    def owner(device_id):
        owner_calls.append(device_id)
        return 9

    for bad in ("d_ZZZZZZZZ", "../x", "", None, 5):
        assert access.authorized_device_id(
            _USER, bad, owner, member, allow_admin=False) is None
    assert owner_calls == [] and member_calls == []
    assert access.authorized_device_id(
        _USER, "d_0000ffff", lambda _d: None, member, allow_admin=False) is None
    assert access.authorized_device_id(
        None, "d_00000001", _lookup, member, allow_admin=False) is None
    no_id = access.Principal("user", None, "x@example.com", "admin")
    assert access.authorized_device_id(
        no_id, "d_00000001", _lookup, member, allow_admin=False) is None


def test_the_default_still_admits_an_admin():
    assert access.authorized_device_id(_ADMIN, "d_00000002", _lookup) == "d_00000002"


def test_decide_with_the_manager_kind_refuses_a_pure_admin_everywhere():
    scoped = _acc(access.USER, _MANAGER)
    member, _calls = _recording_membership()
    for device_id in ("d_00000001", "d_00000002", "d_0000ffff"):
        assert access.decide(_ADMIN, scoped, device_id, _lookup, member) == access.NOT_FOUND
    # The admin is refused through decide, not only through the helper.
    assert access.decide(_ADMIN, _acc(access.USER, "device"), "d_00000002",
                         _lookup, member) == access.ALLOW


def test_decide_with_the_manager_kind_admits_owner_and_co_manager_only():
    scoped = _acc(access.USER, _MANAGER)
    member, _calls = _recording_membership()
    assert access.decide(None, scoped, "d_00000001", _lookup, member) == access.LOGIN
    assert access.decide(_USER, scoped, "d_00000001", _lookup, member) == access.ALLOW
    assert access.decide(_USER, scoped, "d_00000001", _OWNED_BY_OTHER, member) == access.ALLOW
    other = access.Principal("user", 11, "n@example.com", "user")
    assert access.decide(other, scoped, "d_00000001", _OWNED_BY_OTHER, member) == access.NOT_FOUND


def test_the_manager_kind_answers_alike_for_foreign_and_unknown_frames():
    scoped = _acc(access.USER, _MANAGER)
    member, _calls = _recording_membership()
    foreign = access.decide(_USER, scoped, "d_00000002", _lookup, member)
    unknown = access.decide(_USER, scoped, "d_0000ffff", _lookup, member)
    malformed = access.decide(_USER, scoped, "nope", _lookup, member)
    assert foreign == unknown == malformed == access.NOT_FOUND
