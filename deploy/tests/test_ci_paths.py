# SPDX-License-Identifier: AGPL-3.0-only
"""deploy/tests/test_ci_paths.py -- the CI paths filter can only skip inert files.

The only non-Markdown files that start no CI run are the 3D model files under
hardware/cad. These tests prove that set is inert (nothing references it, only
model files live there) and that every other tracked file runs the whole
suite, using the same matcher that reads the paths list from ci.yml.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"
_CI = (_WORKFLOWS / "ci.yml").read_text()
_FIRMWARE = (_WORKFLOWS / "firmware.yml").read_text()
_DEPLOY = (_WORKFLOWS / "deploy.yml").read_text()

_SPEC = importlib.util.spec_from_file_location(
    "ci_path_filter", _ROOT / "scripts" / "ci_path_filter.py"
)
_PF = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PF)

_MODEL_EXTENSIONS = {".stl", ".blend", ".glb", ".3mf"}
_ALLOWED_IN_CAD = _MODEL_EXTENSIONS | {".md"}
_REVIEWED_EXCLUSIONS = {
    "**/*.md",
    ".planning/**",
    ".claude/**",
    "LICENSE",
    "hardware/cad/**/*.stl",
    "hardware/cad/**/*.blend",
    "hardware/cad/**/*.glb",
    "hardware/cad/**/*.3mf",
}
# The only tracked files that may name hardware/cad.
_MAY_NAME_CAD = {
    ".github/workflows/ci.yml",
    "deploy/tests/test_ci_paths.py",
    "deploy/tests/test_ci_runner.py",
    "scripts/test_ci_path_filter.py",
    "deploy/tests/test_docs.py",
}
_SCANNED_SUFFIXES = (
    ".py", ".sh", ".yml", ".yaml", ".toml", ".js", ".json", ".jsonl", ".cfg", ".ini",
)
_CAD_REFERENCE = re.compile(r"hardware['\"]?\s*[,/]\s*['\"]?cad\b")
_HARDWARE_WALK = re.compile(
    r"hardware.{0,80}(glob\(|rglob|os\.walk|iterdir|listdir)"
)


def _tracked(*pathspec):
    out = subprocess.run(
        ["git", "-c", "core.quotepath=off", "ls-files", "--", *pathspec],
        cwd=_ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return out.splitlines()


def _patterns(event, text=_CI):
    return _PF.workflow_paths(text, event)


def _is_inert(path):
    if path.endswith(".md") or path == "LICENSE":
        return True
    if path.startswith((".planning/", ".claude/")):
        return True
    return path.startswith("hardware/cad/") and Path(path).suffix in _MODEL_EXTENSIONS


def test_hardware_cad_holds_only_model_and_note_files():
    for path in _tracked("hardware/cad"):
        assert Path(path).suffix in _ALLOWED_IN_CAD, path


def test_negated_patterns_are_exactly_the_reviewed_set_for_both_events():
    for event in ("push", "pull_request"):
        negated = [p[1:] for p in _patterns(event) if p.startswith("!")]
        assert sorted(negated) == sorted(_REVIEWED_EXCLUSIONS), event


def test_the_two_event_lists_are_identical():
    assert _patterns("push") == _patterns("pull_request")


def test_every_tracked_file_that_is_not_inert_runs_the_suite():
    patterns = _patterns("push")
    files = [p for p in _tracked() if not _is_inert(p)]
    assert files
    for path in files:
        assert _PF.runs([path], patterns), path


def test_every_inert_file_starts_no_run_unless_re_included():
    patterns = _patterns("push")
    for path in _tracked("hardware/cad"):
        if Path(path).suffix in _MODEL_EXTENSIONS:
            assert not _PF.runs([path], patterns), path


def test_nothing_references_hardware_cad_or_walks_hardware():
    hits = set()
    for path in _tracked():
        if path.startswith((".planning/", ".claude/")):
            continue
        if not path.endswith(_SCANNED_SUFFIXES):
            continue
        text = (_ROOT / path).read_text(errors="replace")
        if _CAD_REFERENCE.search(text) or _HARDWARE_WALK.search(text):
            hits.add(path)
    assert hits <= _MAY_NAME_CAD, sorted(hits - _MAY_NAME_CAD)


def test_hypothetical_changes_decide_as_expected():
    patterns = _patterns("push")
    assert _PF.runs(["hardware/cad/new/tool.py"], patterns)
    assert _PF.runs(["hardware/cad/x.step"], patterns)
    assert _PF.runs(["firmware/main/a.c"], patterns)
    model_and_note = ["hardware/cad/print/a.stl", "README.md"]
    assert not _PF.runs(model_and_note, patterns)
    assert _PF.runs(model_and_note + ["server/x.py"], patterns)


def test_firmware_triggers_cannot_match_a_model_file():
    for event in ("push", "pull_request"):
        positive = _patterns(event, _FIRMWARE)
        assert "firmware/**" in positive
        assert "server/hardware.py" in positive
        assert not any(p.startswith("hardware") for p in positive)
        assert not _PF.runs(["hardware/cad/print/a.stl"], positive)


def test_deploy_shipped_path_check_does_not_list_hardware_cad():
    assert "hardware/cad" not in _DEPLOY
    assert "hardware" not in _DEPLOY.split("git diff --quiet", 1)[1].split("fi\n", 1)[0]
