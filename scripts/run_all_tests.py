#!/usr/bin/env python3
"""SkyPane — the single entry point for the whole test suite (orchestration
half; scripts/run-all-tests.sh is the thin invocation wrapper CI and README
both call).

Runs all 18 harnesses under coverage, aggregates the result, and enforces
the coverage threshold configured in pyproject.toml. Plan 04-04's CI
workflow calls run-all-tests.sh rather than restating the file list, and
plan 04-05's README tells contributors to run the same thing — one list,
one place, no drift between local and CI.

This module used to be a bash loop. The concurrency, per-harness timeout
and reporting logic outgrew what bash could do cleanly, so the
orchestration moved here; run-all-tests.sh still owns the PYTHON-interpreter
contract and execs straight into this file.

Deliberately does NOT abort on the first failing harness: a contributor
fixing a broken change wants the full picture in one run, not a report that
stops at the first failure. Every harness always runs to completion (or
its timeout).

Usage:
    scripts/run-all-tests.sh
    PYTHON=/some/other/python3 scripts/run-all-tests.sh
    JOBS=1 scripts/run-all-tests.sh              # old serial behaviour
    HARNESS_TIMEOUT_S=120 scripts/run-all-tests.sh

All configuration is env vars — no argument parsing:
    PYTHON              interpreter used to invoke this file (set by the
                         .sh wrapper's PYTHON contract, not read here)
    JOBS                worker count (default: os.cpu_count())
    HARNESS_TIMEOUT_S    per-harness wall-clock cap in seconds (default: 600)
    COVERAGE_CORE        forwarded to each child if already set; otherwise
                          this script sets it to "sysmon" on Python 3.12+
"""
import concurrent.futures
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

# Canonical 18-file enumeration (M1, measured live during 04-02 planning;
# phase 6 added 6 harnesses — see 06-11-PLAN.md Task 3; 06.6.2-01 added
# companion/test_contrast_check.py; phase 13 plan 01 added
# server/test_manual_resolutions.py; phase 14 plan 01 added
# server/test_colour_rules.py). 04-CONTEXT.md's D-07 list is 7 files
# and is known-stale — do NOT "correct" this list back down to match it.
# This list is the single source of truth CI (04-04) and README.md
# (04-05) both defer to.
HARNESSES = [
    "server/test_config_history.py",
    "server/test_colour_rules.py",
    "server/test_dither.py",
    "server/test_enrich.py",
    "server/test_illustrations.py",
    "server/test_manual_resolutions.py",
    "server/test_panel_preview.py",
    "server/test_pipeline_e2e.py",
    "server/test_plane_detection.py",
    "server/test_poll_loop.py",
    "server/test_render.py",
    "server/test_runway_config.py",
    "stub-server/test_poll_cycle.py",
    "companion/test_companion_app.py",
    "companion/test_config_page.py",
    "companion/test_contrast_check.py",
    "companion/test_status_pages.py",
    "companion/test_view_pages.py",
]

# Submission order only (readability of HARNESSES above stays untouched) —
# longest-first so the critical path is in flight from the first moment,
# not queued behind several short harnesses on a small worker pool. Timings
# measured locally (M-series Mac, python3.11, sequential, under coverage):
# test_render 59.4s, test_poll_loop 22.8s, companion_app 8.9s,
# poll_cycle 3.8s, panel_preview 3.5s, status_pages 2.6s, pipeline_e2e 2.3s;
# everything else under 1s each and left in HARNESSES' own list order.
EXPECTED_SLOWEST = (
    "server/test_render.py",
    "server/test_poll_loop.py",
    "companion/test_companion_app.py",
    "stub-server/test_poll_cycle.py",
    "server/test_panel_preview.py",
    "companion/test_status_pages.py",
    "server/test_pipeline_e2e.py",
)


def _submission_order():
    ordered = [h for h in EXPECTED_SLOWEST if h in HARNESSES]
    ordered += [h for h in HARNESSES if h not in EXPECTED_SLOWEST]
    return ordered


def _run_one(python, harness, out_dir, timeout_s, env):
    out_path = os.path.join(out_dir, harness.replace("/", "__") + ".log")
    start = time.perf_counter()
    with open(out_path, "wb") as out_f:
        # A real file, not a pipe: a pipe can deadlock a chatty harness
        # against a full OS pipe buffer once output exceeds the kernel's
        # default size, which several of these harnesses' verbose PASS
        # logging can do.
        proc = subprocess.Popen(
            [python, "-m", "coverage", "run", harness],
            cwd=REPO_ROOT,
            stdout=out_f,
            stderr=subprocess.STDOUT,
            env=env,
            # Own session/process group, so a timeout can take down the
            # harness AND the child servers several harnesses spawn
            # (companion/app.py, stub-server/byos_server.py) - killing only
            # the harness would orphan those, still bound to their ports.
            start_new_session=True,
        )
        try:
            code = proc.wait(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            proc.wait()
            code = proc.returncode
            timed_out = True
    wall = time.perf_counter() - start
    with open(out_path, "rb") as f:
        output = f.read().decode(errors="replace")
    return {
        "harness": harness,
        "wall": wall,
        "code": code,
        "timed_out": timed_out,
        "output": output,
    }


def _last_nonempty_line(text):
    for line in reversed(text.splitlines()):
        if line.strip():
            return line
    return ""


def main():
    python = sys.executable
    workers = int(os.environ.get("JOBS") or os.cpu_count() or 1)
    timeout_s = float(os.environ.get("HARNESS_TIMEOUT_S", "600"))

    print("==> Clearing stale coverage data files from any previous run")
    for name in os.listdir(REPO_ROOT):
        if name == ".coverage" or name.startswith(".coverage."):
            try:
                os.remove(os.path.join(REPO_ROOT, name))
            except OSError:
                pass

    # coverage.py reads [tool.coverage.run] from pyproject.toml, including
    # `parallel = true` — each process below writes its own .coverage.*
    # data file. Do NOT also pass --append here: coverage.py rejects the
    # combination outright ("Can't append to data files in parallel mode"),
    # and parallel mode is precisely what makes running these 18 processes
    # concurrently safe in the first place.
    env = dict(os.environ)
    if sys.version_info >= (3, 12) and "COVERAGE_CORE" not in os.environ:
        # Measured this session: test_render 60.3s (default core) -> 36.5s
        # (sysmon), test_poll_loop 16.0s -> 10.9s — the tracing overhead
        # essentially vanishes on 3.12+'s sysmon core. Left alone on older
        # interpreters where sysmon doesn't exist, and an explicit
        # COVERAGE_CORE from the caller always wins over this default.
        env["COVERAGE_CORE"] = "sysmon"

    out_dir = tempfile.mkdtemp(prefix="skypane-tests-")
    print_lock = threading.Lock()
    results = {}
    overall_start = time.perf_counter()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            # Threads, not processes: each worker just blocks on a child
            # process's exit, so there's no CPU-bound work in Python itself
            # to parallelise past the GIL.
            futures = {
                pool.submit(_run_one, python, h, out_dir, timeout_s, env): h
                for h in _submission_order()
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results[result["harness"]] = result
                with print_lock:
                    if result["timed_out"]:
                        print(
                            "==> FAIL  %s  (%.1fs, timed out after %gs)"
                            % (result["harness"], result["wall"], timeout_s)
                        )
                        print(result["output"])
                    elif result["code"] != 0:
                        print(
                            "==> FAIL  %s  (%.1fs, exit %s)"
                            % (result["harness"], result["wall"], result["code"])
                        )
                        print(result["output"])
                    else:
                        print(
                            "==> PASS  %s  (%.1fs)"
                            % (result["harness"], result["wall"])
                        )
                        print(_last_nonempty_line(result["output"]))
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    total_wall = time.perf_counter() - overall_start

    print("==> Combining parallel coverage data files")
    subprocess.run([python, "-m", "coverage", "combine"], cwd=REPO_ROOT, env=env)

    print("==> Coverage report (threshold enforced from pyproject.toml, not restated here)")
    coverage_status = subprocess.run(
        [python, "-m", "coverage", "report"], cwd=REPO_ROOT, env=env
    ).returncode

    print("==> Clearing coverage data files (report already produced)")
    for name in os.listdir(REPO_ROOT):
        if name == ".coverage" or name.startswith(".coverage."):
            try:
                os.remove(os.path.join(REPO_ROOT, name))
            except OSError:
                pass

    failed = [
        h for h in HARNESSES if results[h]["code"] != 0 or results[h]["timed_out"]
    ]

    # Slowest-first timing table — how to spot slow-test creep.
    ordered = sorted(HARNESSES, key=lambda h: results[h]["wall"], reverse=True)

    print("==> Timing (slowest first)")
    for h in ordered:
        r = results[h]
        status = "TIMEOUT" if r["timed_out"] else ("PASS" if r["code"] == 0 else "FAIL")
        print("    %-45s %7.1fs  %s" % (h, r["wall"], status))
    print("==> Total wall time: %.1fs (JOBS=%d)" % (total_wall, workers))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("\n## Test suite timing (slowest first)\n\n")
            f.write("| Harness | Wall (s) | Status |\n")
            f.write("| --- | --- | --- |\n")
            for h in ordered:
                r = results[h]
                status = (
                    "TIMEOUT" if r["timed_out"] else ("PASS" if r["code"] == 0 else "FAIL")
                )
                f.write("| %s | %.1f | %s |\n" % (h, r["wall"], status))
            f.write("\nTotal wall time: %.1fs (JOBS=%d)\n" % (total_wall, workers))

    if failed:
        print("==> FAILED harnesses (%d):" % len(failed))
        for f in failed:
            reason = "timed out after %gs" % timeout_s if results[f]["timed_out"] else "exit %s" % results[f]["code"]
            print("    - %s (%s)" % (f, reason))

    if failed or coverage_status != 0:
        print("==> Result: FAIL")
        return 1

    print("==> Result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
