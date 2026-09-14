---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 01
subsystem: companion-controls
tags: [no-js-floor, static-script, css-gate, battery-estimate, executable-contract]
requires:
  - "companion/static/dirty-state.js's delegated document-level change listener (22-01)"
  - "companion/static/style.css's `.js` class, set by nav-dropdown.js (UXA-02)"
  - "companion/static/style.css's `.copy-btn` 22px/-11px/44px hit-area synthesis (06.6.4 D-02)"
  - "companion/battery.py::battery_fraction (24-01)"
  - "server/history_db.py::daily_battery_averages row contract (22-06)"
provides:
  - "companion/static/value-controls.js (the phase's ONE new script)"
  - "companion/app.py::VALUE_CONTROLS_SCRIPT_ROUTE"
  - "companion/layout.py::VALUE_CONTROLS_SCRIPT_SRC"
  - "companion/layout.py::VALUE_CONTROL_* (ten seam attributes) + VALUE_CONTROL_TEXT_TOKEN"
  - "companion/layout.py::JS_GATE_CLASS"
  - "companion/static/style.css::.js-gate / .js .js-gate"
  - "companion/static/style.css::.control-hit-area (+ ::before, .icon)"
  - "companion/static/style.css::.value-control / __track / __handle"
  - "companion/battery.py::battery_life_estimate + the five LIFE_TREND_* states"
  - "companion/test_companion_app.py::_NO_JS_CONTROL_REGISTRY"
affects:
  - "25-03 … 25-07 (each adds markup + one registry row; none touches app.py, layout.py or the script pin)"
  - "25-08 (the phase gate)"
tech-stack:
  added: []
  patterns:
    - "a static script is a library with a guard clause and no subject yet"
    - "the .js gate hides by default and reveals under .js, never the reverse"
    - "the gate class goes on the gated element ITSELF, so nesting cannot be got wrong"
    - "a contract guard proves itself against deliberately-wrong fixtures before an empty registry is trusted"
key-files:
  created:
    - companion/static/value-controls.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/static/style.css
    - companion/battery.py
    - companion/test_companion_app.py
decisions:
  - "the save bar is woken by dispatching a bubbling `change` on the input, which is dirty-state.js's already-public delegated listener — not by moving the control into dirty-state.js"
  - "no load-time DOM write at all: the initial control position is server-rendered, which is what makes the scripts-blocked render correct rather than merely present"
  - "the .js gate reveals through `display: var(--js-gate-display, block)`, so a consumer picks its display without re-deciding the gate's direction"
  - "the battery-life estimate reports five NAMED states; only `falling` carries a number, and no per-wake energy cost is assumed anywhere"
  - "the no-JS contract guard proves itself against four fixtures built from real group-builder output, so an empty registry still demonstrates a working machine"
metrics:
  duration: ~4h
  completed: 2026-09-14
---

# Phase 25 Plan 01: The seam five controls share, and the machine that judges them Summary

One new script with its route, shell registration and the script pin moved once; a
`.js`-gated CSS vocabulary that makes "does not render without script" a property of the
stylesheet; the battery-life arithmetic added to the one estimator; and a no-JS control
contract that fails on a wrong control, proven by five recorded mutations. No control was
built.

## The decision that mattered most

**How a separate script wakes the save bar.** The plan named this as the one thing to
resolve explicitly, and it was right to: a control that changes a value without waking the
save bar looks saved and is not, and the user loses the edit with no error anywhere.

`dirty-state.js`'s own quiet-hours preset handler reaches its bar by calling a private
`notifyDirty()` — a closure inside that file's IIFE, unreachable from another file. Its own
comment says it chose that over dispatching a synthetic event because "constructing one in
an ES5-safe way is awkward and unnecessary when the handler that needs to react lives in
this very same file". That reasoning does not transfer, because the handler no longer lives
in the same file.

The resolution is not a new mechanism: `dirty-state.js` already registers **delegated
document-level `change` and `input` listeners filtered to `e.target.form === form`**
(`companion/static/dirty-state.js:421-430`). That delegation is 22-01's own fix for the B1
defect and is the only reason a `form=`-attached settings field reaches the bar at all. A
bubbling `change` dispatched on the input `value-controls.js` just wrote is, to
`dirty-state.js`, indistinguishable from the user typing in that input — which is exactly
the semantics wanted. **`dirty-state.js` needed no change of any kind.**

The alternative — moving a dial and a slider into `dirty-state.js` — would have put two
page-specific controls inside the file that owns the app's unsaved-edits guard.

It is pinned from both sides, together with `dirty-state.js`'s `e.target.form` filter, and
the event name is read out of **both** construction sites rather than a named constant, so
the modern and legacy branches are also pinned equal to each other.

## Baselines, measured on this tree before editing

| Measurement | Before | After |
|---|---|---|
| `ls companion/static/*.js \| wc -l` | 16 | 17 |
| deferred `<script src=` on the authenticated shell | 14 | **15** |
| deferred `<script src=` on the login shell | 1 | 1 (unchanged) |
| `@supports selector(:has(*))` **blocks** (comment-stripped, on the brace) | 1 | 1 |
| `@keyframes` (comment-stripped) | 4 | 4 |
| `@media (prefers-reduced-motion: reduce)` (comment-stripped) | 2 | 2 |
| `companion/test_companion_app.py` checks | 300 | **313** |
| `companion/test_i18n.py` checks | 24 | 24 |
| `companion/test_status_pages.py` checks | 302 | 302 |
| `companion/test_config_page.py` checks | 240 | 240 |
| `companion/test_contrast_check.py` checks | 49 | 49 |

`EXPECTED_CHECK_COUNT` was re-derived **by running** after each task and appended as a new
assignment: 300 → 306 (Task 1, +6) → 309 (Task 2, +3) → 311 (Task 3, +2) → 313 (Task 4, +2).
Three pre-existing checks were retargeted in place with no count contribution: the
deferred-script pin (14 → 15), the battery one-home guard (now also catching a second
battery-**life** computation), and nothing else.

## What was built

### Task 1 — one script, one route, one pin move

`companion/static/value-controls.js` steers a continuous value: it reads a min, a max, a
step, a field name and a form id off data attributes on a wrapper, clamps and rounds, writes
into the native input the form already posts, dispatches the bubbling `change`, and paints
`aria-valuenow` plus a `--value-fraction` custom property. D17's dial and D18's slider differ
only in `data-value-geometry`.

Three properties worth naming:

- **It holds no value.** Exactly one assignment to a `.value` in the whole file, and the
  control's current state is read back off that same input. Pinned by shape, not by reading.
- **It writes no copy.** `aria-valuetext` is filled from a server-rendered, already-translated
  template on the wrapper; with no template, no `aria-valuetext` is written at all rather than
  an English sentence invented in the script. `companion/i18n_fr/common.py` therefore needed
  **no change** — every literal the file declares is a hyphenated attribute name, a custom
  property or a token with no letters, all of which `test_i18n.py` Check 6 excludes by rule.
  This is recorded because the plan listed that file in `files_modified` and it was not touched.
- **It writes nothing at load.** No `DOMContentLoaded`, no init pass, no class on `<html>`.
  The initial position of every control is server-rendered from the saved value, which is
  what makes the scripts-blocked render correct rather than merely present.

The ten `VALUE_CONTROL_*` seam attributes are defined in `layout.py` so a page module never
types one, and a real GET asserts the served script body names all nine that it consumes.

### Task 2 — the `.js` gate and the shared vocabulary

`.js-gate { display: none }` / `.js .js-gate { display: var(--js-gate-display, block) }`.
`display: none` specifically: `visibility` and `opacity` both leave a focusable ghost a
keyboard user can tab into with scripts blocked. The `var()` indirection means a consumer
sets `--js-gate-display: flex` on its own rule and never writes a `.js`-scoped selector, so
the gate's direction is decided once rather than five times.

`.control-hit-area` joins `references/control-density.md`'s **RELOCATED** touch-target
category as the third consumer of one register entry — every value lifted verbatim from
`.copy-btn`, and the harness asserts them **equal, declaration by declaration**, with the 44
recomputed from the declared box and inset rather than restated.

`.value-control` / `__track` / `__handle` carry only genuinely shared declarations. There is
deliberately **no `__readout` class**: a printed value wears `.time-value`, this file's one
numeric-value role (C5's consolidation of four competing treatments), and a fourth numeric
voice would be reopening C5.

**No focus rule**, stated in a comment: the global `:focus-visible` floor already paints a
handle, which is a real `<button>`.

### Task 3 — the battery-life estimate

`battery_life_estimate(rows, current_wake_interval_s, proposed_wake_interval_s)` in
`companion/battery.py`, returning `trend`, `latest_mv`, `observed_span_days`, `mv_per_day`,
`days_remaining` and `relative_factor`.

Five named states, never an overloaded `None`: `no-reading`, `not-enough-history`, `rising`,
`flat`, `falling`. Only the last carries a number. No per-wake energy cost is assumed
anywhere, because this project has never measured one (DEVICE-05's discharge run is still
deferred).

Two observation floors, both now pinned from the opposite extreme (see mutations 32–33):
`LIFE_MIN_OBSERVED_SPAN_DAYS = 2` (a one-day delta between two daily *averages* is inside
this series' own noise) and `LIFE_MIN_OBSERVED_DROP_MV = 10` (a 1 mV fall over three days
divides out to roughly five years, which a reader takes as a promise).

`relative_factor` is deliberately separable and always available — the ratio of two cadences
and nothing else — which is what lets D18's gauge say something true on day one. Its
docstring states precisely what it is **not**: a multiplier on the lifetime, which would only
be the same number if every joule this device spends went into waking.

### Task 4 — the executable no-JS control contract

`_NO_JS_CONTROL_REGISTRY` is a module-level registry each of 25-03…25-07 appends exactly one
row to. Per row the guard asserts the named field is present in the group builder's own
returned string, is a native `<input>`/`<select>`, is really associated with the form that
posts it, and that **every** element carrying the control's wrapper attribute also carries
`layout.JS_GATE_CLASS`.

Two design decisions inside it:

- **The gate class goes on the gated element itself, never an ancestor.** "This wrapper is
  somewhere inside a gated ancestor" cannot be checked from rendered markup without parsing
  the whole tree; "this wrapper carries the class" is exact. Making them one element removes
  the nesting mistake rather than detecting it.
- **Form association is declared, never guessed.** Both idioms this app uses are legitimate
  (`form=` cross-DOM attachment, and rendering inside the form). The enclosing case is
  verified against a **real authenticated render of the page**, not against the builder's own
  string — see "criteria that did not evaluate as predicted" below.

Zero controls are registered today. The guard is still non-vacuous, because it runs its whole
machine against four fixtures built from **real** `config_page.wake_interval_group()` output:
one correct control it must accept, and three it must reject.

## Mutations — every new check reverted and proven to fail

All mutations were staged first (`git add`), applied, run, and reverted with
`git checkout-index -f --`. `__pycache__` was cleared before every run.

### Task 1

| # | Mutation | Quoted failure |
|---|---|---|
| 1 | a second `.value` assignment (`wrapper.value = value`) | `expected exactly ONE assignment to a `.value` in value-controls.js (the write into the native input the form posts), found 2: ['field.value =', 'wrapper.value ='] — a second one is a parallel copy of a value this file is forbidden to hold` |
| 2 | legacy branch dispatches `input`, modern branch `change` | `value-controls.js constructs 'change' in its modern branch and 'input' in its legacy branch — one of the two browsers would never wake the save bar` |
| 3 | notification constructed non-bubbling | `expected value-controls.js's notification event to be constructed as a BUBBLING event — dirty-state.js listens on `document`, so an event that does not bubble never reaches it` |
| 4 | `VALUE_CONTROLS_SCRIPT_ROUTE` drifted from the src | `value-controls script route drift: '/static/value-controls.js' vs '/static/value-control.js'` (plus `expected 200 …, got 404` from both route checks) |
| 5 | `VALUE_CONTROL_TRACK_ATTR` renamed on the Python side only | `expected the served body to name 'data-value-rail' — the registration seam 25-04 and 25-05 opt into by attribute, so a rename on the Python side alone is a control that renders and steers nothing` |
| 6 | shell registration removed | `expected exactly 15 deferred <script src= tags before </body>, got 14` and `expected exactly one '<script src="/static/value-controls.js" defer></script>', got 0` |

The plan's RED phase for Task 1 was recorded separately: with the script moved aside, all six
new checks failed (404, `FileNotFoundError`, `AttributeError: module 'companion.layout' has no
attribute 'VALUE_CONTROLS_SCRIPT_SRC'`).

### Task 2 — every CSS property added was mutated

| # | Mutation | Quoted failure |
|---|---|---|
| 7 | `.js-gate` uses `visibility: hidden` | `the default `.js-gate` rule declares display: None — it must be `none`, so the gated content is out of the LAYOUT and out of the TAB ORDER with scripts blocked. visibility/opacity leave a focusable ghost.` |
| 8 | gate direction inverted | `the default `.js-gate` rule declares display: 'var(--js-gate-display, block)' — it must be `none` …` |
| 9 | a second, reversed gate rule added (`.js .later-gate { display: none }`) | `` `.js .later-gate` hides its gated content under the `.js` class — the gate runs the other way round: hidden by default, revealed under `.js`, because the reverse flashes a dead control on every load and shows it permanently when a script fails `` |
| 10 | box 22px → 20px | `` `.control-hit-area` declares width: '20px' but `.copy-btn` declares '22px' — the shared class reuses the registered values VERBATIM rather than re-choosing them `` |
| 11 | `::before` inset −11px → −10px | `` `.control-hit-area::before` declares inset: '-10px' but `.copy-btn::before` declares '-11px' `` |
| 12 | glyph 14px → 16px | `` `.control-hit-area .icon` declares width: '16px' but `.copy-btn .icon` declares '14px' `` |
| 13 | `padding: 0` → `2px` | `` `.control-hit-area` declares padding: '2px' but `.copy-btn` declares '0' … `` |
| 14 | `background: transparent` → `inherit` | `` `.control-hit-area` declares background: 'inherit' but `.copy-btn` declares 'transparent' … `` |
| 15 | `align-items` dropped | `` `.control-hit-area` declares align-items: None but `.copy-btn` declares 'center' … `` |
| 16 | `justify-content` dropped | `` `.control-hit-area` declares justify-content: None but `.copy-btn` declares 'center' … `` |
| 17 | `border: none` → `0` | `` `.control-hit-area` declares border: '0' but `.copy-btn` declares 'none' … `` |
| 18 | `.value-control` `touch-action` dropped | `` `.value-control` declares touch-action: None — it must be `none`, or the browser's own panning gesture claims the drag and the control is immovable on every touch device `` |
| 19 | `.value-control__handle` `touch-action: auto` | `` `.value-control__handle` declares touch-action: 'auto' — it must be `none` … `` |
| 20 | `.value-control__track` `position: static` | `` `.value-control__track` must be `position: relative` — it is the positioning context an absolutely-placed handle is measured against … `` |
| 21 | `.value-control__handle` `position: relative` | `` `.value-control__handle` must be `position: absolute` — a handle placed in normal flow cannot be moved by the --value-fraction the script writes `` |
| 22 | `::before` `content` dropped | `` `.control-hit-area::before` declares content: None but `.copy-btn::before` declares '""' — without all three the hit area is not synthesized at all `` |
| 23 | `::before` `position: relative` | `` `.control-hit-area::before` declares position: 'relative' but `.copy-btn::before` declares 'absolute' … `` |
| 24 | `var()` fallback dropped from the reveal | `` the `.js .js-gate` reveal declares display: 'var(--js-gate-display)' with no fallback — a consumer that never sets --js-gate-display would resolve to nothing and the gate would never open `` |

`.control-hit-area`'s `height` and `border-radius` are covered by the same declaration-equality
loop as `width` and `padding` (mutations 10 and 13 exercise the loop itself).

### Task 3

| # | Mutation | Quoted failure |
|---|---|---|
| 25 | rising series divided naively | `a rising series returned days_remaining=-14 — a charged device has a positive slope and there is no honest lifetime to divide out of it; the answer must be None, never a negative or an infinite number` |
| 26 | `max(0.0, …)` floor removed | `a series that has already fallen below the empty endpoint reported days_remaining=-3 — the floor is zero, never a negative lifetime` |
| 27 | the two unknowns given the same value | `LIFE_TREND_NO_READING and LIFE_TREND_NOT_ENOUGH_HISTORY are the same value ('no-reading') — 'we have no battery reading' and 'we have a reading but cannot see a trend yet' are two different sentences a caller has to be able to tell apart` |
| 28 | row order trusted rather than sorted | `a rising series must report 'rising', got 'not-enough-history'` |
| 29 | factor inverted to `current/proposed` | `battery_life_estimate(empty) returned relative_factor=0.5 for 900s -> 1800s — the factor is arithmetic on two cadences and must be available in every shape …` |
| 30 | bool cadence accepted | `a current cadence of True produced relative_factor=1800.0 — an unusable cadence has no factor, and a guessed one is a sentence the user acts on` |
| 31 | a `None`-reading row made fatal instead of dropped | `a series whose newest row has a None reading must drop that row and report 'not-enough-history' off what is left, got 'no-reading'` |
| 32 | `LIFE_MIN_OBSERVED_SPAN_DAYS` 2 → 1 | `a 150 mV fall measured across a ONE-day span reported 'falling' (days_remaining 3) — below LIFE_MIN_OBSERVED_SPAN_DAYS the answer is the named state, because a single day's delta between two daily averages is inside this series' own noise` |
| 33 | `LIFE_MIN_OBSERVED_DROP_MV` 10 → 0 | `battery_life_estimate(two-flat-rows) raised ZeroDivisionError('float division by zero')` |

### Task 4 — the two mutations the plan required, plus three more

| # | Mutation | Quoted failure |
|---|---|---|
| A | a control registered against an input name nothing renders | `the wake-interval slider (25-05-PLAN.md Task 1): no element named 'wake_interval_seconds' appears in its group builder's own output — the control's value must be held by an input the SERVER renders on every render, or there is no way to save it with scripts blocked` |
| B | a gated wrapper moved outside the gate | `the wake-interval slider (25-05-PLAN.md Task 1): an element carries data-value-control OUTSIDE the 'js-gate' gate — <div class="value-control" data-value-control>. A script-only affordance rendered without the gate shows permanently whenever the script does not run, which is the control that renders and does nothing` |
| C | `JS_GATE_CLASS` renamed on the Python side only | `layout.JS_GATE_CLASS is 'js-only' but companion/static/style.css declares no `.js-only` selector on a boundary — the class a page module writes and the rule that hides it are two halves of one contract` |
| D | the guard's own gate assertion disabled | `the contract ACCEPTED a wrapper rendered outside the gate — the guard is vacuous and every control this phase registers would pass it` |
| E | the guard's own native-tag assertion disabled | `the contract ACCEPTED a value held by a div instead of a native input — the guard is vacuous and every control this phase registers would pass it` |

Both required mutations were reverted and the guard is green afterwards. D and E are the
interesting ones: the fixtures catch the **guard itself** becoming vacuous, which an empty
registry never could.

## Checks with no RED phase — said plainly, not manufactured

Three checks added here guard invariants that already held, so there is nothing they could
have failed against before the code existed:

1. **exactly one `@supports selector(:has(*))` block** (Task 2) — a regression guard.
2. **`companion/battery.py` imports nothing from `companion.pages` and nothing from `server`**
   (Task 3) — the module's docstring has claimed this since 19-01 and nothing has ever
   verified it. A docstring has never stopped an import.
3. **the whole of Task 4** — it adds only measurement. Its non-vacuity is demonstrated by
   mutation instead (A–E above).

## Vacuity questions asked, and what changed as a result

Four checks failed the "what would a *wrong* implementation do?" question and were
strengthened before being committed:

1. **The reveal rule's `var()` fallback.** The first draft asserted only that
   `.js .js-gate`'s `display` was neither absent nor `none`. Dropping the `, block` fallback
   would leave `display: var(--js-gate-display)` — which passes that test and resolves to
   nothing for every consumer that does not set the property, i.e. a gate that never opens.
   Now asserted explicitly (mutation 24).
2. **The `::before` was under-asserted.** Only `inset` was compared. Without `content` the
   pseudo-element is never generated at all, and without `position: absolute` the inset has
   nothing to offset from — either omission leaves a 22 px target while every number in the
   file still reads 44. Both added (mutations 22–23).
3. **`.control-hit-area`'s property list was a sample, not the set.** `border`, `background`,
   `align-items` and `justify-content` were unchecked and could have drifted from `.copy-btn`
   silently, which is exactly what "reused verbatim" is meant to prevent. All added
   (mutations 14–17).
4. **Both battery observation floors were load-bearing and unchecked.** Every series shape in
   the first draft spanned either six days or zero, so lowering `LIFE_MIN_OBSERVED_SPAN_DAYS`
   to 1 failed nothing at all, and the drop floor was never exercised either. Two shapes were
   added from the *opposite* extreme — a 150 mV fall across one day, and a 1 mV fall across
   three — which is the "assert the floor, not only the ceiling" rule applied to a threshold
   rather than a coordinate (mutations 32–33). Mutation 33 also showed the drop floor is
   load-bearing for **totality**, not only honesty: without it a perfectly flat series divides
   by zero.

`.value-control__track { position: relative }` and `.control-hit-area .icon` were both
**load-bearing but unchecked** in the first draft and are now asserted (mutations 20, 12).
Nothing added in this plan measured **inert**.

## Criteria that did not evaluate as predicted

Recorded, not quietly adjusted.

1. **The plan's `@supports` grep is wrong on this tree.** Task 2's acceptance criterion says
   `grep -c '@supports selector(:has(\*))' companion/static/style.css` is exactly 1. It
   returns **5**: the block at `style.css:2883` plus four comment paragraphs at :41, :2607,
   :2645 and :2868 that quote the at-rule while explaining the rule. This is standing
   constraint 4 in its other direction — prose satisfying a prose-blind scan. The invariant is
   real; the measurement had to move to comment-stripped source **and** the opening brace,
   where the count is 1. The check is written that way and says why.

2. **The plan located the global focus floor in the wrong place.** Task 2's action says the
   focus treatment "must be the global focus floor already inside the one `@supports` block".
   It is not: the global floor is the top-level rule
   `a/button/input/select/summary:focus-visible` at `style.css:970-976`, outside every feature
   query. What lives *inside* the `@supports` block is the **delegated** focus ring for cards
   wrapping a visually-hidden radio (`.runway-card:has(input:focus-visible)`) — a different
   mechanism for a different markup shape. The plan's *instruction* was right (add no focus
   rule) and is followed; only its citation was wrong. The comment in `style.css` names the
   correct location and explains the distinction so the next reader does not go looking in the
   feature query.

3. **Task 4's form-association criterion could not be met against the builder alone.** The
   criterion asks that the named input "carries either an enclosing form or an explicit `form=`
   association", asserted on the builder's return value. `quiet_hours_group()` does carry
   `form="settings-form"`, but `wake_interval_group()` — D18's own subject — carries **neither**:
   it is rendered *inside* `<form id="settings-form">` by the page, and its builder's output
   contains no form at all. A string assertion on the builder would have failed every
   enclosing-form control, or been weakened to nothing. The guard therefore makes the
   association a **declared** field (`form_assoc: "attribute" | "enclosing"`) and verifies the
   enclosing case against a real authenticated render of the declared route, which is strictly
   stronger than the criterion asked for.

4. **`companion/i18n_fr/common.py` was listed in `files_modified` and was not touched.** The
   script produces no user-visible literal at all — `aria-valuetext` comes from a
   server-rendered translated template — so there was no French sibling to add.
   `test_i18n.py` passes at 24/24 unchanged.

5. **Two of my own mutations initially "failed nothing", and that was my harness's fault, not
   a hole.** Mutations 32–33 were first applied with a `str.replace(..., 1)` that hit the
   *comment* quoting `LIFE_MIN_OBSERVED_SPAN_DAYS = 2` rather than the assignment eleven lines
   below it. The silence was the signal: both were expected to fail. Re-applied against the
   real assignment lines, both fail as shown. Recorded because a mutation that silently
   mutates a comment is a mutation test that proves nothing while looking rigorous.

## Plan assumptions that turned out wrong

- **`battery.py` is not 38 lines.** The plan's `<interfaces>` said so and told me to re-read
  rather than assume; Phase 24 had already grown it to 119 lines with `battery_fraction()` and
  `LOW_BATTERY_DISPLAY_MV`. Extended, as instructed.
- **`battery.py`'s own docstring forbade this task.** Phase 24 left the paragraph *"Deliberately
  NOT added here: a 'battery life remaining' estimate … it needs a discharge model this project
  has no data to justify."* That reasoning was right about the **model** and wrong about the
  **conclusion**: what it ruled out was an estimate built on an assumed per-wake energy cost,
  which `battery_life_estimate()` is not. The paragraph is corrected **in place** with that
  distinction spelled out, rather than deleted.
- **`page_shell()`'s script list is not a loop.** Registering the fifteenth script required
  inserting a fifteenth `'<script src="%s" defer></script>\n'` line into the shell's
  `%`-format template as well as appending to the tuple. The first attempt appended to the
  tuple alone and produced `TypeError: not all arguments converted during string formatting`
  across 30 checks — a loud, immediate failure rather than a silent one, but worth naming for
  the next plan that touches the shell.

## Files touched outside `files_modified`, and why

None. Every file changed is in the plan's `files_modified`. `companion/layout.py` carries one
addition the plan did not anticipate — `JS_GATE_CLASS` — because Task 4's guard has to read
the gate class from somewhere a page module can also read it from, and a page module typing
`"js-gate"` by hand is the rename-drift the pin exists to prevent. `layout.py` is in
`files_modified`; the *task*-level file list for Task 4 named only the harness.

`companion/test_browser_ux.py` was read and never written — 25-02 owns it and its work is
green (178.2 s, PASS).

## One thing 25-04 and 25-05 must not assume

25-02's own `deferred-items.md` entry measured `.copy-btn`'s **real** hit area inside a
Flights detail row at **34×26, not 44×44** — the `::before` is genuinely reaching the hit test,
but neighbours inside `.flight-detail-row__grid` cover its outer edge. The same class measures
45×45 in the row-toggle's position, so the rule is fine and the *placement* is what eats it.

`.control-hit-area` reuses exactly those values, and the check in this plan asserts the
**declared** arithmetic. A control plan adopting it must still measure the result with 25-02's
`_assert_hit_target()` in its own container: 44 is what the rule synthesizes, not necessarily
what the browser resolves.

## Properties found inert

None. Every declaration added to `style.css` in this plan fails a check when mutated
(mutations 7–24). They are nonetheless **load-bearing but not yet consumed** — no markup in
this app carries `.value-control` or `.js-gate` today, by design — so their browser-level
effect is asserted by 25-02's `_assert_js_gate()` / `_assert_hit_target()` once a control plan
gives them a subject.

## Deviations from plan

### Auto-fixed issues

**1. [Rule 1 - Bug] My own stylesheet comment broke an existing guard in another harness**

- **Found during:** Task 2
- **Issue:** The first draft of the `.js-gate` comment quoted `19-10's .js [data-static-save-fallback] rule`
  as the cautionary example. `companion/test_config_page.py` locates that rule by the **first
  occurrence** of the attribute literal in `style.css` and reads a 120-character window after
  it, and separately fails if the exact string `.js [data-static-save-fallback]` appears
  anywhere in the file. My paragraph sat ~9 000 lines earlier than the rule and satisfied both.
  `config-page: 239/240`.
- **Fix:** the paragraph names the rule without quoting the attribute, and says in-line why it
  must not — so the next person adding a comment near it does not repeat this.
- **Files modified:** `companion/static/style.css`
- **Commit:** `3afafa4`

**2. [Rule 3 - Blocking] `page_shell()`'s fixed-arity script template**

- **Found during:** Task 1
- **Issue:** appending `VALUE_CONTROLS_SCRIPT_SRC` to the shell's script tuple without adding
  a matching `%s` line to the shell's format string produced
  `TypeError: not all arguments converted during string formatting` in 30 checks.
- **Fix:** the fifteenth `'<script src="%s" defer></script>\n'` line added.
- **Files modified:** `companion/layout.py`
- **Commit:** `a44ece9`

**3. [Rule 2 - Missing critical functionality] `layout.JS_GATE_CLASS`**

- **Found during:** Task 4
- **Issue:** the contract guard needs the gate class name, and so will every page module from
  25-03 on. A class name typed by hand in five page modules is the rename-drift the whole
  registry exists to prevent.
- **Fix:** `JS_GATE_CLASS` defined in `layout.py`, pinned to a real `style.css` selector on a
  **selector boundary** (a plain substring test would report `.js-gate` as resolved by a
  future `.js-gate-inner`).
- **Files modified:** `companion/layout.py`, `companion/test_companion_app.py`
- **Commit:** `809db90`

### Findings, not changes

**A second new script was never wanted.** The plan asked me to say so in the SUMMARY if the
design pushed toward one. It did not: D17's dial and D18's slider share one clamp/round/
keyboard model and differ only in `data-value-geometry`, and the geometry switch is twelve
lines. The script budget stands at one, and the pin at fifteen, for the rest of the phase.

## Threat model

Every disposition in the plan's register holds as written.

- **T-25-01-A** (a script writing an out-of-range value) — *mitigated*. The script clamps to
  bounds read from the wrapper's data attributes (which `config_page` interpolates from
  `device_config`), the native input keeps its own `min`/`max` constraint validation, and
  `save_device_config()`'s server-side re-check is untouched and remains the real control.
  `boundsFor()` refuses to invent a range when the attributes are missing or unusable, rather
  than guessing one the server would then reject.
- **T-25-01-B** (a new pre-auth static route) — *accepted*. The route matches its sixteen
  siblings exactly; the check asserts it **behaves like** an existing static route (200,
  `text/javascript`, `max-age=300`, no session) rather than assuming.
- **T-25-01-C** (state change by GET) — *n/a*. The script submits nothing; it writes an input
  value and dispatches a DOM event. Every state change stays the existing POST.
- **T-25-01-D** (a lifetime figure the data cannot support) — *mitigated*, and this is the one
  that took real work: five named states, an absolute figure only from `falling`, no assumed
  per-wake cost anywhere, and two observation floors that keep a noisy day and a 1 mV wobble
  from becoming confident numbers.
- **T-25-01-SC** — zero packages installed in any ecosystem.

No new threat surface was found outside the register.

## Requirements

**CFG-46 and CFG-49 are deliberately NOT ticked.** They belong to 25-08, the phase's closing
plan, and four of the five controls they cover do not exist yet. Holding the standard Phases
23 and 24 set with CFG-34, CFG-37, CFG-39 and CFG-42.

## Verification

```
./scripts/run-all-tests.sh   → FAIL, exactly the 5 sandbox baseline failures, verified BY NAME:
  companion/test_companion_app.py
    - POST /airlines/resolve … read-only … (WR-11)
    - POST /airlines/manual-resolutions/{prefix}/delete … read-only … (WR-11)
  companion/test_status_pages.py
    - anomaly_active() runs on every page render and must never raise …
  server/test_manual_resolutions.py
    - add_entry() returns ADD_FAILED … read-only … (WR-11)
    - delete_entry() returns False … read-only … (WR-11)

companion/test_companion_app.py   311/313   (the two WR-11 above)
companion/test_status_pages.py    301/302   (anomaly_active above)
companion/test_config_page.py     240/240
companion/test_contrast_check.py   49/49
companion/test_i18n.py             24/24
companion/test_browser_ux.py       PASS (25-02's, 178.2s)
ruff check .                       All checks passed!
```

No sixth failure. The baseline is unchanged.

## Commits

| Hash | Message |
|---|---|
| `bc36511` | test(25-01): the six checks value-controls.js does not yet satisfy |
| `a44ece9` | feat(25-01): value-controls.js, the phase's one new script, and its pin move |
| `123b103` | test(25-01): the .js gate and the shared control vocabulary, unsatisfied |
| `3afafa4` | feat(25-01): the .js gate and the shared control vocabulary in the stylesheet |
| `153e0de` | test(25-01): the battery-life estimate's totality and honesty, unsatisfied |
| `6245168` | feat(25-01): the battery-life estimate, extended into the one estimator |
| `809db90` | test(25-01): the no-JS control contract, made executable |

## Self-Check: PASSED

Every file this SUMMARY claims to have created or modified exists on disk, every named
symbol resolves (`layout.JS_GATE_CLASS`, `.js-gate` in `style.css`,
`battery.battery_life_estimate`, `_NO_JS_CONTROL_REGISTRY`), and all seven commit hashes
are present in `git log`.
