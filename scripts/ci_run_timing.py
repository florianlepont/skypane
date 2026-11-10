#!/usr/bin/env python3
"""Prints job and step durations of GitHub Actions runs. Stdlib only.

Data comes from the REST API through `gh api` (the GraphQL endpoint that
`gh run view` uses is not reachable from every environment).

Subcommands:
  jobs    RUN_ID...  markdown table of every job and step, plus the run's
                     critical path (earliest job start to latest job end)
  median  RUN_ID...  median wall time, in minutes, of the test check over
                     the given runs
"""
import argparse
import datetime
import json
import os
import re
import statistics
import subprocess
import sys

CHECK_NAME = "Lint, test, coverage, attribution"


def fetch_jobs(run_id, repo):
    """Returns the list of job objects of one run (REST, paginated)."""
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/jobs",
         "--paginate", "--jq", ".jobs[]"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def current_repo():
    """owner/name from GITHUB_REPOSITORY, else from the origin remote."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    url = subprocess.run(["git", "remote", "get-url", "origin"], check=True,
                         capture_output=True, text=True).stdout.strip()
    match = re.search(r"([^/:]+/[^/]+?)(?:\.git)?$", url)
    if not match:
        raise SystemExit(f"cannot derive owner/name from {url!r}; use --repo")
    return match.group(1)


def parse_time(text):
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def seconds_between(start, end):
    if not start or not end:
        return None
    return (parse_time(end) - parse_time(start)).total_seconds()


def critical_path_seconds(jobs):
    """Earliest job start to latest job end across the jobs that ran."""
    ran = [j for j in jobs if j.get("started_at") and j.get("completed_at")
           and j.get("conclusion") != "skipped"]
    if not ran:
        return 0.0
    first = min(parse_time(j["started_at"]) for j in ran)
    last = max(parse_time(j["completed_at"]) for j in ran)
    return (last - first).total_seconds()


def check_seconds(jobs):
    """Wall time of the test check.

    With one job that is the job's own duration; with several it is the
    critical path of every job of the run except the production deploy.
    """
    tests = [j for j in jobs if j.get("name") != "Deploy to production"]
    if len(tests) == 1:
        return seconds_between(tests[0].get("started_at"),
                               tests[0].get("completed_at")) or 0.0
    return critical_path_seconds(tests)


def format_seconds(value):
    return "-" if value is None else f"{value:.0f}"


def jobs_table(run_id, jobs):
    lines = [f"### Run {run_id}", "",
             "| Job | Conclusion | Wall s |", "|---|---|---|"]
    for job in jobs:
        wall = seconds_between(job.get("started_at"), job.get("completed_at"))
        lines.append(f"| {job['name']} | {job.get('conclusion')} "
                     f"| {format_seconds(wall)} |")
    lines += ["", "| Job | Step | Wall s |", "|---|---|---|"]
    for job in jobs:
        for step in job.get("steps", []):
            wall = seconds_between(step.get("started_at"),
                                   step.get("completed_at"))
            lines.append(f"| {job['name']} | {step['name']} "
                         f"| {format_seconds(wall)} |")
    path = critical_path_seconds(jobs)
    lines += ["", f"Critical path: {path:.0f} s ({path / 60:.1f} min)", ""]
    return "\n".join(lines)


def median_minutes(per_run_seconds):
    return statistics.median(per_run_seconds) / 60.0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("jobs", "median"))
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)
    repo = args.repo or current_repo()
    runs = {run_id: fetch_jobs(run_id, repo) for run_id in args.run_ids}
    if args.command == "jobs":
        print("\n".join(jobs_table(run_id, jobs)
                        for run_id, jobs in runs.items()))
        return 0
    seconds = [check_seconds(jobs) for jobs in runs.values()]
    print(f"{median_minutes(seconds):.1f} min over {len(seconds)} run(s): "
          + ", ".join(f"{s / 60:.1f}" for s in seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
