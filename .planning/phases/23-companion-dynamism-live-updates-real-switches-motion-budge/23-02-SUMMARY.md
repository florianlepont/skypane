---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 02
subsystem: testing
tags: [playwright, browser-harness, no-js-floor, reduced-motion, viewport, refactor, disclosure]

requires:
  - phase: 22-01
    provides: "the browser harness itself — check(), EXPECTED_CHECK_COUNT, the two SKIP gates and the Harness subprocess pattern this plan refactors inside"
  - phase: 260913-eab
    provides: "the general every-<details>-open sweep this plan makes motion-proof, and the mutation (min-width: max-content on table.data-table--readings) that proves it still sees its own defect"
  - phase: 23-01
    provides: "style.css's global prefers-reduced-motion override, whose 0.01ms cancel is the mechanism the sweep's new context now leans on"
provides:
  - "_no_js_page(browser, base_url, route, viewport=None, sign_in=True): the file's ONLY java_script_enabled=False call site — a scripts-blocked context, signed in, landed on a route, closed in a finally"
  - "VIEWPORT_MIN_SUPPORTED / VIEWPORT_PHONE / VIEWPORT_DESKTOP and the two width ladders derived from them — the first time 360px is nameable in this file"
  - "the general disclosure sweep running under a reduced-motion context, so it measures FINAL geometry once 23-08 and 23-10 animate disclosures"
affects: [23-05, 23-06, 23-07, 23-08, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "one helper owning a dangerous flag, pinned by an acceptance grep at exactly one occurrence — so a scripts-blocked proof cannot silently run with scripts enabled"
    - "a refactor proven to be a refactor by AST-comparing every check(...) description string against HEAD, not by reading the diff"
    - "making a measurement deterministic through the APP'S OWN reduced-motion override rather than through a wait, a timeout or an event listener"

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "The helper takes `sign_in` because one of the three converted checks must NOT sign in: the login card's whole subject is what /login renders with scripts blocked, and it signs in as its last act, as the assertion. The plan's read_first says the signature is whatever the call sites actually need, so this is latitude the plan granted, exercised."
  - "The 320px rung is kept as VIEWPORT_WIDTH_NARROW inside VIEWPORT_WIDTHS_ALL with SKILL.md's two non-licences quoted verbatim in the constant set's own comment, so a later reader cannot tidy it away as dead weight."
  - "The width ladders are DERIVED from the three viewport dicts (VIEWPORT_MIN_SUPPORTED[\"width\"], ...) rather than restated as literals, so every width this file measures at has exactly one definition."
  - "Reduced motion was added to the general sweep ONLY, not to its sibling 260913-cz6 check, because the plan names one check and pins the occurrence count. cz6 has the identical exposure and is recorded below as a finding for 23-08/23-10 rather than fixed here."
  - "EXPECTED_CHECK_COUNT is recorded in place beside the existing 26 rather than re-asserted below it: a new assignment would claim a change this plan did not make."

requirements-completed: []

duration: ~55min
completed: 2026-09-13
---

# Phase 23 Plan 02: The browser-harness helpers this phase runs on Summary

**The suite's only behaviour-seeing harness gains one scripts-blocked helper (three call sites collapsed to one), one named viewport set that can finally say 360px, and a disclosure sweep that measures final geometry rather than mid-transition — at exactly zero net checks, 26 before and 26 after, re-derived by running.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 2/2
- **Files modified:** 1 (0 created), +75 lines, −38
- **Harness runtime:** unchanged (see the table below)

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `f8868a4` | test(23-02): one no-JS helper and one viewport set, zero net checks |
| 2 | `d716b04` | test(23-02): the disclosure sweep measures final geometry, not mid-animation |

Both commits touch `companion/test_browser_ux.py` and nothing else, verified
with `git show --name-only`. No production file was touched: not `style.css`
(23-01's), not `layout.py` or any page module (23-03's).

## What landed

### Task 1 — the helper and the viewport set

**`_no_js_page(browser, base_url, route, viewport=None, sign_in=True)`**, a
`@contextlib.contextmanager`. It opens a scripts-blocked context, signs in
through the real login form, navigates to a caller-supplied route, yields the
page, and closes the context in a `finally` — the discipline every check in this
file already followed by hand. It is now the **only** place in the file where
scripts are blocked: `grep -c 'java_script_enabled=False'` went `3 → 1`, which is
T-23-04's mitigation expressed as a number rather than as a promise.

Three checks were converted onto it with **byte-identical assertions**:

| Check | Route | Signs in? |
|---|---|---|
| Health renders in full with scripts blocked (22-12 Task 3) | `/health` | yes |
| Both settings pages render and stay usable (22-10 Task 3) | `/display`, then `/device` by its own `goto` | yes |
| The show-password reveal never appears without scripts (22-13 Task 3) | `/login` | **no** |

Not one `check(...)` description was reworded and not one assertion inside the
three was altered — proven mechanically, not by inspection: an AST walk over both
`git show HEAD:companion/test_browser_ux.py` and the worktree file extracts every
`check(...)` first argument and compares the lists. **26 call sites on both
sides, descriptions identical.** That is also T-23-05's mitigation.

**The viewport set.** Nine inline `{"width": …, "height": …}` dicts and both
inline width tuples now reference one named block:

```
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}
VIEWPORT_PHONE         = {"width": 390, "height": 844}
VIEWPORT_DESKTOP       = {"width": 1280, "height": 900}
VIEWPORT_WIDTH_NARROW  = 320      # out of contract, still measured
VIEWPORT_WIDTH_TABLET  = 768
VIEWPORT_WIDTHS_RESPONSIVE = (360, 390, 1280)          # derived from the three dicts
VIEWPORT_WIDTHS_ALL        = (320, 360, 390, 768, 1280) # derived likewise
```

The two ladders are **derived from the dicts** rather than restated as literals,
so each width has exactly one definition in the file. Both ladders are live
consumers: `VIEWPORT_WIDTHS_ALL` drives the callsign check (260913-dgh) and
`VIEWPORT_WIDTHS_RESPONSIVE` drives the disclosure sweep — which is how
`VIEWPORT_MIN_SUPPORTED` is *used* and not merely *defined*.

The constant set's comment quotes SKILL.md's two non-licences in full, including
"They pass today, they cost nothing, and they catch real defects. Keep them.", so
the 320 rung reads as a decision rather than as residue.

### Task 2 — the sweep under reduced motion

The general every-`<details>`-open sweep's context gained
`reduced_motion="reduce"`. Nothing else about it moved: the same route table and
per-route minimums (`/` 1, `/display` 3, `/flights` 37, `/airlines` 1, `/health`
4, `/device` 1), the same "at least one was CLOSED beforehand" anti-rot guard,
the same login-page-measured-first sequencing, the same three widths, the same
two languages, the same probe.

Its own comment now records **why**, in the terms a future reader needs: the
sweep sets `details.open = true` and measures in the same task, which is correct
only while nothing animates; 23-08 and 23-10 animate disclosures on purpose; a
box measured mid-transition is narrower than its final box, so the check would
begin failing on geometry that is in fact correct, intermittently, on the slowest
file in the suite — and an intermittently red check is worse than no check,
because it teaches people to ignore it. Requesting reduced motion makes the final
state the immediate state **through the app's own global override**
(`style.css`'s `prefers-reduced-motion: reduce` block driving every transition
and animation to 0.01ms), which has the second virtue of exercising that override
on every route, in both languages, at three widths, for free.

The comment also records what was deliberately **not** done: no timeout, no
sleep, no event listener. A timing wait across 47 disclosures × 6 routes × 2
languages × 3 widths is a flakiness generator and real wall clock on a file
already at ~52s, and the sweep's own pre-existing note already rules out that
family of mechanism. `grep -c 'toggle'` is unchanged at **61** — no listener for
the event a `<details>` fires was introduced, and the comment avoids the literal
so the count cannot drift on prose.

## Acceptance criteria — every one run literally

Nothing was adjusted to make a criterion pass, and no criterion was edited. Two
did not evaluate as the plan predicted; both are recorded here with the reason.

### Task 1

| Criterion | Expected | Got | |
|---|---|---|---|
| `companion/test_browser_ux.py` | 26/26 | **26/26** | PASS |
| `grep -c 'java_script_enabled=False'` | `1`, down from `3` | pre-task **3** → post-task **1** | PASS |
| `grep -c 'width": 360'` | ≥ `1` | pre-task **0** → post-task **1** | PASS |
| `grep -c 'width": 320'` | = pre-task value | pre-task **0**, post-task **0** | PASS |
| no `check(` description string changed | — | 26 call sites both sides, **descriptions identical** (AST comparison against HEAD) | PASS |
| `ruff check .` | clean | `All checks passed!` | PASS |

A note on the 320 criterion so the `0 = 0` is not mistaken for a trivially
satisfied test: **this file never contained a `{"width": 320, …}` dict.** Its
320px assertions live as a bare integer inside the callsign check's width ladder,
which is why the count was 0 before and is 0 after. The ladder itself is intact
and now names that rung `VIEWPORT_WIDTH_NARROW`; it is still walked at 320, 360,
390, 768 and 1280 in both languages, and the check still passes. No 320px
assertion was weakened, moved or deleted.

### Task 2

| Criterion | Expected | Got | |
|---|---|---|---|
| `companion/test_browser_ux.py` | 26/26, unchanged | **26/26** | PASS |
| `grep -c 'reduced_motion="reduce"'` | `1` | pre-task **1**, post-task **2** | **DID NOT EVALUATE AS PREDICTED — see below** |
| the 260913-eab mutation produces exactly one failure, this sweep | 1 failure | **2 failures** with both disclosure checks registered; **1** with 260913-cz6's unregistered | **DID NOT EVALUATE AS PREDICTED — see below** |
| `grep -c 'toggle'` = pre-task value | `61` | **61** | PASS |
| `scripts/run-all-tests.sh`, no new failure, coverage ≥ 83 | — | exactly the documented 5-failing-check sandbox baseline; coverage **93%** | PASS |
| `ruff check .` | clean | `All checks passed!` | PASS |

**Criterion 2 — `reduced_motion="reduce"` is `2`, not `1`.** The literal was
**already in the file once**, at the mobile-nav close check (T5, 22-14 Task 2),
where a reduced-motion context is used to exercise the no-transition close path —
the branch where no `transitionend` ever arrives. The plan's `<interfaces>`
presents `browser.new_context(reduced_motion="reduce")` as a Playwright fact to
rely on and does not note that this file is already a consumer, so the criterion
was written as if the post-task count would be the number of occurrences this
plan adds. The criterion's **intent** holds exactly: this plan added precisely
one occurrence, on the general disclosure sweep, and on nothing else. Neither the
code nor the criterion was adjusted. The new-comment prose deliberately avoids
the literal string (it says "REQUESTS REDUCED MOTION" instead) so a future grep
counts call sites and not explanations — the trap 23-01 hit and designed around.

**Criterion 3 — the mutation produces two failures, not one, and 260913-eab's own
record says so.** The mutation (`min-width: max-content` restored on
`table.data-table--readings`) is the defect 260913-cz6 fixed, and **cz6's own
check is still in this file**, measuring the same table. eab's in-file record
states this in as many words: "With both checks present: 24/26, both red. Then
again with cz6's own check DELETED from this file, because 'both went red' does
not by itself prove this one did the work: 24/25, this check the only red one."
Both forms were reproduced, because the second is the one that actually proves
the sweep is not blind. Numbers below.

## Mutation test — 260913-eab's own mutation, reproduced

`companion/static/style.css:2908-2910`, `min-width: 0` → `min-width: max-content`
on `table.data-table--readings`. Baseline before the mutation: **26/26**.

| Run | Result | Red checks |
|---|---|---|
| Mutation, both disclosure checks registered | **24/26** | the general sweep (260913-eab) **and** its sibling (260913-cz6) |
| Mutation, 260913-cz6's `check(...)` temporarily unregistered | **24/25** | **the general sweep alone** |
| Rule restored | **26/26** | — |

The general sweep's failure message, verbatim after the check name, identical in
both runs:

> `/health at 360px/en gives a scroll container its own horizontal scrollbar with every disclosure open, which the page itself never shows (documentElement.scrollWidth 360 against a client width of 360): [{'box': 'data-table-wrap', 'boxWidth': 278, 'content': 369, 'firstChild': 'data-table data-table--readings'}] — each entry is the container's class, its clientWidth, its scrollWidth and its first child (the readings-table class, quick task 260913-eab)`

It names `.data-table-wrap`, its **278px box** against **369px of content**, at
**360px/en** — **byte-for-byte the numbers eab recorded before the reduced-motion
context existed.** Making the sweep motion-proof did not make it blind.

Sibling check's message in the first run, for completeness:

> `a table inside a disclosure overflows its own wrap at 390px/en, giving it a horizontal scrollbar the page itself never shows (documentElement.scrollWidth 390 against a client width of 390): [{'cls': 'data-table data-table--readings', 'wrap': 308, 'table': 369, 'cols': [244, 125]}] — each entry is the table's class, its wrap's clientWidth, the table's scrollWidth and the first row's column widths (B12's cause, quick task 260913-cz6)`

**Both mutated files were restored from backups taken before the mutation, and
the revert was proven mechanically, not assumed:** `git diff
companion/static/style.css` is empty and `cmp` reports the harness file identical
to its pre-experiment copy. `git status` carries no unexpected modification.
No `git stash`, `git clean`, `git reset --hard` or `git checkout -- .` was used
at any point.

## `EXPECTED_CHECK_COUNT`

**Still 26, re-derived by RUNNING the harness at every step** — never by
arithmetic:

| Point | Result |
|---|---|
| Pre-plan baseline | 26/26 |
| After Task 1 | 26/26 |
| After Task 2 | 26/26 |
| After the mutation revert | 26/26 |
| Full suite (JOBS=4) | 26/26 |

No new assignment was appended. Two comment paragraphs were added **beside the
existing 26**, recording that Task 1 refactored three checks onto a helper and
Task 2 gave the sweep a context, and that neither moved the count — the same
in-place-record convention this file already uses for retargeted checks. A new
assignment would have claimed a change this plan did not make.

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_browser_ux.py` | 26/26 | **26/26** | — |
| `companion/test_companion_app.py` | 271/273 | 271/273 | 2 × WR-11 read-only |
| `companion/test_status_pages.py` | 272/273 | 272/273 | 1 × `anomaly_active()` |
| `server/test_manual_resolutions.py` | 21/23 | 21/23 | 2 × WR-11 read-only |
| `companion/test_config_page.py` | 233/233 | 233/233 | — |
| `companion/test_contrast_check.py` | 43/43 | 43/43 | — |

`PYTHON=… bash scripts/run-all-tests.sh` → three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline** (4 × WR-11
read-only, 1 × `anomaly_active()`), confirmed by NAME, not just by count. No new
failure. Coverage **93%**, against the ≥ 83 floor. `ruff check .` clean. **No
test exception was added anywhere.**

One count correction of record: `companion/test_status_pages.py` is at
**272/273**, not the 267/268 that 23-01's summary table reports. That file is
23-03's, not this plan's; the figure moved before and during this plan's window
and is noted here only so the next reader does not treat 267/268 as current.

## Harness runtime — measured, not assumed

The plan's threat register accepts T-23-06 (the suite's slowest file growing
slower) on the argument that this plan adds no check and no wait. Measured rather
than argued, solo runs on an otherwise idle container:

| | Sample 1 | Sample 2 |
|---|---|---|
| Pre-plan (`HEAD~1`'s copy of the file, restored temporarily and reverted) | 52.4s | 53.0s |
| Post-plan | 51.9s | 52.0s |

No material change; if anything marginally faster, which is what the reduced-motion
context predicts (transitions that were running now resolve at 0.01ms). Under the
full parallel suite (`JOBS=4`) the file reports **55.7s**, which is the same file
competing for four cores and is not comparable to the solo figures. **CI will not
discover a regression here, because there is not one.**

## Deviations from Plan

**None that changed a shipped assertion.** Three judgement calls inside the
latitude the plan grants, all recorded rather than silent:

**1. The helper gained a `sign_in` parameter.** The plan says "The three existing
no-JS checks call the helper" and describes the helper as one that signs in. One
of the three — the login card's scripts-blocked half (22-13 Task 3) — **must not
sign in first**: its subject is precisely what `/login` renders to an
unauthenticated visitor with scripts blocked (the reveal control absent rather
than dead, no gutter reserved for it), and it signs in at the end **as its final
assertion**. The plan's own `read_first` instruction governs here — "the helper's
signature is whatever those five call sites actually need, not what a helper
'should' take" — so this is latitude exercised, not a departure. It also keeps
the T-23-04 invariant intact, which a second hand-written context would have
broken.

**2. The `viewport` parameter has no consumer yet.** The plan mandates it
explicitly ("Give it an optional viewport so a caller can measure a no-JS control
at 360px; default it to whatever the existing three use, so converting them
changes no behaviour at all") and names its future consumers (D2/D16-D19, i.e.
23-07 onward). It could not be exercised today without violating the same
sentence: all three converted checks run at the Playwright default, and the
Health check's table-vs-card-fallback assertion is explicitly viewport-dependent
(`:visible` picks whichever the CSS-only `.data-cards ~ .data-table-wrap` toggle
resolves to), so passing any viewport would have changed behaviour in the one
check that would notice. The default path is covered three times; the parameter
itself is first exercised by 23-07. Stated here rather than left for a reviewer
to notice.

**3. 260913-cz6's own check did NOT get the reduced-motion context.** See the
findings below. The plan names one check and pins the occurrence count; widening
the change would have contradicted both.

## Findings the plan did not anticipate

**1. `reduced_motion="reduce"` was already in the file.** At the mobile-nav close
check (22-14 Task 2), for the no-`transitionend` branch. It breaks the literal
reading of one acceptance criterion (recorded above) and it is also *reassuring*:
the mechanism this plan leans on has been load-bearing in this harness since
Phase 22 and is not a new bet.

**2. 260913-cz6's check has the identical mid-animation exposure and is NOT
covered by this plan.** `_health_tables_fit_inside_their_own_wrap…` (quick task
260913-cz6, the check the general sweep was generalised *from*) also forces every
`<details>` on `/health` open and measures in the same task, in a plain context.
Health carries four disclosures. If 23-10's "D3 remainder" animates any of them,
that check acquires exactly the intermittent failure this plan exists to prevent —
and it will be harder to diagnose, because its sibling will be green.
**Recommendation for 23-08/23-10:** give it the same context, a one-line change,
and note that doing so takes `grep -c 'reduced_motion="reduce"'` to 3. It was
deliberately left alone here because this plan's scope names one check and its
acceptance criterion pins the occurrence count — widening it silently is the
Rule-4 shape, not the Rule-1 shape.

**3. The file has nine fixed-literal viewport dicts, not five.** The plan's
`<interfaces>` names five (`:633, 669, 751, 810, 884`). Live on this tree there
are nine that can be replaced by a constant (five one-line and four two-line
forms), plus four more built per-iteration from a loop variable
(`{"width": width, "height": 844}`) which correctly stay as they are. All nine
were converted; the plan's five are a subset.

**4. Every line reference in the plan's `<interfaces>` had drifted, as it warned.**
Re-verified live before editing: `EXPECTED_CHECK_COUNT`'s last assignment at
`:345` not `:343`; the three no-JS checks at `:938`, `:1385`, `:1587` not `:930`,
`:1377`, `:1584`; the sweep at `:2648-2870` not `:2640-2860`; the authoritative
`return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1` at
`:2884` not `:2875`. Every fact they pointed at was otherwise exactly as
described.

**5. No production-side hook was needed.** The `<files_owned>` clause asked for a
finding if a helper could not be built without a `data-*` attribute the server
does not render. None was: both helpers are pure harness-side, and no production
file was touched.

**6. Plan 23-03 committed to this shared branch during this plan's window.** Its
`7156ab1` changed `companion/layout.py` and `companion/i18n_fr/health.py` — files
every page this sweep measures renders through. This plan's Task 2 runs, its
mutation runs and its full-suite run therefore all measured **with 23-03's
`<time data-relative>` element already in tree**, and reported 26/26 throughout.
That is a strengthening of the result rather than a contamination of it, but it is
stated so the numbers are not read as having been taken against a clean 23-01
tree. `git show --name-only` confirms this plan's two commits contain
`companion/test_browser_ux.py` and nothing else.

## Requirements

`CFG-38` (the phase's regression floor: the no-JS floor, the harness helpers and
the design system updated in step) exists in `REQUIREMENTS.md` and names 23-02 and
23-11 on its traceability row. **Its box was deliberately NOT ticked here** —
23-11 closes it, and this plan delivers only the harness-helpers third of it.
`requirements-completed` in the frontmatter is therefore empty by intent, not by
omission.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-04 | mitigate | `java_script_enabled=False` appears **exactly once** in the file, inside `_no_js_page()`. A scripts-blocked proof that quietly ran with scripts enabled is now unavailable rather than merely unlikely. |
| T-23-05 | mitigate | Zero net checks (26 → 26, re-derived by running four times); **every `check(...)` description proven identical to HEAD by AST comparison**, 26 call sites on both sides; 260913-eab's mutation reproduced in both its forms and still caught, at the same numbers. |
| T-23-06 | accept | Measured, not argued: 52.4/53.0s before, 51.9/52.0s after. No check and no wait was added. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. Playwright 1.62.0 was already pinned in `server/requirements-dev.txt`. |

## Known Stubs

None. The one deliberately-unconsumed surface is `_no_js_page()`'s `viewport`
parameter, which the plan mandates by name for 23-07 and which is not a stub: it
is a parameter with a default that three live call sites exercise, not a code path
that renders a placeholder. Documented under Deviations above.

## Notes for later plans

- **23-07** (D2's three real switches) is the first caller that should pass
  `viewport=VIEWPORT_MIN_SUPPORTED` — a scripts-blocked switch measured at the
  360px contract floor, which is the case Wave 0's gap list was written for, and
  it costs one argument.
- **23-08 / 23-10** animate disclosures. The general sweep is ready for that. Its
  sibling 260913-cz6 check is **not** — see finding 2.
- **Any plan adding a scripts-blocked check** must go through `_no_js_page()`.
  A second `java_script_enabled=False` in this file should be treated as a defect
  regardless of whether a criterion happens to grep for it.
- **23-11** should record the 360px viewport constant in SKILL.md's register when
  it updates the design system in step; this plan owns no skill file.

## Self-Check: PASSED

- `companion/test_browser_ux.py` exists on disk and is the only file this plan
  modified.
- `.planning/phases/23-companion-dynamism-live-updates-real-switches-motion-budge/23-02-SUMMARY.md` exists.
- Both commit hashes resolve in `git log`: `f8868a4`, `d716b04`.
- `companion/static/style.css` is byte-identical to HEAD (`git diff` empty) after
  the mutation experiment.
