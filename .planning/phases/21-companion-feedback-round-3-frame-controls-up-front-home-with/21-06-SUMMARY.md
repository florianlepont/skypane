---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 06
subsystem: ui
tags: [airlines, resolve-flow, upload, edit-mode]

# Dependency graph
requires: ["21-01", "21-04"]
provides:
  - "companion/pages/airlines_page.py — _resolve_section_html()'s Step-B upload zone renders unconditionally (no edit_mode gate); the shared delete form stays edit_mode-gated (D-20)"
  - "companion/pages/airlines_page.py — _lightbox_html()'s identical no-artwork-yet upload affordance renders unconditionally too; its replace/delete forms stay edit_mode-gated (D-20)"
affects: ["21-08"]

tech-stack:
  added: []
  patterns:
    - "one-line gate removal (D-19/D-20) — no new component, no markup/CSS/copy change, matching 21-UI-SPEC.md §H's own framing"
    - "exact `class=\"{token}\"` matching over bare substring `in rendered` for lightbox class assertions — LIGHTBOX_REPLACE_FORM_CLASS is a prefix of several sibling classes (lightbox__replace-zone/-icon/-hint) that render as part of the upload zone's own markup"
    - "EXPECTED_CHECK_COUNT re-derivation by running the harness and appending a new last assignment, never by arithmetic on the old comment"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/test_view_pages.py

key-decisions:
  - "D-19: dropped both `if edit_mode` guards on the upload zone (the no-JS resolve panel's Step-B branch and the lightbox's identical branch) — one line each, no other code in either function changed"
  - "D-20: left the three replace/delete gates (_resolve_section_html()'s delete_form, _lightbox_html()'s replace_html and delete_html) untouched — 'Change pictures' still gates only replace/delete of existing artwork"
  - "Did not touch _edit_toggle_html() — confirmed it carries zero simple_mode references (plan 21-01 already deleted its early-return, serving both D-17 and D-20 — Pitfall 6)"

patterns-established: []

requirements-completed: ["CFG-24"]

# Metrics
duration: 25min
completed: 2026-09-12
---

# Phase 21 Plan 06: Artwork upload restored in the resolve flow Summary

**Two one-line `if edit_mode` gate removals on `airlines_page.py`'s Step-B upload zone (no-JS resolve panel and lightbox), with the delete/replace gates left untouched.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-12T10:20:00Z (approx, after worktree fast-forward)
- **Completed:** 2026-09-12T10:28:00Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `_resolve_section_html()`'s Step-B branch (`companion/pages/airlines_page.py:1739`) now builds `upload_zone` unconditionally — naming an unrecognised airline and giving it a picture is one job again, reachable without visiting `?edit=1`.
- `_lightbox_html()`'s identical branch (`:1233`) drops the same guard, so the everyday view-only lightbox's own no-artwork-yet drop zone/file picker is no longer hidden behind "Change pictures".
- Both entry-bearing delete-form call sites and the lightbox's replace form stay gated on `edit_mode` (D-20) — verified by grep-based acceptance criteria after each task.
- Confirmed `_edit_toggle_html()` carries zero `simple_mode` references and was not touched by this plan (Pitfall 6 respected).
- Retargeted three `companion/test_view_pages.py` checks and added one new one, re-deriving `EXPECTED_CHECK_COUNT` twice (113 → 114 at Task 1, net 0 at Task 2) by running the harness both times.

## Task Commits

Each task was committed atomically:

1. **Task 1: Drop the step-B upload guard in the resolve panel** - `9c32d7d` (feat)
2. **Task 2: Drop the same guard in the lightbox, keep replace and delete gated** - `d262f14` (feat)

**Plan metadata:** this summary's own commit (docs: complete plan)

## Files Created/Modified
- `companion/pages/airlines_page.py` — dropped the two `if edit_mode` guards on `upload_zone`/`resolve_upload_html`; updated both functions' docstrings and added inline comments citing D-19/D-20 and 21-06-PLAN.md so the reason survives the next audit
- `companion/test_view_pages.py` — imported `server.plane.manual_resolutions` for a real Step-B fixture; retargeted `_airlines_default_render_has_no_edit_only_forms` (drops `RESOLVE_UPLOAD_ZONE_CLASS` from its asserted-absent tuple, then asserts it present exactly once, switching to exact `class="..."` matching for the remaining two tokens); added `_airlines_default_render_step_b_upload_zone_unconditional` (new check, expects two upload zones — one per surface — once both tasks land); retargeted the real-HTTP `_airlines_edit_query_param_exact_one_membership_test` to drop the upload zone from its edit-only tuple and instead assert it present across every query variant; two `EXPECTED_CHECK_COUNT` trail entries appended (113 → 114, then 114 → 114 net 0)

## Decisions Made
- D-19/D-20 as specified in `21-CONTEXT.md` and `21-UI-SPEC.md` §H — no deviation.
- Where the plan's own acceptance criteria anticipated a possible double-count in `_airlines_edit_mode_render_has_exactly_one_of_each_edit_only_form` (which turned out unaffected, since it never sets `resolve_prefix`), the actual double-count surfaced instead in this plan's own new Task-1 check (`_airlines_default_render_step_b_upload_zone_unconditional`), once Task 2 also dropped the lightbox's guard: a Step-B render now legitimately carries two upload zones (fallback panel + lightbox). Fixed the count (1 → 2), not the intent, per the plan's own instruction, and documented the reason in the check's own comment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a substring false-positive in the retargeted absence check**
- **Found during:** Task 2
- **Issue:** `_airlines_default_render_has_no_edit_only_forms` asserted absence of `LIGHTBOX_REPLACE_FORM_CLASS`/`LIGHTBOX_DELETE_CLASS` via a bare `token in rendered` substring test. Once the upload zone became unconditional, its own markup unconditionally emits `lightbox__replace-hint`/`lightbox__replace-icon` (sibling classes that share the `lightbox__replace` prefix), which the substring test falsely matched as the gated replace form.
- **Fix:** Switched both assertions to exact `'class="%s"' % token in rendered` matching, mirroring the discipline the file's own pre-existing `_airlines_edit_mode_render_has_exactly_one_of_each_edit_only_form` check already documents for the identical prefix hazard. Applied the same fix to the new Task-1 check for consistency.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `companion/test_view_pages.py` 114/114 after the fix.
- **Committed in:** `d262f14` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed the real-HTTP edit-query check broken by the now-unconditional upload zone**
- **Found during:** Task 2
- **Issue:** `_airlines_edit_query_param_exact_one_membership_test` treated `RESOLVE_UPLOAD_ZONE_CLASS` as one of three edit-only tokens and asserted its absence under `?edit=2`/`?edit=true`/`?edit=`. This is directly falsified by Task 2's own change (the upload zone is no longer edit-only), and the plan's own acceptance criteria implicitly required this fix (`git diff --stat shows exactly two files changed by this plan`, `test_view_pages.py`... reports M/M) even though the plan's task text didn't name this check by its current line number (it had drifted from the plan's approximate `~2394-2398`/`~2725-2727` references after intervening plans 21-01/21-03/21-04 grew the file).
- **Fix:** Removed `RESOLVE_UPLOAD_ZONE_CLASS` from the `edit_only_tokens` tuple; added a positive assertion that it is present (exact `class="..."` match) across every query variant, including `?edit=1`, proving it survives the real HTTP round trip regardless of edit mode.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `companion/test_view_pages.py` 114/114 after the fix; this specific check passes for all four query variants.
- **Committed in:** `d262f14` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs directly caused by this plan's own guard removal, within scope of the two owned files)
**Impact on plan:** Both fixes were necessary for the retargeted harness to accurately reflect D-19; no scope creep, no files touched beyond `companion/pages/airlines_page.py` and `companion/test_view_pages.py`.

## Issues Encountered
None beyond the two deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- D-19/D-20 fully delivered; the phase's decision list (D-01..D-20) is now complete pending plan 21-08's cross-cutting sweep.
- `<human-check>` items folded into 21-08 remain: visually confirm on Airlines that naming an unrecognised airline shows the picture drop zone in step B without `?edit=1`, and that "Change pictures" still reveals replace/delete on an airline that already has artwork.

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*

## Self-Check: PASSED
- FOUND: companion/pages/airlines_page.py
- FOUND: companion/test_view_pages.py
- FOUND: .planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-06-SUMMARY.md
- FOUND commit: 9c32d7d
- FOUND commit: d262f14
