"""deploy/tests/test_release_manifest.py -- proves
scripts/fw_release_manifest.py generates a release manifest and notes
body entirely from git and the image file, against throwaway git
repositories built fresh in tmp_path (no network, no committed
fixtures). The CLI is exercised via subprocess (the same convention
deploy/tests/test_cert_chain_check.py uses for scripts/), and the
output is round-tripped through server.firmware_registry.publish_release
to prove it is the real shape the registry expects.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from server import firmware_registry

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "fw_release_manifest.py"


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, "git %s failed: %s" % (args, result.stderr)
    return result.stdout


def _init_repo(repo):
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    return repo


def _commit(repo, rel_path, content, message):
    file_path = repo / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    _git(repo, "add", rel_path)
    _git(
        repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
        "commit", "-q", "-m", message,
    )


def _tag(repo, name, ref="HEAD"):
    _git(repo, "tag", name, ref)


def _run_cli(tag, image, out, repo, notes_md=None, extra=()):
    args = [
        sys.executable, str(_SCRIPT),
        "--tag", tag, "--image", str(image), "--out", str(out), "--repo", str(repo),
    ]
    if notes_md is not None:
        args += ["--notes-md", str(notes_md)]
    args += list(extra)
    return subprocess.run(args, capture_output=True, text=True, timeout=60)


@pytest.fixture
def two_release_repo(tmp_path):
    """Commits A (firmware/x), B (server/y), tag fw-v1.0.0, C
    (firmware/z "fix panel"), D (docs), E (firmware/w "add ota"), tag
    fw-v1.1.0 -- the exact history this plan's behaviour block names.
    """
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, "firmware/x.c", "int x;\n", "add x")
    _commit(repo, "server/y.py", "y = 1\n", "add y")
    _tag(repo, "fw-v1.0.0")
    _commit(repo, "firmware/z.c", "int z;\n", "fix panel")
    _commit(repo, "docs/readme.md", "# docs\n", "add docs")
    _commit(repo, "firmware/w.c", "int w;\n", "add ota")
    _tag(repo, "fw-v1.1.0")
    return repo


def _make_image(path, size=1024, fill=b"\xab"):
    path.write_bytes(fill * size)
    return path


def test_second_release_notes_are_firmware_only_newest_first_no_merges(two_release_repo, tmp_path):
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.1.0", image, out, two_release_repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    assert manifest["notes"] == ["Add ota", "Fix panel"]
    assert manifest["version"] == "fw-v1.1.0"


def test_first_release_notes_list_firmware_commits_up_to_it(two_release_repo, tmp_path):
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.0.0", image, out, two_release_repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    # Only firmware/x.c ("add x") is a firmware/ commit reachable from
    # the first tag -- server/y.py is excluded.
    assert manifest["notes"] == ["Add x"]


def test_manifest_fields_match_image_and_commit(two_release_repo, tmp_path):
    image = _make_image(tmp_path / "skypane.bin", size=2048, fill=b"\x11")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.1.0", image, out, two_release_repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())

    expected_sha256 = hashlib.sha256(image.read_bytes()).hexdigest()
    assert manifest["sha256"] == expected_sha256
    assert manifest["size"] == 2048

    expected_commit = _git(two_release_repo, "rev-list", "-n", "1", "fw-v1.1.0").strip()
    assert manifest["commit"] == expected_commit
    assert len(manifest["commit"]) == 40

    expected_date = _git(two_release_repo, "show", "-s", "--format=%cI", expected_commit).strip()
    assert manifest["released_at"] == expected_date


@pytest.mark.parametrize("bad_tag", ["v1.0.0", "fw-v1.0"])
def test_malformed_tag_exits_2(two_release_repo, tmp_path, bad_tag):
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    result = _run_cli(bad_tag, image, out, two_release_repo)
    assert result.returncode == 2
    assert not out.exists()


def test_oversized_image_exits_2(two_release_repo, tmp_path):
    image = tmp_path / "skypane.bin"
    _make_image(image, size=firmware_registry.MAX_IMAGE_BYTES + 1, fill=b"\x00")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.1.0", image, out, two_release_repo)
    assert result.returncode == 2
    assert not out.exists()


def test_long_subject_is_truncated_to_200_chars(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    long_subject = "X" * 250
    _commit(repo, "firmware/x.c", "int x;\n", long_subject)
    _tag(repo, "fw-v1.0.0")
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.0.0", image, out, repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    assert manifest["notes"] == [long_subject[:200]]
    assert len(manifest["notes"][0]) == 200


def test_previous_tag_chosen_by_version_order_not_creation_time(tmp_path):
    """Tags fw-v1.0.5 (commit A) and fw-v1.0.2 (commit B, an ancestor of
    C) are created in *reverse* version order -- fw-v1.0.2 is tagged
    after fw-v1.0.5 -- so a "most recently created tag" implementation
    would wrongly pick fw-v1.0.2 as fw-v1.1.0's previous release. The
    correct previous tag is the higher version, fw-v1.0.5, regardless of
    which tag object is newer.
    """
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, "firmware/a.c", "int a;\n", "commit a")
    _tag(repo, "fw-v1.0.5")  # created first
    _commit(repo, "firmware/b.c", "int b;\n", "commit b")
    _tag(repo, "fw-v1.0.2")  # created second, lower version
    _commit(repo, "firmware/c.c", "int c;\n", "commit c")
    _tag(repo, "fw-v1.1.0")

    import scripts.fw_release_manifest as fw_release_manifest

    prev = fw_release_manifest.previous_tag(str(repo), "fw-v1.1.0")
    assert prev == "fw-v1.0.5"


def test_more_than_60_firmware_commits_are_capped_with_a_summary_entry(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    for i in range(65):
        _commit(repo, "firmware/f%02d.c" % i, "int f%d;\n" % i, "commit %02d" % i)
    _tag(repo, "fw-v1.0.0")
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.0.0", image, out, repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    assert len(manifest["notes"]) == 60
    # Newest first: "commit 64" is the very last commit made.
    assert manifest["notes"][0] == "Commit 64"
    assert manifest["notes"][-1] == "and 6 earlier commits"


def test_notes_md_is_a_heading_plus_bullet_list(two_release_repo, tmp_path):
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    notes_md = tmp_path / "notes.md"
    result = _run_cli("fw-v1.1.0", image, out, two_release_repo, notes_md=notes_md)
    assert result.returncode == 0, result.stderr
    text = notes_md.read_text()
    assert text.startswith("## fw-v1.1.0\n")
    assert "- Add ota" in text
    assert "- Fix panel" in text


def test_manifest_round_trips_through_firmware_registry_publish_release(two_release_repo, tmp_path):
    image = _make_image(tmp_path / "skypane.bin", size=4096, fill=b"\x42")
    out = tmp_path / "release.json"
    result = _run_cli("fw-v1.1.0", image, out, two_release_repo)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())

    state_dir = tmp_path / "state"
    outcome = firmware_registry.publish_release(str(state_dir), manifest, str(image))
    assert outcome == "added"

    registry = firmware_registry.load_registry(str(state_dir))
    release = registry["releases"][0]
    assert release["version"] == "fw-v1.1.0"
    assert release["sha256"] == manifest["sha256"]
    assert release["notes"] == ["Add ota", "Fix panel"]


@pytest.mark.parametrize("subject, expected", [
    ("fix(firmware): refuse to USB-flash an unsigned image (#159)",
     "Refuse to USB-flash an unsigned image"),
    ("feat(firmware): report the Wi-Fi RSSI with every check-in (#168)",
     "Report the Wi-Fi RSSI with every check-in"),
    ("feat!: drop the legacy poll endpoint", "Drop the legacy poll endpoint"),
    ("fix(34): point the hardware-session commands at the release layout (#119)",
     "Point the hardware-session commands at the release layout"),
    ("Phase 42: Remote firmware update over the air (OTA) (#157)",
     "Remote firmware update over the air (OTA)"),
    ("Phase 42.1 - Tighten the retry loop", "Tighten the retry loop"),
    ("fix(firmware): Phase 42: keep the rail off", "Keep the rail off"),
    ("Sleep a fixed 300 s on an unusable NVS (#135) (#136)",
     "Sleep a fixed 300 s on an unusable NVS"),
    ("already a plain sentence", "Already a plain sentence"),
    ("Firmware: sleep on a bad NVS", "Sleep on a bad NVS"),
    ("  fix(firmware):   spaced out  ", "Spaced out"),
])
def test_clean_note_strips_prefixes_and_pr_references(subject, expected):
    import scripts.fw_release_manifest as fw_release_manifest

    assert fw_release_manifest.clean_note(subject) == expected


@pytest.mark.parametrize("subject", [
    "", "   ", "fix(firmware):", "Phase 42:", "(#12)",
    "chore: close v1.0 milestone (#164)", "docs(firmware): flashing guide",
    "ci: pin the build container", "test(firmware): host tests", "style: format",
    "build(deps): bump esp-idf", "Merge branch 'main' into feature",
    "WIP half done", "fixup! earlier commit",
])
def test_clean_note_drops_empty_merge_and_housekeeping_subjects(subject):
    import scripts.fw_release_manifest as fw_release_manifest

    assert fw_release_manifest.clean_note(subject) is None


def test_clean_notes_keeps_order_drops_repeats_and_truncates():
    import scripts.fw_release_manifest as fw_release_manifest

    notes = fw_release_manifest.clean_notes([
        "fix(firmware): keep the rail off (#1)", "chore: noise",
        "Keep the rail off", "feat(firmware): " + "y" * 300, "Second note"])
    assert notes == ["Keep the rail off", "Y" + "y" * 199, "Second note"]
    assert fw_release_manifest.clean_notes([]) == []
    assert fw_release_manifest.clean_notes(["fix(firmware):", "chore: x"]) == []


def test_clean_note_is_deterministic():
    import scripts.fw_release_manifest as fw_release_manifest

    subject = "fix(firmware): keep the rail off (#9)"
    assert [fw_release_manifest.clean_note(subject) for _ in range(3)] == ["Keep the rail off"] * 3


def test_cli_notes_are_cleaned_but_manifest_identity_is_untouched(tmp_path):
    """Only the display notes change: the version, hash, size and commit
    in the manifest, which are what the registry and the frame verify,
    come out exactly as they would without any cleaning."""
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, "firmware/a.c", "int a;\n", "fix(firmware): keep the rail off (#7)")
    _commit(repo, "firmware/b.c", "int b;\n", "chore(firmware): housekeeping (#8)")
    _commit(repo, "firmware/c.c", "int c;\n", "Phase 42: honest Update page (#9)")
    _tag(repo, "fw-v1.0.0")
    image = _make_image(tmp_path / "skypane.bin", size=512, fill=b"\x5a")
    out = tmp_path / "release.json"
    notes_md = tmp_path / "notes.md"
    result = _run_cli("fw-v1.0.0", image, out, repo, notes_md=notes_md)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    assert manifest["notes"] == ["Honest Update page", "Keep the rail off"]
    assert manifest["sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert manifest["size"] == 512 and manifest["version"] == "fw-v1.0.0"
    assert "- Honest Update page" in notes_md.read_text()
    assert firmware_registry.publish_release(
        str(tmp_path / "state"), manifest, str(image)) == "added"


def test_a_release_whose_commits_are_all_housekeeping_has_no_notes(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, "firmware/a.c", "int a;\n", "chore(firmware): bump (#1)")
    _tag(repo, "fw-v1.0.0")
    image = _make_image(tmp_path / "skypane.bin")
    out = tmp_path / "release.json"
    notes_md = tmp_path / "notes.md"
    assert _run_cli("fw-v1.0.0", image, out, repo, notes_md=notes_md).returncode == 0
    assert json.loads(out.read_text())["notes"] == []
    assert "No firmware/ changes recorded" in notes_md.read_text()


def test_no_shell_true_in_the_script():
    text = _SCRIPT.read_text()
    assert "shell=True" not in text
