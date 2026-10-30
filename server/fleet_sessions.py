#!/usr/bin/env python3
"""Server-side sessions and invite-only identity linking for the companion.

Leaf module: stdlib plus `server.fleet_db`. It never imports the companion,
the poll loop, or the byos server.

Invariants:
- Only sha256(token) is ever stored or passed in; the raw token never
  reaches this module or the database.
- A session carries no role and no disabled flag. Both are read fresh from
  `users` on every lookup, so a role change or a disable applies to the
  next request.
- Lifetime is absolute (30 days) and idle (7 days); an expired session is
  deleted on sight.
- Nothing here creates a user. A login is accepted only for a row an admin
  already created: first by its stored (iss, sub), otherwise by a verified
  email on a row that is still unlinked and enabled, linked exactly once.
- All times are integer epoch seconds passed in by the caller.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import NamedTuple

# Same repo-root sys.path bootstrap as server/fleet_db.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import fleet_db  # noqa: E402

ABSOLUTE_LIFETIME_S = 30 * 86400
IDLE_TIMEOUT_S = 7 * 86400
# last_seen_at is rewritten at most this often, to avoid a write per request.
TOUCH_INTERVAL_S = 300

PRINCIPAL_USER = "user"
PRINCIPAL_LEGACY_ADMIN = "legacy-admin"


class SessionRecord(NamedTuple):
    user_id: int | None
    principal: str
    email: str | None
    role: str
    created_at: int
    expires_at: int


class LoginOutcome(NamedTuple):
    user_id: int | None
    # ok, linked, unknown, unverified_email, email_linked_other, disabled
    reason: str


def create_session(
    conn: sqlite3.Connection,
    token_hash: str,
    *,
    user_id: int | None,
    principal: str,
    now: int,
    replace_hash: str | None = None,
) -> None:
    """Store a session, atomically dropping the one it replaces (rotation)."""
    with fleet_db.transaction(conn):
        if replace_hash is not None:
            conn.execute("DELETE FROM sessions WHERE id_hash = ?", (replace_hash,))
        conn.execute(
            "INSERT INTO sessions "
            "(id_hash, user_id, principal, created_at, last_seen_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token_hash, user_id, principal, now, now, now + ABSOLUTE_LIFETIME_S),
        )


def lookup_session(
    conn: sqlite3.Connection, token_hash: str, now: int
) -> SessionRecord | None:
    """The live session for a token hash, or None (expired rows are deleted)."""
    row = conn.execute(
        "SELECT s.principal, s.user_id, s.created_at, s.last_seen_at, "
        "s.expires_at, u.email AS email, u.role AS role, u.disabled AS disabled "
        "FROM sessions s LEFT JOIN users u ON u.id = s.user_id "
        "WHERE s.id_hash = ?",
        (token_hash,),
    ).fetchone()
    if row is None:
        return None
    if now >= row["expires_at"] or now - row["last_seen_at"] >= IDLE_TIMEOUT_S:
        _discard_session(conn, token_hash)
        return None
    if row["principal"] == PRINCIPAL_USER:
        if row["role"] is None:
            _discard_session(conn, token_hash)
            return None
        if row["disabled"]:
            return None
    if now - row["last_seen_at"] > TOUCH_INTERVAL_S:
        try:
            conn.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE id_hash = ?",
                (now, token_hash),
            )
        except sqlite3.OperationalError:
            # Read-only store (unwritable state dir): the session is still
            # valid, only the idle clock cannot advance.
            pass
    is_user = row["principal"] == PRINCIPAL_USER
    return SessionRecord(
        user_id=row["user_id"],
        principal=str(row["principal"]),
        email=str(row["email"]) if is_user else None,
        role=str(row["role"]) if is_user else "admin",
        created_at=int(row["created_at"]),
        expires_at=int(row["expires_at"]),
    )


def _discard_session(conn: sqlite3.Connection, token_hash: str) -> None:
    """Best-effort cleanup of a dead session found during a lookup. A
    read-only store (unwritable state dir) cannot delete; the row stays and
    the lookup still reports no session.
    """
    try:
        delete_session(conn, token_hash)
    except sqlite3.OperationalError:
        pass


def delete_session(conn: sqlite3.Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE id_hash = ?", (token_hash,))


def delete_sessions_for_user(conn: sqlite3.Connection, user_id: int) -> int:
    """Drop every session of a user; joins a caller's open transaction."""
    return conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,)).rowcount


def prune_expired(conn: sqlite3.Connection, now: int) -> int:
    """Delete sessions past their absolute or idle limit; returns the count."""
    return conn.execute(
        "DELETE FROM sessions WHERE expires_at <= ? OR last_seen_at <= ?",
        (now, now - IDLE_TIMEOUT_S),
    ).rowcount


def unlink_identity(conn: sqlite3.Connection, email: str) -> bool:
    """Clear a user's (iss, sub) and sessions so they can be linked afresh.

    Opens its own transaction. Returns True when a link was cleared, False
    for an unknown email or a user that was not linked.
    """
    normalized = fleet_db.normalize_email(email)
    with fleet_db.transaction(conn):
        row = conn.execute(
            "SELECT id, iss, sub FROM users WHERE email = ?", (normalized,)
        ).fetchone()
        if row is None:
            return False
        delete_sessions_for_user(conn, int(row["id"]))
        if row["iss"] is None and row["sub"] is None:
            return False
        conn.execute(
            "UPDATE users SET iss = NULL, sub = NULL WHERE id = ?", (row["id"],)
        )
        return True


def _by_identity(
    conn: sqlite3.Connection, iss: str, sub: str
) -> LoginOutcome | None:
    row = conn.execute(
        "SELECT id, disabled FROM users WHERE iss = ? AND sub = ?", (iss, sub)
    ).fetchone()
    if row is None:
        return None
    if row["disabled"]:
        return LoginOutcome(None, "disabled")
    return LoginOutcome(int(row["id"]), "ok")


def _link_by_email(
    conn: sqlite3.Connection, iss: str, sub: str, email: str
) -> LoginOutcome:
    try:
        normalized = fleet_db.normalize_email(email)
    except ValueError:
        return LoginOutcome(None, "unknown")
    row = conn.execute(
        "SELECT id, iss, sub, disabled FROM users WHERE email = ?", (normalized,)
    ).fetchone()
    if row is None:
        return LoginOutcome(None, "unknown")
    if row["iss"] is not None or row["sub"] is not None:
        return LoginOutcome(None, "email_linked_other")
    if row["disabled"]:
        return LoginOutcome(None, "disabled")
    cur = conn.execute(
        "UPDATE users SET iss = ?, sub = ? "
        "WHERE id = ? AND iss IS NULL AND sub IS NULL AND disabled = 0",
        (iss, sub, row["id"]),
    )
    if cur.rowcount != 1:
        return LoginOutcome(None, "email_linked_other")
    return LoginOutcome(int(row["id"]), "linked")


def resolve_login(
    conn: sqlite3.Connection,
    iss: str,
    sub: str,
    email: str | None,
    email_verified: object,
    now: int,
) -> LoginOutcome:
    """Map verified identity claims to an existing local user, or refuse.

    The stored (iss, sub) wins and the email is not consulted again. An
    unknown sub is linked only through a verified email on an enabled,
    still-unlinked row. `now` is accepted for interface symmetry with the
    session functions; resolution itself is time independent.
    """
    del now
    with fleet_db.transaction(conn):
        known = _by_identity(conn, iss, sub)
        if known is not None:
            return known
        if email_verified is not True:
            return LoginOutcome(None, "unverified_email")
        if not email:
            return LoginOutcome(None, "unknown")
        return _link_by_email(conn, iss, sub, email)
