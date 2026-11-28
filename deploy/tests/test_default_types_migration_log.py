# SPDX-License-Identifier: AGPL-3.0-only
"""The deploy-time migration command prints the default-type lines the operator
reads in the activate log: the dry run says what it would clear, the real run
what it cleared, then the defaults it would set or set by rule, a second run that there is
nothing to do."""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _migrate(state_dir, *extra):
    done = subprocess.run(
        [sys.executable, "-m", "server.fleet_migrate", "--state-dir", str(state_dir),
         "--owner-email", "owner@example.test", *extra],
        cwd=REPO, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return [line for line in done.stdout.splitlines() if line.startswith("airline default types:")]


def test_the_activate_log_carries_the_default_type_lines(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "airline_default_types.json").write_text(json.dumps({"air-france": "B738"}))
    dry = _migrate(state, "--dry-run")
    assert dry[:2] == [
        "airline default types: would clear 1",
        "airline default types: would clear air-france: B738"]
    assert "airline default types: would set air-france: A320 (rule a)" in dry
    assert any(line.startswith("airline default types: would set ") and line[len(
        "airline default types: would set "):].isdigit() for line in dry)
    assert json.loads((state / "airline_default_types.json").read_text()) == {"air-france": "B738"}
    real = _migrate(state)
    assert real[0] == "airline default types: cleared 1"
    assert "airline default types: set air-france: A320 (rule a)" in real
    assert json.loads((state / "airline_default_types.json").read_text())["air-france"] == "A320"
    assert (state / "airline_default_types_set.json").is_file()
    assert _migrate(state) == [
        "airline default types: nothing to do", "airline default types: nothing to do"]
