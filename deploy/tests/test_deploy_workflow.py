"""deploy.yml: manual-only trigger, no environment, and the guard steps.

The guard steps' run: bodies are extracted from the workflow and executed
with bash against shims for git and gh, so no test touches the network.
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"
_DEPLOY_YML = _WORKFLOWS_DIR / "deploy.yml"
_CI_YML = _WORKFLOWS_DIR / "ci.yml"

_MAIN_REF_STEP = "Refuse to run from any ref other than main"
_GUARD_STEP = "Require the tip of main, the confirmation and a green CI run"
_KEY_STEP = "Load deployment SSH key into agent"

TIP = "0123456789abcdef0123456789abcdef01234567"
OTHER = "fedcba9876543210fedcba9876543210fedcba98"


def _step_run(name):
    lines = _DEPLOY_YML.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == f"- name: {name}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body = []
    for ln in lines[run + 1:]:
        if ln.strip() and len(ln) - len(ln.lstrip()) <= indent:
            break
        body.append(ln[indent + 2:] if ln.strip() else "")
    return "\n".join(body) + "\n"


def _step_line(name):
    lines = _DEPLOY_YML.read_text().splitlines()
    return next(i for i, ln in enumerate(lines) if ln.strip() == f"- name: {name}")


# --- structure ---


def test_trigger_is_workflow_dispatch_only():
    text = _DEPLOY_YML.read_text()
    on_block = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
    top_keys = re.findall(r"^  ([a-z_]+):", on_block, re.M)
    assert top_keys == ["workflow_dispatch"]
    assert not re.search(r"^\s*(push|pull_request|schedule|workflow_run):", text, re.M)


def test_no_environment_and_no_job_level_if():
    text = _DEPLOY_YML.read_text()
    assert "environment:" not in text
    assert not re.search(r"^    if:", text, re.M)


def test_permissions_and_concurrency():
    text = _DEPLOY_YML.read_text()
    assert "  contents: read\n  checks: read\n" in text
    assert "group: production-deploy" in text
    assert "cancel-in-progress: false" in text


def test_main_ref_step_runs_before_the_key_is_loaded():
    assert _step_line(_MAIN_REF_STEP) < _step_line(_KEY_STEP)
    assert _step_line(_GUARD_STEP) < _step_line(_KEY_STEP)


def test_secrets_are_only_on_env_or_with_lines():
    for ln in _DEPLOY_YML.read_text().splitlines():
        if "${{ secrets." in ln:
            assert re.match(r"^\s+(DEPLOY_[A-Z_]+|ssh-private-key): \$\{\{ secrets\.", ln), ln


def test_ci_workflow_no_longer_deploys():
    text = _CI_YML.read_text()
    assert "Deploy to production" not in text
    assert "secrets.DEPLOY_" not in text
    assert "environment:" not in text


# --- main-ref step ---


@pytest.mark.parametrize(
    "ref, expected_rc",
    [("refs/heads/main", 0), ("refs/heads/other", 1), ("refs/tags/v1", 1), ("", 1)],
)
def test_main_ref_step(ref, expected_rc):
    env = dict(os.environ, GITHUB_REF=ref)
    result = subprocess.run(
        ["bash", "-c", _step_run(_MAIN_REF_STEP)],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == expected_rc
    if expected_rc:
        assert "::error::" in result.stdout


# --- guard step against shims ---

_FAKE_GIT = """#!/bin/bash
case "$1" in
  ls-remote) printf '%s\\trefs/heads/main\\n' "$FAKE_TIP" ;;
  fetch) exit 0 ;;
  diff) exit "$FAKE_DIFF_RC" ;;
  *) exit 9 ;;
esac
"""

_FAKE_GH = """#!/bin/bash
printf '%s' "$FAKE_CONCLUSIONS"
"""


def _run_guard(tmp_path, *, tip=TIP, sha=TIP, confirm=None, ci_sha="",
               diff_rc=0, conclusions="success\n"):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("git", _FAKE_GIT), ("gh", _FAKE_GH)):
        shim = bindir / name
        shim.write_text(body)
        shim.chmod(0o755)
    env = dict(os.environ)
    env.update(
        PATH=str(bindir) + os.pathsep + env["PATH"],
        GITHUB_SHA=sha,
        GITHUB_REPOSITORY="owner/repo",
        CONFIRM_SHA=sha[:7] if confirm is None else confirm,
        CI_SHA=ci_sha,
        GH_TOKEN="not-a-token",
        FAKE_TIP=tip,
        FAKE_DIFF_RC=str(diff_rc),
        FAKE_CONCLUSIONS=conclusions,
    )
    return subprocess.run(
        ["bash", "-c", _step_run(_GUARD_STEP)],
        env=env, capture_output=True, text=True, timeout=30,
    )


def test_guard_passes_when_everything_holds(tmp_path):
    result = _run_guard(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "::error::" not in result.stdout


def test_guard_passes_with_ci_sha_and_only_unshipped_changes(tmp_path):
    result = _run_guard(tmp_path, ci_sha=OTHER, diff_rc=0)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "case",
    [
        dict(tip=OTHER),
        dict(confirm="abcdef0"),
        dict(confirm="0123456789"),
        dict(confirm="0123ABC"),
        dict(confirm=""),
        dict(conclusions=""),
        dict(conclusions="failure\n"),
        dict(conclusions="success\nfailure\n"),
        dict(conclusions="skipped\n"),
        dict(ci_sha="notahexsha"),
        dict(ci_sha=OTHER[:39]),
        dict(ci_sha=OTHER, diff_rc=1),
        dict(tip="garbage"),
    ],
    ids=lambda c: ",".join(f"{k}={v[:12] if isinstance(v, str) else v}" for k, v in c.items()),
)
def test_guard_refuses(tmp_path, case):
    result = _run_guard(tmp_path, **case)
    assert result.returncode != 0
    assert "::error::" in result.stdout
