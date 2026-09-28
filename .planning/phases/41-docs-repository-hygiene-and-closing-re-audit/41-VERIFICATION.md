---
phase: 41-docs-repository-hygiene-and-closing-re-audit
verified: 2026-09-28T09:15:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "Every audit finding is verified closed against the code (ROADMAP success criterion 2: every ID in the ledger marked closed with its evidence)"
    reason: "HYG-01 and HYG-06 are genuinely open (comment/docstring history references and a comment-guard regex gap; no runtime behaviour involved). The developer accepted them as-is so Phase 42 can start, and deferred the fix to .planning/todos/pending/comment-history-guard-residue.md. Every other ledger ID is VERIFIED-CLOSED or FLAGGED-DIFFERENT with evidence."
    accepted_by: "Florian Lepont"
    accepted_at: "2026-09-28T12:00:00Z"
gaps_accepted:
  - truth: "Every audit finding is verified closed against the code (ROADMAP success criterion 2: every ID in the ledger marked closed with its evidence)"
    status: partial
    reason: "HYG-01 and HYG-06 are genuinely open, independently confirmed. The comment-history guard's regex (scripts/check_comment_history.py:38-55) does not match a letter-suffixed decision ID (e.g. `D-14c`), a dotted UI-SPEC section number (e.g. `06.6.4.1.1-04`), or a bare `NN-NN` reference without a preceding `plan `/`Plan ` marker or trailing ` Task` (e.g. `39-13`, `39-08` used mid-sentence). Confirmed by direct regex inspection and by spot-checking every cited file:line."
    artifacts:
      - path: "scripts/check_comment_history.py"
        issue: "d-id pattern (line 43, `\\bD-(?:A\\d{1,2}|\\d{2}-\\d{2}|\\d{1,3})\\b`) has no trailing-lowercase-letter case; no uispec-section pattern exists at all; bare-plan-id pattern (lines 51-54) requires an adjacent `plan `/`Plan `/` Task` marker, so a bare mid-sentence `NN-NN` reference is invisible to it"
      - path: "companion/test_companion_app_05.py"
        issue: "lines 1036, 1080 — comment cites decision id `D-14c`"
      - path: "companion/test_config_page_01.py"
        issue: "line 481 — comment cites `D-14c`"
      - path: "companion/test_config_page_02.py"
        issue: "line 1593 — comment cites `D-14c`"
      - path: "companion/test_config_page_03.py"
        issue: "lines 1529, 1561, 1654, 1684, 1710 — docstrings cite `D-15b/c/d`; lines 438, 713, 718 cite UI-SPEC section `06.6.4.1.1-05`"
      - path: "companion/test_status_pages_05b.py"
        issue: "line 673 — cites `D-18b` and UI-SPEC section `06.6.4.1.1-03`"
      - path: "companion/test_companion_app_01.py"
        issue: "lines 374, 477, 479, 534, 595 — cite dotted UI-SPEC section numbers `06.6.4.1.1-04`/`06.6.4.1-08`/`06.6.4.1-05`/`06.6.1-05`"
      - path: "companion/test_companion_app_04.py"
        issue: "line 307 — cites UI-SPEC section `06.6.2-12`"
      - path: "companion/test_status_pages_03.py"
        issue: "line 421 — cites UI-SPEC section `06.6.2-04`"
      - path: "pyproject.toml"
        issue: "line 26 — comment reads \"Refreshed 39-13 with...\" (bare plan-id reference, no `plan `/`Plan ` marker)"
      - path: "server/plane/render/cli.py"
        issue: "line 157 — docstring reads \"before the 39-08 split\" (bare plan-id reference)"
      - path: "server/test_render.py"
        issue: "lines 109, 188 — cite \"the 39-08 split\""
    missing:
      - "Extend scripts/check_comment_history.py's `d-id` pattern (line 43) to also accept a single trailing lowercase letter after the numeric suffix, e.g. change `\\d{1,3}\\b` to `\\d{1,3}[a-z]?\\b` in the relevant alternation branch"
      - "Add a new `uispec-section` pattern matching a dotted UI-SPEC section number, e.g. `\\b0\\d\\.\\d+(?:\\.\\d+){1,3}-\\d{2}\\b`"
      - "Loosen the `bare-plan-id` pattern (lines 51-54) so a bare `\\d{1,3}-\\d{2}[a-z]?` is flagged without requiring a preceding `plan `/`Plan ` or trailing ` Task` marker"
      - "Once the guard is fixed, reword the ~21 cited comment/docstring sites across the 12 files above to drop the bare decision/plan/UI-SPEC id (git and .planning/ already carry the history) — no behavior change needed, comment/docstring text only"
      - "Re-run `python3 scripts/check_comment_history.py check` to confirm zero hits after both the regex fix and the reword, then re-tick DOC-03/HYG-01/HYG-06 in .planning/REQUIREMENTS.md with the closing evidence"
---

# Phase 41: Docs, repository hygiene and closing re-audit Verification Report

**Phase Goal:** The docs describe the code as it is, the repository ships nothing it does not use, and every audit finding is verified closed against the code.
**Verified:** 2026-09-28T09:15:00Z
**Status:** passed (1 developer override)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Every doc claim flagged in DOC-01 corrected and re-checked (ROADMAP SC1) | VERIFIED | Independently re-checked all 5 named drift examples from 41-CONTEXT.md against the current tree: `grep -rn "persists nothing" deploy/ ARCHITECTURE.md` → no hits; `grep -n "mode 640" deploy/provision.sh` → no hits, `mode 660` is now the documented value in `deploy/Caddyfile:34`/`deploy/README.md:463`; `grep -rn "18 harnesses" .github` → no hits; `deploy/skypane.env.example:3` reads "Copy this file to `/opt/skypane/skypane.env` ON THE VPS ONLY" — corrected path. DOC-01 ticked in REQUIREMENTS.md:197. |
| 2 | Every ID in the audit ledger marked closed with its evidence (ROADMAP SC2) | PASSED (override) | Override: HYG-01/HYG-06 accepted open by Florian Lepont on 2026-09-28, fix deferred to `.planning/todos/pending/comment-history-guard-residue.md`. Original finding: | 80/82 IDs are VERIFIED-CLOSED or FLAGGED-DIFFERENT (naming/tooling-only, no open risk — independently confirmed ARC-03's `server/plane/calendar_rules/{ics,match,registry}` exists). **HYG-01 and HYG-06 are FLAGGED-OPEN**, independently confirmed genuinely open (see gaps below) — not merely restated from the SUMMARY. |
| 3 | A fresh audit pass finds no regression of a closed item (ROADMAP SC3) | VERIFIED | The base-tree REQUIREMENTS.md (`7bd8664`) had HYG-01/HYG-06 ticked `[x]`/"Complete" (`git show 7bd8664:.planning/REQUIREMENTS.md` lines 148,153,398,403). This phase's re-audit caught that they were falsely marked closed and correctly reopened them (unticked, "Reopened by the Phase 41 re-audit") rather than silently leaving them ticked — this is the criterion working as intended, not a new regression introduced by this phase. `git diff --name-status 7bd8664 HEAD -- ':!.planning'` touches no production behavior outside VENDOR.md/comment edits, confirmed by `check_comment_history.py same-code` (rc 0). |
| 4 | Repository ships nothing it does not use (DOC-02, goal clause 2) | VERIFIED | `hardware/logs/backoff-powercycle.log.gz` present (86.5 KB, gzipped in tree only, history untouched per `git log` showing the file's prior blob still reachable); `_unresolved/air-caraibes-atr72-unused.png` removed (`git log --all -- '*air-caraibes-atr72-unused*'` shows only the removal commit `38d3e888`, confirmed no other reference exists). DOC-02 ticked in REQUIREMENTS.md:198. |
| 5 | Nothing under firmware/ other than VENDOR.md prose differs from the phase base | VERIFIED | `git diff --name-status 7bd8664 HEAD -- firmware/` → `firmware/VENDOR.md` only. |
| 6 | CFG-72/CFG-73 ticked only after their proving tests pass; CFG-74 and CFG-34/37/39/42/50/52/65 byte-identical to base | VERIFIED | Independently re-ran the three named tests with `SKYPANE_REQUIRE_BROWSER=1`: `companion/test_browser_ux_04.py::test_a_settings_card_title_renders_identically_on_both_settings_pages` and `companion/test_browser_ux_quiet_wake.py::test_the_dial_caption_keeps_its_form_after_every_interaction_kind` — both pass (`2 passed in 4.81s`). `git show 7bd8664:.planning/REQUIREMENTS.md \| grep -n CFG-74` byte-identical to current CFG-74 text/line number. |
| 7 | A PR description summarizes Phases 32-41 for the developer | VERIFIED | `41-PR-DESCRIPTION.md` exists (140 lines), contains a phase-by-phase account with PR numbers, verified-criteria counts, and re-audit verdicts per phase. |

**Score:** 7/7 truths verified (6 VERIFIED, 1 PASSED (override)). The original count read 5/7, but only truth 2 was FAILED.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-CLOSING-AUDIT.md` | closing re-audit report, 82 rows, `\| DOC-03 \|` | VERIFIED | Present, 313 lines, all 82 IDs tabulated with verdict, closing commit(s), evidence; verdict totals table (77/3/2) present; `DOC-03` row present |
| `.planning/REQUIREMENTS.md` | CFG-72/73 ticked, DOC-01..03 and flagged rows updated | VERIFIED | `- [x] **CFG-72**`, `- [x] **CFG-73**` present (lines 98-99); DOC-01/DOC-02 ticked (197-198); DOC-03 unticked (199); HYG-01/HYG-06 unticked (148,153) with traceability notes at 398/403 pointing to 41-CLOSING-AUDIT.md |
| `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-PR-DESCRIPTION.md` | draft PR body for the 32-41 arc | VERIFIED | Present, 140 lines, phase-by-phase summary |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| 41-CLOSING-AUDIT.md | 41-REAUDIT-TST-HYG.md, 41-REAUDIT-FW.md, 41-REAUDIT-INT-SEC.md, 41-REAUDIT-EFF-ARC-CMP.md, 41-DOC-DRIFT-DEPLOY.md, 41-DOC-DRIFT-DOCS.md | detail links per row | WIRED | Each row's "Detail" column cites the source slice file (e.g. `41-REAUDIT-TST-HYG.md HYG-01`); all six files present in the phase directory |
| .planning/REQUIREMENTS.md traceability | 41-CLOSING-AUDIT.md | flagged rows point at the report | WIRED | Lines 369 (TST-02), 382 (TST-15), 398 (HYG-01), 403 (HYG-06), 434 (ARC-03), 449 (DOC-03) all read "see 41-CLOSING-AUDIT.md" |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| DOC-01 | 41-01, 41-02, 41-08 | All docs aligned with the code as it stands after phases 32-40 | SATISFIED | Independently spot-checked 5/5 named drift examples corrected; ticked in REQUIREMENTS.md |
| DOC-02 | 41-03, 41-08 | Log gzipped in tree, unused asset removed, archival deferred to v1.0 close | SATISFIED | Verified file states directly |
| DOC-03 | 41-04, 41-05, 41-06, 41-07, 41-08 | Re-audit: every ID in the ledger verified against the code and marked closed | SATISFIED (override) | 80/82 closed; HYG-01/HYG-06 genuinely open — REQUIREMENTS.md itself correctly leaves DOC-03 unticked, consistent with this verification's finding, but the ROADMAP success criterion ("every ID... marked closed") is not fully met |

No orphaned requirements: all three phase-scoped IDs (DOC-01, DOC-02, DOC-03) are claimed across the eight plans' `requirements:` frontmatter, matching REQUIREMENTS.md's Phase 41 rows.

### Anti-Patterns Found

None found in files this phase modified (41-01/02/03/08 touch only markdown, comments/docstrings, and `.planning/`; `check_comment_history.py same-code --base 7bd8664` independently re-run, rc 0, confirming every non-`.planning` file this phase touched changed only in comments/docstrings, with the one documented `argparse`-docstring exception for `stub-server/byos_server.py`).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Comment-history guard passes clean on current tree | `python3 scripts/check_comment_history.py check` | rc 0 | PASS (expected — this is the guard being blind to the gap, not proof the gap is closed) |
| Comment-history guard's regex genuinely misses the cited ID shapes | direct read of `scripts/check_comment_history.py:38-55` against `D-14c`, `06.6.4.1.1-04`, `39-13`/`39-08` mid-sentence | none of the 4 patterns (`d-id`, `plan-artifact`, `bare-plan-id`, others) match any of the three shapes | CONFIRMED GAP |
| ruff clean | `server/.venv/bin/ruff check .` | `All checks passed!` | PASS |
| mypy clean | `server/.venv/bin/mypy` | `Success: no issues found in 12 source files` | PASS |
| function-size gate | `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server` | `401 functions scanned, none over 80` | PASS |
| CFG-72/CFG-73 proving tests | targeted `pytest` run of the 2 named tests with `SKYPANE_REQUIRE_BROWSER=1` | `2 passed in 4.81s` | PASS |
| firmware fence held | `git diff --name-status 7bd8664 HEAD -- firmware/` | `firmware/VENDOR.md` only | PASS |
| ARC-03 naming claim | `ls server/plane/calendar_rules/` | `ics.py match.py registry.py __init__.py` | PASS (confirms FLAGGED-DIFFERENT carries no open risk) |

Full local test suite not re-run in this verification pass — 41-CLOSING-AUDIT.md's own triage of its 40-48 local-only failures (sandbox resource contention, macOS/BSD-`mv`/no-`/proc` limitations, and one unresolved cross-environment `test_fault_screen_mask` anomaly contradicted by a live, fetched GitHub Actions log) was independently plausible on inspection and is not re-litigated here per the task's own instruction not to count sandbox-environment failures as phase gaps absent evidence of a real regression. No new evidence of a regression was found.

### Human Verification Required

None. All must-haves resolved to VERIFIED or FAILED via direct codebase inspection.

### Gaps Summary

The phase substantially achieved its goal: DOC-01 (doc/code alignment) and DOC-02 (repository hygiene) are both genuinely done, and 80 of 82 audit-ledger findings are genuinely closed or closed-with-a-documented-naming-difference. The closing report (`41-CLOSING-AUDIT.md`) is honest and its own flagged items were independently reproduced, not just trusted.

However, ROADMAP success criterion 2 — "every ID in the audit ledger marked closed with its evidence" — is not met: **HYG-01** (21 residual plan/decision-history references surviving in 12 tracked comment/docstring sites) and **HYG-06** (the root cause: the comment-history guard's regex has no case for a letter-suffixed `D-`ID, a dotted UI-SPEC section number, or a bare mid-sentence `NN-NN` reference) are genuinely open, independently confirmed by regex inspection and by reading every cited file:line. This is not a fabricated or overstated gap — the phase's own plan (41-08) deliberately deferred fixing these to a follow-up plan (`/gsd-plan-phase 41 --gaps`) rather than fixing them inside this closing plan, which is a reasonable scoping choice, but it means the phase's own goal text is not yet fully true of the codebase. The fix is small and well-scoped (three regex edits plus ~21 comment rewords, no behavior change, does not touch `firmware/`), and is the correct next step before this phase can be marked passed.

## Developer override (2026-09-28)

The developer accepted HYG-01 and HYG-06 as-is rather than running the
gap-closure plans (drafted in commit `3e45e90a`, then withdrawn). The
recorded gap under `gaps_accepted:` above stays as the specification for
`.planning/todos/pending/comment-history-guard-residue.md`. DOC-03 is ticked on that basis.
