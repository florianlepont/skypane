"""Behaviour tests for server/firmware_cli.py -- the deploy-time operator
CLI that publishes releases into server/firmware_registry.py.

Every assertion is about observable behaviour (exit codes, stdout/stderr
lines, registry contents) -- never about the module's source text.
"""
import hashlib
import os

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
