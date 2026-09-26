"""deploy/tests/test_mac_pull.py -- the Mac-side pull script and its
launchd installer. Runs both POSIX sh scripts as real
subprocesses under /bin/sh (dash on Linux, which enforces POSIX - the
same shell class the scripts are written for; macOS's own /bin/sh is
also a POSIX-only, non-bash shell). A fake `ssh` placed first on PATH
execs the real deploy/backup/backup_gate.py in-process with
SSH_ORIGINAL_COMMAND set to its own last argument, the same way real
ssh/sshd would populate it - so these tests exercise the gate's actual
verb/arity/checksum contract end to end, not a mocked stand-in.
"""
import hashlib
import os
import plistlib
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PULL_SCRIPT = _REPO_ROOT / "deploy" / "backup" / "mac" / "skypane-backup-pull.sh"
_INSTALL_SCRIPT = _REPO_ROOT / "deploy" / "backup" / "mac" / "install-launchagent.sh"
_GATE = _REPO_ROOT / "deploy" / "backup" / "backup_gate.py"

# Like real ssh, the fake forwards (here: drains) its stdin unless -n is
# given - a pull loop that feeds `while read` from a file must not let
# ssh swallow the rest of that file.
_FAKE_SSH = """#!/bin/sh
last=""
no_stdin=0
for arg in "$@"; do
    [ "$arg" = "-n" ] && no_stdin=1
    last="$arg"
done
[ "$no_stdin" -eq 1 ] || cat >/dev/null
case "$last" in
  list)
    if [ -n "${FAKE_SSH_LIST_FAIL_COUNT:-}" ] && [ "${FAKE_SSH_LIST_FAIL_COUNT:-0}" -gt 0 ]; then
      count=0
      [ -f "$FAKE_SSH_LIST_COUNTER_FILE" ] && count=$(cat "$FAKE_SSH_LIST_COUNTER_FILE")
      if [ "$count" -lt "$FAKE_SSH_LIST_FAIL_COUNT" ]; then
        count=$((count + 1))
        echo "$count" > "$FAKE_SSH_LIST_COUNTER_FILE"
        echo simulated-list-failure >&2
        exit 1
      fi
    fi
    ;;
esac
SSH_ORIGINAL_COMMAND="$last" exec "$FAKE_SSH_PYTHON" "$FAKE_SSH_GATE" \\
    --archive-dir "$FAKE_SSH_ARCHIVE_DIR" --pulled-dir "$FAKE_SSH_PULLED_DIR"
"""

_FAKE_SHASUM = """#!/bin/sh
shift
shift
exec sha256sum "$@"
"""


def _write_executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


def _seed_archive(archive_dir, name, content):
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / name).write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    (archive_dir / (name + ".sha256")).write_text("%s  %s\n" % (sha, name))
    return sha


def _run_pull(tmp_path, archive_dir, pulled_dir, dest, list_fail_count=0):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_executable(bin_dir / "ssh", _FAKE_SSH)
    if shutil.which("shasum") is None:
        _write_executable(bin_dir / "shasum", _FAKE_SHASUM)

    conf_dir = tmp_path / "conf"
    conf_dir.mkdir(exist_ok=True)
    conf_path = conf_dir / "backup.conf"
    conf_path.write_text(
        "TARGET=skypane-backup@example.invalid\nKEY=%s\nDEST=%s\n" % (tmp_path / "key", dest)
    )

    env = dict(os.environ)
    env["PATH"] = "%s:%s" % (bin_dir, env.get("PATH", ""))
    env["SKYPANE_BACKUP_CONF"] = str(conf_path)
    env["SKYPANE_PULL_RETRY_SLEEP"] = "0"
    env["FAKE_SSH_PYTHON"] = sys.executable
    env["FAKE_SSH_GATE"] = str(_GATE)
    env["FAKE_SSH_ARCHIVE_DIR"] = str(archive_dir)
    env["FAKE_SSH_PULLED_DIR"] = str(pulled_dir)
    if list_fail_count:
        env["FAKE_SSH_LIST_FAIL_COUNT"] = str(list_fail_count)
        env["FAKE_SSH_LIST_COUNTER_FILE"] = str(tmp_path / "list-fail-counter")

    return subprocess.run(["/bin/sh", str(_PULL_SCRIPT)], env=env, capture_output=True)


class TestPullDownloadVerifyAck:
    def test_first_run_downloads_verifies_and_acks_newest(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        dest = tmp_path / "dest"

        base = datetime(2026, 9, 1, tzinfo=timezone.utc)
        names = []
        for i in range(3):
            ts = (base + timedelta(days=i)).strftime("%Y%m%dT%H%M%SZ")
            name = "skypane-state-%s.tar.gz" % ts
            _seed_archive(archive_dir, name, ("content-%d" % i).encode())
            names.append(name)

        result = _run_pull(tmp_path, archive_dir, pulled_dir, dest)
        assert result.returncode == 0, result.stderr.decode()

        for name in names:
            assert (dest / name).exists()
            assert (dest / name).read_bytes() == (archive_dir / name).read_bytes()
        assert not any(p.name.endswith(".partial") for p in dest.iterdir())

        marker = pulled_dir / "last-pull"
        assert marker.exists()
        assert marker.read_text() == names[-1] + "\n"

    def test_second_run_downloads_nothing_new_still_exits_0(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        dest = tmp_path / "dest"
        name = "skypane-state-20260901T000000Z.tar.gz"
        _seed_archive(archive_dir, name, b"content")

        first = _run_pull(tmp_path, archive_dir, pulled_dir, dest)
        assert first.returncode == 0, first.stderr.decode()
        before_mtime = (dest / name).stat().st_mtime_ns

        second = _run_pull(tmp_path, archive_dir, pulled_dir, dest)
        assert second.returncode == 0, second.stderr.decode()
        assert (dest / name).stat().st_mtime_ns == before_mtime

    def test_corrupted_archive_checksum_mismatch_no_ack(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        dest = tmp_path / "dest"
        name = "skypane-state-20260901T000000Z.tar.gz"
        archive_dir.mkdir(parents=True)
        (archive_dir / name).write_bytes(b"real-bytes")
        # A checksum that will never match the real bytes above,
        # simulating a corrupted transfer / bit-flipped archive.
        (archive_dir / (name + ".sha256")).write_text("0" * 64 + "  " + name + "\n")

        result = _run_pull(tmp_path, archive_dir, pulled_dir, dest)
        assert result.returncode != 0
        assert not (dest / name).exists()
        assert not any(p.name.endswith(".partial") for p in dest.iterdir())
        assert not (pulled_dir / "last-pull").exists()

    def test_list_retries_on_failure_then_succeeds(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        dest = tmp_path / "dest"
        name = "skypane-state-20260901T000000Z.tar.gz"
        _seed_archive(archive_dir, name, b"content")

        result = _run_pull(tmp_path, archive_dir, pulled_dir, dest, list_fail_count=2)
        assert result.returncode == 0, result.stderr.decode()
        assert (dest / name).exists()


class TestRetention:
    def test_keeps_30_newest_plus_oldest_of_each_earlier_month(self, tmp_path):
        archive_dir = tmp_path / "archives"
        pulled_dir = tmp_path / "pulled"
        dest = tmp_path / "dest"
        dest.mkdir(parents=True)

        # Anchored to "now" (not a fixed calendar date) so the 12-month
        # cutoff in the script never trims one of these - the test is
        # about the 30-newest/one-per-month rule, not the cutoff edge.
        now = datetime.now(timezone.utc)
        base = now - timedelta(days=44)
        seeded = []
        for i in range(45):
            day = base + timedelta(days=i)
            name = "skypane-state-%s.tar.gz" % day.strftime("%Y%m%dT%H%M%SZ")
            content = ("content-%d" % i).encode()
            (dest / name).write_bytes(content)
            _seed_archive(archive_dir, name, content)
            seeded.append((name, day))

        result = _run_pull(tmp_path, archive_dir, pulled_dir, dest)
        assert result.returncode == 0, result.stderr.decode()

        remaining = {p.name for p in dest.iterdir() if p.name.startswith("skypane-state-")}

        by_name = sorted(seeded, key=lambda t: t[0])
        newest_30 = by_name[-30:]
        older = by_name[:-30]

        for name, _day in newest_30:
            assert name in remaining

        by_month = {}
        for name, day in older:
            by_month.setdefault(day.strftime("%Y%m"), []).append(name)
        for _month, month_names in by_month.items():
            survivors = sorted(n for n in month_names if n in remaining)
            assert len(survivors) <= 1
            if survivors:
                assert survivors[0] == sorted(month_names)[0]

        assert len(remaining) == 30 + sum(1 for names in by_month.values() if any(n in remaining for n in names))


def _stub_launchctl(bin_dir, log_path):
    _write_executable(
        bin_dir / "launchctl",
        '#!/bin/sh\n'
        'echo "$@" >> "%s"\n'
        'if [ "$1" = bootout ]; then exit 1; fi\n'
        'exit 0\n' % log_path,
    )


class TestInstallLaunchAgent:
    def test_installs_conf_script_plist_and_bootstraps(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        launchctl_log = tmp_path / "launchctl.log"
        _stub_launchctl(bin_dir, launchctl_log)

        env = dict(os.environ)
        env["HOME"] = str(home)
        env["PATH"] = "%s:%s" % (bin_dir, env.get("PATH", ""))

        result = subprocess.run(
            ["/bin/sh", str(_INSTALL_SCRIPT), "skypane-backup@example.invalid", str(home / "key")],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr.decode()

        conf_path = home / ".config" / "skypane" / "backup.conf"
        assert conf_path.exists()
        assert stat.S_IMODE(conf_path.stat().st_mode) == 0o600
        conf_text = conf_path.read_text()
        assert "TARGET=skypane-backup@example.invalid" in conf_text
        assert "DEST=" in conf_text

        script_dest = home / "Library" / "Application Support" / "SkyPane" / "skypane-backup-pull.sh"
        assert script_dest.exists()
        assert stat.S_IMODE(script_dest.stat().st_mode) & 0o111

        plist_path = home / "Library" / "LaunchAgents" / "com.skypane.backup-pull.plist"
        assert plist_path.exists()
        with open(plist_path, "rb") as fh:
            data = plistlib.load(fh)
        assert data["Label"] == "com.skypane.backup-pull"
        assert data["ProgramArguments"] == ["/bin/sh", str(script_dest)]
        assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 30}
        assert data["RunAtLoad"] is True
        assert os.path.isabs(data["StandardOutPath"])
        assert os.path.isabs(data["StandardErrorPath"])
        assert data["StandardOutPath"].startswith(str(home / "Library" / "Logs"))

        raw_plist = plist_path.read_text()
        assert "~" not in raw_plist

        log_lines = launchctl_log.read_text().splitlines()
        assert log_lines[0].startswith("bootout gui/")
        assert log_lines[1].startswith("bootstrap gui/")
        assert str(plist_path) in log_lines[1]

    def test_refuses_documents_desktop_downloads(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _stub_launchctl(bin_dir, tmp_path / "launchctl.log")

        env = dict(os.environ)
        env["HOME"] = str(home)
        env["PATH"] = "%s:%s" % (bin_dir, env.get("PATH", ""))

        for sub in ("Documents", "Desktop", "Downloads"):
            dest = home / sub / "skypane-backups"
            result = subprocess.run(
                ["/bin/sh", str(_INSTALL_SCRIPT), "u@h", str(home / "key"), str(dest)],
                env=env,
                capture_output=True,
            )
            assert result.returncode != 0, sub
            assert not dest.exists(), sub
