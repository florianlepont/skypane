---
phase: 35-comment-purge-in-english-and-dead-code
plan: 03
subsystem: server-plane-detection
tags: [comment-hygiene, docstrings, calendar, enrichment, detection, manual-resolutions]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 01
    provides: scripts/check_comment_history.py (check/ratio/same-code), scripts/comment-history-pending.txt
provides:
  - server/plane/calendar_rules.py, enrich.py, detect.py, manual_resolutions.py purged of
    plan/ticket/decision/review/threat-ID history in comments and docstrings, code unchanged
affects: []

tech-stack:
  added: []
  patterns:
    - "argparse help-text string literals (detect.py's --provider/--runway help, description=) are
      NOT docstrings and are never scanned by check/same-code - a history ID embedded in a regular
      string literal (e.g. 'D-P2-01', 'T-06-02-01' inside build_parser()'s argparse strings) is left
      untouched per purge_rules' 'never edit string literals' rule, even though it looks like the
      history the purge otherwise removes. Do not touch these; same-code's AST diff will fail
      immediately if a regular string literal changes."
    - "one-line trailing inline comments after a dict-literal entry (e.g. enrich.py's
      _ICAO_AIRLINE_PREFIXES) count as full comment_lines in the ratio tool even though most of the
      line is code - dropping a purely evidentiary citation ('# cited callsign X', '# callsign Y')
      that adds no invariant beyond the entry's own value is a meaningful ratio lever distinct from
      docstring compression, and was applied to enrich.py's data table."

key-files:
  created: []
  modified:
    - server/plane/calendar_rules.py
    - server/plane/enrich.py
    - server/plane/detect.py
    - server/plane/manual_resolutions.py

key-decisions:
  - "All four files stay above the 35% comment-ratio guideline after two compression passes each
    (an initial full-file purge, then a targeted second pass on the largest remaining docstrings).
    Each file's remaining density is justified per-file below rather than compressed further, since
    further cuts started removing genuine correctness/security invariants (gate ordering, tamper
    vectors, DoS bounds, cross-process locking rationale) rather than restatement or history."
  - "enrich.py's _ICAO_AIRLINE_PREFIXES table: dropped every purely evidentiary trailing comment
    ('# cited callsign X', '# airline endpoint Y') that recorded only how a mapping was verified,
    while keeping every comment that explains *why* a mapping diverges from what adsbdb itself would
    resolve (corrected brand names, state-vs-commercial distinctions, a defensive typo-alias) - the
    former is a work-log entry the purge_rules class as history; the latter is exactly the kind of
    why-comment a future contributor needs so they don't 'helpfully' revert a deliberate correction."

requirements-completed: [HYG-01]

duration: ~90min
completed: "2026-09-25"
---

# Phase 35 Plan 03: Comment purge, server/plane part B Summary

Purged plan/ticket/decision/review/threat-ID history from every comment and docstring in
`server/plane/{calendar_rules,enrich,detect,manual_resolutions}.py`, rewriting each to keep only
what/why, invariants, security invariants, units and spec pointers, in English, while leaving all
code byte-for-byte unchanged (verified via `same-code --base ee2737a`, no `--allow` needed anywhere
in this plan).

## What was built

**Task 1 — `server/plane/calendar_rules.py` (2221 -> 1418 lines; 118 -> 0 history hits).**

The densest file in this plan: a module docstring, ~45 inline comment/section-header blocks, and
~30 function docstrings carried `plan 16-NN`, `D-NN`, `WR-NN`, `UAT-02`, `CR-01`, `IN-01`,
`T-16-NN`/`T-17-NN` history and multi-paragraph incident narrative (the raw-order-vs-windowed
cap bug, the `webcal://` normalisation fix, the cross-process lock rationale). Rewrote each to its
current why: the leaf-import contract (why this module can never import `colour_rules`, on pain of
an import cycle through `poll_loop.py`), the cross-process `fcntl` lock's reason for existing
alongside a same-process `threading.Lock`, the window-before-cap ordering invariant (windowing after
capping in raw file order silently discards every future flight when a feed lists history first),
the SSRF-hardened fetch's four independent bounds, and the calendar-to-flight matching algorithm's
field-presence/tie-break rules. Two compression passes: an initial ID-removal pass to 41.56%, then a
targeted second pass tightening the five largest remaining docstrings (`save_calendar_url()`,
`fetch_ics()`, `_rebuild_capped_entries()`, `refresh_calendar_registry()`, `match_calendar_theme()`)
to 40.20%.

**Task 2 — `enrich.py`, `detect.py`, `manual_resolutions.py` (169 -> 0 history hits combined).**

- `enrich.py` (1157 -> 773 lines): the module docstring and the multi-source resolution seam
  (`resolve_route()`'s five-way classification, `airline_source_from_callsign()`'s static-then-manual
  precedence) carried the densest per-function history. The `_ICAO_AIRLINE_PREFIXES`/
  `_AIRLINE_NAME_CORRECTIONS` data tables (~290 lines combined) were the heaviest single block:
  every entry's justification was rewritten from a quick-task-ID-and-curl-transcript narrative to a
  one-to-three-line why (a corrected brand name, a state-vs-commercial distinction, a defensive
  typo-alias), and every purely evidentiary trailing comment (`# cited callsign X`) that recorded
  only how an entry was verified, without any invariant a future contributor needs, was dropped
  outright — see key-decisions above.
- `detect.py` (1129 -> 857 lines): `poll_current_aircraft()`'s docstring (originally ~125 lines,
  documenting the candidate-set-vs-final-pick corroboration algorithm with a full incident writeup)
  and `filter_in_geofence()`'s docstring (~83 lines, documenting seven output-dict fields plus the
  airborne-vs-ground corridor distinction) were the two densest. Both were rewritten to keep the
  algorithmic contract and the concrete why (measured feed-disagreement rates, the specific failure
  mode each gate closes) while dropping session narrative, dates, and debug-log file pointers. Two
  argparse help strings (`build_parser()`'s `--provider`/`--runway` help and its `description=`) were
  initially over-purged in the first pass — see Deviations — and restored byte-for-byte since they
  are string literals, not docstrings, and out of scope for this plan.
- `manual_resolutions.py` (508 -> 430 lines): the module docstring and the write-lock/tamper-vector
  discussion (`add_entry()`, `delete_entry()`, `load_manual_resolutions()`) were rewritten to keep
  the file-contract mirror of `device_config.py`, the two-layer path-safety defence
  (`_SAFE_KEY_RE` plus the raw-input `_HOSTILE_NAME_RE` check), and the `_WRITE_LOCK` rationale
  (why a `ThreadingHTTPServer`'s two write endpoints need one atomic load-modify-write cycle, not
  just a locked final replace).

**Verification.** `check --paths` reports 0 hits across all four files. `same-code --base ee2737a`
returns 0 for all four with no `--allow` anywhere — confirming every file's code, including the large
`_ICAO_AIRLINE_PREFIXES`/`_AIRLINE_NAME_CORRECTIONS` dict literals, is byte-identical to base once
comments and docstrings are stripped from the AST comparison. `server/test_calendar_rules.py` (113),
`server/test_enrich.py` (60), `server/test_plane_detection.py` (47) and
`server/test_manual_resolutions.py` (21 passed, 2 pre-existing root-euid skips) all pass individually,
and the full `pytest server -q -n auto` is green (717 passed, 3 pre-existing skips, 0 failed).
`ruff check` is clean on all four files.

## Comment ratio, before -> after

| File | Original | After purge | History hits |
|------|----------|-------------|---------------|
| server/plane/calendar_rules.py | 61.82% | **40.20%** | 118 -> 0 |
| server/plane/enrich.py | 68.71% | **50.58%** | 95 -> 0 |
| server/plane/detect.py | 58.90% | **45.86%** | 46 -> 0 |
| server/plane/manual_resolutions.py | 53.54% | **45.12%** | 28 -> 0 |

All four files stay above the ~35% review-trigger threshold even after two compression passes each.
Each is justified for a distinct, file-scoped reason rather than leftover verbosity — every file was
re-read a second time specifically hunting for restatement, scope talk, and "who calls this" asides,
and none remained to cut without also cutting a genuine invariant:

- **calendar_rules.py (40.20%, 1418 lines)** concentrates six largely-independent security/
  correctness domains in one file: an SSRF-hardened outbound fetch (four independent bounds), a
  cross-process `fcntl` advisory lock (needed because a `threading.Lock` is invisible across the
  poll oneshot's and companion's separate OS processes), a hand-rolled RFC 5545 subset parser, a
  tamper-resistant JSON registry with two distinct DoS bounds (raw-examination ceiling vs.
  post-window cap, and why they must be applied in that order), a secret-file permission-drift
  detector, and a calendar-to-flight matching algorithm with a six-step field-presence/tie-break
  contract. Each domain earns its own short why-comment; the file has no single domain diluting the
  ratio through avoidable length — the five largest remaining docstrings (`save_calendar_url()`,
  `fetch_ics()`, `refresh_calendar_registry()`, `match_calendar_theme()`, `_rebuild_capped_entries()`)
  were each independently compressed a second time and are already near the floor for their
  correctness-critical content.
- **enrich.py (50.58%, 773 lines)** is dominated by one 46-entry curated data table
  (`_ICAO_AIRLINE_PREFIXES`) where roughly a third of the entries require a short correction/
  attribution rationale specifically so a future contributor does not "fix" a deliberately
  non-obvious mapping — e.g. three entries hold a corrected brand name that diverges from what
  adsbdb itself still resolves to, several distinguish a state/charter operator from a commercial
  airline, and one is a defensive typo-alias for a likely misread callsign. Every purely evidentiary
  trailing citation was already stripped (see key-decisions); what remains is one line-or-less of
  genuine why per flagged entry, on a table that is inherently 290 lines of the file's 773. The
  surrounding functions (the five-source `resolve_route()` classification, the static-then-manual
  precedence in `airline_source_from_callsign()`) each carry one non-obvious security-relevant gate
  order that purge_rules require to survive.
- **detect.py (45.86%, 857 lines)** carries two functions whose docstrings document a genuinely
  complex contract: `poll_current_aircraft()`'s candidate-set cross-validation algorithm (why
  comparing final picks alone manufactures false disagreements between two independent feeder
  networks, and the specific safety property that is preserved rather than weakened by comparing
  sets instead) and `filter_in_geofence()`'s seven-field output-tag contract plus the airborne-vs-
  ground corridor distinction. Both were compressed to their algorithmic essence and a concrete
  measured-consequence sentence per invariant; further cuts would drop the contract itself, not
  restatement.
- **manual_resolutions.py (45.12%, 430 lines)** is a small, security-dense file by design: it is
  this project's first runtime-writable identity namespace, and nearly every function documents a
  distinct defence-in-depth layer (the two-layer path-safety check, the write-lock's role versus a
  plain "last write wins" race, the deliberate choice not to touch the illustration-override
  directory on delete). A 430-line file whose entire content is these five or six short invariants
  cannot mathematically sit under 35% without cutting one of them.

## Files Created/Modified

- `server/plane/calendar_rules.py` - module docstring, ~45 inline comment/section-header blocks and
  ~30 docstrings purged of history; code unchanged (same-code, no `--allow`)
- `server/plane/enrich.py` - module docstring purged; the two ICAO-prefix data tables' per-entry
  comments rewritten from quick-task-ID-and-transcript narrative to short why-only notes, purely
  evidentiary trailing citations dropped; ~15 function docstrings purged
- `server/plane/detect.py` - module docstring, the `PROVIDERS` dict's ~40-line comment block, and
  ~18 function docstrings purged; two argparse help string literals restored byte-for-byte after an
  in-scope-boundary mistake during the first pass (see Deviations)
- `server/plane/manual_resolutions.py` - module docstring and ~12 function docstrings purged

## Decisions Made

- Compressed every file in two passes rather than one: an initial ID-removal pass, then a second
  pass specifically re-reading the largest remaining docstrings (each still 20+ lines after pass
  one) and cutting to a one-line summary plus a compact contract, mirroring the tightening pass
  35-02 applied under orchestrator review. Documented as key-decisions above.
- Dropped purely evidentiary trailing comments in `enrich.py`'s `_ICAO_AIRLINE_PREFIXES` table
  (`# cited callsign X`, `# airline endpoint Y`) that recorded only how a mapping was verified,
  since the ratio tool counts a comment-carrying line in full even when most of the line is code,
  and these citations added no invariant beyond the entry's own value.
- Accepted all four files above the 35% guideline with a specific, file-scoped justification each
  (see the ratio table above), rather than cutting further into genuine correctness/security
  invariants to force the number down.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `detect.py`'s first purge pass edited two argparse help string literals,
outside this plan's scope**
- **Found during:** Task 2, verifying `same-code --base ee2737a server/plane/detect.py` after the
  first purge pass.
- **Issue:** While condensing `build_parser()`'s surrounding comments, the argparse
  `description="...(D-P2-01)."` string and the `--runway` help text's `"...T-06-02-01 is the
  library-level fallback..."` string were also edited to remove their embedded history IDs — an
  easy mistake given they read like the same kind of prose the rest of the purge was rewriting, but
  they are regular string literals (CLI `--help` text), not docstrings, and `purge_rules` explicitly
  forbids editing string literals. `same-code` immediately caught this as an AST diff (the tool
  compares the full AST after stripping only comments/docstrings, so any change to a string literal
  shows up as a genuine code difference).
- **Fix:** Reverted both strings to their exact original text via a diff-only edit, re-ran
  `same-code`, confirmed it now returns 0 with no `--allow`. Left the embedded `D-P2-01`/
  `T-06-02-01` IDs in place inside these two strings — `check`'s extractor only scans
  comment/docstring spans, never regular string literals, so these are not flagged as history hits
  and are correctly out of this plan's scope (a markdown-facing rewrite of user-visible `--help`
  text, if ever wanted, belongs to a different, string-literal-aware pass, not this comment purge).
- **Files modified:** `server/plane/detect.py`
- **Commit:** 2db6ba1 (the corrected version is what was committed; the mistaken intermediate edit
  never reached a commit)

---

**Total deviations:** 1 auto-fixed (Rule 1: a same-code-caught scope violation, corrected before
committing)
**Impact on plan:** No code change beyond the in-scope comment/docstring purge landed in any commit;
the string-literal mistake was caught by the plan's own verification gate before it was ever
committed. No scope creep.

## Issues Encountered

None beyond the one documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`server/plane/calendar_rules.py`, `enrich.py`, `detect.py` and `manual_resolutions.py` are fully
purged (0 history hits each) and code-unchanged. Combined with 35-02's five files, all of
`server/plane/` except `__init__.py` (trivial) is now purged. The rest of `server/` (poll_loop.py,
device_config.py, history_db.py, and friends) remains for a later plan in this group.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `server/plane/calendar_rules.py` — FOUND
- `server/plane/enrich.py` — FOUND
- `server/plane/detect.py` — FOUND
- `server/plane/manual_resolutions.py` — FOUND
- Commit 24847df (Task 1: calendar_rules.py) — FOUND
- Commit 2db6ba1 (Task 2: enrich/detect/manual_resolutions.py) — FOUND
