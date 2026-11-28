# SPDX-License-Identifier: AGPL-3.0-only
"""Behaviour of scripts/ci_path_filter.py: GitHub path-filter semantics, the
workflow reader, and the commit-range measurement on throwaway repositories."""
import importlib.util
import pathlib
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "ci_path_filter.py"
_SPEC = importlib.util.spec_from_file_location("ci_path_filter", _PATH)
pf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pf)

_CI = (_ROOT / ".github" / "workflows" / "ci.yml").read_text()
_MODEL_EXCLUSIONS = [f"!hardware/cad/**/*.{ext}" for ext in ("stl", "blend", "glb", "3mf")]
# The workflow's own list, with the 3D-model exclusions present exactly once.
_REAL = pf.workflow_paths(_CI, "push")
_REAL = _REAL + [p for p in _MODEL_EXCLUSIONS if p not in _REAL]

_WORKFLOW = """name: CI
on:
  workflow_dispatch:
  push:
    branches: [main]
    # comment
    paths:
{push}
  pull_request:
    paths:
{pull}

jobs:
  x:
    runs-on: y
"""


def _workflow(push, pull):
    def block(items):
        return "\n".join(f"      - '{item}'" for item in items)
    return _WORKFLOW.format(push=block(push), pull=block(pull))


@pytest.mark.parametrize("files", [
    ["README.md"],
    ["docs/x.md"],
    [".planning/a.json"],
    ["LICENSE"],
    ["hardware/cad/print/a.stl"],
    ["hardware/cad/a.blend", "hardware/cad/b.glb", "hardware/cad/c.3mf"],
    ["hardware/cad/a.stl", "README.md"],
    [],
])
def test_inert_change_sets_start_no_run(files):
    assert pf.runs(files, _REAL) is False


@pytest.mark.parametrize("files", [
    ["deploy/README.md"],
    ["server/assets/fonts/VENDOR.md"],
    ["hardware/cad/new/tool.py"],
    ["hardware/cad/x.step"],
    ["firmware/main/a.c"],
    ["hardware/logtools.py"],
    ["design-exploration/plane-screen/mock_fonts.py"],
    ["hardware/cad/a.stl", "server/x.py"],
])
def test_other_change_sets_run(files):
    assert pf.runs(files, _REAL) is True


def test_star_stays_within_a_segment_and_double_star_crosses_them():
    assert pf.runs(["a/b/c.txt"], ["a/*"]) is False
    assert pf.runs(["a/b.txt"], ["a/*"]) is True
    assert pf.runs(["a/b/c.txt"], ["a/**"]) is True
    assert pf.runs(["top.md"], ["**/*.md"]) is True
    assert pf.runs(["x/y/top.md"], ["**/*.md"]) is True
    assert pf.runs(["ab"], ["a?"]) is True
    assert pf.runs(["a/"], ["a?"]) is False


def test_dots_and_regex_characters_are_literal():
    assert pf.runs(["axmd"], ["a.md"]) is False
    assert pf.runs(["a+b"], ["a+b"]) is True


def test_last_matching_pattern_decides():
    assert pf.runs(["a.md"], ["**", "!**/*.md", "a.md"]) is True
    assert pf.runs(["b.md"], ["**", "!**/*.md", "a.md"]) is False
    assert pf.runs(["a.md"], ["a.md", "!**/*.md"]) is False


def test_workflow_paths_reads_both_events():
    assert pf.workflow_paths(_CI, "push") == pf.workflow_paths(_CI, "pull_request")
    assert pf.workflow_paths(_CI, "push")[0] == "**"


def test_workflow_paths_fails_when_the_block_is_missing():
    with pytest.raises(pf.WorkflowError):
        pf.workflow_paths("on:\n  push:\n    branches: [main]\n", "push")
    with pytest.raises(pf.WorkflowError):
        pf.workflow_paths("name: x\n", "pull_request")


def test_decide_exits_by_outcome(tmp_path, capsys):
    workflow = tmp_path / "ci.yml"
    workflow.write_text(_workflow(["**", "!**/*.md"], ["**", "!**/*.md"]))
    args = ["--workflow", str(workflow)]
    assert pf.main(["decide", *args, "a.md"]) == 1
    assert capsys.readouterr().out.strip() == "skip"
    assert pf.main(["decide", *args, "a.md", "b.py"]) == 0
    assert capsys.readouterr().out.strip() == "run"


def test_decide_rejects_differing_lists(tmp_path):
    workflow = tmp_path / "ci.yml"
    workflow.write_text(_workflow(["**", "!**/*.md"], ["**"]))
    assert pf.main(["decide", "--workflow", str(workflow), "a.py"]) == 2


def test_decide_rejects_a_workflow_without_paths(tmp_path):
    workflow = tmp_path / "ci.yml"
    workflow.write_text("name: x\n")
    assert pf.main(["decide", "--workflow", str(workflow), "a.py"]) == 2
    assert pf.main(["decide", "--workflow", str(tmp_path / "none.yml"), "a.py"]) == 2


def _git(repo, *argv):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    *argv], cwd=repo, check=True, capture_output=True)


def _commit(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    _git(repo, "add", name)
    _git(repo, "commit", "-m", f"change {name}")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "server/start.py", "x = 1\n")
    _commit(root, "hardware/cad/a.stl", "solid\n")
    _commit(root, "notes.md", "text\n")
    _commit(root, "server/other.py", "y = 2\n")
    return root


def test_measure_counts_would_run_and_would_skip(repo, tmp_path, capsys):
    workflow = tmp_path / "ci.yml"
    patterns = ["**", "!**/*.md", "!hardware/cad/**/*.stl"]
    workflow.write_text(_workflow(patterns, patterns))
    code = pf.main(["measure", "--last", "4", "--workflow", str(workflow),
                    "--cwd", str(repo)])
    out = capsys.readouterr().out
    assert code == 0
    lines = out.strip().splitlines()
    assert [line.split()[1] for line in lines[:4]] == ["run", "skip", "skip", "run"]
    assert "commits 4, would run 2, would skip 2, skip 50.0%" in lines[-1]


def test_measure_reports_the_actual_count_when_history_is_shorter(repo, tmp_path, capsys):
    workflow = tmp_path / "ci.yml"
    workflow.write_text(_workflow(["**"], ["**"]))
    pf.main(["measure", "--last", "100", "--workflow", str(workflow),
             "--cwd", str(repo)])
    assert "commits 4, would run 4, would skip 0" in capsys.readouterr().out


def test_measure_uses_the_first_parent_diff_of_a_merge(repo, tmp_path, capsys):
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, "side.py", "z = 3\n")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-m", "merge side", "side")
    workflow = tmp_path / "ci.yml"
    workflow.write_text(_workflow(["**", "!**/*.md"], ["**", "!**/*.md"]))
    pf.main(["measure", "--last", "1", "--workflow", str(workflow),
             "--cwd", str(repo)])
    first = capsys.readouterr().out.splitlines()[0].split()
    assert first[1] == "run"
    assert first[2] == "1"
