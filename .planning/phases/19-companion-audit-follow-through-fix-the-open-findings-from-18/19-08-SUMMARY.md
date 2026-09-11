---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 08
subsystem: ui
tags: [airlines-page, gap-strip, resolve-flow, edit-gating, query-param, stdlib-only]

# Dependency graph
requires:
  - phase: 19
    plan: 03
    provides: "companion/test_view_pages.py's own current shape and check count (76 before this plan)"
  - phase: 19
    plan: 07
    provides: "the CSP's script-src 'self' with no inline scripts, and confirmation of app.py's page_context() shape this plan's edit_mode key builds alongside"
provides:
  - "airlines_page.GAP_STRIP_HEADING/GAP_STRIP_BODY and _gap_strip_html(): the coverage-gap cards' own explained '<section class=\"page-section\">' strip, rendered above the filter bar; the curated artwork grid holds only curated cards"
  - "airlines_page.RESOLVE_BACK_LINK_TEXT now reads '← Back to Airlines' and its href is airlines_page.AIRLINES_ROUTE, not a retyped '/health' literal"
  - "airlines_page.EDIT_QUERY_PARAM and app.py's ctx['edit_mode'] (an exact `== \"1\"` membership test), documented as presentation-only in companion/pages/__init__.py"
  - "_lightbox_html(edit_mode=False) and _resolve_section_html(ctx, edit_mode=False): the replace/upload/delete forms render only under edit_mode; the resolve-name form and resolve-context stay unconditional"
affects: [any future plan touching companion/pages/airlines_page.py's render()/_lightbox_html()/_resolve_section_html(), companion/app.py's page_context(), or companion/test_status_pages.py's airlines-lightbox checks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level-string-constant copy convention (GAP_STRIP_HEADING/GAP_STRIP_BODY), matching health_page.py's SOURCE_FAULT_HEADING/SOURCE_FAULT_BODY - escaped exactly once at the single interpolation point, already-safe markup interpolated verbatim"
    - "Presentation-only query flag: ctx['edit_mode'] decides what renders, never what a POST handler permits - the same exact-membership-test discipline layout.ui_theme_from_cookie()/submitted_scope() already apply to an untrusted query/cookie value before trusting it"
    - "Fully-defaulted trailing keyword for a widened function signature (edit_mode=False on both _lightbox_html() and _resolve_section_html()), matching config_page.py's own established convention for adding behavior without breaking existing callers"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/app.py
    - companion/pages/__init__.py
    - companion/test_view_pages.py

key-decisions:
  - "_gap_strip_html()'s cards container uses class=\"illustration-grid illustration-grid--gap\" (a bare modifier, no new CSS rule) rather than the bare .illustration-grid class, so a full-page-order check can find the curated grid's own exact class=\"illustration-grid\" attribute without also matching the strip - this needed no companion/static/style.css edit (that file is owned by plan 19-10 in this same wave)"
  - "_gap_overflow_html()'s anchor stays pointed at /health, not retargeted to Airlines - the link exists to show the prefixes GAP_BLOCK_CAP hides, and only Health's registry table lists all of them; recorded in a comment per the plan's own instruction"
  - "RESOLVE_STALE_BODY's trailing sentence reworded from \"Check Health for current gaps\" to \"See Health for the complete list of current gaps\" - explicit now that the stale branch is reached from Airlines, not Health"
  - "The resolve-name form and the resolve-context <dl> stay unconditional in both _lightbox_html() and _resolve_section_html() - naming a prefix is the everyday action the gap strip's own sentence invites (\"Tap one to name it\"), so only the artwork-editing tier (replace/upload/delete) is edit-gated"
  - "Applied the identical edit_mode gate to _resolve_section_html()'s own Step B upload zone and both entry-bearing branches' shared delete form, so the no-JS fallback panel matches the dialog rather than diverging from it, per the plan's explicit instruction"

requirements-completed: [CFG-04]

# Metrics
duration: ~15min
completed: 2026-09-11
---

# Phase 19 Plan 08: Airlines Gap Strip, Resolve Back Link, and Edit-Gated Lightbox (D-21/D-22) Summary

**The coverage-gap cards now live in their own explained "Unidentified airlines" strip above the filter bar, the resolve panel's back link returns to Airlines instead of Health, and the lightbox's replace/upload/delete forms render only under an exact `?edit=1` — closing A-38 and A-39.**

## Performance

- **Duration:** ~15 min (first task commit to last)
- **Started:** ~2026-09-11T08:20:00Z (approximate — investigation/reads preceded the first commit)
- **Completed:** 2026-09-11T08:38:03Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments
- `_gap_strip_html()` wraps the gap cards, `GAP_STRIP_HEADING` ("Unidentified airlines") and `GAP_STRIP_BODY` (the exact D-21 sentence) in a real `<section class="page-section">` card, rendered first on the page — a no-gaps render emits nothing extra; `render()` calls `_gallery_grid_html()` without `gap_cards_html`, so the curated artwork grid holds only curated cards
- `RESOLVE_BACK_LINK_TEXT` is now "← Back to Airlines"; `back_link`'s href reads `AIRLINES_ROUTE`, never a retyped `"/health"` literal — a deliberate, commented supersession of the Phase 13 Copy Deck
- `airlines_page.EDIT_QUERY_PARAM` ("edit") and `companion/app.py`'s `ctx["edit_mode"]` (`params.get(EDIT_QUERY_PARAM, [None])[0] == "1"`, an exact membership test) gate the shared lightbox's replace/upload/delete forms and the no-JS fallback panel's own upload/delete forms; the resolve-name form stays unconditional in both. `companion/static/panel-lookup.js` needed no change — its three lookups for these elements already sit outside its mandatory guard and are each used behind their own `if (form)` test

## Task Commits

Each task was committed atomically:

1. **Task 1: Move the gap cards into an explained "Unidentified airlines" strip (D-21)** - `bbf977e` (feat)
2. **Task 2: Send the resolve panel's back link to Airlines (D-21)** - `1698e37` (fix)
3. **Task 3: Gate the lightbox's replace, upload and delete forms behind ?edit=1 (D-22)** - `d8853a2` (feat)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified
- `companion/pages/airlines_page.py` — `GAP_STRIP_HEADING`/`GAP_STRIP_BODY`/`_gap_strip_html()`; `render()`'s tail reordered (strip before the filter bar, `_gallery_grid_html()` called without `gap_cards_html`); `_gallery_grid_html()`'s docstring updated to record the D-21 caller change; `RESOLVE_BACK_LINK_TEXT`/`RESOLVE_STALE_BODY` reworded, `back_link` now built from `AIRLINES_ROUTE`; `EDIT_QUERY_PARAM` added beside `RESOLVE_QUERY_PARAM`; `_lightbox_html(edit_mode=False)` and `_resolve_section_html(ctx, edit_mode=False)` gate the replace/upload/delete forms; `render()` reads `ctx.get("edit_mode")` and threads it through both
- `companion/app.py` — `page_context()` adds `"edit_mode": params.get(airlines_page.EDIT_QUERY_PARAM, [None])[0] == "1"`
- `companion/pages/__init__.py` — documents the new `edit_mode` ctx key as a presentation-only flag, explicitly never a substitute for `require_session()`
- `companion/test_view_pages.py` — new `_seed_unresolved_prefixes()` helper and a `server.poll_loop` import; 8 new checks across the three tasks (gap-strip present/absent, back-link name+href, default-render edit-forms-absent, default-render resolve-name-present, edit-mode-render edit-forms-present, and a real-HTTP exact-"1" round trip); 2 existing checks retargeted in place to render with `edit_mode=True` (the DOM-contract guard and the replace-token three-file guard, both previously asserting the replace form on every render). `EXPECTED_CHECK_COUNT` re-derived three times: 76 → 78 → 79 → 83

## Decisions Made
See `key-decisions` in the frontmatter above for the five load-bearing decisions (the `illustration-grid--gap` modifier class, the overflow link staying on Health, the reworded stale sentence, the resolve-name/resolve-context unconditional carve-out, and the fallback-panel gating parity).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retargeted two pre-existing test_view_pages.py checks that assumed the replace form rendered on every Airlines render**
- **Found during:** Task 3 (Gate the lightbox's replace, upload and delete forms behind ?edit=1)
- **Issue:** `_lightbox_dom_contract_three_file_guard()` and `_replace_lightbox_names_appear_in_three_files_never_in_history()` both called `airlines_page.render({})` and asserted `LIGHTBOX_REPLACE_FORM_CLASS` present — true before this plan, false after, since the replace form is now edit-gated.
- **Fix:** Both now call `airlines_page.render({"edit_mode": True})` instead, with a comment recording the D-22 retarget; a plain `{}` render is exercised separately by this task's own new absence checks.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `companion/test_view_pages.py` 83/83.
- **Committed in:** `d8853a2` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (test retarget required by the plan's own described behavior change, within my owned test file)
**Impact on plan:** Necessary for correctness — this is exactly the "retarget in place" work Task 3's own action text calls for. No scope creep.

## Issues Encountered

**Critical cross-plan test conflict — requires reconciliation before this wave is merged.**

`companion/test_status_pages.py` (owned by plan 19-09 in this same wave; I did not and must not edit it) pins roughly a dozen checks that assert the shared lightbox's replace form, the resolve-section's upload form, and the D-09 delete form all render **unconditionally** on every Airlines render and every real `/airlines` HTTP response. Task 3's own D-22 requirement — gating those three forms behind an exact `?edit=1` — makes every one of those assertions false by design. This is not a bug in this plan's implementation: `companion/test_view_pages.py` (the file this plan owns) is 83/83 green, every acceptance criterion in 19-08-PLAN.md's own text passes verbatim, and `companion/test_companion_app.py` reports exactly the two documented pre-existing root-sandbox WR-11 failures with no new ones.

Running `PYTHON=$(command -v python3) bash scripts/run-all-tests.sh` on top of this plan's three commits reports:
```
==> FAILED harnesses (3):
    - server/test_manual_resolutions.py (exit 1)        <- pre-existing (root-sandbox)
    - companion/test_companion_app.py (exit 1)           <- pre-existing (2 WR-11 root-sandbox FAILs, unchanged)
    - companion/test_status_pages.py (exit 1)            <- 12 FAILs: 1 pre-existing (anomaly_active
                                                             root-sandbox) + 11 NEW, all caused by D-22's
                                                             edit-gating
```

The 11 new `test_status_pages.py` failures (by their own check descriptions, verbatim) all assert one of: "exactly one lightbox replace form is rendered" on a plain render, a file input/action="" always present, the upload form's action always present at Step B, the shared delete form always present once an entry exists, or a real HTTP `GET /airlines` body always containing `LIGHTBOX_REPLACE_FORM_CLASS`. Every one needs the identical fix already applied in `companion/test_view_pages.py` for this plan's own two retargeted checks: render (or request) with `edit_mode=True` (or `?edit=1` for the real-HTTP one) instead of a plain render/request, since that is now the correct way to reach that markup.

**This is out of my file scope** (`companion/test_status_pages.py`, `companion/test_companion_app.py` and `companion/pages/health_page.py` belong to plan 19-09 per this wave's explicit file split) and I did not touch it, per the explicit instruction not to. Flagging this here so the orchestrator (or 19-09's own executor, if it runs after this plan merges) retargets those checks before the wave is considered green — the fix is mechanical and small (render/request with `edit_mode=True`/`?edit=1` at roughly a dozen call sites), not a design problem.

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

- FOUND: companion/pages/airlines_page.py
- FOUND: companion/app.py
- FOUND: companion/pages/__init__.py
- FOUND: companion/test_view_pages.py
- FOUND commit bbf977e
- FOUND commit 1698e37
- FOUND commit d8853a2

## Next Phase Readiness
- D-21/A-38 is closed: the gap cards sit in their own explained strip at the top of Airlines; the resolve panel's back link returns to Airlines
- D-22/A-39 is closed: the everyday Airlines lightbox is view-only (plus the naming form); replace/upload/delete render only for an exact `?edit=1`
- `companion/test_view_pages.py` (83/83); `companion/test_companion_app.py` (209/211 — the two documented pre-existing root-sandbox WR-11 failures, unrelated to this plan, unchanged)
- **Blocker for wave completion, not for this plan's own scope:** `companion/test_status_pages.py` needs ~12 checks retargeted (11 new + reconfirm the 1 pre-existing `anomaly_active()` failure is still the only pre-existing one) to render/request with `edit_mode=True`/`?edit=1` where they currently assume the artwork-editing forms are unconditional. See "Issues Encountered" above for the exact list and fix shape. This plan did not touch `companion/test_status_pages.py`, `companion/test_companion_app.py` or `companion/pages/health_page.py` — those belong to plan 19-09 in this wave.
- No `companion/static/panel-lookup.js` or `companion/static/style.css` changes were made or needed — confirmed via `git diff --stat` against both files (empty)

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 08*
*Completed: 2026-09-11*
