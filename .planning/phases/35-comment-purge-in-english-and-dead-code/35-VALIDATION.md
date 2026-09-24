---
phase: 35
slug: comment-purge-in-english-and-dead-code
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-24
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + xdist (Phase 32 infrastructure), plus firmware host tests (`firmware/tests/run_host_tests.sh`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths` includes `test-support`) |
| **Quick run command** | `python3 scripts/check_comment_history.py same-code --base "$(git merge-base HEAD origin/main)" && python3 scripts/check_comment_history.py check && server/.venv/bin/python -m pytest test-support/test_check_comment_history.py -q` |
| **Full suite command** | `./scripts/run-all-tests.sh && server/.venv/bin/ruff check .` (firmware group adds host tests, log contract, production-config check, build) |
| **Estimated runtime** | quick ~5 s; full ~several minutes (browser tests included) |

---

## Sampling Rate

- **After every task commit:** run the quick command (same-code on changed files + guard).
- **After every plan:** run the full suite for the plan's directory (e.g. `pytest server stub-server -n auto`).
- **At each group's closing plan (one per PR):** run the full suite + ruff + shellcheck (+ firmware checks for the firmware group), measure the ratio after, shrink the pending list.
- **Before `/gsd:verify-work`:** full suite green, guard green with no pending list.
- **Max feedback latency:** ~10 s for the quick command.

---

## Per-Task Verification Map

Filled by the planner per plan. Every purge task's automated verification is the `same-code` check on its files plus the directory's pytest run. Every guard task's verification is `test-support/test_check_comment_history.py`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 35-01-* | 01 | 1 | HYG-04, HYG-06 | — | guard rejects history IDs; security-invariant comments kept | unit + mutation | `pytest test-support/test_check_comment_history.py` | ❌ W0 | ⬜ pending |
| 35-NN-* | purge plans | 2+ | HYG-01/02/03 | — | security-invariant comments survive (rewritten) | same-code + suite | quick command + directory pytest | ✅ after 35-01 | ⬜ pending |
| 35-12-* | dead code | — | HYG-05 | — | N/A | suite | `git grep -nw <name>` empty + full suite | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/check_comment_history.py`: `check`, `ratio` and `same-code` subcommands (plan 35-01)
- [ ] `test-support/test_check_comment_history.py`: pattern + mutation tests (plan 35-01)
- [ ] `scripts/comment-history-pending.txt`: the ratchet list (plan 35-01; deleted by the last plan)
- [ ] `35-BASELINE/ratio-before.tsv`: measured on the Phase-33-complete main (plan 35-01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Kept comments carry a real *why*/invariant, not a restatement | HYG-01/02/03 | Judgement | PR review per group; SUMMARY lists files still >35 % with justification |
| Firmware image behaves identically on the device | HYG-03 | Hardware | Not required: the `cpp -fpreprocessed` same-code proof plus the build shows the compiled input is unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
