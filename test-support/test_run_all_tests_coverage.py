# SPDX-License-Identifier: AGPL-3.0-only
"""Behaviour of scripts/run-all-tests.sh's SKYPANE_COVERAGE switch.

The script is copied into a scratch tree (it deletes .coverage files in its
repository root) and pointed at a fake interpreter that prints the pytest
command line it would have run.
"""
import os
import pathlib
import shutil
import stat
import subprocess

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run-all-tests.sh"

_FAKE_PYTHON = """#!/bin/bash
case "$1" in
    -m) shift; echo "PYTEST $*"; echo "CORE=${COVERAGE_CORE:-unset}" ;;
    *ci_shards.py) echo "some_test.py" ;;
    *) exec python3 "$@" ;;
esac
"""


def _run(tmp_path, env_extra, *args):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "run-all-tests.sh"
    shutil.copy(_SCRIPT, script)
    fake = tmp_path / "fake-python"
    fake.write_text(_FAKE_PYTHON)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    (tmp_path / ".coverage").write_text("stale")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SKYPANE_", "COVERAGE_"))}
    env.update({"PYTHON": str(fake), **env_extra})
    return subprocess.run(["bash", str(script), *args], env=env, cwd=tmp_path,
                          capture_output=True, text=True, check=False)


def _pytest_line(result):
    return next(line for line in result.stdout.splitlines() if line.startswith("PYTEST"))


def test_default_run_measures_coverage_and_keeps_the_floor(tmp_path):
    result = _run(tmp_path, {})
    assert result.returncode == 0, result.stderr
    words = _pytest_line(result).split()
    assert "--cov" in words
    assert "--no-cov" not in words
    assert "--cov-report=term-missing:skip-covered" in words
    assert not any(w.startswith("--cov-fail-under") for w in words)
    assert "CORE=sysmon" in result.stdout


def test_on_is_the_same_as_unset(tmp_path):
    words = _pytest_line(_run(tmp_path, {"SKYPANE_COVERAGE": "on"})).split()
    assert "--cov" in words
    assert "--no-cov" not in words


def test_off_runs_without_tracing_and_without_a_floor(tmp_path):
    result = _run(tmp_path, {"SKYPANE_COVERAGE": "off"})
    assert result.returncode == 0, result.stderr
    words = _pytest_line(result).split()
    assert "--no-cov" in words
    assert "--cov" not in words
    assert not any(w.startswith("--cov-") for w in words)
    assert "coverage not measured" in result.stdout
    assert "CORE=unset" in result.stdout
    assert not (tmp_path / ".coverage").exists()


def test_off_keeps_the_junit_report_and_the_shard_selection(tmp_path):
    result = _run(tmp_path, {
        "SKYPANE_COVERAGE": "off",
        "SKYPANE_TEST_GROUP": "core",
        "SKYPANE_TEST_SHARD": "1/2",
        "SKYPANE_JUNIT_XML": "junit-core-1.xml",
    })
    assert result.returncode == 0, result.stderr
    words = _pytest_line(result).split()
    assert words[words.index("--junitxml") + 1] == "junit-core-1.xml"
    assert words[-1] == "some_test.py"
    assert "--no-cov" in words


def test_on_partial_run_still_writes_data_only(tmp_path):
    result = _run(tmp_path, {
        "SKYPANE_TEST_GROUP": "core", "SKYPANE_TEST_SHARD": "0/2"})
    words = _pytest_line(result).split()
    assert "--cov-fail-under=0" in words
    assert "--cov-report=" in words


def test_an_unknown_value_is_refused(tmp_path):
    result = _run(tmp_path, {"SKYPANE_COVERAGE": "false"})
    assert result.returncode == 2
    assert "SKYPANE_COVERAGE must be on or off" in result.stderr
