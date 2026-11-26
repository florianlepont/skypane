"""Behaviour of scripts/ci_gates.py on constructed JUnit files."""
import importlib.util
import pathlib

_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ci_gates.py"
_SPEC = importlib.util.spec_from_file_location("ci_gates", _PATH)
gates = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gates)


def _report(tmp_path, name, tests, failures=0, errors=0, skipped=0, wrapped=True):
    suite = (f'<testsuite name="pytest" tests="{tests}" failures="{failures}" '
             f'errors="{errors}" skipped="{skipped}"></testsuite>')
    body = f"<testsuites>{suite}</testsuites>" if wrapped else suite
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def _run(*argv):
    return gates.main(list(argv))


def test_a_baseline_sized_report_passes(tmp_path, capsys):
    path = _report(tmp_path, "a.xml", 12821)
    assert _run("totals", path) == 0
    assert "12821 executed" in capsys.readouterr().out


def test_several_files_are_summed(tmp_path):
    first = _report(tmp_path, "a.xml", 10000)
    second = _report(tmp_path, "b.xml", 2821, wrapped=False)
    assert _run("totals", first, second) == 0
    assert _run("totals", first) == 1


def test_a_failure_or_an_error_fails_the_gate(tmp_path):
    assert _run("totals", "--min-executed", "1",
                _report(tmp_path, "f.xml", 10, failures=1)) == 1
    assert _run("totals", "--min-executed", "1",
                _report(tmp_path, "e.xml", 10, errors=1)) == 1


def test_fewer_executed_tests_than_the_floor_fails(tmp_path):
    path = _report(tmp_path, "a.xml", 100, skipped=10)
    assert _run("totals", "--min-executed", "91", "--max-skipped", "10", path) == 1
    assert _run("totals", "--min-executed", "90", "--max-skipped", "10", path) == 0


def test_skipped_tests_above_the_ceiling_fail(tmp_path):
    path = _report(tmp_path, "a.xml", 100, skipped=1)
    assert _run("totals", "--min-executed", "1", "--max-skipped", "0", path) == 1


def test_a_missing_file_a_malformed_file_and_no_file_are_errors(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("not xml", encoding="utf-8")
    empty = tmp_path / "empty.xml"
    empty.write_text("<testsuites/>", encoding="utf-8")
    assert _run("totals", str(tmp_path / "missing.xml")) == 2
    assert _run("totals", str(bad)) == 2
    assert _run("totals", str(empty)) == 2
    assert _run("totals") == 2


def _shard_dir(tmp_path, count, coverage):
    for index in range(count):
        shard = tmp_path / f"test-data-core-{index}"
        shard.mkdir()
        (shard / f"junit-core-{index}.xml").write_text("<testsuite/>")
        if coverage:
            (shard / ".coverage").write_text("data")
    return str(tmp_path)


def test_artifacts_with_coverage_needs_one_of_each_per_shard(tmp_path, capsys):
    directory = _shard_dir(tmp_path, 3, coverage=True)
    assert _run("artifacts", "--expected", "3", "--with-coverage", directory) == 0
    assert "found 3 coverage files and 3 JUnit files" in capsys.readouterr().out
    assert _run("artifacts", "--expected", "4", "--with-coverage", directory) == 1


def test_artifacts_with_coverage_fails_when_a_coverage_file_is_missing(tmp_path):
    directory = _shard_dir(tmp_path, 3, coverage=True)
    (tmp_path / "test-data-core-1" / ".coverage").unlink()
    assert _run("artifacts", "--expected", "3", "--with-coverage", directory) == 1


def test_artifacts_with_coverage_fails_when_a_junit_file_is_missing(tmp_path):
    directory = _shard_dir(tmp_path, 3, coverage=True)
    (tmp_path / "test-data-core-2" / "junit-core-2.xml").unlink()
    assert _run("artifacts", "--expected", "3", "--with-coverage", directory) == 1


def test_artifacts_without_coverage_says_so_and_passes(tmp_path, capsys):
    directory = _shard_dir(tmp_path, 3, coverage=False)
    assert _run("artifacts", "--expected", "3", "--without-coverage", directory) == 0
    out = capsys.readouterr().out
    assert "coverage: not measured on pull requests; measured on main" in out


def test_artifacts_without_coverage_still_counts_junit_files(tmp_path):
    directory = _shard_dir(tmp_path, 3, coverage=False)
    assert _run("artifacts", "--expected", "4", "--without-coverage", directory) == 1


def test_artifacts_without_coverage_refuses_unexpected_coverage_files(tmp_path, capsys):
    directory = _shard_dir(tmp_path, 3, coverage=True)
    assert _run("artifacts", "--expected", "3", "--without-coverage", directory) == 1
    assert "not measured" not in capsys.readouterr().out


def test_artifacts_requires_a_coverage_mode(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        _run("artifacts", "--expected", "1", str(tmp_path))
