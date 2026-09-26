---
phase: 35-comment-purge-in-english-and-dead-code
plan: 21b
subsystem: infra
tags: [comment-hygiene, ci-guard, systemd, firmware, deploy]

# Dependency graph
requires:
  - phase: 35-comment-purge-in-english-and-dead-code (35-21)
    provides: "groups 1-9 purged; scripts/check_comment_history.py CLI"
  - commit: dbc1c28
    provides: "same-code fix: blank/comment-only lines are ignored in hash-comment files, so a comment can shrink instead of only reword"
provides:
  - "The 24 highest comment-ratio #-comment files re-tightened now that same-code allows shortening, not just rewording"
  - "Two stale/broken comments fixed in passing (Rule 1): sdkconfig.ee02.defaults' 'NOT YET CONFIRMED ON LIVE HARDWARE' panel-pin claim, and a dangling unmatched-parenthesis/incomplete-sentence fragment in ci.yml and deploy.sh"
affects: [35-22]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "deploy/tests/test_units.py asserts IPAddressDeny/IPAddressAllow are absent from two units by literal substring match on the whole unit file text -- a tightened comment must avoid spelling those directive names even when describing their absence"
    - "The pragma-preservation check (_PRAGMA_RE) matches any comment line starting with '# shellcheck', not just real shellcheck directives -- a prose sentence that happens to start that way must stay byte-identical or be reworded to not start with the word shellcheck"

key-files:
  created: []
  modified:
    - deploy/skypane.env.example, deploy/Caddyfile, firmware/sdkconfig.ee02.defaults
    - pyproject.toml, server/requirements-dev.in, .gitignore
    - deploy/render_caddyfile.sh, scripts/run-all-tests.sh, deploy/deploy.sh
    - .github/workflows/ci.yml, .github/workflows/firmware.yml
    - deploy/provision.sh, scripts/lock-deps.sh, firmware/sdkconfig.defaults
    - deploy/skypane-companion.service, deploy/skypane-byos.service, deploy/skypane-poll.service, deploy/skypane-backup.service
    - deploy/backup/install-backup-key.sh, firmware/monitor.sh
    - firmware/main/Kconfig.projbuild, firmware/build.sh, firmware/flash.sh, firmware/provision.sh

key-decisions:
  - "Kconfig `help` text is not a `#`-comment (extract_hash only extracts real # lines), so it is out of scope for this pass; only firmware/main/Kconfig.projbuild's one #-comment block was tightened, leaving the dense datasheet/provenance help text from earlier plans untouched"
  - "Dropped skypane-byos.service's stale 'a future plan (Wave B) adds --bind/IPAddressDeny' forward-looking note: deploy/README.md's 'Known vendored behaviour' section already documents the firewall-layer mitigation as the accepted, verified end state, not a pending gap"
  - "Reworded (not deleted) the two 'no IP filter' comments in skypane-companion.service/skypane-poll.service after they first broke deploy/tests/test_units.py::test_companion_and_poll_have_no_ip_filter by literally containing the substring IPAddressDeny"

requirements-completed: []

# Metrics
duration: 20min
completed: 2026-09-26
---

# Phase 35 Plan 21b: Post-fix comment tightening pass Summary

**Re-tightened the 24 `#`-comment files with the highest comment ratio now that `same-code` (fixed in dbc1c28) ignores blank/comment-only lines, cutting 534 comment lines (1153 -> 619, a 46% reduction) across 8 commits with zero code-line changes proven by `same-code --base dbc1c28` on every file.**

## Why this plan exists

Earlier purge plans in this phase (through 35-21) edited these same files while `_hash_code_lines` still kept a positional blank for every comment line it touched — deleting a comment line shifted every later line's index and failed `same-code`, so those plans could only **reword** comments in `.sh`/`.service`/`.yml`/`.toml`/sdkconfig/Kconfig files, never shorten them. Commit `dbc1c28` (this same session, immediately before this plan) fixed that: blank and comment-only lines are now dropped before comparison. This plan re-visits the files with the worst resulting comment-to-code ratio and applies the caps (file header <= 8 lines, any comment block <= 4 lines) that were previously unreachable.

## Files: before -> after comment lines (of total lines)

| File | Before (comment/total) | After (comment/total) |
|---|---|---|
| deploy/skypane.env.example | 88/108 | 42/62 |
| deploy/Caddyfile | 100/126 | 31/57 |
| firmware/sdkconfig.ee02.defaults | 82/106 | 42/69 |
| pyproject.toml | 132/179 | 46/93 |
| server/requirements-dev.in | 22/32 | 18/28 |
| .gitignore | 39/61 | 29/51 |
| deploy/render_caddyfile.sh | 39/68 | 15/45 |
| scripts/run-all-tests.sh | 37/68 | 23/55 |
| deploy/deploy.sh | 33/61 | 22/51 |
| .github/workflows/ci.yml | 146/286 | 62/202 |
| deploy/provision.sh | 102/224 | 58/181 |
| scripts/lock-deps.sh | 22/51 | 13/42 |
| firmware/sdkconfig.defaults | 32/79 | 30/77 |
| deploy/skypane-companion.service | 31/80 | 15/64 |
| deploy/backup/install-backup-key.sh | 25/66 | 20/62 |
| firmware/monitor.sh | 16/43 | 14/42 |
| deploy/skypane-byos.service | 26/76 | 8/58 |
| .github/workflows/firmware.yml | 27/84 | 18/75 |
| deploy/skypane-poll.service | 13/57 | 11/55 |
| deploy/skypane-backup.service | 17/59 | 8/50 |
| firmware/main/Kconfig.projbuild | 12/241 | 9/238 |
| firmware/build.sh | 32/106 | 23/98 |
| firmware/flash.sh | 23/129 | 16/123 |
| firmware/provision.sh | 57/266 | 46/256 |
| **Total (24 files)** | **1153/2656 (43.4%)** | **619/2134 (29.0%)** |

Ratios computed with `server/.venv/bin/python scripts/check_comment_history.py ratio <files>` against `git show dbc1c28:<file>` (before) and the working tree (after).

## What was kept verbatim

- Every SPDX/copyright header and Apache-2.0 attribution line.
- Every `# CONFIG_X is not set` sdkconfig line and every Kconfig symbol/`default`/`depends on` line (none needed removing; the one `#`-comment block in Kconfig.projbuild was tightened, its `help` text left alone as out of scope — see key-decisions).
- Every `# shellcheck ...`, `# noqa`, `# fmt:`, `# ruff:`, `# pragma: no cover` pragma and every shebang, byte-for-byte where the pragma checker's line-start match required it (one `# shellcheck is preinstalled...` sentence in ci.yml had to stay unedited on its own line because the checker treats any `# shellcheck...`-prefixed line as a pragma to preserve verbatim, regardless of intent).
- The two CI `env:` command-injection-prevention comments (SSH host key, deploy target) and every systemd hardening directive's "why", per this project's `CLAUDE.md`.
- All file modes, ownership, ufw rules, ExecStart commands, esptool/docker flags, partition offsets, action-pin SHAs, secrets names, and coverage/lint thresholds — no directive, value or key changed anywhere.

## Auto-fixed issues (Rule 1)

1. **`firmware/sdkconfig.ee02.defaults`**: header claimed panel pins were "NOT YET CONFIRMED ON LIVE HARDWARE," contradicted by `hardware/BRINGUP-LOG.md`'s "Board Profile Verification: VERIFIED — 2026-08-25." Corrected while tightening the same paragraph.
2. **`firmware/sdkconfig.defaults`**: dropped a stale "not introduced until plan 01-05" cross-reference — `main/Kconfig.projbuild` has long existed in the tree.
3. **`deploy/deploy.sh`**: removed a dangling, grammatically incomplete trailing clause ("...so a failed activation turns this script red too, and so the CI job.") left over from an earlier edit that could only reword, not delete.
4. **`.github/workflows/ci.yml`**: fixed an unmatched open-parenthesis in the venv-install step's comment, from the same earlier-edit limitation.
5. **`deploy/skypane-byos.service`**: dropped a stale "a future plan (Wave B) adds --bind/IPAddressDeny" forward-looking note; `deploy/README.md`'s own "Known vendored behaviour" section documents the current firewall-layer mitigation as the accepted, verified state.

## Verification

- `server/.venv/bin/python scripts/check_comment_history.py same-code --base dbc1c28 <all 24 changed files>` — exit 0 (no code-line differs from the pre-fix base).
- `server/.venv/bin/python scripts/check_comment_history.py check` (whole tree, no `--paths`) — exit 0.
- `server/.venv/bin/ruff check .` — all checks passed.
- `./scripts/run-all-tests.sh` — full suite green twice: once right after the pyproject.toml/`.gitignore`/deps edits (2695 passed, 5 skipped, coverage 93.24%), and again as the final all-files-done confirmation (2695 passed, 5 skipped, exit code 0, 261s).
- `./firmware/tests/run_host_tests.sh` — 10/10 hardware-free suites pass.
- `sh firmware/tests/check_log_contract.sh` and `sh firmware/tests/check_production_config.sh static` — both PASS, re-run after every firmware-adjacent commit.
- `systemd-analyze security --offline=true --threshold=20` on all four `deploy/*.service` files — all below threshold (0.8-1.5), matching CI's gate.
- `bash -n` / `sh -n` on every changed shell script — all pass.
- `python3 -c "import yaml; yaml.safe_load(...)"` on both changed workflow files, and `tomllib.load(...)` on `pyproject.toml` — both parse.
- `pytest deploy -n auto` re-run after each of the two systemd/service-file edits (the wording collision with `test_companion_and_poll_have_no_ip_filter` was caught and fixed before its commit) — 131/131 passed each time.

## Commits

1. `a8f758a` — env template, Caddyfile, EE02 sdkconfig
2. `d0d33a3` — pyproject.toml, dev deps, .gitignore
3. `cf8085f` — deploy/render_caddyfile.sh, run-all-tests.sh, deploy.sh
4. `0add64c` — ci.yml, firmware.yml
5. `39b7468` — provision.sh, lock-deps.sh, sdkconfig.defaults
6. `8038ba2` — the four systemd unit files
7. `f1bead5` — install-backup-key.sh, monitor.sh
8. `2bd30d7` — build.sh, flash.sh, provision.sh, Kconfig.projbuild

(This SUMMARY's own commit follows as the plan-metadata commit, per the objective's instruction that this plan has no PLAN.md.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale hardware-confirmation claim in sdkconfig.ee02.defaults**
- **Found during:** tightening the EE02 panel-pin comment block
- **Issue:** header said panel pins were "NOT YET CONFIRMED ON LIVE HARDWARE"; `hardware/BRINGUP-LOG.md` already records them VERIFIED (2026-08-25)
- **Fix:** corrected the claim while shortening the same paragraph
- **Files modified:** firmware/sdkconfig.ee02.defaults
- **Verification:** cross-checked BRINGUP-LOG.md's "Board Profile Verification" section before editing; `check_production_config.sh static` and `check_log_contract.sh` still pass
- **Committed in:** a8f758a

**2. [Rule 1 - Bug] Stale plan cross-reference in sdkconfig.defaults**
- **Found during:** tightening the FlightPortrait-settings comment block
- **Issue:** comment said the CONFIG_FP_* namespace "is not introduced until plan 01-05" — that file has existed in the tree for many phases
- **Fix:** dropped the stale forward reference
- **Files modified:** firmware/sdkconfig.defaults
- **Committed in:** 39b7468

**3. [Rule 1 - Bug] Dangling incomplete sentence in deploy.sh**
- **Found during:** tightening the "why git archive" header paragraph
- **Issue:** trailing clause "...so a failed activation turns this script red too, and so the CI job." is grammatically incomplete (missing a verb)
- **Fix:** dropped the fragment when condensing the paragraph
- **Files modified:** deploy/deploy.sh
- **Committed in:** cf8085f

**4. [Rule 1 - Bug] Unmatched parenthesis in ci.yml step comment**
- **Found during:** tightening the "Create virtualenv" step comment
- **Issue:** an opening "(installing it alone with --require-hashes pulls in..." was never closed
- **Fix:** rewrote the sentence without the dangling paren
- **Files modified:** .github/workflows/ci.yml
- **Committed in:** 0add64c

**5. [Rule 1 - Bug] Stale forward-looking note in skypane-byos.service**
- **Found during:** tightening the [Unit] access-control comment
- **Issue:** "a future plan (Wave B) adds a --bind flag and IPAddressDeny/IPAddressAllow" is contradicted by deploy/README.md's own documentation of the current firewall-layer approach as the accepted, verified end state
- **Fix:** dropped the stale forward reference
- **Files modified:** deploy/skypane-byos.service
- **Committed in:** 8038ba2

**6. [Rule 1 - Bug] Comment wording collided with a test's substring assertion**
- **Found during:** verifying the systemd unit files commit (`pytest deploy`)
- **Issue:** the first draft of the tightened "no IP filter" comments in skypane-companion.service and skypane-poll.service literally spelled "IPAddressDeny", which `deploy/tests/test_units.py::test_companion_and_poll_have_no_ip_filter` asserts is absent from those two unit files (it checks the whole file text, not just directive lines)
- **Fix:** reworded to "No systemd IP address allow-list filter here" (matching the pre-existing style), re-ran `pytest deploy -n auto` to confirm
- **Files modified:** deploy/skypane-companion.service, deploy/skypane-poll.service
- **Verification:** `pytest deploy -n auto` — 131/131 passed after the reword
- **Committed in:** 8038ba2

---

**Total deviations:** 6 auto-fixed (5 Rule 1 stale/broken comment fixes, 1 Rule 1 test-collision fix caught before commit)
**Impact on plan:** All fixes are corrections to comment text only (no behaviour or directive changed); none expand scope beyond the tightening objective.

## Issues Encountered

- The `_PRAGMA_RE` pragma-preservation check in `check_comment_history.py` matches any comment line starting with the literal text `# shellcheck`, not only genuine `# shellcheck disable=...` directives. `.github/workflows/ci.yml`'s "shellcheck is preinstalled on the ubuntu-24.04 runner image" sentence happens to start that way, so `same-code` required that exact line to stay byte-identical; caught by running `same-code` before committing, fixed by keeping that one line unedited and compressing only the following lines.
- `deploy/tests/test_units.py::test_companion_and_poll_have_no_ip_filter` asserts a literal substring is absent from two unit files' full text; the first draft of a shortened comment tripped it (see deviation 6 above). Caught by running `pytest deploy -n auto` before the commit, as required.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 35-22 (the phase's final closing plan) can proceed: this plan touched none of the files 35-22 itself modifies (`scripts/check_comment_history.py`, `scripts/comment-history-pending.txt`, `test-support/test_check_comment_history.py`), and `check_comment_history.py check` with no arguments still exits 0 over the whole tree.
- `35-COMMENT-RATIO.md` was not updated by this plan (it is not a `#`-comment file and was outside this plan's explicit file list); 35-22's own "final ratio table" task will pick up these files' new, lower ratios when it re-runs `ratio --before 35-BASELINE/ratio-before.tsv --markdown` over the whole tree.
- No blockers. No PR was opened and nothing was pushed by this plan, matching prior plans' convention that the orchestrator owns that step.

## Self-Check: PASSED

- All 24 changed files confirmed present on disk (`[ -f "$f" ]` for each).
- All 8 task commit hashes (`a8f758a`, `d0d33a3`, `cf8085f`, `0add64c`, `39b7468`, `8038ba2`, `f1bead5`, `2bd30d7`) confirmed in `git log --oneline --all`.
- Final `./scripts/run-all-tests.sh` re-run after the last commit: 2695 passed, 5 skipped, exit code 0.
