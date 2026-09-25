---
phase: 35-comment-purge-in-english-and-dead-code
plan: 07
subsystem: stub-server-comment-hygiene
tags: [comment-hygiene, ci-guard, ratchet, stub-server, device-protocol, drift-guard]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 06
    provides: "server/ fully purged and CI-enforced (group 2 closed)"
provides:
  - "stub-server/byos_server.py, devices_cli.py, make_test_panel.py, test_devices_registry.py,
    test_poll_cycle.py, .gitignore purged of plan/ticket/decision/review/phase-ID history
    (0 hits across all 6 comment-syntax-supported stub-server/ files), code unchanged"
  - "35-COMMENT-RATIO.md group-3 section with per-file before/after ratios, group total, and
    justifications for the two files still above the 35% guideline"
  - "group 3 (stub-server/) closed: 0 pending-list lines, 0 history hits, full suite green"
affects: [35-08, 35-09]

tech-stack:
  added: []
  patterns:
    - "argparse module docstrings (description=__doc__) need --allow <that file> in same-code even
      when the plan's own conventions text says 'no ALLOW' - byos_server.py and make_test_panel.py
      both read __doc__ for their CLI; devices_cli.py uses a literal description string instead and
      needs no --allow, confirmed by grepping for the literal substring '__doc__' across the group"
    - "a module docstring that doubles as a giant table-of-contents for a test file's own test
      docstrings is a paraphrase of the next lines (purge_bar violation), not just history-ID
      carrying text - test_poll_cycle.py's 41-line enumeration paragraph was dropped in favour of
      pointing at each test's own docstring, not merely ID-stripped in place"

key-files:
  created: []
  modified:
    - stub-server/byos_server.py
    - stub-server/make_test_panel.py
    - stub-server/test_poll_cycle.py
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md

key-decisions:
  - "byos_server.py and make_test_panel.py both read description=__doc__ for their argparse CLI,
    so group 3's same-code proof needs --allow for both (not 'no ALLOW' as the plan's own
    conventions text stated) - matching the purge_bar's own runtime-__doc__ file list. Confirmed
    devices_cli.py uses a literal description string, not __doc__, so it needs no --allow."
  - "byos_server.py (35.2%) and make_test_panel.py (36.4%) sit just above the ~35% guideline after
    two compression passes each (52.2%->35.2% and 41.7%->36.4%); documented in 35-COMMENT-RATIO.md
    since the remaining comments are the device-protocol security invariants and non-obvious
    byte-packing math the plan's own must_haves require to survive, not restatement or scope talk."
  - "devices_cli.py, .gitignore, and test_devices_registry.py already carried 0 history hits and
    were already within the ratio guideline (22.7%, 30.0%, 12.0%) - left unmodified rather than
    rewritten for its own sake."

requirements-completed: []

duration: ~45min
completed: "2026-09-25"
---

# Phase 35 Plan 07: stub-server/ purge and group 3 close Summary

Purged plan/ticket/decision/review/phase-ID history from `stub-server/byos_server.py`'s module
docstring and every function docstring/comment, `make_test_panel.py`'s module docstring, and
`test_poll_cycle.py`'s module docstring and section headers, keeping the device-protocol security
invariants (registry fail-closed enrolment, timing-safe secret comparison, X-Battery-Mv bounds,
the four-function sleep_s composition order) and the Spectra 6 byte-packing math intact as
concise why-comments, in English, with all code byte-for-byte unchanged; then closed PR group 3
by proving the whole group history-free and code-unchanged, ratcheting `stub-server/` out of the
CI guard's pending list, and recording the group's ratio evidence.

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-25T09:48Z
- **Completed:** 2026-09-25T10:20Z
- **Tasks:** 2 completed
- **Files modified:** 5 (`byos_server.py`, `make_test_panel.py`, `test_poll_cycle.py`,
  `scripts/comment-history-pending.txt`, `35-COMMENT-RATIO.md`)

## Accomplishments
- `byos_server.py`: rewrote the module docstring (dropped the ~40-line "SkyPane local
  modifications" change-narrative section entirely, keeping only current --help-accurate
  behaviour), all six module-level constant comments, and every function docstring across two
  compression passes (52.2% -> 35.2% comment ratio, 49 -> 0 history hits), while keeping every
  security invariant the plan's must_haves named: the registry's fail-closed contract (vs.
  `load_state()`'s fail-open one), `secret_matches()`'s `hmac.compare_digest` timing-safety note,
  the `X-Battery-Mv` bounds' PROTOCOL.md §2 sentinel rationale, and the load-bearing nesting order
  across `display_off_sleep_s()` / `battery_critical_sleep_s()` / `quiet_hours_sleep_s()`. The
  vendored `seconds_until_quiet_hours_end()` function body/docstring and the `_HHMM_RE` constant
  are byte-for-byte untouched, per the drift guard `test_poll_cycle.py` enforces against
  `server/device_config.py`.
- `make_test_panel.py`: compressed the module docstring (still `--help` text via
  `description=__doc__`) and one function docstring, 41.7% -> 36.4%, keeping the non-obvious
  byte-pair/nibble-packing geometry (0 history hits, none to begin with).
- `test_poll_cycle.py`: dropped the module docstring's 41-line paraphrase-of-the-suite paragraph
  (a purge_bar violation independent of its ID hits) in favour of pointing at each test's own
  docstring, purged three section-header comments and two test docstrings of `MR-N`/`D-NN`
  history, and rewrote the harness/fixture docstrings' `MR-4`/`MR-5`/`MR-9`/`DEVICE-04`/
  `DEVICE-05` references (25.7% -> 24.3%, 20 -> 0 hits); test names and assertion-message strings
  unchanged. `test_devices_registry.py` already carried 0 history hits and needed no edits.
- `devices_cli.py` and `stub-server/.gitignore` already had 0 history hits and ratios well under
  35% (22.7%, 30.0%) - verified compliant and left unmodified.
- Group-level `same-code --base f266a05` passes for all 3 changed files with `--allow
  byos_server.py --allow make_test_panel.py`, and `check --paths $(git ls-files stub-server/)`
  reports 0 history hits across all 6 scanned files.
- `scripts/comment-history-pending.txt` shrunk from 179 to 177 lines (both `^stub-server/` lines
  removed); `check` with no args stays green, so CI's guard now covers `stub-server/`
  unconditionally.
- `35-COMMENT-RATIO.md` gained a group-3 section: full 6-file before/after table, a group-total
  row matching the baseline's group-3 row exactly (2915 -> 2627 lines, 32.7% -> 25.4%, 69 -> 0
  history hits), and justifications for the two files still above the ~35% guideline.
- Full suite green after re-verifying (no `origin/main` advance since group start, so no merge
  was needed): `./scripts/run-all-tests.sh` -> 2564 passed, 132 skipped (pre-existing
  Playwright-environment skips), 0 failed. `ruff check .` clean.

## Task Commits

1. **Task 1: Purge stub-server production files** - `473cf6e` (refactor)
2. **Task 2: Purge stub-server tests and close group 3** - `6021431` (refactor)

**Plan metadata:** pending (final docs commit, this file + STATE.md/ROADMAP.md)

## Files Created/Modified
- `stub-server/byos_server.py` - module docstring, constant comments, and every function
  docstring purged of history, two compression passes to reach the ratio guideline
- `stub-server/make_test_panel.py` - module docstring and one function docstring compressed
- `stub-server/test_poll_cycle.py` - module docstring rewritten (dropped the paraphrase
  paragraph), three section headers and two test docstrings purged of `MR-N`/`D-NN` IDs
- `scripts/comment-history-pending.txt` - removed both `^stub-server/` lines (179 -> 177 lines)
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` - added the
  group-3 (stub-server/) per-file ratio table, group total, and above-35% justifications

## Decisions Made
- Used `--allow stub-server/byos_server.py --allow stub-server/make_test_panel.py` in the
  group-level `same-code` proof, overriding the plan's own "GROUP_PATHS = stub-server/, no ALLOW"
  convention text: both files read `description=__doc__` for their argparse CLI (confirmed by
  grepping the literal substring `__doc__` across every stub-server/ file), which the `same-code`
  tool keeps in its AST comparison whenever `"__doc__"` appears anywhere in the file text - the
  same mechanism 35-02/35-06 already established for `server/plane/illustrations.py` and
  `server/plane/render.py`. `devices_cli.py` was confirmed to use a literal description string
  instead, so no `--allow` was needed for it.
- Accepted `byos_server.py` at 35.2% and `make_test_panel.py` at 36.4% after two compression
  passes each rather than continuing to cut: both are dominated by load-bearing security/protocol
  invariants (composition order across three sleep_s pins, timing-safe secret comparison,
  byte-pair nibble packing) the plan's own must_haves and threat model (T-35-06) require to
  survive - documented with a one-line justification per file in `35-COMMENT-RATIO.md`, mirroring
  the group-2 precedent for `dither.py`/`runway_config.py`.
- Left `devices_cli.py`, `stub-server/.gitignore`, and `test_devices_registry.py` unmodified:
  each already had 0 history hits and a comment ratio under the 35% guideline, so editing them
  would have been change for its own sake rather than purge work.

## Deviations from Plan

None - plan executed exactly as written, aside from the documented `--allow` correction above
(Rule 3 - blocking: the plan's own verify commands and conventions text would otherwise fail
`same-code` on two files that legitimately need it, the same class of stale-plan-command issue
35-02 and 35-06 both encountered and corrected in their own executions).

## Issues Encountered
None beyond the `--allow` correction documented above.

## User Setup Required
None - no external service configuration required.

## Verification Results

- **Task 1 same-code:** `same-code --base f266a05 --allow stub-server/byos_server.py
  stub-server/byos_server.py stub-server/devices_cli.py stub-server/make_test_panel.py
  stub-server/.gitignore` (and separately with `--allow stub-server/make_test_panel.py`) -> exit 0
- **Task 1 check:** `check --paths` the four Task 1 files -> 0 history hits
- **Task 1 tests:** `pytest stub-server -q -n auto` -> 33 passed
- **Task 2 same-code:** `same-code --base f266a05 --allow stub-server/byos_server.py --allow
  stub-server/make_test_panel.py $(git diff --name-only f266a05 -- stub-server/)` -> exit 0
- **Task 2 check:** `check --paths $(git ls-files stub-server/)` (8 files, 6 with comment-syntax
  support) -> 0 history hits
- **Pending list:** `grep -c '^stub-server/' scripts/comment-history-pending.txt` -> 0; `check`
  (no args) -> exit 0
- **Ratio table:** `35-COMMENT-RATIO.md` group-3 section - group total 2915 -> 2627 lines, 32.7%
  -> 25.4%, 69 -> 0 history hits (matches `35-BASELINE/INDEX.md`'s group-3 row exactly)
- **Drift guard:** `pytest stub-server/test_poll_cycle.py::test_quiet_hours_helpers_drift_guard_matches_device_config`
  -> 1 passed (the vendored `seconds_until_quiet_hours_end()`/`_HHMM_RE` copies stayed
  byte-for-byte equal to `server/device_config.py`'s)
- **Full suite:** `./scripts/run-all-tests.sh` -> 2564 passed, 132 skipped (pre-existing
  Playwright-environment skips, unrelated to this plan), 0 failed
- **ruff:** `server/.venv/bin/ruff check .` -> "All checks passed!"
- **shellcheck:** not installed in this environment; per the plan's own instruction, CI is the
  gate for `deploy/*.sh`
- **Merge with origin/main:** not needed - `origin/main` had not advanced since the group-2 merge
  (`git merge-base HEAD origin/main` still equals `f266a05`, the literal group base)
- **PR:** not opened by this executor - per the orchestrator's instructions, this plan stayed on
  `claude/plan-phase-35` and did not push or open a PR; the orchestrator handles push/PR after
  this plan returns
- **REQUIREMENTS.md:** HYG-01/HYG-03 intentionally left unmarked, per the executor's instructions,
  since they span groups not yet closed (companion, deploy/scripts, firmware remain)

## Next Phase Readiness
`stub-server/` is fully purged, code-unchanged, and CI-enforced (0 pending-list lines, 0 history
hits). The group's ratio evidence is recorded for the phase's closing report. Remaining
pending-list groups (companion Python production/tests/JS/CSS, `deploy/`+`scripts/`+`.github/`+
root config+`adsb-test/`+`hardware/` scripts, `firmware/`) are unaffected and untouched by this
plan.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `stub-server/byos_server.py` — FOUND
- `stub-server/make_test_panel.py` — FOUND
- `stub-server/test_poll_cycle.py` — FOUND
- `scripts/comment-history-pending.txt` — FOUND
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — FOUND
- Commit 473cf6e (Task 1: purge stub-server production files) — FOUND
- Commit 6021431 (Task 2: purge tests and close group 3) — FOUND
