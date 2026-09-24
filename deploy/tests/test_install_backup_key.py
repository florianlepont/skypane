"""deploy/tests/test_install_backup_key.py — deploy/backup/install-backup-key.sh
(SEC-04, D-05), run as a real subprocess against a tmp BACKUP_HOME with
SKYPANE_KEY_ALLOW_NONROOT=1 and a stub `chown` on PATH (the script's only
external command that needs real root). Also carries the text checks for
the SKYPANE_OFFBOX_MARKER doc block in deploy/skypane.env.example and the
CI shellcheck step in .github/workflows/ci.yml (37-RESEARCH.md CP-8,
SEC-04 D-07).
"""
import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "deploy" / "backup" / "install-backup-key.sh"
_ENV_EXAMPLE = _REPO_ROOT / "deploy" / "skypane.env.example"
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

_VALID_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyDataForTesting123 skypane-backup-pull@mac"
_VALID_KEY_2 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDifferentKeyData456789012 other@mac"


def _write_chown_stub(bindir):
    """A no-op chown stub: the script's only real-root-requiring call.
    Everything else it does (install -d, mktemp, mv, chmod) works fine
    unprivileged against a tmp BACKUP_HOME.
    """
    stub = bindir / "chown"
    stub.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
    stub.chmod(0o755)


@pytest.fixture
def key_env(tmp_path):
    backup_home = tmp_path / "backup-home"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _write_chown_stub(bindir)

    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["BACKUP_HOME"] = str(backup_home)
    env["SKYPANE_KEY_ALLOW_NONROOT"] = "1"
    return backup_home, env


def _run(key, env):
    return subprocess.run(
        ["bash", str(_SCRIPT), key],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _auth_keys_path(backup_home):
    return backup_home / ".ssh" / "authorized_keys"


def test_valid_key_installs_forced_command_line_mode_0644(key_env):
    backup_home, env = key_env
    result = _run(_VALID_KEY, env)
    assert result.returncode == 0, result.stderr

    auth_keys = _auth_keys_path(backup_home)
    lines = [ln for ln in auth_keys.read_text().splitlines() if ln]
    assert len(lines) == 1
    assert lines[0].startswith(
        'restrict,command="/usr/bin/python3 /usr/local/lib/skypane/backup_gate.py" ssh-ed25519'
    )
    assert (auth_keys.stat().st_mode & 0o777) == 0o644


def test_rerunning_replaces_never_duplicates(key_env):
    backup_home, env = key_env
    assert _run(_VALID_KEY, env).returncode == 0
    result = _run(_VALID_KEY_2, env)
    assert result.returncode == 0, result.stderr

    lines = [ln for ln in _auth_keys_path(backup_home).read_text().splitlines() if ln]
    assert len(lines) == 1
    assert "other@mac" in lines[0]
    assert "skypane-backup-pull@mac" not in lines[0]


@pytest.mark.parametrize(
    "bad_key",
    [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB foo@bar",
        'command="sh" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample foo@bar',
        'ssh-ed25519 AAAA"AAAA foo@bar',
        "ssh-ed25519 AAAA\\AAAA foo@bar",
    ],
    ids=["ssh-rsa", "pre-existing-options", "double-quote", "backslash"],
)
def test_rejected_keys_exit_nonzero_and_touch_nothing(key_env, bad_key):
    backup_home, env = key_env
    result = _run(bad_key, env)
    assert result.returncode != 0
    assert not _auth_keys_path(backup_home).exists()


def test_empty_argument_rejected(key_env):
    backup_home, env = key_env
    result = subprocess.run(
        ["bash", str(_SCRIPT)], env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert not _auth_keys_path(backup_home).exists()


def test_newline_embedded_in_key_rejected(key_env):
    # A shell argv element cannot itself contain a raw newline from the
    # caller's single-quoted paste without it being a *second* argument -
    # this proves the script only ever accepts and validates $1, so an
    # attempted multi-line paste is either a usage error (too many args
    # are just ignored, $1 alone is validated) or fails the single-line
    # regex outright.
    backup_home, env = key_env
    result = _run("ssh-ed25519 AAAA\nAAAA foo@bar", env)
    assert result.returncode != 0
    assert not _auth_keys_path(backup_home).exists()


def test_install_backup_key_sh_syntax():
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_env_example_documents_offbox_marker():
    text = _ENV_EXAMPLE.read_text()
    assert "SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull" in text


def test_env_example_header_says_root_owned_600_read_by_systemd():
    text = _ENV_EXAMPLE.read_text()
    assert "root:root" in text
    assert "0600" in text or "600" in text


def test_ci_yml_shellchecks_deploy_scripts():
    text = _CI_YML.read_text()
    assert "shellcheck" in text.lower()
    assert "deploy" in text
