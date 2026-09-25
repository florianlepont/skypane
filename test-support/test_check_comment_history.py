"""Tests for scripts/check_comment_history.py, the comment-history guard.

Loads the tool by file path (it is a standalone script, not a package) and
exercises its pattern matching, per-language extraction, same-code
comparison and CLI subcommands directly, plus one end-to-end `check` run
over a throwaway git repository with a planted history ID.
"""
import gzip
import importlib.util
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_PATH = os.path.join(REPO_ROOT, "scripts", "check_comment_history.py")


def _load_tool():
    spec = importlib.util.spec_from_file_location("check_comment_history", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cch = _load_tool()


def _hits(text):
    """Return the list of (pattern_name, matched_text) found in a comment/docstring blob."""
    return [(name, matched) for name, _start, matched in cch.find_pattern_hits(text)]


def _hit_names(text):
    return {name for name, _matched in _hits(text)}


# ---------------------------------------------------------------------------
# Pattern positives, one per pattern x wrapped in each applicable comment
# syntax's literal delimiters (the delimiters themselves are irrelevant to
# find_pattern_hits, which operates on already-extracted comment text; the
# per-syntax extraction is proven separately below).
# ---------------------------------------------------------------------------

PLAN_ARTIFACT_SAMPLES = [
    "22-08-PLAN.md",
    "19-REVIEW.md",
    "06.6.3-CONTEXT",
    "12-04-SUMMARY.md",
    "07-02-RESEARCH",
    "14-01a-VERIFICATION.md",
    "09-03-UI-SPEC",
    "20-05-PATTERNS",
    "18-02-VALIDATION",
    "22-11-UAT",
]


@pytest.mark.parametrize("sample", PLAN_ARTIFACT_SAMPLES)
def test_plan_artifact_pattern_positive(sample):
    text = "# see %s for details" % sample
    assert "plan-artifact" in _hit_names(text), "did not flag %r" % sample


D_ID_SAMPLES = ["D-06", "D-A3", "D-34-03", "D-1", "D-123"]


@pytest.mark.parametrize("sample", D_ID_SAMPLES)
def test_d_id_pattern_positive(sample):
    text = "// decision %s applies here" % sample
    matched = [m for name, m in _hits(text) if name == "d-id"]
    assert sample in matched, "did not flag the full id %r, got %r" % (sample, matched)


ALLOWLISTED_PREFIXES = [
    "CFG", "TST", "FW", "INT", "CMP", "SEC", "DEVICE", "HYG", "EFF", "ARC",
    "RER", "PLANE", "DOC", "VIS", "MSG", "UXA", "UIR", "MR", "CP", "DP",
    "SEED", "UAT", "QT", "WR", "CR", "IN", "BL",
]


@pytest.mark.parametrize("prefix", ALLOWLISTED_PREFIXES)
def test_prefix_id_pattern_positive(prefix):
    text = "# requirement %s-14 covers this" % prefix
    assert "prefix-id" in _hit_names(text), "did not flag prefix %r" % prefix


THREAT_ID_SAMPLES = ["T-32-01", "T-32-01-01", "T-35-01"]


@pytest.mark.parametrize("sample", THREAT_ID_SAMPLES)
def test_threat_id_pattern_positive(sample):
    text = "/* threat %s mitigated below */" % sample
    assert "threat-id" in _hit_names(text), "did not flag %r" % sample


def test_quick_task_pattern_positive():
    text = "# fixed in quick task 260923-gaf"
    assert "quick-task" in _hit_names(text)


def test_phase_word_pattern_positive():
    text = "# left over from Phase 28"
    assert "phase-word" in _hit_names(text)


def test_planning_path_pattern_positive():
    text = "# see .planning/audits/2026-09-23-code-audit.md"
    assert "planning-path" in _hit_names(text)


BARE_PLAN_ID_POSITIVES = [
    "# see plan 22-08 for the rationale",
    "# see Plan 22-08 for the rationale",
    "# 22-08 Task 3 covers this",
]


@pytest.mark.parametrize("text", BARE_PLAN_ID_POSITIVES)
def test_bare_plan_id_pattern_positive(text):
    assert "bare-plan-id" in _hit_names(text), "did not flag %r" % text


# ---------------------------------------------------------------------------
# Negatives: legitimate technical text that must never be flagged, and IDs
# that only appear where the guard must not look (string literals, JS
# URLs/regex literals, CSS url(), Python f-strings).
# ---------------------------------------------------------------------------

NEGATIVE_TEXTS = [
    "# hashed with SHA-256",
    "# encoded as UTF-8",
    "# see VPS-1 for the host",
    "# served over HTTP-2",
    "# generated on 2026-09-23",
    "# vendored as runway-02-20.png",
    "# see pages 10-20 of the datasheet",
    "# happens once in a blue moon, like the phase of the moon",
    "# retry after phase 2 completes",
]


@pytest.mark.parametrize("text", NEGATIVE_TEXTS)
def test_negative_text_not_flagged(text):
    assert _hits(text) == [], "false positive on %r: %r" % (text, _hits(text))


def test_id_inside_python_string_literal_not_flagged():
    source = 'x = "see 22-08-PLAN.md for details"  # unrelated comment\n'
    spans = cch.extract_python(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" not in _hit_names(combined)


def test_id_inside_python_fstring_not_flagged():
    source = 'msg = f"decision D-06 applies"  # nothing to see here\n'
    spans = cch.extract_python(source)
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" not in _hit_names(combined)


def test_id_inside_js_url_not_flagged():
    source = 'const u = "https://example.org/22-08-PLAN.md"; // fetch it\n'
    spans = cch.extract_js(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" not in _hit_names(combined)


def test_id_inside_js_regex_literal_not_flagged():
    source = "const re = /D-06/; // matches a decision id\n"
    spans = cch.extract_js(source)
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" not in _hit_names(combined)


def test_id_inside_css_url_not_flagged():
    source = "body { background: url(22-08-PLAN.md); } /* background image */\n"
    spans = cch.extract_css(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" not in _hit_names(combined)


# ---------------------------------------------------------------------------
# Per-syntax extraction: the plan-artifact and d-id patterns each planted in
# every comment syntax that can carry it.
# ---------------------------------------------------------------------------

def test_python_hash_comment_extraction_flags_id():
    source = "x = 1  # see 22-08-PLAN.md\n"
    spans = cch.extract_python(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" in _hit_names(combined)


def test_python_docstring_extraction_flags_id():
    source = '''def f():\n    """Does a thing (D-06)."""\n    return 1\n'''
    spans = cch.extract_python(source)
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" in _hit_names(combined)


def test_c_line_comment_extraction_flags_id():
    source = 'int x = 1; // see 22-08-PLAN.md\n'
    spans = cch.extract_c(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" in _hit_names(combined)


def test_c_block_comment_extraction_flags_id():
    source = '/* decision D-06 applies */\nint x = 1;\n'
    spans = cch.extract_c(source)
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" in _hit_names(combined)


def test_js_line_comment_extraction_flags_id():
    source = 'let x = 1; // see 22-08-PLAN.md\n'
    spans = cch.extract_js(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" in _hit_names(combined)


def test_js_block_comment_extraction_flags_id():
    source = '/* decision D-06 applies */\nlet x = 1;\n'
    spans = cch.extract_js(source)
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" in _hit_names(combined)


def test_css_block_comment_extraction_flags_id():
    source = '/* see 22-08-PLAN.md */\nbody { color: red; }\n'
    spans = cch.extract_css(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" in _hit_names(combined)


def test_hash_format_extraction_flags_id():
    source = "#!/bin/sh\n# decision D-06 applies\necho hi\n"
    spans = cch.extract_hash(source, "example.sh")
    combined = "\n".join(text for _line, text in spans)
    assert "d-id" in _hit_names(combined)


def test_hash_format_ignores_hash_inside_quotes():
    source = 'echo "no # comment here"\n'
    spans = cch.extract_hash(source, "example.sh")
    assert spans == []


def test_xml_comment_extraction_flags_id():
    source = "<plist>\n<!-- see 22-08-PLAN.md -->\n</plist>\n"
    spans = cch.extract_xml(source)
    combined = "\n".join(text for _line, text in spans)
    assert "plan-artifact" in _hit_names(combined)


# ---------------------------------------------------------------------------
# same-code
# ---------------------------------------------------------------------------

def _write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


@pytest.fixture
def scratch_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def _commit_all(repo, message):
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_same_code_python_equal_for_comment_only_edit(scratch_repo):
    _write(scratch_repo / "m.py", "def f():\n    # 22-08-PLAN.md note\n    return 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.py", "def f():\n    # trimmed note\n    return 1\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"])
    assert differing == []


def test_same_code_python_differs_for_code_token_change(scratch_repo):
    _write(scratch_repo / "m.py", "def f():\n    return 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.py", "def f():\n    return 2\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"])
    assert differing != []


def test_same_code_python_differs_for_dropped_pragma(scratch_repo):
    _write(scratch_repo / "m.py", "import os  # noqa: F401\nx = 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.py", "import os\nx = 1\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"])
    assert differing != []


def test_same_code_python_differs_for_changed_spdx_line(scratch_repo):
    _write(scratch_repo / "m.py", "# SPDX-License-Identifier: Apache-2.0\nx = 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.py", "# SPDX-License-Identifier: MIT\nx = 1\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"])
    assert differing != []


def test_same_code_python_keeps_module_docstring_when_dunder_doc_read(scratch_repo):
    _write(
        scratch_repo / "m.py",
        '"""Old help text."""\nimport argparse\nargparse.ArgumentParser(description=__doc__)\n',
    )
    base = _commit_all(scratch_repo, "base")
    _write(
        scratch_repo / "m.py",
        '"""New help text."""\nimport argparse\nargparse.ArgumentParser(description=__doc__)\n',
    )
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"])
    assert differing != [], "a changed module docstring must count as code when __doc__ is read"


def test_same_code_allow_suppresses_a_listed_file(scratch_repo):
    _write(scratch_repo / "m.py", "def f():\n    return 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.py", "def f():\n    return 2\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.py"], allow=["m.py"])
    assert differing == []


def test_same_code_cli_allow_takes_one_path_and_keeps_positional_paths(scratch_repo, monkeypatch):
    _write(scratch_repo / "a.py", "x = 1\n")
    _write(scratch_repo / "b.py", "y = 1\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "a.py", "x = 2\n")
    _write(scratch_repo / "b.py", "y = 2\n")
    monkeypatch.chdir(scratch_repo)
    assert cch.main(["same-code", "--base", base, "--allow", "a.py", "b.py"]) == 1
    assert cch.main(["same-code", "--base", base, "--allow", "a.py", "--allow", "b.py", "a.py", "b.py"]) == 0


def test_same_code_c_equal_for_comment_only_edit(scratch_repo):
    _write(scratch_repo / "m.c", "int f(void) {\n    // 22-08-PLAN.md note\n    return 1;\n}\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.c", "int f(void) {\n    // trimmed note\n    return 1;\n}\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.c"])
    assert differing == []


def test_same_code_c_differs_for_code_token_change(scratch_repo):
    _write(scratch_repo / "m.c", "int f(void) {\n    return 1;\n}\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.c", "int f(void) {\n    return 2;\n}\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.c"])
    assert differing != []


def test_same_code_js_equal_for_comment_only_edit(scratch_repo):
    _write(scratch_repo / "m.js", "function f() {\n  // 22-08-PLAN.md note\n  return 1;\n}\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.js", "function f() {\n  // trimmed note\n  return 1;\n}\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.js"])
    assert differing == []


def test_same_code_js_differs_for_code_token_change(scratch_repo):
    _write(scratch_repo / "m.js", "function f() {\n  return 1;\n}\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.js", "function f() {\n  return 2;\n}\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.js"])
    assert differing != []


def test_same_code_css_equal_for_comment_only_edit(scratch_repo):
    _write(scratch_repo / "m.css", "/* 22-08-PLAN.md note */\nbody { color: red; }\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.css", "/* trimmed note */\nbody { color: red; }\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.css"])
    assert differing == []


def test_same_code_css_differs_for_code_token_change(scratch_repo):
    _write(scratch_repo / "m.css", "body { color: red; }\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.css", "body { color: blue; }\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.css"])
    assert differing != []


def test_same_code_hash_format_equal_for_comment_only_edit(scratch_repo):
    _write(scratch_repo / "m.sh", "#!/bin/sh\n# 22-08-PLAN.md note\necho hi\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.sh", "#!/bin/sh\n# trimmed note\necho hi\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.sh"])
    assert differing == []


def test_same_code_hash_format_differs_for_code_line_change(scratch_repo):
    _write(scratch_repo / "m.sh", "#!/bin/sh\necho hi\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.sh", "#!/bin/sh\necho bye\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.sh"])
    assert differing != []


def test_same_code_sdkconfig_removed_config_line_differs(scratch_repo):
    _write(scratch_repo / "sdkconfig.defaults", "# a comment\nCONFIG_FOO=y\n# CONFIG_BAR is not set\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "sdkconfig.defaults", "# a comment\nCONFIG_FOO=y\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["sdkconfig.defaults"])
    assert differing != [], "dropping a sdkconfig CONFIG_ line must count as a code change"


def test_same_code_pragma_multiset_change_alone_differs_for_hash_format(scratch_repo):
    _write(scratch_repo / "m.sh", "#!/bin/sh\n# shellcheck disable=SC2086\necho hi\n")
    base = _commit_all(scratch_repo, "base")
    _write(scratch_repo / "m.sh", "#!/bin/sh\necho hi\n")
    differing = cch.same_code(str(scratch_repo), base, paths=["m.sh"])
    assert differing != []


# ---------------------------------------------------------------------------
# ratio
# ---------------------------------------------------------------------------

def test_ratio_tsv_columns_and_values(tmp_path):
    f = tmp_path / "m.py"
    _write(f, "x = 1  # 22-08-PLAN.md\ny = 2\n")
    out = tmp_path / "ratio.tsv"
    cch.write_ratio_tsv([str(f)], str(out), root=str(tmp_path))
    lines = out.read_text().splitlines()
    header = lines[0].split("\t")
    assert header == ["path", "lines", "comment_lines", "ratio", "history_hits", "bytes", "gzip_bytes"]
    row = lines[1].split("\t")
    assert row[0] == "m.py"
    assert int(row[1]) == 2
    assert int(row[2]) == 1
    assert int(row[4]) == 1
    assert int(row[5]) == f.stat().st_size
    assert int(row[6]) == len(gzip.compress(f.read_bytes(), 9))


def test_ratio_markdown_before_after_table(tmp_path):
    f = tmp_path / "m.py"
    _write(f, "x = 1  # 22-08-PLAN.md\ny = 2\n")
    before = tmp_path / "before.tsv"
    cch.write_ratio_tsv([str(f)], str(before), root=str(tmp_path))
    _write(f, "x = 1\ny = 2\n")
    md = cch.markdown_ratio_table([str(f)], str(before), root=str(tmp_path))
    assert "m.py" in md
    assert "|" in md


# ---------------------------------------------------------------------------
# check: end-to-end over a throwaway git repository with a planted ID
# ---------------------------------------------------------------------------

def test_check_flags_planted_id_in_temp_git_repo(scratch_repo):
    _write(scratch_repo / "clean.py", "x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=scratch_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=scratch_repo, check=True)
    result = subprocess.run(
        [sys.executable, TOOL_PATH, "check", "--paths", "clean.py"],
        cwd=scratch_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    _write(scratch_repo / "clean.py", "x = 1  # see D-06\n")
    result = subprocess.run(
        [sys.executable, TOOL_PATH, "check", "--paths", "clean.py"],
        cwd=scratch_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "clean.py" in result.stdout


def test_check_paths_flag_ignores_pending_list(scratch_repo):
    _write(scratch_repo / "pending.py", "x = 1  # see D-06\n")
    (scratch_repo / "scripts").mkdir()
    _write(scratch_repo / "scripts" / "comment-history-pending.txt", "pending.py\n")
    subprocess.run(["git", "add", "-A"], cwd=scratch_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=scratch_repo, check=True)
    result = subprocess.run(
        [sys.executable, TOOL_PATH, "check", "--paths", "pending.py"],
        cwd=scratch_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "explicit --paths must ignore the pending list"


def test_tool_own_comments_pass_check():
    result = subprocess.run(
        [sys.executable, TOOL_PATH, "check", "--paths", "scripts/check_comment_history.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_test_file_itself_passes_check():
    result = subprocess.run(
        [sys.executable, TOOL_PATH, "check", "--paths", "test-support/test_check_comment_history.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_stdlib_only_imports():
    import ast as _ast

    with open(TOOL_PATH) as fh:
        tree = _ast.parse(fh.read())
    third_party = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            names = [n.name.split(".")[0] for n in node.names]
        elif isinstance(node, _ast.ImportFrom) and node.level == 0:
            names = [node.module.split(".")[0]] if node.module else []
        else:
            continue
        for name in names:
            if name in sys.builtin_module_names:
                continue
            spec = importlib.util.find_spec(name)
            if spec is None or spec.origin is None:
                continue
            if "site-packages" in spec.origin or "dist-packages" in spec.origin:
                third_party.append(name)
    assert third_party == [], "non-stdlib imports found: %r" % third_party
