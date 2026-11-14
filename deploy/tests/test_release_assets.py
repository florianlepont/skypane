"""scripts/fw_release_assets.py: which release assets the deploy downloads."""
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "fw_release_assets.py"
sys.path.insert(0, str(_SCRIPT.parent))
import fw_release_assets  # noqa: E402

TAG = "fw-v1.0.0"
KEY = "seeed-ee04-7in3-spectra6"
LEGACY = [f"skypane-{TAG}.bin", "release.json"]
TYPED = [f"release-{KEY}.json", f"skypane-{KEY}-{TAG}.bin"]


def _cli(tag, names):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), tag],
        input="".join(n + "\n" for n in names),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_live_only_release_is_the_legacy_pair():
    assert fw_release_assets.wanted_assets(TAG, ["release.json", f"skypane-{TAG}.bin"]) == LEGACY


def test_legacy_then_typed_pair():
    names = [*TYPED, *LEGACY]
    assert fw_release_assets.wanted_assets(TAG, names) == LEGACY + TYPED


def test_typed_only_release():
    assert fw_release_assets.wanted_assets(TAG, TYPED) == TYPED


@pytest.mark.parametrize("missing", [0, 1])
def test_incomplete_typed_pair_yields_nothing(missing):
    names = [n for i, n in enumerate(TYPED) if i != missing]
    assert fw_release_assets.wanted_assets(TAG, names) == []


@pytest.mark.parametrize(
    "key",
    ["UPPER", "a/b", "$(x)", "a;b", "a b", "x" * 65, "", "..", "a`b`"],
)
def test_hostile_keys_are_never_returned(key):
    names = [f"release-{key}.json", f"skypane-{key}-{TAG}.bin"]
    assert fw_release_assets.wanted_assets(TAG, names) == []


def test_max_length_key_is_accepted():
    key = "a" * 64
    names = [f"release-{key}.json", f"skypane-{key}-{TAG}.bin"]
    assert fw_release_assets.wanted_assets(TAG, names) == names


def test_only_the_legacy_manifest_name_is_not_a_typed_item():
    assert fw_release_assets.wanted_assets(TAG, ["release.json"]) == []


def test_output_is_sorted_by_key():
    names = []
    for key in ("zzz", "aaa"):
        names += [f"release-{key}.json", f"skypane-{key}-{TAG}.bin"]
    assert fw_release_assets.wanted_assets(TAG, names) == [
        "release-aaa.json", f"skypane-aaa-{TAG}.bin",
        "release-zzz.json", f"skypane-zzz-{TAG}.bin",
    ]


def test_cli_prints_one_name_per_line():
    result = _cli(TAG, [*TYPED, *LEGACY, "notes.txt"])
    assert result.returncode == 0
    assert result.stdout.splitlines() == LEGACY + TYPED


def test_cli_exits_1_and_prints_nothing_when_nothing_wanted():
    result = _cli(TAG, ["release.json", "other.bin"])
    assert result.returncode == 1
    assert result.stdout == ""


@pytest.mark.parametrize("tag", ["a/b", "a b", "$(x)", "a;b", "", "-x"])
def test_cli_rejects_hostile_tags(tag):
    result = _cli(tag, LEGACY)
    assert result.returncode == 2
    assert result.stdout == ""
