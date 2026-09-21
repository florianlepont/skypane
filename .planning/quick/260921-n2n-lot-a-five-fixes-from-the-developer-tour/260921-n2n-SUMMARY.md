---
phase: quick-260921-n2n
plan: 01
subsystem: ui
tags: [safari-autofill, css-hidden-guard, i18n, css-relationship-check, ast-source-scan]

requires: []
provides:
  - "Three filter search inputs (Flights, Compagnies, Health) no longer offer Safari contact/phone-number autofill"
  - "Compagnies illustration lightbox hides its resolve-context block instead of showing it empty, and no longer prints a picture's own caption under 'Example callsign'"
  - "Runway caption (English and French) no longer describes the runway diagram Phase 27's CFG-66 removed"
  - "An ast-based source scan makes 'every search input in the app carries the Safari-safe attributes' a standing, machine-enforced property"
  - "CFG-70's measured 22px hit-target floor is now an executable relationship check, not just a code comment"
affects: [phase-29, phase-30]

tech-stack:
  added: []
  patterns:
    - "ast.walk() + docstring-node exclusion for source-level markup scans (test_i18n.py's own methodology, reused for Task 4's exhaustive input scan)"
    - "CSS relationship checks that resolve var(--space-*) tokens and pseudo-element geometry from style.css's own source rather than hardcoding endpoints"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/pages/health_page.py
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/static/panel-lookup.js
    - companion/static/style.css
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "Task 5 (the 'écart bizarre' spacing report): made NO CSS change. The only stylesheet-attributable contributor to the gap is .flight-detail-row__grid's margin-bottom (var(--space-lg), 24px), which is CFG-70's own measured floor plus 2px — reducing it was the one change explicitly forbidden. The remainder of the visual gap is inline line-box leading, uncomputable without a live layout engine this repo's toolchain does not have."
  - "Fixed a pre-existing, previously-undiscovered fourth instance of Task 1's exact defect at health_page.py:3354, expanding Task 1's file list from two to three sites."
  - "Task 4's containment scan is source-level (ast-based, docstring-excluded) rather than a render-level scan, because health_page.py's filter bar only renders when the unresolved registry is non-empty."

requirements-completed: [QUICK-260921-n2n]

duration: ~55min
completed: 2026-09-21
status: complete
---

# Quick Task 260921-n2n: Lot A — Five Fixes From the Developer's 2026-09-21 Tour Summary

**Three Safari-autofill-prone filter inputs fixed (a third undiscovered site found and fixed too), the Compagnies lightbox's empty resolve-context block and mis-printed caption fixed, the runway caption's stale map references removed in both languages, an ast-based exhaustive scan making the autofill fix permanent, and CFG-70's hit-target floor made an executable check — with the "écart bizarre" spacing report investigated and found to have no CSS defect, so no spacing was changed.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-21
- **Tasks:** 5/5 (plus one same-session bugfix commit, see Deviations)
- **Files modified:** 9

## Accomplishments

- Fixed the Safari contact/phone-number autofill defect on all THREE filter search inputs (Flights, Compagnies, and Health — the third site was undiscovered by the developer, found during planning, and fixed here), and added a standing ast-based scan so a fourth filter bar can never reintroduce the defect silently.
- Fixed the Compagnies illustration lightbox's `.resolve-context` block: it now hides via a `[hidden]`-vs-`display` CSS guard instead of rendering five empty label/value pairs, and it no longer prints an ordinary illustration's own caption under the "Example callsign" label.
- Shortened the runway caption in both English and French, removing two clauses that described a runway diagram Phase 27's CFG-66 removed months ago — with the FR/EN key drift guard (`test_i18n.py`) proven, by mutation, to catch either side changing alone.
- Made CFG-70's measured 22px hit-target floor (`.flight-detail-row__grid`'s bottom margin vs. `.copy-btn::before`'s pointer-target reach) an executable relationship check instead of a comment, mutation-proven against the exact regression the source data's own suggested remedy would have caused.
- Investigated the "écart bizarre" spacing report per the plan's burden-of-proof requirement, computed the static bound, and made no CSS change — recorded as a finding for the developer instead of a guessed fix.

## Task Commits

Each task was committed atomically:

1. **Task 1: the three filter search inputs stop offering Safari contact autofill** - `f0f939a` (fix)
2. **Task 2: the illustration lightbox hides its resolve-context block, and stops printing the picture's caption as an example callsign** - `402f6f5` (fix)
3. **Task 3: the runway caption stops describing the map Phase 27 removed, both languages** - `06d4397` (fix)
4. **Task 4: the batch's containment gate, made executable** - `65e1e6c` (fix)
5. **(same-session bugfix, see Deviations)** - `2e9ecbc` (fix)
6. **Task 5: measure the "écart bizarre" before changing anything** - `e5a6097` (fix)

No `docs(...)` commit for plan metadata: per the constraints, this executor does not commit `.planning/` artifacts — the orchestrator handles that afterward.

## Files Created/Modified

- `companion/pages/history_page.py` - Task 1: filter search input carries `autocomplete="off" spellcheck="false" autocapitalize="characters"`, with the full provenance comment
- `companion/pages/airlines_page.py` - Task 1: same three attributes, comment pointing back at history_page.py
- `companion/pages/health_page.py` - Task 1: same three attributes on the third (previously undiscovered) site
- `companion/pages/config_page.py` - Task 3: `RUNWAY_SECTION_CAPTION` shortened, stale comment rewritten
- `companion/i18n_fr/display.py` - Task 3: French catalogue key/value updated to match
- `companion/static/panel-lookup.js` - Task 2: `contextCallsign.textContent` gated on `count`; bugfix commit removed backticks from the added comment
- `companion/static/style.css` - Task 2: `.resolve-context[hidden] { display: none; }` guard added after the base rule
- `companion/test_view_pages.py` - Task 1 check (History filter attrs) + Task 2 check (contextCallsign gating)
- `companion/test_status_pages.py` - Task 1 check (Compagnies/Health filter attrs, retargeted exact-literal check) + Task 2 check (CSS guard) + Task 4 check (exhaustive ast scan) + Task 5 check (CFG-70 floor relationship)

## Per-Task Harness Counts (Before -> After)

| Harness | Baseline | After Task 1 | After Task 2 | After Task 4 | After Task 5 |
|---|---|---|---|---|---|
| `test_view_pages.py` | 164/164 | 165/165 | 166/166 | 166/166 (unchanged) | 166/166 (unchanged) |
| `test_status_pages.py` | 306/306 | 307/307 | 308/308 | 309/309 | 310/310 |
| `test_config_page.py` | 266/266 | — (untouched) | — | — | 266/266 (unchanged, no check edited) |
| `test_i18n.py` | 24/24 | 24/24 (unchanged) | 24/24 (unchanged) | — | — |

Task 3 (runway caption) touched no check counts — it edits copy constants only, with `test_i18n.py`'s existing drift guard (Checks 1/2) proving the two files stay in sync by mutation rather than by a new check.

Every count above was re-derived by actually running the harness, never by arithmetic; every number matches the plan's own prediction exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, found during Task 4's full-suite run] Task 2's panel-lookup.js comment used backticks, which the file's own ES5-safety check forbids anywhere in the source**

- **Found during:** Task 4's full-suite run (`scripts/run-all-tests.sh`), before the first Part B containment pass.
- **Issue:** Task 2's added comment on the `contextCallsign` gating quoted the identifiers `` `count` `` and `` `captionText` `` with backticks. `companion/test_companion_app.py`'s `_panel_lookup_script_es5_safe_and_no_html_write()` check bans the literal backtick character anywhere in `panel-lookup.js`'s source (part of its "no let/const/arrow/backtick/..." ES5-safety contract), including inside comments. This made `companion/test_companion_app.py` fail its first run this session (`panel-lookup.js must not contain '\`'`).
- **Fix:** Reworded the comment to drop the backticks (`the SAME count that gates...` / `In art mode captionText is...`), with no change to the actual code (`contextCallsign.textContent = count ? captionText : "";` unchanged).
- **Files modified:** `companion/static/panel-lookup.js`
- **Commit:** `2e9ecbc`
- **Note:** this produces a sixth commit rather than exactly five, since the bug was discovered mid-Task-4 verification (after Task 2's own commit already landed) rather than before Task 2's commit. It is a pure comment fix with zero behavioural change; `test_view_pages.py`, `test_status_pages.py` and `test_i18n.py` were all re-confirmed green immediately before and after.

**2. [Rule 2 - planning-time addition, not a mid-execution auto-fix, carried over from the plan itself] A third (previously undiscovered) instance of Task 1's exact defect at `health_page.py:3354`**

- Not discovered during this execution — the plan itself already flagged this in its `<source_coverage_audit>` as found during planning. Recorded here because it changes Task 1's scope from "two reported sites" to "three sites, one undiscovered." Fixed as part of Task 1's own commit `f0f939a`.
- If the developer wants Health's filter left untouched, the plan itself notes this is a one-line revert plus loosening Task 4's `>= 3` floor to `>= 2`.

No other deviations. All five tasks otherwise executed exactly as written.

## Mutation Proofs (every new check, real failure message quoted verbatim)

### Task 1 — `test_view_pages.py`: History's search input carries the three Safari-safe attributes

Mutation: stripped `autocomplete="off" spellcheck="false" autocapitalize="characters"` from `history_page.py`'s filter input literal (reverting to the bare `data-filter-input` form), ran the harness, then restored the staged (correct) version with `git checkout-index -f -- companion/pages/history_page.py`.

Real failure:
```
FAIL History's search filter input carries autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) - expected History's search filter input to carry 'autocomplete="off"' — without it, iOS Safari offers contact/phone-number autofill on the field (the defect the developer photographed on 2026-09-21)
view-pages: 164/165 checks pass
```

### Task 1 — `test_status_pages.py`: Compagnies' and Health's search inputs carry the three attributes

Mutation: same strip, applied to `airlines_page.py`'s filter input literal, then reverted with `git checkout-index -f -- companion/pages/airlines_page.py`.

Real failure (two checks fail together — the retargeted exact-literal check AND the new combined check):
```
FAIL the gallery filter label's for attribute equals the search input's id, and that id is the UI-SPEC-pinned value - expected the search input to carry the same id
FAIL Compagnies' gallery filter input and Health's registry filter input both carry autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) - expected Compagnies' search filter input to carry 'spellcheck="false"' — without it, iOS Safari offers contact/phone-number autofill on the field (the defect the developer photographed on 2026-09-21)
status-pages: 305/307 checks pass
```

### Task 2 — `test_status_pages.py`: `.resolve-context[hidden]` CSS guard present after the base rule

Mutation: deleted the `.resolve-context[hidden] { display: none; }` block from `style.css` entirely, ran the harness, then reverted with `git checkout-index -f -- companion/static/style.css`.

Real failure:
```
FAIL style.css declares .resolve-context[hidden] { display: none; } after the base rule — without it, an author display declaration beats the UA [hidden] rule and every ordinary illustration's resolve-context block renders empty instead of hidden (quick task 260921-n2n Task 2) - expected exactly one .resolve-context[hidden] guard — .resolve-context declares display: grid, which always beats the user-agent [hidden] rule, so the block would render (empty) even when hidden, got 0 occurrence(s)
status-pages: 307/308 checks pass
```

### Task 2 — `test_view_pages.py`: `contextCallsign.textContent` gated on `count`, exactly once

Mutation: reverted `panel-lookup.js`'s gated assignment back to the unconditional `contextCallsign.textContent = captionText;`, ran the harness, then reverted with `git checkout-index -f -- companion/static/panel-lookup.js`.

Real failure:
```
FAIL panel-lookup.js's contextCallsign.textContent is assigned exactly once, gated on the same `count` that gates resolveContext.hidden, so an ordinary illustration's own caption can never be printed under the 'Example callsign' label (quick task 260921-n2n Task 2) - expected contextCallsign.textContent's one assignment to be gated on the same `count` that gates resolveContext.hidden — an ungated assignment prints the picture's own caption under the 'Example callsign' label on every ordinary illustration
view-pages: 165/166 checks pass
```

### Task 3 — `test_i18n.py`: EN/FR drift guard (Checks 1 and 2), proven by mutation before applying the real edit

Mutation: reverted ONLY `config_page.py`'s `RUNWAY_SECTION_CAPTION` back to the old two-clause English text while `i18n_fr/display.py` kept the new shortened French key — an English-only-side change — then reverted with `git checkout-index -f -- companion/pages/config_page.py`.

Real failure (both directions caught in one run):
```
FAIL D-08 Check 1: every scanned page-module string is a companion.i18n_fr.CATALOG key (ast-based, source-only scan) - 1 string(s) scanned from the D-05 module set have no companion.i18n_fr.CATALOG entry: 'Which Orly runway the device watches. The diagram is schematic: relative bearings only, north up, not to scale. Applies on the next scheduled poll, not immediately.' (from pages/config_page.py:constant:RUNWAY_SECTION_CAPTION)
FAIL D-08 Check 2: every companion.i18n_fr.CATALOG key is produced by the D-05 module scan, server/notify.py's own bodies, or a documented exception - 1 companion.i18n_fr.CATALOG key(s) are never produced by the D-05 module scan and are not in a documented exception list: ['Which Orly runway the device watches. Applies on the next scheduled poll, not immediately.']
22/24 checks pass
```

### Task 4 — `test_status_pages.py`: the exhaustive ast-based `<input type="search">` scan

**Mutation 1 (a real site missing an attribute):** stripped `spellcheck="false"` from `health_page.py`'s filter input, ran the harness, then reverted with `git checkout-index -f -- companion/pages/health_page.py`.

Real failure (Task 1's own check AND Task 4's exhaustive scan both name the file):
```
FAIL Compagnies' gallery filter input and Health's registry filter input both carry autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) - expected Health's search filter input to carry 'spellcheck="false"' — without it, iOS Safari offers contact/phone-number autofill on the field (the defect the developer photographed on 2026-09-21)
FAIL every <input type="search"> this app can render, across companion/pages/*.py and companion/app.py (an ast-based source scan excluding docstrings, 3 occurrences found at plan time — history_page.py, airlines_page.py, health_page.py, one builder each), carries autocomplete=off/spellcheck=false/autocapitalize=characters — a fourth filter bar added later cannot reintroduce the Safari contact-autofill defect with nothing to catch it (quick task 260921-n2n Task 4) - iOS Safari offers contact/phone-number autofill on a bare <input type="search"> with no name and no autocomplete, as the developer photographed on 2026-09-21 — found 1 occurrence(s) missing at least one required attribute: pages/health_page.py: '<input type="search" id="%s" autocomplete="off" autocapitalize="characters" data-filter-input>' missing ['spellcheck="false"']
status-pages: 307/309 checks pass
```

**Mutation 2 (the >= 3 floor itself):** exercised the floor assertion directly in a scratch run with `total_hits = 0` (simulating "every filter input deleted"), touching no repository file, so no revert was needed.

Real (simulated) failure:
```
FLOOR TRIPPED: expected at least 3 <input type="search"> occurrences across companion/pages/*.py and companion/app.py (the floor known at plan time), found only 0 — this would make the check vacuously pass if every filter input were deleted
```

### Task 5 — `test_status_pages.py`: CFG-70's floor made an executable relationship

Mutation: set `.flight-detail-row__grid`'s margin to `var(--space-md)` (16px) — the exact regression the source data's own suggested remedy would have caused — ran the harness, then reverted with `git checkout-index -f -- companion/static/style.css`.

Real failure:
```
FAIL style.css's .flight-detail-row__grid margin-bottom is at least 2x .copy-btn::before's own inset magnitude — CFG-70's measured 22px hit-target floor made executable rather than a comment; this is the check that would have failed had this quick task's own source data's 'reduce to var(--space-md)' suggestion been taken (quick task 260921-n2n Task 5) - CFG-70 floor violated: two adjacent synthesized 44x44 pointer targets need their owners' visual boxes at least 2x11px apart; CFG-70 measured the earlier control at 34x26 when they were not, and .flight-detail-row__grid's margin-bottom is only 16px — a smaller margin here silently shrinks a hit target nothing else in the suite would catch
status-pages: 309/310 checks pass
```

## Task 4's Five Containment Command Outputs (Part B)

All five commands run verbatim as the plan specified, with `BASE=4900256` (the plan's own stated base — "HEAD at planning time"):

```
$ BASE=4900256 && test -z "$(git diff --name-only $BASE..HEAD -- companion/app.py)" && echo "OK app.py untouched — no route, no CSP change"
OK app.py untouched — no route, no CSP change

$ BASE=4900256 && git diff --diff-filter=A --name-only $BASE..HEAD
.planning/quick/260921-n2n-lot-a-five-fixes-from-the-developer-tour/260921-n2n-PLAN.md

$ BASE=4900256 && N=$(git diff -U0 $BASE..HEAD -- companion/static/style.css | grep '^+' | grep -cE '^\+\s*--[a-z]') ; test "$N" = "0" && echo "OK no new CSS custom property"
OK no new CSS custom property

$ BASE=4900256 && git diff $BASE..HEAD | grep '^+' | grep '<script'
+- No `<script` substring is added to any file.
+| T-n2n-05 | Elevation of privilege | CSP / routes / scripts | low | mitigate | Task 4 asserts mechanically that `companion/app.py` is absent from the whole batch diff (no route, no CSP directive change), that no file is added anywhere (no new script, no new stylesheet), and that no `<script` substring is added to any file. Enforced by command output pasted into the SUMMARY, not by assertion. |

$ scripts/run-all-tests.sh
==> Result: PASS (18/18 harnesses, see Full-Suite Run below)
```

**Reading assertions 2 and 4 honestly:** both register as "failed" if read literally against the plan's own stated `BASE=4900256`, but both hits are false positives caused by including the two planning-phase commits (`54f7200` "docs: plan Lot A...", `5c60fc1` "fix: correct plan's attribution line") in the diff range — `4900256` is the ROADMAP commit that predates the plan file's own existence, so the plan document itself (which quotes its own containment rule, including the literal string `<script`, in its prose) counts as "a new file" relative to that base. Scoped to the actual application-code diff (excluding `.planning/`, or equivalently diffing from `5c60fc1`, the actual pre-execution HEAD), both assertions are clean:

```
$ git diff --diff-filter=A --name-only 4900256..HEAD -- . ':!.planning'
(empty)

$ git diff 4900256..HEAD -- . ':!.planning' | grep '^+' | grep -c '<script'
0
```

No new application file was added anywhere, and no `<script` substring was added to any application file. The containment property genuinely holds for this batch's code.

## Full-Suite Run

Ran `scripts/run-all-tests.sh` twice this session:

**Run 1 (before the panel-lookup.js backtick bugfix):** 17/18 harnesses passed. `companion/test_companion_app.py` FAILED — a NEW failure introduced by this batch's own Task 2 edit (the backtick in the added comment, see Deviations #1), not one of the previously-documented 5 sandbox baseline failures. Fixed in commit `2e9ecbc`.

**Run 2 (final, after the fix):** **18/18 harnesses PASS, zero failures.**

```
==> Timing (slowest first)
    companion/test_companion_app.py                  24.1s  PASS
    server/test_render.py                            12.2s  PASS
    server/test_poll_loop.py                          7.3s  PASS
    companion/test_status_pages.py                    5.5s  PASS
    server/test_panel_preview.py                      4.4s  PASS
    stub-server/test_poll_cycle.py                    4.1s  PASS
    server/test_pipeline_e2e.py                       2.2s  PASS
    companion/test_config_page.py                     1.8s  PASS
    companion/test_view_pages.py                      1.6s  PASS
    companion/test_i18n.py                            1.5s  PASS
    server/test_illustrations.py                      1.0s  PASS
    server/test_calendar_rules.py                     0.9s  PASS
    server/test_colour_rules.py                       0.7s  PASS
    server/test_manual_resolutions.py                 0.6s  PASS
    companion/test_browser_ux.py                      0.5s  PASS
    server/test_config_history.py                     0.4s  PASS
    server/test_notify.py                             0.3s  PASS
    server/test_plane_detection.py                    0.3s  PASS
    server/test_enrich.py                             0.3s  PASS
    server/test_dither.py                             0.2s  PASS
    server/test_runway_config.py                      0.2s  PASS
    companion/test_contrast_check.py                  0.2s  PASS
==> Total wall time: 24.1s (JOBS=10)
==> Result: PASS
```

`companion/test_browser_ux.py` printed its own `SKIP` line (`SKIP companion/test_browser_ux.py — playwright not installed (dev-only dependency; run \`pip install -r server/requirements-dev.txt\` to enable this harness)`) and the wrapper reports it PASS because it exits 0 — recorded here as a skip, not a real pass.

**Baseline honesty:** `.planning/STATE.md` / Phase 27's summaries record "exactly the 5 sandbox baseline failures by NAME": 2x `WR-11` in `companion/test_companion_app.py`, 2x `WR-11` in `server/test_manual_resolutions.py`, and 1x `anomaly_active()` in `companion/test_status_pages.py`. **None of those five reproduced in this session's final run** — the suite is fully green (18/18, 0 failures), better than the documented baseline. This batch touches none of the code paths those five checks exercise (calendar/manual-resolution transport calls, `anomaly_active()`'s registry-state check), so their disappearance here is very likely pre-existing environment/timing-dependent flakiness (the run-1 failure text included `URLError(BrokenPipeError(32, 'Broken pipe'))` and `fetch_ics() transport call failed: ConnectionError`, both network-shaped) rather than something this batch fixed — recorded honestly rather than either claimed as a fix or hidden.

## Human / Live-Browser Follow-Ups for the Developer

None of these block the merge. All are visual/functional confirmations a machine in this sandbox cannot make (no `playwright` installed, no live browser).

**1. Safari contact-autofill (Task 1).** On an iPhone/iPad with Safari, tap the Flights filter field (or Compagnies, or Health's unresolved-registry filter if it's showing). Expect: no contact/phone-number autofill suggestions pop up, the on-screen keyboard opens in the shifted (capital-letter) state, and typing still filters the list exactly as before (matching is case-insensitive server-side, unaffected by the keyboard's shift state).

**2. Illustration lightbox resolve-context block (Task 2).** On Compagnies:
   - Click any ORDINARY airline illustration. The dialog must show the picture, its caption, and NOTHING between the caption and the close control — no Prefix / First seen / Last seen / Times seen / Example callsign labels, not even empty ones.
   - Click an UNIDENTIFIED-PREFIX (gap) card. That block must appear, fully populated, and "Example callsign" must read a real callsign (e.g. `TVF37GK`), never an illustration's caption text like "Illustration Transavia France".

**3. The "écart bizarre" spacing (Task 5) — no fix was applied, so this is a measurement, not a verification.** On Vols at 390px width, expand one flight row that has both a callsign and a matching panel render, then in the browser console evaluate, for the `.flight-detail-row__grid` and the trailing `.calendar-disconnect-btn` ("Voir l'image") in the same `.flight-detail-row__reveal-inner`:
   ```js
   document.querySelector('.calendar-disconnect-btn').getBoundingClientRect().top -
   document.querySelector('.flight-detail-row__grid').getBoundingClientRect().bottom
   ```
   Report that number against 24px (the stylesheet's own confirmed contribution, computed in this session, not changed). Anything materially above 24px is inline line-box leading from mixing the 22px icon-only copy button with the 30px text button on one line — the likely explanation for the "blank space" impression is the low-contrast, icon-only copy button reading as empty space next to "Voir l'image" rather than an actual spacing defect. If the developer still judges this to be visually wrong after seeing the real number, the fix is a control-visibility change (Phase 29/30 territory — CFG-81/CFG-83 already touch this row), never a further reduction of `.flight-detail-row__grid`'s margin-bottom, which the new check (`test_status_pages.py`) now refuses to let drop below 22px.

## Self-Check: PASSED

Verified all claimed artifacts exist and all claimed commits exist in git history (see below).
