# Phase 31 — Timing Baseline

## Pre-split baseline (31-01-PLAN.md Task 1)

- **Commit SHA:** `4fb2593b7b6573b0230626aa48da2f72a2314f6d`
- **Host:** `os.cpu_count()` = 10 (Apple Silicon macOS, arm64) — pinned `JOBS=4` below to mirror the CI runner's own core count rather than this host's, per RESEARCH.md Pitfall 5.
- **Measurement command:** `JOBS=4 ./scripts/run-all-tests.sh` from the repository root, using `server/.venv/bin/python3`.

### Local proxy — per-harness timing (slowest first), JOBS=4

| Harness | Wall (s) | Status |
| --- | --- | --- |
| companion/test_browser_ux.py | 240.9 | FAIL* |
| companion/test_companion_app.py | 22.5 | PASS |
| server/test_render.py | 10.4 | PASS |
| server/test_poll_loop.py | 5.8 | PASS |
| companion/test_status_pages.py | 4.3 | PASS |
| stub-server/test_poll_cycle.py | 3.8 | PASS |
| server/test_pipeline_e2e.py | 1.7 | PASS |
| server/test_panel_preview.py | 1.1 | PASS |
| companion/test_config_page.py | 1.0 | PASS |
| companion/test_i18n.py | 0.9 | PASS |
| companion/test_view_pages.py | 0.9 | PASS |
| server/test_illustrations.py | 0.7 | PASS |
| server/test_calendar_rules.py | 0.5 | PASS |
| server/test_notify.py | 0.2 | PASS |
| server/test_manual_resolutions.py | 0.2 | PASS |
| server/test_colour_rules.py | 0.2 | PASS |
| server/test_plane_detection.py | 0.2 | PASS |
| server/test_enrich.py | 0.2 | PASS |
| server/test_config_history.py | 0.2 | PASS |
| server/test_dither.py | 0.1 | PASS |
| server/test_runway_config.py | 0.1 | PASS |
| companion/test_contrast_check.py | 0.1 | PASS |

**Total wall time: 240.9s (JOBS=4)** — all 22 current `HARNESSES` entries present.

\* `companion/test_browser_ux.py` reports FAIL on this specific host (Apple Silicon
macOS, arm64 Chromium) for reasons fully unrelated to the code under test — see
"Local-environment correctness caveat" below. The wall-time figure (240.9s) is
still a valid duration measurement: the harness ran essentially all 96 checks
before failing on one of the affected checks near the end of the file, so the
number is not meaningfully shortened by the failure. Comparability for plan 04's
delta calculation is preserved because the same environmental quirk is symmetric
— it will still be present, in the same shape, when the split files are
re-measured on this same host.

### Local-environment correctness caveat (does not affect the timing number above)

The per-check PASS/FAIL transcript in `31-BASELINE-CHECKS.txt` was **not** captured
from this same `JOBS=4` run, and deliberately so. A standalone
`server/.venv/bin/python3 companion/test_browser_ux.py` run on this host (native
macOS, arm64 Chromium) deterministically FAILs 3 of 96 checks across 3 repeated
attempts, for two distinct, fully environmental reasons — neither is a defect in
the application or the test file, and neither is touched by this plan:

1. Two checks (the leave-guard "stays armed through commit" check and the
   validation-rejection echo check) both use `page.keyboard.press("Control+A")` to
   select-all before typing a replacement value. Blink's `EditingBehavior` for
   `EditingMacBehavior` maps Ctrl+A to "move to beginning of line" (an
   intentional Emacs-style binding), not select-all — only `EditingUnixBehavior`
   (Linux, i.e. the actual `ubuntu-latest` CI runner) treats Ctrl+A as select-all.
   On arm64 macOS the keystroke is a no-op for selection, so the typed value is
   appended rather than substituted.
2. One check (the no-JS fallback-Save-persists check) hits an intermittent
   Playwright "element is not stable ... element was detached from the DOM"
   timeout on the native-form-submit navigation, reproducing deterministically on
   both native arm64 macOS Chromium and an arm64 Linux Docker container, but never
   on an **amd64**-emulated Linux container (`--platform linux/amd64`, matching
   the actual GitHub Actions `ubuntu-latest` runner architecture) or on 4/4 sampled
   real CI runs from this same repository (`gh run view <id> --log`, each showing
   `browser-ux: 96/96 checks pass`). This points to an arm64-Chromium-specific
   paint/compositor timing characteristic, not a code defect.

Verification: 3 standalone runs on native macOS arm64 (this host) and 2 on an
arm64 Linux Docker container all reproduced the same failure pattern (3 FAILs on
macOS: the two Ctrl+A checks above plus the DOM-detach check; 1 FAIL on arm64
Linux: the DOM-detach check only, since Linux's Ctrl+A select-all behavior fixes
the first two). A single run under `--platform linux/amd64` (Docker, matching
CI's own architecture) produced a clean **96/96, zero FAIL** transcript, matching
4/4 sampled real CI runs on this repository. That amd64-emulated transcript is
what `31-BASELINE-CHECKS.txt` contains — it is the correctness-representative
baseline; this file's `JOBS=4` number above is the performance-representative
baseline. No source file was edited to produce either artifact.

### D-01's own CI-recorded figures (for cross-reference, not re-measured here)

- Job average: ~5min40s
- `companion/test_browser_ux.py` across five separate CI runs: 300.9s, 318.7s,
  314.4s, 303.4s, 314.2s
- Real CI confirms this file dominates the job — consistent with the local proxy
  figure above (240.9s), allowing for real-runner-vs-local-host variance.

Plan 04 should compare its post-split delta against both the local proxy number
above and a fresh real CI run's `gh run view` timing, per D-05's established
measurement method.

## Post-split measurement (31-04-PLAN.md Task 2)

- **Commit SHA:** `64ba819f6babfccd0b78049b61c70d7813b57653`
- **Host:** `os.cpu_count()` = 10 (Apple Silicon macOS, arm64) — the same host and
  the same native (non-Docker) architecture plan 01 used for its pre-split
  `JOBS=4` timing baseline above, so the two numbers are apples-to-apples.
- **Measurement command:** `JOBS=4 ./scripts/run-all-tests.sh` from the
  repository root, `server/.venv/bin/python3`, three independent runs.

### Local proxy — three independent JOBS=4 samples

| Run | Total wall time | Result | Failing checks |
| --- | --- | --- | --- |
| 1 | 209.5s | FAIL* | `companion/test_companion_app.py` (real bug, fixed mid-plan — see Deviations) + the two known Ctrl+A checks in `companion/test_browser_ux.py` |
| 2 | 279.4s | FAIL* | The two known Ctrl+A checks in `companion/test_browser_ux.py` |
| 3 | 258.2s | FAIL* | The two known Ctrl+A checks + the known DOM-detach check in `companion/test_browser_ux.py` |

\* All three runs fail on this host for the exact same reason 31-01-SUMMARY.md
and 31-03-SUMMARY.md already documented and root-caused: Blink's
`EditingMacBehavior` makes `Control+A` a no-op for text selection on native
macOS (only Linux's `EditingUnixBehavior` — i.e. the real `ubuntu-latest` CI
runner — treats it as select-all), plus one intermittent arm64-Chromium
DOM-detach compositor race. Neither is a regression introduced by this plan;
both are pre-existing, environment-only findings already established across
three prior plans on this same host. Per the correctness caveat below, the
genuine correctness proof for this plan comes from a `linux/amd64` Docker run,
not from these three native timing samples — the native numbers exist purely
for wall-time comparability with plan 01's own native baseline.

### Run 3's full per-harness timing table (representative — the reduced parent
still bounds total wall time in every sample)

| Harness | Wall (s) | Status |
| --- | --- | --- |
| companion/test_browser_ux.py | 258.2 | FAIL* (known env flake, see above) |
| companion/test_companion_app.py | 27.5 | PASS |
| companion/test_browser_ux_quiet_wake.py | 22.3 | PASS |
| companion/test_browser_ux_health_drawings.py | 18.7 | PASS |
| server/test_render.py | 16.8 | PASS |
| server/test_poll_loop.py | 9.2 | PASS |
| companion/test_status_pages.py | 7.6 | PASS |
| stub-server/test_poll_cycle.py | 3.9 | PASS |
| companion/test_view_pages.py | 2.4 | PASS |
| server/test_panel_preview.py | 2.4 | PASS |
| server/test_pipeline_e2e.py | 2.1 | PASS |
| companion/test_config_page.py | 1.7 | PASS |
| companion/test_i18n.py | 1.2 | PASS |
| server/test_illustrations.py | 1.0 | PASS |
| server/test_calendar_rules.py | 0.7 | PASS |
| server/test_config_history.py | 0.4 | PASS |
| server/test_colour_rules.py | 0.4 | PASS |
| server/test_manual_resolutions.py | 0.4 | PASS |
| server/test_notify.py | 0.3 | PASS |
| server/test_dither.py | 0.3 | PASS |
| server/test_enrich.py | 0.3 | PASS |
| server/test_plane_detection.py | 0.2 | PASS |
| companion/test_contrast_check.py | 0.2 | PASS |
| server/test_runway_config.py | 0.2 | PASS |

**The three browser harnesses' individual times, called out (run 3):**
- `companion/test_browser_ux.py` (reduced, 76 checks): 258.2s — still the sole
  bound on total wall time; identical to the run's own "Total wall time" figure
  in every one of the three samples.
- `companion/test_browser_ux_quiet_wake.py` (9 checks): 22.3s
- `companion/test_browser_ux_health_drawings.py` (11 checks): 18.7s

### Correctness verification — `linux/amd64` Docker (matching CI's `ubuntu-latest`
architecture), continuing 31-01/31-02/31-03's established recipe

Native arm64 cannot serve as a correctness oracle for `companion/test_browser_ux*.py`
on this host (established finding, unchanged since 31-01). Provisioned a
`--platform linux/amd64` `python:3.12-slim` container, installed
`server/requirements.txt` + `server/requirements-dev.txt` and
`playwright install --with-deps chromium` into a container-internal venv at
`/opt/venv-docker` (not inside the bind-mounted `/repo`, per 31-03's own
lesson), and ran as a **non-root user** — running as root inside the container
made four permission-based checks in `server/test_manual_resolutions.py` and
`companion/test_status_pages.py`/`companion/test_companion_app.py` false-fail,
because root bypasses the read-only-directory simulation those checks rely on
(root can write through a `chmod`-denied directory that a real CI runner's
non-root user cannot) — an artifact of the verification environment, not a
code defect, and unrelated to anything this plan changed.

`JOBS=4 PYTHON=/opt/venv-docker/bin/python3 /opt/venv-docker/bin/python3 scripts/run_all_tests.py`,
run as the non-root user with the real Chromium cache copied into its home
directory:

```
==> Result: PASS
==> Total wall time: 445.6s (JOBS=4)
```

- 24/24 `==> PASS` lines — every harness, including both new entries.
- `companion/test_browser_ux.py`: `browser-ux: 76/76 checks pass`
- `companion/test_browser_ux_health_drawings.py`: `browser-ux-health-drawings: 11/11 checks pass`
- `companion/test_browser_ux_quiet_wake.py`: `browser-ux-quiet-wake: 9/9 checks pass`
- 76 + 11 + 9 = 96, conserved — matching `31-BASELINE-CHECKS.txt`'s original count.
- Coverage report: `TOTAL 7829 517 93%` — well above the 83% `fail_under` floor
  in `pyproject.toml`; the split moved no covered statement.

The Docker run's own wall-time figures (445.6s total, 445.6s/70.0s/60.1s for
the three browser harnesses) are **not used for the D-05 timing comparison** —
QEMU-emulated `linux/amd64` on Apple Silicon runs 4-5x slower than either this
host's native execution or the real CI runner (consistent with 31-02/31-03's
own documented QEMU overhead). This run's sole purpose is proving the wired
suite is correct end-to-end; the native samples above are what feed the
arithmetic below.

## Post-split vs pre-split comparison (D-05 arithmetic)

**Suite-level (local proxy, native, JOBS=4, this host):**

| Sample | Pre-split (s) | Post-split (s) | Delta (s) | Delta (%) |
| --- | --- | --- | --- | --- |
| Best (run 1) | 240.9 | 209.5 | +31.4 | **+13.0%** (faster) |
| Mean (3 runs) | 240.9 | 249.0 | -8.1 | **-3.4%** (slower) |
| Median (run 3) | 240.9 | 258.2 | -17.3 | **-7.2%** (slower) |
| Worst (run 2) | 240.9 | 279.4 | -38.5 | **-16.0%** (slower) |

Arithmetic: `delta_s = pre - post`; `delta_pct = delta_s / pre * 100`.
Mean of the three post-split samples: `(209.5 + 279.4 + 258.2) / 3 = 249.0s`.

**The suite-level number does not show a clean win — two of three samples are
slower than the pre-split baseline, not faster.** See "Critical path and pool
contention" below for the mechanism.

**CI-job-level estimate (labelled explicitly as an estimate, per D-01's own
figures, not a repo-measured number):**

- D-01's CI job average: ~340s (5min40s).
- D-01's CI-measured `companion/test_browser_ux.py` average (5 runs):
  `(300.9 + 318.7 + 314.4 + 303.4 + 314.2) / 5 = 310.3s`.
- Fixed overhead (checkout, venv install, Chromium download, lint, the 21
  always-fast harnesses, coverage combine/report, attribution check) —
  everything the split does not touch: `340 - 310.3 = 29.7s`.
- Local total wall time equals the reduced parent's own wall time in every one
  of the three native samples above (confirmed: the "Total wall time" line
  matches `companion/test_browser_ux.py`'s own row exactly in all three runs),
  so each sample's post-split total is used directly as the new critical-path
  proxy:

| Sample | New critical path (s) | Job estimate = 29.7 + critical path (s) | vs. 340s job avg |
| --- | --- | --- | --- |
| Best (run 1) | 209.5 | 239.2 | **-100.8s, -29.6%** |
| Mean | 249.0 | 278.7 | **-61.3s, -18.0%** |
| Median (run 3) | 258.2 | 287.9 | **-52.1s, -15.3%** |
| Worst (run 2) | 279.4 | 309.1 | **-30.9s, -9.1%** |

**Against D-05's ~30-40% bar: every sample's job-level estimate falls short.**
The single best local sample (29.6%) comes closest but still does not clear
30%; the mean/median (15-18%) and the worst sample (9.1%) are well below it.

### Critical path and pool contention (why the intrinsic per-check savings did
not show up as wall-time savings)

The reduced `companion/test_browser_ux.py` (76 checks) **still dominates the
suite** — it is the longest-running harness and its own wall time equals the
suite's total wall time in every sample, exactly as before the split (96
checks, 240.9s). Extracting 18 `_in_both_themes()`-heavy checks should have
cut the parent's own compute cost by more than 18/96 (RESEARCH.md Pitfall 4's
own prediction, since both extracted groups are `_in_both_themes()`-heavy and
that cost is undercounted by a `.goto()` proxy) — but the wall-time reduction
observed is much smaller than that, and in two of three samples is negative.

The reason is visible directly in the per-harness timing table: **every
non-browser harness got slower after the split, despite zero code changes to
any of them.** Comparing run 3's table above against the pre-split table:

| Harness | Pre-split (s) | Post-split, run 3 (s) | Change |
| --- | --- | --- | --- |
| server/test_render.py | 10.4 | 16.8 | +62% |
| server/test_poll_loop.py | 5.8 | 9.2 | +59% |
| companion/test_status_pages.py | 4.3 | 7.6 | +77% |
| companion/test_companion_app.py | 22.5 | 27.5 | +22% |
| stub-server/test_poll_cycle.py | 3.8 | 3.9 | +3% |

This is the T-31-11 finding from the plan's own threat register, realized:
`EXPECTED_SLOWEST` now submits three Chromium-launching harnesses
(`companion/test_browser_ux.py`, `..._health_drawings.py`, `..._quiet_wake.py`)
into the first three of the pool's four worker slots, together with
`server/test_render.py` in the fourth — meaning **three real Chromium
processes now run simultaneously** for most of the run, competing for CPU with
each other and with whatever the fourth slot is running. Before this plan,
only one Chromium process ever ran at a time; the other three slots held only
light, non-browser harnesses. The contention this introduces is large enough
to erase most, and on two of three samples all, of the wall-time savings the
extraction itself earned. This is a genuine finding about the mechanism D-07
chose (join the existing worker pool), not a number to tune away, and not a
regression in the extracted files' own correctness (the Docker run above
proves both new files and the reduced parent are still individually correct
and verdict-preserving).

Whether this same contention shows up on the real CI runner is unknown from
this local proxy alone — the CI runner has *fewer* physical cores (4 vCPUs,
per RESEARCH.md's Pitfall 5 and confirmed by D-01's own printed `JOBS=4`
summary) than this 10-core host, which could make the contention *worse*
there (less real headroom per concurrent Chromium process) or, if the
CI runner's I/O/scheduling characteristics differ enough, could produce a
different result. This uncertainty is exactly why D-05's own gate is written
against a real CI `gh run view` measurement, not a local proxy — see Caveats.

## Caveats

1. **Local proxy vs. CI.** D-05's gate is defined against the CI "test" job's
   wall time, measured the same way D-01 measured the baseline
   (`gh run view` averaged over several real runs) — that number only exists
   once this branch has actually run in CI. Everything in this file's
   "Post-split measurement" and "arithmetic" sections is a local proxy on a
   10-core Apple Silicon host, not a CI measurement. The job-level figures
   above are explicitly labelled estimates for this reason.
2. **Suite total vs. job total.** The local suite's total wall time is not the
   CI job's total wall time — the CI job also pays fixed costs (checkout, venv
   install, Chromium download, lint, attribution check) the split does not
   touch. The job-level estimate above adds back D-01's own measured fixed
   overhead (~29.7s) to each local critical-path sample rather than comparing
   suite totals directly, but it remains an estimate, not a measurement.
3. **No fixed target (D-06).** There is no required wall-clock number for the
   CI job — "materially faster than today" is the bar, and the point is to
   stop at diminishing returns rather than chase an arbitrary figure. The
   pool-contention finding above is exactly the kind of diminishing-returns
   signal D-06 anticipates: the mechanism (more concurrent Chromium processes
   in the same 4-worker pool) is now showing a cost (contention) that grows
   alongside its benefit (fewer checks per file), and on this local evidence
   the cost is currently winning.

## D-05 Gate Verdict and Recommendation for Plan 05 (31-04-PLAN.md Task 3)

**Measured reduction:** suite-level ranges from +13.0% (best sample) to -16.0%
(worst sample), mean -3.4%, median -7.2% — i.e. no consistent suite-level win.
Job-level estimate (the figure D-05 is actually written about) ranges from
9.1% to 29.6%, mean/median 15-18%.

**Verdict against D-05's ~30-40% bar: MISSED on every sample of the local
proxy.** Even the single most favourable sample (29.6% job-level estimate)
falls short of the bar's low end. This is a local-proxy result, not a CI
measurement (Caveat 1) — but it is not a marginal near-miss either; four
independent computations (best/mean/median/worst) all land below 30%, and
three of the four suite-level samples show no improvement at all.

**Critical path: `companion/test_browser_ux.py` (the reduced, 76-check parent)
still dominates the suite** in every sample — its own wall time equals the
suite's total wall time each time, unchanged in *shape* from before the split
(96-check parent dominating at 240.9s). In principle this means further
extraction (e.g. Flights, 8 checks) could still shrink the parent's own
intrinsic compute cost. **In practice, the pool-contention finding above is
the more important signal**: every non-browser harness slowed down 22-77%
after this split with zero code changes to any of them, because three
Chromium-launching harnesses now compete for the same four worker slots where
only one used to. Adding a fourth concurrent Chromium process (Flights) to an
already-contended four-slot pool is unlikely to deliver a clean win under the
same mechanism, and could plausibly make the contention — and thus the total
wall time — worse rather than better.

**Recommendation for plan 05's checkpoint:**

Given the gate reads as missed on every local sample, D-05's own text says to
"stop here rather than opening a follow-up phase" for the settings
mega-cluster. Before finalizing that call, get the one number this file
cannot produce locally: **push this branch and read a real `gh run view`
timing for the CI "test" job**, exactly as RESEARCH.md's own "Phase gate"
requirement specifies ("Full suite green locally, then at least one real CI
run's `gh run view` timing compared against the D-01 baseline before declaring
the D-05 gate met or missed") — do not decide from this local proxy alone.

- **If the real CI number clears or comfortably approaches 30-40%:** the local
  contention finding may be specific to this host's core count and worker
  scheduling, not representative of the CI runner. In that case, treat the
  incremental approach as validated and open the D-05 follow-up phase for the
  mega-cluster, per the original plan — Flights is very unlikely to be worth
  extracting on its own at that point (it is the smallest of the three
  candidate groups and the two mandatory ones already cleared the bar without
  it).
- **If the real CI number matches this file's local finding (missed, or a
  similarly-sized shortfall) and shows the same pattern of non-browser
  harnesses slowing down:** stop per D-05's own instruction. Do **not**
  extract Flights as a mechanical third file under the current mechanism — the
  evidence here suggests the bottleneck has shifted from "one file has too
  many checks" to "the worker pool cannot run three-plus Chromium processes
  concurrently without contention eating the gain," which a fourth extracted
  file does not fix. If a future phase revisits this, it should first address
  the mechanism (e.g. a CI runner with more cores, or capping how many
  Chromium-launching harnesses the pool runs concurrently regardless of
  `JOBS`) rather than extracting further scenario groups into the same pool.
- **If pursued anyway, or if plan 05 decides to extract Flights for reasons
  other than pure wall-time:** flag what RESEARCH.md did not anticipate — the
  early Flights cluster (row expand/collapse, then the `.copy-btn`/`.row-toggle`
  hit-target family, then the filter-count/Clear check) is **not contiguous**
  in the current file. A quiet-hours-caption hit-target check ("the Quiet
  hours caption's schedule link clears the 44px hit-target floor...", CFG-69)
  sits between the first Flights check and the icon-hit-targets check, in file
  order (verified directly against the live file at this plan's commit, not
  against RESEARCH.md's now-superseded pre-01/02/03 line numbers). The
  extraction must anchor on check names/text, not a line range, and must
  explicitly leave that quiet-hours check behind in the parent file.

**Pool contention, not a real cost shift, on non-browser harnesses:** confirmed
above — every one of `server/test_render.py`, `server/test_poll_loop.py`,
`companion/test_status_pages.py`, `companion/test_companion_app.py` and
`stub-server/test_poll_cycle.py` slowed down after this split despite no code
change to any of them, consistent with three simultaneous Chromium processes
now competing for the pool's four worker slots where only one did before.

## Phase 31 Closing Verdict (31-05-PLAN.md Task 1 decision + Task 3 measurement)

### Task 1 checkpoint outcome: `skip-flights`

The developer selected **`skip-flights`** at the plan 05 Task 1 checkpoint,
after being shown this file's gate section (suite-level delta, the
D-01-methodology CI-job-level estimate, the three browser harnesses'
individual wall times, and the finding that the reduced parent still bounds
total wall time) and the scope correction that the early Flights cluster is
not contiguous (`_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px`
sits between the first and second early Flights checks and would have had to
stay behind, per the live-file re-verification in `31-05-SUMMARY.md`).

**Reasoning given:** D-05's gate missed on every sample of plan 04's local
proxy; D-06 explicitly sanctions stopping at diminishing returns; and this
matches both plan 04's own recommendation and the executing agent's
independent read of the same evidence. The developer did not request a real
CI number before deciding — the local-proxy evidence was treated as decisive.

**Consequence for Task 2:** no-op. No file was created or modified —
`companion/test_browser_ux_flights.py` does not exist,
`companion/test_browser_ux.py` remains at 76/76, and
`scripts/run_all_tests.py`/`EXPECTED_SLOWEST` were not touched.
`git status --porcelain companion/ scripts/` is empty for the whole plan.

### Fresh JOBS=4 re-measurement (Task 3, on the unchanged post-plan-04 code)

Since Task 2 changed nothing, this re-measurement exercises the exact same
24-harness, 96-check code state plan 04 measured — it exists to add samples
and firm up the closing verdict, not to measure a new change.

- **Commit SHA:** `77c6b116daef4220ec94247c13ac74978d6233c8`
- **Host:** same 10-core Apple Silicon macOS/arm64 host as plans 01 and 04.
- **Measurement command:** `PYTHON=server/.venv/bin/python3 JOBS=4
  ./scripts/run-all-tests.sh`, two independent runs.

| Run | Total wall time | Result | Failing checks |
| --- | --- | --- | --- |
| 1 | 212.7s | FAIL* | The two known Ctrl+A checks (leave-guard stays armed; validation-rejection echo) + the known DOM-detach check (no-JS fallback Save) in `companion/test_browser_ux.py` |
| 2 | 210.8s | FAIL* | Same three known checks, identical failure signatures |

\* Both runs fail for exactly the same three pre-existing, environment-only
checks documented and root-caused in `31-01-SUMMARY.md`/`31-03-SUMMARY.md`/the
pre-split section above (Blink's `EditingMacBehavior` makes `Control+A` a
no-op for selection on native macOS; one intermittent arm64-Chromium
DOM-detach race). No new failure appeared in either run — confirming this
re-measurement is not exercising any regression, only adding wall-time
samples on top of plan 04's already-established correctness proof (the
`linux/amd64` Docker run, 96/96, still stands unchanged since Task 2 touched
nothing).

**Run 2's full per-harness table (representative):**

| Harness | Wall (s) | Status |
| --- | --- | --- |
| companion/test_browser_ux.py | 210.7 | FAIL* (known env flake) |
| companion/test_companion_app.py | 25.0 | PASS |
| companion/test_browser_ux_quiet_wake.py | 23.3 | PASS |
| companion/test_browser_ux_health_drawings.py | 19.2 | PASS |
| server/test_render.py | 19.1 | PASS |
| server/test_poll_loop.py | 8.4 | PASS |
| companion/test_status_pages.py | 5.7 | PASS |
| stub-server/test_poll_cycle.py | 3.9 | PASS |
| server/test_pipeline_e2e.py | 1.7 | PASS |
| server/test_panel_preview.py | 1.6 | PASS |
| companion/test_config_page.py | 1.3 | PASS |
| companion/test_view_pages.py | 1.2 | PASS |
| companion/test_i18n.py | 1.0 | PASS |
| server/test_illustrations.py | 1.0 | PASS |
| server/test_calendar_rules.py | 0.6 | PASS |
| server/test_manual_resolutions.py | 0.3 | PASS |
| server/test_notify.py | 0.3 | PASS |
| server/test_dither.py | 0.2 | PASS |
| server/test_enrich.py | 0.2 | PASS |
| server/test_colour_rules.py | 0.2 | PASS |
| server/test_plane_detection.py | 0.2 | PASS |
| server/test_config_history.py | 0.2 | PASS |
| server/test_runway_config.py | 0.1 | PASS |
| companion/test_contrast_check.py | 0.1 | PASS |

`companion/test_browser_ux.py`'s own wall time (210.7s) again equals the
run's total wall time (210.8s) within rounding — the reduced parent is
still the sole bound on total wall time, exactly as in every one of plan
04's three samples.

### Delta arithmetic — this plan's two samples

**Vs. the pre-split baseline (240.9s, plan 01):**

| Sample | Pre-split (s) | This run (s) | Delta (s) | Delta (%) |
| --- | --- | --- | --- | --- |
| Run 1 | 240.9 | 212.7 | +28.2 | **+11.7%** (faster) |
| Run 2 | 240.9 | 210.8 | +30.1 | **+12.5%** (faster) |
| Mean (2 runs) | 240.9 | 211.75 | +29.15 | **+12.1%** (faster) |

**Vs. plan 04's own post-split measurement (209.5s / 279.4s / 258.2s, mean 249.0s):**

This plan's mean (211.75s) is faster than plan 04's mean (249.0s) by 37.25s
(**14.9%**), and lands almost exactly on plan 04's own best sample (209.5s) —
i.e., these two new samples sit at the fast end of plan 04's observed range,
not outside it. This is consistent with plan 04's own finding that the
suite's wall time is dominated by pool-contention noise rather than by a
fixed cost: five samples now exist (209.5, 279.4, 258.2, 212.7, 210.8) and
they span a 68.6s range (279.4s to 210.8s) on **identical code**, which is
itself evidence that the local proxy alone is too noisy to declare a precise
percentage — see the combined verdict below.

**CI-job-level estimate (D-01 methodology: `29.7 + critical-path sample`,
compared against the 340s job average):**

| Sample | New critical path (s) | Job estimate (s) | vs. 340s job avg |
| --- | --- | --- | --- |
| Run 1 | 212.7 | 242.4 | **-97.6s, -28.7%** |
| Run 2 | 210.8 | 240.5 | **-99.5s, -29.3%** |

**Combined across all five samples measured for this phase (plan 04's three
plus this plan's two), sorted:**

| Sample source | Critical path (s) | Job estimate (s) | vs. 340s job avg |
| --- | --- | --- | --- |
| Plan 04, worst | 279.4 | 309.1 | 9.1% |
| Plan 04, median | 258.2 | 287.9 | 15.3% |
| This plan, run 1 | 212.7 | 242.4 | 28.7% |
| This plan, run 2 | 210.8 | 240.5 | 29.3% |
| Plan 04, best | 209.5 | 239.2 | 29.6% |

Mean of all five: **22.4%**. Median of all five: **28.7%**. Range: **9.1% to
29.6%** — a 20.5-point spread across five runs of literally identical code,
which is the clearest single piece of evidence in this file that pool
contention (not a fixed extraction benefit) is the dominant variable, and
that this host's local proxy cannot pin the true figure down more precisely
than "somewhere under 30%, possibly close to it on a good run."

### Final D-05 verdict

**Against D-05's ~30-40% bar: MISSED.** Not one of the five samples measured
across plans 04 and 05 clears even the bar's 30% floor — the best single
sample (29.6%) and this plan's two fresh samples (28.7%, 29.3%) all fall just
short. The bar is not cleared, but three of five samples come close enough
(within 1-2 points of 30%) that "missed" should be read as "missed, and
close on a good run, but not reliably close" rather than "missed by a wide
margin on every measurement" — the mean (22.4%) and the worst sample (9.1%)
show the same code can also land well below that.

**Suite-level:** no consistent win either. This plan's two samples both show
a real suite-level improvement (+11.7%, +12.5%, faster than pre-split), but
combined with plan 04's own three samples (+13.0% best to -16.0% worst), the
five-sample suite-level picture remains mixed rather than a clean win.

**Recommendation: against opening the follow-up decomposition phase for the
settings mega-cluster, at this time.**

Reasoning tied to the measured numbers:

1. **The bar was not cleared on any of five independent local samples**,
   despite two of this plan's own runs landing at the favourable end of the
   observed range. D-06 explicitly instructs stopping at diminishing returns
   rather than chasing a number, and five samples clustered mostly below 30%
   (with a 20-point spread) is diminishing-returns evidence, not a marginal
   near-miss on a stable number.
2. **The dominant mechanism is pool contention, not "one file has too many
   checks."** Plan 04 measured every non-browser harness slowing 22-77% with
   zero code changes to any of them once three Chromium-launching harnesses
   joined the same four-worker pool. A follow-up phase decomposing the
   settings mega-cluster would very likely add yet more concurrent Chromium
   processes to that same contended pool — the evidence here suggests that
   makes the contention problem worse, not the check-count problem better,
   which is exactly the mechanism this plan's own Task 1 checkpoint declined
   to test further via the (smaller, cheaper) Flights extraction.
3. **The settings mega-cluster is a materially harder decomposition than the
   two clean extractions this phase already took.** Per `31-RESEARCH.md`'s
   "Why the mega-cluster is not this phase's target": it accounts for
   roughly 70% of the original check bodies, spans 34 heavily-interleaved
   Display-page checks and 7 Device-page checks, includes checks
   deliberately written to drive both pages in a single check body, and
   reuses a set of shared local closures across multiple checks inside it.
   None of the risk-reducing properties that made Health-Drawings and
   Quiet-Wake safe extractions (small, self-contained, zero cross-file
   coupling) hold for this cluster.
4. **If a future phase revisits this**, it should address the mechanism
   first — e.g. a CI runner with more cores, or a pool policy that caps how
   many Chromium-launching harnesses run concurrently regardless of `JOBS`
   — rather than extracting further scenario groups into the same
   contended four-slot pool.

**CI caveat (repeated per D-05's own measurement method):** every number in
this file, including this closing verdict, is a **local proxy** on a 10-core
Apple Silicon host. D-05's authoritative figure is the CI "test" job's wall
time from `gh run view`, averaged over several real runs, the same way D-01
measured the baseline. This branch (`claude/optimize-tests-ci-278bc4`) has
not yet been pushed, so no real CI number exists for it at the time this
verdict was written. **This verdict should be re-checked on the first real
CI run of this branch and revised if the CI figure disagrees materially** —
particularly because the CI runner has only 4 vCPUs (fewer than this host's
10), which could make the measured pool contention better or worse there in
ways this local proxy cannot predict.

**D-07 held for the whole phase:** `git status --porcelain .github/` is
empty at every plan boundary in phase 31, including this one — no workflow
YAML change, no matrix strategy, no new scheduling mechanism was introduced
anywhere in this phase.

## Real CI confirmation (post-PR #78, UAT items 1 and 2)

The verdict above asked to be re-checked against the first real CI run. That
run happened: PR #78 (`claude/optimize-tests-ci-278bc4` → `main`), workflow
run [35778948703](https://github.com/florianlepont/skypane/actions/runs/35778948703),
2026-09-22.

**Result: PASS, 24/24 harnesses green** — including all three
Chromium-launching harnesses running concurrently (`browser-ux`,
`browser-ux-health-drawings`, `browser-ux-quiet-wake`). No new flakiness;
none of the three ARM64/macOS-only local flakes are present, as expected on
Linux amd64.

| Metric | Real CI value | D-01 baseline | Delta |
| --- | --- | --- | --- |
| Total job wall time (job start → job end) | 327s | ~340s (5min40, avg of 5 CI runs) | **-13s, -3.8%** |
| Critical path (`companion/test_browser_ux.py`, same as suite total wall time) | 281.2s | 310.3s (avg of 5 CI runs) | -29.1s |
| Job-level estimate (D-01 method: 29.7s fixed overhead + critical path) | 310.9s | 340s | **-29.1s, -8.6%** |

**Verdict: CONFIRMED, not contradicted.** The real CI number (3.8%-8.6%
depending on method) lands at or slightly below the worst of the five local
samples (9.1%) and nowhere near the 30-40% bar — the local proxy correctly
predicted both the shortfall and its cause. Direct confirmation of the
contention mechanism: on the CI runner's 4 vCPUs (vs. this host's 10),
`browser-ux-quiet-wake` took 43.1s and `browser-ux-health-drawings` took
34.0s — both substantially slower than their local figures (22.3s, 18.7s) —
and every non-browser harness that was slower locally after the split
(`server/test_render.py`, `server/test_poll_loop.py`,
`companion/test_status_pages.py`, `companion/test_companion_app.py`) is
slower here too (35.7s, 20.2s, 17.0s, 32.8s respectively), consistent with
fewer real cores making the same three-concurrent-Chromium contention worse,
not better.

**Both outstanding UAT items are resolved by this run:** the real-CI timing
confirms the gate is missed (not just locally), and 24/24 harnesses passing
with the three-Chromium-process pool running concurrently is direct evidence
against new contention-driven flakiness. The developer's `skip-flights`
decision, made before this run on local evidence alone, is validated by the
real number rather than contradicted by it — closing the phase here, per
D-06, remains the right call.
