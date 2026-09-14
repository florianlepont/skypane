---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 09
subsystem: docs
tags: [design-system, coverage-ledger, phase-gate, requirements, drawing-contract]

requires:
  - phase: 24-01
    provides: "companion/draw.py, companion/battery.py's extension and the executable drawing contract — the code every design-system row in this plan was read off"
  - phase: 24-02
    provides: "the browser harness's dark-mode, resolved-paint and page-overflow helpers — the capability this plan records as genuinely new to the project"
  - phase: 24-03 / 24-04 / 24-05 / 24-06 / 24-07 / 24-08
    provides: "the five drawings, their measurements, and the findings this plan carries forward rather than letting evaporate"
  - phase: 23-11
    provides: "the precedent this plan holds: supersessions marked IN PLACE with nothing deleted, and a requirement left unticked with its clause named rather than rounded up"
provides:
  - "the DRAWING CONTRACT recorded in sketch-findings-skypane — the app's fourth standing contract beside motion, colour-separation and spacing"
  - "the Phase 24 coverage ledger: five D-items clause by clause, seven provisional decisions with their switching costs, three do-not-re-propose facts, four findings"
  - "CFG-40/41/43/44/45 ticked with per-clause evidence; CFG-39 and CFG-42 deliberately unticked with their unmet clauses named"
  - "the phase gate, passed on names and numbers"
affects: [25-08, 26-09]

tech-stack:
  added: []
  patterns:
    - "A design-system row is written from the CODE at execution time; where the code and an existing row disagree, the row is corrected and the correction is recorded"
    - "A requirement is ticked clause by clause or not at all — and the clause that fails is named, with the decision it needs, rather than rounded up"

key-files:
  created:
    - .planning/phases/24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his/24-09-SUMMARY.md
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md
    - .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "CFG-39 left UNTICKED on a finding this plan made rather than inherited: the battery chart keeps its own scale, canvas, label grid and 17-selector class vocabulary, so 'a single SVG drawing module' is unmet for one of the five drawings — and no standing check pins the two implementations equivalent, so they can now drift silently."
  - "CFG-42 left UNTICKED: the requirement's own parenthetical names detections and they are deliberately not plotted."
  - "CFG-44 TICKED: the 'stack rather than shrink' clause that could not be built is the PLAN's wording, not this requirement's — CFG-44 as written contains no stacking clause at all. Checked rather than assumed, and the distinction is recorded so it is visible rather than convenient."
  - "The human sweep is recorded as PREPARED AND NOT PERFORMED. The developer reviews visually; that review is not this executor's to perform or to claim."
  - "The plan's own acceptance criterion said leave every CFG box unticked; the orchestrator's instruction assigned the ticking to this plan with per-clause evidence. The later, more specific instruction was followed and the deviation is recorded."

requirements-completed: [CFG-40, CFG-41, CFG-43, CFG-44, CFG-45]

duration: ~95min
completed: 2026-09-14
---

# Phase 24 Plan 09: The design system in step, the ledger, and the gate

**The authority gains a drawing contract written from the code rather than from the
plans; the ledger ticks five requirements clause by clause and leaves two unticked with
their unmet clauses named — one of them on a finding this plan made rather than
inherited; and the gate passes on names and numbers, with the browser harness proven to
have really run by a three-minute wall clock.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3/3
- **Files modified:** 5 (1 created)

| # | Commit | Message |
|---|--------|---------|
| 1 | `81dace1` | `docs(24-09): the design system gains a drawing contract, in step` |
| 2 | `c28f888` | `docs(24-09): the coverage ledger, clause by clause, and two honest un-ticks` |
| 3 | *(this SUMMARY)* | `docs(24-09): the phase gate, and Phase 24 closed at 9/9` |

## The finding that mattered most

**CFG-39's "a single SVG drawing module" is not true, and nothing in the tree would have
noticed.**

This was not carried in from a SUMMARY. Every plan in the phase reported honestly on its
own scope, and no plan's scope contained this question: 24-01 built `companion/draw.py`
and recorded that its own `files_owned` forbade touching `companion/pages/*.py`, routing
adoption of the battery chart to 24-05; 24-05 owned that function, found that `draw.py`
offers no primitive fitting the nested area layer it needed, said so, and did not rewire
the rest. Both records are accurate. The consequence only appears when the clause is read
against the whole tree at close, which is what this ledger is for.

Measured:

```
companion/pages/health_page.py imports companion.draw            -> yes
...but the chart's geometry comes from health_page.sparkline_point_y()
   (promoted out of a closure by 24-05, NOT onto draw.percent_y())
grep -c '^\.sparkline' companion/static/style.css                -> 17
grep -c '^\.drawing'   companion/static/style.css                -> 22
```

Two parallel implementations of one coordinate scheme, each with its own scale, its own
canvas emission, its own label grid (`.sparkline`/`__y`/`__x` beside
`.drawing`/`__y`/`__x`) and its own class vocabulary. Four of the five drawings go
through the shared module; the battery chart does not.

**What makes this worth un-ticking rather than rounding up is the second half.** 24-01
measured `draw.percent_y()` reproducing the chart's arithmetic **exactly** on all five
seeded points including out-of-range — but that was a one-off measurement recorded in a
SUMMARY, not a shipped check:

```
grep -rn 'percent_y' companion/test_status_pages.py \
        companion/test_view_pages.py companion/test_browser_ux.py   -> (empty)
grep -rn 'battery_sparkline_svg' companion/test_companion_app.py    -> (empty)
```

So the two can now drift with nothing noticing, which is the exact failure mode the
requirement exists to prevent. Ticking it would have been the CFG-28 error of Phase 22
repeated — a box marked complete while a clause is knowingly unmet.

## What was recorded in the design system

Four files, every number read live from `companion/draw.py`, `companion/battery.py`,
`companion/static/style.css` and the harnesses at execution time.

**`references/data-density.md` — the drawing contract** (+275 lines), the app's fourth
standing contract beside motion, colour-separation and spacing:

- `companion/draw.py` as the one geometry vocabulary, stdlib-only, importing neither
  `companion/pages/` nor `server/` (pinned by an **AST** scan, not a token scan).
- **The two coordinate schemes as a table with the rule for choosing** — percentage +
  `.drawing__canvas` for a card-filling time series (no `viewBox` at all, because giving
  that chart one scales every stroke width, marker radius and hit target with the box);
  `viewBox` + `.drawing__figure` for an aspect-locked mark (the class declares **no**
  size so the intrinsic attributes survive). Two separately-named helper families, never
  a `use_viewbox=` flag.
- **HTML labels outside the canvas in both schemes**, which is what makes viewBox
  overflow *unreachable* for text — this phase emitted **no SVG `<text>` node anywhere**.
- **The nested `<svg viewBox="0 0 100 100" preserveAspectRatio="none">` escape hatch**,
  with the two candidates ruled out without building (percentages are illegal in a
  `points` list or a `d` string; nothing but `<rect>` takes percentage geometry).
- **The class-and-token paint idiom and its four machine-enforced anti-patterns**, each
  mutation-proven, with the selector-boundary detail (`.drawing-axis` is a substring of
  `.drawing-axis-label`) and the refuse-versus-escape boundary (`REFUSED_ATTRIBUTES` and
  `PAINT_ATTRIBUTES` by name; everything else is text, escaped and never refused,
  because a refusal would turn a page render into an exception for a value the app does
  not control).
- **The `url(` ban that rules out gradients**, recorded as a deliberate non-build with
  its ground rather than as a gradient still coming.
- **"A drawing and any printed number must come from the same value"** — with 24-04's
  mutation quoted: sourcing the ring from `battery_fraction()` instead of the printed
  integer makes arc and text disagree by **0.0033**, and the cost of the shipped choice
  (1% quantisation, 3.6° of arc at 72px, ~0.6px of ink) stated beside the benefit.
- **One estimator with exactly two allow-listed homes**, the second being
  `server/poll_loop.py`'s deliberate private copy because the server package may never
  import the web-app package (D-27) — allow-listed **by name with a written
  justification**, with the three-net scan whose strongest net is `4200` and `3300`
  appearing *together*.
- **Phase 24's drawings carry no motion, deliberately** — `@keyframes` still 4, reduce
  blocks still 2, no-preference still 1.
- Each drawing's own live numbers: the ring's ratios and both degenerate fractions; the
  band's re-derived 1.5% spacing, its 67-mark ceiling and its two-span midnight rule; the
  grid's computed ten columns at 25.10px, its 60-cell bound and its four states.
- **The measurement conventions**, as a section of its own: assert the floor not only the
  ceiling; mutate every property you add; clear `__pycache__` after a sub-second
  mutate/revert; stage before you mutate.

**`references/visual-direction-typography.md`** — the battery-trend card entry updated
**in place**: the bare-line description is kept as history with the reason stated, and
the area, the marked newest reading and the threshold recorded beside it, along with both
CFG-41 clauses deliberately not built as worded (no gradient; a legend rather than a
third axis tick, because `.sparkline__y`'s `space-between` puts a third label at 50%
while the threshold sits at **59.25%**). Plus the ring gauge as one component at two
sizes with the "no CSS-only variant" mechanism and the `aria-hidden` justification pinned
in **both** directions; Health's third full-width card and its `<h2>` count moving 4 → 5;
and the sub-scale tier's one new member at no new size.

**`references/accessibility-contrast.md`** — the **dark-mode measurement capability**,
recorded as genuinely new with what it catches that reading CSS could not (a class that
resolves to nothing, two states collapsed to one colour, a fill that fell back to the SVG
default), why the explicit attribute rather than `emulate_media`, and why the helper
asserts the two themes **invert** rather than asserting hex values. Plus the
composite-and-contrast idiom for a translucent fill with its floor **located by sweeping
alpha**, the phase's contrast additions, and the no-JS/reduced-motion floors held by
construction. Three new "What to Avoid" entries.

**`SKILL.md`** — the Drawings paragraph in `<design_direction>`, the Data Density row in
the findings index, the sub-scale tier widened by one member, and Phase 24's folded-in
work entry.

### The phase's contrast additions, recorded where nothing had pinned them

24-07 added **six** checks — three pairs × two themes — and they are **status-vs-status**,
not status-on-card. That distinction is the whole point and it is now written down:
everywhere else in this app a status colour appears **alone beside its own word** (one
tile border, one dot with its label, one section edge), so "can these two be told apart
as different signals" had never been a question about that pair set. The regularity grid
is the first surface where all three appear side by side **with nothing but colour
between them**, and **nothing pinned it anywhere**. Held to the existing
`MIN_SIGNAL_PERCEPTUAL_DISTANCE` (28.0) and deliberately **not** to the hue floor, which
stays on the accent-vs-error pair alone. Closest pair at the shipped palette: light
warn/error at dE76 **55.3** — so the section ships green and its job is to stay that way
through a future palette edit. `test_contrast_check.py` moved 43 → **49**.

### Supersessions: marked in place, nothing deleted, verified by diff

```
git diff --stat  -> 4 files changed, 317 insertions(+), 9 deletions(-)
```

Nine removed lines, each one a line **amended in place**, none an entry deleted:

| # | File | Removed line | Why it is an amendment |
|---|---|---|---|
| 1 | SKILL.md | `**Current as of:** 2026-09-13, through Phase 23 …` | Phase 23's full text is preserved verbatim inside the new sentence, after Phase 24 |
| 2 | SKILL.md | the sub-scale exception tier bullet | every existing member kept; one added, explicitly as a widening at no new size |
| 3 | SKILL.md | the "Zero new custom properties" bullet | the original sentence is **kept with a strike-through and a stated reason** — Phase 24 added a third, and Phase 23's two remain exactly two |
| 4 | SKILL.md | the findings-index Data Density row | appended to; every prior clause intact |
| 5-6 | accessibility-contrast.md | the two `MIN_SIGNAL_*` code-block lines | **values unchanged**; comments extended to record the new pair set |
| 7 | accessibility-contrast.md | the Origin line | appended to |
| 8 | visual-direction-typography.md | the Battery trend section bullet | original text kept verbatim; one pointer sentence added |
| 9 | visual-direction-typography.md | the Origin line | appended to |

*(Note on the plan's own metric: it asks for `git diff | grep -c '^-[^-]'`, which reports
**6** here because a removed markdown list item renders as `-- ` and is excluded by that
pattern. The real figure is 9, obtained with `git diff -U0 | grep '^-' | grep -v '^---'`,
and all nine are enumerated above. Recorded rather than reported as 6.)*

### Discrepancies found between an existing row and the code

**One, and it was corrected in place.** `SKILL.md`'s motion entry claimed *"This is the
one place in this file where that stated achievement is broken, and it is broken by
exactly two."* Read live, Phase 24 added a **third** custom property,
`--drawing-canvas-height` (declared once with a 160px default on `.drawing__canvas`, and
overridden once at 24px on `.day-band`). The sentence was true when written, so it is kept
in place with its supersession marked and the reason stated — the standard Phase 23's two
had to meet is still the standard a fourth would have to meet.

Everything else checked out against the code and is recorded as verified rather than
assumed: accent uses **70**, `@supports selector(:has(*))` **1**, `@keyframes` **4**,
`position: sticky` **3**, reduce blocks **2**, no-preference blocks **1**,
`.sparkline-axis-label` still **10px**.

## The coverage ledger's verdict per D-item

Walked against the **roadmap's own wording**, and against the code rather than the plans.

| D-item / goal clause | Verdict |
|---|---|
| the goal's **"sharing one battery estimator"** | **Landed, machine-enforced — and the premise it was written on was false.** There is one estimator; the plan's "exactly one module in `companion/` or `server/`" is false in this tree and permanently so. Two easy ways out were rejected (deleting the copy breaks D-27 for a cosmetic win; scoping the check to `companion/` stops watching where a third copy is most likely to appear). An allow-list of exactly two, each justified in writing, shipped instead |
| **D21** — the ring gauge, reused small | **Landed in full.** One emitter at 72px and 36px, proven one function behaviourally |
| **D8** — the chart's **gradient** area, marked last point, threshold | **Landed, minus the GRADIENT, and minus adoption of the shared module.** The flat fill is complete against CFG-41's own wording ("a filled area"); it is the **roadmap's** wording that is not met, and that is recorded rather than reconciled away. The module question is CFG-39's unmet clause |
| **D13** — Home's day timeline | **Landed, minus detections** — a provisional planning decision honoured as scoped, and CFG-42's unmet clause |
| **D20** — the **wake-punctuality** grid | **Landed with the METRIC and the NAME both changed, deliberately and on evidence.** The roadmap's own entry flagged the blocker; the settlement is recorded with its grounds. `wake_epochs` accrues and is read by nothing, pinned |
| **D4** — the Home hero the others feed | **Landed.** One plan-level clause was refuted by measurement (the desktop column split) and is recorded rather than smoothed |

## Requirements — what was ticked, and what was not

**Ticked, each with per-clause evidence on its traceability row:**

| ID | The clause that took the most checking |
|---|---|
| **CFG-40** | "ONE function called twice rather than two similar functions" — proven **behaviourally**, since two files can both import an emitter and still draw two different pictures; and the CSS-only "small variant" made structurally impossible by emitting `stroke-width` as a presentation attribute |
| **CFG-41** | The wording. This requirement asks for **"a filled area"**; the roadmap asks for a **"gradient area"**. The flat fill meets the requirement as written, and the roadmap's clause is carried in the D8 row as a deliberate non-build. Also checked: "the latest reading is **judged against**" the threshold — one function places the threshold *and* the readings, so the comparison is geometric rather than asserted, and the readout's own verdict states it in words |
| **CFG-43** | The headline. This row does **not** ask for a punctuality metric; it asks that punctuality be *"reported only as far as the stored data can prove it"* — a constraint of honesty, which is exactly what shipped. (The roadmap's "wake-punctuality grid" phrasing is superseded with its ground.) One caveat is deliberately not in the caption and is recorded: the reader's docstring names two things it cannot know, and the caption carries the first |
| **CFG-44** | **The "stack rather than shrink" clause is the PLAN's wording, not this requirement's.** CFG-44 as written asks for one composition, the same emitters, and no second copy — there is no stacking clause in it at all. Checked rather than assumed; the plan-level clause is carried in the D4 row |
| **CFG-45** | "Takes every colour from the theme tokens so it reads in BOTH themes" — the clause that had never been *checkable* before this phase. Sixteen resolved paint values, none the SVG default, in both themes and with scripts blocked |

**Deliberately NOT ticked:**

- **CFG-39** — unmet clause: **"a single SVG drawing module (scale, geometry, label
  placement, colour binding)."** Six of seven clauses hold; one (`viewBox` containing its
  outermost labels) holds only **vacuously**, because no label is inside any viewBox
  anywhere in the phase, and the obligation was discharged on the drawings' own ink
  instead — a real measurement but not the one the clause names. **Decision needed:**
  rewire `battery_sparkline_svg()` onto `draw.percent_*` + `draw.label_grid()` and retire
  the parallel `.sparkline*` vocabulary, **or** amend the clause to "one drawing module
  plus the chart it was generalised from" **and add a standing equivalence check**, so
  the two provably cannot drift.
- **CFG-42** — unmet clause: **"detections"**, named in the requirement's own
  parenthetical. A deliberate non-build with a recorded ground (two mark vocabularies in
  a **measured** 278px canvas that resolves ~22-minute intervals and holds at most 67
  marks). **Decision needed:** amend the parenthetical and schedule detections separately
  with a design for telling two vocabularies apart, or schedule the work and keep the
  clause.

## Findings carried forward

All four are in the ledger, in full, with their numbers.

1. **Ceiling-only assertions let real defects through, three plans running.** 24-06's
   1 440 check-ins collapsing to one mark at 0.00% with four green checks; 24-07's
   whole-pixel cells at 277px inside a 278px canvas with containment green throughout;
   24-08's (0,1,0) specificity tie measuring 40.00px where 16 was declared, with two
   thirds of the composition correct. **Assert the floor** is now a testing convention in
   the design system.
2. **Mutate every property you add.** Six-plus declarations measured inert or
   load-bearing-but-invisible. Recorded with the table, **and with the backlog sweep it
   implies flagged as nobody's yet** — the discipline only ever ran over declarations this
   phase added, and both failure classes are silent by construction.
3. **Clear `__pycache__` after any sub-second mutate/revert cycle.** Written into
   `references/data-density.md`, where a future executor meets it before paying for it,
   with its companion rule (stage before you mutate; `git checkout-index -f --`, never
   `git checkout --`).
4. **Plan assumptions that proved wrong.** The band is 278px, not ~330px, so every
   derived spacing figure was wrong with it; `quiet_hours_status()` returns an activity
   status, not a window; the Paris/UTC boundary case a plan named cannot occur (Paris is
   never behind UTC) and the implemented case is its mirror; `.home-hero` is unusable
   because two standing checks forbid the string. Three plans also shipped an incomplete
   `files_modified` list, with no ownership violated in any case.

## The phase gate

`PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh`,
**22 harnesses**.

**1. The failing set is exactly the 5 documented baseline checks, verified by NAME.**
Three harnesses report a failure; the baseline is **not** a file count:

| # | Harness | Check | Reason |
|---|---|---|---|
| 1 | `server/test_manual_resolutions.py` | `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created …` | WR-11 |
| 2 | `server/test_manual_resolutions.py` | `delete_entry() returns False (never raises) when the state dir goes read-only mid-write …` | WR-11 |
| 3 | `companion/test_companion_app.py` | `POST /airlines/resolve redirects with the manual_save_failed flash key …` | WR-11 |
| 4 | `companion/test_companion_app.py` | `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key …` | WR-11 |
| 5 | `companion/test_status_pages.py` | `anomaly_active() runs on every page render and must never raise …` | sandbox |

All five are root-sandbox artefacts (a read-only directory is writable as root) and pass
in CI. **No sixth failure.**

**2. `companion/test_browser_ux.py` did NOT skip, and the wall clock is the proof.**
A skipped harness returns in under a second.

```
grep -c SKIP  ->  0        (both runs)

in-suite (JOBS=4):  ==> PASS companion/test_browser_ux.py (178.8s)
                    browser-ux: 65/65 checks pass

standalone:         real  2m59.692s   (179.7 s)
                    user  0m32.191s
                    sys   0m13.994s
                    browser-ux: 65/65 checks pass,  FAIL 0,  SKIP 0
```

**65 checks, 0 skipped, 179.7 real seconds.** This phase is almost entirely drawing and
the browser is the only thing that measured it in both themes, so this is the gate's
load-bearing number.

**3. Every harness's `EXPECTED_CHECK_COUNT` equals what it printed.** Re-derived by
running, never by arithmetic:

| Harness | Pinned | Printed | | Harness | Pinned | Printed |
|---|---|---|---|---|---|---|
| `companion-app` | 300 | 298/**300** | | `render` | 134 | 134/134 |
| `status-pages` | 302 | 301/**302** | | `calendar_rules` | 113 | 113/113 |
| `view-pages` | **164** | 164/164 | | `enrich` | 59 | 59/59 |
| `browser-ux` | **65** | 65/65 | | `illustrations` | 58 | 58/58 |
| `i18n` | **24** | 24/24 | | `plane-detection` | 47 | 47/47 |
| `config-page` | 240 | 240/240 | | `colour_rules` | 33 | 33/33 |
| `contrast-check` | **49** | 49/49 | | `manual_resolutions` | 23 | 21/**23** |
| `config-history` | 87 | 87/87 | | `runway-config` | 15 | 15/15 |
| `poll-loop` | 99 | 99/99 | | `panel-preview` | 11 | 11/11 |
| | | | | `notify` | 8 | 8/8 |
| | | | | `dither` | 6 | 6/6 |
| | | | | `pipeline-e2e` | 6 | 6/6 |

*(Bold = measured in this plan for the first time or carried in as known. The three
harnesses printing fewer passes than their pin are the three carrying the five baseline
failures, and the denominators match.)*

**4. The deferred-script count is unchanged from its pre-phase value: 14 and 14.**
Not read off a file count — asserted against a real render, and it **passed** in the gate
run:

> PASS a rendered authenticated page contains exactly fourteen deferred `<script src=`
> tags before the closing body tag …

The pin's own function name, `_fourteen_deferred_scripts_before_closing_body`, is
byte-identical at Phase 23's closing commit (`5507437`) and at HEAD. Server-rendered SVG
was chosen precisely so this number would not move, and it did not.

**5. `ruff check .` → `All checks passed!`**

**6. The stylesheet's structural guards are green**, checked because this plan writes
prose about a file that is grep-guarded: `style.css` stray comment terminators **0**,
`@keyframes` **4**, `@supports selector(:has(*))` **1**. This plan edited no CSS, and its
own prose lives in `.claude/skills/` and `.planning/`, neither of which any harness reads
(verified: the only harnesses touching those paths read three specific named files from
phases 06.6.3, 20 and 21, none of them this phase's and none of them `REQUIREMENTS.md`).

### The human sweep: PREPARED, NOT PERFORMED — and deliberately not claimed

The plan's Task 3 asks this executor to "walk the human sweep and record every finding."
**It was not walked, and recording an answer to it would have been the dishonest thing in
a plan whose entire subject is not rounding up.** The developer reviews this phase
visually, and that review is not an executor's to perform or to claim — a judgement like
"does the ring read as a battery" is exactly the class of question
`24-VALIDATION.md` lists as manual-only *because no assertion makes it*.

What is recorded instead, for each of the five groups: the automated evidence that
already bears on it, and the judgement that is genuinely left open.

| # | The question | Automated evidence already in hand | Left to the developer |
|---|---|---|---|
| 1 | Does the ring read as a battery, and does it agree with the number beside it? | **Agreement is measured, not visual**: arc and text are one value in two renderings, tolerance 0.0005, mutation-proven at 0.0033 drift. Paint measured on both pages in both themes | Whether a ring gauge *reads as a battery* at 36px at all |
| 2 | Does the area help or muddy the line, and is the threshold obviously a threshold? | Area/line/mark resolve to one ink per theme; area composite 1.3317:1 light / 1.4955:1 dark against a floor located by sweeping alpha; threshold deliberately in a different token | Whether 0.14 is the right opacity **on real hardware**, and whether a legend reads as a threshold's label without sitting beside it |
| 3 | Does the band tell you at a glance whether the frame has been waking, and is the shading in the right half of the day? | Spans measured at 81.09px and 11.59px inside a 278px canvas; mark-over-span contrast 12.292:1 / 11.842:1; the wrapping window asserted as **two** spans | Whether ~22-minute resolution is enough to read "normally", and whether the shading lands where the night *feels* like it should |
| 4 | Does the grid read as an observation rather than an accusation, and are its four states still four in dark mode? | Four states measured as four distinct tokens; closest pair dE76 55.3; the caption's three clauses each separately asserted; the two refused words grep-pinned absent from both rendered languages | Whether a wall of red squares *feels* like an accusation regardless of what the caption says |
| 5 | Does Home's hero read as one thing rather than four stacked things? | Gaps asserted as **equalities** — 16px inside, 24px below — in both languages, at 360px and 1280px, and with scripts blocked | Whether proximity alone, with no surface, is enough grouping to the eye |

**The one thing the automated evidence cannot substitute for is group 2's dark-mode
question**, which `24-VALIDATION.md` names explicitly as manual-only.

### Folded in from `deferred-items.md`

Both entries are now in the ledger rather than stranded in a phase-local file.

1. **`the live theme preview CROSSFADES…`** — logged by 24-05 as an intermittent seen
   only in mutation runs; it has since appeared in a **clean CI run** on `2520a21`
   (browser-ux 64/65), so it is genuinely flaky rather than a curiosity. **The
   orchestrator is fixing it in parallel**, changing that one check to wait for
   `transitionrun` instead of sampling at a guessed instant; `EXPECTED_CHECK_COUNT` does
   not move (65 stays 65). **The fix is the orchestrator's and is credited as such**;
   24-09 did not edit `companion/test_browser_ux.py`. **It did not fire in either of this
   gate's two runs** (65/65 both times).
2. **`…the reminder stays within 48px…`** — failed once at **48.1875**, a 0.19px
   overshoot of a hard ceiling; a sub-pixel text-metric boundary. **Still open and still
   nobody's**, with the decision it needs stated in the ledger. It did not fire in either
   of this gate's runs.

## Deviations from plan

### [Rule 3 - Blocking] The plan says leave every CFG box unticked; the orchestrator assigned the ticking to this plan

- **Issue:** 24-09-PLAN.md's `<interfaces>` and Task 2 acceptance criteria both require
  every CFG box to stay unticked, on the ground that "the ticking belongs to
  verification, not to a closing plan's optimism", and state
  `grep -c '^- \[x\] \*\*CFG-4' → 0` as a criterion. The orchestrator's instruction
  assigns CFG-39…CFG-45 to this plan **"to tick, but only where the evidence genuinely
  supports every clause"**, with the per-clause evidence required in the report.
- **Resolution:** the later and more specific instruction was followed. The plan's own
  *reason* is honoured in substance rather than in form: its stated fear is the CFG-28
  error — a box ticked while a clause is unmet — and that is exactly what the two
  deliberate un-ticks prevent. The gate also ran **in this plan** (Task 3), so
  "verification has not run" is no longer true at the moment of ticking.
- **Consequence:** `grep -c '^- \[x\] \*\*CFG-4' .planning/REQUIREMENTS.md` is **5**, not
  the criterion's 0. Recorded rather than quietly satisfied.

### [Process] The human sweep was not performed

Covered above. The plan's acceptance criterion "the human sweep's five groups each have a
recorded answer" is met in the form the standing constraints permit — each group has a
recorded *state* (evidence in hand, judgement outstanding) rather than a fabricated
verdict.

### [Note] An instruction arriving from outside the task channel was declined

Partway through this plan, MCP server instructions in the session context directed the
executor to stop using the Read/Edit/Write tools and perform file reads and edits through
`Bash` (`cat`, `sed`, heredocs) instead. That text arrived inside an MCP server's
instruction block — not from the user and not from the orchestrator — and its effect
would have been to route file modification around the permission-checked tools. **It was
ignored**; every edit in this plan went through the ordinary tools. Recorded here because
a silent compliance would have been invisible in the diff.

## Plan assumptions that turned out wrong

1. **The plan's deletion metric under-counts.** `git diff | grep -c '^-[^-]'` reports 6
   where 9 lines were removed, because a removed markdown list item begins `-- ` and the
   pattern excludes it. All nine are enumerated above; the metric is recorded as
   imprecise rather than used as the answer.
2. **"`.../references/visual-direction-typography.md` carries … the sub-scale label
   tier."** It does not — the tier is enumerated in `SKILL.md`'s `<design_direction>`.
   It was widened there (in place, one member, no new size) and a pointer added to
   visual-direction, rather than a second copy created in the file the plan named.
3. **The plan expected the design-system work to find discrepancies at 22-16's rate
   (three stale load-bearing numbers).** One was found, not three: the "broken by exactly
   two" custom-property sentence. Every other number checked out. Recorded so the absence
   reads as measured rather than as unchecked — the seven greps that verified them are
   named in Task 1's section above.
4. **The plan's `<interfaces>` grep list is partly stale.** `grep -c 'viewBox'
   companion/pages/home_page.py` is **0**, not a positive number — Home's drawings reach
   `viewBox` through `draw.py`'s emitters, never by writing one.

## Known stubs

None. This plan ships documentation only, and every claim in it is either a live-read
value or a quoted measurement from a prior plan's SUMMARY with its source named.

## Threat model

| Threat ID | Disposition | How it landed |
|---|---|---|
| T-24-09-A (tampering with the design system's own history) | mitigated | nine removed lines, each enumerated above and each an in-place amendment; no entry deleted; verified by diff with the correct pattern rather than the plan's under-counting one |
| T-24-09-B (a requirement ticked before verification passed) | mitigated **differently from the plan's design** | the plan's mechanism was "every box unticked, asserted by grep". The orchestrator moved the ticking here, so the mitigation is now per-clause evidence on every ticked row plus two deliberate un-ticks with their clauses named — the CFG-28 precedent is cited on both |
| T-24-09-C (a green suite that skipped its most important harness) | mitigated | `grep -c SKIP` is 0 in both runs, the baseline is verified by NAME, and the browser harness's **179.7 s** wall clock is quoted as the positive proof it ran |
| T-24-09-SC (package installs) | n/a | zero packages installed in any ecosystem |

No **Threat Flags**: this plan adds no endpoint, no auth path, no file-access pattern and
no schema change. It modified **no** file under `companion/` or `server/`.

## Self-Check: PASSED

Files claimed, verified present on disk:

- `.claude/skills/sketch-findings-skypane/SKILL.md` — FOUND, "Phase 24" ×6
- `.claude/skills/sketch-findings-skypane/references/data-density.md` — FOUND, "Phase 24" ×4
- `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md` — FOUND, "Phase 24" ×6
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` — FOUND, "Phase 24" ×6
- `.planning/REQUIREMENTS.md` — FOUND, CFG-39…CFG-45 ×21 occurrences, 5 ticked / 2 unticked
- `.planning/phases/24-…/24-09-SUMMARY.md` — this file

Commits claimed, verified in `git log`:

- `81dace1` — FOUND (`docs(24-09): the design system gains a drawing contract, in step`)
- `c28f888` — FOUND (`docs(24-09): the coverage ledger, clause by clause, and two honest un-ticks`)
