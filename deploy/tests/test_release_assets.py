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


# --- the deploy.yml "Download firmware releases" step, run against a fake gh ---

_DEPLOY_YML = _SCRIPT.parent.parent / ".github" / "workflows" / "deploy.yml"


def _download_step_script():
    """The run: body of the Download firmware releases step."""
    lines = _DEPLOY_YML.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "- name: Download firmware releases")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body = []
    for ln in lines[run + 1:]:
        if ln.strip() and len(ln) - len(ln.lstrip()) <= indent:
            break
        body.append(ln[indent + 2:] if ln.strip() else "")
    return "\n".join(body) + "\n"


_FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
root = os.environ["FAKE_GH_DIR"]
assets = json.load(open(os.path.join(root, "assets.json")))
if a[:2] == ["release", "list"]:
    print("\\n".join(assets))
elif a[:2] == ["release", "view"]:
    print("\\n".join(assets[a[2]]))
elif a[:2] == ["release", "download"]:
    tag = a[2]
    pats = [a[i + 1] for i, x in enumerate(a) if x == "--pattern"]
    out = a[a.index("--dir") + 1]
    with open(os.path.join(root, "downloads.log"), "a") as f:
        for p in pats:
            f.write(tag + "/" + p + "\\n")
            open(os.path.join(out, p), "w").write("x")
else:
    sys.exit(9)
"""


def _run_download_step(tmp_path, assets_by_tag):
    import json
    import os

    work = tmp_path / "work"
    work.mkdir()
    (work / "scripts").symlink_to(_SCRIPT.parent)
    fake = tmp_path / "fake"
    (fake / "bin").mkdir(parents=True)
    (fake / "assets.json").write_text(json.dumps(assets_by_tag))
    gh = fake / "bin" / "gh"
    gh.write_text(_FAKE_GH)
    gh.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(fake / "bin") + os.pathsep + env["PATH"]
    env["FAKE_GH_DIR"] = str(fake)
    result = subprocess.run(
        ["bash", "-c", _download_step_script()],
        cwd=work, env=env, capture_output=True, text=True, timeout=60,
    )
    log = fake / "downloads.log"
    downloaded = log.read_text().splitlines() if log.exists() else []
    files = sorted(str(p.relative_to(work / "firmware-releases")) for p in (work / "firmware-releases").rglob("*") if p.is_file())
    return result, downloaded, files


def test_ci_step_live_only_release_downloads_exactly_the_legacy_pair(tmp_path):
    tag = "fw-v1.0.0"
    result, downloaded, files = _run_download_step(
        tmp_path, {tag: [f"skypane-{tag}.bin", "release.json", "notes.txt"]})
    assert result.returncode == 0, result.stderr
    assert sorted(downloaded) == sorted([f"{tag}/skypane-{tag}.bin", f"{tag}/release.json"])
    assert files == [f"{tag}/release.json", f"{tag}/skypane-{tag}.bin"]
    assert "::warning::" not in result.stdout


def test_ci_step_incomplete_tag_warns_and_skips(tmp_path):
    tag = "fw-v1.0.0"
    result, downloaded, files = _run_download_step(tmp_path, {tag: [f"skypane-{tag}.bin"]})
    assert result.returncode == 0, result.stderr
    assert downloaded == [] and files == []
    assert (
        f"::warning::release {tag} is missing skypane-{tag}.bin or release.json"
        " - skipping its firmware import"
    ) in result.stdout


def test_ci_step_typed_pair_is_downloaded_with_exact_names(tmp_path):
    tag = "fw-v1.0.0"
    names = [f"skypane-{tag}.bin", "release.json", *TYPED, "release-BAD$(x).json"]
    result, downloaded, _ = _run_download_step(tmp_path, {tag: names})
    assert result.returncode == 0, result.stderr
    assert sorted(downloaded) == sorted(f"{tag}/{n}" for n in LEGACY + TYPED)
