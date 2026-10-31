"""Behaviour of the console helpers: the lockout throttle, the audit
helpers and the one-shot flash cookie."""
import base64
import json
import threading
import types

import pytest

from companion import access, console_flash, i18n, prefs, throttle
from companion import audit
from server import fleet_db


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


# --- throttle ----------------------------------------------------------


def test_limit_failures_lock_a_key_and_it_unlocks_after_the_window():
    clock = FakeClock()
    gate = throttle.LockoutThrottle(limit=3, lockout_s=60, clock=clock)
    assert gate.locked_for("a") == 0
    assert gate.record_failure("a") is False
    assert gate.record_failure("a") is False
    assert gate.record_failure("a") is True
    assert gate.locked_for("a") == 60
    assert gate.locked_for("b") == 0
    clock.now += 20
    assert gate.locked_for("a") == 40
    clock.now += 40
    assert gate.locked_for("a") == 0
    # A fresh window starts from zero failures.
    assert gate.record_failure("a") is False


def test_a_failure_while_locked_does_not_extend_the_lockout():
    clock = FakeClock()
    gate = throttle.LockoutThrottle(limit=1, lockout_s=60, clock=clock)
    assert gate.record_failure("a") is True
    clock.now += 30
    assert gate.record_failure("a") is False
    assert gate.locked_for("a") == 30


def test_success_clears_the_counter_and_reset_clears_everything():
    gate = throttle.LockoutThrottle(limit=2, lockout_s=60, clock=FakeClock())
    gate.record_failure("a")
    gate.record_success("a")
    assert gate.record_failure("a") is False
    gate.record_failure("a")
    gate.record_failure("b")
    gate.reset()
    assert gate.locked_for("a") == 0
    assert gate.key_count() == 0


def test_stale_partial_counts_lapse():
    clock = FakeClock()
    gate = throttle.LockoutThrottle(limit=2, lockout_s=60, clock=clock)
    gate.record_failure("a")
    clock.now += 61
    assert gate.record_failure("a") is False
    assert gate.locked_for("a") == 0


def test_table_never_exceeds_max_keys_and_a_locked_key_outlives_idle_ones():
    gate = throttle.LockoutThrottle(limit=2, lockout_s=600, max_keys=5, clock=FakeClock())
    gate.record_failure("locked")
    gate.record_failure("locked")
    assert gate.locked_for("locked") > 0
    for index in range(200):
        gate.record_failure("idle-%d" % index)
        assert gate.key_count() <= 5
    assert gate.locked_for("locked") > 0


def test_idle_keys_are_evicted_before_least_recently_seen_locked_ones():
    clock = FakeClock()
    gate = throttle.LockoutThrottle(limit=2, lockout_s=600, max_keys=4, clock=clock)
    gate.record_failure("idle-a")
    gate.record_failure("locked-1")
    gate.record_failure("locked-1")
    gate.record_failure("idle-b")
    gate.record_failure("locked-2")
    gate.record_failure("locked-2")
    assert gate.key_count() <= 4
    assert gate.locked_for("locked-1") > 0
    assert gate.locked_for("locked-2") > 0
    for index in range(100):
        gate.record_failure("flood-%d" % index)
        assert gate.key_count() <= 4
    assert gate.key_count() == 4


def test_concurrent_failures_from_threads_never_lose_a_count():
    gate = throttle.LockoutThrottle(limit=10_000, lockout_s=60)
    per_thread = 500
    start = threading.Barrier(8)

    def hammer():
        start.wait()
        for _ in range(per_thread):
            gate.record_failure("one-key")

    workers = [threading.Thread(target=hammer) for _ in range(8)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert gate._entries["one-key"].failures == 8 * per_thread


# --- audit -------------------------------------------------------------


def _handler(state_dir, peer="127.0.0.1", xff=None, principal=None):
    headers = {"X-Forwarded-For": xff} if xff else {}
    return types.SimpleNamespace(
        client_address=(peer, 5555),
        headers=types.SimpleNamespace(get=lambda name, default=None: headers.get(name, default)),
        args=types.SimpleNamespace(state_dir=str(state_dir)),
        _safe_principal=lambda: principal)


ADMIN = access.Principal(access.KIND_USER, 7, "admin@example.org", access.ADMIN)


def test_actor_uses_the_signed_in_email_and_the_proxy_forwarded_address():
    handler = _handler("x", peer="127.0.0.1", xff="1.1.1.1, 203.0.113.9", principal=ADMIN)
    actor = audit.actor_for(handler)
    assert actor == fleet_db.AuditActor(7, "admin@example.org", "203.0.113.9")


def test_actor_ignores_a_forwarded_header_from_a_non_loopback_peer():
    handler = _handler("x", peer="198.51.100.4", xff="203.0.113.9", principal=ADMIN)
    assert audit.actor_for(handler).source_ip == "198.51.100.4"


def test_actor_without_a_principal_is_unknown():
    actor = audit.actor_for(_handler("x"))
    assert actor.user_id is None and actor.label == "unknown"


def _rows(state_dir):
    conn = fleet_db.connect(str(state_dir))
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM audit_log ORDER BY id")]
    finally:
        conn.close()


def test_record_in_rolls_back_with_the_caller_and_standalone_survives(tmp_path):
    handler = _handler(tmp_path, principal=ADMIN)
    conn = fleet_db.connect(str(tmp_path))
    try:
        with pytest.raises(RuntimeError):
            with fleet_db.transaction(conn):
                audit.record_in(handler, conn, "frame.retire", "device", "d_1", "ok")
                raise RuntimeError("action failed")
    finally:
        conn.close()
    assert _rows(tmp_path) == []
    audit.record_standalone(
        handler, "frame.retire", "device", "d_1", "failed", {"reason": "busy"})
    rows = _rows(tmp_path)
    assert [(row["action"], row["outcome"]) for row in rows] == [("frame.retire", "failed")]
    assert rows[0]["actor_label"] == "admin@example.org"
    assert json.loads(rows[0]["detail"]) == {"reason": "busy"}


def test_record_in_commits_with_the_caller(tmp_path):
    handler = _handler(tmp_path, principal=ADMIN)
    conn = fleet_db.connect(str(tmp_path))
    try:
        with fleet_db.transaction(conn):
            audit.record_in(handler, conn, "user.disable", "user", "3", "ok")
    finally:
        conn.close()
    assert [row["action"] for row in _rows(tmp_path)] == ["user.disable"]


def test_no_forbidden_value_reaches_the_audit_table(tmp_path):
    forbidden = ["ABCD-EFGH", "sekret-token-value", "guess-1234"]
    handler = _handler(tmp_path, principal=ADMIN)
    audit.record_standalone(
        handler, "pairing.claim", "pending", "p_1", "failed", {"reason": "invalid"})
    dump = json.dumps(_rows(tmp_path))
    for value in forbidden:
        assert value not in dump


# --- flash -------------------------------------------------------------

TITLE = i18n.Message("testflash.title", "Moved {name}")
DETAIL = i18n.Message("testflash.detail", "To {owner}")


@pytest.fixture(autouse=True)
def _english_and_flash_key():
    prefs.set_request_prefs(lang="en")
    console_flash.register_flash("test_ok", "success", TITLE, DETAIL)
    console_flash.register_flash("test_err", "error", TITLE, None)
    yield
    console_flash._REGISTRY.pop("test_ok", None)
    console_flash._REGISTRY.pop("test_err", None)


def _cookie_request(set_cookie_value):
    return set_cookie_value.split(";", 1)[0]


def test_queued_cookie_is_http_only_same_site_strict_and_short_lived():
    header = console_flash.queue_flash("test_ok", name="Kitchen", owner="a@b.c")
    assert header.startswith("sp_flash=")
    assert "HttpOnly" in header and "SameSite=Strict" in header
    assert "Path=/" in header and "Max-Age=60" in header


def test_take_flash_renders_once_and_clears_the_cookie():
    header = console_flash.queue_flash("test_ok", name="Kitchen", owner="a@b.c")
    markup, clear = console_flash.take_flash(_cookie_request(header))
    assert "Moved Kitchen" in markup and "To a@b.c" in markup
    assert "toast--success" in markup and "data-toast-autohide" in markup
    assert "Max-Age=0" in clear and clear.startswith("sp_flash=")
    assert console_flash.take_flash(None) == ("", None)


def test_error_flash_never_auto_hides():
    header = console_flash.queue_flash("test_err", name="Kitchen")
    markup, _clear = console_flash.take_flash(_cookie_request(header))
    assert "toast--error" in markup and "autohide" not in markup


@pytest.mark.parametrize("value", [
    "!!!not-base64!!!",
    base64.urlsafe_b64encode(b"[1, 2]").decode(),
    base64.urlsafe_b64encode(json.dumps({"k": "nope", "p": {}}).encode()).decode(),
    "A" * 2000,
])
def test_unknown_tampered_or_oversize_values_render_nothing(value):
    markup, clear = console_flash.take_flash("sp_flash=" + value)
    assert markup == ""
    assert clear is not None


def test_parameters_are_html_escaped_and_no_format_string_runs():
    header = console_flash.queue_flash(
        "test_ok", name="<script>alert(1)</script>", owner="{name.__class__}")
    markup, _clear = console_flash.take_flash(_cookie_request(header))
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "__class__" in markup


def test_oversize_parameters_are_dropped_not_truncated_into_a_bad_cookie():
    many = {"p%d" % index: "x" * 500 for index in range(8)}
    header = console_flash.queue_flash("test_ok", **many)
    value = header.split(";", 1)[0].split("=", 1)[1]
    assert len(value) <= console_flash.MAX_COOKIE_VALUE_BYTES
    markup, _clear = console_flash.take_flash("sp_flash=" + value)
    assert "Moved" in markup
