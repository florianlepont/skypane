---
phase: 70-private-repository-and-ci
plan: 06b
type: execute
wave: 4
depends_on: [70-06, 70-07]
files_modified:
  - scripts/ci_path_filter.py
  - scripts/test_ci_path_filter.py
  - .github/workflows/ci.yml
  - .github/workflows/deploy.yml
  - deploy/tests/test_ci_runner.py
  - deploy/tests/test_ci_paths.py
  - deploy/README.md
  - CONTRIBUTING.md
  - deploy/tests/test_docs.py
  - .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md
autonomous: true
requirements: [PRV-02]
must_haves:
  truths:
    - "A change to any code file, or to any non-Markdown file a test reads (including every non-Markdown file under firmware/ and hardware/), still runs the whole suite: every shard, the browser tests, and all three gates. Markdown files that tests read (COMPLIANCE.md, firmware/SIGNING.md, CONTRIBUTING.md and the hardware/*.md notes) stay excluded by the existing `!**/*.md` filter exactly as today; only deploy/README.md and the VENDOR.md files are re-included"
    - "A commit that touches only 3D model files under hardware/cad (and Markdown, .planning, .claude, LICENSE) starts no CI run, exactly like a docs-only commit today"
    - "No job is conditional on paths: a CI run that exists is always the full run, so the aggregate check 'Lint, test, coverage, attribution' reports on every run and the coverage floor, executed-test floor and skipped ceiling see the whole suite"
    - "scripts/ci_gates.py, pyproject.toml (fail_under, testpaths) and scripts/ci_shards.py are unchanged"
    - "A file of any other type added under hardware/cad (for example a .py) matches no exclusion, so that commit runs the full suite and the guard tests run"
    - "The measured number of the last 100 commits that skip the heavy jobs, before and after, is recorded in 70-MEASUREMENTS.md"
  artifacts:
    - path: "scripts/ci_path_filter.py"
      provides: "GitHub paths-filter matcher, reads the filter from ci.yml; decide and measure subcommands"
    - path: "deploy/tests/test_ci_paths.py"
      provides: "Proof tests: excluded set holds only inert files, nothing references them, every other tracked file runs CI"
    - path: ".github/workflows/ci.yml"
      provides: "push and pull_request paths filter with the four 3D-model exclusions"
      contains: "!hardware/cad/**/*.stl"
  key_links:
    - from: "deploy/tests/test_ci_paths.py"
      to: ".github/workflows/ci.yml"
      via: "scripts/ci_path_filter.py reads the same paths list the workflow uses"
      pattern: "workflow_paths"
    - from: ".github/workflows/deploy.yml"
      to: "CI check 'Lint, test, coverage, attribution'"
      via: "ci_sha input for a tip that has no CI run"
      pattern: "ci_sha"
---

<objective>
Split the CI by changed paths, as the owner decided on 2026-11-26 (recorded in 70-MEASUREMENTS.md): a change that touches no code and no file read by any test needs no heavy jobs. Plan 70-10 (the visibility flip) depends on this plan and checks the `D-07 delivered:` line this plan writes; this plan does not touch 70-10.

Ordering: this plan depends on 70-07 (wave 4) because both plans edit 70-MEASUREMENTS.md and plan 70-07 writes most of it; running after 70-07 keeps same-wave file ownership disjoint. 70-MEASUREMENTS.md, including the line `D-07 decision: request-path-splitting-plan (decided by the owner, 2026-11-26)` and the "Runner host" section, already exists on main (decision recorded before this plan runs, so no decision is asked again). This plan edits only (a) a new section "CI path splitting" that it appends and (b) the single new `D-07 delivered:` line after the decision line; it never rewrites other sections.

Design chosen, and why it is safe: a workflow-level `paths` exclusion in `.github/workflows/ci.yml`, not a job-level `changes` job. The only change class that may skip anything is "no code, no file read by a test", and a workflow-level filter delivers exactly that with the smallest change: a skipped commit starts no run at all, like a docs-only commit does today. No job gets a path condition, so a run that exists is always the full run and every gate (`scripts/ci_gates.py` executed floor 12,821 and skipped ceiling 0, the `fail_under = 93` coverage floor, the shard-count and one-JUnit-per-shard checks) sees the whole suite unchanged and is neither edited nor made conditional. A job-level design would need conditional gates (skipped jobs accepted, floors adjusted) which weakens them, for no extra skipped commit. The aggregate check keeps `if: always()` and still reports on every run that runs at all.

Exclusions are by file type, not by directory: `hardware/cad/**/*.stl`, `*.blend`, `*.glb`, `*.3mf`. A `.py`, `.sh`, `.json` or any other type added under `hardware/cad` matches `**` and runs the suite, so a code file can never be skipped by being placed there, and the guard tests in this plan run on that very commit. `firmware/` stays on the full suite (28 test files read it). `hardware/` other than the proven-inert model files stays included (hardware/test_logtools_*.py and fixtures/logs read by tests). `design-exploration/` stays included too: it holds 11 Python files that `ruff check .` lints (this corrects the research note that called it inert).

Deploy precondition: `deploy.yml` still requires a green "Lint, test, coverage, attribution" run for the SHA. A tip that touched only excluded files has no CI run, so the owner passes the existing `ci_sha` input (the last commit that had a run); the shipped-path diff check there does not list `hardware/cad`, so it needs no logic change, only comment and doc wording.

Purpose: fewer billable or runner minutes on commits that cannot change any test result, without any chance of skipping a test.
Output: path-filter matcher and measurement tool, updated ci.yml, updated `deploy/tests/test_ci_runner.py`, new proof tests, docs, and before/after numbers in 70-MEASUREMENTS.md.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-CONTEXT.md
@.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-RESEARCH.md
@.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md
@.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-06-SUMMARY.md
@.github/workflows/ci.yml
@.github/workflows/deploy.yml
@deploy/tests/test_ci_runner.py

Facts established while planning (re-verify in task 2 with the greps, do not trust blindly):
- hardware/cad tracks 11 files: 6 .stl, 2 .blend, 1 .glb, 1 .3mf and README.md (already excluded by `!**/*.md`). No .py/.js/.sh/.yml/.toml/.json there.
- Grep of every .py/.sh/.yml/.toml/.js/.json outside .venv, .claude, .planning found no reference to hardware/cad. The only readers of hardware/ are hardware/logs, hardware/fixtures (tests), firmware/monitor.sh (writes hardware/logs) and `server/hardware.py` (names hardware/*.md in strings).
- Whole-tree walkers: scripts/check_comment_history.py (git ls-files, skips files with no extractor, so .stl/.blend/.glb/.3mf are skipped), scripts/exposure_scan.py, scripts/ci_shards.py (test files only), scripts/check_function_size.py (server, stub-server only), scripts/check-attribution.sh (server/assets only).
- ci.yml `on.push.paths` and `on.pull_request.paths` are identical lists; firmware.yml uses positive paths only (firmware/**, server/hardware.py), so it is untouched by this plan.
- ci.yml header comment says "docs-only changes are skipped by the paths filter"; deploy.yml input `ci_sha` description and a step comment say "docs-only"/"Markdown-only"; deploy/README.md line ~469 says "A docs-only tip has no CI run". No document states "no path splitting"; CONTRIBUTING.md's "still runs the whole suite" is about `run-all-tests.sh` and stays true.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Path-filter matcher with decide and measure subcommands</name>
  <files>scripts/ci_path_filter.py, scripts/test_ci_path_filter.py</files>
  <read_first>
    - .github/workflows/ci.yml (lines 31-58: the exact `paths:` list syntax, two-space and six-space indents)
    - scripts/ci_shards.py (style: stdlib only, argparse subcommands, REPO_ROOT, git via subprocess with argument lists)
    - scripts/ci_gates.py (style reference for a small stdlib gate script with exit codes)
  </read_first>
  <behavior>
    - Pattern semantics follow GitHub: `*` matches within one path segment, `**` matches across segments (`**/` also matches zero directories), `?` one non-slash character, a leading `!` excludes, patterns are applied in order and the last matching pattern decides a file. A change set runs CI when at least one file ends up included.
    - With the real ci.yml list: `README.md`, `docs/x.md`, `.planning/a.json`, `LICENSE`, `hardware/cad/print/a.stl` give no run; `deploy/README.md` and `server/assets/fonts/VENDOR.md` run (re-included); `hardware/cad/new/tool.py`, `hardware/cad/x.step`, `firmware/main/a.c`, `hardware/logtools.py`, `design-exploration/plane-screen/mock_fonts.py` run.
    - A mixed set (`hardware/cad/a.stl` plus `README.md`) gives no run; (`hardware/cad/a.stl` plus `server/x.py`) runs; an empty set gives no run.
    - The list is read from the workflow text, for the `push` and the `pull_request` event; reading fails loudly (non-zero exit) when either list is missing or the two lists differ.
    - `measure` over a commit range reports, per commit on the first-parent line, whether CI would run and prints totals (commits counted, would run, would skip, skip percentage).
  </behavior>
  <action>
    Create scripts/ci_path_filter.py (stdlib only, no code blocks needed here, follow ci_shards.py style) with these functions and subcommands. `workflow_paths(text, event)` scans the workflow text for the `paths:` block under the given event (`push` or `pull_request`) using a line scan (same text-scan discipline as deploy/tests/test_ci_runner.py, no YAML parser) and returns the ordered pattern list; raise a dedicated error class if the block is absent. `compile_pattern(pattern)` translates one pattern to an anchored regex (`**/` to an optional any-prefix group, `**` to any characters, `*` to non-slash characters, `?` to one non-slash character, everything else escaped). `runs(files, patterns)` returns True when at least one file ends included, applying the in-order, last-match-wins rule with a leading `!` meaning exclude. `decide FILE...` subcommand reads the push list from `.github/workflows/ci.yml` (or `--workflow PATH`), checks that the push and pull_request lists are identical, prints `run` or `skip` and exits 0 for run, 1 for skip, 2 for a workflow it cannot read. `measure --last N [--ref REV] [--workflow PATH]` lists the last N commits on the first-parent line of REV with `git log --first-parent`, takes each commit's changed files with `git diff --name-only <sha>^ <sha>` (the empty tree for a root commit, and for a merge commit the first-parent diff, which is the whole pull request), prints one line per commit (short sha, run or skip, file count) then a totals line, and exits 0; if fewer than N commits exist it reports the actual count. All git calls use argument lists, never a shell. Keep every function under 40 lines. Comments in English, no plan, decision or phase identifiers (CLAUDE.md comment rule). Write scripts/test_ci_path_filter.py first (RED) covering every case in the behavior block, including a temporary workflow text with differing push and pull_request lists (must raise) and `measure` against a throwaway git repository built in tmp_path with commits that touch an stl only, a .md only, and a .py; then implement until green. Tests must not use the network (pytest-socket guard is on) and must not skip.
  </action>
  <acceptance_criteria>
    - `server/.venv/bin/python -m pytest scripts/test_ci_path_filter.py -q` passes with 0 skipped.
    - `server/.venv/bin/python scripts/ci_path_filter.py decide README.md` exits 1 and prints `skip`; `... decide server/x.py` exits 0 and prints `run`. (Run these two against the repository's ci.yml only after task 2; before task 2 the `hardware/cad/a.stl` case is expected to print `run`.)
    - `server/.venv/bin/ruff check scripts/ci_path_filter.py scripts/test_ci_path_filter.py` is clean.
    - `server/.venv/bin/python scripts/check_comment_history.py check` exits 0.
    - `server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2` exits 0 (the new test file is in exactly one shard without editing scripts/ci_shard_weights.json).
  </acceptance_criteria>
  <verify>
    <automated>server/.venv/bin/python -m pytest scripts/test_ci_path_filter.py -q && server/.venv/bin/ruff check scripts && server/.venv/bin/python scripts/check_comment_history.py check && server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2</automated>
  </verify>
  <done>The matcher reproduces GitHub path-filter behaviour for the repository's real list, reads the list from ci.yml, and can count would-run/would-skip commits over a range.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the 3D-model exclusions to ci.yml and prove the excluded set is inert</name>
  <files>.github/workflows/ci.yml, .github/workflows/deploy.yml, deploy/tests/test_ci_runner.py, deploy/tests/test_ci_paths.py</files>
  <read_first>
    - .github/workflows/ci.yml (header comment lines 1-30, `on:` block lines 33-58, the `test` job `if: ${{ always() }}`)
    - .github/workflows/deploy.yml (the `ci_sha` input description and the comment above the `git diff --quiet` pathspec)
    - deploy/tests/test_ci_runner.py (all of it, especially `test_no_test_is_skipped_by_path_or_weakened` which asserts `"changes:" not in _CI`)
    - scripts/ci_path_filter.py (from task 1)
    - scripts/ci_gates.py, pyproject.toml lines 100-110, scripts/ci_shards.py (read to confirm they are NOT to be edited)
  </read_first>
  <behavior>
    - Every tracked file other than Markdown, `.planning/**`, `.claude/**`, `LICENSE`, and the four 3D-model types under hardware/cad makes `runs()` true against ci.yml's real list.
    - The tracked files (`git ls-files hardware/cad`) under hardware/cad all have an extension in {.stl, .blend, .glb, .3mf, .md}.
    - No .py/.sh/.js/.yml/.yaml/.toml/.json/.jsonl/.cfg/.ini file outside the allowed-reference set mentions hardware/cad, in any spelling (`hardware/cad`, `"hardware", "cad"`, `"hardware" / "cad"`), and no such file globs or walks the hardware directory.
    - Every negated pattern in ci.yml's list belongs to a reviewed set; a new exclusion fails the test until a person adds it to that set with its proof.
    - ci.yml has no `changes` job, no job-level `if:` other than the fork-pull-request guard on the three work jobs and `always()` on `test`, no `needs.changes`, and the three gates and the shard-count check are still present.
  </behavior>
  <action>
    First re-run the proof greps and record their (empty) results in the SUMMARY: list `git ls-files hardware/cad` by extension; grep every tracked .py/.sh/.yml/.yaml/.toml/.js/.json file outside .venv, .claude, .planning for `hardware/cad`, `"cad"` joined to `hardware`, and for `hardware` followed within 80 characters by `glob(`, `rglob`, `os.walk`, `iterdir`, `listdir`. If ANY hit appears (other than the test files named below) STOP: do not exclude that path, record the hit, and return to the caller. Do not weaken a gate to proceed.
    Edit .github/workflows/ci.yml: in BOTH `push.paths` and `pull_request.paths` insert, after `- '!LICENSE'` and before the two re-include lines, the four entries `- '!hardware/cad/**/*.stl'`, `- '!hardware/cad/**/*.blend'`, `- '!hardware/cad/**/*.glb'`, `- '!hardware/cad/**/*.3mf'`. Do not touch jobs, matrices, gates, `needs`, concurrency or env. Update the header comment (lines 3-8) and the comment above the push paths (lines 37-40): say that no job has a path condition, that a commit touching only Markdown, planning notes, LICENSE or the 3D model files under hardware/cad starts no run, that those model files are the only non-Markdown files excluded because no code or test reads them, that the exclusion is by file type so any other file added there runs the suite, and that the gates in scripts/ci_gates.py need the whole suite so a run that exists is always whole. English, no plan/decision/phase identifiers. Edit .github/workflows/deploy.yml wording only: the `ci_sha` description says the tip may be a commit that has no CI run (documentation or 3D model files only), and the step comment above the `git diff --quiet` pathspec says "Commits that never run CI (Markdown, 3D model files) may sit between the CI commit and the tip; any shipped path may not." Leave the pathspec, shell logic and every other line byte-identical (confirm with `git diff -U0 .github/workflows/deploy.yml` showing comment/description lines only).
    Edit deploy/tests/test_ci_runner.py: rename `test_no_test_is_skipped_by_path_or_weakened` to `test_no_job_is_conditional_on_paths_and_no_gate_is_weakened`; keep the existing assertions on `ci_shards.py check`, `ci_gates.py`, the combine step, the totals step, `- '!**/*.md'`, `- '!.planning/**'`; replace `assert "changes:" not in _CI` with assertions that no `  changes:` job exists (regex over job keys), that `needs.changes` and `dorny/paths-filter` are absent, that the `test` job still has `if: ${{ always() }}` and `needs: [static, tests-core, tests-browser]`, and that the only `if:` lines at job level are the fork guard on the three work jobs. Add an assertion that the four `hardware/cad` entries appear exactly twice each (push and pull_request).
    Create deploy/tests/test_ci_paths.py importing scripts/ci_path_filter.py by file path with importlib (the repo uses `--import-mode=importlib` and `pythonpath` ["."], so `from scripts import ...` follows whatever test_ci_secrets.py does; copy its import style). Tests: (1) allowlist: every path from `git ls-files hardware/cad` (not a filesystem walk: gitignored .blend1 backups and other untracked files must not matter) has an extension in the five allowed; (2) the reviewed exclusion set: the set of negated patterns in ci.yml equals exactly {`**/*.md`, `.planning/**`, `.claude/**`, `LICENSE`} plus the four model patterns, for both events; (3) every `git ls-files` path that is not Markdown, not under `.planning/` or `.claude/`, not LICENSE and not a hardware/cad model file has `runs()` true (this is the "no code path skips the suite" test; it also covers firmware/, hardware/ logs and fixtures, design-exploration/, docs/ non-Markdown, scripts/, test-support/); (4) the reference scan described in the behavior block over tracked files of the listed suffixes, excluding exactly these five tracked files, the only ones allowed to mention the path: .github/workflows/ci.yml, deploy/tests/test_ci_paths.py, deploy/tests/test_ci_runner.py, scripts/test_ci_path_filter.py, deploy/tests/test_docs.py (task 3 adds `hardware/cad` assertions there); the test asserts the set of hits is a subset of these five, and the five are the single allowlist constant in the test; (5) a hypothetical `hardware/cad/new/tool.py`, `hardware/cad/x.step` and `firmware/main/a.c` each yield run, a hypothetical `hardware/cad/print/a.stl` plus `README.md` yields skip, and the same plus `server/x.py` yields run; (6) firmware.yml triggers (`firmware/**`, `server/hardware.py`) are untouched and none of them can match a model file under hardware/cad; (7) deploy.yml's shipped-path pathspec contains none of the hardware/cad path (so `ci_sha` works for a cad-only tip). Use `git ls-files` through subprocess (CI always has git and a checkout); no skips. Write the tests first, confirm test (2)/(5) fail before the ci.yml edit, then edit ci.yml and go green.
    Do not edit scripts/ci_gates.py, scripts/ci_shards.py, scripts/ci_shard_weights.json or pyproject.toml.
  </action>
  <acceptance_criteria>
    - `server/.venv/bin/python -m pytest deploy/tests/test_ci_runner.py deploy/tests/test_ci_paths.py deploy/tests/test_ci_secrets.py deploy/tests/test_deploy_workflow.py scripts/test_ci_path_filter.py -q` passes with 0 skipped.
    - `git diff --stat -- scripts/ci_gates.py scripts/ci_shards.py scripts/ci_shard_weights.json pyproject.toml` prints nothing.
    - `server/.venv/bin/python scripts/ci_path_filter.py decide hardware/cad/print/skypane_lid.stl` exits 1; `... decide hardware/cad/print/skypane_lid.stl server/poll.py` exits 0; `... decide firmware/main/main.c` exits 0.
    - `grep -c "hardware/cad/\*\*/\*\.\(stl\|blend\|glb\|3mf\)" .github/workflows/ci.yml` prints 8 (4 patterns x 2 events); the same file has no line matching `^  changes:`.
    - `grep -n "ci_gates.py totals" .github/workflows/ci.yml` and the `fail_under = 93` line in pyproject.toml are present and unmodified.
    - `server/.venv/bin/ruff check .`, `server/.venv/bin/python scripts/check_comment_history.py check`, `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server` and `server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2` all exit 0.
    - `git diff -U0 .github/workflows/deploy.yml` shows only comment and input-description lines changed.
  </acceptance_criteria>
  <verify>
    <automated>server/.venv/bin/python -m pytest deploy/tests scripts/test_ci_path_filter.py stub-server/test_phase47_freeze.py -q -p no:cacheprovider && server/.venv/bin/ruff check . && server/.venv/bin/python scripts/check_comment_history.py check && server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2 && git diff --quiet -- scripts/ci_gates.py scripts/ci_shards.py scripts/ci_shard_weights.json pyproject.toml</automated>
  </verify>
  <done>ci.yml excludes only the four inert model types under hardware/cad, in both events; the proof tests fail if any code or test-read path could skip the suite; the runner test no longer asserts "no changes job" but asserts "no job is conditional on paths"; gates and floors are byte-identical.</done>
</task>

<task type="auto">
  <name>Task 3: Update the docs and record the before/after measurement</name>
  <files>deploy/README.md, CONTRIBUTING.md, deploy/tests/test_docs.py, .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md</files>
  <read_first>
    - deploy/README.md (the "Production deploy (started by hand)" section around the `ci_sha` paragraph, ~line 455-480, and any CI paragraph)
    - CONTRIBUTING.md lines 14-32
    - deploy/tests/test_docs.py (`_text()`, the firmware-releases section test as the style to copy)
    - .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md (all of it)
    - scripts/ci_path_filter.py (measure subcommand output format)
  </read_first>
  <action>
    Record BASE_REV first: BASE_REV is the output of `git rev-parse` for the commit before the first 06b commit (the HEAD of the checkout when this plan started, before task 1's commit). Read the pre-plan workflow from it with `git show <BASE_REV>:.github/workflows/ci.yml` into a file in the scratchpad directory (never into the repository) and name BASE_REV in the record.
    Docs. deploy/README.md: in the production-deploy section replace "A docs-only tip has no CI run" with wording that a tip that touched only Markdown, `.planning`, `.claude`, LICENSE or 3D model files under `hardware/cad` has no CI run, then add one short paragraph "Which commits start CI" stating (also include these two facts: Markdown files that tests read, such as COMPLIANCE.md and firmware/SIGNING.md, are excluded like all Markdown except deploy/README.md and the VENDOR.md files, as today; and GitHub evaluates a path filter against at most the first 300 changed files of a push or pull request, so a change set larger than that is decided on that sample): every other change runs the whole suite (every shard, the browser tests, the coverage floor, the executed-test floor and the skipped ceiling); no job has a path condition; the aggregate check "Lint, test, coverage, attribution" reports on every run that exists; the exclusions are by file type under `hardware/cad`, so any other file added there runs CI; and that a tip with no CI run is deployed by passing `ci_sha`. CONTRIBUTING.md: after the aggregate-check sentence add one sentence that commits touching only documentation or the 3D model files under `hardware/cad` start no CI run, and that any change to code or to a non-Markdown file a test reads runs everything, and one sentence that GitHub's path filter looks at no more than the first 300 changed files. No plan or decision identifiers in any of these texts. Grep deploy/runner/README.md and COMPLIANCE.md for "docs-only", "path" and "whole suite"; per planning neither states "no path splitting", so edit them only if the grep finds such a statement, and say which in the SUMMARY.
    deploy/tests/test_docs.py: add a test `test_ci_paths_section_states_what_skips_and_what_never_does` asserting the README contains the "Which commits start CI" heading text, the words `hardware/cad`, `ci_sha`, "Lint, test, coverage, attribution", and does not contain "docs-only tip"; and nothing that reads CONTRIBUTING.md: CONTRIBUTING.md is excluded by `!**/*.md`, so a test reading it would not run on a commit that edits only it; the smaller change is to leave the filter alone and assert only deploy/README.md (already re-included). `deploy/tests/test_docs.py` is on the five-file reference-scan allowlist for its `hardware/cad` literal, so its own edit stays green; confirm by running deploy/tests/test_ci_paths.py in this task's verify. Existing docs tests stay unchanged and passing.
    Measurement. Run `server/.venv/bin/python scripts/ci_path_filter.py measure --last 100 --workflow <saved pre-plan ci.yml>` and again with `--workflow .github/workflows/ci.yml`, both from the same HEAD, and a third time restricted to commits that did not already skip, to count how many of the commits that run today would stop running. Append to 70-MEASUREMENTS.md a section "CI path splitting" with: method (first-parent commits as the unit, an approximation of a push; GitHub applies the filter per push, so a push of several commits behaves like the union of their files), the base commit, the date, the counts of the last 100 commits that would skip before and after (docs-only share and 3D-model share separately), the number of commits skipped only because of this plan, and an estimate of runner minutes saved per month from the measured wall-clock or the 60 billable minute figure already in the context (stated as an estimate with its inputs). Report the real numbers even if the gain is zero or very small, and say so in plain words; do not round up. Change nothing else in that file (edit only the new "CI path splitting" section and the single `D-07 delivered:` line): keep the exact existing line `D-07 decision: request-path-splitting-plan (decided by the owner, 2026-11-26)` and add a following line `D-07 delivered: workflow-level paths exclusion of 3D model files under hardware/cad, no job-level change detection, gates unchanged`. State in the same section that the visibility flip may proceed on this point.
  </action>
  <acceptance_criteria>
    - `server/.venv/bin/python -m pytest deploy/tests/test_docs.py deploy/tests/test_ci_paths.py -q` passes with 0 skipped and includes the new tests (the reference scan accepts test_docs.py).
    - `grep -c "docs-only tip" deploy/README.md` prints 0; `grep -c "Which commits start CI" deploy/README.md` prints 1.
    - 70-MEASUREMENTS.md contains the heading "CI path splitting", two numeric counts out of 100 labelled before and after, the base commit, and the line starting `D-07 delivered:`; it contains no token, key, host or serial number.
    - `server/.venv/bin/ruff check .` and `server/.venv/bin/python scripts/check_comment_history.py check` exit 0; `git diff --quiet -- scripts/ci_gates.py pyproject.toml` exits 0.
    - Full local run of `./scripts/run-all-tests.sh` is NOT required; instead `server/.venv/bin/python -m pytest deploy scripts -q -p no:cacheprovider` passes.
  </acceptance_criteria>
  <verify>
    <automated>server/.venv/bin/python -m pytest deploy/tests/test_docs.py deploy/tests/test_ci_paths.py deploy/tests/test_ci_runner.py -q && grep -c "Which commits start CI" deploy/README.md && grep -q "^D-07 delivered:" .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md</automated>
  </verify>
  <done>Docs describe which commits start CI and how a tip without a run is deployed; the measurement section holds before/after counts of the last 100 commits with method and honest interpretation.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| commit -> CI trigger | changed paths decide whether any check runs at all |
| CI result -> production deploy | deploy.yml requires a green aggregate check for the SHA |
| contributor/session branch -> self-hosted runner | unchanged by this plan; fewer runs, same isolation |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70-06b-01 | Tampering | ci.yml paths exclusion | mitigate | Exclusion is by file type (.stl/.blend/.glb/.3mf) not by directory, so any code or config file placed under hardware/cad matches `**`, starts a full run, and the guard tests then execute. test_ci_paths.py fails when an unreviewed exclusion is added, when a non-model file sits in hardware/cad, or when any tracked non-excluded file would skip. |
| T-70-06b-02 | Tampering | a future test reads a hardware/cad file | mitigate | Adding the reader changes a .py file, which runs the full suite, and the reference scan in test_ci_paths.py fails on that same commit until the exclusion is removed. |
| T-70-06b-03 | Repudiation | commit merged with no CI result | mitigate | Same state as today's docs-only commits: deploy.yml still demands a green "Lint, test, coverage, attribution" run for the SHA; a tip with no run needs `ci_sha`, whose shipped-path diff check is unchanged. Documented in deploy/README.md. |
| T-70-06b-04 | Denial of service / false green | aggregate check and gates | mitigate | No job becomes conditional; `test` keeps `if: always()` and the existing `needs` result check; ci_gates.py, pyproject.toml floors and ci_shards.py are asserted unmodified (git diff empty) and test_ci_runner.py asserts the gate steps and absence of a `changes` job or path conditions. |
| T-70-06b-05 | Elevation of privilege | path filter and fork pull requests | accept | The fork-PR guard on the three work jobs is untouched; a PR that runs no workflow reaches no runner, which only reduces exposure. |
| T-70-06b-07 | Tampering | GitHub path filters look at only the first 300 changed files | accept | A push or pull request of more than 300 changed files is evaluated on a sample; a code change hidden past file 300 behind 300 excluded files is not credible in this single-owner repository, and the documented fallback is `workflow_dispatch`, which is in the `on:` block. Stated in deploy/README.md and CONTRIBUTING.md. |
| T-70-06b-06 | Information disclosure | measurement record | mitigate | 70-MEASUREMENTS.md receives counts and a commit hash only; no token, host, key or serial number. |
</threat_model>

<verification>
- All new and updated tests pass with zero skipped: scripts/test_ci_path_filter.py, deploy/tests/test_ci_paths.py, deploy/tests/test_ci_runner.py, deploy/tests/test_docs.py.
- `scripts/ci_gates.py`, `scripts/ci_shards.py`, `scripts/ci_shard_weights.json`, `pyproject.toml` have an empty diff.
- ruff, comment-history guard, function-size gate (80) and the shard-membership check exit 0.
- Executed-test count only goes up (new tests added), so the floor in ci_gates.py is not touched; a maintainer raising it is a separate ratchet step, not part of this plan.
- Not verifiable in this plan: an actual GitHub run on a cad-only commit (the filter is checked by the matcher and text tests). After merge, the owner can confirm by pushing a commit touching only one .stl and seeing that no CI run starts; record it in the SUMMARY as not run if not done.
</verification>

<success_criteria>
- Owner decision of 2026-11-26 is delivered: path-based splitting exists, no code change and no test-read file can skip any test, browser tests run on every code change.
- The aggregate check still reports on every run that exists; gates unchanged.
- test_ci_runner.py deliberately updated; docs consistent; measurement recorded; plan 70-10 flagged as depending on this plan.
</success_criteria>

<output>
Create `.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-06b-SUMMARY.md` when done
</output>
