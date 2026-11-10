"""Behaviour of scripts/ci_shards.py: groups and shards cover every file once."""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ci_shards.py"
_SPEC = importlib.util.spec_from_file_location("ci_shards", _SCRIPT)
shards_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(shards_mod)

PATHS = [
    "companion/test_browser_big.py",
    "companion/test_browser_small.py",
    "companion/test_mixed.py",
    "companion/test_plain.py",
    "server/test_a.py",
    "server/test_b.py",
    "server/test_c.py",
]
SOURCES = {
    "companion/test_browser_big.py": "def test_x(): pass\n" * 30,
    "companion/test_browser_small.py": "def test_x(): pass\n",
    "companion/test_mixed.py": "@pytest.mark.browser\ndef test_x(): pass\n",
    "companion/test_plain.py": "def test_x(): pass\n" * 5,
    "server/test_a.py": "def test_x(): pass\n" * 9,
    "server/test_b.py": "def test_x(): pass\n" * 8,
    "server/test_c.py": "def test_x(): pass\n",
}


def _build(browser, core, weights=None):
    return shards_mod.build_shards(PATHS, SOURCES, weights or {},
                                   {"browser": browser, "core": core})


@pytest.mark.parametrize("browser", [1, 2, 3, 6])
@pytest.mark.parametrize("core", [1, 2, 5])
def test_every_file_is_in_exactly_one_shard(browser, core):
    shards = _build(browser, core)
    assert shards_mod.completeness_problems(PATHS, shards) == []
    assert shards_mod.marker_problems(shards, SOURCES) == []


def test_a_file_using_the_browser_marker_goes_to_the_browser_group():
    shards = _build(1, 1)
    assert "companion/test_mixed.py" in shards["browser"][0]
    assert "companion/test_plain.py" in shards["core"][0]


def test_one_shard_returns_the_whole_group():
    shards = _build(1, 1)
    assert shards["browser"][0] == sorted(
        ["companion/test_browser_big.py", "companion/test_browser_small.py",
         "companion/test_mixed.py"])


def test_heavy_files_land_in_different_shards_and_the_result_is_stable():
    first = _build(2, 2, {"server/test_a.py": 100, "server/test_b.py": 90})
    again = _build(2, 2, {"server/test_a.py": 100, "server/test_b.py": 90})
    assert first == again
    where = {p: i for i, shard in enumerate(first["core"]) for p in shard}
    assert where["server/test_a.py"] != where["server/test_b.py"]


def test_the_check_reports_a_file_missing_from_every_shard():
    shards = _build(2, 2)
    shards["core"][0] = [p for p in shards["core"][0] if p != "server/test_a.py"]
    shards["core"][1] = [p for p in shards["core"][1] if p != "server/test_a.py"]
    assert shards_mod.completeness_problems(PATHS, shards) == [
        "server/test_a.py: in no shard"]


def test_the_check_reports_a_file_in_two_shards():
    shards = _build(2, 2)
    holder = next(i for i, shard in enumerate(shards["core"])
                  if "server/test_c.py" in shard)
    shards["core"][1 - holder].append("server/test_c.py")
    problems = shards_mod.completeness_problems(PATHS, shards)
    assert len(problems) == 1
    assert problems[0].startswith("server/test_c.py: in 2 shards")


def test_the_check_reports_a_browser_marker_file_in_the_core_group():
    shards = _build(1, 1)
    shards["core"][0].append("companion/test_mixed.py")
    assert shards_mod.marker_problems(shards, SOURCES) == [
        "companion/test_mixed.py: uses the browser marker but is in the core group"]


def test_the_real_tree_is_covered_exactly_once_for_several_shard_counts():
    for browser, core in ((1, 1), (3, 2), (4, 2), (6, 5)):
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), "check",
             "--browser-shards", str(browser), "--core-shards", str(core)],
            capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_the_real_browser_group_includes_the_heaviest_browser_files():
    out = subprocess.run(
        [sys.executable, str(_SCRIPT), "files", "browser", "0", "1"],
        capture_output=True, text=True, check=True).stdout.split()
    assert "companion/test_browser_overhaul_sweep.py" in out
    assert "companion/test_browser_components_page.py" in out
    assert "companion/test_static_cache.py" in out


def test_an_unknown_group_or_out_of_range_index_fails():
    for argv in (["files", "bogus", "0", "1"], ["files", "core", "2", "2"],
                 ["files", "core", "0", "0"]):
        result = subprocess.run([sys.executable, str(_SCRIPT), *argv],
                                capture_output=True, text=True)
        assert result.returncode != 0


def test_junit_times_are_summed_per_test_file(tmp_path):
    junit = tmp_path / "j.xml"
    junit.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="server.test_a" name="t1" time="2.4"/>'
        '<testcase classname="server.test_a.TestK" name="t2" time="1.2"/>'
        '<testcase classname="companion.test_plain" name="t3" time="0.1"/>'
        '<testcase classname="gone.test_missing" name="t4" time="9"/>'
        "</testsuite></testsuites>", encoding="utf-8")
    weights = shards_mod.weights_from_junit(
        [str(junit)], {"server/test_a.py", "companion/test_plain.py"})
    assert weights == {"companion/test_plain.py": 1, "server/test_a.py": 4}


def test_a_weight_for_a_file_that_no_longer_exists_is_ignored():
    shards = shards_mod.build_shards(
        PATHS, SOURCES, {"server/test_deleted.py": 999}, {"browser": 2, "core": 2})
    assert shards_mod.completeness_problems(PATHS, shards) == []
