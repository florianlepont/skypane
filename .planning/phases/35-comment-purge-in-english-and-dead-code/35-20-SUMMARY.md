---
phase: 35-comment-purge-in-english-and-dead-code
plan: 20
subsystem: infra
tags: [deploy, systemd, caddy, ci, shell, ruff, coverage, comment-hygiene]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: 35-19 (group 7 close, style.css) — the comment-history CLI, the ratchet's pending list, and the 35-COMMENT-RATIO.md table this plan appends to
provides:
  - deploy/, scripts/ (minus the guard tool itself), .github/, adsb-test/, hardware/logtools.py, pyproject.toml, conftest.py and .gitignore purged of every plan/ticket/decision/threat-ID comment reference, English-only
  - group 8 removed from scripts/comment-history-pending.txt (only firmware/ remains pending)
  - a group-8 section in 35-COMMENT-RATIO.md with per-file before/after ratios, the over-35%-comment review list, and the same-code --allow rationale
  - deploy/tests/test_install_backup_key.py's env-example-permissions test rewritten to check deploy/provision.sh's actual chown/chmod directives instead of a comment
affects: [35-21, 35-22]

tech-stack:
  added: []
  patterns:
    - "For hash-comment-format files (.sh, .service, .timer, .yml, .toml, Caddyfile, .gitignore, .env.example), same-code compares every line position-by-position after stripping trailing comments, so a comment line can never be added or removed without shifting later code out of place -- only in-place text edits are safe; Python files have no such constraint since same-code compares the AST with (non-__doc__) docstrings stripped"

key-files:
  created: []
  modified:
    - deploy/.gitignore
    - deploy/Caddyfile
    - deploy/activate.sh
    - deploy/deploy.sh
    - deploy/harden_sshd.sh
    - deploy/provision.sh
    - deploy/render_caddyfile.sh
    - deploy/skypane-backup.service
    - deploy/skypane-backup.timer
    - deploy/skypane-byos.service
    - deploy/skypane-companion.service
    - deploy/skypane-poll.service
    - deploy/skypane-poll.timer
    - deploy/skypane.env.example
    - deploy/backup/backup_gate.py
    - deploy/backup/skypane_backup.py
    - deploy/backup/install-backup-key.sh
    - deploy/backup/mac/install-launchagent.sh
    - deploy/backup/mac/skypane-backup-pull.sh
    - deploy/backup/mac/skypane-backup-pull.plist.template
    - deploy/tests/conftest.py
    - deploy/tests/test_activate.py
    - deploy/tests/test_backup.py
    - deploy/tests/test_backup_gate.py
    - deploy/tests/test_caddyfile.py
    - deploy/tests/test_ci_secrets.py
    - deploy/tests/test_deploy.py
    - deploy/tests/test_docs.py
    - deploy/tests/test_install_backup_key.py
    - deploy/tests/test_mac_pull.py
    - deploy/tests/test_provision.py
    - deploy/tests/test_units.py
    - scripts/check-attribution.sh
    - scripts/lock-deps.sh
    - .github/workflows/ci.yml
    - pyproject.toml
    - conftest.py
    - .gitignore
    - adsb-test/analyze_samples.py
    - adsb-test/query_aggregator.py
    - adsb-test/sample_window.py
    - hardware/logtools.py
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md

key-decisions:
  - "Discovered scripts/check_comment_history.py's same-code dispatch has no XML branch for .plist.template files (extract_hash finds no '#' spans, so the hash-line comparator treats the whole file as code); allowed deploy/backup/mac/skypane-backup-pull.plist.template with a manually-confirmed comment-only diff rather than edit the guard, which is out of scope for this plan"
  - "Fixed deploy/tests/test_install_backup_key.py's env-example-permissions test in its own commit before purging the comment it read, per the plan's explicit instruction; the rewritten assertion checks deploy/provision.sh's actual chown/chmod directives"
  - "For every hash-comment-format file, edited comment TEXT in place at fixed line positions rather than deleting/consolidating lines, since same-code's line-position comparator would otherwise misattribute a later code line to a removed comment slot"
  - "Did not mark HYG-01/HYG-03 complete, did not merge origin/main, push, or open a PR -- per the orchestrator's explicit sequential-execution instruction for this run"

requirements-completed: []

duration: ~2h
completed: 2026-09-26
---

# Phase 35 Plan 20: Group 8 comment purge (deploy/, scripts/, .github/, root config, adsb-test/, hardware/) Summary

**Purged all 199 plan/ticket/decision/threat-history references from 47 files across deploy/, scripts/, .github/, root config, adsb-test/ and hardware/logtools.py comments, discovering and working around a same-code tool gap for XML `.plist.template` files, then closed group 8 of the phase's comment-history ratchet, leaving only firmware/ pending.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3 (deploy production purge, deploy tests + scripts + .github + root + adsb-test + hardware purge, group close) — executed as 16 commits for interruption resilience (2-4 files each)
- **Files modified:** 42 code/config files + `scripts/comment-history-pending.txt` + `35-COMMENT-RATIO.md`

## Accomplishments

- 47 files: 199 -> 0 history hits, `check --paths` reports 0 for all of them, and the argument-less `check` (after the pending-list edit) exits 0 for every tracked file outside `firmware/`
- `same-code --base 8840b0a` exits 0 for the whole group, with exactly three documented `--allow` exceptions (two plan-authorized argparse `__doc__` modules, one discovered tool gap, one plan-authorized test-assertion rewrite — see below)
- `systemd-analyze security --offline=true --threshold=20` passes for all four `deploy/*.service` units (directives byte-unchanged)
- Full suite green: `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` — 2691 passed, 5 skipped (pre-existing root-euid skips), coverage 93.24% against the 93% gate
- `ruff check .` clean; every changed `.sh` file passes `bash -n` (`shellcheck` not installed locally, so CI's lint job is the gate, per the plan's own fallback)
- `scripts/comment-history-pending.txt`: 80 entries -> 37, all remaining paths under `firmware/` (group 9)
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` gained a group-8 section: per-file before/after ratios, a group total (7505 lines, 24.7% -> 24.3% comment ratio, 199 -> 0 history hits), 15 files still above ~35% comments each with a one-line justification, and the `--allow` rationale

## Task Commits

Each 2-4 file batch was committed atomically (`docs(35-20):` comment-only edits, one `test(35-20):` for the approved assertion rewrite):

1. `57f8669` — Caddyfile, activate.sh, deploy.sh
2. `a24fd2b` — harden_sshd.sh, provision.sh, render_caddyfile.sh
3. `0951f6e` — skypane-backup.service, skypane-backup.timer, skypane-byos.service, skypane-companion.service
4. `94ddfd8` — test(35-20): rewrite test_install_backup_key.py's env-permissions assertion (behavior change, its own commit, before the comment purge)
5. `b1a0792` — skypane-poll.service, skypane-poll.timer, skypane.env.example
6. `df60a22` — backup_gate.py, skypane_backup.py
7. `9feeb50` — install-backup-key.sh, install-launchagent.sh, skypane-backup-pull.sh, skypane-backup-pull.plist.template
8. `23a732f` — deploy/tests/conftest.py, test_activate.py, test_backup.py, test_backup_gate.py
9. `cec7b12` — test_caddyfile.py, test_ci_secrets.py, test_deploy.py, test_docs.py
10. `d27bd1f` — test_install_backup_key.py (comment purge), test_mac_pull.py, test_provision.py, test_units.py
11. `4ace2f1` — scripts/check-attribution.sh, scripts/lock-deps.sh
12. `989559f` — .github/workflows/ci.yml
13. `2e104ad` — pyproject.toml, conftest.py, .gitignore
14. `1bf7ce8` — adsb-test/analyze_samples.py, query_aggregator.py, sample_window.py
15. `acbd033` — hardware/logtools.py
16. `89724e7` — group 8 close: pending-list removal + 35-COMMENT-RATIO.md group-8 section

_Note: this plan is `type="execute"`, not TDD — no test -> feat -> refactor cycle; each commit is either a comment-only `docs(35-20):` edit or, once, an approved `test(35-20):` assertion rewrite done ahead of the comment it unblocked._

## Files Created/Modified

- `deploy/*` (production units, scripts, Caddyfile, env example, backup/mac scripts) — every comment purged of plan/ticket/decision/threat IDs; directives, permissions and code paths byte-unchanged
- `deploy/tests/*.py` — module docstrings and inline comments purged; test names and assertion strings unchanged except the one approved rewrite in `test_install_backup_key.py`
- `scripts/check-attribution.sh`, `scripts/lock-deps.sh` — header IDs removed; `run-all-tests.sh`/`run-local-verify.sh` already carried none
- `.github/workflows/ci.yml` — paths-filter header, requirements-lock, shellcheck, systemd-analyze and deploy-secret step comments purged; `dependabot.yml`/`firmware.yml` already carried none
- `pyproject.toml`, `conftest.py`, `.gitignore` (root) — ruff/pytest/coverage config and DNS-guard fixture comments purged
- `adsb-test/analyze_samples.py`, `query_aggregator.py`, `sample_window.py` — module docstrings purged; `.gitignore` already carried none
- `hardware/logtools.py` — subcommand-help docstring and section-comment IDs removed (one D-07 reference inside an argparse `help=` string literal was left untouched, per the rule against editing string literals)
- `scripts/comment-history-pending.txt` — every group-8 path removed, leaving only `firmware/*`
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — group-8 section appended

## Decisions Made

- **Hash-comment-format line-position constraint discovered and worked around systematically.** `same-code`'s comparator for `.sh`/`.service`/`.timer`/`.yml`/`.toml`/`Caddyfile`/`.gitignore`/`.env.example` files strips each line's trailing comment and compares the resulting list position-by-position against the base. A comment-only line always reduces to `""`, so deleting or adding one shifts every later code line's index and fails the comparison, even though no code actually changed. All edits to these formats were therefore done as fixed-line-count, in-place text rewrites (remove the ID phrase, reflow the sentence within the same or adjacent comment lines) rather than deleting or condensing whole lines. Python files (`.py`) have no such constraint, since `same-code` compares the parsed AST with non-`__doc__` docstrings stripped, so module/function docstrings there were edited freely.
- **`deploy/backup/mac/skypane-backup-pull.plist.template` needed `same-code --allow`, undocumented by the plan.** `scripts/check_comment_history.py`'s `same-code` dispatch has no XML branch: `check`/`ratio` call `extract_xml` for `.plist.template`, but `same-code` falls through to the generic hash-line comparator, which finds no `#`-prefixed comment spans in XML and therefore treats the entire file (including the `<!-- -->` block) as code. Any edit inside the comment trips a false "code changed" positive. Since `scripts/check_comment_history.py` is out of scope for this plan (reserved for 35-01/35-22), the file was allowed in `same-code` with the diff manually confirmed comment-only via both `git diff` and an `xml.etree.ElementTree` structural comparison (byte-identical parsed tree outside the comment).
- **`deploy/tests/test_install_backup_key.py` needed `same-code --allow` for an approved reason, not a bug.** 35-01's own G-33 audit flagged `test_env_example_header_says_root_owned_600_read_by_systemd` as the plan's one class-(b) source-read hit: it asserted `"root:root"`/`"600"` against `deploy/skypane.env.example`'s header comment text, which would have blocked purging that comment. Per this plan's `<purge_bar>`, the test was rewritten in its own preceding commit (`94ddfd8`) to assert the same fact against `deploy/provision.sh`'s actual `chown root:root`/`chmod 600` directives instead — a real, intentional code change that legitimately differs from base, not a purge regression.
- **Grepped every other `deploy/tests/*.py` `read_text()` call for comment-text assertions** (per the plan's instruction): all other hits check directives (`ExecStart=`, `IPAddressDeny`, hardening keys), log output, or greppable code substrings (`rsync`, `sha256sum`, `chown -R`) — none reads comment prose. No other test needed rewriting.
- **`hardware/logtools.py`'s `check-battery` help string keeps its `D-07` mention** — it lives inside an `argparse` `help=` string literal (user-facing CLI text), not a comment, and the guard correctly does not flag it; per the purge rules, string literals are never edited.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `same-code` has no XML dispatch branch for `.plist.template`**
- **Found during:** Task 1, purging `deploy/backup/mac/skypane-backup-pull.plist.template`
- **Issue:** Editing the file's `<!-- -->` header comment (removing `SEC-04, D-04`) made `same-code --base 8840b0a` report the file as differing, even though the parsed plist structure was byte-identical. Root cause: `_same_code_one()` routes any file with a non-`None` `extractor_for_path()` result to `_same_code_hash()`, which always calls `extract_hash()` (a `#`-comment scanner) regardless of the actual extractor (`extract_xml` for `.plist.template`), so it finds zero comment spans in XML and compares the raw file text, including the comment, as "code".
- **Fix:** Confirmed the diff was comment-only via `git diff` and an `xml.etree.ElementTree` parse-and-compare (byte-identical tree outside the `<!--...-->` node). Allowed the file with `--allow` for this plan's own verification, documented in the commit message and the 35-COMMENT-RATIO.md group-8 section. Did not modify `scripts/check_comment_history.py` (out of scope, reserved for 35-01/35-22).
- **Files modified:** `deploy/backup/mac/skypane-backup-pull.plist.template`
- **Commit:** `9feeb50`

**2. [Rule 1 - Editing mistake caught before commit] Two line-numbering slips while doing surgical edits on hash-format shell scripts**
- **Found during:** Task 1, editing `deploy/activate.sh` and `deploy/Caddyfile`
- **Issue:** A first attempt at `deploy/activate.sh` used stale line numbers from an earlier read, duplicating one comment line and corrupting another (`# leaves a red CI job...` appeared twice). A first attempt at `deploy/Caddyfile`'s header used a full rewrite that shortened the file below its base line count, breaking `same-code`'s line-position invariant.
- **Fix:** `git checkout -- <file>` to revert to the clean base before any commit was made, re-read the exact current line numbers with `awk 'NR==...'` immediately before each edit, and re-verified `same-code`/`check` before proceeding. Neither mistake was ever committed.
- **Files modified:** `deploy/activate.sh`, `deploy/Caddyfile` (both fixed before their respective commits)
- **Commit:** `57f8669` (both files landed correctly in this commit)

---

**Total deviations:** 2 (1 auto-fixed tool-gap workaround via `--allow`, Rule 3; 1 self-caught editing mistake fixed before any commit, not a landed defect)
**Impact on plan:** The XML tool gap is a real, reusable finding for 35-21/35-22 (firmware's `VENDOR.md`-adjacent files are Markdown, out of scope, but any future XML/plist-like format would hit the same gap). No scope creep — both fixes stayed within the group-8 file set the plan already named.

## Issues Encountered

None beyond the two deviations above — both were caught by `same-code`/`git diff` before landing in git history.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Group 8 is closed: `scripts/comment-history-pending.txt` lists only `firmware/*` paths, and the argument-less `check` exits 0 for every other tracked file the tool has a comment syntax for.
- HYG-01 and HYG-03 are now fully satisfied by the sum of groups 1-8, but per the orchestrator's explicit instruction for this sequential run, this plan does **not** mark them complete in `REQUIREMENTS.md`, does not merge `origin/main`, does not push, and does not open a PR — all left to the orchestrator's own bookkeeping.
- 35-21 (group 9: firmware, behind gate G-34) and 35-22 (phase close: delete the ratchet mechanism, final mutation proof, final `35-COMMENT-RATIO.md`) are unblocked and ready to run next per the phase's wave ordering. 35-22 should also decide whether to fix the XML same-code dispatch gap this plan found in `scripts/check_comment_history.py` (currently the tool has no `.plist.template`/XML branch in `same-code`, only in `check`/`ratio`) before deleting the pending-list ratchet mechanism, since firmware carries no `.plist.template` files but any future XML-like format purge would hit the same gap.

## Self-Check: PASSED

All 16 commit hashes (`57f8669`, `a24fd2b`, `0951f6e`, `94ddfd8`, `b1a0792`, `df60a22`, `9feeb50`, `23a732f`, `cec7b12`, `d27bd1f`, `4ace2f1`, `989559f`, `2e104ad`, `1bf7ce8`, `acbd033`, `89724e7`) found in `git log`. All 42 modified files, `scripts/comment-history-pending.txt` and `35-COMMENT-RATIO.md` exist on disk with the expected content.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-26*
