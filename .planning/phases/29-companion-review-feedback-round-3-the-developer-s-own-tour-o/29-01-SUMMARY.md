---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 01
subsystem: ui
tags: [companion, airlines-page, html-forms, i18n, css, python-stdlib-http]

requires:
  - phase: 21-06
    provides: "the dialog's unconditional resolve-upload zone this plan's forms sit beside"
  - phase: 22-11
    provides: "the page-wide editing toggle, badge and per-card Replace control this plan deletes"
provides:
  - "Compagnies' illustration dialog with its Replace/Delete forms rendering unconditionally, no page-wide editing mode, no per-card Replace button"
  - "companion/pages/airlines_page.py with _edit_toggle_html(), EDIT_QUERY_PARAM and six toggle/badge/replace copy constants deleted"
  - "companion/app.py and companion/pages/__init__.py with the edit_mode ctx key and its documented contract removed"
affects: [29-02, 29-03, 29-04, 29-05, 29-06]

tech-stack:
  added: []
  patterns:
    - "A dialog's own two-form visibility split (replace vs delete) is decided entirely client-side from a trigger's own data attributes, never from a server-side render-time flag — the dialog always carries both forms, panel-lookup.js's existing mode/manual reads choose which is shown per open."

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/app.py
    - companion/pages/__init__.py
    - companion/i18n_fr/airlines.py
    - companion/static/style.css
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "Deleted the now-dead .page-header__screen .section-caption and .page-header__screen .banner__pill CSS rules alongside the three .airlines-edit-toggle rule blocks — both selectors only ever matched markup the deleted _edit_toggle_html() produced, and no other page nests a .section-caption or .banner__pill inside .page-header__screen (config_page.py applies the class directly to a <p>, never as a wrapper)."
  - "The new per-card vocabulary check derives its expected attribute count from the module's own _VIEW_PANEL_*_ATTR constants at runtime, explicitly excluding _VIEW_PANEL_CLOSE_ATTR (the dialog's own Close-button attribute, never part of a card trigger's vocabulary) rather than hardcoding 14 or trusting a stale '15' in prior docstrings."
  - "Dropped the redundant second '?edit=1' HTTP fetch from test_status_pages.py's real-HTTP end-to-end check instead of keeping it pointed at a URL that is now byte-identical to the plain /airlines fetch already captured — a duplicate fetch proving nothing new is a maintenance liability, not a property."

requirements-completed: [CFG-81]

coverage:
  - id: D1
    description: "Opening any known airline's illustration dialog on /airlines shows a Replace-picture form with no query parameter in the URL and no page-wide toggle anywhere on the page"
    requirement: CFG-81
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_default_render_always_has_the_dialogs_forms"
        status: pass
      - kind: integration
        ref: "companion/test_view_pages.py#_airlines_dialog_forms_render_unconditionally_over_real_http"
        status: pass
    human_judgment: true
    rationale: "Visual placement and click behavior of the dialog in a real browser cannot be proven by a Python-only harness (no playwright in this sandbox) — see Human Follow-ups."
  - id: D2
    description: "Opening the dialog for a manually resolved entry additionally shows a Delete form; opening it for a non-manual entry does not"
    requirement: CFG-81
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_default_render_always_has_the_dialogs_forms"
        status: pass
    human_judgment: true
    rationale: "The show/hide split is decided by panel-lookup.js at click time in a real browser; a Python harness can only prove both forms are always present in the document, not that the script toggles them correctly per click."
  - id: D3
    description: "No page-wide picture-editing toggle, badge, or per-card Replace control renders anywhere on /airlines, in either language"
    requirement: CFG-81
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_no_page_wide_editing_mode_survives"
        status: pass
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary"
        status: pass
    human_judgment: false
  - id: D4
    description: "With scripts blocked the served /airlines HTML still contains the dialog's Replace form markup; the resolve-context block stays guarded by its stylesheet hidden rule"
    requirement: CFG-81
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_default_render_always_has_the_dialogs_forms"
        status: pass
      - kind: integration
        ref: "companion/test_status_pages.py (the /both-tabs end-to-end check's /airlines branch)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-09-21
status: complete
---

# Phase 29 Plan 01: Illustration Dialog Owns Its Actions Summary

**Deleted Compagnies' page-wide "Change pictures"/"Done" toggle, its badge, its caption, and the per-card Replace button; the shared lightbox's Replace and Delete forms now render on every page load, shown or hidden per click by panel-lookup.js's existing mode/manual attribute reads — no script change.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-21T19:20:00Z
- **Completed:** 2026-09-21T19:46:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Deleted `_edit_toggle_html()`, the per-card `.calendar-disconnect-btn` Replace control, `EDIT_QUERY_PARAM`, and six English/French copy-constant pairs, plus the three `.airlines-edit-toggle` CSS rule blocks and two now-dead nested rules (`.page-header__screen .section-caption`, `.page-header__screen .banner__pill`)
- Made `_lightbox_html()`'s Replace/Delete forms and `_resolve_section_html()`'s Delete form unconditional; deleted the `ctx["edit_mode"]` key, its `app.py` reader, and its documented contract in `companion/pages/__init__.py`
- Rewrote the harness: inverted one check, retired five, added one, replaced one, retargeted two real-HTTP checks in place — `test_view_pages.py` 166→162 (re-derived), `test_status_pages.py` unchanged at 311 (re-derived)
- `panel-lookup.js` has a zero-line diff — its existing `replaceForm.hidden = (mode !== "art")` / `deleteForm.hidden = (manual === "")` assignments are the entire mechanism

## Task Commits

Each task was committed atomically:

1. **Task 1: delete the page-wide editing toggle, the editing badge, the per-card Replace control and their six copy constants** - `802e76e` (fix)
2. **Task 2: the dialog's Replace and Delete forms render unconditionally, and the query-parameter plumbing is deleted** - `be14f9a` (fix)
3. **Task 3: rewrite the harness checks that tested the removed distinction, and pin the new unconditional behaviour** - `bbc98f9` (test)

## Before/After Harness Counts (re-derived by running)

| Harness | Before | After | Delta |
|---|---|---|---|
| `test_view_pages.py` | 166/166 | 162/162 | -4 |
| `test_status_pages.py` | 311/311 | 311/311 | 0 |
| `test_i18n.py` | 24/24 | 24/24 | 0 |
| `test_config_page.py` | 266/266 | 266/266 | 0 (untouched, confirmed unaffected) |
| `test_browser_ux.py` | SKIP | SKIP | n/a (no playwright in this sandbox) |
| Full suite (`scripts/run-all-tests.sh`) | — | PASS, all harnesses green | — |

## Mutation Proofs

**1. Item 1's inverted check (`_airlines_default_render_always_has_the_dialogs_forms`)** — mutated `_lightbox_html()`'s `replace_html = _lightbox_replace_form_html()` to `replace_html = _lightbox_replace_form_html() if False else ""`, ran `test_view_pages.py`, quoted the real failures verbatim, then reverted with `git checkout-index -f -- companion/pages/airlines_page.py`:

```
FAIL a default airlines_page.render({}) call (no query parameter involved) carries exactly one each of the dialog's replace form, delete form and upload zone — the page-wide editing mode that used to gate replace/delete behind an exact ?edit=1 is deleted (CFG-81, 29-01-PLAN.md) - expected exactly one 'lightbox__replace' in a default render (no page-wide editing mode gates this dialog form any more, CFG-81), got 0
FAIL a render of a Step-B entry (name saved, no artwork yet) contains exactly two upload zones and two manual-delete forms (the no-JS fallback panel's own copy plus the lightbox's, both unconditional per CFG-81), and exactly one replace form (the dialog's own copy — this no-JS fallback panel has none of its own) (D-19, 21-06-PLAN.md Task 1; retargeted by 29-01-PLAN.md) - expected exactly one 'lightbox__replace' (the dialog's own copy — this no-JS fallback panel has none of its own) in a Step-B render, got 0
FAIL a real authenticated GET of /airlines renders the dialog's replace, delete and upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark renders identically — against a real running service, proving the removed query parameter has no reader anywhere in the real request path (CFG-81, 29-01-PLAN.md) - expected /airlines to render a 'lightbox__replace' form (CFG-81: unconditional now)
```

`git status --porcelain companion/pages/airlines_page.py` was clean after the revert; `test_view_pages.py` returned to 162/162.

**2. Item 3's new absence check (`_airlines_no_page_wide_editing_mode_survives`)** — re-added a bare `<a class="airlines-edit-toggle" href="/airlines?edit=1">x</a>` into `render()`'s return expression, ran `test_view_pages.py`, quoted the real failure verbatim, then reverted:

```
FAIL the deleted page-wide editing toggle (its class literal) and the deleted ?edit= query parameter (its literal form) never render again, in either language, whether the query string is absent or carries an arbitrary unrelated value (CFG-81, 29-01-PLAN.md) - expected no airlines-edit-toggle anchor to ever render again (lang='en')
```

`git status --porcelain companion/pages/airlines_page.py` was clean after the revert; `test_view_pages.py` returned to 162/162.

## Surviving Negative-Grep Occurrences

`grep -cE 'edit_mode|EDIT_QUERY_PARAM' companion/pages/airlines_page.py companion/app.py companion/pages/__init__.py` — **0 for all three files** (Task 2's own hard gate, confirmed clean).

`grep -cE 'edit_mode|\?edit=1' companion/test_view_pages.py` — **15 surviving occurrences**, all inside:
- Five pre-existing, untouched `EXPECTED_CHECK_COUNT` historical-delta comments predating this plan (lines 92, 305, 308, 368, 422) — this codebase's own append-only convention keeps every past delta's own record verbatim; scrubbing them would rewrite history unrelated to this plan's own diff.
- This plan's own new `EXPECTED_CHECK_COUNT` retirement comment (2 occurrences) and the new/retargeted checks' own docstrings/messages (8 occurrences) — retirement comments and the new absence check's own assertion literal, exactly the exception the plan's acceptance criteria states.

`grep -cE 'edit_mode|\?edit=1' companion/test_status_pages.py` — **11 surviving occurrences**, all inside this plan's own new `EXPECTED_CHECK_COUNT` comment (3) and the "no edit_mode needed"/"?edit=1 fetch...deleted" retirement comments left at each swept call site (8) — none is a live reference to the removed ctx key or query literal in executable code.

## Files Created/Modified
- `companion/pages/airlines_page.py` - deleted the toggle builder, per-card control, six copy constants, `EDIT_QUERY_PARAM`, and the `edit_mode` parameter/local everywhere it appeared; both dialog forms and the no-JS delete form are unconditional
- `companion/app.py` - deleted the `"edit_mode"` context-dict key and its doc comment
- `companion/pages/__init__.py` - deleted the `edit_mode` ctx-contract bullet; rewrote the "presentation only" sentence that used to cite it as an example
- `companion/i18n_fr/airlines.py` - deleted the six French twins of the deleted English constants and the docstring paragraph crediting them
- `companion/static/style.css` - deleted the three `.airlines-edit-toggle` rule blocks plus the two now-dead nested rules that only ever styled the deleted toggle's markup
- `companion/test_view_pages.py` - inverted/retired/added/replaced the five checks named in the plan plus three more genuinely broken by the same change (a Step-B upload-zone check, a "one change-pictures toggle" check, two French-render needle lists), retargeted three render() call sites and one real-HTTP browser check
- `companion/test_status_pages.py` - narrowed the replace-action vocabulary check from 2 to 1 trigger per airline, dropped the now-duplicate `?edit=1` fetch, swept eleven `edit_mode=True` render() call sites

## Decisions Made
- Removed the two now-dead `.page-header__screen`-scoped CSS rules alongside the three explicitly named `.airlines-edit-toggle` blocks (see key-decisions above) — a direct, mechanical consequence of deleting the only markup that ever nested a `.section-caption`/`.banner__pill` inside that wrapper, not a separate scope expansion.
- Derived the per-card vocabulary check's expected attribute count from `_VIEW_PANEL_*_ATTR` module constants at runtime (excluding the Close-button-only one) rather than trusting a stale "fifteen" figure already present in an untouched pre-existing docstring elsewhere in the module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed three genuinely-broken (not just five named) test_view_pages.py checks left failing by Tasks 1-2**
- **Found during:** Task 3
- **Issue:** Beyond the plan's five explicitly named checks, three more existing checks broke as a direct, mechanical consequence of Tasks 1-2's deletions: `_airlines_default_render_step_b_upload_zone_unconditional` (asserted zero delete/replace forms, now wrong since both are unconditional), `_airlines_default_render_has_one_change_pictures_toggle` (asserted the deleted toggle exists), and two French-render checks whose needle lists referenced the deleted "Modifier les images" string and `CHANGE_PICTURES_TEXT` constant.
- **Fix:** Retargeted the Step-B check's counts to the new reality (2 delete forms, 1 replace form, 2 upload zones); retired the toggle-existence check (folded into the new absence check); removed the stale needles from both French-render checks.
- **Files modified:** companion/test_view_pages.py
- **Verification:** `test_view_pages.py` 162/162
- **Committed in:** bbc98f9 (Task 3 commit)

**2. [Rule 1 - Bug] Fixed eleven `edit_mode=True` render() call sites and one duplicate-fetch check in test_status_pages.py**
- **Found during:** Task 3
- **Issue:** The plan's read_first named "22 and 3 occurrences" of `edit_mode`/`edit=1` in this file at planning time; running the harness after Tasks 1-2 surfaced one hard failure (the replace-action vocabulary check still expecting 2 triggers per airline) plus eleven now-meaningless `edit_mode=True` kwargs that happened not to fail outright (since the kwarg is silently ignored) but left the harness testing a distinction that no longer exists, plus one check making a real HTTP fetch to a `?edit=1` URL that is now byte-identical to the plain URL already fetched in the same check.
- **Fix:** Narrowed the vocabulary check to 1 trigger/airline; swept every `edit_mode=True` call site to a plain render(); dropped the now-duplicate second fetch, retargeting its assertions onto the single remaining `body_text`.
- **Files modified:** companion/test_status_pages.py
- **Verification:** `test_status_pages.py` 311/311
- **Committed in:** bbc98f9 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — genuine test breakage directly caused by this plan's own production-code changes, within the two files this plan already owns)
**Impact on plan:** Both auto-fixes were necessary for the harness to pass at all; neither touched a file outside `files_modified`. No scope creep.

## Issues Encountered
None beyond the two deviations documented above.

## Known Stubs
None.

## Threat Flags
None — this plan only removes presentation-only surface (a query parameter and a client-only toggle); no new network endpoint, auth path, file-access pattern, or schema change was introduced. The threat register's own three entries (T-29-01-01/02/03) are all "the removed thing was already presentation-only" arguments, not new surface.

## Human Follow-ups
Carried from the plan (not blocking — no playwright in this sandbox):
1. On Compagnies, click any ordinary airline illustration with no query string in the URL. Expect: the picture, its caption, a "Remplacer l'image" form, and NO Prefix/First seen/Last seen/Times seen/Example callsign block.
2. Click a manually resolved airline's illustration. Expect the Delete form additionally present. Click a non-manual one: Delete absent.
3. Confirm no "Modifier les images" link appears anywhere on the page, and that visiting `/airlines?edit=1` renders exactly the same page as `/airlines`.

## Next Phase Readiness
Plan 29-01 is complete and unblocks 29-02 (which reorders `render()`'s remaining return-expression terms — this plan deliberately left that order untouched, as instructed). No blockers.

## Self-Check: PASSED

All 7 files in `files_modified` confirmed present on disk; all 3 task commit hashes (`802e76e`, `be14f9a`, `bbc98f9`) confirmed present in `git log`.

---
*Phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o*
*Plan: 01*
*Completed: 2026-09-21*
