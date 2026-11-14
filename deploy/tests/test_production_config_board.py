"""Behaviour of the board argument of firmware/tests/check_production_config.sh built mode."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "firmware" / "tests" / "check_production_config.sh"
FIXTURES = REPO / "firmware" / "tests" / "fixtures" / "production_config"


def make_build(tmp_path: Path, board: str) -> Path:
    """Copy a fixture sdkconfig next to the stand-in artefacts built mode requires."""
    build = tmp_path / f"build-{board}"
    build.mkdir()
    shutil.copy(FIXTURES / board / "sdkconfig", build / "sdkconfig")
    (build / "skypane.bin").write_bytes(b"image")
    (build / "project_description.json").write_text('{"project_version": "v1.2.3"}')
    return build


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def mutate(build: Path, old_prefix: str, new_line: str | None) -> None:
    path = build / "sdkconfig"
    lines = path.read_text().splitlines()
    out = []
    for line in lines:
        if line.startswith(old_prefix):
            if new_line is not None:
                out.append(new_line)
        else:
            out.append(line)
    path.write_text("\n".join(out) + "\n")


def test_second_fixture_passes(tmp_path):
    build = make_build(tmp_path, "second")
    result = run("built", str(build), "second")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "production-config built: PASS" in result.stdout


def test_ee02_fixture_passes_with_and_without_board(tmp_path):
    build = make_build(tmp_path, "ee02")
    assert run("built", str(build), "ee02").returncode == 0
    assert run("built", str(build)).returncode == 0


def test_second_fixture_without_board_argument_passes(tmp_path):
    build = make_build(tmp_path, "second")
    assert run("built", str(build)).returncode == 0


@pytest.mark.parametrize(
    ("prefix", "replacement", "named"),
    [
        ("CONFIG_FP_PANEL_7IN3E", "# CONFIG_FP_PANEL_7IN3E is not set", "CONFIG_FP_PANEL_7IN3E=y"),
        ("CONFIG_FP_PANEL_BUFFER_BYTES", "CONFIG_FP_PANEL_BUFFER_BYTES=960000", "CONFIG_FP_PANEL_BUFFER_BYTES=192000"),
        ("CONFIG_FP_HW_REV", 'CONFIG_FP_HW_REV="proto-e1004"', "proto-ee04"),
        ("CONFIG_SKYPANE_HW_TYPE", 'CONFIG_SKYPANE_HW_TYPE="xiao-ee02-13in3-spectra6"', "CONFIG_SKYPANE_HW_TYPE"),
        ("CONFIG_FP_PANEL_BUFFER_BYTES", None, "CONFIG_FP_PANEL_BUFFER_BYTES=192000"),
    ],
)
def test_second_negative_cases(tmp_path, prefix, replacement, named):
    build = make_build(tmp_path, "second")
    mutate(build, prefix, replacement)
    result = run("built", str(build), "second")
    assert result.returncode != 0
    assert named in result.stdout


def test_empty_hardware_key_fails(tmp_path):
    build = make_build(tmp_path, "second")
    mutate(build, "CONFIG_SKYPANE_HW_TYPE", 'CONFIG_SKYPANE_HW_TYPE=""')
    result = run("built", str(build), "second")
    assert result.returncode != 0
    assert "CONFIG_SKYPANE_HW_TYPE" in result.stdout


def test_ee02_with_panel_option_set_fails(tmp_path):
    build = make_build(tmp_path, "ee02")
    mutate(build, "# CONFIG_FP_PANEL_7IN3E", "CONFIG_FP_PANEL_7IN3E=y")
    assert run("built", str(build), "ee02").returncode != 0


def test_ee02_with_missing_key_fails(tmp_path):
    build = make_build(tmp_path, "ee02")
    mutate(build, "CONFIG_SKYPANE_HW_TYPE", None)
    assert run("built", str(build), "ee02").returncode != 0


def test_second_fixture_fails_as_ee02(tmp_path):
    build = make_build(tmp_path, "second")
    assert run("built", str(build), "ee02").returncode != 0


def test_ee02_fixture_fails_as_second(tmp_path):
    build = make_build(tmp_path, "ee02")
    assert run("built", str(build), "second").returncode != 0


def test_bad_board_word_prints_usage(tmp_path):
    build = make_build(tmp_path, "second")
    result = run("built", str(build), "third")
    assert result.returncode == 2
    assert "usage" in result.stderr
