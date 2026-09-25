# Phase 35: Comment purge in English and dead code - Context

**Gathered:** 2026-09-24
**Status:** Ready for planning
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (HYG-01..HYG-06, decision D-A3), the developer's phase brief for this session, the Phase 32/33 artifacts, and one question answered by the developer (tests are in scope)

<domain>
## Phase Boundary

Comments say what the code does and why, in English, and nothing else. Plan, ticket and decision history lives in git and `.planning/`. Dead code is removed. A CI guard stops the history from coming back.

- **HYG-01**: Python comments and docstrings (production **and tests**).
- **HYG-02**: `companion/static/style.css` and the companion JS files.
- **HYG-03**: C/H, shell, systemd units, Caddyfile, env example, sdkconfig, Kconfig, CMake, YAML/TOML comments.
- **HYG-04**: the English-only rule written in `.claude/CLAUDE.md` and `CONTRIBUTING.md`.
- **HYG-05**: dead code deleted. Candidates from the ledger: `health_page.health_severity`, `health_page.anomaly_active`, `draw.usable_pairs`, `draw.label_grid`, and comments about removed features (`app.py` ~3450/3514, `auth.py` ~63). Re-check each candidate against current main before deleting it.
- **HYG-06**: a CI lint guard that rejects plan/ticket IDs in comments, proven by mutation.

**Not in this phase:**
- Markdown docs (`README.md`, `ARCHITECTURE.md`, `deploy/README.md`, `server/README.md`, …) belong to Phase 41 (DOC-01..03). The one exception is `firmware/VENDOR.md`, whose provenance is rewritten concisely in the firmware wave.
- `.planning/` and `.claude/skills/`.
- Firmware dead code (FW-13) belongs to Phase 34.
- Any behaviour change. The only code (non-comment) diffs allowed are the HYG-05 deletions and the tests that exercise only the deleted functions.
</domain>

<decisions>
## Implementation Decisions

### What a comment may say (D-A3, locked)
- Keep: what the code does when it is not obvious, the *why* (constraints, trade-offs, upstream quirks), invariants, security invariants (why a check exists), units and formats, and pointers to external specs such as RFCs, datasheets or upstream APIs.
- Drop: plan/ticket/decision/review IDs (`22-08-PLAN.md Task 1`, `D-06`, `B16`, `WR-03 (19-REVIEW.md)`, `CFG-85`, `UXA-14`, `T-32-01-01`, quick-task ids like `260923-gaf`, `Phase 28`, `.planning/...` paths), change narratives ("previously…", "was removed in…", "the developer asked…"), quotes from review rounds, and restatements of the code.
- Rewrite instead of deleting when a comment mixes history with a real *why*: keep the *why* in one or two plain sentences.
- Docstrings: one summary line, plus args/returns/raises or an invariant only when they add something. A 40-line docstring over one line of code becomes one or two lines.
- English only. French quotes inside comments are dropped or translated. UI strings stay bilingual: `companion/i18n_fr/` string literals and every user-facing string literal are code, never edited in this phase.

### Must survive, rewritten concisely where needed (locked)
- License and attribution headers: SPDX lines, Apache-2.0 upstream attribution (FlightPortrait, YODE PTE LTD), `NOTICE`, `firmware/NOTICE`, `firmware/LICENSE`, and the `firmware/VENDOR.md` provenance.
- Tool pragmas, exactly as they are: `# noqa`, `# type: ignore`, `# pragma: no cover`, `# shellcheck …`, `# fmt: …`, `# ruff: …`, shebangs, encoding lines.
- Semantic "comments": `# CONFIG_X is not set` in `sdkconfig*` files is configuration, not a comment.
- Module docstrings read at runtime (`argparse.ArgumentParser(description=__doc__)` in `companion/app.py`, `deploy/backup/backup_gate.py`, `deploy/backup/skypane_backup.py`, `server/plane/illustrations.py`) are `--help` text. They may be trimmed of history but stay accurate help text, and the plan owning the file records the change.
- Text that a check or test greps: `firmware/tests/check_log_contract.sh` greps `app_main.c`, `state_machine.c` and `VENDOR.md`. Log format strings are code anyway, but check that no grepped line is a comment.

### Scope includes tests (developer decision, 2026-09-24)
- The purge and the guard cover test files too: `server/test_*`, `stub-server/test_*`, `companion/test_*`, `companion/conftest.py`, `conftest.py`, `test-support/`, `deploy/tests/`, `firmware/tests/`.
- Test **function names stay unchanged**, because the Phase 32/33 migration ledgers reference node ids. Assertion-message string literals are code: they may keep an ID, and the guard does not scan them.

### Execution gates (locked)
- **G-33:** no plan runs before Phase 33 is complete on `main`: all 33 SUMMARYs are present, `33-VERIFICATION.md` has status passed, and ROADMAP marks Phase 33 complete. The first plan checks this before doing anything else. It also checks that no remaining test reads source files or comments: `companion/test_suite_guards.py` is green, and a grep over every `test_*.py`, `conftest.py` and `test-support/` file (all directories, not only companion) finds no read of a production source file as text. Any hit outside companion (for example a server or deploy test that greps a comment) is fixed or recorded before the purge touches that file.
- **G-34:** the firmware wave (C, H, sdkconfig, Kconfig, CMake, firmware shell, `VENDOR.md`) runs only after plan 34-11 is complete on `main` (`34-11-SUMMARY.md` present, Phase 34 marked complete). It is the last purge wave.
- **One writer per file per wave.** Plans in the same wave have disjoint `files_modified`.
- **One PR per directory group,** so each PR stays reviewable. The groups: (1) foundation, (2) server/, (3) stub-server/, (4) companion Python production, (5) companion tests + test-support, (6) companion static JS, (7) style.css, (8) deploy/ + scripts/ + .github/ + root config + adsb-test/ + hardware/ scripts, (9) firmware + phase close.
- Merge `main` into the working branch before each PR. When STATE.md or ROADMAP.md conflict, keep both sides.

### Proof of "no behaviour change" (locked; every group)
- Full pytest suite green (`./scripts/run-all-tests.sh`), `ruff check .` green, `shellcheck` on deploy scripts green, and for the firmware group: `firmware/tests/run_host_tests.sh`, `check_log_contract.sh`, `check_production_config.sh static`, and `firmware/build.sh`.
- A mechanical **same-code check** against the group's base commit, run on every changed file:
  - Python: AST equal once docstrings are removed.
  - C/H: `cpp -fpreprocessed -P` output equal.
  - JS/CSS: token stream equal once comments are removed.
  - Hash-comment formats: non-comment lines equal.
  - Pragmas and SPDX lines: same multiset before and after.
  The only files allowed to differ are those listed explicitly for HYG-05 or runtime `__doc__`.
- Comment ratio measured per file before and after, and recorded in `35-COMMENT-RATIO.md`. The `style.css` shipped size is reported raw and gzip, before and after.
- Coverage does not drop below the gate in `pyproject.toml`. Deleting dead code can only raise it.

### HYG-06 guard (locked shape, details are Claude's discretion)
- A stdlib-only Python script run in CI next to `ruff`. It extracts comments and docstrings per language and fails on history IDs. Its tests live in `test-support/`.
- **Ratchet rollout:** the guard lands in wave 1 with an explicit pending list of the paths not yet purged. Each group's closing plan removes its paths. The last plan deletes the pending mechanism, so the guard covers every tracked code file.
- **Mutation-proven:** for every pattern, a test plants it in each comment syntax and asserts the guard fails. Removing any alternative from the pattern makes a test fail (recorded in SUMMARY). IDs in string literals and code are never flagged. A planted ID in a real file makes the CI step exit non-zero.
- No inline suppression pragma. A false positive is fixed by narrowing the pattern and adding a test for the legitimate text, for example `SHA-256`, `UTF-8`, ISO dates, `runway-02-20.png`, numeric ranges.

### Claude's Discretion
- The internal design of the guard/ratio/same-code tool (one script with subcommands is suggested), exact regexes (tuned against the tree), and plan splits within a group as long as files stay disjoint.
- A file still above ~35 % comment lines after its purge is a review trigger, not a failure. The SUMMARY says why its comments earn their place.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md`: D-A3, HYG-01..06, FW-13 (not this phase)
- `.planning/REQUIREMENTS.md`: HYG-01..06
- `.planning/ROADMAP.md`: Phase 35 success criteria
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-CONTEXT.md`: TST-12 behaviour-over-source-text rule; `companion/test_suite_guards.py` (G1..G6)
- `scripts/check-attribution.sh`: existing CI guard pattern
- `.github/workflows/ci.yml` (lint job: ruff, shellcheck), `.github/workflows/firmware.yml`
- `pyproject.toml`: pytest/coverage/ruff config, `testpaths`
- `firmware/VENDOR.md`, `firmware/NOTICE`, `NOTICE`: provenance to keep
</canonical_refs>

<specifics>
## Specific Ideas

- Cost discipline: this is a mechanical phase. Reuse Phase 32/33 patterns and keep agent fan-out small.
- Commit messages are in English.
</specifics>

<deferred>
## Deferred Ideas

- Markdown docs purge and correction: Phase 41.
- `.claude/skills/sketch-findings-skypane` history: not source; out of scope.
</deferred>
