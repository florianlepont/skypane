"""INT-01's reproduction: two OS processes, each 200 iterations of a locked
read-increment-save cycle against the same `poll_state.json`, must end at
counter == 400 with zero exceptions in either child and zero lost updates.

This is a REGRESSION test against the pre-`poll_cycle_lock()` code shape
(a fixed `poll_state.json.tmp` name, no cross-process lock): the child
script below falls back to a no-op context manager when
`poll_loop.poll_cycle_lock` does not exist yet, so this file's RED run
(recorded in the plan's own SUMMARY) demonstrates the bug this plan fixes,
not merely a missing attribute error.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LOCK_RACE_TEMPLATE = """
import contextlib
import sys
sys.path.insert(0, {repo_root!r})
import server.poll_loop as poll_loop

state_dir, count = sys.argv[1], int(sys.argv[2])

lock_ctx = getattr(poll_loop, "poll_cycle_lock", None) or (lambda sd: contextlib.nullcontext())

for _ in range(count):
    with lock_ctx(state_dir):
        state = poll_loop.load_poll_state(state_dir)
        state["counter"] = state.get("counter", 0) + 1
        poll_loop.save_poll_state(state_dir, state)
"""


def test_two_processes_x_200_locked_increments_end_at_400_no_lost_updates(tmp_path):
    state_dir = str(tmp_path)
    script = tmp_path / "_racer.py"
    script.write_text(_LOCK_RACE_TEMPLATE.format(repo_root=REPO_ROOT))

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT

    procs = [
        subprocess.Popen(
            [sys.executable, str(script), state_dir, "200"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    outcomes = [(p.wait(timeout=60), p.stdout.read(), p.stderr.read()) for p in procs]
    exit_codes = [code for code, _out, _err in outcomes]
    stderrs = [err for _code, _out, err in outcomes]
    assert exit_codes == [0, 0], (
        "expected both child processes to exit 0, got %r; stderr=%r" % (exit_codes, stderrs))
    assert all(not err for err in stderrs), (
        "expected empty stderr from both children, got %r" % (stderrs,))

    import server.poll_loop as poll_loop

    final_state = poll_loop.load_poll_state(state_dir)
    assert final_state.get("counter") == 400, (
        "expected the counter to end at 400 (two processes x 200 locked increments with zero "
        "lost updates), got %r" % (final_state.get("counter"),))
    leftovers = [name for name in os.listdir(state_dir) if name.endswith(".tmp")]
    assert leftovers == [], "expected no leftover .tmp file in state_dir, found %r" % (leftovers,)
