"""Skin-tone trial library and command line."""
import subprocess
import sys
from pathlib import Path

import pytest
from photo_scenes import face_scene, to_stored_jpeg
from PIL import Image
from skypane_test_support import REPO_ROOT as _ROOT
from skypane_test_support import child_env

from server.photo import __main__ as cli
from server.photo import trial
from server.photo.normalize import PhotoRejected
from server.photo.prep import DEFAULT_PREP

REPO_ROOT = Path(_ROOT)
SMALL_PANELS = {"portrait": (60, 80), "landscape": (80, 48)}
ONE_SET = [("default", DEFAULT_PREP)]


def _write_photo(path):
    img, _ = face_scene("IV")
    path.write_bytes(to_stored_jpeg(img))


def test_grid_writes_a_sheet_per_tone_with_finite_rows(tmp_path):
    rows = trial.run_grid(tmp_path, panels=SMALL_PANELS, sets=ONE_SET)
    sheets = sorted(p.name for p in tmp_path.glob("*.png"))
    assert sheets == [f"skin-tone-{t}.png" for t in ("I", "II", "III", "IV", "V", "VI")]
    assert len(rows) == 6 * 2 * 2 * 2
    assert trial.rows_finite(rows)
    assert {r["scene"] for r in rows} == {"full", "dull"}
    for sheet in tmp_path.glob("*.png"):
        with Image.open(sheet) as img:
            assert img.format == "PNG"


def test_bands_rows_measure_inside_the_photo_area(tmp_path):
    rows = trial.run_grid(tmp_path, tones=["III"], panels=SMALL_PANELS, sets=ONE_SET)
    for r in rows:
        assert sum(r["palette_share"]) == pytest.approx(1.0)
        assert r["fidelity_error"] >= 0


def test_param_sets_are_one_factor_around_the_default():
    sets = dict(trial.param_sets())
    assert sets["default"] == DEFAULT_PREP
    assert len(set(sets.values())) == len(sets)
    assert {"sat1.0", "sat1.3", "str0.5", "cut0.5", "cut2.0"} <= set(sets)


def test_render_file_writes_both_previews(tmp_path):
    src = tmp_path / "in" / "My Portrait!.jpg"
    src.parent.mkdir()
    _write_photo(src)
    written = trial.render_file(src, tmp_path / "out", "bands")
    assert sorted(p.name for p in written) == [
        "My_Portrait_-landscape-bands.png", "My_Portrait_-portrait-bands.png"]
    for p in written:
        with Image.open(p) as img:
            assert img.format == "PNG" and img.mode == "P"
            assert img.getextrema()[1] <= 5


def test_render_file_reports_rejection_reason(tmp_path):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"not an image")
    with pytest.raises(PhotoRejected) as info:
        trial.render_file(bad, tmp_path / "out")
    assert info.value.reason


def test_repository_output_is_refused(tmp_path):
    with pytest.raises(ValueError):
        trial.check_out_dir(REPO_ROOT / "scratch-out")
    with pytest.raises(ValueError):
        trial.check_out_dir(REPO_ROOT)
    assert not (REPO_ROOT / "scratch-out").exists()


def test_default_output_is_outside_the_repository():
    out = trial.default_out_dir()
    try:
        assert REPO_ROOT not in out.resolve().parents
    finally:
        out.rmdir()


def test_cli_in_process(tmp_path, capsys):
    src = tmp_path / "p.jpg"
    _write_photo(src)
    assert cli.main(["--in", str(src), "--out", str(tmp_path / "o")]) == 0
    assert len(list((tmp_path / "o").glob("*.png"))) == 2
    assert capsys.readouterr().out.count(".png") == 2


def test_cli_failures_return_two(tmp_path, capsys):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"nope")
    assert cli.main(["--in", str(bad), "--out", str(tmp_path / "o")]) == 2
    assert capsys.readouterr().err.startswith("rejected: ")
    src = tmp_path / "p.jpg"
    _write_photo(src)
    assert cli.main(["--in", str(src), "--out", str(tmp_path), "--fit", "zoom"]) == 2
    assert cli.main(["--in", str(src)]) == 2
    assert cli.main(["--in", str(src), "--out", str(REPO_ROOT / "x")]) == 2
    assert not (REPO_ROOT / "x").exists()


def test_cli_subprocess_synthetic_smoke(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "server.photo", "--synthetic", "--out", str(tmp_path)],
        env=child_env(), cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(list(tmp_path.glob("skin-tone-*.png"))) == 6
