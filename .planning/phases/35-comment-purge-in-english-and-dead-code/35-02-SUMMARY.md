---
phase: 35-comment-purge-in-english-and-dead-code
plan: 02
subsystem: server-plane-render
tags: [comment-hygiene, docstrings, render, illustrations, dither, colour-rules, runway-config]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 01
    provides: scripts/check_comment_history.py (check/ratio/same-code), scripts/comment-history-pending.txt
provides:
  - server/plane/render.py, illustrations.py, colour_rules.py, dither.py, runway_config.py purged of
    plan/ticket/decision/review/phase-ID history in comments and docstrings, code unchanged
affects: []

tech-stack:
  added: []
  patterns:
    - "argparse module docstrings (description=__doc__) are trimmed of history but kept as accurate
      --help text; same-code needs --allow <that file> for the file whose module docstring changed"
    - "large narrative evidence tables stored as string-literal tuple data (not comments/docstrings)
      are out of scope for the purge - the tool's extractor and the purge_rules both treat them as code"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/plane/illustrations.py
    - server/plane/colour_rules.py
    - server/plane/dither.py
    - server/plane/runway_config.py

key-decisions:
  - "render.py also reads `description=__doc__` for its CLI (missed by 35-CONTEXT.md's --help-docstring
    list, which named only illustrations.py). Extended the illustrations.py-only --allow precedent to
    render.py's module docstring too, since it is the same runtime-read pattern and the alternative
    (leaving its docstring's ~15 plan/decision IDs unpurged) would fail the plan's own 'no comment or
    docstring carries a history ID' truth."
  - "The plan's own Task 2 verify command (`same-code --base $B --allow file1 file1 file2 file3 file4`)
    is unrunnable as literally written: argparse's `--allow` uses nargs='*', which greedily swallows
    every token after it, leaving the positional `paths` argument empty and defaulting same-code to
    every changed file in the tree (which then failed on server/plane/render.py's already-committed
    docstring change from Task 1). Ran the equivalent command with `--allow` placed after the
    positional paths instead; verified the corrected invocation returns 0 and that dropping --allow
    entirely still passes for colour_rules.py/dither.py/runway_config.py."

requirements-completed: [HYG-01]

duration: ~35min
completed: "2026-09-25"
---

# Phase 35 Plan 02: Comment purge, server/plane part A Summary

Purged plan/ticket/decision/review/phase-ID history from every comment and docstring in
`server/plane/{render,illustrations,colour_rules,dither,runway_config}.py`, rewriting each to keep
only what/why, invariants, security invariants, units and spec pointers, in English, while leaving
all code (including the large per-airline evidence tables, which are string-literal data, not
comments) byte-for-byte unchanged.

## What was built

**Task 1 — `server/plane/render.py` (3044 -> 2804 lines; 312 -> 0 history hits).**

The file's module docstring, ~50 inline comment blocks, and ~30 function/class docstrings carried
`D-NN`, `Phase N`, `CFG-NN`, `T-NN-NN`, quick-task IDs, and multi-paragraph change narratives
(font-weight tuning sessions, illustration-crop debugging, band-theme rounds, etc.). Rewrote each to
its current why: layout invariants (SAFE_BOX vs. the frame/illustration inset), the opaque-bbox
anchoring rule (why `.content` and not `.rect`), the theme-weight/dithered-background resolution
chain, the four locked hold-screen copy blocks, and the diagonal-band trapezoid geometry. Discovered
mid-task that `render.py`'s CLI also builds its argparse parser with `description=__doc__` (this file
is not on 35-CONTEXT.md's runtime-`__doc__` list, which named only `companion/app.py`,
`deploy/backup/backup_gate.py`, `deploy/backup/skypane_backup.py` and `illustrations.py`) — see
Deviations.

**Task 2 — `illustrations.py`, `colour_rules.py`, `dither.py`, `runway_config.py` (98 -> 0 history hits
combined).**

- `illustrations.py`'s module docstring was the densest history in this file set: a ~160-line
  chronicle of quick tasks (`260827-kih`, `260827-jz6`, `260827-lgt`, `260921-v9c`), a live-resolution
  table with dates and curl transcripts, and a "superseded rule" narrative. Rewritten to ~25 lines
  describing the current selection algorithm (Tier 1-4), the correction seam
  (`enrich.correct_airline_name()`), the `_TYPE_SHAPE_BUCKETS` classifier, and the CLI's five flags —
  the argparse `--help` text this docstring feeds. Two inline comments referenced content that lived
  only in the now-shortened module docstring ("the module docstring's table above", "the
  `[DEVELOPER-OBSERVED]` token defined here and in HANDOFF.md"); both were rewritten to be
  self-contained or to point only at HANDOFF.md. Section-header comments inside `_LIVE_RESOLVED_
  AIRLINES`/`_ILLUSTRATION_TARGETS`/`_TYPE_SHAPE_BUCKETS` (`# --- Quick task 260827-jz6 ... ---`, per
  ICAO-type-family comments naming `D-03`/`260827-kih`/etc.) were purged of IDs while keeping the
  airline/shape groupings they document. The evidence strings inside each `_ILLUSTRATION_TARGETS`
  tuple (e.g. `"D-03 baseline; [VERIFIED-CALLSIGN]"`, the `[DEVELOPER-OBSERVED]` paragraphs) are
  **not** comments or docstrings — they are string-literal data consumed as-is by
  `target_airline_names()`/`target_variants_by_airline()` and rendered verbatim by
  `companion/pages/airlines_page.py` — so `check`'s extractor never flags them and the purge_rules'
  string-literal protection applies; they were left untouched.
- `colour_rules.py`: module docstring and ~10 inline comments (`D-07`/`D-08`/`D-09`/`D-12`/`D-13`,
  `T-15-01`/`T-15-02`/`T-15-04`/`T-15-05`, `WR-02`, `bare-plan-id`s) rewritten to keep the leaf-import
  invariant, the write-lock/TOCTOU rationale, and the resolver's calendar-beats-rule precedence.
- `dither.py`: module docstring and two inline comments (`03-RESEARCH.md Pitfall 2/3`, `Phase 7 07-01`)
  rewritten to keep the "no `.point()` remap", "no 256-entry palette padding", and "quantize against
  only {ink, White}" invariants.
- `runway_config.py`: module docstring and one docstring (`D-03`, `D-P2-04`, `A-02-02-01`,
  `T-02-02-01`, `Phase 1`) rewritten to keep the deadband/hold-last-state contract and the asymmetric
  evidence warning (descend threshold real-data-backed, climb threshold provisional).

**Verification.** `check --paths` reports 0 hits across all five files. `same-code` (run with
`--allow` placed after the positional file list, to avoid the argparse pitfall documented below)
returns 0 for all five, with `--allow` limited to `render.py`/`illustrations.py` — `colour_rules.py`,
`dither.py` and `runway_config.py` pass with no `--allow` at all, confirming their code and every
non-runtime-read docstring are byte-identical to base. `--help` on `illustrations.py`'s CLI still
prints a real usage line built from the trimmed docstring. 260 tests across
`test_render.py`/`test_illustrations.py`/`test_colour_rules.py`/`test_dither.py`/`test_runway_config.py`
pass, plus the full `pytest server -q -n auto` (717 passed, 3 pre-existing environment skips, 0
failed). `ruff check server/plane/` is clean.

## Comment ratio, before -> after

| File | Before | After | History hits before -> after |
|------|--------|-------|-------------------------------|
| server/plane/render.py | 52.14% | 48.11% | 312 -> 0 |
| server/plane/illustrations.py | 43.50% | 34.48% | 93 -> 0 |
| server/plane/colour_rules.py | 44.36% | 43.94% | 27 -> 0 |
| server/plane/dither.py | 53.57% | 52.55% | 10 -> 0 |
| server/plane/runway_config.py | 74.23% | 73.12% | 12 -> 0 |

Three files remain above the ~35% review-trigger threshold in 35-CONTEXT.md. Each carries dense
why-comments and invariant/security-invariant documentation the purge_rules require to survive
rather than be dropped:

- **runway_config.py (73.12%)** is a 93-line module whose entire value is a well-evidenced,
  asymmetric-confidence decision (the descend threshold is real-flight-data-backed, the climb
  threshold is symmetry-derived and unvalidated) — the docstring exists to keep a future reader from
  treating both thresholds as equally trustworthy. Short files with one dense decision naturally sit
  well above the ratio floor.
- **dither.py (52.55%)** documents three non-obvious Pillow footguns (256-entry palette padding, a
  `.point()` remap that would scramble palette indices, and the reason a full 6-color quantizer would
  mis-classify a lightened Blue/Green as the wrong ink) that are exactly the kind of "why, not what"
  the purge_rules protect.
- **render.py (48.11%)** is the largest and most layout-dense file in the phase: every pixel-offset
  constant (illustration centring fractions, text gaps, battery-icon geometry) carries a why-comment
  explaining the specific visual defect it fixes (per-file drop-shadow padding varying the aircraft's
  visible centre by 100+px, etc.) — dropping these would leave the next reader unable to tell a
  load-bearing offset from an arbitrary one. The pre-purge ratio (52.14%) barely moved because the
  bulk of each comment's line count was already why-content, not history; the purge mostly removed
  short ID fragments embedded inside otherwise-necessary sentences.

## Files Created/Modified

- `server/plane/render.py` - module docstring, ~50 inline comment blocks and ~30 docstrings purged of
  history; code unchanged (verified via same-code with `--allow` for the module docstring only)
- `server/plane/illustrations.py` - module docstring rewritten from a ~160-line chronicle to a
  ~25-line current-behaviour description feeding `argparse --help`; ~15 inline comment blocks and 4
  docstrings purged; the two large per-airline evidence tables (string-literal data) untouched
- `server/plane/colour_rules.py` - module docstring and ~10 comments/docstrings purged
- `server/plane/dither.py` - module docstring and 4 comments/docstrings purged
- `server/plane/runway_config.py` - module docstring and 1 docstring purged

## Decisions Made

- Extended the illustrations.py-only `--allow` treatment to `server/plane/render.py` as well, since
  render.py independently reads `description=__doc__` for its own CLI — a case 35-CONTEXT.md's
  runtime-`__doc__` file list missed. Documented the old/new first line for both files below, per the
  plan's illustrations.py instruction, applied to both files since both needed it.
- Left every string-literal "note" field inside `illustrations.py`'s `_ILLUSTRATION_TARGETS`/
  `_LIVE_RESOLVED_AIRLINES` tables untouched — these are data consumed by
  `companion/pages/airlines_page.py` and `target_airline_names()`, not comments, and the purge_rules
  explicitly protect string literals.

### render.py module docstring, old vs. new first line

- Old: `"""Minimal-but-real panel renderer for the plane view (PLANE-01/02/03).`
- New: `"""Panel renderer for the plane view: departure and arrival cards for the`

### illustrations.py module docstring, old vs. new first line

- Old: `"""Per-airline aircraft illustration selection (D-06, D-08, D-09, D-19,`
- New: `"""Per-airline aircraft illustration selection.`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] render.py also reads `description=__doc__`, which 35-CONTEXT.md's
--help-docstring list omitted**
- **Found during:** Task 1, while purging the module docstring's `D-21`/`D-24`/`D-25`/`D-26`/`D-27`/
  `Phase 3`/`Phase 7`/`Phase 8` history.
- **Issue:** The plan's Task 1 acceptance criteria requires `same-code --base "$BASE"
  server/plane/render.py` to exit 0 with **no** `--allow`, while the same task's `check --paths`
  requires 0 hits. `render.py:2823` has `parser = argparse.ArgumentParser(description=__doc__)`
  (grepped before editing), which the tool's `same-code` detects via a literal `"__doc__"` substring
  search and therefore keeps the module docstring in the AST comparison — so purging the docstring's
  history IDs (required for 0 hits) unavoidably makes `same-code` differ without `--allow`, no matter
  how the docstring is worded. 35-CONTEXT.md's list of runtime-`__doc__` files (`companion/app.py`,
  `deploy/backup/backup_gate.py`, `deploy/backup/skypane_backup.py`, `server/plane/illustrations.py`)
  does not include `render.py`, which is why the plan's Task 1 verify command has no `--allow`.
- **Fix:** Trimmed render.py's module docstring the same way illustrations.py's was trimmed (history
  removed, `--help`-accurate content kept), and ran `same-code` with `--allow
  server/plane/render.py` to confirm the docstring is the *only* difference from base. Documented the
  old/new first line above, mirroring the plan's own illustrations.py instruction.
- **Files modified:** `server/plane/render.py`
- **Commit:** 032929f

**2. [Rule 3 - Blocking] Task 2's own verify command's `--allow`/`paths` ordering is unrunnable as
written**
- **Found during:** Task 2, running the plan's literal verify command for the four-file same-code
  check.
- **Issue:** `same-code --base "$B" --allow server/plane/illustrations.py server/plane/illustrations.py
  server/plane/colour_rules.py server/plane/dither.py server/plane/runway_config.py` — the CLI
  defines `--allow` with `nargs="*"`, which greedily consumes every following token (including the
  four `paths` positionals), leaving `paths` empty. An empty `paths` list makes `same-code` default to
  *every* file changed since base (`git diff --name-only`), which by Task 2 time included
  `server/plane/render.py` from Task 1's already-landed commit — and `render.py` isn't in this
  (swallowed) `--allow` list, so the command reported `server/plane/render.py` as differing and exited
  1, even though every one of the four Task 2 files was correct.
- **Fix:** Ran the semantically equivalent command with the positional `paths` listed before `--allow`
  (`same-code --base "$B" file1 file2 file3 file4 --allow server/plane/illustrations.py`), which
  argparse parses unambiguously. Confirmed it returns 0, and separately confirmed
  `colour_rules.py`/`dither.py`/`runway_config.py` pass with no `--allow` argument at all (isolating
  that only `illustrations.py`'s docstring differs). No tool or file changed — this is a
  command-invocation correction, not a code fix.
- **Files modified:** none (verification-only)
- **Commit:** n/a (no code change; recorded here for the group's review record)

---

**Total deviations:** 2 auto-fixed (2 blocking/verify-command corrections, no code beyond the
in-scope docstring purge)
**Impact on plan:** Both are verification-command corrections needed to prove the purge is correct
under the plan's own truths; neither required any code change beyond the comment/docstring purge
already in scope. No scope creep.

## Issues Encountered

None beyond the two documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`server/plane/render.py`, `illustrations.py`, `colour_rules.py`, `dither.py` and `runway_config.py`
are fully purged (0 history hits) and code-unchanged. The remaining `server/plane/` modules
(`calendar_rules.py`, `detect.py`, `enrich.py`, `manual_resolutions.py`, `__init__.py`) and the rest
of `server/` are out of this plan's `files_modified` scope and remain for a later plan in this wave
or group.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `server/plane/render.py` — FOUND
- `server/plane/illustrations.py` — FOUND
- `server/plane/colour_rules.py` — FOUND
- `server/plane/dither.py` — FOUND
- `server/plane/runway_config.py` — FOUND
- Commit 032929f (Task 1: render.py) — FOUND
- Commit 13100b3 (Task 2: illustrations/colour_rules/dither/runway_config) — FOUND
