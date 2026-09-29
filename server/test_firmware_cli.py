"""Behaviour tests for server/firmware_cli.py -- the deploy-time operator
CLI that publishes releases into server/firmware_registry.py.

Every assertion is about observable behaviour (exit codes, stdout/stderr
lines, registry contents) -- never about the module's source text.
"""
import hashlib
import os

import pytest

from server import firmware_cli, firmware_registry

COMMIT = "a" * 40


def _write_release_subdir(base, tag, image=None, released_at="2026-09-28T00:00:00+00:00", **overrides):
    """Write <base>/<tag>/{skypane-<tag>.bin,release.json} with a
    manifest that matches the image's real hash/size unless overridden.
    """
    image = image if image is not None else (tag.encode() + b"-image-payload")
    subdir = base / tag
    subdir.mkdir(parents=True, exist_ok=True)
    image_path = subdir / ("skypane-%s.bin" % tag)
    image_path.write_bytes(image)
    manifest = {
        "version": tag,
        "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image),
        "released_at": released_at,
        "commit": COMMIT,
        "notes": ["Fixed the thing"],
    }
    manifest.update(overrides)
    (subdir / "release.json").write_text(__import__("json").dumps(manifest))
    return subdir


# --- import-dir ------------------------------------------------------------

def test_import_dir_publishes_two_valid_releases_and_prints_added_twice(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    _write_release_subdir(base, "fw-v1.0.2")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.count("added fw-v1.0.1") == 1
    assert out.count("added fw-v1.0.2") == 1

    registry = firmware_registry.load_registry(str(state_dir))
    versions = {r["version"] for r in registry["releases"]}
    assert versions == {"fw-v1.0.1", "fw-v1.0.2"}


@pytest.mark.parametrize("argv_shape", ["before", "after"])
def test_state_dir_is_honoured_before_or_after_the_subcommand(tmp_path, capsys, argv_shape):
    """--state-dir works on either side of the subcommand, and the value
    given is the one used, not the default. A deploy once failed because
    its call put --state-dir after `import-dir`, which argparse rejected.
    """
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    if argv_shape == "before":
        argv = ["--state-dir", str(state_dir), "import-dir", str(base)]
    else:
        argv = ["import-dir", str(base), "--state-dir", str(state_dir)]

    assert firmware_cli.main(argv) == 0
    assert "added fw-v1.0.1" in capsys.readouterr().out
    registry = firmware_registry.load_registry(str(state_dir))
    assert [r["version"] for r in registry["releases"]] == ["fw-v1.0.1"]

    list_argv = (["--state-dir", str(state_dir), "list"] if argv_shape == "before"
                 else ["list", "--state-dir", str(state_dir)])
    assert firmware_cli.main(list_argv) == 0
    assert "fw-v1.0.1" in capsys.readouterr().out


def test_import_dir_rerun_prints_exists_twice_and_exits_0(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    _write_release_subdir(base, "fw-v1.0.2")

    firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    capsys.readouterr()

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.count("exists fw-v1.0.1") == 1
    assert out.count("exists fw-v1.0.2") == 1


def test_import_dir_mismatched_bytes_exits_1_names_tag_and_field_other_still_reported(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    # sha256 in the manifest does not match the real image bytes.
    _write_release_subdir(base, "fw-v1.0.2", sha256="0" * 64)

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "added fw-v1.0.1" in out.out
    assert "fw-v1.0.2" in out.err
    assert "sha256" in out.err

    registry = firmware_registry.load_registry(str(state_dir))
    versions = {r["version"] for r in registry["releases"]}
    assert versions == {"fw-v1.0.1"}


def test_import_dir_stale_release_sha_conflict_alone_does_not_block_deploy(tmp_path, capsys):
    """A release already registered by an earlier deploy whose staged
    asset now disagrees with the recorded sha256 (a GitHub Release
    deleted and re-signed -- RSA-PSS signatures are randomized, so
    re-signing always changes the hash -- or a corrupted/truncated
    file) must not fail this command: import-dir re-imports every
    published release on every deploy, so a fatal per-item error here
    would block every future, otherwise-unrelated code deploy until
    someone edits the registry by hand.
    """
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    assert firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)]) == 0
    capsys.readouterr()
    original_sha = hashlib.sha256(b"fw-v1.0.1-image-payload").hexdigest()

    # The staged directory's asset changed since it was first registered
    # -- same tag, different bytes.
    _write_release_subdir(base, "fw-v1.0.1", image=b"different-bytes-now")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 0, "a stale conflict on an already-registered release must not block the deploy: %r" % (out.err,)
    assert "fw-v1.0.1" in out.err
    assert "already registered -- not blocking this deploy over it" in out.err

    registry = firmware_registry.load_registry(str(state_dir))
    release = next(r for r in registry["releases"] if r["version"] == "fw-v1.0.1")
    assert release["sha256"] == original_sha, "the originally registered image must never be overwritten by a conflict"


def test_import_dir_new_tag_failure_still_blocks_despite_unrelated_stale_release(tmp_path, capsys):
    """A brand-new tag's own failure still blocks the deploy exactly as
    before, even alongside an unrelated already-registered release whose
    own re-import now conflicts (downgraded to a warning by the test
    above) -- only a tag genuinely new to this deploy is this run's
    problem.
    """
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    assert firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)]) == 0
    capsys.readouterr()

    _write_release_subdir(base, "fw-v1.0.1", image=b"different-bytes-now")  # stale, non-fatal
    _write_release_subdir(base, "fw-v1.0.3", sha256="0" * 64)  # new, must still fail

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    err_lines = out.err.splitlines()
    assert any("fw-v1.0.1" in ln and "already registered -- not blocking this deploy over it" in ln
               for ln in err_lines)
    fw103_lines = [ln for ln in err_lines if "fw-v1.0.3" in ln]
    assert fw103_lines, "expected an error line naming the new, genuinely failing tag"
    assert not any("already registered" in ln for ln in fw103_lines), (
        "a genuinely new tag's failure must never be downgraded to a non-blocking warning")

    registry = firmware_registry.load_registry(str(state_dir))
    versions = {r["version"] for r in registry["releases"]}
    assert versions == {"fw-v1.0.1"}


def test_import_dir_rejects_non_tag_subdirectory_name(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    not_a_tag = base / "not-a-release-tag"
    not_a_tag.mkdir(parents=True)
    (not_a_tag / "skypane-not-a-release-tag.bin").write_bytes(b"x")
    (not_a_tag / "release.json").write_text("{}")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "added fw-v1.0.1" in out.out
    assert "not-a-release-tag" in out.err
    assert "not a release tag" in out.err


def test_import_dir_rejects_missing_release_json(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    (subdir / "skypane-fw-v1.0.1.bin").write_bytes(b"x")
    # No release.json written.

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "fw-v1.0.1" in out.err
    assert "release.json" in out.err


def test_import_dir_rejects_directory_manifest_version_mismatch(tmp_path, capsys):
    """A release.json whose own version disagrees with its directory
    would otherwise publish that directory's image under a different
    label -- compute_offer's same-version and floor checks would then
    run against the wrong one.
    """
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    # Directory is named fw-v1.0.2, but the manifest inside claims a
    # different version -- the image file itself is still
    # skypane-fw-v1.0.2.bin, matching the directory name (the way a
    # real CI-produced subdirectory always names it).
    _write_release_subdir(base, "fw-v1.0.2", version="fw-v1.0.3")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "added fw-v1.0.1" in out.out
    assert "fw-v1.0.3" not in out.out
    assert "fw-v1.0.2: release.json version 'fw-v1.0.3' does not match directory" in out.err

    registry = firmware_registry.load_registry(str(state_dir))
    versions = {r["version"] for r in registry["releases"]}
    assert versions == {"fw-v1.0.1"}


def test_import_dir_rejects_symlinked_image(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    real_subdir = _write_release_subdir(base, "fw-v1.0.9")
    real_image = real_subdir / "skypane-fw-v1.0.9.bin"

    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    (subdir / "skypane-fw-v1.0.1.bin").symlink_to(real_image)
    (subdir / "release.json").write_text(
        __import__("json").dumps({
            "version": "fw-v1.0.1", "sha256": "0" * 64, "size": 1,
            "released_at": "2026-09-28T00:00:00+00:00", "commit": COMMIT, "notes": [],
        })
    )

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "fw-v1.0.1" in out.err
    assert "symlink" in out.err


def test_import_dir_bench_flag_not_accepted(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")

    try:
        firmware_cli.main(["--state-dir", str(state_dir), "import-dir", "--bench", str(base)])
        raised = False
    except SystemExit as exc:
        raised = True
        assert exc.code == 2
    assert raised


def test_import_dir_missing_directory_exits_1(tmp_path, capsys):
    state_dir = tmp_path / "state"
    missing = tmp_path / "does-not-exist"

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(missing)])
    out = capsys.readouterr()

    assert rc == 1
    assert "not a directory" in out.err


def test_import_dir_oversized_manifest_rejected(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    (subdir / "skypane-fw-v1.0.1.bin").write_bytes(b"x")
    (subdir / "release.json").write_text("x" * (firmware_cli._MAX_MANIFEST_BYTES + 1))

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "cap" in out.err


def test_import_dir_non_json_manifest_rejected(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    (subdir / "skypane-fw-v1.0.1.bin").write_bytes(b"x")
    (subdir / "release.json").write_text("{not json")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "fw-v1.0.1" in out.err
    assert "not valid JSON" in out.err


def test_import_dir_manifest_must_be_an_object(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    (subdir / "skypane-fw-v1.0.1.bin").write_bytes(b"x")
    (subdir / "release.json").write_text("[]")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "must be a JSON object" in out.err


def test_import_dir_missing_image_rejected(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    subdir = base / "fw-v1.0.1"
    subdir.mkdir(parents=True)
    # No skypane-fw-v1.0.1.bin written at all.
    (subdir / "release.json").write_text("{}")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 1
    assert "not a regular file" in out.err


def test_import_dir_skips_stray_top_level_file(tmp_path, capsys):
    base = tmp_path / "releases"
    state_dir = tmp_path / "state"
    _write_release_subdir(base, "fw-v1.0.1")
    base.mkdir(parents=True, exist_ok=True)
    (base / "README.txt").write_text("not a release directory")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "import-dir", str(base)])
    out = capsys.readouterr()

    assert rc == 0
    assert "added fw-v1.0.1" in out.out
    assert "README.txt" not in out.err


# --- import-bench ------------------------------------------------------------

def test_import_bench_records_bench_true_and_generated_note(tmp_path, capsys):
    state_dir = tmp_path / "state"
    image = tmp_path / "bench.bin"
    image.write_bytes(b"a-bench-image-payload")

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image), "--version", "fw-v1.0.1-bench1",
    ])
    out = capsys.readouterr().out

    assert rc == 0
    assert "added fw-v1.0.1-bench1" in out

    registry = firmware_registry.load_registry(str(state_dir))
    release = registry["releases"][0]
    assert release["version"] == "fw-v1.0.1-bench1"
    assert release["bench"] is True
    assert release["notes"] == ["Bench image (not a release)"]


def test_import_bench_symlinked_image_rejected(tmp_path, capsys):
    state_dir = tmp_path / "state"
    real_image = tmp_path / "real.bin"
    real_image.write_bytes(b"payload")
    link = tmp_path / "link.bin"
    link.symlink_to(real_image)

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(link), "--version", "fw-v1.0.1-bench1",
    ])
    out = capsys.readouterr()

    assert rc == 1
    assert "symlink" in out.err


def test_import_bench_rejects_bare_release_tag_version(tmp_path, capsys):
    """A bench version with no suffix could squat a future release's
    version -- the real CI release would then fail import with a sha
    conflict, wrongly blamed on the release itself.
    """
    state_dir = tmp_path / "state"
    image = tmp_path / "bench.bin"
    image.write_bytes(b"payload")

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image), "--version", "fw-v1.3.0", "--commit", COMMIT,
    ])
    out = capsys.readouterr()

    assert rc == 1
    assert "looks like a release tag" in out.err
    registry = firmware_registry.load_registry(str(state_dir))
    assert registry["releases"] == []


def test_import_bench_accepts_explicit_commit_outside_a_git_checkout(tmp_path, monkeypatch, capsys):
    """--commit lets import-bench run from a checkout-less release
    directory such as /opt/skypane/current (git archive output, no
    .git) -- the only place a real deployed frame's poll loop and byos
    ever read from.
    """
    state_dir = tmp_path / "state"
    image = tmp_path / "bench.bin"
    image.write_bytes(b"payload")
    monkeypatch.setattr(firmware_cli, "_repo_root", lambda: str(tmp_path))

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image), "--version", "fw-v1.0.1-bench1", "--commit", COMMIT,
    ])
    out = capsys.readouterr().out

    assert rc == 0
    assert "added fw-v1.0.1-bench1" in out
    registry = firmware_registry.load_registry(str(state_dir))
    assert registry["releases"][0]["commit"] == COMMIT


def test_import_bench_rejects_malformed_explicit_commit(tmp_path, capsys):
    state_dir = tmp_path / "state"
    image = tmp_path / "bench.bin"
    image.write_bytes(b"payload")

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image), "--version", "fw-v1.0.1-bench1", "--commit", "not-a-commit",
    ])
    out = capsys.readouterr()

    assert rc == 1
    assert "must be 40 lowercase hex characters" in out.err
    registry = firmware_registry.load_registry(str(state_dir))
    assert registry["releases"] == []


def test_import_bench_outside_a_git_checkout_reports_no_commit(tmp_path, monkeypatch, capsys):
    state_dir = tmp_path / "state"
    image = tmp_path / "bench.bin"
    image.write_bytes(b"payload")
    monkeypatch.setattr(firmware_cli, "_repo_root", lambda: str(tmp_path))

    rc = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image), "--version", "fw-v1.0.1-bench1",
    ])
    out = capsys.readouterr()

    assert rc == 1
    assert "could not resolve a git commit" in out.err


def test_current_commit_returns_none_when_git_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        firmware_cli.subprocess, "run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("git not found")),
    )
    assert firmware_cli._current_commit() is None


def test_import_bench_rebinding_existing_version_to_different_sha_fails(tmp_path, capsys):
    state_dir = tmp_path / "state"
    image1 = tmp_path / "bench1.bin"
    image1.write_bytes(b"payload-one")
    image2 = tmp_path / "bench2.bin"
    image2.write_bytes(b"payload-two-different")

    rc1 = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image1), "--version", "fw-v1.0.1-bench1",
    ])
    capsys.readouterr()
    assert rc1 == 0

    rc2 = firmware_cli.main([
        "--state-dir", str(state_dir), "import-bench",
        "--file", str(image2), "--version", "fw-v1.0.1-bench1",
    ])
    out = capsys.readouterr()

    assert rc2 == 1
    assert "already registered" in out.err


# --- list --------------------------------------------------------------------

def test_list_prints_version_published_at_size_and_installed_count(tmp_path, capsys):
    state_dir = tmp_path / "state"
    image = b"list-me-image-payload"
    manifest = {
        "version": "fw-v1.0.1", "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image), "released_at": "2026-09-28T00:00:00+00:00",
        "commit": COMMIT, "notes": [],
    }
    image_path = tmp_path / "image.bin"
    image_path.write_bytes(image)
    firmware_registry.publish_release(str(state_dir), manifest, str(image_path), now="2026-09-28T00:05:00+00:00")

    rc = firmware_cli.main(["--state-dir", str(state_dir), "list"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "fw-v1.0.1" in out
    assert "2026-09-28T00:05:00+00:00" in out
    assert str(len(image)) in out
    assert out.strip().endswith("0")


def test_list_no_releases_prints_placeholder(tmp_path, capsys):
    state_dir = tmp_path / "state"
    os.makedirs(str(state_dir), exist_ok=True)

    rc = firmware_cli.main(["--state-dir", str(state_dir), "list"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "no releases" in out
