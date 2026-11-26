"""deploy/tests/test_ci_runner.py -- the CI workflows are runner-agnostic.

Text scan, no YAML parser (same discipline as test_ci_secrets.py): jobs pick
their runner from the repository variable CI_RUNS_ON with a GitHub-hosted
default, steps needing sudo or apt run only on hosted runners, a fork pull
request never reaches a self-hosted runner, and nothing that makes the suite
run less than whole was added.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"
_CI = (_WORKFLOWS / "ci.yml").read_text()
_FIRMWARE = (_WORKFLOWS / "firmware.yml").read_text()

_RUNS_ON = "runs-on: ${{ fromJSON(vars.CI_RUNS_ON || '\"ubuntu-latest\"') }}"
_HOSTED = "if: runner.environment == 'github-hosted'"
_SELF_HOSTED = "if: runner.environment == 'self-hosted'"


def _steps(text):
    """Split a workflow into step blocks (text from one `- name:` to the next)."""
    parts = re.split(r"(?m)^(?=      - name: )", text)
    return [p for p in parts if p.startswith("      - name: ")]


def _step_named(text, name):
    for step in _steps(text):
        if step.startswith(f"      - name: {name}\n"):
            return step
    raise AssertionError(f"no step named {name!r}")


def test_every_ci_and_firmware_job_reads_runner_from_variable():
    assert _CI.count(_RUNS_ON) == 4
    assert _FIRMWARE.count(_RUNS_ON) == 3
    assert "runs-on: ubuntu-latest" not in _CI
    assert "runs-on: ubuntu-latest" not in _FIRMWARE


def test_workflows_that_must_work_with_the_mac_off_stay_hosted():
    for name in ("firmware-chain-check.yml", "firmware-release.yml", "deploy.yml"):
        text = (_WORKFLOWS / name).read_text()
        assert "runs-on: ubuntu-latest" in text, name
        assert "CI_RUNS_ON" not in text, name


def test_no_workflow_uses_pull_request_target():
    for path in _WORKFLOWS.glob("*.yml"):
        assert "pull_request_target" not in path.read_text(), path.name


def test_sudo_and_apt_steps_run_on_hosted_runners_only():
    for step in _steps(_CI):
        if re.search(r"\bsudo\b|--with-deps", step):
            assert _HOSTED in step, step.splitlines()[0]


def test_setup_python_is_hosted_only_and_followed_by_a_distro_check():
    assert _CI.count("actions/setup-python") == 4
    assert _CI.count("Use the distro Python 3.14 (self-hosted)") == 4
    lines = _CI.splitlines()
    for i, line in enumerate(lines):
        if "actions/setup-python" in line:
            assert _HOSTED in "\n".join(lines[i + 1 : i + 3])
    for step in _steps(_CI):
        if step.startswith("      - name: Use the distro Python 3.14 (self-hosted)"):
            assert _SELF_HOSTED in step
            assert "python3.14 --version" in step
            assert "GITHUB_PATH" in step


def test_browser_job_installs_chromium_without_apt_on_self_hosted():
    step = _step_named(_CI, "Install the Chromium headless shell (self-hosted)")
    assert _SELF_HOSTED in step
    assert "playwright install --only-shell chromium" in step
    assert "--with-deps" not in step


def test_pull_requests_from_forks_never_reach_the_runner():
    guard = (
        "if: github.event_name != 'pull_request' || "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    for job in ("static", "tests-core", "tests-browser"):
        block = re.search(rf"(?ms)^  {job}:\n(.*?)^    steps:", _CI).group(1)
        assert guard in block, job


def test_no_job_is_conditional_on_paths_and_no_gate_is_weakened():
    assert "ci_shards.py check" in _CI
    assert "ci_gates.py" in _CI
    assert "Combine coverage and apply the coverage floor" in _CI
    assert "--with-coverage" in _CI
    assert "Check test totals (no failures, executed floor, skipped ceiling)" in _CI
    assert "- '!**/*.md'" in _CI
    assert "- '!.planning/**'" in _CI
    assert not re.search(r"(?m)^  changes:", _CI)
    assert "needs.changes" not in _CI
    assert "dorny/paths-filter" not in _CI
    test_job = re.search(r"(?ms)^  test:\n(.*?)^    steps:", _CI).group(1)
    assert "if: ${{ always() }}" in test_job
    assert "needs: [static, tests-core, tests-browser]" in test_job
    job_level_ifs = re.findall(r"(?m)^    if: .*$", _CI)
    guard = (
        "    if: github.event_name != 'pull_request' || "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    assert sorted(job_level_ifs) == sorted([guard] * 3 + ["    if: ${{ always() }}"])


_NOT_PR = "if: github.event_name != 'pull_request'"
_ONLY_PR = "if: github.event_name == 'pull_request'"
_MAIN_UPLOAD = "Upload coverage data and JUnit report"
_PR_UPLOAD = "Upload JUnit report (pull request, coverage not measured)"
_TOTALS = "Check test totals (no failures, executed floor, skipped ceiling)"
_COUNT_MAIN = "Require one coverage file and one JUnit file per shard"
_COUNT_PR = "Require one JUnit file per shard (pull request, coverage not measured)"
_FLOOR = "Combine coverage and apply the coverage floor"


def _test_job_steps():
    block = re.search(r"(?ms)^  test:\n.*", _CI).group(0)
    return _steps(block)


def test_coverage_is_measured_on_main_and_dispatch_not_on_pull_requests():
    # Shards: the coverage switch is derived from the event, and only the
    # pull_request event turns it off.
    expected = (
        "SKYPANE_COVERAGE: ${{ github.event_name == 'pull_request' "
        "&& 'off' || 'on' }}"
    )
    for name in ("Run the non-browser test files", "Run the browser test files"):
        step = _step_named(_CI, name)
        assert expected in step, name
        assert "\n        if:" not in step, name
    assert _CI.count("SKYPANE_COVERAGE:") == 2

    # Coverage steps of the aggregate run on every event but pull_request.
    for name in (_COUNT_MAIN, _FLOOR):
        assert _NOT_PR in _step_named(_CI, name), name
    assert "--with-coverage" in _step_named(_CI, _COUNT_MAIN)
    assert "coverage combine" in _step_named(_CI, _FLOOR)
    assert "coverage report" in _step_named(_CI, _FLOOR)
    assert "--fail-under=" not in _step_named(_CI, _FLOOR)

    # The pull-request replacement still counts shards and says out loud that
    # coverage was not measured.
    pr_step = _step_named(_CI, _COUNT_PR)
    assert _ONLY_PR in pr_step
    assert "--without-coverage" in pr_step
    assert "ci_gates.py artifacts --expected" in pr_step
    assert '"$GITHUB_STEP_SUMMARY"' in pr_step


def test_coverage_upload_fails_loudly_on_main_and_junit_always_uploads():
    assert _CI.count(_MAIN_UPLOAD) == 2
    assert _CI.count(_PR_UPLOAD) == 2
    for step in _steps(_CI):
        if step.startswith(f"      - name: {_MAIN_UPLOAD}\n"):
            assert "if: ${{ always() && github.event_name != 'pull_request' }}" in step
            assert "if-no-files-found: error" in step
            assert "include-hidden-files: true" in step
            assert "            .coverage\n" in step
        if step.startswith(f"      - name: {_PR_UPLOAD}\n"):
            assert "if: ${{ always() && github.event_name == 'pull_request' }}" in step
            assert "if-no-files-found: error" in step
            assert ".coverage" not in step
            assert "path: junit-" in step


def test_test_totals_gate_and_shard_check_run_on_every_event():
    for name in ("Require every job above to have succeeded", _TOTALS):
        assert "\n        if:" not in _step_named(_CI, name), name
    assert "ci_gates.py totals test-data/*/junit-*.xml" in _step_named(_CI, _TOTALS)
    # Only the coverage-data steps may be conditioned on the event.
    conditioned = [
        step.splitlines()[0]
        for step in _test_job_steps()
        if "github.event_name" in step
    ]
    assert sorted(conditioned) == sorted(
        f"      - name: {name}" for name in (_COUNT_MAIN, _COUNT_PR, _FLOOR)
    ), conditioned


def test_shard_counts_match_the_matrices_and_split_evenly_over_runners():
    def env_count(name):
        return int(re.search(rf'(?m)^  {name}: "(\d+)"$', _CI).group(1))

    def matrix_shards(job):
        block = re.search(rf"(?ms)^  {job}:\n(.*?)^    steps:", _CI).group(1)
        listed = re.search(r"shard: \[([0-9, ]+)\]", block).group(1)
        return [int(n) for n in listed.split(",")]

    for job, name in (("tests-core", "CORE_SHARDS"), ("tests-browser", "BROWSER_SHARDS")):
        assert matrix_shards(job) == list(range(env_count(name))), job
    # Two single-job runners and a four-runner host both get a whole number
    # of test jobs.
    assert (env_count("BROWSER_SHARDS") + env_count("CORE_SHARDS")) % 4 == 0
    assert "expected=$((BROWSER_SHARDS + CORE_SHARDS))" in _CI


def test_model_file_exclusions_appear_once_per_event():
    for ext in ("stl", "blend", "glb", "3mf"):
        assert _CI.count(f"- '!hardware/cad/**/*.{ext}'") == 2, ext
