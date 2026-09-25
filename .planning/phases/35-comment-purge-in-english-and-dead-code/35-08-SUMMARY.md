---
phase: 35-comment-purge-in-english-and-dead-code
plan: 08
subsystem: companion-comment-hygiene
tags: [comment-hygiene, companion, auth, security-invariants, wcag, battery-estimate]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 07
    provides: "stub-server/ fully purged and CI-enforced (group 3 closed); scripts/check_comment_history.py (check/ratio/same-code) stable"
provides:
  - "companion/app.py, auth.py, __init__.py, battery.py, frame_state.py, i18n.py, prefs.py,
    screens.py, wake.py, illustration_normalize.py, contrast_check.py, theme_preview.py purged
    of plan/ticket/decision/review/phase-ID history (0 hits across all 12 files), code unchanged"
  - "per-file before/after comment ratios and above-35% justifications, recorded in this SUMMARY
    (the group-4 closing plan folds them into 35-COMMENT-RATIO.md)"
affects: [35-09, 35-10, 35-11, 35-12, 35-13]

tech-stack:
  added: []
  patterns:
    - "same-code needs --allow companion/app.py only for its argparse module docstring
      (description=__doc__); a second same-code run with no --allow fails only on that
      docstring, confirming no other file in the group differs on code"
    - "repeated near-identical docstring paragraphs (the 'No CSRF token: SameSite=Strict...'
      block appeared 3x verbatim in app.py) are a purge_bar restatement violation independent
      of history-ID content: kept the fullest occurrence, compressed the other two to a
      one-line pointer back to it"
    - "a run of near-identical thin-delegate methods (17 _serve_*_script() methods in app.py,
      each with its own per-constant docstring restating 'thin delegate... mirroring X's shape
      exactly') collapses to one shared comment above the group and bare one-line method bodies,
      since same-code strips function docstrings from its AST comparison entirely (only the
      module docstring needs --allow), so dropping them costs nothing on the code-unchanged proof"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/auth.py
    - companion/__init__.py
    - companion/battery.py
    - companion/frame_state.py
    - companion/i18n.py
    - companion/prefs.py
    - companion/screens.py
    - companion/wake.py
    - companion/illustration_normalize.py
    - companion/contrast_check.py
    - companion/theme_preview.py

key-decisions:
  - "app.py's module docstring (the argparse --help text) was trimmed from a 37-line docstring
    naming D-02/D-22/SEC-01/06-CONTEXT.md etc. to a 26-line docstring keeping only the
    whole-site auth gate, the --bind/Caddy rationale, the poll-pipeline single-writer
    invariant and the startup-refusal contract — same-code needs --allow companion/app.py
    for this file alone, confirmed by a second same-code run with no --allow (fails only on
    the module docstring)."
  - "auth.py's display-mode-cookie history comment (the sibling per-browser cookie a retired
    switch used, ~lines 61-66 before this plan) was deleted outright per the plan's own
    instruction, rather than compressed to a why — there was no surviving why to keep, since
    the feature and its cookie are both gone and nothing under companion/ reads that cookie
    name again."
  - "Kept, concisely, in every file: auth/session/CSRF/throttle security invariants (constant-time
    password compare, HMAC-derived signing key, Origin/Sec-Fetch-Site gate reasoning, login
    throttle bucket-eviction trade-off), cookie-flag reasoning (Secure/HttpOnly/SameSite),
    the WCAG 2.1 formula pointers in contrast_check.py, and the millivolt/percent units and
    curve-derivation math in battery.py — matching the plan's must_haves."
  - "A second (tightening) pass, requested by the orchestrator after reviewing the first pass's
    ratios as insufficiently compressed, applied hard per-block caps (module docstring ≤10
    lines/≤15 for app.py's argparse text, function/class docstring ≤8 lines/≤15 for genuine
    security or contract content, comment blocks ≤5 lines) and deleted every numbered
    narration list, module tour, and 'sits beside'/who-consumes-list paragraph outright,
    keeping only the load-bearing invariant sentence(s). app.py landed at 29.1%, auth.py at
    34.4% (both under the ~35% target); every small module dropped further still, documented
    per-file in the ratio table below."

requirements-completed: []

duration: ~2h
completed: "2026-09-25"
---

# Phase 35 Plan 08: companion app.py, auth.py and small modules purge Summary

Purged plan/ticket/decision/review/phase-ID history from `companion/app.py` (the companion
service's 3,700-line route table and every handler), `companion/auth.py` (the shared-password
session/CSRF gate), and nine small page-independent modules (`__init__.py`, `battery.py`,
`frame_state.py`, `i18n.py`, `prefs.py`, `screens.py`, `wake.py`, `illustration_normalize.py`,
`contrast_check.py`, `theme_preview.py`), keeping every auth/session/CSRF/throttle security
invariant, cookie-flag rationale, WCAG formula pointer and millivolt/percent unit as a concise
why-comment, in English, with all code byte-for-byte unchanged (AST-equal modulo docstrings);
`app.py`'s argparse `--help` text was trimmed to accurate current-state usage.

## Performance

- **Duration:** ~2h
- **Completed:** 2026-09-25T10:56Z
- **Tasks:** 2 completed
- **Files modified:** 12

## Accomplishments

- `companion/app.py`: purged the module docstring (argparse `--help` text — see the recorded
  before/after below), every module-level constant comment (the fifteen-plus `*_SCRIPT_ROUTE`
  constants collapsed from one restated invariant per constant to one shared comment above the
  block), the `FLASH_MESSAGES`/`FLASH_ROLES` dicts' per-key history comments, and every route
  handler's docstring — including the two most security-dense ones,
  `_handle_illustration_replace()` (the first untrusted file upload this codebase handles: the
  six-step membership-test-before-any-path-is-built order) and `_handle_settings_post()` (the
  `_POLL_LOCK`-is-process-local-not-cross-process correction, and the fcntl-flock-based
  cross-process lock that actually protects the calendar-registry race) — both kept in full as
  ordered security-property lists, only shorter. 457 -> 0 history hits, 57.16% -> 47.08% comment
  ratio (3744 -> 3027 lines; the drop in line count is comment compression, not code deletion).
- `companion/auth.py`: purged the module docstring and every function/class docstring and
  comment, dropping the display-mode-cookie history comment entirely (no surviving why to
  keep — the plan's own scoped deletion). Kept the constant-time `hmac.compare_digest()`
  password check, the HMAC-derived (never raw-password) signing key, the nanosecond-resolution
  token-collision reasoning, the Secure/HttpOnly/SameSite cookie-flag rationale, the
  LoginThrottle per-address bucket/eviction trade-off, and the full Origin/Sec-Fetch-Site CSRF
  gate reasoning (`post_origin_ok()`'s four-rule order). 43 -> 0 history hits, 51.67% -> 50.00%
  ratio (540 -> 522 lines).
- The nine small modules: purged every history reference while keeping each module's real
  why — `contrast_check.py`'s WCAG 2.1 SC 1.4.3 spec pointers and signal-separation
  calibration numbers; `battery.py`'s 14-knot millivolt-to-percent curve derivation, the
  companion-display-vs-device-warning threshold distinction, and the no-per-wake-cost
  discharge-projection reasoning; `frame_state.py`'s single-source-of-truth state-resolution
  contract; `theme_preview.py`'s cache-key invalidation scheme and crop-box pixel-geometry
  math; `screens.py`'s registry design; `prefs.py`'s one-set-path/two-read-path discipline;
  `wake.py`'s single-import-path rationale; `i18n.py`'s translate-then-escape contract; and
  `illustration_normalize.py`'s crop-then-recentre fix and target-frame-size derivation.
  102 -> 0 history hits across the nine files combined.
- `same-code --base 059774e` passes for all twelve files: `--allow companion/app.py` (its
  module docstring, argparse `--help` text) is required, and every other file passes with no
  `--allow`; a second `same-code` run confirms `companion/app.py` differs only in that one
  docstring when `--allow` is omitted. `check --paths` (all twelve files) reports 0 history
  hits. `pytest companion -q -n auto` -> 1545 passed, 129 skipped (pre-existing Playwright
  browser-shell absence, unrelated to this plan). `ruff check` on all twelve files -> "All
  checks passed!". The dead-code guard
  (`git diff "$BASE" -- companion/ | grep -E '^-def (health_severity|anomaly_active|
  usable_pairs|label_grid)'`) is empty: no function was deleted (HYG-05 is 35-13's job).

## Task Commits

1. **Task 1: Purge companion/app.py** - `113ad8a` (refactor)
2. **Task 2: Purge auth.py and the small modules, then run the companion suite** - `c441a0e` (refactor)
3. **Second pass: tighten comment/docstring compression to hard caps (orchestrator review)** -
   `be2578f` (docs)

**Plan metadata:** pending (final docs commit, this file + STATE.md/ROADMAP.md)

## Files Created/Modified

- `companion/app.py` - module docstring (argparse `--help` text), every module-level constant
  comment, the `FLASH_MESSAGES`/`FLASH_ROLES` dicts, every route handler docstring
- `companion/auth.py` - module docstring, every function/class docstring and comment; the
  display-mode-cookie history comment deleted outright
- `companion/__init__.py` - one-line module docstring
- `companion/battery.py` - module docstring and every comment; millivolt/percent units and
  curve-derivation math kept
- `companion/frame_state.py` - module docstring and every docstring/comment; single-source-of-
  truth state-resolution contract kept
- `companion/i18n.py` - module and function docstrings
- `companion/prefs.py` - module docstring; the retired display-mode-preference paragraph
  dropped as a comment about a removed feature
- `companion/screens.py` - module docstring and every comment; per-group registry design kept
- `companion/wake.py` - module docstring, compressed to the re-export shim's single-import-
  path rationale
- `companion/illustration_normalize.py` - module docstring and constant comments; crop/
  recentre geometry math kept
- `companion/contrast_check.py` - module docstring and comments; WCAG formula pointers and
  calibration numbers kept
- `companion/theme_preview.py` - module docstring and every function docstring/comment;
  cache-key invalidation scheme and crop-box geometry math kept

## `--help` text before/after (companion/app.py)

**Before (first paragraph, 5 lines):**
```
companion/app.py — the SkyPane companion service entrypoint: a stdlib
`ThreadingHTTPServer` plus a hand-rolled route table, mirroring
`stub-server/byos_server.py`'s own shape (D-03, 06-CONTEXT.md: this is a
separate process, its own systemd unit — it never touches that vendored
device-protocol server).
```

**After (first paragraph, 3 lines):**
```
SkyPane companion service: a stdlib `ThreadingHTTPServer` with a
hand-rolled route table, run as its own systemd unit, separate from the
vendored device-protocol server in `stub-server/`.
```

The rest of the docstring (whole-site auth-gate exemption list, `--bind`/Caddy rationale,
poll-pipeline single-writer invariant, startup-refusal contract) is unchanged in substance,
compressed line-for-line by dropping history IDs. `python -m companion.app --help` still
prints accurate usage text (verified below).

## Comment ratios (before -> pass 1 -> pass 2 tightened)

Source: `35-BASELINE/ratio-before.tsv` (before) and `check_comment_history.py ratio` on this
plan's own HEAD (pass 1, then pass 2 after the orchestrator's tightening review). The group-4
closing plan folds this table into `35-COMMENT-RATIO.md` alongside the rest of the
companion-production group.

Pass 2 applied hard per-block caps (module docstring ≤10 lines, ≤15 for app.py's argparse
`--help` text; function/class docstring ≤8 lines, ≤15 for genuine security/contract content;
comment blocks ≤5 lines) and deleted module-tour/"sits beside"/who-consumes-list prose entirely,
replacing numbered narration lists with the load-bearing invariant sentence(s) only.

| File | Lines before | Lines pass 1 | Lines pass 2 | Comment % before | Comment % pass 1 | Comment % pass 2 | History hits |
|---|---:|---:|---:|---:|---:|---:|---:|
| companion/__init__.py | 1 | 1 | 1 | 100.0% | 100.0% | 100.0% | 0 |
| companion/app.py | 3744 | 3027 | 2258 | 57.2% | 47.1% | **29.1%** | 0 |
| companion/auth.py | 540 | 522 | 398 | 51.7% | 50.0% | **34.4%** | 0 |
| companion/battery.py | 457 | 433 | 269 | 63.0% | 61.0% | 37.2% | 0 |
| companion/contrast_check.py | 226 | 211 | 154 | 62.0% | 59.2% | 44.2% | 0 |
| companion/frame_state.py | 216 | 197 | 102 | 69.9% | 67.0% | 36.3% | 0 |
| companion/i18n.py | 42 | 41 | 29 | 66.7% | 65.9% | 51.7% | 0 |
| companion/illustration_normalize.py | 153 | 142 | 86 | 68.6% | 66.2% | 44.2% | 0 |
| companion/prefs.py | 59 | 45 | 30 | 76.3% | 68.9% | 53.3% | 0 |
| companion/screens.py | 139 | 114 | 81 | 68.4% | 61.4% | 45.7% | 0 |
| companion/theme_preview.py | 376 | 364 | 208 | 62.5% | 61.3% | 32.2% | 0 |
| companion/wake.py | 38 | 19 | 19 | 78.9% | 57.9% | 57.9% | 0 |
| **Group total** | **5991** | **5116** | **3635** | **58.9%** | **49.3%** | **34.5%** | **0** |

Both target files land at or under the ~35% ceiling: `app.py` 29.1%, `auth.py` 34.4%. Every
small module dropped substantially further (e.g. `frame_state.py` 67.0% -> 36.3%, `theme_preview.py`
61.3% -> 32.2%, `screens.py` 61.4% -> 45.7%), each now "as low as its genuine content allows" —
the remaining lines are per-function invariant sentences and named-constant units, not
restatement, module tours or numbered body narration (all deleted in this pass).

### Files still above the ~35% guideline (pass 2)

| File | Pass 2 | Justification |
|---|---:|---|
| companion/battery.py | 37.2% | `battery_life_estimate()`'s docstring is kept at 14 lines (within the ≤15 security/contract exception) as the one place the output-field contract (which callers key off) is documented; the curve-derivation and threshold-distinction comments are each ≤5 lines. |
| companion/contrast_check.py | 44.2% | A pure-stdlib WCAG 2.1 implementation with very little code to dilute against: the spec URL pointers (required to stay per the plan), three calibration-number comments and one signal-separation-vs-contrast distinction, all now ≤5-line blocks. |
| companion/frame_state.py | 36.3% | A 102-line single-source-of-truth state machine; module docstring and all four docstrings are now ≤8 lines (module docstring in fact ≤6), holding only the state/delay contract sentences every consumer relies on. |
| companion/i18n.py | 51.7% | A 29-line module: one real function and its test-only sibling, each with a short never-raise contract; two documented functions in a file this size cannot go lower without dropping the contract itself. |
| companion/illustration_normalize.py | 44.2% | An 86-line geometry module: the crop-box derivation constant comment (5 lines) and the two function docstrings (≤8 and ≤5 lines) are the file's only comments. |
| companion/prefs.py | 53.3% | A 30-line module whose only content is the one-set-path/two-read-path invariant; module docstring is 9 lines, at the small-file floor for stating it at all. |
| companion/screens.py | 45.7% | An 81-line registry module: module docstring (8 lines) plus short per-group split/render-order comments, each ≤5 lines. |
| companion/theme_preview.py | 32.2% | Now under 35% itself; kept for completeness — a cache/geometry module whose function docstrings were cut from 5 verbose paragraphs each to ≤8-line invariant statements. |
| companion/wake.py | 57.9% | A 19-line re-export shim; unchanged from pass 1 (already at the tiny-file floor — the docstring explaining why the shim exists is the whole file's content, no numbered lists or module tour to cut). |
| companion/__init__.py | 100.0% | A one-line file: a single docstring, no code at all. Ratio is not a meaningful signal at this size. |

## Decisions Made

- `same-code` for `companion/app.py` requires `--allow companion/app.py`, matching the group's
  own runtime-`__doc__` precedent already established for `server/plane/illustrations.py` and
  `stub-server/byos_server.py` in earlier plans — confirmed by grepping for the literal
  substring `__doc__` in `companion/app.py` (`ArgumentParser(description=__doc__)` in
  `build_parser()`) and by a second `same-code` run with no `--allow`, which fails only on the
  module docstring.
- Collapsed the seventeen near-identical `_serve_*_script()` delegate methods in `app.py` (each
  had its own per-constant docstring restating "thin delegate onto `_serve_script_file()`,
  mirroring X's shape exactly" plus a history ID) to one shared comment above the group and bare
  one-line method bodies. `same-code` strips function docstrings from its AST comparison
  entirely (confirmed: only the module docstring needed `--allow`), so this was free on the
  code-unchanged proof and a genuine purge_bar fix (restatement of the next line, repeated
  seventeen times) independent of the history-ID content.
- Deleted `auth.py`'s display-mode-cookie history comment (the sibling per-browser cookie a
  retired display-mode switch used) entirely rather than rewriting it to a why, per the plan's
  own explicit scope instruction — there is no surviving why once the feature and its cookie
  are both gone.
- Ran a second (tightening) pass after the orchestrator judged the first pass's ratios
  insufficiently compressed: applied hard per-block line caps (module docstring ≤10/≤15 lines,
  function/class docstring ≤8/≤15 lines, comment blocks ≤5 lines) file by file, deleting every
  numbered narration list, module tour and "sits beside"/who-consumes-list paragraph outright
  and keeping only the invariant sentence(s) a caller actually depends on. `app.py` (29.1%) and
  `auth.py` (34.4%) now both land at or under the ~35% target; the nine small modules dropped
  further still (documented per-file above) without losing any required security/WCAG/unit
  why-comment.

## Deviations from Plan

None - plan executed exactly as written. The `same-code --allow companion/app.py` requirement
and the module-docstring recording were both anticipated by the plan's own task instructions.

## Issues Encountered

None. One large `Edit` call against `companion/app.py` failed on a string-match mismatch
partway through the file (a large multi-paragraph old_string spanning a section that had
already shifted after a prior edit); recovered by re-reading the affected region and splitting
the edit into smaller, precisely-matched pieces — no impact on the final result, not counted as
a deviation since no code or comment content was lost or left inconsistent.

## User Setup Required

None - no external service configuration required.

## Verification Results

- **Task 1 same-code:** `same-code --base 059774e --allow companion/app.py companion/app.py`
  -> exit 0; `same-code --base 059774e companion/app.py` (no `--allow`) -> exit 1, differing
  only on `companion/app.py` (the module docstring), confirming no code changed.
- **Task 1 check:** `check --paths companion/app.py` -> 0 history hits.
- **Task 1 --help:** `python -m companion.app --help` -> prints accurate usage text.
- **Task 1 ruff:** `ruff check companion/app.py` -> "All checks passed!".
- **Task 2 same-code:** `same-code --base 059774e` over the eleven small/auth files -> exit 0
  (no `--allow` needed for any of them).
- **Task 2 check:** `check --paths` over the eleven files -> 0 history hits.
- **Task 2 dead-code guard:** `git diff 059774e -- companion/ | grep -E '^-def
  (health_severity|anomaly_active|usable_pairs|label_grid)'` -> empty (no function deleted).
- **Full companion suite:** `pytest companion -q -n auto` -> 1545 passed, 129 skipped
  (pre-existing Playwright headless-shell absence, unrelated to this plan), 0 failed.
- **ruff (all twelve files):** `ruff check companion/app.py companion/auth.py
  companion/__init__.py companion/battery.py companion/frame_state.py companion/i18n.py
  companion/prefs.py companion/screens.py companion/wake.py
  companion/illustration_normalize.py companion/contrast_check.py companion/theme_preview.py`
  -> "All checks passed!".
- **Comment-history guard scope:** these twelve files remain listed in
  `scripts/comment-history-pending.txt` (not removed by this plan — that is the group-4
  closing plan's job, per this phase's ratchet-rollout convention observed in every prior
  non-closing plan in this phase).
- **PR / push:** not performed by this executor — per the orchestrator's instructions, this
  plan stayed on `claude/plan-phase-35` and did not push or open a PR.
- **REQUIREMENTS.md:** HYG-01 intentionally left unmarked, per the executor's instructions,
  since it spans later groups (companion tests, companion JS, style.css) not yet purged.
- **Second pass (tightening) same-code:** `same-code --base 059774e --allow companion/app.py`
  over all twelve files -> exit 0; the same command with no `--allow` -> exit 1, differing only
  on `companion/app.py`, confirming code stayed unchanged through the tightening edits.
- **Second pass check:** `check --paths` over all twelve files -> 0 history hits.
- **Second pass ruff:** `ruff check` over all twelve files -> "All checks passed!".
- **Second pass pytest:** `pytest companion -q -n auto` -> 1545 passed, 129 skipped (same counts
  as after the first pass), 0 failed.
- **Second pass ratios:** `companion/app.py` 29.1%, `companion/auth.py` 34.4% (both at/under the
  ~35% target); full per-file table above.

## Next Phase Readiness

`companion/app.py`, `auth.py` and the nine small page-independent modules are fully purged,
code-unchanged, and test-green. Group 4 (companion Python production) still has
`companion/pages/*.py`, `companion/layout.py`, `companion/draw.py` and the remaining production
files outstanding for later plans in this wave before the group-closing plan (35-13) ratchets
`companion/` production files out of the pending list and records the group's full ratio table.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `companion/app.py` — FOUND
- `companion/auth.py` — FOUND
- `companion/__init__.py` — FOUND
- `companion/battery.py` — FOUND
- `companion/frame_state.py` — FOUND
- `companion/i18n.py` — FOUND
- `companion/prefs.py` — FOUND
- `companion/screens.py` — FOUND
- `companion/wake.py` — FOUND
- `companion/illustration_normalize.py` — FOUND
- `companion/contrast_check.py` — FOUND
- `companion/theme_preview.py` — FOUND
- Commit `113ad8a` (Task 1: purge companion/app.py) — FOUND
- Commit `c441a0e` (Task 2: purge auth.py and the small modules) — FOUND
- Commit `be2578f` (Second pass: tighten comment/docstring compression to hard caps) — FOUND
