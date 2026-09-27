#!/usr/bin/env python3
"""Guards that server/poll_loop.py is only an entrypoint, and that the
companion and the poll-cycle library depend on it in no direction:

  * importing companion.app never loads server.poll_loop
  * importing server.poll_cycle never loads server.poll_loop
  * server.poll_loop.run_once/PollBusy are the identical poll_cycle
    objects (the bindings main() needs), and poll_loop carries none of
    the transitional/removed names a caller might otherwise reach through
    it by habit
  * `python3 server/poll_loop.py --help` still works as the systemd
    entrypoint's own CLI, run from a cwd other than the repo root

Every subprocess check below proves this by importing fresh in a child
interpreter and inspecting sys.modules there, never by reading source
text - the same pattern companion/test_companion_app_03.py's own isolation
tests use.
"""
import json
import subprocess
import sys

from skypane_test_support import REPO_ROOT, child_env

import server.poll_cycle as poll_cycle
import server.poll_loop as poll_loop


def _run_child(script, cwd=None, timeout=60):
    return subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=cwd or REPO_ROOT,
        capture_output=True, text=True, timeout=timeout)


def test_companion_app_import_never_loads_poll_loop():
    """`import companion.app` in a fresh subprocess leaves server.poll_loop
    out of sys.modules - the companion reaches the poll cycle only through
    server.poll_cycle."""
    script = (
        "import json, sys\n"
        "import companion.app\n"
        "print(json.dumps('server.poll_loop' in sys.modules))\n"
    )
    result = _run_child(script)
    assert result.returncode == 0, result.stdout + result.stderr
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert loaded is False, (
        "expected importing companion.app to never pull in server.poll_loop, but it did")


def test_poll_cycle_import_never_loads_poll_loop():
    """`import server.poll_cycle` in a fresh subprocess leaves server.poll_loop
    out of sys.modules - poll_cycle never imports the entrypoint that wraps it."""
    script = (
        "import json, sys\n"
        "import server.poll_cycle\n"
        "print(json.dumps('server.poll_loop' in sys.modules))\n"
    )
    result = _run_child(script)
    assert result.returncode == 0, result.stdout + result.stderr
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert loaded is False, (
        "expected importing server.poll_cycle to never pull in server.poll_loop, but it did")


def test_poll_loop_run_once_and_pollbusy_are_the_poll_cycle_objects():
    """server.poll_loop.run_once/PollBusy - the two bindings main() needs -
    are the identical server.poll_cycle objects, not copies."""
    assert poll_loop.run_once is poll_cycle.run_once, (
        "expected poll_loop.run_once to be the identical poll_cycle.run_once object")
    assert poll_loop.PollBusy is poll_cycle.PollBusy, (
        "expected poll_loop.PollBusy to be the identical poll_cycle.PollBusy object")


def test_poll_loop_carries_none_of_the_transitional_or_removed_names():
    """poll_loop has no now_s/poll_cycle_lock/_save_to_gallery/write_panel_atomic
    (this plan's own transitional bindings, now removed) and no load_poll_state
    (moved to state_store well before this plan) - a caller must reach every one
    of these through server.poll_cycle or server.state_store, never through
    server.poll_loop."""
    removed_names = (
        "now_s", "poll_cycle_lock", "_save_to_gallery", "write_panel_atomic",
        "load_poll_state",
    )
    for name in removed_names:
        assert not hasattr(poll_loop, name), (
            "poll_loop.%s still exists - should be reached only through "
            "server.poll_cycle or server.state_store" % name)


def test_poll_loop_help_works_from_another_cwd(tmp_path):
    """`python3 server/poll_loop.py --help` exits 0 and prints --state-dir,
    run with cwd set to a directory other than the repo root - proves the
    entrypoint's own repo-root sys.path bootstrap, not an accident of the
    caller's cwd."""
    script_path = "%s/server/poll_loop.py" % REPO_ROOT
    result = subprocess.run(
        [sys.executable, script_path, "--help"], env=child_env(), cwd=str(tmp_path),
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--state-dir" in result.stdout, (
        "expected --help output to document --state-dir, got %r" % (result.stdout,))
