---
phase: 35-comment-purge-in-english-and-dead-code
plan: 01
subsystem: tooling
tags: [ci, comments, hygiene, guard]
dependency_graph:
  requires: []
  provides:
    - scripts/check_comment_history.py (check/ratio/same-code, stdlib only)
    - scripts/comment-history-pending.txt (ratchet list, group closes shrink it)
    - CI lint-job guard step
    - 35-BASELINE/ratio-before.tsv, 35-BASELINE/INDEX.md
    - English-only rule in .claude/CLAUDE.md and CONTRIBUTING.md (HYG-04)
  affects:
    - .github/workflows/ci.yml
requirements: [HYG-04, HYG-06]
tech_stack:
  added: []
  patterns:
    - "string/regex/url-aware per-language comment extraction (tokenize+ast for Python, hand tokenizers for C/JS/CSS, quote-aware scanner for hash formats, <!-- --> for XML)"
    - "same-code proof via AST/cpp/token comparison plus a pragma+SPDX multiset check, independent of the history-reference guard"
key_files:
  created:
    - scripts/check_comment_history.py
    - scripts/comment-history-pending.txt
    - test-support/test_check_comment_history.py
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-BASELINE/ratio-before.tsv
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-BASELINE/INDEX.md
  modified:
    - .github/workflows/ci.yml
    - .claude/CLAUDE.md
    - CONTRIBUTING.md
decisions:
  - "Group 1 ('foundation') has no directory bucket in the baseline totals: this plan's own new files land in the directory groups their paths already belong to (scripts/ and test-support/), per 35-CONTEXT.md's group list."
  - "Baseline ratio was measured with this plan's own CI-guard-step comment and pending-list file already in place (not before them), since Task 3's own ordering runs the baseline after adding both — 'before' means before the per-group purge starts, not before plan 35-01 itself."
metrics:
  duration: "~25 minutes"
  completed: "2026-09-25"
---

# Phase 35 Plan 01: Comment-history guard foundation Summary

Built a stdlib-only Python tool (`check`/`ratio`/`same-code`) that finds plan/ticket-history
references in comments and docstrings across seven language families, mutation-proved every
regex alternative (43/43), wired it into CI behind a 208-file ratchet pending list, recorded the
264-file baseline (comment ratio, history-hit counts, `style.css` raw/gzip size), and wrote the
English-only rule in both `.claude/CLAUDE.md` and `CONTRIBUTING.md`.

## What was built

**Task 1 — Gate G-33, source-read audit, HYG-04.**
- G-33 evidence on `origin/main` (8449b34): 33 files matching `33-*-SUMMARY.md` under the Phase 33
  directory; `33-VERIFICATION.md` has `status: passed`; `ROADMAP.md`'s Phase 33 section reads
  "Plans: 33/33 plans complete". `companion/test_suite_guards.py` passes (91 tests).
- Source-read audit: grepped every `test_*.py`, `conftest.py`, `test-support/*.py`,
  `deploy/tests/*.py` and `firmware/tests/*.sh` for `read_text(`, `open(`, `getsource`, `__doc__`,
  and grep/sed on source paths. Findings and classification:
  - The overwhelming majority (companion fixtures/state-dir I/O, `server/test_calendar_rules.py`,
    `server/test_colour_rules.py`, `stub-server/test_poll_cycle.py`'s
    `DEVICE_CONFIG_MODULE_PATH`/`POLL_LOOP_MODULE_PATH`/`SERVER_PATH` reads, `deploy/tests/*`'s
    `.read_text()` on scripts/units/CI YAML, `firmware/tests/check_log_contract.sh`'s greps) are
    **class (a)**: they read fixture/state data, or extract a specific code construct (a function
    def block, an `ExecStart=` value, a `CONFIG_X =` assignment, a YAML `run:` block, a substring
    absence check like "rsync" not in `deploy.sh`) by directive or behaviour — never comment text
    — so they are safe to purge around.
  - `server/test_illustrations.py::test_variants_derived_from_targets_no_second_table` uses
    `inspect.getsource()` to assert a code identifier (`_ILLUSTRATION_TARGETS`) appears in a
    function's source. Also class (a) (it checks a code token, not a comment), but flagged here
    because it is the one `getsource` use outside companion (companion's own guard G2 bans
    `getsource` outright) — worth a look when the server group purges that file.
  - **One class (b) hit**: `deploy/tests/test_install_backup_key.py::test_env_example_header_says_root_owned_600_read_by_systemd`
    reads `deploy/skypane.env.example` as text and asserts `"root:root"` and `"0600"`/`"600"`
    appear in it — both of which currently live only in a `#` comment header
    (`deploy/skypane.env.example:13`, which itself carries `(SEC-07, D-19)` — exactly the kind of
    reference this guard exists to purge). This is outside companion, so it does not fail G-33
    per the plan's own rule, but it must be fixed before the deploy purge group (directory group 8,
    the plan CONTEXT.md names as an example "35-20 deploy tests") touches that comment — either by
    rewriting the assertion to check the actual permission-mode code path, or by moving the
    asserted facts into a line the guard treats as code.
  - No class (b) hits in companion (already guarded by `test_suite_guards.py`), so G-33 holds.
- HYG-04: added a "Language and comments" block to `.claude/CLAUDE.md`'s conventions section and a
  "## Code language and comments" section to `CONTRIBUTING.md`. Both state: English-only for code,
  identifiers, comments, docstrings, docs and commits; the companion UI stays bilingual
  (`companion/i18n_fr/` and user-facing string literals); a comment says what and why (invariants,
  security invariants, units, spec pointers); no plan/ticket/decision/review/phase IDs in
  comments; enforced by `scripts/check_comment_history.py check`.

**Task 2 — the tool, TDD.**
- RED: `test-support/test_check_comment_history.py` written first (98 tests), committed while it
  could not even import the not-yet-written module (`FileNotFoundError`).
- GREEN: `scripts/check_comment_history.py`, stdlib only (`argparse`, `ast`, `gzip`, `io`, `os`,
  `re`, `shutil`, `subprocess`, `sys`, `tokenize`, `collections.Counter`). Three subcommands:
  - `check [--paths P ...]`: scans `git ls-files` minus exclusions minus the pending list by
    default, or exactly the given paths (ignoring the pending list) with `--paths`. Prints
    `path:line: pattern-name: text` and exits 1 on any hit.
  - `ratio [--out TSV] [--before TSV --markdown] [paths]`: per-file TSV
    (path, lines, comment_lines, ratio, history_hits, bytes, gzip_bytes), or a markdown
    before/after table.
  - `same-code --base REV [--allow P ...] [paths]`: Python via `ast.dump()` with docstrings
    stripped (module docstring kept when the module reads `__doc__`, detected by a `__doc__`
    substring check); C/H via `cpp -fpreprocessed -P -w` with an internal string-aware-tokenizer
    fallback when `cpp` is unavailable; JS/CSS via comment-stripped whitespace-token comparison;
    hash formats via non-comment-line comparison (an sdkconfig `# CONFIG_X is not set` line counts
    as code, so dropping one is a real difference); every language additionally requires an equal
    pragma/SPDX-or-Copyright-line multiset (a dropped `# noqa`/`# shellcheck`/shebang, or a
    changed SPDX line, differs even if nothing else changed).
  - Pattern set (see mutation proof below): `plan-artifact` (phase[.sub]*[-plan[letter]]-SUFFIX,
    10 suffixes incl. `.md`), `d-id` (`D-06`, `D-A3`, `D-34-03`), `prefix-id` (27-prefix
    allowlist, never a generic `[A-Z]+-\d+`), `threat-id` (`T-NN-NN[-NN[-NN]]`), `quick-task`
    (`NNNNNN-xxx`), `phase-word` (capital-`P` `Phase N` only), `planning-path` (`.planning/`),
    `bare-plan-id` (`NN-NN` only after `plan `/`Plan ` or before ` Task`).
  - Extraction is string/regex/url-aware per language: Python via `tokenize` COMMENT tokens plus
    `ast`-located docstrings; C/H, JS and CSS via hand-written character scanners that skip
    string/char literals (and, for JS, template literals and a regex-literal heuristic keyed on
    the preceding operator/keyword; and, for CSS, `url(...)`) before ever looking for `//` or
    `/* */`; hash formats via a quote-aware `#`-at-token-start scanner (an sdkconfig disabled-line
    is excluded from the comment span entirely, i.e. treated as code); XML via `<!-- -->` for
    `*.plist.template`.
- Fixed two `ruff` findings during GREEN (unused `tempfile` import, unused `stdlib_paths`
  variable) and one guard self-hit (the test file's own module docstring named "HYG-06" — removed
  the reference) before both files passed the tool's own `check`.

**Mutation proof.** Wrote a throwaway script (not committed; lived only in the scratch directory)
that, for each of the pattern set's 43 regex alternatives (10 `plan-artifact` suffixes, 3 `d-id`
branches, all 27 `prefix-id` allowlist entries, 3 `bare-plan-id` forms — lowercase `plan `,
capitalised `Plan `, and the ` Task` suffix branch), removed that one alternative from a working
copy of the tool, ran the full test file, confirmed at least one test failed, then restored the
file via `git checkout --` before the next mutation. First pass found a real gap: removing the
`\d{2}-\d{2}` branch from `d-id` let `D-34-03` still match (truncated to `D-34` via the `\d{1,3}`
branch) without `test_d_id_pattern_positive` noticing, because that test only asserted the pattern
*name* was present, not the matched text. Fixed by asserting the exact matched substring for every
`d-id` sample. Re-run: **43/43 alternatives now fail at least one test when removed**, and
`git diff` was empty after every restore (confirmed again after the final commit).

**Task 3 — pending list, CI step, baseline, planted-ID proof.**
- `scripts/comment-history-pending.txt`: 208 files (of the 264 the tool has a comment syntax for)
  carrying at least one of 9441 total history hits, one path per line, sorted, preceded by a `#`
  header the tool ignores. `check` (no `--paths`) now exits 0.
- CI: added a "Comment history guard" step to the lint job in `.github/workflows/ci.yml`, right
  after "Lint (blocking …)", running `server/.venv/bin/python scripts/check_comment_history.py
  check`. The step's own 2-line comment carries no history reference (verified with
  `check --paths .github/workflows/ci.yml`, which shows only pre-existing, pending-listed hits
  elsewhere in the file).
- Baseline: `35-BASELINE/ratio-before.tsv` (264 rows) and `35-BASELINE/INDEX.md` — measured on top
  of commit `83f4620` plus this plan's own then-uncommitted pending-list/CI-step additions.
  Per-group totals (files / lines / comment lines / ratio / history hits): server/ 36/30940/11511/
  37%/1689; stub-server/ 6/2915/954/33%/69; companion production (py) 33/30353/19291/64%/3620;
  companion tests + test-support/ 52/50312/12948/26%/2605; companion static JS 17/6518/3738/57%/
  340; `companion/static/style.css` 1/10689/6842/64%/830; deploy+scripts+.github+root+adsb-test+
  hardware 48/8325/1897/23%/199; firmware/ 71/8472/2087/25%/89. `style.css`: 512795 bytes raw,
  170113 bytes gzip -9. Interpreter: CPython 3.11.15 (`server/.venv`).
- Planted-ID proof: `check` on a clean checkout exits **0**. Planted `# see D-06` at the top of
  `.github/dependabot.yml` (tracked, not in the pending list) → `check` exits **1**, printing
  `.github/dependabot.yml:6: d-id: D-06`. Reverted with `git checkout -- .github/dependabot.yml`
  → `check` exits **0** again, `git diff` empty.
- Close: `ruff check .` clean; `shellcheck` not installed locally (per the plan's own fallback,
  CI's `firmware.yml`/`ci.yml` shellcheck step is the gate for this run); full suite via
  `./scripts/run-all-tests.sh` — **2564 passed, 132 skipped** (Playwright headless-shell binary
  not installed in this sandbox, plus a few root-euid-only skips — both pre-existing environment
  conditions, unrelated to this change), **0 failed**, coverage **93.08%** against the 93% gate.
  `origin/main` had not advanced past this branch's base (8449b34), so no merge was needed.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Test bug found by mutation testing] `d-id`'s `D-34-03` test didn't prove the
`\d{2}-\d{2}` alternative**
- **Found during:** Task 2's required mutation-proof pass.
- **Issue:** `test_d_id_pattern_positive` asserted only that the pattern name `"d-id"` appeared in
  the hit set for a sample, not that the *matched text* covered the whole sample. Removing the
  `\d{2}-\d{2}` branch from the `d-id` regex left `D-34-03` still flagged (as a truncated `D-34`
  match via the remaining `\d{1,3}` branch), so the test kept passing — a real mutation-proof gap.
- **Fix:** Changed the assertion to require the exact sample string among the matched texts.
  Re-ran the full 43-mutation sweep: all now fail as expected.
- **Files modified:** `test-support/test_check_comment_history.py`
- **Commit:** 83f4620

### Not auto-fixed (recorded, not this plan's file)

**2. [class (b) source-read, outside this plan's ownership] `deploy/tests/test_install_backup_key.py`
reads a comment's text**
- See Task 1 write-up above. Not fixed here because `deploy/tests/` is not in this plan's
  `files_modified`; the deploy purge group (directory group 8) must fix it before purging
  `deploy/skypane.env.example`'s header comment.

## Threat Flags

None. This plan only adds an offline, read-only CI lint step (no new network endpoint, auth path,
or trust-boundary change); `T-35-01`..`T-35-04` from the plan's own threat model are the complete
threat surface and are addressed by the mutation-proof pass, the absence of a suppression pragma,
the pragma/SPDX same-code check, and the accepted-risk ratchet list respectively.

## Orchestrator note

Per the sequential-executor instructions for this run, no branch was created (already on
`claude/plan-phase-35`, based on up-to-date `origin/main`) and this plan did not push or open the
group-1 draft PR — the orchestrator handles push/PR for this group. `origin/main` was fetched and
confirmed to be an ancestor of this branch, so no merge was necessary.

## Self-Check: PASSED

- `scripts/check_comment_history.py` — FOUND
- `scripts/comment-history-pending.txt` — FOUND
- `test-support/test_check_comment_history.py` — FOUND
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-BASELINE/ratio-before.tsv` — FOUND
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-BASELINE/INDEX.md` — FOUND
- Commit de7eb3e (HYG-04 docs) — FOUND
- Commit 2f9f424 (RED tests) — FOUND
- Commit 4799c70 (GREEN tool) — FOUND
- Commit 83f4620 (mutation-proof fix) — FOUND
- Commit fec79f6 (CI + baseline) — FOUND
