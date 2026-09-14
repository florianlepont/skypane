---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 08
subsystem: ui
tags: [home, composition, svg, layout, cascade, refresh-registry, i18n, no-js]

requires:
  - phase: 24-04
    provides: "draw.ring_gauge() — the ONE ring emitter — and home_page.BATTERY_RING_SIZE, the 36px box chosen from the 360px floor"
  - phase: 24-06
    provides: "draw.day_band(), home_page._day_band_html(), and the MEASURED 278px band canvas that draw.DAY_BAND_MIN_MARK_SPACING_PERCENT was re-derived from"
  - phase: 24-02
    provides: "companion/test_browser_ux.py's _set_ui_theme(), _computed_paint(), _assert_no_page_overflow() and _no_js_page()"
  - phase: 21-04
    provides: "the deleted phase-20 hero row and status-card builder, and the frame-verdict-exactly-once property this plan had to keep"
provides:
  - "home_page._hero_html() / HERO_CLASS — Home's top as ONE composition, assembled from calls"
  - "home_page._current_picture_html() — the picture builder renamed out of the word 'hero'"
  - ".home-overview — a grouping container that owns the rhythm between the strip, the tiles and the band"
  - "a behavioural 'fed by' proof: a draw.py class constant replaced at check time moves the hero AND the page the emitter was borrowed from"
  - "Home's refresh-swap registry asserted through the browser's own selector engine"
affects: [24-09]

tech-stack:
  added: []
  patterns:
    - "A composition expressed as proximity and asserted as two numbers: --space-md inside the group, --space-lg below it, both as EQUALITIES"
    - "A behavioural link test: monkeypatch the shared emitter's own class constant at check time and require both consumers to move"
    - "Anti-restatement scanning over string LITERALS with docstrings excluded — prose is not evidence, and draw.DRAWING_GRID_CLASS is the single word 'drawing'"
    - "A refresh-registry assertion run through document.querySelectorAll rather than a witness literal, because a witness is a second transcription of the selector"

key-files:
  created: []
  modified:
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/test_view_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "The hero is a grouping container with NO surface of its own — two of its three parts are already cards, and taking the band's card away to make room for one would widen its canvas past the 278px draw.py's spacing constant was derived from"
  - "One column at every width: any column split puts the band in a 288px column (canvas 256px), narrower than it is at the 360px floor. The floor-vs-not-floor property is carried by the PARTS instead"
  - "The class is .home-overview, not .home-hero — two standing checks assert the phase-20 string never returns to this page"
  - "No new user-visible string: the hero is a composition, not copy, so companion/i18n_fr/home.py is unchanged"

patterns-established:
  - "Mutate every CSS declaration you add: all four mutated RED, and one of them was already BROKEN when it did"
  - "A same-second revert can poison __pycache__: Python validates a .pyc by source mtime at one-second granularity, so a fast git checkout-index can leave a mutated module live"

requirements-completed: []

duration: one session
completed: 2026-09-14
---

# Phase 24 Plan 08: D4's Home Hero Summary

Home's top is now one composition — the shared Frame strip, the three status
tiles carrying 24-04's ring, and 24-06's day band — assembled from calls into
the shared emitters, with "fed by" turned from a claim a reviewer has to trust
into a property a check can lose: replace a class constant inside
`companion/draw.py` and both the hero and the page the emitter was borrowed
from change.

## Performance

- **Tasks:** 3 of 3
- **Commits:** 8
- **Files modified:** 4 (of the 5 the plan listed; see "Plan assumptions")
- **Harness runs:** 15 (9 of them full browser runs at ~3 min each), plus one
  direct Chromium measurement pass

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `2650bc5` | `test(24-08): a failing check for the hero the drawings feed` |
| 2 | `e506e47` | `feat(24-08): Home's top is one composition, assembled from calls` |
| 3 | `d44110d` | `test(24-08): say what the estimator guard actually catches` |
| 4 | `33019cf` | `test(24-08): "fed by" is now a property a check can lose` |
| 5 | `f2b31af` | `test(24-08): the hero measured — stacked, both themes, no script` |
| 6 | `5e69251` | `fix(24-08): the hero's own rhythm loses to the strip on source order` |
| 7 | `164ad6d` | `docs(24-08): the numbers behind "one column at every width"` |
| 8 | `413904b` | `docs(24-08): the hero is 880px at 1280, not the 928 inferred from a mutation` |

## The decision that mattered most

**The hero composes VERTICALLY and gives itself no surface — and both halves of
that were decided by the band's 278px, not by taste.**

The obvious reading of "one composition" is a card holding the three parts, and
the obvious reading of "the stack is a floor behaviour rather than the only
behaviour" (the plan's own words) is a hero that splits into columns on the
desktop. Both were rejected on measurements:

- **A surface.** Two of the three parts are already cards (`.frame-strip` is an
  accent `.stat-tile`, `.day-band` is a `.page-section`) and the third is a grid
  of three more, so a background and a border on the container is a card holding
  cards. The way out — take `.day-band`'s own card away so the hero can carry
  one — **widens the band's canvas**, and `draw.DAY_BAND_MIN_MARK_SPACING_PERCENT`
  was re-derived by 24-06 from that canvas measuring exactly 278px. Changing it
  silently invalidates the constant that keeps two check-in marks readable as two.
- **Columns.** Mutation MC8 put `grid-template-columns: 2fr 1fr` on the container
  and the browser answered with the number the decision needed. Measured directly:
  the hero is **880.00px at a 1280px viewport**, so a one-third column (880 less
  the rule's own 16px gap, divided by three) is **288px** — against the **310px** a
  band *card* needs to keep its canvas at 278 (278 plus `.page-section`'s own
  2 × `--space-md` of padding), which would leave the canvas at **256px**. A
  desktop hero with columns would render the band **narrower than it is at the
  360px floor**. That is the "fits by shrinking its parts" failure the requirement
  exists to refuse, arriving through the desktop rather than the phone.

  **The first draft of that arithmetic was wrong, and the way it was wrong is
  worth recording.** 928 was read off MC8's own failure message — `hero child 1
  starts at 928.00 against the first child's 336.00` — which is that child's LEFT
  EDGE, not the container's width. A mutation's message is evidence about the
  clause that fired, not a measurement of anything else in the sentence. Measured
  directly afterwards (`.home-overview` at 1280px: left 336, width 880), the
  conclusion is unchanged and stronger: 288px, not 304.

So the composition is **proximity**, and it is asserted as two numbers rather
than left to the eye: the parts sit one `--space-md` (16px) apart inside the
container and the container sits one `--space-lg` (24px) above the picture row —
bound tighter than they are separated. The floor-vs-not-floor property is carried
by the **parts**: the three tiles each take their own row at 360px and share one
row at 1280px, and that is what the check asserts.

## The defect the CSS-mutation discipline found before anyone looked at the page

`.home-overview > *` is **(0,1,0)** — the universal selector contributes nothing —
which **ties** `.frame-strip`'s own (0,1,0) `margin-bottom: var(--space-lg)` and
leaves the outcome to source order. `.frame-strip` is declared ~360 lines further
down `style.css`, so it won.

Measured in Chromium on the first browser run:

> `in en at 360px: the hero's parts 0 and 1 sit 40.00px apart, not the 16px one --space-md declares. 40px is what three parts that kept their own bottom margins render, and it reads as three stacked blocks rather than one composition`

40 = 24 + 16, exactly what the check's own message had predicted in the abstract.
`.home-section` and `.page-section` are both declared *above* the new rule and
lost, so the tiles-to-band gap was already the intended 16 — **two thirds of the
composition were correct and one third was not**, which is precisely the shape a
ceiling ("at most 40px") or an eyeball would have passed. Fixed with the doubled
selector `.home-overview.home-overview > *` (0,2,0), the same cascade hazard and
the same fix `.page-section.banner--anomaly` and the `.battery-trend-section`
status borders already document in this file. The universal child is kept rather
than a hand-list of the three parts, so a fourth part added later surrenders its
margin too.

## The infrastructure hazard this plan hit, and every later mutation run depends on

**A same-second revert poisons `__pycache__`, and the resulting failure looks
exactly like a defect in your own work.**

After the manual `companion/draw.py` mutation (below), `git checkout-index -f --`
restored the source and `git status` was clean — but the next full browser run
reported **two failures in 24-04's ring checks** on Home. The mutated class string
was still being served:

```
<circle class="MUTATED-ring-value" cx="18.00" cy="18.00" r="15.12" ...>
```

`companion/__pycache__/draw.cpython-311.pyc` still contained `MUTATED`, and
`companion/draw.py`'s restored mtime was **1789366876 — the same second** the
`.pyc` had recorded. CPython validates a cached bytecode file by comparing the
source mtime for *equality* at one-second granularity, so the stale cache was
considered valid and the corrected source was never recompiled. The mutation and
its revert had both happened inside one second because the renders between them
took milliseconds.

Verified against a pristine tree (`git archive 5d82c34` into a temp directory,
run with the same interpreter): **63/63, clean** — so the failures were the cache,
not the hero. Clearing every `__pycache__` outside `.venv` restored 63/63 on this
tree. **Any executor doing sub-second mutate/revert cycles in this repository
should clear `__pycache__` after reverting**, or the next harness run will
measure a module that no longer exists on disk.

## Mutations, with their quoted failure messages

### Task 1 — the composition (`companion/test_view_pages.py`, one check)

| # | Mutation | Result |
|---|----------|--------|
| M1 | the day band moved back OUTSIDE the hero | RED |
| M2 | the picture row swallowed INTO the hero | RED |
| M3 | the hero slicer made naive (first `</div>` wins) | RED |
| M4 | a forked ring inlined into `home_page.py` | RED (×2 checks) |
| M5 | a second estimator copied into `home_page.py` | RED (×2 checks) |
| M6 | the estimator imported bare and called unqualified | RED (×2 checks) |
| M7 | the frame verdict duplicated in **French only** | RED — see vacuity below |

**M1** — `expected the day band inside the hero — a composition that does not contain its parts is a wrapper, not a hero (looked for '<section class="[^"]*\bday-band\b')`

**M2** — `expected 'home-picture-row' outside the hero — the hero is Home's TOP, not its whole body`

**M3** — `expected the three status tiles inside the hero — a composition that does not contain its parts is a wrapper, not a hero (looked for 'class="dashboard-grid home-status-grid"')`
(This is the proof that the **balanced `<div>` scan is load-bearing**: the hero's
first descendant `</div>` belongs to the Frame strip, so a naive slicer returns a
fragment that stops before the tiles. The shipped check passes only because the
scan is balanced.)

**M4** — `expected exactly one battery ring value arc on Home, got 2`
(24-04's own ring check fired too: `expected exactly one ring on Home (one track, one value arc), got 1 track(s) and 2 value arc(s)`.)

**M5** — `companion/pages/home_page.py contains '4200' — geometry and battery arithmetic belong to the shared modules, and a page that carries either has started a second copy`
(The pre-existing D-01 guard fired as well: `expected home_page.battery_percent to be gone after the D-01 move`.)

**M6** — `companion/pages/home_page.py names battery_percent( with no module qualifier — either a local definition or a bare 'from companion.battery import' — and both make the estimator read as this page's own. It has exactly two allowed homes and this module is not one of them, so every call site here says so`

### Task 2 — "fed by" (`companion/test_view_pages.py`, two checks)

**Task 2 adds only measurement, so it has no RED phase.** Said plainly rather
than manufactured: the two checks passed against the implementation the moment
they were written, and the evidence that they are worth their runtime is below.

| # | Mutation | Result |
|---|----------|--------|
| M8 | **a simulated fork** — the ring's markup inlined into `home_page.py` with the real class strings | RED (both Task-2 checks + 24-04's) |
| M9 | the check itself writes a class literal down | RED |
| M10 | the "targeted mutation" clause aimed at `DRAWING_CANVAS_CLASS` | **did not fire** — see below |
| M10b | the same clause aimed at `DRAWING_RING_TRACK_CLASS` | RED |
| M11 | the band's shaded span dropped (`_quiet_hours_window` forced to `None`) | RED (+ 24-06's own check) |

**M8 (the plan's required fork proof)** —
structural check: `companion/pages/home_page.py writes the drawing class 'drawing__figure' into a string literal — the page calls the emitters, it does not restate their markup`
behavioural check: `a change inside the shared ring emitter did not reach the hero — it draws its own ring, not the shared one`
(24-04's proportions check also fired: `Home's ring draws 1.0000 of its circumference while the tile prints '≈ 43%' beside it`.)

**M9** — `this check writes the drawing class 'drawing-ring-value' into a literal instead of reading it from companion/draw.py — rename the constant and a literal here goes on passing against the fork`

**M10b** — `changing the band emitter also changed Health, which draws no band — the mutation is not measuring what it names`

**M11** — `the hero's band draws only 2 kind(s) of shape (['drawing-band', 'drawing-band-mark']) — with a quiet-hours window configured and two check-ins on the day it owes three: its own frame, the shaded span and the marks`

### The manual mutation the plan asked for, run by hand on this tree

One edit in `companion/draw.py`:
`DRAWING_RING_VALUE_CLASS = "drawing-ring-value"` → `"MUTATED-ring-value"`.
Both pages rendered before and after, then reverted:

| | before | after |
|---|--------|-------|
| Home's hero (36px box) | `<circle class="drawing-ring-value" cx="18.00" cy="18.00" r="15.12" ... stroke-width="4.32"` | `<circle class="MUTATED-ring-value" cx="18.00" cy="18.00" r="15.12" ... stroke-width="4.32"` |
| Health (72px box) | `<circle class="drawing-ring-value" cx="36.00" cy="36.00" r="30.24" ... stroke-width="8.64"` | `<circle class="MUTATED-ring-value" cx="36.00" cy="36.00" r="30.24" ... stroke-width="8.64"` |

**One edit, two pages, two different sizes** — which is CFG-44's claim in one
observation. Reverted with `git checkout-index -f --`; see the `__pycache__`
hazard above for what that revert cost to notice.

### Task 3 — the hero in a browser (`companion/test_browser_ux.py`, two checks)

Every declaration the new CSS adds was mutated. **None was inert**, and one was
already broken when it was mutated.

| # | Mutation | Result |
|---|----------|--------|
| MC1 | `display: grid` → `display: block` (is the gap doing anything?) | RED |
| MC2 | `gap: var(--space-md)` removed | RED |
| MC3 | the container's own `margin-bottom: var(--space-lg)` removed | RED |
| MC4 | the doubled selector reverted to `.home-overview > *` | **RED — and this was the real shipped defect, found before the fix existed** |
| MC5 | the hero shrinks its parts (`transform: scale(0.5)` on the ring) | RED |
| MC6 | the hero narrows the band (`padding-inline: var(--space-lg)`) | RED (+ 24-06's spacing floor) |
| MC7 | a stale Home refresh-swap selector in the registry | RED |
| MC8 | the hero split into two columns on the desktop | RED |

**MC1 / MC2** — `in en at 360px: the hero's parts 0 and 1 sit 0.00px apart, not the 16px one --space-md declares. 40px is what three parts that kept their own bottom margins render, and it reads as three stacked blocks rather than one composition`

**MC3** — `in en at 360px: the hero sits 0.00px above the picture row, not the 24px one --space-lg declares — the group has to be separated from what follows it by MORE than its parts are separated from each other, or the grouping says nothing`

**MC4** — `in en at 360px: the hero's parts 0 and 1 sit 40.00px apart, not the 16px one --space-md declares.` (the defect, quoted in full above)

**MC5** — `in en the hero's ring renders 18.00px wide, not the 36px home_page.BATTERY_RING_SIZE declares — a hero that fits by shrinking its parts has passed an overflow check and failed CFG-44`

**MC6** — `in en the hero's band canvas measures 262.00px, not the 278.00px 24-06 measured and derived draw.py's 1.50% minimum mark spacing from — narrowing the band inside the hero silently invalidates that derivation`
and, from **24-06's own floor**, in the same run:
`in en the canvas measures 262.00px, so draw.py's 1.50% minimum spacing is 3.93px centre to centre — under the 4px two 2px marks need to keep a clear pixel between them. The constant's derivation and this layout have drifted apart`
**16px of padding is all it takes to break the derivation.** This is the
measurement behind the "no surface of its own" decision, arriving from the
opposite direction.

**MC7** — `at 360px these declared Home refresh regions match nothing in the rendered page: ['.home-hero .frame-strip'] — a stale swap selector stops the live refresh and says nothing`

**MC8** — `at 1280px: hero child 1 starts at 928.00 against the first child's 336.00 — the hero is not one column`

## A check that failed the vacuity question, and what was done

**"The frame verdict appears exactly once" was already asserted twice on this page
— in English.** The new clause asks it in both languages, and M7 is the proof that
the French half is not redundant coverage: the hero was made to print the verdict
a second time **only when the catalogue translates it**, so English was
byte-identical.

Result: **161/162 — exactly one check failed**, mine, on the French half:

> `in fr expected exactly one frame verdict on Home, got ['Se connecte normalement', 'N’a pas répondu depuis un moment']`

Every English verdict check in the repository (21-04's, 24-04's, 24-06's) stayed
green through a duplicated verdict. The French half is load-bearing.

A second vacuity question was asked of the anti-restatement scan and it changed
the design: the first draft was a bare substring scan, and it failed immediately
because `draw.DRAWING_GRID_CLASS` is the single word **"drawing"**, which appears
in `home_page.py`'s own prose ("a drawing that implied calibration would
out-claim the number it sits beside") and in the check's own failure messages.
The shipped scan reads **string literals only, docstrings excluded**, and asks two
precise questions of each — is it a class name outright, or does it write one into
a `class="..."` attribute. Prose is not evidence.

## Criteria that did not evaluate as predicted

**M10 — "aim the targeted-mutation clause at a constant both pages use and it
should fire."** It did not: 164/164, green. Measured reason — under this check's
minimal Health fixture (two `device_health` rows), Health renders the **ring**
(`drawing__figure`, the unit-canvas scheme) and **no percentage canvas at all**,
so `DRAWING_CANVAS_CLASS` is not on that page and patching it leaves Health
byte-identical for a reason that has nothing to do with targeting. **M10b** aimed
the same clause at `DRAWING_RING_TRACK_CLASS`, which both pages genuinely draw,
and it fired. Recorded rather than quietly adjusted: the clause is live, and the
constant M10 chose was the wrong probe, not the clause.

**Two of the check's own bugs were caught by its own messages** on the first
browser run and are worth recording because both are "a true number about the
wrong element":

- `in en the hero's ring renders 30.24px wide, not the 36px ...` — the probe was
  measuring `.drawing-ring-value`, the value **arc**, whose bounding rectangle is
  its diameter (2 × r = 30.24). The ring's **box** is the `<svg>` the emitter
  sized. Fixed, with the reason written where the selector stands.
- `expected three status tiles inside the hero at both widths, got 4 and 4` — the
  Frame strip also carries `.stat-tile`. Scoped to `.home-status-grid .stat-tile`,
  matching this file's own `_TILE_CONTENT_PROBE`.

## Plan assumptions that turned out wrong

1. **"The stack is a floor behaviour rather than the only behaviour"** reads as a
   hero that becomes multi-column on the desktop. Measured, it cannot be: 880px of
   hero at 1280px gives a one-third column of 288px against the 310px a band card
   needs to keep its canvas at 278. The hero is **one column at every width**; the
   floor-vs-not-floor property is asserted of its **parts** (three tiles, three
   rows at 360px, one row at 1280px) instead.
2. **`.home-hero` is not available as a class name.** The plan anticipated a
   naming collision and a rename; it did not anticipate that the obvious name is
   *forbidden* — `companion/test_view_pages.py:6816` and
   `companion/test_companion_app.py:6500` both assert the phase-20 string never
   returns to this page. The container is `.home-overview` and the loser of the
   collision (`_hero_figure_html`) became `_current_picture_html`, so exactly one
   identifier on this page means "hero".
3. **No new strings.** The plan's Task 1 behaviour list ends "New strings exist in
   both languages"; the hero introduces none, because it is a composition rather
   than copy. `companion/i18n_fr/home.py` is listed in `files_modified` and is
   **unchanged**. The container is a `<div>` with no role and no accessible name
   on purpose: the three parts keep their own `<h2>`s, so a screen reader reads
   this page exactly as it did before, and a landmark with no name would be a
   second, weaker claim about the same grouping.
4. **Task 1's `<files>` list omits `companion/test_view_pages.py`** although the
   task is `tdd="true"` and its RED check has nowhere else to live. The check was
   written there (the file is in the plan-level `files_modified`), and commit 1 is
   the RED commit.
5. **The refresh-registry criterion is satisfied in Task 3, not Task 1.** The
   Flights idiom (23-08) maps each selector to a witness literal; that is a
   *second transcription* of the selector and can agree with the page while the
   selector itself disagrees. Home's five regions are run through
   `document.querySelectorAll` in the browser instead — the real engine — and MC7
   proves it fires.
6. **The DB-read count was already pinned.** Measured before any edit with a
   counting `history_db.open_db`: **3 reads** (recent flights, latest battery, the
   band's check-ins). After the hero: **3**. 24-06's own check asserts exactly
   that number, so the criterion needed no new assertion — only the measurement,
   which is recorded here.

## Files touched outside `files_modified`

**None permanently.** `companion/draw.py` and `companion/layout.py` were each
mutated temporarily (the manual "fed by" proof and MC7) and reverted with
`git checkout-index -f --` against the staged tree; both are byte-identical to
their pre-plan state. `companion/i18n_fr/home.py` is listed in `files_modified`
and was not touched at all, for the reason in Plan assumptions 3.

## Re-derived check counts (obtained by RUNNING, never by arithmetic)

| Harness | Before | After | Δ |
|---------|--------|-------|---|
| `companion/test_view_pages.py` | 161 | **164** | +1 (Task 1), +2 (Task 2) |
| `companion/test_browser_ux.py` | 63 | **65** | +2 (Task 3) |

Both constants were appended (never edited in place) with a comment citing this
plan and task, and both totals were read off the harness's own final line.

## Threat model

| Threat ID | Disposition | How it is now held |
|-----------|-------------|--------------------|
| T-24-08-A (a forked emitter drifting) | mitigated | the structural check computes both pages' ring vocabularies from the markup and refuses any class `draw.py` does not name; the behavioural check replaces a constant at check time and requires both consumers to move; M8's simulated fork fails both |
| T-24-08-B (extra DB queries on the busiest page) | mitigated | 3 reads before, 3 after, measured; 24-06's existing check pins the number |
| T-24-08-C (a duplicated frame verdict) | mitigated | counted exactly once in **both** languages; M7 proves the French half is not redundant |
| T-24-08-D (a stale refresh-swap selector) | mitigated | all five Home regions run through the browser's own selector engine at 360px, at 1280px and with scripts blocked; MC7 proves it fires |
| T-24-08-SC (package installs) | n/a | zero packages installed in any ecosystem |

## Known stubs

None. Every part of the hero is fed by a real read, and the two degenerate cases
(`_day_band_html()` returning `""` for an unreadable `history.db`, and the battery
tile omitting its ring for a device with no reading) are pre-existing, documented
behaviours the container deliberately does not paper over — the wrapper is
unconditional precisely so that a failed query cannot also move everything below
it.

## Threat flags

None. The hero adds no endpoint, no auth path, no file access and no schema
change; it is a `<div>` around markup three existing builders already emitted.

## Verification

- `companion/test_view_pages.py` → **164/164**
- `companion/test_browser_ux.py` → **65/65** (Home's pre-existing overflow check
  passes unchanged, its name untouched)
- `companion/test_status_pages.py` → unchanged (Health is untouched); its single
  failure is the `anomaly_active()` sandbox baseline
- `companion/test_companion_app.py` → 298/300, the two WR-11 read-only baselines
- `companion/test_i18n.py` → 24/24
- `ruff check .` → clean
- `./scripts/run-all-tests.sh` → **the failing set is exactly the 5 sandbox
  baseline names**, no sixth:
  - `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created…` (WR-11)
  - `delete_entry() returns False (never raises) when the state dir goes read-only mid-write…` (WR-11)
  - `POST /airlines/resolve redirects with the manual_save_failed flash key…` (WR-11)
  - `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key…` (WR-11)
  - `anomaly_active() runs on every page render and must never raise…`

Measurements at the 360px floor (both languages, identical), read directly off
Chromium rather than inferred from the checks' own tolerances: hero **312.00px**
wide at left 24, its three children all at left 24 and 312.00 wide, inner gaps
**16.00 / 16.00**, hero-to-picture-row **24.00**, ring **36.00 × 36.00**, band
canvas **278.00 × 24.00**, five marks drawn of five seeded, tiles at tops
905.4 / 1041.0 / 1176.5 (three rows), no page overflow (360/360). At 1280px: hero
**880.00px** wide at left 336, still one column with the same 16.00 / 16.00
inside and 24.00 below, three tiles all at top 459.6 (one row), band canvas
**830.00px** — wider than the 278.00 it gets at the floor. With scripts blocked:
every hero child's left, width and gap identical to the scripted run, both
drawings at the same boxes, all five refresh regions still matching.

## Self-Check: PASSED
