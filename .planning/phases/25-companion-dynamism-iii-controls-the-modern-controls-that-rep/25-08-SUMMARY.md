---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 08
subsystem: design-system
tags: [design-system, coverage-ledger, phase-gate, decision-list, documentation-only]

requires:
  - phase: 25-01
    provides: the one new script, the `.js` gate vocabulary, the battery-life arithmetic, the executable no-JS control contract
  - phase: 25-02
    provides: the four browser-harness instruments every control plan ran on
  - phase: 25-03
    provides: D16's runway map
  - phase: 25-04
    provides: D17's quiet-hours dial
  - phase: 25-05
    provides: D18's wake-interval slider and its two gauges
  - phase: 25-06
    provides: D5's theme carousel and the Display page-height instrument
  - phase: 25-07
    provides: D19's artwork drop zone
provides:
  - "the CONTROLS contract in `sketch-findings-skypane` — the fifth standing contract beside motion, colour-separation, spacing and drawings"
  - "the touch-target register's Phase 25 entries, every number MEASURED in its own container"
  - "the no-JS control contract as a named design-system pattern"
  - "the continuous-value keyboard model, recorded once, with the native Page rule corrected to a percentage of the band"
  - "the Phase 25 coverage ledger in .planning/REQUIREMENTS.md — every clause of all five D-items with one of three verdicts"
  - "the developer's eight-decision list, each with its alternative and its reversal cost AS IT NOW STANDS"
  - "the phase gate, re-derived by running"
affects: [26-01, 26-02, "every future control plan"]

tech-stack:
  added: []
  patterns:
    - "a number recorded in the design system is READ FROM THE CODE at the moment it is written, never copied from a plan or a summary"
    - "a supersession is marked IN PLACE with its reason; the value of a recorded rejection is that a later reader can see what was rejected and on what ground"
    - "a requirement is ticked per CLAUSE or not at all — a shortfall is never compressed into a tick"

key-files:
  created:
    - .planning/phases/25-companion-dynamism-iii-controls-the-modern-controls-that-rep/25-08-SUMMARY.md
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "CFG-46, CFG-47, CFG-48, CFG-49 and CFG-51 ticked with per-clause evidence; three re-scopes named in place rather than compressed into a tick"
  - "CFG-50 NOT ticked — two clauses fail: nothing is behind the disclosure (a closed <details> hides its own children), and the clause the requirement nominates as its own judge returns 3743 px against X6's 2600 px"
  - "CFG-52 NOT ticked — 'operable from the keyboard with no pointer event at all' is measured for four of the five controls and unmeasured for D19, whose control is a native file input the harness submits by clicking"
  - "Phase 24's own omission from references/data-density.md's Origin line was corrected in place at this phase's close, because a missing attribution is the same class of defect as a stale number"

requirements-completed: [CFG-46, CFG-47, CFG-48, CFG-49, CFG-51]

metrics:
  duration: ~3h
  completed: 2026-09-14
  checks_added: 0
  browser_harness: "81/81, 0 SKIP, 0 FAIL, 270s standalone"
---

# Phase 25 Plan 08: the design system in step, the clause ledger, the decision list, the phase gate Summary

**Five controls' worth of learning written into the design system in place with nothing
deleted; every clause of all five D-items given one of three verdicts; five requirements
ticked on per-clause evidence and two deliberately left unticked with the unmet clause
named; and a gate whose browser harness ran for 270 real seconds and printed no SKIP.**

This plan wrote no application code and changed no behaviour. `companion/`, `server/`,
`stub-server/` and `scripts/` are byte-identical across all three of its commits.

---

## Task commits

| Task | Commit | What |
|---|---|---|
| 1 | `157dd0f` | the controls contract, recorded in step with the five that taught it |
| 2 | `d06a59a` | the coverage ledger, and one decision list for the morning |
| 3 | `5a35e05` | the phase gate, re-derived by running on the final tree |

---

## Task 1 — the design system, updated in step

**Every numeric value added to the skill was read from the code in this task.** The
commands and their outputs:

```
$ grep -c '@supports selector(:has(\*))' companion/static/style.css          6
$ grep -c '@keyframes' companion/static/style.css                            5
$ grep -c '^@keyframes' companion/static/style.css                           4
$ grep -c '@media (prefers-reduced-motion: reduce)' companion/static/style.css   3
$ grep -c 'prefers-reduced-motion: no-preference' companion/static/style.css     2
$ ls companion/static/*.js | wc -l                                          17
$ grep -cE 'position: *sticky' companion/static/style.css                    3
```

and the same file with `/* … */` stripped, which is the form every pin uses and the
only form that means anything here:

```
@supports selector(:has(*)) {  blocks   1
@keyframes                              4
prefers-reduced-motion: reduce          2
prefers-reduced-motion: no-preference   1
position: sticky                        1
'drawer' mentions                       0
stray comment terminators               0
```

against the phase's base commit `f7d25d9` (`git show f7d25d9:companion/static/style.css`),
which reads **1 / 4 / 2 / 1** — so four of the five are unmoved and the fifth (`.js`
files) is 16 → 17, exactly one more.

```
$ git ls-tree --name-only f7d25d9 companion/static/ | grep -c '\.js$'        16
$ wc -l companion/static/value-controls.js                                  795
$ grep -c '\.value = ' companion/static/value-controls.js                     1
$ wc -l companion/static/theme-preview.js companion/static/panel-lookup.js  418 / 681
$ git diff --stat f7d25d9 HEAD -- companion/illustration_normalize.py       (empty)
```

Live CSS values read straight out of the stylesheet for the register entries:
`.control-hit-area` 22 × 22 / `inset: -11px` / 14 px glyph, identical declaration-for-
declaration to `.copy-btn`; `.quiet-dial__handle::before { inset: -12px }`;
`.theme-chip-grid--strip { scroll-padding-right: 104px }` against
`.theme-chip--compact { width: 104px }`; `.theme-carousel__pagers { gap: var(--space-lg) }`;
`.quiet-dial { width: 176px; --quiet-dial-radius: 78px }`; `.upload-drop__preview
{ aspect-ratio: var(--upload-preview-ratio) }` with **no fallback**.

Every measured hit area, page height and paint value came from a named SUMMARY's
recorded browser measurement, and each is attributed to its plan in the skill.

### What was recorded, by file

**`references/control-density.md`** (+141 / −2) — a new "Phase 25" section:

- **The touch-target register's Phase 25 entries, each filed in the correct category
  with its MEASURED numbers**, and a table naming the plan each came from:
  - *exempt-by-delegation, precondition re-measured, no new entry* — the runway radios
    (wrapping labels **90 × 201 / 89 × 197 / 88 × 197**, 25-03) and the eighteen chip
    radios in the strip (**106 × 71**, 25-06).
  - *relocated, three new consumers of `.control-hit-area` at `.copy-btn`'s own values
    verbatim* — both dial handles and both carousel pagers, **45 × 45** each
    (25-04, 25-06), **with the one override going UPWARD** (`-12px`, because the handle
    rides a rotate/translate pair, lands off the pixel grid and measured **43 × 43** at
    the shared value).
  - *kept* — the wake-interval range at the global `input, select` floor unmodified,
    **279 × 45** (25-05), the third native input shape in this category.
  - *met-directly* — the artwork drop zone, **241 × 154** (25-07).
  - **Nothing was traded. No control landed below 44 px. No fifth category was needed**,
    so there is no new named exception to argue for.
- **"Hit targets are MEASURED, never declared"**, with the phase's three proofs that a
  synthesized 44 is not a resolved 44: `.copy-btn` 34 × 26 (occluding neighbours), the
  handle 43 × 43 (fractional pixel position), the Previous pager 30 × 45 (a sibling's
  own `::before` winning an 8 px gap — which is why the pager gap is a hit-target
  number and not a spacing one).
- **The no-JS control contract as a named pattern** — its two shapes, the `.js` gate's
  hide-by-default direction with all three load-bearing properties, the gate class going
  on the gated element itself, the rule that only what *cannot* work without a script is
  gated, and the proof being **operate-submit-persist** and never *render*.
- **The continuous-value keyboard model, recorded once**, with 25-05's correction of
  record kept in place: native Page keys move **10 % of the band**, not ten steps
  (measured `PageUp` 60 → 420), and the dial matched the native model deliberately. Plus
  the double-role error and the never-prevent-a-native-default rule.
- **The one-script budget and how it was kept** — five controls, one new script, three
  taxes paid once, and the reason each of the other four paid nothing.
- **Scroll-snap and the keyboard made to agree**, with the measured failure
  (six ArrowDowns leaving the chip 50 px outside a 278 px strip), the four candidates
  measured, and the harness pinning the two numbers equal.
- **The two-declaration grid blowout**, with the measurement that each declaration alone
  leaves the whole 2049 px blowout in place.
- Nine new **What to Avoid** entries and five new CSS-pattern blocks.

**`references/settings-page-patterns.md`** (+57 / −1) — the Quiet hours card's new shape
(the ring, the still-visible time inputs, the one span triple, the `aria-hidden` readout,
the 176 px geometry argument, the deliberate absence of a minimum separation, and the
preset-repaint finding); the Wake interval card's two gauges with **the battery gauge's
honesty rule**; the `<details>`-not-`<dialog>` choice with the recommended shape recorded
as impossible; **Display's page height before and after**; and a live re-verification of
the `:has()` block count that extends the file's own stale-number warning with its
converse (prose satisfying a prose-blind scan). Seven new **What to Avoid** entries.

**`references/accessibility-contrast.md`** (+30 / −1) — the no-JS floor extended from a
**page** floor to a **control** floor, with the three weaker proofs that pass against a
broken control (one of which this app satisfies by design); the gate's `display: none`
choice and its two-direction assertion; `display: none` destroying focusability while
`.click()` keeps working; the announcement gate on a dragged value and the `role="slider"`
double-role error; the refusal message's measured contrast; and **the CSP recorded as
shaping what a control may do**, with the one-validator seam and its deliberate fail-open
direction. Seven new **What to Avoid** entries.

**`references/data-density.md`** (+191 / −1) — the estimator's second arithmetic beside
the existing one-estimator entry, carrying the **battery honesty rule** (five named
states, a number only from `falling`, two observation floors, the absolute sentence
rendered outside every script-writable element, and Phase 24's own forbidding paragraph
recorded as corrected in place rather than deleted); the **framing-preview** pattern with
the recorded ground for having no client crop and the three-way equivalence proof in its
real order of strength; and **six measurement conventions on top of Phase 24's four**,
including a table of the specific vacuity shapes that pass while proving nothing. Five
new **What to Avoid** entries.

**`SKILL.md`** (+17 / −6) — a **Controls** paragraph in `<design_direction>` as the fifth
standing contract; the Phase 25 **Folded-In Work** entry; the **Current as of** line; four
`<findings_index>` rows extended; and Phase 23's accent-list finding re-checked live and
recorded as **still open**.

### The supersession discipline, verified by diff rather than claimed

```
$ git diff --numstat -- .claude/skills/sketch-findings-skypane/
17	6	SKILL.md
30	1	references/accessibility-contrast.md
141	2	references/control-density.md
191	1	references/data-density.md
57	1	references/settings-page-patterns.md
```

**436 insertions, 11 deletions, and every one of the 11 was inspected: all are lines
re-stated in full and extended.** Five are `Origin` lines gaining a Phase 25 clause; four
are `<findings_index>` rows gaining a Phase 25 clause; one is the `Current as of` line
(whose Phase 24 description survives verbatim, demoted to "and through Phase 24 before
it", which is the chain this line has always used); and one is the Drawings bullet, which
keeps its sentence and gains a marker that its "14" is superseded as the live number.
**Zero deleted lines of recorded reasoning.**

Two supersessions are marked **in place with a stated reason** rather than rewritten:
Phase 24's "the deferred-script pin is still **14**" (kept, because what it records is
Phase 24's own achievement and the standard a fifteenth script had to meet), and 25-04's
"Page keys move ten steps" (kept in `references/control-density.md`, corrected to the
percentage rule with the arithmetic explaining why the two looked identical on a
96-step band).

### The two standing refusals, confirmed unreversed

```
$ grep -i drawer   <comment-stripped style.css>     0
$ position: sticky <comment-stripped style.css>     1   (pre-phase value; not a day header)
```

Neither the **overlay drawer** nor **sticky day headers** was reopened by any plan in
this phase, and a line recording that is now in the ledger's gate section.

---

## Task 2 — the coverage ledger and the developer's decision list

`.planning/REQUIREMENTS.md` (+422 / −12). The twelve deleted lines are the five
`- [ ]` checkboxes that became `- [x]`, and the seven one-line `Planned — …`
traceability rows replaced by their real long-form status. **Nothing was lost**: each
old row's substance was checked and carried into its replacement, and two pieces that
were not carried on the first pass were patched back before the commit — CFG-50's quoted
22-10 sentence ("is NOT met and cannot be by density alone — folding the grid behind the
big preview is D5") and CFG-52's enumeration of 25-02's four instruments.

### The verdicts

| Requirement | Verdict |
|---|---|
| **CFG-46** | **Ticked.** Six clauses, each with its evidence. The one nuance stated rather than glossed: the French-catalogue tax was assessed once and came to **zero**, because the script produces no user-visible literal at all — a stronger outcome than paying it, not a skipped payment. |
| **CFG-47** | **Ticked, as worded, with one word re-scoped and the ground stated.** "One drawn map" renders as one map drawn three times, once per card, because an `<svg>` cannot contain a `<label>` or an `<input>` and a shared canvas would put all three touch targets on absolutely-positioned overlays — the exact failure this requirement's own third clause exists to measure. |
| **CFG-48** | **Ticked.** All five clauses measured, plus four deliberate departures from plan sentences each argued in the row. |
| **CFG-49** | **Ticked.** All six clauses, with the battery clause's honesty shown to be **structural** rather than promised. |
| **CFG-50** | **NOT ticked.** See below. |
| **CFG-51** | **Ticked.** All five clauses measured through a real Chromium, with the three-way picked-vs-dropped proof recorded in its real order of strength. |
| **CFG-52** | **NOT ticked.** See below. |

### CFG-50 — why it does not tick

Three of five clauses hold outright (the carousel over the one existing grid; the single
`:has()` feature query still single; the compact chip still size-only). **Two fail:**

1. **"with the full set behind a native disclosure"** — nothing is behind it, at any
   time. A closed `<details>` hides its own non-summary children, so the recommended
   containing shape would have hidden all eighteen themes whenever shut and left no
   strip. The shipped mechanism is the opposite arrangement and the disclosure changes a
   **layout**, not a **visibility**.
2. **"judged by Display's MEASURED page height"** — the judging was done properly, by an
   instrument built before there was anything to like, and **the verdict is a failure**:
   **3743 px at 390 px (from 4276, −533) and 3752 px at 360 px (from 4269, −517).** X6's
   phone target is **2600 px**, so it is **1143 px over**, and D5's own audit row ("below
   1500 px") is **2243 px** away. The carousel *costs* ~82 px against the ~615 px the
   strip removes, and that is inside the −533 rather than hidden.

**Decisions it needs:** on the height — accept the number and amend or retire X6's phone
target, or schedule a density pass against what is genuinely left (four more cards plus
the Frame strip, which is not a grid and has no win of this size inside a control plan's
scope), or re-word the clause to name the measurement; on the disclosure — amend the
clause to say it changes a layout, or ask for something genuinely hidden, which means
two sets of radios and the duplicate-setting surface 25-06 refused.

### CFG-52 — why it does not tick

Five of six clauses hold and are measured: saving-not-rendering (five named checks),
the touch floor at 360 px, both themes, the motion budget, and the design system updated
in step. **The sixth — "is operable from the keyboard with no pointer event at all" — is
measured for FOUR of the five controls and unmeasured for the fifth.**

Measured with the pointer recorder proving itself alive on each: D16 (`pointer_events: []`),
D17 (ArrowRight / End / Home, `pointer_events: []`), D18 (one 60 s step,
`pointer_events: []`), D5 (one, six and seventeen ArrowDowns, `pointer_events: []`, plus
a scripts-blocked focus-and-arrow clause). **D19 has none**: its control is the native
`<input type="file">`, whose keyboard activation opens the platform's own file chooser,
and `_upload_without_js()` puts the file in through `page.set_input_files()` and
**submits by clicking the real submit button**. The drop zone itself is measured to add
zero focusable descendants with scripts blocked, so nothing was taken away from a
keyboard visitor — what is missing is the positive measurement this requirement asks for.

**Decision it needs:** amend the clause to name what a headless harness can drive (and
record the platform file chooser as the platform's — this app has no code between the
keyboard and that input), **or** schedule the measurement, which may well be buildable
(Tab to the input, press Enter inside `expect_file_chooser()`, and submit by pressing
Enter on the focused submit button).

### The clause walk

Every clause of D16, D17, D18, D5 and D19 now carries one of three verdicts in the
ledger — **built**, **re-scoped** (with what the audit said and what shipped), or **not
built** (with its ground and the decision it needs). Nine clauses are not built or are
re-scoped, and each carries its reason:

- **D16** — "one SVG map" (three copies of one map), "reuse the PNGs" (redrawn, PNGs
  kept), "tracked runway in accent" (pays in ink), "one 300 px object on phone" (three
  53 px maps), the caption's relative-lengths clause, and a north marker.
- **D17** — "hidden synced `<input type="time">`" (they stay visible and authoritative),
  "fixes B14" (already fixed in 22-10, preserved), the Page-key size, the minimum
  separation (answered *no*, deliberately), and the 128 px ring.
- **D18** — "≈ 38 days" (narrowed to observed history), the ratio wording, and the
  `.value-control` class deliberately not adopted.
- **D5** — the dialog, the "behind" a disclosure, the 24 px dots, the adjacency with the
  big preview, the 1500 px height, and the three unconverted grids.
- **D19** — the canvas crop, the progress bar (**and the "Uploading…" label that was
  also not built**, recorded rather than glossed), the hover-only aircraft types, and
  "two cards per row on phone" (**already shipped in Phase 22, not this phase's work**,
  recorded so a future audit does not read it as outstanding).

### The eight decisions, each with its reversal cost as it now stands

All eight from `25-RESEARCH.md` are collected in one place, each with the alternative it
was chosen over and **what reversing it would cost today**. Three costs have moved since
planning and the ledger says which: **decision 1** (one script) went **up** — the two
controls the file serves differ in two attributes rather than one, and a third uses the
file mainly to make it stand aside; **decision 4** (`<details>`) went **up** and now
collides with the phase's own no-JS floor; **decision 5's** canvas-crop half went **up**,
because `panel-lookup.js` now carries a standing assertion that adding one would first
have to delete. Two are unchanged and cheap (**decision 2**, the photographs;
**decision 5's** progress-bar and hover halves). **Decision 3** (the battery gauge) is
unchanged in cost but changed in *risk* — the invented-figure failure mode is now closed
by construction — and DEVICE-05 (closing 2026-09-23) is the input that upgrades it
without the card changing. **Decision 6** is the one whose *answer* has changed, and it
is now a question about what to do with 3743 px rather than about how to measure.

**Decisions 7 and 8 are recorded as the planning conditions this phase ran under**, with
the sequencing made part of the record rather than folklore: no CONTEXT.md, no UI-SPEC,
and `.planning/ROADMAP.md`'s Phase 25 entry carrying the developer's own standing
instruction verbatim — *"this phase must not be executed before the developer has seen
Phases 23 and 24 on screen."*

### Findings folded in rather than left stranded

Eight findings carry forward in the ledger (vacuity and mutation; never sample at a
guessed instant; the synthetic event and the trusted-drag instrument that answers it; a
function NAME tripping a guard that was right; the two mutate/revert accidents and the
`__pycache__` hazard; the null-control requirement; three plan shapes that were
impossible as written; and the accent-reservation list still not exhaustive). Both
entries in this phase's `deferred-items.md` are folded in as **product findings needing a
decision**: the eighteen themes whose Departures and Arrivals swatches are the same
colour, and `.copy-btn`'s 34 × 26 hit area in a Flights detail row.

---

## Task 3 — the phase gate

### The full suite, verified BY NAME

`PYTHON=/home/user/skypane/server/.venv/bin/python3 bash scripts/run-all-tests.sh`, run
**three times** — before this plan's edits, after the design-system commit, and on the
final tree. Identical every time: **exactly five `FAIL` lines in the whole output**, and
they are these five and no others:

1. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because the parent directory is read-only — CR-01's exact reproduction case (WR-11)` — `server/test_manual_resolutions.py`
2. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write, and the existing entry survives untouched since the write never happened — CR-01's mirror case for delete (WR-11)` — `server/test_manual_resolutions.py`
3. `anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely` — `companion/test_status_pages.py`
4. `POST /airlines/resolve redirects with the manual_save_failed flash key (never a dropped connection) when add_entry() cannot write because the state dir is read-only — the exact failure mode CR-01 fixed, exercised end to end (WR-11)` — `companion/test_companion_app.py`
5. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key, leaving the entry in place, when delete_entry() cannot write because the state dir is read-only (WR-11)` — `companion/test_companion_app.py`

**4 × WR-11 read-only + 1 × `anomaly_active()`. No sixth.** They fail only because this
container runs as root; they pass in CI. Verified by **check NAME**, never by
failing-file count — three harnesses report FAIL and five checks do.

### The browser harness did NOT skip — stated explicitly

```
$ grep -c SKIP <whole suite output>                  0
$ grep -c SKIP <standalone harness output>           0
$ server/.venv/bin/python3 companion/test_browser_ux.py
browser-ux: 81/81 checks pass
exit=0   wall clock = 270s
```

**81/81, 0 FAIL, 0 SKIP.** **274.8 s inside the suite** (where it is the critical path —
total suite wall time is 274.8 s at `JOBS=4`, and the next-slowest harness is 31.7 s) and
**270 s / 4 m 30 s standalone**. A skipped harness returns in under a second; this phase
is almost entirely interaction, so that wall clock is the proof it ran.

### Structural pins, re-verified from the code against the phase base `f7d25d9`

| Pin | Base | Now |
|---|---|---|
| `@supports selector(:has(*)) {` blocks (comment-stripped, brace-anchored) | 1 | **1** |
| `@keyframes` (comment-stripped; `^@keyframes` agrees) | 4 | **4** |
| `@media (prefers-reduced-motion: reduce)` (comment-stripped) | 2 | **2** |
| `prefers-reduced-motion: no-preference` (comment-stripped) | 1 | **1** |
| `ls companion/static/*.js \| wc -l` | 16 | **17** — exactly one more |
| deferred `<script src=` on the authenticated shell | 14 | **fifteen** — its own named check passes |
| stray comment terminators in `style.css` | 0 | **0** |
| `position: sticky` (comment-stripped) | 1 | **1** |
| `companion/illustration_normalize.py` | — | **unchanged by one line**, `git diff` empty |

The bare greps are recorded so the next reader does not read them as a regression:
`grep -c '@supports selector(:has(\*))'` returns **6** and `grep -c '@keyframes'` returns
**5**, both because this phase's own comments quote the at-rules while explaining them.
This is the file's stale-number warning running in its other direction — prose satisfying
a prose-blind scan — and it is now recorded in `references/settings-page-patterns.md`.

`companion/app.py` gained 28 lines across the whole phase, all of them 25-01's static
route for the one new script (the comment, the constant, the path and the serve method),
and is **unchanged by one line against 25-07's base** — the CSP was not widened for the
artwork preview.

### The five no-JS persistence checks, by name

One per control, all passing, all reading the value back from disk:

1. *"the runway still SAVES with scripts blocked through the map, at 360px and in BOTH shipped languages — operated natively, submitted through the real form, re-read FROM DISK after a fresh GET, and restored through the identical sequence; with the server-rendered map present on the scripts-blocked page itself, asserted after the save so it can never stand in for it (D-09/CFG-47, 25-03-PLAN.md Task 3)"*
2. *"the quiet window still SAVES with scripts blocked through the dial — both ends set natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way … and the server-drawn ARC, the readout, both time inputs, B14's two 24h siblings and the three presets are all present on the scripts-blocked page, asserted after the save so none of them can stand in for it (D-09/CFG-48, 25-04-PLAN.md Task 4)"*
3. *"the wake interval still SAVES with scripts blocked beside the slider — typed natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way … and the out-of-range trap is re-proven end to end (D-09/CFG-49/T-25-05-B, 25-05-PLAN.md Task 3)"*
4. *"the theme still SAVES with scripts blocked through the carousel, at 360px and in BOTH shipped languages — operated natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way — … the saved theme's radio takes focus and one ArrowDown moves the selection (which display:none would take away) … (CFG-50/D-09, 25-06-PLAN.md Task 4)"*
5. *"with scripts blocked at 360px, an artwork file chosen through the native `<input type="file">` and submitted through the fallback panel's own form is STORED (read back off the real state directory, never off the page — a rejected upload redirects to a page that looks like success) and SERVED back by the illustration route as an image at illustration_normalize.ILLUSTRATION_TARGET_SIZE … (CFG-51/D-09, 25-07-PLAN.md Task 3)"*

The structural half is `_NO_JS_CONTROL_REGISTRY` in `companion/test_companion_app.py`:
**six rows for five controls** (D17 holds two values in two inputs and therefore owns two
rows), each declaring its form association rather than guessing it.

### Final `EXPECTED_CHECK_COUNT` for every harness this phase moved

| Harness | Pre-phase | Final | Passing here |
|---|---|---|---|
| `companion/test_browser_ux.py` | 65 | **81** | 81/81, 0 SKIP |
| `companion/test_companion_app.py` | 300 | **314** | 312/314 (the two WR-11) |
| `companion/test_config_page.py` | 240 | **259** | 259/259 |
| `companion/test_status_pages.py` | 302 | **305** | 304/305 (`anomaly_active()`) |
| `companion/test_i18n.py` | 24 | 24 | 24/24 |
| `companion/test_view_pages.py` | 164 | 164 | 164/164 |
| `companion/test_contrast_check.py` | 49 | 49 | 49/49 |

`ruff check .` → **All checks passed!**

---

## Criteria that did not evaluate as predicted

1. **The plan's `<interfaces>` grep for the `:has()` block count is wrong on this tree,
   in the direction the phase met twice already.** `grep -c '@supports selector(:has(\*))'`
   returns **6**, not 1: one real block plus five comment paragraphs quoting the at-rule.
   The plan's own binding constraint ("read every number from the code") is what caught
   it; the number recorded in the skill is the comment-stripped, brace-anchored **1**,
   with the bare 6 recorded beside it so the next reader is not surprised by it a third
   time. The same applies to `@keyframes`: **5** bare, **4** comment-stripped.

2. **`references/data-density.md`'s `Origin` line had never been extended by Phase 24**,
   which added that file's single largest entry (the whole drawing contract) and its four
   measurement conventions. Found while appending Phase 25's own clause. **Corrected in
   place at this phase's close, with the omission named**, because a missing attribution
   is the same class of defect as a stale number: the next reader trusts the Origin line
   to say who wrote what, and it was two phases behind.

3. **The plan's own acceptance criterion "each new touch-target entry names its category
   and its measured numbers" needed a fifth category that does not exist — and should
   not.** Phase 25's five controls distribute across **four** of the register's existing
   categories (exempt-by-delegation, relocated, kept, met-directly) and none of them
   traded anything away, so the traded-away list is untouched and no new named exception
   had to be argued. That is recorded explicitly, because `.airline-card__chip`'s 20 px
   entry is the precedent for what a below-floor control would have cost.

4. **CFG-52 was expected to tick and does not.** The plan's objective assumed the closing
   plan would tick all seven. Working the clause walk found that
   "operable from the keyboard with no pointer event at all" has no measurement for D19 —
   `_upload_without_js()` submits by clicking. Recorded rather than rounded up.

5. **CFG-50 does not tick for TWO reasons, not one.** The height was the expected one.
   The second — that nothing is behind the disclosure — came out of the clause walk
   itself, and it is arguably the more interesting of the two, because it is a clause
   that cannot be satisfied as written by any implementation at all.

---

## Deviations from plan

### Auto-fixed issues

**1. [Rule 1 — bug] A heading was orphaned by an insertion in
`references/settings-page-patterns.md`**

- **Found during:** Task 1, immediately after inserting the four new Phase 25 sections.
- **Issue:** the insertion anchor matched the paragraph under
  `### \`.field-error\` is not a settings-only class (Phase 22, X3)` rather than the
  heading itself, leaving that heading stranded above four unrelated sections and
  duplicated below them.
- **Fix:** the stranded copy removed; the heading now sits with its own paragraph, and
  every Phase 25 section precedes it.
- **Files modified:** `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md`
- **Commit:** `157dd0f`

**2. [Rule 1 — bug] A fabricated strikethrough in `SKILL.md`**

- **Found during:** Task 1, reviewing the diff for the supersession discipline.
- **Issue:** the in-place supersession of Phase 24's deferred-script pin was written as
  `~~14 is the current value.~~` — striking through a sentence that had never existed in
  the file. That is not marking a supersession in place; it is inventing prior text to
  strike.
- **Fix:** rewritten as a plain statement that the figure is superseded as the live
  number, with Phase 24's own sentence left untouched beside it.
- **Commit:** `157dd0f`

**3. [Rule 1 — bug] A wrong `grep -l` claim in CFG-52's status row**

- **Found during:** Task 2, verifying every claim in the seven new rows against the
  code.
- **Issue:** the row said `grep -l CFG-52 …` returns "25-02, 25-06, 25-07 and 25-08". It
  returns **25-02, 25-03, 25-04, 25-05, 25-06 and 25-08** — 25-07 asserts the same floor
  for D19 but cites CFG-51 rather than this ID.
- **Fix:** corrected to the real list, **with the 25-07 detail kept** because it is
  exactly why the one unmeasured clause below it is D19's.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Commit:** `d06a59a`

**4. [Rule 2 — missing critical functionality] Two pieces of prior recorded reasoning
were not carried into the replacement rows**

- **Found during:** Task 2, auditing the diff's twelve deleted lines one by one.
- **Issue:** CFG-50's old row quoted 22-10's own verdict ("is NOT met and cannot be by
  density alone — folding the grid behind the big preview is D5") and CFG-52's old row
  enumerated 25-02's four instruments. Neither survived the first draft of the
  replacement. Replacing a row is not licence to lose what it recorded.
- **Fix:** both patched back before the commit — 22-10's sentence with a note that its
  prediction turned out right, and the four instruments named with what each measures.
- **Commit:** `d06a59a`

### Deliberate departures from plan sentences

**A. The skill's six files are five.** The plan's `files_modified` lists five reference
files plus `SKILL.md`; the skill has **six** reference files, and
`references/mobile-navigation.md` and `references/visual-direction-typography.md` were
read and **not** written. Nothing in this phase touched navigation or typography — zero
new sizes, families, weights or nav renderings — so an entry in either would have been a
phase name with no finding under it. Stated rather than quietly skipped.

**B. `companion/i18n_fr/*` was not touched by this plan either**, which is worth one line
because the phase added eight catalogue entries in 25-05 and six in 25-07 and
`test_i18n.py` is 24/24 unchanged throughout: its completeness checks cover new entries
by rule, so no harness moved.

---

## Properties found inert

None — this plan added no declaration and no check. Its one measurable property is the
diff shape, and that is reported above.

## Known stubs

None. Every section this plan promised is written, and every number in them was read from
the code in the task that wrote it.

## Threat model

| Threat ID | Disposition | What was done |
|---|---|---|
| T-25-08-A | mitigate | A requirement marked complete whose clauses were not all built. **Two boxes were left unticked** on exactly this ground, each naming its unmet clause and the decision it needs, and the ledger gives **every** clause of all five D-items one of three verdicts with no clause unaccounted for. |
| T-25-08-B | mitigate | A stale number copied into the design system. **Every value was read from the code in Task 1**, with the commands and outputs recorded above; the plan's own `:has()` grep was wrong on this tree and was caught by that discipline rather than propagated. The one omission found in the other direction (Phase 24's missing Origin attribution) was corrected in place. |
| T-25-08-SC | n/a | Zero packages installed in any ecosystem. |

No new threat surface: this plan writes only Markdown, adds no route, no auth path, no
file access pattern and no schema change.

## Threat flags

None.

## Verification

```
PYTHON=/home/user/skypane/server/.venv/bin/python3 bash scripts/run-all-tests.sh
  → FAIL (expected): exactly the 5 sandbox baseline failures, verified BY NAME
    grep -c SKIP over the whole output: 0

server/.venv/bin/python3 companion/test_browser_ux.py
  → browser-ux: 81/81 checks pass, exit=0, wall clock 270s, 0 SKIP, 0 FAIL

ruff check .                       All checks passed!
```

**`<human-check>` REMAINS REQUIRED AND IS THIS PHASE'S REAL GATE.** All five controls
judged together on a real phone at 360 px and on a desktop, in both themes, in both
languages, with the developer operating each one by touch and by keyboard — and
specifically: the dial's handles when the window's ends are close, the battery gauge's
**wording**, Display's page height, and whether the three clauses removed from D19 are
accepted. Phase 06.6.1-06 is the precedent: a real-device session found two confirmed CSS
defects that no harness had caught. **That review is the developer's and is not claimed
here; the PR is not marked ready and nothing is merged.**

## Self-Check: PASSED

Files claimed created or modified, verified on disk:

```
FOUND: .claude/skills/sketch-findings-skypane/SKILL.md
FOUND: .claude/skills/sketch-findings-skypane/references/control-density.md
FOUND: .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
FOUND: .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
FOUND: .claude/skills/sketch-findings-skypane/references/data-density.md
FOUND: .planning/REQUIREMENTS.md
FOUND: .planning/phases/25-…/25-08-SUMMARY.md
```

Commits claimed, verified in `git log`:

```
FOUND: 157dd0f  docs(25-08): the controls contract, recorded in step with the five that taught it
FOUND: d06a59a  docs(25-08): the coverage ledger, and one decision list for the morning
FOUND: 5a35e05  docs(25-08): the phase gate, re-derived by running on the final tree
```

Content claims spot-checked against the files: `.claude/skills/…/control-density.md`
contains "Phase 25"; `.planning/REQUIREMENTS.md` contains "CFG-46" with a `- [x]`
checkbox and a long-form status row; the Phase 25 coverage ledger section exists with all
five D-item walks, the eight decisions, the findings, the folded-in deferred items and
the phase gate.
