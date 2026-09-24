"""deploy/tests/test_provision.py — deploy/harden_sshd.sh (SEC-08, D-08)
run as a real subprocess against a fake sshd_config.d and stub sshd/
systemctl, plus text/syntax checks on deploy/provision.sh's release
layout, env ownership and skypane-backup changes (SEC-04, SEC-05,
SEC-07). provision.sh itself needs a real root machine to exercise
end-to-end (useradd/apt-get/ufw/systemctl are not something a sandboxed
test should run for real) — RESEARCH.md's own SEC-08 "Test in CI" note
says the same about the SSH step, which is exactly why it was extracted
into the small, self-contained harden_sshd.sh this file exercises for
real.
"""
import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEPLOY = _REPO_ROOT / "deploy"
_HARDEN_SH = _DEPLOY / "harden_sshd.sh"
_PROVISION_SH = _DEPLOY / "provision.sh"

_EXPECTED_DIRECTIVES = [
    "PermitRootLogin no",
    "PasswordAuthentication no",
    "KbdInteractiveAuthentication no",
    "PubkeyAuthentication yes",
    "PermitEmptyPasswords no",
    "X11Forwarding no",
    "MaxAuthTries 3",
]


def _write_stub(path, body):
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)


@pytest.fixture
def sshd_env(tmp_path):
    """A fake sshd_config.d tree, a main sshd_config carrying the real
    Ubuntu Include line, and stub sshd/systemctl binaries on a dedicated
    PATH. FAKE_SSHD_T_RC (env var, read by the stub) controls whether the
    stub's `sshd -t` call succeeds; every argv the stubs receive is
    appended to calls.log so tests can assert call order.
    """
    config_dir = tmp_path / "sshd_config.d"
    config_dir.mkdir()
    config = tmp_path / "sshd_config"
    config.write_text(
        "Include /etc/ssh/sshd_config.d/*.conf\n"
        "Subsystem sftp /usr/lib/openssh/sftp-server\n"
    )

    bindir = tmp_path / "bin"
    bindir.mkdir()
    call_log = tmp_path / "calls.log"
    call_log.write_text("")

    _write_stub(
        bindir / "sshd",
        "import os, sys\n"
        f"_LOG = {str(call_log)!r}\n"
        "with open(_LOG, 'a') as f:\n"
        "    f.write('sshd ' + ' '.join(sys.argv[1:]) + chr(10))\n"
        "if '-t' in sys.argv[1:]:\n"
        "    sys.exit(int(os.environ.get('FAKE_SSHD_T_RC', '0')))\n"
        "if '-T' in sys.argv[1:]:\n"
        "    sys.stdout.write('permitrootlogin no\\n')\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n",
    )
    _write_stub(
        bindir / "systemctl",
        "import sys\n"
        f"_LOG = {str(call_log)!r}\n"
        "with open(_LOG, 'a') as f:\n"
        "    f.write('systemctl ' + ' '.join(sys.argv[1:]) + chr(10))\n"
        "sys.exit(0)\n",
    )

    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["SSHD_CONFIG_DIR"] = str(config_dir)
    env["SSHD_CONFIG"] = str(config)
    env["SSHD_BIN"] = "sshd"
    env["SYSTEMCTL"] = "systemctl"

    return SimpleNamespace(
        config_dir=config_dir,
        config=config,
        dropin=config_dir / "00-skypane.conf",
        call_log=call_log,
        env=env,
    )


def _run_harden(sshd_env):
    return subprocess.run(
        ["bash", str(_HARDEN_SH)],
        env=sshd_env.env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_success_writes_exact_directives_mode_0644_and_reloads_after_validation(sshd_env):
    result = _run_harden(sshd_env)
    assert result.returncode == 0, result.stderr

    assert sshd_env.dropin.exists()
    lines = [ln for ln in sshd_env.dropin.read_text().splitlines() if ln]
    assert lines == _EXPECTED_DIRECTIVES
    assert (sshd_env.dropin.stat().st_mode & 0o777) == 0o644

    log_lines = sshd_env.call_log.read_text().splitlines()
    t_idx = next(i for i, ln in enumerate(log_lines) if ln.startswith("sshd -t"))
    reload_idx = next(
        i for i, ln in enumerate(log_lines)
        if ln.startswith("systemctl try-reload-or-restart ssh.service")
    )
    assert t_idx < reload_idx, "sshd -t must run before the reload"


def test_sshd_t_failure_restores_previous_dropin_and_never_reloads(sshd_env):
    previous_content = "# a previous, hand-written drop-in\nPermitRootLogin yes\n"
    sshd_env.dropin.write_text(previous_content)

    sshd_env.env["FAKE_SSHD_T_RC"] = "1"
    result = _run_harden(sshd_env)

    assert result.returncode != 0
    assert sshd_env.dropin.read_text() == previous_content
    assert "systemctl" not in sshd_env.call_log.read_text()


def test_sshd_t_failure_with_no_previous_dropin_removes_the_new_one(sshd_env):
    assert not sshd_env.dropin.exists()

    sshd_env.env["FAKE_SSHD_T_RC"] = "1"
    result = _run_harden(sshd_env)

    assert result.returncode != 0
    assert not sshd_env.dropin.exists()
    assert "systemctl" not in sshd_env.call_log.read_text()


def test_main_config_without_include_line_fails_loudly(tmp_path):
    config_dir = tmp_path / "sshd_config.d"
    config_dir.mkdir()
    config = tmp_path / "sshd_config"
    config.write_text("Subsystem sftp /usr/lib/openssh/sftp-server\n")

    env = dict(os.environ)
    env["SSHD_CONFIG_DIR"] = str(config_dir)
    env["SSHD_CONFIG"] = str(config)

    result = subprocess.run(
        ["bash", str(_HARDEN_SH)], env=env, capture_output=True, text=True, timeout=30,
    )

    assert result.returncode != 0
    assert "Include" in result.stderr
    assert not (config_dir / "00-skypane.conf").exists()


def test_harden_sshd_sh_syntax():
    result = subprocess.run(["bash", "-n", str(_HARDEN_SH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --- deploy/provision.sh: text checks + bash -n only (needs a real root
# machine to actually run — see module docstring). ---


def _provision_text():
    return _PROVISION_SH.read_text()


def test_provision_sh_syntax():
    result = subprocess.run(["bash", "-n", str(_PROVISION_SH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_provision_sh_calls_harden_sshd_with_no_swallowed_failure():
    text = _provision_text()
    assert "harden_sshd.sh" in text
    assert not re.search(r"reload ssh.*\|\|\s*true", text)


def test_provision_sh_no_longer_recursively_chowns_app_root():
    text = _provision_text()
    assert 'chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"' not in text


def test_provision_sh_env_file_root_owned_and_guarded_by_existence_check():
    text = _provision_text()
    assert 'if [ -f "${APP_ROOT}/skypane.env" ]' in text
    assert "chown root:root" in text
    assert "chmod 600" in text


def test_provision_sh_creates_release_layout_dir():
    text = _provision_text()
    assert '"${APP_ROOT}/releases"' in text


def test_provision_sh_no_longer_installs_units_or_caddyfile():
    text = _provision_text()
    assert "/etc/systemd/system/skypane-" not in text
    # The host Caddyfile is shared with other projects: provision.sh may
    # only read it (to print a reminder), never write it.
    assert 'HOST_CADDYFILE="/etc/caddy/Caddyfile"' in text
    for line in text.splitlines():
        code = line.split("#", 1)[0] if not line.lstrip().startswith("echo") else ""
        if "HOST_CADDYFILE" in code or "/etc/caddy/Caddyfile" in code:
            assert not re.search(r">\s*\S*(HOST_CADDYFILE|/etc/caddy/Caddyfile)", code), line
            assert not re.search(r"\b(cp|mv|install|tee|sed -i|rm)\b", code), line


def test_provision_sh_creates_caddy_sites_dir_root_owned_0755():
    text = _provision_text()
    assert 'CADDY_SITES_DIR="/etc/caddy/sites"' in text
    assert 'install -d -o root -g root -m 0755 "${CADDY_SITES_DIR}"' in text
    assert "import sites/*.caddy" in text


def test_provision_sh_creates_backup_user_with_sh_shell_never_in_skypane_group():
    text = _provision_text()
    assert text.count("skypane-backup") >= 3
    assert "--shell /bin/sh" in text
    assert not re.search(r"usermod -aG .*skypane skypane-backup|usermod -aG skypane skypane-backup", text)


def test_provision_sh_venv_created_root_owned():
    text = _provision_text()
    assert "chown -R root:root" in text
    assert '"${APP_ROOT}/venv"' in text
