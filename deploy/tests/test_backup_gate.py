"""deploy/tests/test_backup_gate.py -- the forced-command gate. Runs
deploy/backup/backup_gate.py as a real subprocess (the gate itself runs
under /usr/bin/python3 outside the venv, via sshd's `command=`) with
SSH_ORIGINAL_COMMAND set the way sshd would set it, so this test
exercises the exact argv/env contract, not an in-process import.
"""
import hashlib
import os
import stat
import subprocess
import sys
import threading
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_GATE_PATH = _REPO_ROOT / "deploy" / "backup" / "backup_gate.py"


def _run(archive_dir, pulled_dir, command):
    env = dict(os.environ)
    if command is None:
        env.pop("SSH_ORIGINAL_COMMAND", None)
    else:
        env["SSH_ORIGINAL_COMMAND"] = command
    return subprocess.run(
        [
            sys.executable,
            str(_GATE_PATH),
            "--archive-dir",
            str(archive_dir),
            "--pulled-dir",
            str(pulled_dir),
        ],
        env=env,
        capture_output=True,
    )


def _seed_archive(archive_dir, name, content=b"archive-bytes"):
    archive_dir.mkdir(parents=True, exist_ok=True)
    path = archive_dir / name
    path.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    (archive_dir / (name + ".sha256")).write_text("%s  %s\n" % (sha, name))
    return path, sha


class TestList:
    def test_list_one_line_per_archive_sorted_omits_missing_sha(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        _seed_archive(archive_dir, "skypane-state-20260921T031500Z.tar.gz", b"bb")
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz", b"a")
        # No .sha256 for this one - must be omitted.
        (archive_dir / "skypane-state-20260922T031500Z.tar.gz").write_bytes(b"ccc")

        result = _run(archive_dir, pulled_dir, "list")
        assert result.returncode == 0
        lines = result.stdout.decode().splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("skypane-state-20260920T031500Z.tar.gz ")
        assert lines[1].startswith("skypane-state-20260921T031500Z.tar.gz ")
        assert "skypane-state-20260922T031500Z.tar.gz" not in result.stdout.decode()


class TestGet:
    def test_get_valid_archive_streams_identical_bytes(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        content = b"the archive contents, byte for byte"
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz", content)

        result = _run(archive_dir, pulled_dir, "get skypane-state-20260920T031500Z.tar.gz")
        assert result.returncode == 0
        assert result.stdout == content

    def test_get_symlink_rejected(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        archive_dir.mkdir()
        real = tmp_path / "outside.tar.gz"
        real.write_bytes(b"secret elsewhere")
        link = archive_dir / "skypane-state-20260920T031500Z.tar.gz"
        link.symlink_to(real)

        result = _run(archive_dir, pulled_dir, "get skypane-state-20260920T031500Z.tar.gz")
        assert result.returncode == 2
        assert result.stdout == b""

    def test_get_rejections(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz", b"x")

        for command in (
            "get ../../opt/skypane/skypane.env",
            "get /etc/passwd",
            "get skypane-state-20260920T031500Z.tar.gz extra",
            "get skypane-state-x.tar.gz",
            "get",
        ):
            result = _run(archive_dir, pulled_dir, command)
            assert result.returncode == 2, command
            assert result.stdout == b"", command


class TestAck:
    def test_ack_valid_archive_writes_marker_atomically(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz")

        result = _run(archive_dir, pulled_dir, "ack skypane-state-20260920T031500Z.tar.gz")
        assert result.returncode == 0

        marker = pulled_dir / "last-pull"
        assert marker.read_text() == "skypane-state-20260920T031500Z.tar.gz\n"
        assert stat.S_IMODE(marker.stat().st_mode) == 0o644
        # The temp name is a unique mkstemp name, not the old fixed
        # ".last-pull.tmp" - assert no file in pulled_dir ends with .tmp,
        # rather than the absence of one specific literal name.
        for entry in os.listdir(pulled_dir):
            assert not entry.endswith(".tmp")

    def test_concurrent_acks_land_one_full_name_no_stray_tmp(self, tmp_path):
        """Two `ack` invocations for two different valid archives, run as
        real concurrent subprocesses, both exit 0 and leave `last-pull`
        holding one of the two names in full (never a torn mix of both),
        with no `.tmp` file left behind in `pulled_dir` - the unique
        mkstemp name means neither process can collide with the other's
        temp file the way a fixed `.last-pull.tmp` name could.
        """
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz")
        _seed_archive(archive_dir, "skypane-state-20260921T031500Z.tar.gz")

        results = {}

        def run(name):
            results[name] = _run(archive_dir, pulled_dir, "ack %s" % name)

        names = [
            "skypane-state-20260920T031500Z.tar.gz",
            "skypane-state-20260921T031500Z.tar.gz",
        ]
        threads = [threading.Thread(target=run, args=(name,)) for name in names]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert not t.is_alive()

        for name in names:
            assert results[name].returncode == 0, results[name].stderr

        marker = pulled_dir / "last-pull"
        assert marker.read_text() in ("%s\n" % names[0], "%s\n" % names[1])
        for entry in os.listdir(pulled_dir):
            assert not entry.endswith(".tmp")

    def test_ack_absent_archive_leaves_marker_unchanged(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        _seed_archive(archive_dir, "skypane-state-20260920T031500Z.tar.gz")
        pulled_dir.mkdir()
        marker = pulled_dir / "last-pull"
        marker.write_text("skypane-state-20260919T031500Z.tar.gz\n")

        result = _run(archive_dir, pulled_dir, "ack skypane-state-20260921T031500Z.tar.gz")
        assert result.returncode == 2
        assert marker.read_text() == "skypane-state-20260919T031500Z.tar.gz\n"


class TestRejectedCommands:
    def test_unsupported_and_malformed_commands(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        archive_dir.mkdir()

        for command in (
            None,  # SSH_ORIGINAL_COMMAND unset entirely
            "",
            "sh",
            "bash -i",
            "list; cat /etc/passwd",
            "rsync --server -e.LsfxC . /opt/skypane/state",
        ):
            result = _run(archive_dir, pulled_dir, command)
            assert result.returncode == 2, command
            assert result.stdout == b"", command
            stderr_lines = [line for line in result.stderr.decode().splitlines() if line.strip()]
            assert len(stderr_lines) == 1, command

    def test_unbalanced_quote_is_rejected(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        archive_dir.mkdir()

        result = _run(archive_dir, pulled_dir, "get 'unterminated")
        assert result.returncode == 2
        assert result.stdout == b""
