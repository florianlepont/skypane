# Phase 70: CI measurements and decisions

Outcomes and numbers only. No serial number, network name, token or key.

## Decision record

D-07 decision: request-path-splitting-plan (decided by the owner, 2026-11-26)
D-07 delivered: workflow-level paths exclusion of 3D model files under hardware/cad, no job-level change detection, gates unchanged

The owner chose to have the CI split by changed paths, in a separate plan (70-06b), instead of keeping the whole suite on every code change. The constraints of that plan are the ones already agreed: no test is skipped for a change to code, the browser tests still run on every change to code, the aggregate check "Lint, test, coverage, attribution" always reports, and the coverage and test-count gates are not weakened. The visibility flip waits for that plan.

Context given to the owner before the decision: 22 of the last 52 commits were docs-only and already skip the CI; 28 test files read `firmware/`; the gates require the executed-test floor and a skipped ceiling of zero; `hardware/cad` holds only 3D and note files that no code or test reads.

## Runner host

- Machine: laptop, Apple Silicon (M5 chip), 16 GB of memory, arm64 (no emulation needed for the tests).
- Uptime: on almost all the time, no detailed schedule; a laptop sleeps when the lid is closed, so the runner serves jobs only while the Mac is awake (see the runner README).
- Sizing agreed: 2 single-use runners, one VM each, about 5 GB per VM, instead of the 4 runners of the kit's default; expected wall-clock per full run about 25 to 35 minutes (to be measured).
- Free disk space (read from the Mac on 2026-11-27): 27 GB free; the two VMs have a 20 GB disk each.
- Machine as measured on 2026-11-27: 10 cores, 16 GB; each VM 4 CPUs, 5 GiB of memory, 20 GiB disk (aarch64); `JOBS=2` test workers per job. The sizing line above (25 to 35 minutes) turned out too optimistic: see "Before and after".

## CI path splitting

Delivered by plan 70-06b on 2026-11-26. Design: a workflow-level `paths` exclusion in `ci.yml` (push and pull_request) for `hardware/cad/**/*.stl`, `*.blend`, `*.glb`, `*.3mf`, on top of the existing Markdown, `.planning`, `.claude` and LICENSE exclusions. No job is conditional on paths, so a run that exists is always the whole run and the gates (`scripts/ci_gates.py`, coverage floor, shard checks) are unchanged.

Method: `scripts/ci_path_filter.py measure --last 100`, once with the `ci.yml` of the base commit and once with the new `ci.yml`. The unit is the first-parent commit, an approximation of a push (GitHub applies the filter per push, so a push of several commits behaves like the union of their files). Base commit: `2188a9e1f3b2935c292dc3e41601063f12092e6d` (main, before this plan). The 100 commits span 2026-11-21 to 2026-11-26.

| Measure (last 100 first-parent commits) | Before | After |
|---|---|---|
| Commits that would run CI | 61 | 49 |
| Commits that would skip CI | 39 | 51 |

- Docs-only share (Markdown, planning, LICENSE, already skipped before): 39 of 100.
- 3D-model share (skipped only because of this plan): 12 of 100. All 12 touched 3D model files under `hardware/cad` plus Markdown or planning files only.
- Heavy runs avoided: 12 of the 61 commits that run today (about 20 percent of them).
- Estimate of minutes saved per month, from the inputs only: 60 billable minutes per full hosted run (context D-05), about 20 commits per day in this 5-day window (a busy period, 100 commits in 5 days) giving about 600 commits a month, 12 percent of them newly skipped: 600 x 0.12 x 60 = about 4,300 billable minutes per month on hosted runners. On the self-hosted runner the same figure is runner time (expected 25 to 35 minutes of wall-clock per run), not billed minutes. The window is dense with 3D-model work; a quieter month would save less, and the saving is zero in a month without such commits.
- Not measured here: an actual GitHub run on a model-only commit. After merge, a push touching only one `.stl` should start no run.

The visibility flip may proceed on this point.

## Coverage only on main

Decision (owner, 2026-11-26; the owner works alone and wants shorter PR CI): every test still runs on every pull request and on main; only the coverage tracing and the coverage floor move to pushes to `main` and manual `workflow_dispatch` runs.

Measured motivation, from `70-TEST-AUDIT.md`: twelve core files (2,783 tests), 4 workers, took 68.4 s without coverage and 79.8 s with `--cov` and `COVERAGE_CORE=sysmon`, so coverage tracing costs about 17 percent of test time (the C tracer would cost 72 percent). Not measured on the browser group or on Python 3.14.

What changes: on `pull_request` the shards run with `SKYPANE_COVERAGE=off` (`pytest --no-cov`) and write only the JUnit report. The aggregate check "Lint, test, coverage, attribution" still requires every job, one JUnit file per shard and the totals gate (no failures, executed floor, skipped ceiling 0); it skips only the coverage-data steps and writes "coverage: not measured on pull requests; measured on main". On main and dispatch nothing changes. Cost: a pull request is not checked against the coverage floor, so a drop shows up as a red CI on main after the merge and the deploy guard refuses that commit.

Not measured here: the time saved on a real PR run (needs a CI run after merge).

## Runner install

Dates: installed and registered on 2026-11-25 and 2026-11-26 (owner's Mac, Lima VMs, launchd loops).

- runners: 2 (one single-use runner per VM, a new just-in-time registration for every job)
- runner idle and visible: yes (GitHub showed both runners online and busy on 2026-11-26; the owner's local session read the same)
- variable set: yes, `CI_RUNS_ON` = `["self-hosted","skypane-ci"]`; the owner removes it while the repository is public to get fast hosted runs, and sets it again before the flip
- collaborators: none
- outside collaborators approval required: to be confirmed by the owner before the flip
- fork PR workflows disabled: to be confirmed by the owner before the flip (the fork-pull-request guard in `ci.yml` is in place)

Problems found and fixed while running real CI on the VMs (2026-11-26): `/tmp` in RAM filled by test data (fixed with `TMPDIR=/home/runner/tmp`, later a wipe after every job); too many xdist workers for 5 GiB (`JOBS=2`); no C compiler (4 firmware cross-check tests errored) and no `node` (33 minifier tests skipped, which the gate refuses): both added to the VM definition; the Mac went to sleep and killed two jobs (kept awake with `caffeinate`); the 20-minute job limit cancelled four jobs (now 45 minutes when `CI_RUNS_ON` is set).

## Before and after

baseline billable minutes: 60 (run 45337958006, hosted, 2-core Linux, each job rounded up per minute; about 17 runs a day)

Hosted fallback (repository still public, so nothing is billed today): runs 1485 and 1487 took about 10 minutes of wall-clock each. Billable minutes if the repository were private: about 55 to 60 per run, read from the job times of run 1487 (static 1; core 6 and 7; browser 10, 9, 10 and two more of the same size); hosted minutes on the private repository were not measured because the repository is public. hosted fallback billable minutes: about 60 (estimate, not measured)

Mac runner (2 runners, VMs of 4 CPUs, 5 GiB, 2 test workers per job):

| Run | What | Wall-clock | Runner time of the test jobs | Longest job |
|---|---|---|---|---|
| 1483 (2026-11-26, first complete run) | before the VM fixes | 82 minutes | invalid: sleep, missing tools, 20-minute limit | 20 minutes |
| 1490 (PR) | after the VM fixes, coverage on | 57 minutes, one job failed once and passed on re-run | about 114 minutes over 7 jobs | 19.3 minutes |
| 1492 (PR, no coverage) | after the test speed changes | not isolated (shared the runners with other runs) | about 91 minutes over 7 jobs | 14.7 minutes |
| 1498 (main, coverage on) | after the speed changes | 67 minutes, shared | about 77 minutes over 7 jobs | 12.3 minutes |
| PR run of the 8-shard change | 8 test jobs, no coverage | not isolated | about 87 minutes over 8 jobs | 12.6 minutes |

wall-clock per run: Mac about 50 to 60 minutes when the runners are not shared (57 minutes measured once on 2026-11-26, 67 minutes shared); hosted fallback about 10 minutes. A clean, solo run of the final layout was not measured: the runners were always shared with other runs.

runners: 2

Test speed work (audit in `70-TEST-AUDIT.md`, merged 2026-11-26): about 20 percent less runner time for the test jobs (114 to 91 minutes), and coverage only on `main` (about 17 percent of test time measured on core files). The eight-shard layout shows no measurable gain on two runners (87 minutes over 8 jobs against 77 over 7 with coverage on); its value is balance (four jobs per runner) and four-runner hosts.

Gate numbers (read from the gate on green runs 1498 and 1504): skipped: 0 (the gate refuses any skipped test and both runs passed it); executed: 17552 test items collected (`pytest --collect-only`), against the gate floor of 12,821, which is not changed; browser shards run: 6 (8 test jobs with the 2 core shards).

Monthly minutes (estimates from the inputs, not measurements): before, about 500 runs a month at 60 billable minutes is about 30,000 against about 2,000 included; with the Mac runner, the hosted minutes left are the deploy (about 1 per deploy), the firmware release build (about 3 per release) and the daily CA chain check (about 30 a month), so well under 100. A month entirely on hosted runners at the path-filtered rate (about 300 runs of 60 minutes) would be about 18,000 minutes, about $96 above the $12 of included compute at $0.006 per minute.

charge status: postponed with no new date (2026-11-27): GitHub's changelog says it is "postponing the announced billing change for self-hosted GitHub Actions to take time to re-evaluate our approach"; the billing documentation lists self-hosted runners as free and not reducing the included compute. The included compute on GitHub Free is $12 a month, about 2,000 Linux 2-core minutes at $0.006 per minute (arithmetic, not stated on the page). Re-check before the flip and again by 2026-12-24.

## Decision record: where CI runs

Interim state (2026-11-27): CI runs on the owner's Mac when `CI_RUNS_ON` is set and on hosted runners when it is not; hosted runs are free while the repository is public. The docs-only skip, the path filter and the owner's decision of 2026-11-26 are in force; no test is skipped for a change to code and the browser tests run on every change to code.

Open decision for the owner, before the flip: keep the Mac (free, about 50 to 60 minutes per run, sleeps, shared with the owner's work), a second-hand mini PC with four runners (about 150 to 250 euros once, about 25 to 30 minutes expected, not measured), or the paid hosted minutes (about $96 a month at the current rate, not recommended). Recommendation recorded: the mini PC; the Mac is acceptable until it is bought. Mac settings tried or still open: `JOBS=3` on one VM (not tried), a shard count that divides evenly (done, 8 test jobs).

decision: pending the owner
