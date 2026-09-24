"""One pytest test per legacy companion harness - each still a standalone
`check()`/`EXPECTED_CHECK_COUNT`/`main()` script (their migration is Phase
33 scope), run as a real subprocess and asserted only on exit code, until
Phase 33 rewrites them as native pytest tests. This module is what makes
those 9 files reachable through `pytest -n auto` without pytest ever
importing them directly as test modules - conftest.py's collect_ignore
keeps them (and their shared helper module) out of collection so this file
is the only path to them.
"""

import os
import re
import signal
import subprocess
import sys

import pytest

from skypane_test_support import LEGACY_COMPANION_HARNESSES, REPO_ROOT, child_env

pytestmark = pytest.mark.legacy_harness

_COMPANION_DIR = os.path.join(REPO_ROOT, "companion")

# The browser harnesses exit 0 after printing a line starting "SKIP " when
# Playwright is missing or Chromium cannot launch - without this, that
# vacuous exit 0 would read as ~90 browser checks passing.
_HARNESS_SKIP_LINE = re.compile(r"(?m)^SKIP .*$")


def _browser_required():
    """True in CI (GitHub sets CI=true) or with SKYPANE_REQUIRE_BROWSER=1:
    there, a harness that could not launch Chromium is a failure, not a
    skip. Locally it stays a visible pytest skip.
    """
    return (
        os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1"
        or os.environ.get("CI", "").lower() == "true"
    )


@pytest.mark.parametrize(
    "harness",
    LEGACY_COMPANION_HARNESSES,
    ids=[os.path.basename(h)[:-3] for h in LEGACY_COMPANION_HARNESSES],
)
def test_legacy_companion_harness_exits_zero(harness, tmp_path):
    timeout_s = float(os.environ.get("HARNESS_TIMEOUT_S", "600"))
    out_path = tmp_path / "output.log"

    with open(out_path, "wb") as out_fh:
        proc = subprocess.Popen(
            [sys.executable, harness],
            cwd=REPO_ROOT,
            stdout=out_fh,
            stderr=subprocess.STDOUT,
            # 32-11-PLAN.md Task 2 (TST-03): every legacy companion harness,
            # and every process it starts (their own Harness classes copy
            # this env), runs under the no-network guard. Fake providers are
            # NOT enabled here - only test_companion_app.py's own Harness
            # enables them (Task 1) - so a harness that reaches a provider
            # without asking for the fake fails loudly instead of silently
            # succeeding.
            env=child_env(),
            # Own process group, same reason the prior hand-rolled test
            # runner's own _run_one() (retired by 32-13-PLAN.md) used one:
            # a timeout must take down the harness AND
            # any child server it spawned (companion/app.py,
            # stub-server/byos_server.py), or that child is orphaned, still
            # bound to its port.
            start_new_session=True,
        )
        try:
            returncode = proc.wait(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            proc.wait()
            returncode = proc.returncode
            timed_out = True

    output = out_path.read_bytes().decode(errors="replace")
    last_lines = "\n".join(output.splitlines()[-200:])

    if timed_out:
        pytest.fail(
            "%s did not exit within %.0fs, killed - last 200 lines:\n%s"
            % (harness, timeout_s, last_lines)
        )

    assert returncode == 0, (
        "%s exited %d - last 200 lines:\n%s" % (harness, returncode, last_lines)
    )

    skip_line = _HARNESS_SKIP_LINE.search(output)
    if skip_line:
        if _browser_required():
            pytest.fail(
                "%s skipped itself, but CI / SKYPANE_REQUIRE_BROWSER=1 requires "
                "it to run - last 200 lines:\n%s" % (harness, last_lines)
            )
        pytest.skip("%s: %s" % (harness, skip_line.group(0)))


def test_legacy_harness_list_matches_disk():
    # SEC-01 (37-01-PLAN.md): test_login_throttle.py is the first native
    # pytest test module under companion/, collected directly by pytest
    # rather than run through this shim — it is exempted here the same
    # way test_browser_ux_helpers.py (a shared helper, not a harness in
    # its own right) already is.
    on_disk = {
        "companion/%s" % name
        for name in os.listdir(_COMPANION_DIR)
        if name.startswith("test_")
        and name.endswith(".py")
        and name not in (
            "test_legacy_harness_shim.py",
            "test_browser_ux_helpers.py",
            "test_login_throttle.py",
        )
    }
    assert on_disk == set(LEGACY_COMPANION_HARNESSES)
