---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 10
subsystem: ui
tags: [css, motion, starting-style, dialog, aspect-ratio, layout-shift, skeleton, crossfade, progressive-enhancement, no-js-floor, playwright, harness]

requires:
  - phase: 23-01
    provides: "--motion-fast/--motion-slow, the one-keyframes-per-animation guard, the two-reduce-block pin and the interpolate-size/calc-size ban — every one of which this plan passes unaided, and one of which (the pulse) it deliberately declines to spend"
  - phase: 23-08
    provides: "the one-directional entrance precedent (opening animates, closing is instant) and the written argument against transition-behavior: allow-discrete, which this plan reuses verbatim for a modal"
  - phase: 23-09
    provides: "the save bar, whose arrival removes the inline fallback Save and moves everything below it by 36px — the reason this plan's chip measurements are taken relative to the grid rather than to the page"
  - phase: 22-15
    provides: "T6's constant 1px border plus inset ring, and the measured 98.67-against-96.66 that the selection scale must not reintroduce"
  - phase: 22-01
    provides: "T8's SkyPaneLivePreview.refresh() and the Cancel-restore browser check, both of which the crossfade had to survive"
  - phase: 21-05
    provides: "theme-preview.js's card-scoped rewrite (R-11) and its standing no-timer/no-network/no-state rule"
provides:
  - "a selection transition on the BASE rule of .theme-chip, .theme-chip__body and .runway-card, animating the live :has(input:checked) treatment and the --selected fallback from one declaration, with the feature-query block count still exactly one"
  - "transform: scale(1.02) on both halves of each parity pair, cleared by both saved-but-not-live rules — a selection signal that changes no layout box"
  - "ONE @starting-style entrance on .lightbox[open] serving BOTH dialogs, with display/allow-discrete and ::backdrop animation deliberately absent"
  - "the live theme preview's crossfade: one class in style.css, driven from theme-preview.js by transitionend plus the image's own load/error, with no timer and no second image layer"
  - "a fix for a ~500px desktop layout shift on Home that predates this plan: the frame picture now reserves its final box at 1280px as well as at 360px"
  - "one skeleton rule, two surfaces, painted as the image's own background so it is hidden by the image's own arrival with no script and no class"
  - "test_browser_ux.py +3 checks (54), test_config_page.py +1 (240), test_view_pages.py +1 (153), plus two pre-existing checks retargeted in place"
affects: [23-11]

tech-stack:
  added: []
  patterns:
    - "animate live :has() state from OUTSIDE its feature query: a transition is a property of the element, not of the state, so one declaration on the base rule reaches both the live treatment and the server-rendered fallback and no second @supports block is ever needed"
    - "measure LAYOUT boxes with offsetWidth/offsetHeight/offsetLeft/offsetTop and VISUAL boxes with getBoundingClientRect(), and say which one an assertion is about — the difference is exactly what makes a transform-based selection signal provably free of T6"
    - "prove a layout-shift fix by HOLDING the real image request through a route handler, measuring, releasing, and measuring again — never by racing the network and hoping"
    - "an event-driven state machine that waits on transitionend must also ask whether a transition will actually run; a class removed and re-added without an intervening style recalculation transitions nothing and the wait never ends"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/pages/config_page.py
    - companion/test_config_page.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "THE DECISION THAT MATTERED MOST: the selection scale is a transform, and the existing T6/B9 browser check was taught the difference between a layout box and a visual box rather than being loosened. getBoundingClientRect() reports the box AFTER transforms, so a resting scale(1.02) made that check's three-equal-widths assertion fail by 1.9px and its equal-tops assertion fail by ~1px — on a build that is CORRECT. The tempting fixes were both wrong: shrinking the scale until it squeaked under the tolerance would have been passing by luck, and deleting the assertion would have retired the check T6 was closed with. Instead the read neutralises transform (and transition, or it would catch the 180ms unwind mid-flight) and the check now ALSO asserts that exactly one of the three cards really is scaled — so the neutralisation is only ever legitimate while the scale genuinely exists. The new chip check measures offset* throughout, which is transform-independent by definition."
  - "The transition is declared on the base rules and the ONE @supports selector(:has(*)) block declares no transition at all, with both facts asserted inside a SINGLE check function so that moving one inside fails exactly once rather than twice. The stylesheet says why in as many words at the declaration site, because the next person to touch this will reach for a second feature query."
  - "The dialog entrance is one-directional: opening animates, closing is instant, and `display`/`allow-discrete` is banned by a harness check rather than by a comment. 23-08 already made this trade for the Flights detail row; a modal raises the stakes, because a <dialog> that has not reached display:none is an invisible sheet in the top layer. The mutation proved the check's value in an unexpected way — with allow-discrete added, the viewport-centre hit test came back FALSE (the closed dialog had left the top layer and sat in normal flow, away from the centre) while `display: block` and a 307,965px2 box both caught it. A hit test alone would have passed the defect."
  - "::backdrop is deliberately not animated. The global reduced-motion override matches `*, *::before, *::after`, which are element selectors; ::backdrop is none of them, exactly as this file already records for the view-transition pseudo-element tree. An animated backdrop would be motion a reduced-motion visitor cannot switch off."
  - "The crossfade is a single-element dissolve, not a second image layer, and it is driven by events rather than by a timer — theme-preview.js's own standing rule. The src swap therefore lands one var(--motion-fast) after the click, which is why 22-01's Cancel/T8 assertions were retargeted in place from a synchronous read to a bounded wait_for_function. The contract those assertions own (the preview follows the edit; Cancel restores it) is unchanged; only the instant it is read at moved."
  - "The skeleton does NOT shimmer, and this is a deviation from the plan's own behaviour bullet recorded rather than quietly absorbed. See 'Deviations' below: the placement that makes a CSS-only skeleton auto-hide is the placement that makes a pulse breathe the decoded picture forever."
  - "aspect-ratio: 3 / 4 is declared explicitly on the frame picture rather than left to the width/height attributes. It makes the reservation a guarantee instead of a coincidence (the box no longer depends on the ratio of whatever bytes arrive), and because this file's universal reset makes every box border-box, a declared ratio applies to the BORDER box, which is what makes the desktop width resolve to exactly the 60vh cap rather than 60vh minus the hairline."
  - "The browser fixture's 8x8 stand-in render became 600x800 — the size Home's own <img> declares. An image whose loaded ratio is 1:1 against a 3:4 promise makes a layout-shift measurement meaningless, and the one fixture in this repository that a browser measures that shift against cannot be the one whose proportions are wrong."

patterns-established:
  - "When a plan's visual change breaks an existing geometric assertion, ask which BOX the old assertion was about before touching its tolerance. A tolerance widened to accommodate a correct change is a tolerance that will no longer catch the defect it was written for."
  - "A check that neutralises something in order to measure past it must, in the same breath, assert that the thing it neutralised is really there. Otherwise the neutralisation quietly converts the check into one that also passes when the feature is gone."
  - "A layout-shift assertion needs a floor on the reserved box as well as an equality: a collapsed box equals a collapsed box, and that is exactly how the check would have passed on the defect it found."

requirements-completed: []

duration: ~3h30m
completed: 2026-09-13
---

# Phase 23 Plan 10: D3's remainder Summary

**Selecting a chip or a card now answers with a scale and a wash that fades in
without moving a single layout box; the live preview crossfades and settles on
the theme you actually chose, even when Cancel interrupts it mid-fade; both
dialogs arrive through one `@starting-style` rule and leave without a trace; and
Home's frame picture — which turned out to reserve nothing at all at 1280px and
jumped ~500px on every desktop load — now holds its place before it arrives. The
app's most delicate cascade region is byte-for-byte as it was, and the
`@supports selector(:has(*))` block count is still exactly one.**

## Performance

- **Duration:** ~3 h 30 m
- **Tasks:** 3/3
- **Commits:** 6 (3 test, 3 feat)

| Commit    | What                                                          |
| --------- | ------------------------------------------------------------- |
| `f784b6a` | test: selection answers, and the one feature query stays one   |
| `902a897` | feat: selection answers, and the one feature query stays one   |
| `3875e12` | test: the preview crossfade and both dialog entrances          |
| `2251824` | feat: the preview crossfade and both dialog entrances          |
| `1c692c6` | test: two images hold their place before they arrive           |
| `a8e8437` | feat: two images hold their place before they arrive           |

## Re-derived check counts (obtained by RUNNING, never by arithmetic)

| Harness                          | Before | After | Delta |
| -------------------------------- | ------ | ----- | ----- |
| `companion/test_config_page.py`  | 239    | 240   | +1    |
| `companion/test_view_pages.py`   | 152    | 153   | +1    |
| `companion/test_browser_ux.py`   | 50     | 54    | +4    |
| `companion/test_companion_app.py`| 291    | 291   | 0     |
| `companion/test_status_pages.py` | 287    | 287   | 0     |
| `companion/test_contrast_check.py` | 43   | 43    | 0 (M/M) |

`test_browser_ux.py`'s +4 is +1 for Task 1 (chip selection), +2 for Task 2
(dialogs, crossfade) and +1 for Task 3 (skeletons). Two further checks in that
file were extended IN PLACE with no count change: the three-runway-card T6/B9
measurement, and 22-01's Cancel/T8 preview restore.

## Criterion counts

| Criterion | Value | Note |
| --------- | ----- | ---- |
| `grep -c '@supports selector(:has(\*)) {'` | **1** | unchanged, the plan's single largest risk |
| `grep -v '^ *[*/]' \| grep -c 'prefers-reduced-motion: reduce'` | **2** | unchanged; no per-rule block added anywhere |
| `grep -c '@keyframes'` | **4** | unchanged; the skeleton spends none |
| `grep -cE '=>\|\blet \|\bconst \|innerHTML' theme-preview.js` | **0** | still ES5-safe |
| coverage | **93%** | ≥ 83 |

## The decision that mattered most, and why

**The selection scale is a `transform`, and the existing T6/B9 measurement was
taught the difference between a layout box and a visual box rather than having
its tolerance loosened.**

`getBoundingClientRect()` reports the box *after* transforms. A resting
`scale(1.02)` on the selected runway card therefore made 22-15's still-green
three-equal-outer-widths assertion fail by 1.9px, and its equal-tops assertion
fail by ~1px — **on a build that is correct**, because a transform participates
in no layout at all and no sibling moves.

Two tempting fixes were both wrong. Shrinking the scale until the difference fell
under the existing 1px tolerance would have been passing by luck, and the scale
would have been chosen by a test rather than by the design. Deleting the
assertion would have retired the check T6 was closed with, on the exact axis T6
was about.

What landed instead: the measurement neutralises `transform` for the duration of
the read (and `transition` first, or it would catch the 180ms unwind mid-flight
and measure a value that is neither box), and — this is the part that makes the
neutralisation honest — the same check now asserts that **exactly one of the
three cards really is scaled**. Neutralising a thing you have not proven exists
is how a check quietly becomes one that also passes when the feature is gone. The
new chip check reads `offsetWidth/offsetHeight/offsetLeft/offsetTop` throughout,
which is transform-independent by definition and needs no neutralisation at all.

## Mutations (every new check reverted and proven to fail)

Each mutation was applied to a staged tree, run, and reverted with
`git checkout --`. Every one produced **exactly one** failing check.

1. **Move `.theme-chip`'s transition from the base rule into the feature query.**
   > `.theme-chip must declare the selection transition on its OWN base rule — a transition declared on the base rule animates the property however the state is reached, which is why the live :has() treatment needs no second feature query (D3, 23-10-PLAN.md Task 1)`

2. **Add a `transition` inside the feature query while leaving the base ones in
   place** (the mutation that proves the "no transition inside the block" clause
   is not vacuous — mutation 1 alone is caught by the base-rule clause first).
   > `the ONE @supports selector(:has(*)) block declares a `transition` — it must not. A transition belongs on each selectable surface's BASE rule, where it animates the live :has() treatment and the --selected fallback identically from one declaration; moving it inside the query is the first step toward the second feature-query block Phase 15's D-05 already had retired (D3, 23-10-PLAN.md Task 1)`

3. **Drop the scale from the `--selected` fallback, keeping the live one.**
   > `expected '.theme-chip--selected {' to carry the selection scale (`transform: scale(...)`) — the wash's fade is the primary signal and the scale is its punctuation, and a transform changes no layout box so T6 cannot recur through it`

4. **Give the live-selected chip a `margin-left: 4px`** (a selection signal that
   moves a layout box — the T6 class of defect).
   > `the chip's own LAYOUT box changed on selection: left went from 0 to 4. T6's defect was exactly this (98.67px against 96.66px at 390px); a transform-based scale must change no layout box at all`

5. **Change every `scale(1.02)` to `scale(1)`** (a transform that is present but
   says nothing).
   > `expected the selection transform to SCALE UP (matrix a > 1), got 'matrix(1, 0, 0, 1, 0, 0)'`

6. **Add `display … allow-discrete, overlay … allow-discrete` to the `.lightbox`
   transition** — the mechanism T-23-36 names. Caught twice, source and browser:
   > `the .lightbox transition must NOT carry `display`/`allow-discrete`: a modal that has not reached display:none is an invisible sheet over the page that swallows clicks (T-23-36) …`
   > `/history: expected the closed dialog's display to be 'none', got 'block' — a dialog left displayed after close() is an invisible sheet over the page (T-23-36) (full read {'open': False, 'display': 'block', 'area': 307965, 'hit': False, 'hitTag': 'SPAN.cell-primary'})`

7. **Remove the `@starting-style` block, keeping the transition.**
   > `/history: expected the dialog to be MID-FADE two frames after opening (D3: both dialogs fade and zoom in via @starting-style), got opacity 1 with transition '0.18s, 0.18s' on 'opacity, transform' — a dialog already fully opaque two frames in is the instant open this plan replaces`

8. **Restore `width: auto` on the desktop frame picture.**
   > `/ at 1280px: the UNLOADED image reserves only [2, 2.66] — a collapsed box is the layout shift a skeleton exists to prevent, and it would make the equality below pass for the wrong reason (T-23-39)`

9. **Remove the skeleton gradient.**
   > `/ at 360px: .preview-frame__image paints no skeleton at all while its image is still coming — the reserved box is correct and completely blank`

10. **Disable the crossfade's computed-opacity guard** (`if (false)`), stressed
    14 times through the Cancel-interrupt path:
    > `trial 1 STALL {'src': '/theme-preview/black.png?live=1', 'op': '0', 'cls': 'theme-live-preview__image theme-live-preview__image--swapping'} orig /theme-preview/white.png?live=1` — 4 stalls in 14 runs without the guard, **0 in 14 with it**.

Both Task 2 browser checks were additionally proven RED against the unmodified
app before any implementation existed:
> `/history: … got opacity 1 with transition '0s' on 'all' — a dialog already fully opaque two frames in is the instant open this plan replaces`
> `expected the live preview to be MID-CROSSFADE two frames after the chip was selected, got opacity 1 with transition '0s' on 'all' — a preview still fully opaque two frames in is the CUT this plan replaces, and every other assertion in this check is satisfied by that cut`

## Checks that failed the vacuity question, and what was done

**1. The crossfade check passed on the CUT.** When first written, the "settles on
the correct theme / Cancel restores the saved one" check went green against the
unmodified app — because a preview that swaps instantly also settles on the right
theme at opacity 1. Every assertion in it was satisfied by doing nothing. Fixed
by adding a mid-flight sample: the click and a two-`requestAnimationFrame` read
happen inside one `evaluate`, and the preview must be strictly below opacity 1
two frames in. That sample is what produced the RED quoted above.

**2. The runway T6 check would have passed with the scale gone.** Neutralising
the transform in order to read the layout box makes the check blind to whether
any transform exists. Answered by asserting, in the same read, that exactly one
of the three cards carries a non-`none` computed transform — captured *before*
the override is applied.

**3. The layout-shift equality would have passed on the defect.** `before == after`
is satisfied by `2x2 == 2x2`. Answered with a floor on the reserved box per
surface (100px for the picture, 30px for the compact chip band), plus an
assertion that `naturalWidth` is still 0 when the "before" read is taken — so a
race that let the image resolve early cannot be mistaken for a reservation.

**4. The `.lightbox[open]` rule count read 2 on a correct file.** See "criteria
that did not evaluate as predicted" below.

## Criteria that did not evaluate as predicted (recorded, not adjusted)

**`grep -c '@starting-style'` does not answer the question the plan asks.** The
criterion is "at least 1, and matches the number of dialog entrances declared
(state both numbers)". The raw grep now returns **7**, because five of those
occurrences are prose — 23-01's and 23-08's comments discussing the at-rule, plus
this plan's own. Comment-stripped, the file holds **2** `@starting-style` blocks:
23-08's Flights detail row, and this plan's. Dialog entrances declared: **1**.
Dialogs served by it: **2** (History's `.lightbox` and the Airlines gallery's
`.lightbox--wide` are the same component under two classes). The harness check
asserts the comment-stripped numbers, which are the ones that mean anything.

**`.lightbox[open] {` occurs twice on a correct file**, because the
`@starting-style` block necessarily repeats the selector it starts. The first
version of that assertion demanded 1 and failed on the correct implementation. It
now removes the `@starting-style` blocks before counting, and the message says so.

**The mutation that added `allow-discrete` was NOT caught by the hit test.** The
browser check's viewport-centre `elementFromPoint` returned a `SPAN.cell-primary`
— the closed-but-displayed dialog had left the top layer and sat in normal flow,
nowhere near the centre. `display: block` and a 307,965px² bounding box both
caught it. The hit test is kept (it is the assertion that matches the threat as
stated), but it is no longer the only one, and the finding is recorded here
because a check built on the hit test alone would have passed this defect.

## Deviations from Plan

### 1. [Rule 1 — Bug, found while measuring] Home's frame picture reserved nothing at all on desktop

- **Found during:** Task 3, probing before writing assertions.
- **Issue:** At 360px the picture was already reserved (312 × 415.3 before the
  bytes arrived and after). At 1280px it measured **2 × 2** before and
  **380 × 506** after — the figure went from 51.2px tall to 555.6px. Home's whole
  picture column jumped roughly 500px on every desktop load, and had done since
  the desktop cap was written. The cause is that `width: auto` on an image with
  no content yet leaves it with an intrinsic size of **zero** however well known
  its ratio is: the `width="600" height="800"` attributes supply a ratio, and a
  ratio alone resolves nothing without a definite size in one axis. Mobile
  escaped only because `width: 100%` is definite.
- **Fix:** the desktop rule's `width: auto` becomes
  `width: min(100%, calc(60vh * 3 / 4))` — the same 60vh cap the `max-height`
  states, written as a definite width the ratio can resolve from — and
  `aspect-ratio: 3 / 4` plus `object-fit: contain` are declared explicitly so the
  reservation does not depend on the shape of whatever bytes arrive. Both caps
  are kept as belt-and-braces.
- **Files:** `companion/static/style.css`
- **Commit:** `a8e8437`

### 2. [Rule 1 — Bug, found by a flaky harness run] The crossfade could stall invisible on the discarded theme

- **Found during:** Task 2. The Cancel/T8 browser check failed once, then passed
  on a rerun with no code change. Rather than accept the flake, the interleaving
  was reproduced: **4 stalls in 14 runs**, every one leaving the preview at
  opacity 0 showing the theme the user had just discarded.
- **Issue:** the machine waits on `transitionend`, and a `transitionend` only
  arrives if a transition actually *ran*. It does not run when the image is
  already invisible, nor when the fade class is removed and re-added without the
  browser performing a style recalculation in between — an image `load` event and
  a click landing inside the same frame does exactly that.
- **Fix:** after adding the fade class, `theme-preview.js` reads the **computed**
  opacity; if it is already 0 there is no fade-out left to wait for, so the swap
  happens immediately. 0 stalls in 14 runs after. Pinned structurally in
  `test_config_page.py` because the browser-level reproduction is probabilistic.
- **Files:** `companion/static/theme-preview.js`, `companion/test_config_page.py`
- **Commit:** `2251824`

### 3. The skeleton does not shimmer — a plan behaviour bullet declined, with reasons

The plan asks for "a quiet background treatment that pulses with plan 23-01's
keyframes at the slow token, hidden the moment the image paints". Those two
clauses are in direct conflict, and the conflict is structural rather than a
matter of effort.

The only place a pure-CSS skeleton can live and still auto-hide on load is the
image element's **own background**: `background-image` paints above the element's
`background-color` and below the decoded bitmap, so the arrival of the picture
covers it with no script, no timer and no class. That is the mechanism the plan
itself asks for ("use the image's own load state rather than a timer"). But
`skypane-pulse` cycles **opacity**, and opacity belongs to the element — an
`animation` on this `<img>` would go on breathing the **decoded picture**,
forever, on a page somebody leaves open all day. That is precisely the complaint
23-01's own keyframes comment says a motion budget exists to prevent.

The alternatives were considered and are worse. A pulsing overlay on the
*container* is covered by the image's own opaque backing from the first frame and
is never visible. An overlay *above* the image can never learn that the image
arrived, because CSS has no loaded state to select on. An infinite animation that
keeps running behind a loaded picture is compositor work with nothing to show for
it. And a JavaScript-toggled overlay would need a fourteenth static script, its
own route in `companion/app.py` and its own CSP pin — for a decoration; the
plan's own `files_modified` list omits `app.py`, which reads as the same verdict.

So the sheen is a **static** gradient in this file's existing muted-text
`color-mix` idiom, one rule shared by the two surfaces. It reads as a
placeholder, costs nothing, disappears the instant the picture paints, spends no
keyframes (the file's four stay four) and is trivially correct under reduced
motion. The reasoning is written into `style.css` at the declaration, not only
here.

### 4. Files touched beyond a task's own `<files>` list

Task 1 and Task 2 both carry acceptance criteria beginning "A browser check …",
and `companion/test_browser_ux.py` is listed in the plan's `files_modified` but
in neither task's own `<files>`. It was edited in both commits. Conversely,
`companion/pages/history_page.py` and `companion/pages/airlines_page.py` are
listed in `files_modified` and Task 2 and were **not** touched: both dialogs
already render as `<dialog class="lightbox">`, so the entrance is one CSS rule and
no markup change is needed. `companion/pages/config_page.py` was touched in Task 3
rather than Task 2.

## Plan assumptions that turned out wrong

1. **"the frame picture … reserve[s] their FINAL size" was framed as something to
   confirm.** It was false at 1280px, by ~500px, and had been for some time. The
   plan's instruction to "confirm the reserved box equals the loaded image's box
   by measuring both" is exactly what found it — an inspection would not have.

2. **"The skeleton's shimmer spends plan 23-01's one `@keyframes`."** The file
   holds **four** keyframes blocks, not one (`skypane-pulse`, `skypane-fade-in`,
   `skypane-row-arrive`, `skypane-bar-arrive`), and 23-01's guard bans *duplicate
   names*, not a fifth block. The relevant one would have been `skypane-pulse`;
   see deviation 3 for why it is not spent.

3. **"`@starting-style` is Baseline newly … verified to parse"** — true, and the
   file already contained one, added by 23-08. This plan adds the second, not the
   first.

4. **The chip preview band's inline style.** `config_page.py` rendered
   `style="background:#hex"` — the *shorthand*, which resets `background-image` to
   `none`, and an inline style beats every author rule. The stylesheet's skeleton
   for that band was unreachable until the emitter was changed to
   `background-color`. Same rendered value, same placeholder; the change is
   load-bearing.

5. **The chip's first rendered preview band is the COMPACT variant** (36px, not
   the base 56px) — the Frame colours card's grid comes first in the document.
   The measurement floor was set from that measured number rather than the one
   the base rule states.

6. **Selecting a chip moves the page by 36px, and it is not this plan's doing.**
   23-09's save bar replaces the section's inline fallback Save when it arrives,
   which removes a real 36px above the Frame colours card; every chip measured
   1608 before and 1572 after. The chip check therefore measures positions
   relative to the chip grid, and measures *every* chip in the grid rather than
   only the clicked one.

## Interaction with plan 23-09's file (recorded, as instructed)

`companion/static/dirty-state.js` was **not** edited. Its Cancel handler still
calls `window.SkyPaneLivePreview.refresh()` exactly as before; the entire
adaptation happened on the `theme-preview.js` side, as the plan directed. The
interaction is real though: `refresh()` now enters the crossfade rather than
assigning a src, which is how deviation 2's stall was reachable at all, and is
why 22-01's Cancel assertion moved from a synchronous read to a bounded wait.

## Verification

- `companion/test_config_page.py` → 240/240, both `:has()` block checks green
- `companion/test_view_pages.py` → 153/153
- `companion/test_browser_ux.py` → 54/54
- `companion/test_companion_app.py` → 289/291 (the two documented root-sandbox
  WR-11 FAILs); the motion guard green
- `companion/test_contrast_check.py` → 43/43 (M/M); no colour moved
- `companion/test_status_pages.py` → 286/287 (the documented `anomaly_active()`
  root-sandbox FAIL); style.css's zero-stray-terminator structural guard green
- `scripts/run-all-tests.sh` → failing set is **exactly** the 5 baseline names
  (4 × WR-11 read-only, 1 × `anomaly_active()`), in the same 3 harnesses as the
  pre-plan baseline; coverage **93%**
- `ruff check .` → clean

### The 5 baseline failures, by name (verified unchanged)

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … (WR-11)`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created … (WR-11)`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)`
5. `anomaly_active() runs on every page render and must never raise …`

## Human check (folded into 23-11's sweep)

Click through several theme chips and watch the selection answer and the preview
cross-fade; open and close both dialogs; hard-reload Home on a throttled
connection at a desktop width and confirm nothing jumps when the picture arrives
(this is the one with a measured before/after); repeat the lot with reduce-motion
on.

## Self-Check: PASSED

All seven modified/created files exist on disk; all six commit hashes resolve in
`git log --oneline --all`.
