---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 03
subsystem: companion-settings-save-floor
tags: [no-js-floor, css-gate, ast-source-proof, mutation-testing, superseded-contract]
requires:
  - "companion/pages/config_page.py::STATIC_SAVE_FALLBACK_ATTR, render() (06.6.4.1-01, 22-01-PLAN.md Task 2/B1)"
  - "companion/test_browser_ux.py::_persist_without_js, _no_js_page, VIEWPORT_MIN_SUPPORTED (25-02/25-03)"
provides:
  - "companion/static/style.css::.js [data-static-save-fallback] (the reverted plain gate, superseded-in-writing comment)"
  - "companion/test_config_page.py::_the_native_submit_is_emitted_unconditionally_on_every_render (source+render proof)"
  - "companion/test_browser_ux.py::_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies (disk+submit proof)"
affects:
  - "27-04 (auto-save) — depends on this plan's floor check passing UNCHANGED; also inherits two dirty-bar-referencing checks this plan touched that WILL need retargeting when the bar itself is retired"
  - "27-09 (the phase gate; this plan ticks no requirement itself — CFG-64/CFG-71 are 27-09's to tick)"
tech-stack:
  added: []
  patterns:
    - "the floor is kept BY CONSTRUCTION (unconditional emission, proven at the AST source level plus a per-scope render count) rather than by a CSS visibility rule's specificity — the CSS rule is now free to be the simplest possible script-presence gate"
    - "a superseded contract is amended IN WRITING: the original comment block is kept verbatim and a dated, plan-id-stamped paragraph is appended after it, naming what replaced it without quoting any CSS selector literal (D-30 — test_config_page.py locates rules by the first occurrence of a literal in style.css)"
    - "a CSS gate change that a pre-existing check encodes with SCRIPTS ENABLED (not blocked) must be hunted down and retargeted in place — running the affected task's own harness in isolation is not enough; only the FULL suite surfaces a check written against the behaviour being intentionally superseded"
key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_browser_ux.py
    - companion/test_config_page.py
decisions:
  - "Task 3's field is tracked_runway, reusing 25-03's own field and its exact form=\"settings-form\" mutation (M20) — theme_arriving/calendar_theme_id were considered and rejected: their default is None (\"same as departures\"), and _persist_once()'s own stored-vs-value string comparison cannot verify a clear-to-None restore (submitting the empty-string leading chip normalises to None on disk, which the helper reads as 'stored is None' and raises even on a correct restore) — a structural mismatch with the generic helper, not a per-field preference"
  - "the pre-existing _fallback_save_reachable_until_bar_proven_live check (D-01/B1's own contract, scripts ENABLED) was retargeted in place rather than left to fail — Task 2's CSS change intentionally makes the fallback hide IMMEDIATELY once script runs, the opposite of what that check asserted; found only by running the FULL test_browser_ux.py suite, not by the two task-scoped harness runs alone"
  - "_style_css_references_static_save_fallback_attr (test_config_page.py) was retargeted in place, not deleted, using the same distinctive-sentence-survives-verbatim technique this plan's own style.css comment amendment uses, so the Python check and the CSS comment it verifies stay in the same 'superseded in writing' discipline"
metrics:
  duration: ~1h10m
  completed: 2026-09-15
  checks_added: "browser-ux 82 -> 83; config-page 260 -> 261"
  browser_harness: "83/83, 345.6s (full suite run)"
  config_harness: "261/261, 2.6s"
  full_suite: "sandbox baseline exactly 5 failing checks, verified BY NAME, no sixth"
requirements-completed: []
---

# Phase 27 Plan 03: the no-JS save floor becomes structural — Summary

**The native settings submit is now emitted unconditionally on every render (proven at the AST source level plus a per-scope count, not assumed), the fallback-hide CSS rule reverts to the plain `.js` gate it originally shipped as, B1/P0's superseded two-marker contract is amended in writing rather than deleted, and the floor is proven to save to disk — with the submit's presence asserted AFTER the save — before 27-04 retires the save bar it used to depend on.**

## Performance

- **Duration:** ~1h10m
- **Tasks:** 3 of 3, plus one pre-existing check retargeted in place (found only by running the full suite)
- **Files modified:** 4 (`config_page.py` — reviewed, no diff; `style.css`; `test_browser_ux.py`; `test_config_page.py`)
- **Commits:** 3

## Commits

| # | Commit | Subject |
|---|---|---|
| 1 | `ca27c2a` | test: prove the native submit is emitted unconditionally (CFG-64) |
| 2 | `2c47284` | fix: revert the fallback-hide rule to the plain .js gate (CFG-64) |
| 3 | `b717aab` | test: prove the floor saves to disk after the gate simplifies (CFG-64) |

## The decision that mattered most

**Running the FULL `test_browser_ux.py` suite before committing Task 3 — not just the new check — is what caught a second, unlisted casualty of Task 2's CSS change: `_fallback_save_reachable_until_bar_proven_live`.**

That check encoded B1/P0's own two-marker contract directly, with scripts *enabled*: it asserted the fallback stayed **visible** on a fresh load (before the bar had ever shown) and only hid **after** the bar had genuinely revealed itself. Task 2's whole point is that the fallback no longer waits for that proof — with the plain `.js` gate, it hides the instant script runs, unconditionally, regardless of dirty state. That is not a bug Task 2 introduced; it is the exact, deliberate behaviour change this plan exists to make. But the check asserting the *old* behaviour does not know that, and nothing in Task 2's own `<files>` list (`companion/static/style.css` only) or Task 3's own scope would have surfaced it — only running the entire file did. It was retargeted in place (`_fallback_save_hides_immediately_once_script_runs`), asserting the new claim (hidden immediately, stays hidden once the bar appears too, the bar's own Save still genuinely submits), with a comment explaining the supersession the same way `style.css`'s own comment does.

This is the same shape as the `_style_css_references_static_save_fallback_attr` retarget in `test_config_page.py`, found by the SAME discipline one level earlier (running `test_config_page.py` after the CSS edit, before ever touching the browser harness). Two checks encoding the same superseded contract, in two different files, at two different layers (markup assertion vs. real-browser interaction) — neither was in either task's own `<files>` list, and both were necessary fixes for the plan's own stated verification bar ("no SKIP", "exactly the 5 baseline failures").

## Mutations, quoted

**Task 1 — deleting `STATIC_SAVE_FALLBACK_ATTR` from the return template's own tuple:**

```
render()'s one return statement never names STATIC_SAVE_FALLBACK_ATTR at all — the submit is
not part of what this function returns
```

Two pre-existing checks also failed alongside it on the same mutation (the D-09 no-JS-floor check and the B1/D1 swap-region check), corroborating that this surface was already under test from other angles — the new check adds the SOURCE-level proof those two lacked.

**Task 2 — reverting the selector back to the two-marker shape (`.dirty-ready.dirty-shown [data-static-save-fallback]`):**

```
expected the fallback-hide rule's OWN selector to carry neither dirty-ready nor dirty-shown any
more (CFG-64: the floor is kept by unconditional emission, not by these two markers) — selector
window reads "succeeded. */\n.dirty-ready.dirty-shown [data-static-save-fallback] {\n  display:
none;\n}\n\n/* 22-14-PLAN.md Task 2 (X9/D-10): `.mobile-nav__nav`'s own rule is\n * "
```

**Task 3 — removing `form="settings-form"` from the runway radios (the same mutation 25-03 recorded as M20), run against a standalone harness+browser rather than the full suite:**

```
_persist_without_js: the 'tracked_runway' control on /display belongs to no <form>, so with
scripts blocked there is nothing that can post it at all
```

Message is byte-identical in shape to 25-03's own M20 record, confirming the check exercises the same real DOM `form=` association, not a fabricated one.

## Checks that failed the vacuity question, and what was done

- **Task 1's source-and-render proof** would have been vacuous if it only checked render-time output (a page that happens to render the attribute today says nothing about whether a future branch could omit it on some other path). It additionally walks the AST: exactly one `return` statement, that statement a direct member of the function body (never nested under `if`/`for`/`while`/`try`), and the attribute reached as a bare `Name` never behind an `ast.IfExp`. Mutation-tested by deleting the attribute — confirmed non-vacuous (quoted above).
- **Task 2's retargeted CSS check** would have been vacuous if it only asserted the NEW selector was present without also asserting the OLD combined selector was gone — a check that never looks for the thing it claims was removed cannot tell "reverted" from "duplicated." Mutation-tested by reverting the selector back to the two-marker shape (quoted above) — the check fails specifically on the "neither marker" assertion, not on some unrelated clause.
- **Task 3's floor check** would have been vacuous if it asserted only "the submit renders" (passes against a page that saves nothing — the Phase 22 P0 exactly) or only "the value reaches disk" (passes against a submit hidden by `display:none`, unreachable, that some OTHER code path happened to POST). It carries both facts about the ONE relationship, deliberately never split into two checks, with the submit's presence asserted textually AFTER the disk read succeeds. Mutation-tested via the `form=` removal (quoted above), which fails specifically on the disk-read half — confirming the check's failure mode names the actual missing property (no `<form>` to post through) rather than a downstream symptom.

## Any criterion that did not evaluate as predicted

The plan's Task 2 acceptance criteria named specific absolute counts for two structural invariants. Both were re-measured directly rather than assumed, and both diverged from the plan's stated number while the actual invariant ("unmoved by this plan's edit") held:

- **`grep -c '@keyframes' companion/static/style.css`**: plan says **4**; measured **5**, both before and after this plan's diff (4 real `@keyframes` blocks plus one pre-existing comment mention at line 3143, "... and no new @keyframes."). The plan's number appears to predate that comment landing. Unmoved by this plan either way — confirmed by measuring before and after the edit, not by trusting the plan's figure.
- **`interpolate-size`/`calc-size(` count**: plan says **0**; measured **2**, both before and after (two pre-existing prose mentions of the *ban* on these properties, at lines 609 and 4232 — neither is a live declaration). Unmoved by this plan.
- **The brace-anchored `@supports selector(:has(*))` count**: plan says **1**; measured **1**, matching exactly.

Recorded here per the standing instruction to report predicted-vs-actual divergence rather than silently reconcile it. Neither divergence reflects anything this plan touched — both counts were identical immediately before and after the diff, which is the actual property Task 2's acceptance criteria cared about ("the stylesheet's structural counts are unmoved").

## The superseded-comment text, as written

Appended after B1/P0's own comment block at `companion/static/style.css`, which is kept **verbatim** (not one sentence removed):

> 27-03-PLAN.md (2026-09-15, CFG-64): SUPERSEDED above, not withdrawn — the account above was correct for a page whose only save feedback was the bar it describes, and this paragraph does not erase that history. Auto-save (27-04) retires the bar entirely; with no dirty state left to represent, there is nothing left for the two narrowing marker classes above to mean on THIS rule, and nothing left for them to prove the liveness of. The floor this rule used to carry is kept a different way now: render()'s emission of the attribute STATIC_SAVE_FALLBACK_ATTR names is unconditional on every scope (companion/pages/config_page.py, verified at the source by 27-03-PLAN.md Task 1), so there is no render-time branch left for a hiding rule to guard against. Hiding this button is now a plain script-presence decision — the same one the file's other progressive-enhancement rules already make — rather than a proof that a specific replacement bar succeeded.

No CSS selector literal appears anywhere in the new paragraph (D-30) — cross-references are by Python constant name (`STATIC_SAVE_FALLBACK_ATTR`) and plan id only. Verified by scanning the added lines for `.`-prefixed tokens: the only matches are file extensions (`.md`, `.py`), not selectors.

## Re-derived counts, obtained by running

- `config-page`: **260 → 261** (`EXPECTED_CHECK_COUNT` updated; Task 1's source-and-render proof is the one addition; Task 2's CSS-comment check is retargeted in place, net 0).
- `browser-ux`: **82 → 83** (`EXPECTED_CHECK_COUNT` updated; Task 3's disk-and-submit proof is the one addition; the pre-existing B1/D-01 check is retargeted in place, net 0). Verified **twice**: once before the B1/D-01 retarget (82/83, one real failure), once after (83/83, clean).
- **Sandbox baseline, verified BY NAME via the full `scripts/run-all-tests.sh`**: exactly 5 — `POST /airlines/resolve` WR-11, `POST /airlines/manual-resolutions/{prefix}/delete` WR-11 (both `companion/test_companion_app.py`), `add_entry()`/`delete_entry()` WR-11 (both `server/test_manual_resolutions.py`), and `anomaly_active()` (`companion/test_status_pages.py`). **No sixth failure.**

## What was built

### Task 1 — the submit becomes unconditional, verified at the source

Read the settings-form builder first, per the plan's own instruction to verify rather than assume. **Finding: the emission was already unconditional.** `render()` has exactly one `return` statement (confirmed via `sed`/`grep` across the function's own line span, and again via `ast.walk`), it is a direct statement of the function body — never nested inside any of the three `scope` branches (`SCOPE_ALL`/`SCOPE_DISPLAY`/`SCOPE_DEVICE`) — and `STATIC_SAVE_FALLBACK_ATTR` appears exactly once in the whole module, as a bare tuple element inside that one return's own `%`-formatting args. **No production code changed** for Task 1; the only diff is the new check itself.

Added `_the_native_submit_is_emitted_unconditionally_on_every_render` (`companion/test_config_page.py`): an AST-level proof (one return, unconditioned, the attribute reached as a bare `Name` outside any `ast.IfExp`) plus a render-level proof (all three scopes render the attribute exactly once, in a single check rather than three, naming the failing scope). Mutation-tested (quoted above).

### Task 2 — the visibility rule reverts to the plain `.js` gate

`companion/static/style.css`: the selector changes from `.dirty-ready.dirty-shown [data-static-save-fallback]` to `.js [data-static-save-fallback]`. The original B1/P0 comment block is kept intact; a dated paragraph is appended (quoted above in full). Structural counts confirmed unmoved (see "criterion that did not evaluate as predicted" above); zero stray comment terminators (`/*` count == `*/` count, 492 each, before and after).

`companion/test_config_page.py`'s `_style_css_references_static_save_fallback_attr` was retargeted in place (not in Task 2's own `<files>` list, but required for the plan's own "no SKIP, passes" verification bar) to assert the new selector shape, the old combined selector's absence, the original comment's distinctive sentences surviving verbatim, and the dated `27-03-PLAN.md`/`SUPERSEDED` paragraph's presence. Mutation-tested (quoted above).

### Task 3 — the floor proven by saving to disk, both languages, 360px

Added `_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies` (`companion/test_browser_ux.py`): `tracked_runway` via `_persist_without_js()` (GET → operate → submit → second GET → disk read), in both shipped languages, at `VIEWPORT_MIN_SUPPORTED`, restored as the last act — then, in the SAME check, a separate `_no_js_page()` block asserts the `data-static-save-fallback` submit is present and **visible**, textually placed AFTER the disk-read assertions so a rendering can never stand in for the save. Mutation-tested via 25-03's own M20 (quoted above), run against a standalone harness+browser script rather than the full suite (faster iteration; the full suite confirmed the fix afterward).

Discovered and fixed in the same task, by running the full suite: `_fallback_save_reachable_until_bar_proven_live` (scripts-enabled B1/D-01 contract check) failed against Task 2's change. Retargeted to `_fallback_save_hides_immediately_once_script_runs`, asserting the fallback is hidden immediately on a fresh scripted load, stays hidden once the dirty bar appears, and that the bar's own Save still genuinely submits. Also fixed one now-inaccurate failure-message string in `_with_no_script_there_is_no_bar_and_the_fallback_save_is_the_only_way` ("the fallback-hide rule keys on both" → notes Task 2 no longer keys on either marker).

## Files Created/Modified

- `companion/pages/config_page.py` — **reviewed, not modified.** The single-return, unconditional-emission property Task 1 proves already held; no diff was needed to satisfy it.
- `companion/static/style.css` — the fallback-hide rule's selector, and the superseded-contract paragraph.
- `companion/test_config_page.py` — the new source-and-render proof (Task 1); the retargeted CSS-comment check (Task 2, not in its own `<files>` list but required); `EXPECTED_CHECK_COUNT` 260→261.
- `companion/test_browser_ux.py` — the new disk-and-submit proof (Task 3); the retargeted B1/D-01 check and one failure-message fix (found running the full suite, not in Task 3's own `<files>` list but required); `EXPECTED_CHECK_COUNT` 82→83.

## Decisions Made

See `decisions` frontmatter and "The decision that mattered most" above for full reasoning; in one line each:

1. `tracked_runway` (25-03's own field, 25-03's own M20 mutation) for Task 3's floor check — `theme_arriving`/`calendar_theme_id` rejected: their None-default "clear" semantics break `_persist_once()`'s own stored-vs-value comparison for a restore leg.
2. `_fallback_save_reachable_until_bar_proven_live` retargeted in place, not left failing or deleted — it is B1/D-01's own contract, and Task 2 intentionally supersedes it; found only by running the FULL suite.
3. `_style_css_references_static_save_fallback_attr` retargeted in place, using the same "distinctive sentences survive verbatim" technique as the CSS comment it verifies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking issue] `_style_css_references_static_save_fallback_attr` asserted the superseded selector shape**
- **Found during:** Task 2, running `companion/test_config_page.py` immediately after the CSS edit
- **Issue:** the check required both `dirty-ready`/`dirty-shown` in the selector window and explicitly asserted the OLD `.js`-only selector must be absent — the exact opposite of Task 2's own change
- **Fix:** retargeted in place to assert the new selector shape, the old two-marker selector's absence, and the superseded-comment's presence
- **Files modified:** `companion/test_config_page.py`
- **Verification:** mutation-tested (quoted above); `companion/test_config_page.py` 261/261
- **Committed in:** `2c47284`

**2. [Rule 3 — blocking issue] `_fallback_save_reachable_until_bar_proven_live` asserted the superseded B1/D-01 visibility behaviour with scripts enabled**
- **Found during:** Task 3, running the FULL `companion/test_browser_ux.py` suite (not surfaced by either task's own scoped verification command)
- **Issue:** asserted the fallback stays visible-with-script until the dirty bar proves itself live, then hides — Task 2's plain `.js` gate hides it immediately instead, unconditionally
- **Fix:** retargeted to `_fallback_save_hides_immediately_once_script_runs`, asserting the new behaviour plus confirming the dirty bar's own Save is unaffected
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** full suite run twice (82/83 before the fix showing this as the ONE real failure, 83/83 after); `scripts/run-all-tests.sh` final pass, exactly 5 baseline failures by name
- **Committed in:** `b717aab`

**3. [Rule 1 — documentation bug] a failure-message string in a neighbouring check claimed the fallback-hide rule still "keys on both" markers**
- **Found during:** Task 3, reading the surrounding area of the file while investigating the retarget above
- **Issue:** `_with_no_script_there_is_no_bar_and_the_fallback_save_is_the_only_way`'s own failure message (only shown if that check ever fails) asserted a now-false claim about the CSS rule's selector
- **Fix:** message updated to note Task 2's change and that this assertion is now corroboration, not the floor itself
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** the check's PASS path is unaffected (message text only surfaces on failure); syntax-checked via `ast.parse`
- **Committed in:** `b717aab`

---

**Total deviations:** 3 auto-fixed (2 Rule 3 — blocking issues Task 2's own intentional change created in checks outside either task's own `<files>` list; 1 Rule 1 — a documentation string made false by the same change). **Impact on plan:** all three were necessary for the plan's own verification bar (no SKIP, full suite passes with exactly the 5 baseline failures); none changed this plan's scope, `must_haves`, or files ultimately touched (all three retargeted files were already in the plan's frontmatter `files_modified` list, even though not named in the specific task that ended up needing them).

## Issues Encountered

None beyond the three auto-fixed items above, each already documented with how it was found and resolved.

## A note for 27-04's author

**This plan's Task 3 floor check (`_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies`) does not depend on the dirty bar at all** — it operates a form field with scripts blocked, submits through the native fallback, and reads disk. 27-04 retiring the dirty bar should leave this check passing **unchanged**, which is the property the orchestrator asked to be verified explicitly: it does not.

**Two OTHER checks this plan touched DO reference the dirty bar and WILL need attention in 27-04**, and that is expected, not a sign the floor moved:
- `_fallback_save_hides_immediately_once_script_runs` (this plan's own retarget) asserts the bar appears on an edit and its own Save submits — both claims about the bar itself, which 27-04 removes.
- `_with_no_script_there_is_no_bar_and_the_fallback_save_is_the_only_way` (pre-existing, 23-09-PLAN.md) asserts `.dirty-ready`/`.dirty-shown` are absent from `<html>` and that `[data-dirty-bar]` computes `display:none` with scripts blocked — both statements about a bar 27-04 deletes outright.

Neither of these is Task 3's own floor check. If 27-04 needs to edit **`_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies` itself** to pass, that is the signal the floor moved and should be flagged loudly in that plan's own SUMMARY — but the two bar-referencing checks above are not that signal; they are simply testing the thing 27-04 is explicitly tasked with removing.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

All claimed files verified present (`companion/pages/config_page.py`, `companion/static/style.css`,
`companion/test_browser_ux.py`, `companion/test_config_page.py`, this SUMMARY). All three commit hashes
(`ca27c2a`, `2c47284`, `b717aab`) verified present in `git log --oneline --all`. No missing items.
