---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
verified: 2026-09-22T22:10:00Z
status: passed
score: 9/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Push this branch and read a real `gh run view` timing for the CI \"test\" job (at least one real run), comparing against D-01's ~340s baseline."
    expected: "A materially faster wall time (D-06's bar — no fixed target). 31-TIMINGS.md's own local-proxy estimate ranges 9.1%-29.6% job-level (mean 22.4%, median 28.7%) across five samples, missing D-05's 30-40% gate on every sample; the phase's own closing verdict explicitly asks for this to be \"re-checked on the first real CI run ... and revised if the CI figure disagrees materially.\""
    why_human: "Local timing on a 10-core Apple Silicon host is explicitly documented in 31-TIMINGS.md as a proxy, not a CI measurement — the actual GitHub Actions runner (4 vCPUs) is the only environment that can produce the authoritative number, and this branch had not yet been run in CI at verification time."

  - test: "On that same real CI run, confirm the pool-contention finding (three simultaneous Chromium-launching harnesses now share the 4-worker pool where only one used to) does not degrade test-job reliability — i.e. check for new timeouts/failures on the non-browser harnesses that were measured slowing 22-77% locally with zero code changes."
    expected: "24/24 harnesses pass in CI, with no new intermittent failures beyond the three already-documented, pre-existing ARM64/macOS-only Chromium flakes (which do not reproduce on Linux amd64, i.e. real CI)."
    why_human: "Contention behavior is resource/scheduler-dependent and cannot be observed from a local macOS host or from grep/static analysis — it can only be confirmed by watching several real CI runs for flakiness, which is exactly the class of risk this phase's own TIMINGS.md flags as unresolved without a real run."
---

# Phase 31: CI test suite — parallelize companion/test_browser_ux.py Verification Report

**Phase Goal:** Reduce the CI "test" job's wall-clock time by making `companion/test_browser_ux.py` run in true parallel instead of as one sequential ~300s+ script, without losing coverage or introducing flakiness (per ROADMAP.md's Phase 31 entry).
**Verified:** 2026-09-22
**Status:** human_needed
**Re-verification:** No — initial verification

## Note on requirement-ID sourcing

ROADMAP.md's own Phase 31 entry states `Requirements: TBD (scope defined by 31-CONTEXT.md's D-01 through D-07)`, and `.planning/REQUIREMENTS.md` has no Phase 31 section (it tracks user-facing v1 requirements — PLANE-\*, DEVICE-\*, CFG-\* — not test-infrastructure work). This is expected for an infra phase, not an omission: D-01 through D-07 in `31-CONTEXT.md` are the authoritative must-haves for this phase, and every PLAN's `requirements:` frontmatter field cites a subset of them. No orphaned requirement IDs exist because REQUIREMENTS.md was never meant to carry this phase's scope.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pre-split baseline (JOBS=4 timing + 96-check PASS/FAIL transcript) measured and recorded (D-01/D-02/D-03) | VERIFIED | `31-TIMINGS.md` "Pre-split baseline" section: 240.9s local proxy, 5 real CI figures (300.9-318.7s) cross-referenced; `31-BASELINE-CHECKS.txt` exists (53,895 bytes) as the 96-check per-check transcript |
| 2 | `companion/test_browser_ux_helpers.py` exists as a pure shared module (no `main()`, no `EXPECTED_CHECK_COUNT`), and cross-group-coupled helpers (`_quiet_arc_minutes`, `_handle_sel`) were promoted there | VERIFIED | `grep -n "^def main\|EXPECTED_CHECK_COUNT\s*=" companion/test_browser_ux_helpers.py` returns nothing; file docstring states "This is NOT a harness"; all three consumer files import from it (`from companion.test_browser_ux_helpers import (`) |
| 3 | 2 of the planned 2-3 largest scenario groups extracted into independently-runnable, pattern-consistent standalone harnesses (D-04) | VERIFIED | `companion/test_browser_ux_health_drawings.py` (own `Harness()`, own subprocess) and `companion/test_browser_ux_quiet_wake.py` (same pattern) both exist; ran each standalone in this verification: `browser-ux-health-drawings: 11/11 checks pass` and `browser-ux-quiet-wake: 9/9 checks pass` |
| 4 | Extracted harnesses skip cleanly (exit 0) when Playwright/Chromium is unavailable, matching every other harness's contract | VERIFIED | Both new files contain the identical `except ImportError: ... "SKIP ... playwright not installed"` clean-skip pattern (lines ~76-92 of each) |
| 5 | Original file's check count re-derived by running (not paper arithmetic), landing at 76/76 after both extractions | VERIFIED | `grep -c "^\s*check("` on `companion/test_browser_ux.py` = 76; live `EXPECTED_CHECK_COUNT = 76` is the last assignment before `main()`'s gate; matches 31-02/31-03-SUMMARY.md's own re-derivation record |
| 6 | Total 96 checks conserved across the split — no coverage lost | VERIFIED | 76 + 11 + 9 = 96 (independently counted, not copied from SUMMARY); `31-TIMINGS.md`'s `linux/amd64` Docker run reports `96/96` conserved and `TOTAL 7829 517 93%` coverage, above the 83% `fail_under` floor in `pyproject.toml` |
| 7 | Extracted files registered in `HARNESSES` and `EXPECTED_SLOWEST`; mechanism is exclusively the existing local worker pool — zero `.github/workflows/ci.yml` changes (D-07) | VERIFIED | AST count: `HARNESSES` = 24 entries, `EXPECTED_SLOWEST` = 10 entries, both new files present in both; `git diff main...HEAD --stat -- .github/` is empty |
| 8 | The split does not introduce new flakiness — correctness is proven on the CI-matching architecture, and the only observed native failures are pre-existing, already-documented environmental flakes | VERIFIED | `31-TIMINGS.md`'s `linux/amd64` Docker run (matching `ubuntu-latest`) is clean 96/96 across all three files; the orchestrator's independent full-suite regression check (JOBS=4, native ARM64) reproduced exactly the 3 pre-existing Ctrl+A/DOM-detach flakes already root-caused in plans 01/03/04's SUMMARYs, no new failure |
| 9 | D-05's wall-time gate was actually measured (not asserted), and the phase closes with an explicit written verdict + follow-up recommendation, honoring D-06's diminishing-returns doctrine; the Flights checkpoint decision is recorded faithfully | VERIFIED | `31-TIMINGS.md`'s "Phase 31 Closing Verdict" section: 5 independent local samples (9.1%-29.6% job-level estimate, mean 22.4%, median 28.7%) against the 30-40% bar, explicit "MISSED" verdict, explicit recommendation against opening a follow-up phase; `companion/test_browser_ux_flights.py` correctly does NOT exist, `git status --porcelain companion/ scripts/` clean per 31-05-SUMMARY.md, and 31-05-SUMMARY.md records the developer's verbatim reasoning for `skip-flights` |
| 10 | The CI "test" job is actually materially faster in real CI (not just local proxy), and the pool-contention mechanism (3 simultaneous Chromium harnesses in a 4-worker pool) does not introduce new flakiness on the real, more resource-constrained runner | Present, not confirmed — routed to human verification | `31-TIMINGS.md` itself flags this as unresolved: "This branch ... has not yet been pushed, so no real CI number exists for it at the time this verdict was written. This verdict should be re-checked on the first real CI run." No `gh run view` evidence for this branch was available to check |

**Score:** 9/10 truths verified programmatically; 1 requires a real CI run to close (see Human Verification below).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `companion/test_browser_ux_helpers.py` | Pure shared helper module, no harness surface | VERIFIED | 2,687 lines, imports cleanly, no `main()`/`EXPECTED_CHECK_COUNT` |
| `companion/test_browser_ux_health_drawings.py` | Standalone 11-check harness | VERIFIED | Own `Harness()`, ran standalone — 11/11 pass |
| `companion/test_browser_ux_quiet_wake.py` | Standalone 9-check harness | VERIFIED | Own `Harness()`, ran standalone — 9/9 pass |
| `companion/test_browser_ux.py` (reduced) | 76-check parent, imports from helpers module | VERIFIED | 76 `check()` calls, `EXPECTED_CHECK_COUNT = 76` |
| `companion/test_browser_ux_flights.py` | Conditional — only if checkpoint selected extract-flights | CORRECTLY ABSENT | Checkpoint selected `skip-flights`; file does not exist, matching the deliberate no-op |
| `scripts/run_all_tests.py` (`HARNESSES`/`EXPECTED_SLOWEST`) | 24 / 10 entries respectively | VERIFIED | AST-counted directly: 24 / 10 |
| `31-BASELINE-CHECKS.txt` | Pre-split 96-check transcript | VERIFIED | Exists, 53,895 bytes |
| `31-TIMINGS.md` | Pre-split + post-split + closing verdict sections | VERIFIED | All three sections present with real numbers, Docker correctness proof, five-sample D-05 arithmetic |
| `.github/workflows/ci.yml` | Unchanged | VERIFIED | `git diff main...HEAD -- .github/` empty |
| `pyproject.toml` `[tool.coverage.run]` | Unchanged omit glob (new files auto-omitted) | VERIFIED | `companion/test_*.py` glob unchanged, matches all three affected files |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `companion/test_browser_ux.py` | `companion.test_browser_ux_helpers` | `from ... import (...)` | WIRED | Import present at line 103; file runs (verified via independent per-harness spot checks and the orchestrator's full-suite run) |
| `companion/test_browser_ux_health_drawings.py` | `companion.test_browser_ux_helpers` | `from ... import (...)` | WIRED | Import present; standalone run passes 11/11, proving no `NameError` |
| `companion/test_browser_ux_quiet_wake.py` | `companion.test_browser_ux_helpers` | `from ... import (...)` | WIRED | Import present; standalone run passes 9/9 |
| `scripts/run_all_tests.py` `HARNESSES`/`EXPECTED_SLOWEST` | new harness files | list entries | WIRED | Both new file paths present in both lists (AST-verified); a file merely existing without a `HARNESSES` entry would be invisible to CI — not the case here |
| `companion/test_companion_app.py` (`VIEW_TRANSITION_ROUTES` AST check) | `companion/test_browser_ux_helpers.py` | AST parse retarget | WIRED (cosmetic warning only) | 31-REVIEW.md WR-01: retarget is functionally correct (parses the right file), but two failure-message strings still say the old filename — cosmetic, non-blocking, no code-review critical/blocker findings |

### Requirements Coverage (D-01 through D-07, per 31-CONTEXT.md)

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| D-01 | Measured CI baseline (~5min40 job, 300-320s for the target file) | SATISFIED | Recorded in `31-TIMINGS.md`, cross-referenced against real `gh run view` figures |
| D-02 | Informational — structural cost, not fixed sleeps | SATISFIED (background) | Documented in `31-CONTEXT.md`; motivated the extraction approach, no standalone action required |
| D-03 | Informational — known accepted tradeoff, first attempt to fix | SATISFIED (background) | Framing only, no standalone action required |
| D-04 | Incremental extraction of 2-3 largest scenario groups | SATISFIED | 2 extracted (health-drawings 11, quiet-wake 9); third (Flights) explicitly and deliberately skipped at the plan-05 checkpoint — within D-04's stated 2-3 range |
| D-05 | ~30-40% wall-time reduction gate, decides whether to open a follow-up phase | MEASURED, GATE MISSED, DECISION HONORED | Five local-proxy samples (9.1%-29.6%), explicit "MISSED" verdict recorded in `31-TIMINGS.md`; developer's checkpoint decision to stop (not open a follow-up phase) recorded verbatim in `31-05-SUMMARY.md` — real CI confirmation still outstanding, see Human Verification |
| D-06 | No fixed target; stop at diminishing returns | SATISFIED | Explicitly invoked as the reasoning for the `skip-flights` decision; pool-contention finding documented as the concrete diminishing-returns evidence |
| D-07 | Join existing local worker pool; zero CI YAML changes | SATISFIED | `HARNESSES`/`EXPECTED_SLOWEST` updated; `git diff` on `.github/` empty at every plan boundary per `31-05-SUMMARY.md`'s own claim, independently re-confirmed here |

No orphaned requirement IDs — every ID in `31-CONTEXT.md`'s `<decisions>` block is cited by at least one plan's `requirements:` frontmatter, and this phase does not map to any `.planning/REQUIREMENTS.md` row (see note above).

### Anti-Patterns Found

None. Scanned all five phase-touched files (`companion/test_browser_ux.py`, `companion/test_browser_ux_health_drawings.py`, `companion/test_browser_ux_helpers.py`, `companion/test_browser_ux_quiet_wake.py`, `scripts/run_all_tests.py`) plus `pyproject.toml` for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" — zero debt markers. The handful of "placeholder" string hits in `test_browser_ux.py`/`test_browser_ux_helpers.py` are legitimate domain terms (i18n placeholder text, UI "no data" chips), not stub markers.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Health-drawings harness runs standalone and passes its full count | `server/.venv/bin/python3 companion/test_browser_ux_health_drawings.py` | `browser-ux-health-drawings: 11/11 checks pass` | PASS |
| Quiet-wake harness runs standalone and passes its full count | `server/.venv/bin/python3 companion/test_browser_ux_quiet_wake.py` | `browser-ux-quiet-wake: 9/9 checks pass` | PASS |
| All five phase-touched files compile cleanly | `python3 -m py_compile companion/test_browser_ux.py companion/test_browser_ux_health_drawings.py companion/test_browser_ux_quiet_wake.py companion/test_browser_ux_helpers.py scripts/run_all_tests.py` | `ALL COMPILE OK` | PASS |
| No CI workflow file changed anywhere in the phase's commit range | `git diff main...HEAD --stat -- .github/` | (empty) | PASS |
| Full suite regression (orchestrator, independent of this report) | `JOBS=4 ./scripts/run-all-tests.sh` (native ARM64) | 23/24 harnesses pass; the one failure reproduces exactly the 3 pre-existing, documented ARM64/macOS flakes (2x Ctrl+A, 1x DOM-detach), not a new regression | PASS (per orchestrator's independently-run regression check, cross-checked against 31-01/31-03/31-04-SUMMARY.md's root-cause record) |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` files; its "probes" are the harnesses themselves, covered under Behavioral Spot-Checks above.

### Human Verification Required

### 1. Real CI wall-time confirmation

**Test:** Push this branch (or merge to a branch that triggers `ci.yml`) and read at least one real `gh run view` timing for the "test" job, comparing against D-01's ~340s baseline the same way D-01 itself was measured.
**Expected:** A materially faster wall time (D-06's bar). The phase's own local-proxy evidence (5 samples, 9.1%-29.6% job-level estimate, missing D-05's 30-40% gate on every sample) is the best evidence available today, but `31-TIMINGS.md` explicitly asks for this to be checked against a real number before the verdict is treated as final.
**Why human:** Only the actual GitHub Actions runner (4 vCPUs, different scheduler characteristics than the 10-core local host used for every measurement in this phase) can produce this number. No `gh run view` data exists for this specific branch yet.

### 2. Real-CI flakiness check under pool contention

**Test:** On that same real CI run (ideally 2-3 runs), confirm no new intermittent failures appear on the non-browser harnesses that plan 04 measured slowing 22-77% locally once three Chromium-launching harnesses joined the same 4-worker pool.
**Expected:** 24/24 harnesses pass, with failures (if any) limited to the three already-documented ARM64/macOS-only flakes — which should not even reproduce on Linux, the real CI OS.
**Why human:** Resource contention under a real scheduler is not observable from static analysis or from a local macOS host; it requires watching actual CI runs.

### Gaps Summary

No structural gaps. Every artifact the phase's plans committed to exists, is substantive, and is wired: the shared helper module is pure, both extractions are independently runnable and were re-verified standalone in this report (11/11 and 9/9), the reduced parent is provably still 76/76 by direct count, the 96-check total is conserved with coverage above threshold, the worker-pool registration is correct and `.github/workflows/ci.yml` was never touched, and the optional third extraction's absence is a deliberate, faithfully-recorded checkpoint decision rather than an unfinished task.

The one open item is empirical, not structural: D-05's wall-time gate was measured as MISSED on every local-proxy sample, and the phase's own closing verdict explicitly says that call should be revisited against a real CI number once this branch has actually run in GitHub Actions — which has not happened yet. This is not treated as a phase failure (per the explicit human decision already made at the plan-05 checkpoint, and D-06's sanction to stop at diminishing returns), but it is exactly the kind of "real-time behavior / external service" fact that only a human watching an actual CI run can close out. Recorded as human-verification items above rather than as gaps.

---

_Verified: 2026-09-22_
_Verifier: Claude (gsd-verifier)_
