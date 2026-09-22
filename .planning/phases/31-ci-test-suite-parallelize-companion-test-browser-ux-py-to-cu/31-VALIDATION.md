---
phase: 31
slug: ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-22
updated: 2026-09-22
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

This phase is unusual: its deliverable *is* test infrastructure. Every artifact
it produces is itself an automated check, so validation is not a layer bolted on
top — it is the same code. The one thing that needs deliberate design is the
comparison that proves the split preserved behaviour, because no existing tooling
in this repo does it.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Hand-rolled `check(name, fn)` / `EXPECTED_CHECK_COUNT` / `main()` convention (Phase 4 D-07). No pytest anywhere in this repo. |
| **Config file** | None per-file. Orchestration lives in `scripts/run_all_tests.py`; `scripts/run-all-tests.sh` owns the `PYTHON` interpreter contract; coverage scope lives in `pyproject.toml` `[tool.coverage.run]`. |
| **Quick run command** | `server/.venv/bin/python3 companion/test_browser_ux_<group>.py` (one harness standalone, from the repository root) |
| **Full suite command** | `JOBS=4 ./scripts/run-all-tests.sh` (all harnesses, pinned to CI's worker count, with coverage) |
| **Estimated runtime** | Standalone extracted harness: expect roughly 30-80s each (measured per file in plans 02/03). Reduced `companion/test_browser_ux.py`: expect roughly 200-260s. Full suite pre-split baseline: ~320s at `JOBS=4`; post-split target is materially lower (D-06). |

**Interpreter prerequisite.** `server/.venv` does not exist in this worktree.
`scripts/run-all-tests.sh` hard-exits without it, so nothing in this phase can be
validated until plan 01 task 1 provisions it. That is the phase's only Wave 0
gap and it is scheduled as the first task of the first plan.

**Worker-count pinning.** Every timing measurement in this phase runs with
`JOBS=4`. This host reports more cores than the GitHub-hosted `ubuntu-latest`
runner, and an unpinned local run hides the contention CI actually experiences,
understating the split's benefit (RESEARCH.md Pitfall 5).

---

## Sampling Rate

- **After every task commit:** run the specific file(s) that task touched
  standalone — `server/.venv/bin/python3 companion/test_browser_ux*.py` — plus
  `server/.venv/bin/ruff check` on the touched directory.
- **After every plan wave:** `JOBS=4 ./scripts/run-all-tests.sh`.
- **Before `/gsd-verify-work`:** full suite green, and the four-way check-name
  comparison against `31-BASELINE-CHECKS.txt` clean.
- **Max feedback latency:** ~80s for a single extracted harness; ~260s for the
  reduced parent; ~320s for the full suite. Longer than the usual target, and
  unavoidable — every check drives a real Chromium against a real HTTP
  subprocess. The mitigation is that each task's own verify runs only the file
  it touched, not the suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Decision | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | D-01, D-06 | T-31-SC | Installs only from the repo's own pinned requirements files, identical to CI | smoke + measurement | `server/.venv/bin/python3 companion/test_browser_ux.py` then `JOBS=4 ./scripts/run-all-tests.sh` | ✅ existing | ⬜ pending |
| 31-01-02 | 01 | 1 | D-04 | T-31-01 | Relocated code keeps the parent's no-external-URL constraint verbatim | structural (AST) + import smoke | `server/.venv/bin/ruff check companion/test_browser_ux_helpers.py` + AST shape assertions | ❌ created by this task | ⬜ pending |
| 31-01-03 | 01 | 1 | D-04 | T-31-01 | N/A — import rewiring only | regression (transcript diff) | `server/.venv/bin/python3 companion/test_browser_ux.py` diffed against `31-BASELINE-CHECKS.txt` | ✅ existing | ⬜ pending |
| 31-02-01 | 02 | 2 | D-04, D-07 | T-31-03 | New harness navigates only to `Harness.base_url()`; skips cleanly without Chromium | smoke (11/11) + skip-path | `server/.venv/bin/python3 companion/test_browser_ux_health_drawings.py` | ❌ created by this task | ⬜ pending |
| 31-02-02 | 02 | 2 | D-04 | T-31-03 | N/A | smoke (85/85) + counter conservation | `server/.venv/bin/python3 companion/test_browser_ux.py` + AST sum assertion | ✅ existing | ⬜ pending |
| 31-02-03 | 02 | 2 | D-04 | T-31-03, T-31-04 | Concurrent harnesses cannot collide on an ephemeral port | integration (2-way diff + concurrency) | Concurrent two-file run + PASS-name set comparison against baseline | ✅ (artifact from 31-01-01) | ⬜ pending |
| 31-03-01 | 03 | 3 | D-04, D-07 | T-31-06, T-31-07 | New harness navigates only to `Harness.base_url()`; skips cleanly | smoke (9/9) + skip-path + import-shape | `server/.venv/bin/python3 companion/test_browser_ux_quiet_wake.py` | ❌ created by this task | ⬜ pending |
| 31-03-02 | 03 | 3 | D-04 | T-31-07 | Staying dirty-bar audit still resolves the promoted shared helpers | smoke (76/76) + counter conservation | `server/.venv/bin/python3 companion/test_browser_ux.py` + AST sum assertion | ✅ existing | ⬜ pending |
| 31-03-03 | 03 | 3 | D-04 | T-31-06, T-31-08 | Three concurrent harnesses cannot collide | integration (3-way diff + concurrency) | Concurrent three-file run + PASS-name set comparison against baseline | ✅ (artifact from 31-01-01) | ⬜ pending |
| 31-04-01 | 04 | 4 | D-07, D-03 | T-31-10 | No workflow YAML change; no new scheduling mechanism | structural (AST) | AST assertions on `HARNESSES` / `EXPECTED_SLOWEST` + `tomllib` assertions on `pyproject.toml` | ✅ existing | ⬜ pending |
| 31-04-02 | 04 | 4 | D-01, D-05, D-06 | T-31-11, T-31-12 | Timeout + SIGKILL bounds any hang under 4-way contention | integration (full suite) + measurement | `JOBS=4 ./scripts/run-all-tests.sh` | ✅ existing | ⬜ pending |
| 31-04-03 | 04 | 4 | D-05, D-06 | T-31-12 | Measurement records SHA, JOBS and samples so the verdict is re-derivable | document assertion + regression | Gate-section keyword/percentage assertion + parent re-run | ✅ (artifact from 31-01-01) | ⬜ pending |
| 31-05-01 | 05 | 5 | D-04, D-05, D-06 | T-31-15 | No source edit during the checkpoint | gate-input assertion | Gate-input assertion on `31-TIMINGS.md` + clean `git status` on source dirs | ✅ (artifact from 31-04-03) | ⬜ pending (blocking checkpoint) |
| 31-05-02 | 05 | 5 | D-04 | T-31-13 | Interleaved non-Flights check survives in the parent | conditional smoke (8/8, 68/68) + 4-way diff | Concurrent four-file run + PASS-name set comparison, or `SKIPPED-BY-CHECKPOINT` | ❌ conditional | ⬜ pending |
| 31-05-03 | 05 | 5 | D-05, D-06, D-07 | T-31-14 | CI YAML confirmed unmodified for the whole phase | integration (full suite) + document assertion | `JOBS=4 ./scripts/run-all-tests.sh` + AST wiring assertion + `git status --porcelain .github/` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Decision column note.** No REQ-IDs are mapped to this phase (ROADMAP records
"Requirements: TBD"). Scope is defined by CONTEXT.md's D-01 through D-07, so the
D-IDs are the trackable references and every one of them appears above.

---

## Wave 0 Requirements

- [ ] `server/.venv` — provisioned from `server/requirements.txt` and
      `server/requirements-dev.txt`, mirroring `.github/workflows/ci.yml` lines
      78-82. **Blocking:** `scripts/run-all-tests.sh` hard-exits without it.
- [ ] Chromium installed into that venv via `python -m playwright install
      chromium`. **Blocking for correctness validation:** without it every
      browser harness returns a clean SKIP with exit 0, which would make the
      entire phase appear green while validating nothing.
- [ ] `31-BASELINE-CHECKS.txt` — the pre-split 96-check PASS/FAIL transcript.
      **Blocking and irreproducible:** it stops being obtainable the moment plan
      02 lands, and it is the only reference the Pitfall 2 comparison can diff
      against.
- [ ] `31-TIMINGS.md` pre-split section — the `JOBS=4` baseline. Same
      irreproducibility.

All four are scheduled as plan 01 task 1, which runs before any source edit in
the phase.

**No test-framework gap.** The `check()`/`EXPECTED_CHECK_COUNT` convention this
phase must follow already exists and is fully specified. The only genuinely new
validation machinery is the standalone-versus-monolith transcript comparison,
which no existing tooling performs — it is scheduled explicitly as its own task
in plans 02, 03 and 05 rather than assumed.

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| CI "test" job wall-clock reduction against the D-01 baseline | D-05 | The authoritative figure is the GitHub Actions job's own wall time, which only exists after this branch runs in CI. A local `JOBS=4` run is a proxy: it excludes checkout, venv install and the Chromium download, and runs on different hardware. | After merge, run `gh run view <run-id>` on the resulting `ci.yml` runs, average the "test" job wall time over several runs the way D-01 did, and compare against its recorded ~5min40. Revise the verdict in `31-TIMINGS.md` if the CI figure disagrees materially with the local proxy. |
| Whether to open the D-05 follow-up decomposition phase | D-05, D-06 | A judgement about risk appetite and diminishing returns, explicitly reserved to the developer by D-05 and D-06. | Plan 05 task 1's blocking `checkpoint:decision`, taken against the measured numbers in `31-TIMINGS.md`. |

Everything else in this phase has automated verification.

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify — 15 of 15, including the checkpoint,
      whose automated portion asserts its gate inputs are present and that no
      source file was edited during it.
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify —
      every task has one.
- [x] Wave 0 covers all MISSING references — the venv, Chromium, and both
      irreproducible baseline artifacts are plan 01 task 1.
- [x] No watch-mode flags — every command is a single-shot run.
- [x] Feedback latency bounded: ~80s per extracted harness, ~260s for the reduced
      parent, ~320s for the full suite. Per-task verifies run only the touched
      file, keeping the common case at the low end.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-09-22
