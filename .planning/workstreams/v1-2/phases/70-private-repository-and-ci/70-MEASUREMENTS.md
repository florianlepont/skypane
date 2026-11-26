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
- Free disk space: to be confirmed by the owner (at least 60 GB advised).

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
