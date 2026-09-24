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

from skypane_test_support import (
    LEGACY_COMPANION_HARNESSES,
    ORIGINAL_COMPANION_HARNESSES,
    REPO_ROOT,
    child_env,
)

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


_NON_LEGACY_MARKERS = ("EXPECTED_CHECK_COUNT", "def check(", "def main(")


def test_legacy_set_is_consistent_with_disk():
    """LEGACY_COMPANION_HARNESSES (derived from disk by
    skypane_test_support.legacy_companion_harnesses()) stays trustworthy:
    every legacy path is real, a harness a migration plan already
    finished leaves no legacy marker behind, and no new
    companion/test_*.py file hides a fresh legacy-style harness the shim
    and companion/test_suite_guards.py's exemption set would never see.
    """
    # (a) every legacy path exists.
    for relpath in LEGACY_COMPANION_HARNESSES:
        assert os.path.exists(os.path.join(REPO_ROOT, relpath)), (
            "%s is in LEGACY_COMPANION_HARNESSES but missing from disk" % (relpath,))

    legacy = set(LEGACY_COMPANION_HARNESSES)

    # (b) every ORIGINAL_COMPANION_HARNESSES entry that is NOT legacy is
    # either gone from disk (the chain's last plan deletes it outright)
    # or free of every legacy marker - a migration plan that finishes a
    # harness must not leave EXPECTED_CHECK_COUNT/check()/main() behind
    # for a later run to mistake as still-legacy.
    for relpath in ORIGINAL_COMPANION_HARNESSES:
        if relpath in legacy:
            continue
        full_path = os.path.join(REPO_ROOT, relpath)
        if not os.path.exists(full_path):
            continue
        with open(full_path, encoding="utf-8") as fh:
            source = fh.read()
        for marker in _NON_LEGACY_MARKERS:
            assert marker not in source, (
                "%s is no longer legacy but still contains %r" % (relpath, marker))

    # (c) no companion/test_*.py outside the 9 originals hides a new
    # legacy-style file - a new file could otherwise carry
    # EXPECTED_CHECK_COUNT without ever being tracked by the shim or the
    # guard's exemption set.
    originals = set(ORIGINAL_COMPANION_HARNESSES)
    for name in os.listdir(_COMPANION_DIR):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        relpath = "companion/%s" % (name,)
        if relpath in originals:
            continue
        with open(os.path.join(_COMPANION_DIR, name), encoding="utf-8") as fh:
            for line in fh:
                assert not line.startswith("EXPECTED_CHECK_COUNT"), (
                    "%s is not one of the 9 original harnesses but has a line starting "
                    "EXPECTED_CHECK_COUNT - a new legacy-style file must not hide here"
                    % (relpath,))
