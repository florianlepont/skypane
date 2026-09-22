# Phase 31: CI test suite — parallelize companion/test_browser_ux.py - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce the CI "test" job's wall-clock time by making `companion/test_browser_ux.py` — currently one sequential 16,361-line script that dominates the job — run in true parallel, without losing coverage or introducing flakiness. Infrastructure/test-tooling work, orthogonal to the companion UI phases (27-30) that happen to touch the same directory.

</domain>

<decisions>
## Implementation Decisions

### Measured baseline (live, from `gh run view` on 5 recent `ci.yml` runs)
- **D-01:** The CI "test" job averages ~5min40 wall time. `companion/test_browser_ux.py` alone takes 300-320s consistently (300.9s, 318.7s, 314.4s, 303.4s, 314.2s across the 5 runs) — ~88-90% of the job's total. All 21 other harnesses in `scripts/run_all_tests.py`'s `HARNESSES` list finish in under 32s **combined** (second-slowest is `companion/test_companion_app.py` at 31.2s). The worker pool (`JOBS=4` on the CI runner, confirmed from the run's own printed summary) already runs every harness concurrently, so the job's total time is bounded by this one file regardless of anything else in the suite.
- **D-02 [informational]:** The 300s+ is not explained by fixed sleeps — only 10.6s total comes from `page.wait_for_timeout()` calls across the whole file. The real cost is structural: 108 `page.goto()` calls and 184 browser/context/page creations, executed sequentially inside one `main()` that shares a single Playwright `browser` and a single `companion/app.py` subprocess `harness`, accumulating into one global `results` list gated by an `EXPECTED_CHECK_COUNT` invariant (`main()` returns non-zero if the count doesn't match, at the very bottom of the file). Background measurement motivating D-04's extraction approach — not a standalone action; the extraction work in plans 31-01 through 31-03 IS the response to this finding.
- **D-03 [informational]:** `scripts/run_all_tests.py` already documents this file as "the slowest single file by construction" — a known, accepted tradeoff at the time it was written, not a bug. This phase is the first attempt to actually reduce it. Background framing/motivation for the phase's existence — not a standalone action.

### Scope and risk appetite (user decision)
- **D-04 (user decision):** Incremental approach — extract the 2-3 largest logical scenario groups (e.g. Vols/Flights, Compagnies/Airlines, Paramètres/Settings — exact grouping is Claude's Discretion, see below) out of `test_browser_ux.py` into their own independently-runnable files in **this** phase. Do NOT attempt to fully decompose the entire 16,361-line file in one shot — it is the largest and most heavily-invested test file in the repo (150+ chained scenarios, extensive historical commentary tied to specific plan IDs), and a one-shot full split was explicitly rejected as too risky for one phase.
- **D-05 (user decision):** Success gate for continuing beyond this phase — if the first incremental extraction measurably cuts the CI "test" job's wall time by **at least ~30-40%**, that validates the approach and a follow-up phase should be opened to finish decomposing the rest of the file. If the measured gain is below that, stop here rather than opening a follow-up phase — the incremental win wasn't judged worth the additional risk on the remaining file.
- **D-06 (user decision):** No fixed target wall-clock time for the CI job (e.g., no "must be under 2 minutes"). "Materially faster than today" is the bar; the planner/executor should stop at diminishing returns rather than chase an arbitrary number.

### Parallelization mechanism (user decision)
- **D-07 (user decision):** Extracted files join the **existing local worker pool** — i.e. they become new entries in `scripts/run_all_tests.py`'s `HARNESSES` list (and `EXPECTED_SLOWEST` ordering, since they'll be among the slowest) and are picked up automatically by the `JOBS=4` `ThreadPoolExecutor` pool already in `scripts/run_all_tests.py`. **No GitHub Actions workflow/YAML changes** — `.github/workflows/ci.yml` should not need to change at all for this phase (it already just calls `./scripts/run-all-tests.sh`). A GitHub Actions matrix strategy (separate runners per shard) was explicitly considered and rejected for this phase: it would duplicate per-shard setup cost (checkout + venv install + Playwright Chromium download, ~35s each) and add workflow complexity, for a mechanism this repo doesn't otherwise use anywhere in `ci.yml`.

### Claude's Discretion
- Exact scenario-group boundaries for the 2-3 files extracted in this phase — should follow the app's own natural page/feature boundaries (the file's internal structure already groups checks by page area: flights, airlines, settings/config, health/état, calendar, theme, uploads, a11y/hit-targets) rather than an arbitrary line-count split. Pick the 2-3 groups that are both large (high time-savings potential) and have the cleanest boundaries (least shared mutable state with the rest of the file) — this determination needs the researcher/planner to actually read the file's `check()` call sites, not a decision made blind here.
- Whether each extracted file gets its own `companion/app.py` subprocess + Playwright `browser` instance (matching the established pattern every other `companion/test_*.py` harness in this repo already uses) — this is the obvious, pattern-consistent choice and doesn't need user confirmation.
- Whether shared helpers (`_login`, `_wait_for_bar`, `seed_state_dir`, etc.) get factored into a shared non-test helper module imported by both the original file and the new extracted files, vs. duplicated — planner's call, guided by avoiding meaningful duplication without over-engineering a shared module for what might end up being 2-3 call sites.
- Each extracted file gets its own `EXPECTED_CHECK_COUNT` invariant, matching the established one-file-one-counter convention every other harness in this repo already follows (Phase 4's D-07 convention: `check()`/PASS-FAIL/`EXPECTED_CHECK_COUNT`, verified live in `server/test_*.py`, `companion/test_*.py`, etc.) — not a decision point, just confirming existing convention carries over.
- `pyproject.toml`'s coverage config (`parallel = true`, one `.coverage.*` data file per process) already supports adding more concurrent processes with zero changes — confirmed by reading `[tool.coverage.run]`; splitting into more files is additive to this, not a change to it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The file being split
- `companion/test_browser_ux.py` — the 16,361-line target of this phase. Single shared `browser` + `harness` (companion/app.py subprocess) in `main()`, `check(name, fn)` accumulator pattern, `EXPECTED_CHECK_COUNT` gate at the very end (`total == EXPECTED_CHECK_COUNT`). Helper functions worth knowing before splitting: `_login`, `_wait_for_bar`/`_wait_for_bar_hidden`, `seed_state_dir`, `_set_ui_theme`, `_in_both_themes`, `_assert_hit_target` — used across many scenario groups, candidates for a shared helper module.

### Test orchestration (CI must keep invoking these correctly)
- `scripts/run_all_tests.py` — the orchestration layer: `HARNESSES` list (18 entries today — D-04's extraction adds 2-3 more, going to 20-21), `EXPECTED_SLOWEST`/`_submission_order()` (longest-first submission ordering — new extracted files should likely be added here too, near the top, since they'll be among the slowest), `_run_one()` (per-harness subprocess invocation under `coverage run`, own process group, timeout + SIGKILL), `JOBS` env var (worker count, defaults to `os.cpu_count()`, CI prints "JOBS=4").
- `scripts/run-all-tests.sh` — thin wrapper CI and README both call; owns the `PYTHON` interpreter contract. No changes expected.
- `.github/workflows/ci.yml` — the "test" job. D-07 means this file should not need changes for this phase's work (it already just runs `./scripts/run-all-tests.sh`); if research finds a reason it *does* need to change, flag that as a deviation from the discussed decision, don't just do it silently.
- `pyproject.toml` `[tool.coverage.run]` — `parallel = true`, `source = ["server", "stub-server", "companion"]`, `omit` list already excludes `companion/app.py` (measured as structurally unmeasurable — subprocess boundary) and the `test_*.py` files themselves. New extracted files are `companion/test_*.py` and are auto-omitted by the existing glob; no coverage config change expected.

### Established convention this phase must follow
- `.planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/04-CONTEXT.md` — D-07 defines the `check()`/PASS-FAIL/`EXPECTED_CHECK_COUNT` harness convention every test file in this repo (including `test_browser_ux.py` itself) already follows; any new extracted file must follow the same convention, not invent a new one.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/run_all_tests.py`'s worker pool, timeout handling, and coverage-parallel plumbing already support adding more harness files with zero orchestration changes — the extraction work is purely about creating new, independently-runnable `companion/test_*.py` files and adding their names to `HARNESSES`/`EXPECTED_SLOWEST`.
- Every other `companion/test_*.py` harness already demonstrates the "launch companion/app.py as its own subprocess on its own port" pattern the extracted files should reuse (e.g. `companion/test_companion_app.py`, `companion/test_config_page.py`).

### Established Patterns
- One file = one `check()`/`EXPECTED_CHECK_COUNT` harness, exit 0/1, is the universal convention (D-07 from Phase 4, confirmed still followed by every harness in the current `HARNESSES` list).
- `scripts/run_all_tests.py`'s `EXPECTED_SLOWEST` submission-order list exists specifically so slow harnesses start first and aren't queued behind fast ones on a small worker pool — the same reasoning applies to whatever new files this phase creates.

### Integration Points
- New extracted files must be added to `scripts/run_all_tests.py`'s `HARNESSES` list (and almost certainly `EXPECTED_SLOWEST`) for CI to pick them up at all — a file that exists but isn't listed there silently never runs in CI.
- `companion/test_browser_ux.py` currently "skips cleanly (exit 0) when playwright/Chromium is unavailable" (per `scripts/run_all_tests.py`'s own comment) — any extracted files must preserve this same skip-when-unavailable behavior, not turn a missing-Chromium environment into a hard CI failure.

</code_context>

<specifics>
## Specific Ideas

No UI/copy requirements — this is test-infrastructure work. The concrete decisions above (incremental 2-3 group extraction, ≥~30-40% measured gain as the bar for a follow-up phase, local worker-pool mechanism with no CI YAML changes, no fixed time target) are the specifics.

</specifics>

<deferred>
## Deferred Ideas

- Full decomposition of the remaining scenario groups in `companion/test_browser_ux.py` beyond the first 2-3 extracted here — deferred to a follow-up phase, conditional on D-05's measured-gain gate.
- A GitHub Actions matrix strategy (per-shard runners) — considered and rejected for this phase (D-07); could be revisited later if the local worker-pool approach turns out to be CPU-bound-limited on the 4-core CI runner even after extraction.
- The ~20s/run Playwright Chromium-download caching opportunity noticed during discovery (unrelated, small, separate from this phase's dominant bottleneck) — not folded into this phase; flagged separately, not part of this phase's scope.

</deferred>

---

*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Context gathered: 2026-09-22*
