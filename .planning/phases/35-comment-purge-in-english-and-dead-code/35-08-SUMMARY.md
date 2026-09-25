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
  - "Every one of the twelve files sits above the ~35% ratio guideline after purge (see table
    below); none needed a second compression pass beyond what is recorded here, because a
    second read of each found only restatement/history left to cut, not genuine why-comments —
    those were already compressed to one-line form in the same pass."

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

## Comment ratios (before -> after)

Source: `35-BASELINE/ratio-before.tsv` (before) and `check_comment_history.py ratio` on this
plan's own HEAD (after), once `same-code`/`check` both pass. The group-4 closing plan folds
this table into `35-COMMENT-RATIO.md` alongside the rest of the companion-production group.

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| companion/__init__.py | 1 | 1 | 100.0% | 100.0% | 2 -> 0 |
| companion/app.py | 3744 | 3027 | 57.2% | 47.1% | 457 -> 0 |
| companion/auth.py | 540 | 522 | 51.7% | 50.0% | 43 -> 0 |
| companion/battery.py | 457 | 433 | 63.0% | 61.0% | 31 -> 0 |
| companion/contrast_check.py | 226 | 211 | 62.0% | 59.2% | 8 -> 0 |
| companion/frame_state.py | 216 | 197 | 69.9% | 67.0% | 17 -> 0 |
| companion/i18n.py | 42 | 41 | 66.7% | 65.9% | 4 -> 0 |
| companion/illustration_normalize.py | 153 | 142 | 68.6% | 66.2% | 4 -> 0 |
| companion/prefs.py | 59 | 45 | 76.3% | 68.9% | 5 -> 0 |
| companion/screens.py | 139 | 114 | 68.4% | 61.4% | 26 -> 0 |
| companion/theme_preview.py | 376 | 364 | 62.5% | 61.3% | 25 -> 0 |
| companion/wake.py | 38 | 19 | 78.9% | 57.9% | 7 -> 0 |
| **Group total** | **5991** | **5116** | **58.9%** | **49.3%** | **629 -> 0** |

### Files still above the ~35% guideline

Every file in this plan sits above the guideline. Two forces both push these twelve files
higher than the group-2/group-3 precedents: (1) `app.py` and `auth.py` are the single largest
concentration of documented security invariants in the whole codebase (auth, session, CSRF,
throttling — the plan's own must_haves require every one of these to keep a one-line why), and
(2) the other ten files are small (19-540 lines), and a short file with even one genuine
multi-line invariant sits well above 35% by construction, matching this phase's own precedent
for small files (`server/plane/runway_config.py` at 59.0% in group 2, `stub-server/
make_test_panel.py` at 36.4% in group 3).

| File | After | Justification |
|---|---:|---|
| companion/app.py | 47.1% | The companion service's entire route table and every POST handler's security reasoning — the whole-site auth gate exemption list, the CSP directive-by-directive rationale, the CSRF SameSite=Strict posture (stated once in full, pointed to by the other two occurrences after a restatement pass), and the two most complex handlers' ordered security-property lists (`_handle_illustration_replace()`'s six-step untrusted-upload defence, `_handle_settings_post()`'s process-local-vs-cross-process lock correction). Re-read twice hunting for restatement (the fifteen near-identical `_serve_*_script()` docstrings collapsed to one shared comment plus bare bodies, and a three-times-repeated CSRF paragraph collapsed to one full copy plus two pointers) before accepting the remainder as load-bearing. |
| companion/auth.py | 50.0% | A small (522-line), pure security module by design: password hashing, constant-time comparison, HMAC-derived session-token signing, cookie-flag reasoning, login-throttle bucket eviction, and the CSRF Origin/Sec-Fetch-Site gate's four-rule order each earn their own why-comment, per this plan's own must_haves. |
| companion/battery.py | 61.0% | A data/math-dense estimation module: the 14-knot millivolt-to-percent curve's derivation, the companion-display-vs-device-warning threshold distinction (two different numbers for two different jobs), and the no-per-wake-cost discharge-projection reasoning are all genuine units-and-measurement why, not restatement. |
| companion/contrast_check.py | 59.2% | A pure-stdlib WCAG 2.1 implementation: the spec pointers (kept per this plan's own instruction), the three named threshold constants' calibration numbers, and the signal-separation-vs-contrast distinction are the file's entire content — there is very little code to dilute the comments against. |
| companion/frame_state.py | 67.0% | A small (197-line) single-source-of-truth state machine: the three-state condition table and the three-branch delay-sentence contract exist specifically so every consumer (the Frame strip, Home, Health, every settings caption) reads the same computed state, and that "exactly one place decides this" invariant is the module's whole reason to exist. |
| companion/i18n.py | 65.9% | A tiny (41-line) module: one real function (`t()`) and its test-only sibling, each documenting a genuine never-raise/degrade-to-English contract; a short file with two documented functions sits well above 35% by construction. |
| companion/illustration_normalize.py | 66.2% | A geometry-math module: the crop-box derivation (why 450x132, why it is derived from a measured median ratio rather than typed), and the single-source-of-truth import constraint on `server.plane.render._opaque_bbox()` are genuine why, not restatement. |
| companion/prefs.py | 68.9% | A tiny (45-line) module whose entire job is documenting one invariant: one set path, two read paths, no other mutation path — the same discipline auth.py's own module-level mutable state is held to. |
| companion/screens.py | 61.4% | A small (114-line) registry module: the everyday-vs-advanced group split and the render-order comments document real page-composition decisions a future screen type must follow. |
| companion/theme_preview.py | 61.3% | A cache/geometry module: the cache-key invalidation scheme (theme retune, crop-box change, cache-version escape hatch, live-event-id axis) and the crop-box pixel-geometry derivation (which rows are ink, why 390..840 clears every one of them) are both genuinely non-obvious and load-bearing. |
| companion/wake.py | 57.9% | A 19-line re-export shim whose only job is explaining why it exists (a single import path to `server.wake`, so two readers of `companion.wake.*` can never come to believe there are two definitions of "late"); the docstring is the whole file's content. |
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
- Accepted all twelve files above the ~35% guideline after a first compression pass each,
  documented per-file above, rather than continuing to cut: a second read of every file found
  only restatement and repeated-paragraph content left to compress (already fixed above), never
  a genuine why-comment that could be cut without violating this plan's own must_haves (keep
  every auth/session/CSRF/throttle invariant, WCAG pointer, and unit).

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
