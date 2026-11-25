"""scripts/fw_publish_signed.py with every external tool faked.

`run` is the script's single subprocess seam; the fake below plays git, gh,
docker and the manifest/registry commands, so no docker, network or real
key is involved. The fake key file holds a synthetic marker built at test
time.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "fw_publish_signed.py"
sys.path.insert(0, str(_SCRIPT.parent))
import fw_publish_signed as fps  # noqa: E402

TAG = "fw-v1.2.3"
COMMIT = "c" * 40
KEY_MARKER = "synthetic-key-bytes-" + "k" * 24


class World:
    """Scripted outside world plus a record of every call."""

    def __init__(self):
        self.calls = []
        self.on_main = True
        self.runs = [
            {"databaseId": 77, "headSha": COMMIT, "headBranch": TAG, "conclusion": "success"}
        ]
        self.release_exists = False
        self.files = {n: ("content-" + n).encode() for n in fps.UNSIGNED_FILES}
        self.tamper = None
        self.extra_file = None
        self.fail_signing = False

    def cmds(self, *prefix):
        return [c for c in self.calls if tuple(c[: len(prefix)]) == prefix]

    def __call__(self, argv, cwd=None, env=None, check=True):
        self.calls.append(list(argv))
        rc, out = self._dispatch(list(argv))
        if check and rc != 0:
            raise fps.PublishError("%s failed" % argv[0])
        return subprocess.CompletedProcess(argv, rc, out, "")

    def _dispatch(self, argv):
        tool = argv[0]
        if tool == "git":
            return self._git(argv)
        if tool == "gh":
            return self._gh(argv)
        if tool == "docker":
            return self._docker(argv)
        if "fw_release_manifest.py" in argv[1]:
            return self._manifest(argv)
        return 0, "fw-v1.2.3  ready\n"

    def _git(self, argv):
        sub = argv[3]
        if sub == "rev-list":
            return 0, COMMIT + "\n"
        if sub == "merge-base":
            return (0 if self.on_main else 1), ""
        if sub == "rev-parse":
            return 0, "abcdef1234567890\n"
        if sub == "worktree" and argv[4] == "add":
            Path(argv[-2]).mkdir(parents=True)
        return 0, ""

    def _gh(self, argv):
        if argv[1:3] == ["run", "list"]:
            return 0, json.dumps(self.runs)
        if argv[1:3] == ["run", "download"]:
            self._download(Path(argv[argv.index("-D") + 1]))
            return 0, ""
        if argv[1:3] == ["release", "view"]:
            return (0 if self.release_exists else 1), ""
        return 0, ""

    def _download(self, dest):
        dest.mkdir(parents=True)
        sums = []
        for name, data in self.files.items():
            (dest / name).write_bytes(data)
            sums.append("%s  %s" % (hashlib.sha256(data).hexdigest(), name))
        (dest / fps.SUMS_NAME).write_text("\n".join(sums) + "\n")
        if self.tamper:
            (dest / self.tamper).write_bytes(b"tampered")
        if self.extra_file:
            (dest / self.extra_file).write_bytes(b"x")

    def _docker(self, argv):
        if "sign_data" in argv:
            if self.fail_signing:
                return 1, ""
            out = argv[argv.index("--output") + 1]
            host = Path(argv[argv.index("-v") + 1].split(":")[0])
            (host / Path(out).name).write_bytes(b"signed-" + out.encode())
        return 0, ""

    def _manifest(self, argv):
        if "--check-only" in argv:
            return 0, ""
        for flag in ("--out", "--notes-md"):
            if flag in argv:
                Path(argv[argv.index(flag) + 1]).write_text("generated " + flag)
        return 0, ""


@pytest.fixture
def world(monkeypatch):
    w = World()
    monkeypatch.setattr(fps, "run", w)
    return w


@pytest.fixture
def key_file(tmp_path):
    path = tmp_path / "fake-signing-key.pem"
    path.write_text(KEY_MARKER)
    path.chmod(0o600)
    return path


def _invoke(tmp_path, key_file, *extra, tag=TAG):
    state = tmp_path / "state"
    argv = [tag, "--key-file", str(key_file), "--repo", str(tmp_path), "--state-dir", str(state)]
    return fps.main(argv + list(extra)), state


def test_bad_tag_refused_before_anything_runs(world, key_file, tmp_path):
    rc, _ = _invoke(tmp_path, key_file, tag="fw-v1.2")
    assert rc == 1
    assert world.calls == []


def test_tag_not_on_main_is_refused(world, key_file, tmp_path):
    world.on_main = False
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("docker")


@pytest.mark.parametrize(
    "run",
    [
        {"databaseId": 1, "headSha": "d" * 40, "headBranch": TAG, "conclusion": "success"},
        {"databaseId": 1, "headSha": COMMIT, "headBranch": "main", "conclusion": "success"},
        {"databaseId": 1, "headSha": COMMIT, "headBranch": TAG, "conclusion": "failure"},
    ],
)
def test_run_must_match_tag_commit_and_succeed(world, key_file, tmp_path, run):
    world.runs = [run]
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("gh", "run", "download")


def test_tampered_unsigned_file_is_refused(world, key_file, tmp_path):
    world.tamper = "second-skypane.bin"
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("docker")


def test_unexpected_extra_file_is_refused(world, key_file, tmp_path):
    world.extra_file = "extra.bin"
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("docker")


def test_missing_file_is_refused(world, key_file, tmp_path):
    del world.files["bootloader.bin"]
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("docker")


def test_loose_key_mode_is_refused(world, key_file, tmp_path):
    key_file.chmod(0o644)
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert not world.cmds("docker")


def test_dry_run_publishes_nothing_and_imports_into_scratch(world, key_file, tmp_path, capsys):
    rc, state = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 0
    assert not world.cmds("gh", "release", "create")
    assert not world.cmds("gh", "workflow", "run")
    imports = [c for c in world.calls if "server.firmware_cli" in c]
    assert any("import-dir" in c for c in imports)
    assert str(state / "scratch-state") in imports[0]
    assert "Dry run complete" in capsys.readouterr().out


def test_real_run_creates_release_once_with_exact_seven_names(world, key_file, tmp_path):
    rc, state = _invoke(tmp_path, key_file, "--yes")
    assert rc == 0
    creates = world.cmds("gh", "release", "create")
    assert len(creates) == 1
    create = creates[0]
    assert create[4:11] == [str(state / "stage" / n) for n in fps.asset_names(TAG)]
    assert [Path(p).name for p in create[4:11]] == [
        "skypane-fw-v1.2.3.bin",
        "release.json",
        "bootloader-fw-v1.2.3.bin",
        "partition-table-fw-v1.2.3.bin",
        "ota_data_initial-fw-v1.2.3.bin",
        "skypane-seeed-ee04-7in3-spectra6-fw-v1.2.3.bin",
        "release-seeed-ee04-7in3-spectra6.json",
    ]
    assert "--verify-tag" in create
    assert create[create.index("--title") + 1] == TAG


def test_existing_release_is_refused(world, key_file, tmp_path):
    world.release_exists = True
    rc, _ = _invoke(tmp_path, key_file, "--yes")
    assert rc == 1
    assert not world.cmds("gh", "release", "create")


def test_key_is_mounted_read_only_without_network_and_never_printed(
    world, key_file, tmp_path, capsys
):
    rc, _ = _invoke(tmp_path, key_file, "--yes")
    assert rc == 0
    signs = [c for c in world.cmds("docker") if "sign_data" in c]
    assert len(signs) == 2
    for call in signs:
        assert "--network" in call and call[call.index("--network") + 1] == "none"
        assert "%s:/key.pem:ro" % key_file in call
        assert fps.SIGNING_IMAGE in call
    seen = capsys.readouterr()
    assert KEY_MARKER not in seen.out + seen.err
    assert str(key_file) not in seen.out + seen.err


def test_signatures_are_verified_against_the_committed_public_key(world, key_file, tmp_path):
    _invoke(tmp_path, key_file, "--dry-run")
    verifies = [c for c in world.cmds("docker") if "verify_signature" in c]
    assert len(verifies) == 2
    assert all(
        any(a.endswith("skypane-signing-pubkey.pem:/pubkey.pem:ro") for a in c) for c in verifies
    )
    assert len([c for c in world.calls if "--check-only" in c]) == 2


def test_deploy_dispatch_needs_a_y_answer(world, key_file, tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    rc, _ = _invoke(tmp_path, key_file)
    assert rc == 0
    assert world.cmds("gh", "release", "create")
    assert not world.cmds("gh", "workflow", "run")


def test_deploy_dispatch_on_y_uses_first_seven_of_main(world, key_file, tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    rc, _ = _invoke(tmp_path, key_file)
    assert rc == 0
    assert world.cmds("gh", "workflow", "run") == [
        ["gh", "workflow", "run", "deploy.yml", "--ref", "main", "-f", "confirm_sha=abcdef1"]
    ]


def test_worktree_is_removed_after_a_failure(world, key_file, tmp_path):
    world.fail_signing = True
    rc, _ = _invoke(tmp_path, key_file, "--dry-run")
    assert rc == 1
    assert any(c[3:5] == ["worktree", "remove"] for c in world.cmds("git"))


def test_help_mentions_dry_run_and_key_file():
    out = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0
    assert "--dry-run" in out.stdout and "--key-file" in out.stdout
