"""Behaviour of scripts/ci_run_timing.py on recorded job data (no network)."""
import importlib.util
import pathlib

_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ci_run_timing.py"
_SPEC = importlib.util.spec_from_file_location("ci_run_timing", _PATH)
timing = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(timing)


def _job(name, start, end, conclusion="success", steps=()):
    return {"name": name, "conclusion": conclusion, "started_at": start,
            "completed_at": end, "steps": list(steps)}


def test_a_single_job_run_reports_that_jobs_own_duration():
    jobs = [_job("Lint, test, coverage, attribution",
                 "2026-11-10T06:44:52Z", "2026-11-10T07:12:19Z"),
            _job("Deploy to production", "2026-11-10T07:12:19Z",
                 "2026-11-10T07:12:19Z", "skipped")]
    assert timing.check_seconds(jobs) == 27 * 60 + 27


def test_parallel_jobs_report_the_critical_path_not_the_sum():
    jobs = [_job("static", "2026-11-10T10:00:00Z", "2026-11-10T10:02:00Z"),
            _job("browser 1", "2026-11-10T10:00:05Z", "2026-11-10T10:08:00Z"),
            _job("browser 2", "2026-11-10T10:00:07Z", "2026-11-10T10:07:00Z"),
            _job("Lint, test, coverage, attribution",
                 "2026-11-10T10:08:01Z", "2026-11-10T10:08:30Z"),
            _job("Deploy to production", "2026-11-10T10:08:31Z",
                 "2026-11-10T10:08:31Z", "skipped")]
    assert timing.check_seconds(jobs) == 8 * 60 + 30


def test_median_of_an_odd_and_an_even_number_of_runs():
    assert timing.median_minutes([600, 1200, 900]) == 15.0
    assert timing.median_minutes([600, 1200]) == 15.0


def test_the_jobs_table_lists_every_job_and_step_with_the_critical_path():
    steps = [{"name": "Run tests", "started_at": "2026-11-10T06:45:46Z",
              "completed_at": "2026-11-10T07:12:14Z"}]
    jobs = [_job("Lint, test, coverage, attribution", "2026-11-10T06:44:52Z",
                 "2026-11-10T07:12:19Z", steps=steps)]
    table = timing.jobs_table(42770577886, jobs)
    assert "### Run 42770577886" in table
    assert "| Lint, test, coverage, attribution | success | 1647 |" in table
    assert "| Lint, test, coverage, attribution | Run tests | 1588 |" in table
    assert "Critical path: 1647 s (27.4 min)" in table


def test_skipped_jobs_do_not_stretch_the_critical_path():
    jobs = [_job("a", "2026-11-10T10:00:00Z", "2026-11-10T10:01:00Z"),
            _job("deploy", "2026-11-10T11:00:00Z", "2026-11-10T11:00:00Z",
                 "skipped")]
    assert timing.critical_path_seconds(jobs) == 60
