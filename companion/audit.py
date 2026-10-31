"""Audit-log helpers for console handlers.

The actor and source address come from the handler, never from request
fields a caller controls. No function here accepts a code, guess, token or
secret; `detail` carries non-secret facts only.
"""
from companion import auth
from server import fleet_db


def actor_for(handler):
    """The `fleet_db.AuditActor` for this request: the signed-in user's id
    and email, and the caller's address. `X-Forwarded-For` counts only when
    the TCP peer is loopback (the reverse proxy); see `auth.client_ip`.
    """
    principal = handler._safe_principal()
    source_ip = auth.client_ip(
        handler.client_address[0], handler.headers.get("X-Forwarded-For"))
    if principal is None:
        return fleet_db.AuditActor(None, "unknown", source_ip)
    return fleet_db.AuditActor(principal.user_id, principal.email or "unknown", source_ip)


def record_in(handler, conn, action, target_type, target_id, outcome, detail=None):
    """Append one row inside the caller's open transaction on `conn`, so it
    commits or rolls back together with the action it describes.
    """
    return fleet_db.audit_append(
        conn, actor_for(handler), action, target_type, target_id, outcome, detail)


def record_standalone(handler, action, target_type, target_id, outcome, detail=None):
    """Append one row in its own transaction on a fresh connection, for a
    failed or denied attempt recorded after the action's transaction rolled
    back (a row written inside it would roll back too).
    """
    actor = actor_for(handler)
    conn = fleet_db.connect(handler.args.state_dir)
    try:
        with fleet_db.transaction(conn):
            return fleet_db.audit_append(
                conn, actor, action, target_type, target_id, outcome, detail)
    finally:
        conn.close()
