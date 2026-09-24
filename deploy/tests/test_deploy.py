"""deploy/tests/test_deploy.py — deploy/deploy.sh (SEC-05). Runs the real
repository (git archive needs a real repo to work against — this test
does not use the fake_root fixtures) with a fake `ssh` stub on PATH that
captures argv and, for the first call, the tar stream piped to its
stdin — so this test exercises deploy.sh's actual git archive/ssh
transport, not a mock of it.
"""
import os
import subprocess
import tarfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEPLOY_SH = _REPO_ROOT / "deploy" / "deploy.sh"


def _write_ssh_stub(bindir, log_path):
    """A fake ssh: logs its own argv, and for the tar-extraction call
    (identified by its remote command containing "tar -x") captures
    whatever was piped to its stdin so the test can inspect the tar
    listing. For the activate.sh call, its exit status is controlled by
    FAKE_SSH_ACTIVATE_RC (default 0) so deploy.sh's own exit-status
    propagation can be exercised both ways.
    """
    script = bindir / "ssh"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        f"_LOG = {str(log_path)!r}\n"
        "_args = sys.argv[1:]\n"
        "with open(_LOG, 'a') as f:\n"
        "    f.write('ssh ' + ' '.join(_args) + chr(10))\n"
        "_remote = _args[-1] if _args else ''\n"
        "if 'tar -x' in _remote:\n"
        "    data = sys.stdin.buffer.read()\n"
        "    _cap = os.environ.get('STUB_SSH_TAR_CAPTURE')\n"
        "    if _cap:\n"
        "        with open(_cap, 'wb') as tf:\n"
        "            tf.write(data)\n"
        "    sys.exit(0)\n"
        "if 'activate.sh' in _remote:\n"
        "    sys.exit(int(os.environ.get('FAKE_SSH_ACTIVATE_RC', '0')))\n"
        "sys.exit(0)\n"
    )
    script.chmod(0o755)


def _run_deploy(tmp_path, args=("ubuntu@203.0.113.10",), extra_env=None):
    bindir = tmp_path / "sshbin"
    bindir.mkdir()
    log_path = tmp_path / "ssh-calls.log"
    log_path.write_text("")
    tar_capture = tmp_path / "captured.tar"
    _write_ssh_stub(bindir, log_path)

    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["STUB_SSH_TAR_CAPTURE"] = str(tar_capture)
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        ["bash", str(_DEPLOY_SH), *args],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result, log_path, tar_capture


def _head_sha():
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_deploy_streams_committed_tree_then_runs_activate(tmp_path):
    result, log_path, tar_capture = _run_deploy(tmp_path)
    assert result.returncode == 0, result.stderr

    calls = [line for line in log_path.read_text().splitlines() if line.strip()]
    assert len(calls) == 2, calls

    sha = _head_sha()
    incoming = f"/opt/skypane/releases/.incoming-{sha}"

    assert "tar -x" in calls[0]
    assert "activate.sh" in calls[1]
    assert f"sudo bash '{incoming}/deploy/activate.sh' '{sha}' '{incoming}'" in calls[1]

    with tarfile.open(str(tar_capture), "r:") as tar:
        names = tar.getnames()

    for expected in (
        "deploy/activate.sh",
        "deploy/render_caddyfile.sh",
        "deploy/backup/backup_gate.py",
        "companion/app.py",
        "server/poll_loop.py",
        "stub-server/byos_server.py",
        "adsb-test/runway3.json",
    ):
        assert expected in names, expected

    assert not any(n.startswith("server/state/") for n in names)
    assert not any(".venv/" in n for n in names)
    assert "deploy/skypane.env" not in names


def test_activate_failure_propagates_nonzero_exit(tmp_path):
    result, _, _ = _run_deploy(tmp_path, extra_env={"FAKE_SSH_ACTIVATE_RC": "1"})
    assert result.returncode != 0


def test_activate_success_propagates_zero_exit(tmp_path):
    result, _, _ = _run_deploy(tmp_path, extra_env={"FAKE_SSH_ACTIVATE_RC": "0"})
    assert result.returncode == 0


def test_no_argument_prints_usage_and_fails(tmp_path):
    result, _, _ = _run_deploy(tmp_path, args=())
    assert result.returncode != 0
    assert "ubuntu@" in result.stderr


def test_no_rsync_or_sha256sum_in_deploy_sh():
    text = _DEPLOY_SH.read_text()
    assert "rsync" not in text
    assert "sha256sum" not in text
