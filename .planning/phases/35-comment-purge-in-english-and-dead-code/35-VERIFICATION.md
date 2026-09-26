---
phase: 35-comment-purge-in-english-and-dead-code
verified: 2026-09-26T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 35: Comment purge in English and dead code Verification Report

**Phase Goal:** Comments say what the code does and why, in English, and nothing else; plan/ticket history lives in git and `.planning/`. Dead code removed. A CI guard keeps the history from coming back.
**Verified:** 2026-09-26
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Comment ratio measured before/after per file; `style.css` shipped size reported | VERIFIED | `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` has per-group before/after tables (groups 2-9) plus a "Final — whole-tree summary" section (line 778): 264→267 files, 148524→117887 lines, 39.9%→24.1% comment ratio, 9441→0 history hits. `style.css` shipped size raw/gzip before/after is recorded at line 457 and again in the Final section (line 833); 17 JS files' shipped sizes recorded at line 417/847. |
| 2 | No plan/ticket reference in any comment (CI guard green, mutation-proven) | VERIFIED | `server/.venv/bin/python scripts/check_comment_history.py check` run live against the working tree: **exit 0**, no `--paths` (scans every tracked code file, no pending/ratchet list — `scripts/comment-history-pending.txt` confirmed absent from the filesystem). 35-22-SUMMARY.md documents a 45-mutation kill sweep plus a 6-language planted-ID sweep (`# see D-06` in one file per language family, `check` exits 1 and names the file each time, reverted). Manual re-check for `TODO/FIXME/XXX/HACK/PLACEHOLDER`-style debt markers across `companion/server/stub-server/firmware/deploy/scripts` found no real hits outside test identifier names and third-party `.venv` packages. |
| 3 | English-only rule written in CLAUDE.md and CONTRIBUTING.md | VERIFIED | `.claude/CLAUDE.md` lines 46-48: "Code, identifiers, comments, docstrings, docs and commit messages are in English." plus the bilingual-UI carve-out. `CONTRIBUTING.md`'s "Code language and comments" section (line ~36) carries the same rule plus the plan/ticket-ID prohibition and cites the guard. |
| 4 | Suite green with no behaviour change | VERIFIED | Live run of `./scripts/run-all-tests.sh`: **2578 passed, 132 skipped, exit 0**, coverage 93.07% (gate 93.0%, `pyproject.toml`). `server/.venv/bin/ruff check .`: **all checks passed**. The 132 skips are Playwright browser-launch skips (`chromium_headless_shell` executable absent in this sandbox — an environment limitation, not a phase regression; 35-22-SUMMARY.md's own run with `SKYPANE_REQUIRE_BROWSER=1` in its authoring environment reports 2705 passed/5 skipped, i.e. the browser suite does exist and pass when the browser binary is present). Working tree is clean (`git status --short` empty) — nothing was modified during this verification. |

**Score:** 4/4 truths verified

### HYG Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| HYG-01 | Python comments/docstrings (prod + tests) in English, history dropped | VERIFIED | Guard passes tree-wide; spot-checked `companion/auth.py`, `companion/app.py` — no removed-feature narrative comments remain around former line markers (files have shrunk substantially, e.g. `app.py` now 2258 lines). |
| HYG-02 | `style.css` and companion JS purged | VERIFIED | Group 6/7 sections in `35-COMMENT-RATIO.md`; guard covers `.js`/`.css` (planted-ID sweep included `copy-button.js` and `style.css`). |
| HYG-03 | C/H, shell, systemd, Caddyfile, env example, sdkconfig, Kconfig, CMake, YAML/TOML comments purged | VERIFIED | Group 8/9 sections plus 35-21b's 24-file re-tightening pass (env example, Caddyfile, sdkconfig, systemd units, CI YAML, firmware shell/Kconfig) documented with before/after line counts and `same-code` proofs. |
| HYG-04 | English-only rule in CLAUDE.md and CONTRIBUTING.md | VERIFIED | Confirmed by direct read (see Truth 3 above). |
| HYG-05 | Dead code deleted: `health_page.health_severity`, `health_page.anomaly_active`, `draw.usable_pairs`, `draw.label_grid`, removed-feature comments in `app.py`/`auth.py` | VERIFIED | `grep -rn "health_severity\|anomaly_active\|usable_pairs\|label_grid"` across `.py/.js/.css` finds **no function definitions** with these names in `companion/pages/health_page.py` (functions there: `overall_severity`, `_offbox_anomaly_text`, `_anomaly_category_text`, …) or `companion/draw.py` (functions there: `grid_columns`, `grid_cell_size`, `regularity_grid`); the only remaining textual hits are a test-fixture string literal in `companion/test_suite_guards.py` (guard self-test data, never executed as a call) and unrelated local test helpers (`_anomaly_active` in `test_status_pages_01.py`, a reimplementation, not a call to the deleted function). |
| HYG-06 | CI lint guard rejecting plan/ticket IDs, mutation-proven | VERIFIED | `.github/workflows/ci.yml` lines 95-98: "Comment history guard" step runs `server/.venv/bin/python scripts/check_comment_history.py check` unconditionally, right after the blocking `ruff check .` step. Guard re-run live: exit 0. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `scripts/check_comment_history.py` | check/ratio/same-code CLI, no ratchet list | VERIFIED | `scripts/comment-history-pending.txt` absent; `check` with no args scans whole tree; live run exit 0 |
| `.github/workflows/ci.yml` | "Comment history guard" CI step | VERIFIED | present, unconditional, in lint job |
| `.claude/CLAUDE.md` / `CONTRIBUTING.md` | English-only rule text | VERIFIED | both files carry the rule |
| `.planning/phases/.../35-COMMENT-RATIO.md` | before/after ratios + style.css shipped size | VERIFIED | Final whole-tree section present with all required numbers |
| `test-support/test_check_comment_history.py` | guard's own tests, mutation-proven | VERIFIED | present; 35-22-SUMMARY.md documents 113 passing plus the 45-mutation kill sweep run against the final tree |

### Anti-Patterns Found

None outside third-party `server/.venv/` packages (not project code) and identifier names that merely contain the substring "PLACEHOLDER" (e.g. `WAKE_INTERVAL_PLACEHOLDER_TEXT`), which are legitimate code, not comment debt markers.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Comment-history guard passes on real tree | `server/.venv/bin/python scripts/check_comment_history.py check` | exit 0 | PASS |
| Lint clean | `server/.venv/bin/ruff check .` | "All checks passed!" | PASS |
| Full suite green, no behaviour change | `./scripts/run-all-tests.sh` | 2578 passed, 132 skipped (env: no Playwright browser binary), exit 0, coverage 93.07% ≥ 93.0% gate | PASS |
| Pending/ratchet mechanism removed | `ls scripts/comment-history-pending.txt` | absent | PASS |
| HYG-05 dead functions absent | `grep` for the 4 named functions as defs | no matches (only unrelated fixture/test-helper text) | PASS |

### Requirements Coverage

All of HYG-01 through HYG-06 are marked Complete in `.planning/REQUIREMENTS.md`'s checkbox list and traceability table, and each is independently confirmed above against the live tree, not just the SUMMARY narrative.

### Human Verification Required

None. All four ROADMAP success criteria and all six HYG requirements are independently verifiable from the repository and command output; no visual, real-time, or external-service behaviour is in scope for this phase.

### Gaps Summary

No gaps. One environment-only note (not a phase gap): this sandbox's Playwright install lacks the `chromium_headless_shell` binary, so browser-dependent tests skip here (132 skipped vs. the 5 skipped reported in 35-22-SUMMARY.md's `SKYPANE_REQUIRE_BROWSER=1` run in its own environment). This is a sandbox/tooling difference, not a regression introduced by this phase — the non-browser suite, ruff, and the comment-history guard all pass cleanly, and coverage clears the gate.

---

_Verified: 2026-09-26_
_Verifier: Claude (gsd-verifier)_
