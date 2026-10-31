"""Admin console routes for the users area: the Users page, invite, role
change, disable, enable and identity unlink.

Security invariants:
- Every route is admin-only and every POST carries a CSRF token.
- A role is read only from the local user row. The accepted role names are
  exactly `user` and `admin`.
- The user id in the path is shape-checked (digits only) before any lookup.
- Each change and its audit row share one `BEGIN IMMEDIATE` transaction, so
  the last-administrator and self-action guards cannot be raced. A refusal
  rolls the change back and is audited afterwards as a denied row.
- Disabling or unlinking deletes the user's sessions in the same transaction.
- The page never shows the issuer or subject of a linked identity.
"""
import datetime
import re
import sqlite3

from companion import audit, console_flash, i18n, route_types
from companion.pages import users_page
from server import fleet_db, fleet_sessions

# Same literals as companion/console_routes.py (which imports this module, so
# it cannot be imported at module level); a test pins that the two agree.
USERS_PATH = "/users"
USERS_INVITE_PATH = "/users/invite"
USER_ACTION_PREFIX = "/users/"
ROLE_SUFFIX = "/role"
DISABLE_SUFFIX = "/disable"
ENABLE_SUFFIX = "/enable"
UNLINK_SUFFIX = "/unlink"

_USER_ID_RE = re.compile(r"\A[0-9]{1,9}\Z")
_MAX_EMAIL_CHARS = 254
_ROLES = (users_page.ROLE_USER, users_page.ROLE_ADMIN)

FLASH_INVITED = "users.invited"
FLASH_ROLE_SAVED = "users.role_saved"
FLASH_DISABLED = "users.disabled"
FLASH_ENABLED = "users.enabled"
FLASH_UNLINKED = "users.unlinked"
FLASH_LAST_ADMIN = "users.last_admin"
FLASH_SELF_ACTION = "users.self_action"
FLASH_NOT_FOUND = "users.not_found"
FLASH_NOT_LINKED = "users.not_linked"
FLASH_BAD_ROLE = "users.bad_role"

_REFUSED_TITLE = i18n.msg("admin_users.flash_action_refused", "Action refused")
console_flash.register_flash(
    FLASH_INVITED, "success",
    i18n.msg("admin_users.flash_invitation_saved", "Invitation saved"),
    i18n.msg("admin_users.flash_invitation_saved_detail", "{email} can now sign in as {role}."))
console_flash.register_flash(
    FLASH_ROLE_SAVED, "success",
    i18n.msg("admin_users.flash_role_saved", "Role saved"),
    i18n.msg("admin_users.flash_role_saved_detail", "{email} is now {role}."))
console_flash.register_flash(
    FLASH_DISABLED, "success",
    i18n.msg("admin_users.flash_user_disabled", "User disabled"),
    i18n.msg(
        "admin_users.flash_user_disabled_detail",
        "{email} is signed out and cannot sign in."))
console_flash.register_flash(
    FLASH_ENABLED, "success",
    i18n.msg("admin_users.flash_user_enabled", "User enabled"),
    i18n.msg("admin_users.flash_user_enabled_detail", "{email} can sign in again."))
console_flash.register_flash(
    FLASH_UNLINKED, "success",
    i18n.msg("admin_users.flash_identity_unlinked", "Identity unlinked"),
    i18n.msg(
        "admin_users.flash_identity_unlinked_detail",
        "{email} is signed out and will be re-linked at next sign-in."))
console_flash.register_flash(
    FLASH_LAST_ADMIN, "error", _REFUSED_TITLE,
    i18n.msg(
        "admin_users.flash_last_admin_detail",
        "At least one active administrator must remain."))
console_flash.register_flash(
    FLASH_SELF_ACTION, "error", _REFUSED_TITLE,
    i18n.msg(
        "admin_users.flash_self_action_detail",
        "You cannot disable or demote yourself."))
console_flash.register_flash(
    FLASH_NOT_FOUND, "error",
    i18n.msg("admin_users.flash_user_not_found", "User not found"),
    i18n.msg(
        "admin_users.flash_user_not_found_detail",
        "It may already have been changed. Nothing was modified."))
console_flash.register_flash(
    FLASH_NOT_LINKED, "error",
    i18n.msg("admin_users.flash_nothing_to_unlink", "Nothing to unlink"),
    i18n.msg(
        "admin_users.flash_nothing_to_unlink_detail",
        "That user has no linked identity. Nothing was modified."))
console_flash.register_flash(
    FLASH_BAD_ROLE, "error",
    i18n.msg("admin_users.flash_choose_a_role", "Choose a role"),
    i18n.msg(
        "admin_users.flash_choose_a_role_detail",
        "The role must be User or Administrator. Nothing was modified."))


class _UnknownUser(Exception):
    """The target user row does not exist."""


class _NotLinked(Exception):
    """The target user has no linked identity."""


# ---- page ---------------------------------------------------------------


def _build_rows(conn, actor_id):
    raw = fleet_db.list_users_with_frame_counts(conn)
    active_admins = fleet_db.count_active_admins(conn)
    rows = []
    for row in raw:
        is_active_admin = row["role"] == "admin" and not row["disabled"]
        rows.append(users_page.UserRow(
            user_id=int(row["id"]), email=str(row["email"]), role=str(row["role"]),
            disabled=bool(row["disabled"]), has_identity=bool(row["has_identity"]),
            last_seen=None if row["last_seen_at"] is None else float(row["last_seen_at"]),
            frame_count=int(row["frame_count"]), is_self=int(row["id"]) == actor_id,
            is_last_admin=is_active_admin and active_admins <= 1))
    return tuple(rows)


def _view(h, **invite_state):
    principal = h._safe_principal()
    actor_id = principal.user_id if principal is not None else None
    conn = fleet_db.connect(h.args.state_dir)
    try:
        rows = _build_rows(conn, actor_id)
    finally:
        conn.close()
    return users_page.UsersView(
        rows=rows, now=datetime.datetime.now(datetime.timezone.utc), **invite_state)


def _render(h, status=200, **invite_state):
    from companion import console_routes
    return h._console_page(
        console_routes.USERS_ROUTE, None,
        lambda: users_page.render(_view(h, **invite_state)),
        users_page.USERS_PURPOSE, status=status)


def handle_users_get(h, m):
    return _render(h)


# ---- invite -------------------------------------------------------------


def handle_invite(h, m):
    form = h.read_form()
    raw_email = form.get(users_page.EMAIL_FIELD, "").strip()
    role = form.get(users_page.ROLE_FIELD, "")
    errors = {}
    email = None
    if len(raw_email) <= _MAX_EMAIL_CHARS:
        try:
            email = fleet_db.normalize_email(raw_email)
        except ValueError:
            email = None
    if email is None:
        errors["email_error"] = i18n.t(users_page.INVITE_EMAIL_ERROR)
    if role not in _ROLES:
        errors["role_error"] = i18n.t(users_page.INVITE_ROLE_ERROR)
    if errors:
        return _invite_failure(h, raw_email, role, errors)
    conn = fleet_db.connect(h.args.state_dir)
    try:
        try:
            with fleet_db.transaction(conn):
                user_id = fleet_db.add_user(conn, email, role)
                audit.record_in(
                    h, conn, "user.invite", "user", str(user_id), "ok", {"role": role})
        except sqlite3.IntegrityError:
            return _invite_failure(
                h, raw_email, role,
                {"email_error": i18n.t(users_page.INVITE_DUPLICATE_ERROR)})
    finally:
        conn.close()
    return h.redirect(USERS_PATH, set_cookie=console_flash.queue_flash(
        FLASH_INVITED, email=email, role=users_page.role_name(role)))


def _invite_failure(h, raw_email, role, errors):
    return _render(
        h, status=400, email_value=raw_email[:_MAX_EMAIL_CHARS],
        role_selected=role if role in _ROLES else users_page.ROLE_USER, **errors)


# ---- row actions --------------------------------------------------------


def _back(flash_key, **params):
    return console_flash.queue_flash(flash_key, **params)


def _target_id(m):
    """The numeric user id from the path, or None for any other shape."""
    return int(m.captured) if _USER_ID_RE.match(m.captured) else None


def _actor_id(h):
    principal = h._safe_principal()
    return None if principal is None else principal.user_id


def _run_action(h, user_id, action, change, success_flash):
    """Run `change(conn, actor_id, row)` and write its audit row in one
    transaction. `change` returns (audit detail, flash params) or raises a
    guard error, in which case nothing is kept and a denied row is written.
    Returns the redirect response.
    """
    conn = fleet_db.connect(h.args.state_dir)
    try:
        try:
            with fleet_db.transaction(conn):
                row = conn.execute(
                    "SELECT id, email, role, disabled, iss, sub FROM users WHERE id = ?",
                    (user_id,)).fetchone()
                if row is None:
                    raise _UnknownUser()
                detail, params = change(conn, _actor_id(h), row)
                if detail is not None:
                    audit.record_in(h, conn, action, "user", str(user_id), "ok", detail or None)
        except _UnknownUser:
            return h.redirect(USERS_PATH, set_cookie=_back(FLASH_NOT_FOUND))
        except _NotLinked:
            return h.redirect(USERS_PATH, set_cookie=_back(FLASH_NOT_LINKED))
        except (fleet_db.LastAdminError, fleet_db.SelfActionError) as exc:
            reason = "self" if isinstance(exc, fleet_db.SelfActionError) else "last_admin"
            audit.record_standalone(
                h, action, "user", str(user_id), "denied", {"reason": reason})
            flash = FLASH_SELF_ACTION if reason == "self" else FLASH_LAST_ADMIN
            return h.redirect(USERS_PATH, set_cookie=_back(flash))
    finally:
        conn.close()
    return h.redirect(USERS_PATH, set_cookie=_back(success_flash, **params))


def _unknown_id(h):
    return h.redirect(USERS_PATH, set_cookie=_back(FLASH_NOT_FOUND))


def handle_role(h, m):
    user_id = _target_id(m)
    if user_id is None:
        return _unknown_id(h)
    role = h.read_form().get(users_page.ROLE_FIELD, "")
    if role not in _ROLES:
        return h.redirect(USERS_PATH, set_cookie=_back(FLASH_BAD_ROLE))

    def change(conn, actor_id, row):
        if row["role"] == role:
            return None, {"email": row["email"], "role": users_page.role_name(role)}
        fleet_db.set_user_role_guarded(conn, actor_id, user_id, role)
        return (
            {"from": row["role"], "to": role},
            {"email": row["email"], "role": users_page.role_name(role)})

    return _run_action(h, user_id, "user.role", change, FLASH_ROLE_SAVED)


def handle_disable(h, m):
    user_id = _target_id(m)
    if user_id is None:
        return _unknown_id(h)

    def change(conn, actor_id, row):
        fleet_db.set_user_disabled_guarded(conn, actor_id, user_id, True)
        return {}, {"email": row["email"]}

    return _run_action(h, user_id, "user.disable", change, FLASH_DISABLED)


def handle_enable(h, m):
    user_id = _target_id(m)
    if user_id is None:
        return _unknown_id(h)

    def change(conn, actor_id, row):
        if not row["disabled"]:
            return None, {"email": row["email"]}
        fleet_db.set_user_disabled_guarded(conn, actor_id, user_id, False)
        return {}, {"email": row["email"]}

    return _run_action(h, user_id, "user.enable", change, FLASH_ENABLED)


def handle_unlink(h, m):
    user_id = _target_id(m)
    if user_id is None:
        return _unknown_id(h)

    def change(conn, actor_id, row):
        if row["iss"] is None and row["sub"] is None:
            raise _NotLinked()
        # The same effect as `fleet_sessions.unlink_identity`, which opens a
        # transaction of its own and so cannot share the audit row's.
        fleet_sessions.delete_sessions_for_user(conn, user_id)
        conn.execute("UPDATE users SET iss = NULL, sub = NULL WHERE id = ?", (user_id,))
        return {}, {"email": row["email"]}

    return _run_action(h, user_id, "user.unlink", change, FLASH_UNLINKED)


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(USERS_PATH), handle_users_get, route_types.ADMIN_ONLY),
    route_types.Route(
        "POST", route_types.Exact(USERS_INVITE_PATH), handle_invite,
        route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(USER_ACTION_PREFIX, ROLE_SUFFIX), handle_role,
        route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(USER_ACTION_PREFIX, DISABLE_SUFFIX),
        handle_disable, route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(USER_ACTION_PREFIX, ENABLE_SUFFIX),
        handle_enable, route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(USER_ACTION_PREFIX, UNLINK_SUFFIX),
        handle_unlink, route_types.ADMIN_ONLY, csrf=True),
)
