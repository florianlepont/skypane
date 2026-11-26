#!/usr/bin/env python3
"""GitHub paths-filter matcher for .github/workflows/ci.yml. Stdlib only.

Reads the `paths:` list of the workflow's `push` and `pull_request` events
(a line scan, no YAML parser) and answers whether a set of changed files
starts a CI run. Pattern semantics follow GitHub: `*` stays inside one path
segment, `**` crosses segments (`**/` also matches no directory), `?` is one
non-slash character, a leading `!` excludes, patterns apply in order and the
last matching pattern decides a file. A change set runs CI when at least one
file ends up included.

Subcommands:
  decide [--workflow PATH] FILE...
      Prints `run` (exit 0) or `skip` (exit 1); exit 2 when the workflow
      cannot be read or its push and pull_request lists differ.
  measure --last N [--ref REV] [--workflow PATH] [--cwd DIR]
      For the last N first-parent commits of REV, prints whether CI would
      run, then totals. A merge commit counts as its first-parent diff.
"""
import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
EVENTS = ("push", "pull_request")


class WorkflowError(Exception):
    """The workflow has no readable paths list for an event, or the lists differ."""


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _event_block(lines, event):
    """Lines of the `on:` child named `event`, or None when absent."""
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == f"  {event}:" or line.startswith(f"  {event}: "):
            start = i
            break
    if start is None:
        return None
    block = []
    for line in lines[start + 1:]:
        if line.strip() and not line.lstrip().startswith("#") and _indent(line) <= 2:
            break
        block.append(line)
    return block


def workflow_paths(text, event):
    """Ordered `paths:` patterns of one event of the workflow text."""
    block = _event_block(text.splitlines(), event)
    if block is None:
        raise WorkflowError(f"no `{event}` event in the workflow")
    patterns = []
    in_paths = False
    for line in block:
        stripped = line.strip()
        if stripped == "paths:":
            in_paths = True
            continue
        if not in_paths or not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("- "):
            break
        patterns.append(stripped[2:].strip().strip("'\""))
    if not patterns:
        raise WorkflowError(f"no `paths:` list under `{event}`")
    return patterns


def compile_pattern(pattern):
    """Anchored regex for one path pattern (without a leading `!`)."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _included(path, compiled):
    """Last matching pattern decides; no match means not included."""
    verdict = False
    for negated, regex in compiled:
        if regex.match(path):
            verdict = not negated
    return verdict


def runs(files, patterns):
    """True when at least one file ends up included by the ordered patterns."""
    compiled = [(p.startswith("!"), compile_pattern(p.lstrip("!"))) for p in patterns]
    return any(_included(path, compiled) for path in files)


def load_patterns(workflow_path):
    """The shared push/pull_request list; raises when missing or different."""
    with open(workflow_path, encoding="utf-8") as handle:
        text = handle.read()
    lists = [workflow_paths(text, event) for event in EVENTS]
    if lists[0] != lists[1]:
        raise WorkflowError("push and pull_request paths lists differ")
    return lists[0]


def _git(cwd, *argv):
    return subprocess.run(["git", "-c", "core.quotepath=off", *argv], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout


def _changed_files(cwd, sha):
    parent = f"{sha}^"
    has_parent = subprocess.run(["git", "rev-parse", "--verify", "--quiet", parent],
                                cwd=cwd, capture_output=True).returncode == 0
    base = parent if has_parent else EMPTY_TREE
    return _git(cwd, "diff", "--name-only", base, sha).splitlines()


def measure(patterns, last, ref, cwd, out=None):
    """Prints one line per commit and a totals line; returns (total, run)."""
    out = out or sys.stdout
    shas = _git(cwd, "log", "--first-parent", "--format=%H", "-n", str(last),
                ref).split()
    would_run = 0
    for sha in shas:
        files = _changed_files(cwd, sha)
        verdict = runs(files, patterns)
        would_run += verdict
        print(f"{sha[:8]} {'run' if verdict else 'skip'} {len(files)}", file=out)
    total = len(shas)
    skipped = total - would_run
    share = 100.0 * skipped / total if total else 0.0
    print(f"commits {total}, would run {would_run}, would skip {skipped}, "
          f"skip {share:.1f}%", file=out)
    return total, would_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    decide = sub.add_parser("decide")
    decide.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    decide.add_argument("files", nargs="+")
    meas = sub.add_parser("measure")
    meas.add_argument("--last", type=int, required=True)
    meas.add_argument("--ref", default="HEAD")
    meas.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    meas.add_argument("--cwd", default=REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        patterns = load_patterns(args.workflow)
    except (OSError, WorkflowError) as exc:
        print(f"cannot read the paths filter: {exc}", file=sys.stderr)
        return 2
    if args.command == "decide":
        verdict = runs(args.files, patterns)
        print("run" if verdict else "skip")
        return 0 if verdict else 1
    measure(patterns, args.last, args.ref, args.cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
