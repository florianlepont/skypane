"""The cross-process poll-cycle lock, companion side: POST /poll-now never
blocks a request thread on poll.lock. With the lock held by another
process, it answers the existing poll_already_running flash immediately
(never waiting for the lock); the busy attempt does not consume the
poll-trigger cooldown, so the very next request, once the lock is free,
still gets a real cycle.
"""
import os
import time

from companion_app_server import http_request, login

from server import atomic_io


def test_poll_now_answers_already_running_without_waiting_on_a_held_lock(make_app_server):
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    cookie = login(server)

    lock_path = os.path.join(server.state_dir, "poll.lock")
    with atomic_io.exclusive_lock(lock_path, 5):
        start = time.monotonic()
        status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=cookie)
        elapsed = time.monotonic() - start
        assert status == 303, "expected a 303 redirect, got %d" % status
        location = headers.get("Location", "")
        assert "flash=poll_already_running" in location, (
            "expected the poll_already_running flash key while poll.lock is held by another "
            "process, got %r" % location)
        assert elapsed < 3.0, (
            "expected POST /poll-now to answer without waiting on the held lock, took %.2fs"
            % elapsed)

    # The busy attempt above must not have consumed the poll-trigger
    # cooldown: once poll.lock is free, the very next trigger still runs a
    # real cycle and gets poll_triggered, never poll_cooldown.
    status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_triggered" in location, (
        "expected poll_triggered once poll.lock is free (the busy attempt above must not have "
        "consumed the cooldown), got %r" % location)
