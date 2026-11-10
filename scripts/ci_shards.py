#!/usr/bin/env python3
"""Splits the test files into groups and shards. Stdlib only.

A file belongs to the `browser` group when its name contains "browser" or its
source uses the `browser` pytest marker; every other test file belongs to the
`core` group. Each group is split into COUNT shards by greedy longest-first
packing on a per-file weight, so shard i of COUNT is a stable list of whole
files. Selection is always by file path: no test id is ever deselected, and a
file is never split, so module-scoped fixtures are not duplicated.

Weights come from `scripts/ci_shard_weights.json` (file path -> seconds) when
that file exists; a file without an entry weighs its number of `def test_`
occurrences.

Subcommands:
  files GROUP INDEX COUNT   print the shard's files, one per line
  check [--browser-shards N] [--core-shards M]
                            fail unless every test file is in exactly one shard
  weights JUNIT_XML...      print the summed test time per test file, as the
                            JSON map that scripts/ci_shard_weights.json holds
"""
import argparse
import fnmatch
import json
import os
import xml.etree.ElementTree as ET
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PATHS = ("server", "stub-server", "companion", "test-support", "deploy",
              "hardware")
TEST_PATTERNS = ("test_*.py", "*_test.py")
WEIGHTS_FILE = os.path.join(REPO_ROOT, "scripts", "ci_shard_weights.json")
GROUPS = ("browser", "core")


def tracked_test_files(root=REPO_ROOT):
    """Files under the test paths that pytest would collect.

    Tracked files plus untracked ones that are not ignored, so a new test file
    that is not yet committed is still selected by a local partial run.
    """
    out = subprocess.run(["git", "ls-files", "--cached", "--others",
                          "--exclude-standard", "--", *TEST_PATHS], cwd=root,
                         check=True, capture_output=True, text=True).stdout
    return sorted(
        path for path in out.splitlines()
        if any(fnmatch.fnmatch(os.path.basename(path), pattern)
               for pattern in TEST_PATTERNS))


def read_source(path, root=REPO_ROOT):
    with open(os.path.join(root, path), encoding="utf-8") as handle:
        return handle.read()


def is_browser_file(path, source):
    return "browser" in os.path.basename(path) or "mark.browser" in source


def load_weights(path=WEIGHTS_FILE):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def file_weight(path, source, weights):
    if path in weights:
        return float(weights[path])
    return float(max(1, source.count("def test_")))


def split_groups(paths, sources):
    groups = {name: [] for name in GROUPS}
    for path in paths:
        name = "browser" if is_browser_file(path, sources[path]) else "core"
        groups[name].append(path)
    return groups


def pack(paths, weight_of, count):
    """Greedy longest-first packing into `count` deterministic shards."""
    shards = [[] for _ in range(count)]
    loads = [0.0] * count
    for path in sorted(paths, key=lambda p: (-weight_of[p], p)):
        target = min(range(count), key=lambda i: (loads[i], i))
        shards[target].append(path)
        loads[target] += weight_of[path]
    return [sorted(shard) for shard in shards]


def build_shards(paths, sources, weights, counts):
    """Returns {group: [shard files, ...]} for the requested shard counts."""
    groups = split_groups(paths, sources)
    result = {}
    for name in GROUPS:
        weight_of = {p: file_weight(p, sources[p], weights)
                     for p in groups[name]}
        result[name] = pack(groups[name], weight_of, counts[name])
    return result


def completeness_problems(paths, shards):
    """Lists every file that is in zero or in more than one shard."""
    seen = {}
    for name, group_shards in shards.items():
        for index, shard in enumerate(group_shards):
            for path in shard:
                seen.setdefault(path, []).append((name, index))
    problems = [f"{p}: in no shard" for p in paths if p not in seen]
    problems += [f"{p}: in {len(where)} shards {where}"
                 for p, where in sorted(seen.items()) if len(where) > 1]
    return problems


def marker_problems(shards, sources):
    """Files that use the browser marker but sit in the core group."""
    return [f"{p}: uses the browser marker but is in the core group"
            for shard in shards["core"] for p in shard
            if "mark.browser" in sources[p]]


def load_sources(paths, root=REPO_ROOT):
    return {path: read_source(path, root) for path in paths}


def path_for_classname(classname, known):
    """Maps a JUnit classname (dotted module, maybe a class) to a test file."""
    parts = classname.split(".")
    while parts:
        candidate = "/".join(parts) + ".py"
        if candidate in known:
            return candidate
        parts.pop()
    return None


def weights_from_junit(junit_paths, known):
    """Sums testcase times per known test file over the given JUnit files."""
    totals = {}
    for junit in junit_paths:
        for case in ET.parse(junit).getroot().iter("testcase"):
            path = path_for_classname(case.get("classname", ""), known)
            if path is not None:
                totals[path] = totals.get(path, 0.0) + float(case.get("time", "0"))
    return {path: max(1, round(seconds)) for path, seconds in sorted(totals.items())}


def command_weights(args):
    weights = weights_from_junit(args.junit, set(tracked_test_files()))
    json.dump(weights, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def command_files(args):
    if args.group not in GROUPS:
        raise SystemExit(f"unknown group {args.group!r}; use browser or core")
    if args.count < 1 or not 0 <= args.index < args.count:
        raise SystemExit("INDEX must satisfy 0 <= INDEX < COUNT, COUNT >= 1")
    paths = tracked_test_files()
    counts = {"browser": 1, "core": 1}
    counts[args.group] = args.count
    shards = build_shards(paths, load_sources(paths), load_weights(), counts)
    print("\n".join(shards[args.group][args.index]))
    return 0


def command_check(args):
    paths = tracked_test_files()
    sources = load_sources(paths)
    counts = {"browser": args.browser_shards, "core": args.core_shards}
    shards = build_shards(paths, sources, load_weights(), counts)
    problems = completeness_problems(paths, shards) + marker_problems(
        shards, sources)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"ok: {len(paths)} test files in "
              f"{args.browser_shards} browser + {args.core_shards} core shards")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    files = sub.add_parser("files")
    files.add_argument("group")
    files.add_argument("index", type=int)
    files.add_argument("count", type=int)
    check = sub.add_parser("check")
    check.add_argument("--browser-shards", type=int, default=1)
    check.add_argument("--core-shards", type=int, default=1)
    weights = sub.add_parser("weights")
    weights.add_argument("junit", nargs="+")
    args = parser.parse_args(argv)
    handlers = {"files": command_files, "check": command_check,
                "weights": command_weights}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
