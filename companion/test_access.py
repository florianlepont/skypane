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


def test_home_for():
    assert access.home_for(_USER) == "/account"
    assert access.home_for(_ADMIN) == "/"
