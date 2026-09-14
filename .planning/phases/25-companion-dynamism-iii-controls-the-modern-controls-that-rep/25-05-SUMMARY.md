---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 05
subsystem: ui
tags: [wake-interval, range-input, native-control, battery-estimate, no-js, value-controls, i18n, honesty]

requires:
  - phase: 25-01
    provides: "the .js gate, the VALUE_CONTROL_* seam, value-controls.js, the executable no-JS control contract, and battery.battery_life_estimate()"
  - phase: 25-02
    provides: "_persist_without_js(), _operate_with_keyboard(), _assert_hit_target(), _assert_js_gate(), _no_js_page(cookies=)"
  - phase: 25-04
    provides: "the repaint-from-elsewhere listeners, the isTrusted refusal, and the keyboard model the native range turns out to own"
provides:
  - "config_page.wake_gauge_interval_s() — one resolution of the subject the slider and both gauges share"
  - "two server-rendered gauges: a freshness BOUND and a battery sentence that names its own ignorance"
  - "a native <input type=\"range\"> with no name, inside the .js gate, steering the number input that already existed"
  - "value-controls.js's MIRROR seam (a native control that carries the value and posts nothing) and its READOUT seam (a sentence rewritten from a server-rendered translated template)"
  - "_NO_JS_CONTROL_REGISTRY's third row"
affects: [25-06, 25-07, 25-08]

tech-stack:
  added: []
  patterns:
    - "a native control as the enhancement, with the script reduced from steering to syncing"
    - "a gesture-handler guard that stands aside for a wrapper holding a native mirror"
    - "a live sentence split into a server-only half and a script-writable half, so the script cannot become braver than the server was"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/layout.py
    - companion/static/value-controls.js
    - companion/static/style.css
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py

key-decisions:
  - "The battery gauge's live half names TWO CADENCES rather than a ratio — a ratio needs a decimal, a decimal needs a locale-specific decimal mark, and two integers need neither"
  - "The absolute days figure is server-rendered OUTSIDE every readout, so no template the script can reach contains one"
  - "The range is a real native range: the script stands aside from all three gesture handlers for it, because preventDefault on a pointerdown cancels the browser's own thumb drag"
  - "The slider and both gauges render only when a usable interval exists — a range with no value sits at the midpoint of its own band, which one drag would save"
  - "wake_battery_life_text() was renamed wake_battery_observed_text() because the one-home guard was right to object to the NAME; the answer was to stop claiming to compute a lifetime, not to allow-list the claim"
  - "The shared .value-control class is deliberately NOT worn by this control"

patterns-established:
  - "One subject resolution: the gauges and the slider are fed by a single wake_gauge_interval_s() call, so they cannot describe different values"
  - "A readout declares a BASE at which it says nothing at all, which is what every page load and every scripts-blocked render is"
  - "An honesty rule made structural: a script that only substitutes into templates cannot state what no template contains"

requirements-completed: []

duration: 87min
completed: 2026-09-14
---

# Phase 25 Plan 05: D18's Wake-Interval Slider Summary

**A native range that can only ever steer the number input that already existed, beside two sentences that make the trade-off visible — one of which is true by construction and one of which says, in a rendered sentence, that this frame has never measured what a wake costs.**

## Performance

- **Duration:** 87 min (first commit 13:38:49Z, last 14:36:00Z, plus the measurement and mutation runs)
- **Tasks:** 3/3
- **Files modified:** 8
- **Commits:** 3, one per task

## Task commits

1. **Task 1: the two gauges, server-rendered** — `fca1507` (feat)
2. **Task 2: the gated range, synced** — `c47ad86` (feat)
3. **Task 3: measured at 360px, by keyboard, trap re-proven** — `090673d` (test)

## The decision that mattered most

**The battery gauge's live half names two cadences instead of a ratio, and the absolute figure lives outside every element the script can write.**

The plan asked for a relative statement built on `battery_life_estimate()`'s `relative_factor`, and the obvious rendering of that is "≈ 2.0× more often than the saved one". Building it exposed three problems at once, and all three dissolve together:

1. **A ratio needs a decimal, and a decimal needs a locale.** French writes `2,0`, English `2.0`. The number is computed in the *browser* while the slider moves, so the decimal mark would have had to travel to the script as one more attribute — a per-language formatting rule inside a file whose whole contract is that it carries no copy.
2. **A decimal needs one rounding rule in two languages of source.** `Math.round()` is half-**up**, Python's `round()` is half-to-**even**, and this control really reaches a tie: 1260 s against 1200 s is exactly 1.05. The sentence would have changed when nothing changed, at exactly the position where the server had rendered it.
3. **A ratio needs two wordings** (more often / less often) and therefore two more template attributes.

"This setting wakes the frame every 51 min instead of every 5 min" needs none of that: two integers, one wording, one substitution, and the saved cadence baked in by the server because it is fixed for the life of the page. `relative_factor` is still what decides whether there is anything to say at all — it is the guard rather than the number, and it still refuses a bool cadence, a non-numeric one and an absurd one on this card's behalf.

The second half of the decision is what makes the honesty rule structural rather than a promise. The **absolute** "≈ N days" sentence is rendered by the server, outside every readout element, and the script never touches it. What the script may rewrite is a `<span>` whose template names two cadences and contains no days figure at all. So "if the server said *not enough history*, the script keeps saying so" is not a policy the next editor has to remember — **there is no template through which the script could say anything else**, and a check asserts exactly that.

## Exactly what the battery gauge claims, and what it refuses to claim

Rendered live on this tree, at the seeded 300 s interval:

> Not enough battery history yet to say how long a charge lasts — this frame has never measured what one wake costs. While the screen is off the frame wakes every 5m instead, whatever this is set to.

and, once the slider moves, a third clause appears:

> This setting wakes the frame every 51 min instead of every 5 min.

**It claims:** a days figure *only* when `companion/battery.py` reports `LIFE_TREND_FALLING` with an integer `days_remaining` — i.e. only from this device's own observed daily-average discharge slope, measured over at least `LIFE_MIN_OBSERVED_SPAN_DAYS` (2) with at least `LIFE_MIN_OBSERVED_DROP_MV` (10) of fall. It carries the `≈` marker the battery percentage already wears and names its source ("from this frame's own recent readings"), over a **14-day** window — deliberately shorter than health_page's three-month trend window, because the sentence says *recent* and a slope measured across a charge three months ago is not.

**It refuses:** any figure derived from an assumed per-wake energy cost. The audit's "estimated battery life ≈ 38 days" **cannot be computed honestly today** and this plan does not compute it. Four of `battery_life_estimate()`'s five named trends carry no number, and all four render the same named sentence here: no reading, not enough history, **rising** (a charged device has a positive slope, and dividing by it gives a negative or infinite lifetime — both numbers a user would act on), and flat. It also refuses to imply that the configured interval is in force while the screen is off, because `server/wake.py` pins `DISPLAY_OFF_SLEEP_S` ahead of this field entirely.

**DEVICE-05 is live and will change this.** The real device's discharge run is at 3338 mV, already below its 3400 mV cutoff, and closes 2026-09-23. It will finally supply a **measured mAh-per-cycle figure**. Nothing in this plan needs to change to accept it: a later plan can add a second, model-based branch to `battery_life_estimate()` and this card will print it through the same `WAKE_BATTERY_DAY(S)_TEXT` wording — **the gap is in the data, not in the presentation**, and this is recorded so a later plan upgrades the gauge rather than rediscovers the gap.

## What was built

### Task 1 — two sentences, correct before any script runs

`wake_gauge_interval_s()` resolves the subject **once**: an int inside `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]`, honouring D-07's echo (a rejected save's raw string) **only where that string is a usable interval**. A submitted `"7"` renders no gauge at all, because a gauge about 7 seconds describes a cadence this device cannot be configured to use. Everything this plan adds is fed from that one call, so the slider and the two gauges cannot describe different values.

`_wake_minutes()` is the one ceiling expression both sentences and the script read. **Up, not down:** a 90-second cadence bounds the wait at a minute and a half, and `90 // 60` prints "at most 1 min", which is *false*. Every value the slider can reach is a whole minute anyway; the ceiling exists for the values already on disk from before this control existed.

The freshness sentence is a **bound** and the word "at most" is asserted to be in the wording, not just in the docstring.

### Task 2 — the mirror seam, and a script that syncs instead of steers

`layout.py` gained five names: `VALUE_CONTROL_INPUT_ATTR` (the mirror) and four `VALUE_CONTROL_READOUT_*` names. `value-controls.js` gained `mirrorFor()`, `writeValue()`, `readoutQuantity()`, `paintReadouts()` and `steeredHere()` — and **all three gesture listeners now stand aside for a wrapper holding a mirror**. That guard is load-bearing rather than tidy: `preventDefault()` on a pointerdown over a native range cancels the browser's own thumb drag outright, and a keydown handler that both prevents the default and steps the value moves the control twice per arrow press. Proven by the browser mutation below.

The `.value` assignment count is still **one**, and the check that pins it was **strengthened rather than satisfied**. Funnelling two writes through one helper would have satisfied the count while quietly reopening what it guards, so the check now pins the *shape*: the assignment lives in `writeValue()`, there is exactly one `writeValue(field, …)` and exactly one `writeValue(mirrorFor(wrapper), …)`, and the second one is asserted to lie **inside `paint()`** — strictly downstream of a value read back off the field. The file's own header paragraph was rewritten to say all of this in the same place it claims "this file never holds a value".

### Task 3 — the browser

Three checks, none of which asserts that the slider renders. See the measurements below.

## Every mutation, with its quoted failure

Each was applied to exactly one line (or one contiguous block), the changed line confirmed by re-reading the file *after* substitution — a `count(old) == 1` refusal plus a report of the line numbers before and after, which is the "mutated a comment" trap closed by machine — then reverted with `git checkout-index -f --`, with `__pycache__` cleared before and after every run.

### Task 1 — the gauges

| # | Mutation | Quoted failure |
|---|---|---|
| M1 | the minute ceiling becomes a floor (`-(-int(x) // 60)` → `int(x) // 60`, line 3014) | *wake_freshness_text(90) names ['1']; 90 seconds is 2 whole minutes — and it must round UP, because 'at most 1 min' is FALSE for a 90-second cadence* |
| M2 | "at most" dropped from the wording (line 572) | *the freshness wording 'A plane reaches the frame # min after it passes.' does not say 'at most' before its quantity — a bound stated without it is a claim about typical behaviour, and nothing in this project measures that* (and, separately, *has no French sibling*) |
| M3 | the trend test inverted (line 3074) | *the battery sentence 'Not enough battery history yet…' does not carry battery_life_estimate()'s own figure (4 days) — the one estimate lives in companion/battery.py* |
| M4 | singular/plural collapsed to the plural (line 3076) | *a one-day estimate renders "≈ 1 days of battery left…" rather than the singular wording — '1 days' is the missing-plural defect* |
| M5 | the band test dropped from the gauge subject | *wake_gauge_interval_s(0) resolved to an interval* + *stored BELOW the floor: a gauge rendered for a value the field itself refuses to show — that is the card inventing a subject* |
| M6 | **the page module invents a figure when the estimate declines** (line 3079) | *with rising (the device was charged) the battery sentence reads "≈ 205 days of battery left at this interval…"; it owes the named 'not enough history yet' state* + *companion/pages/config_page.py uses 'days_remaining' as an IDENTIFIER — the days-remaining arithmetic has exactly one home and companion/pages is not it* |
| M7 | the `≈` marker dropped (line 582) | *the battery sentence "4 days of battery left…" drops the ≈ honesty marker this app already wears on the battery percentage — an observed projection is not a datasheet figure* |
| M8 | the screen-off clause dropped from the card (line 3249) | *the rendered gauges do not carry the screen-off clause — a visitor who has turned the screen off reads a battery claim that does not apply to their frame* |
| M9b | the gauges and the error block swap places | *a gauge renders between the input and its own error message (gauge at 896, error block at 1093) — the message has to read as attached to the control it is about* |
| M10 | the number input's own tag gains `inputmode="numeric"` (line 3347) | *saved, in band: the number input is no longer byte-identical to its pre-plan output.* |

M6 is the one that matters: it is the dishonest-state defect written deliberately, and **two independent checks caught it**.

### Task 2 — the range and the seam

| # | Mutation | Quoted failure |
|---|---|---|
| M11 | the range gains `name="wake_interval_s"` | *the range carries a name (…) — it would post a second value for the same setting and whichever arrived last would win, silently* |
| M12 | `role="slider"` added | *the range carries a role (…) — a native range input IS a slider, with its own aria-valuenow and its own keyboard model; role="slider" on top of that is the double-role error* |
| M13 | the gate class dropped from the wrapper | *an element carries data-value-control outside the 'js-gate' gate: `<div class="wake-slider " …>`* — and, from 25-01's contract, *the contract rejected a CORRECT control…* |
| M14 | bounds restated as literals (30/7200) | *the range's min is not 60 — `<input type="range" … min="30" max="7200" …>`* |
| M15 | the script floors instead of ceiling | *value-controls.js does not take the CEILING of value/scale — the server does (_wake_minutes()), and a script that floored it would print a bound that is not true* |
| M16 | the keydown listener stops standing aside for a mirror | *value-controls.js's keydown listener does not stand aside for a wrapper with a mirror — a native range would be stepped twice per key or pinned in place by a prevented default* |
| M17 | the readout base set to 0 | *the relative readout's base is '0', not the saved interval — a readout with no base compares the saved value with itself on every page load* |
| M18 | the battery readout handed the DAYS wording as its template | *a readout template carries the days wording ("≈ # days of battery left…") — the absolute figure is server-rendered from observed history, and a template containing it is a script that can invent one* |
| M19 | the mirror attribute renamed on the Python side only | *value-controls.js never names 'data-value-native', so the markup's own attribute is read by nothing and the gauge is correct at load and stale for ever after* (+ the served-body pin) |
| M20 | the mirror write moved out of `paint()` | *expected exactly one `writeValue(mirrorFor(wrapper),` in value-controls.js (the mirror, which posts nothing and is written only from paint()), found 0* |

### Task 3 — the browser

| # | Mutation | Quoted failure |
|---|---|---|
| M21 | **the range-to-number write disabled** (the plan's required mutation) | *dragging the range across 153px of its own track left the number input at '600' — the range steers the control that already existed, or it steers nothing* |
| M22 | `.wake-slider__input { width: 100% }` → `auto` | *the range measures 147.00px inside a 278.00px content box (the number input beside it is 96.00px) — a range input's intrinsic width is about 129px…* (**passed** before the vacuity fix below) |
| M23 | `.wake-slider { margin-top }` → 0 | *the slider's wrapper computes margin-top '0px' — without it the range sits flush against the number input's own row* |
| M24 | the readout scale attribute set to 1 | *the freshness gauge reads 'A plane reaches the frame at most 3060 min after it passes.'; the server's own wording for 3060 seconds is 'A plane reaches the frame at most 51 min after it passes.'* |
| M25 | the gate class dropped (browser half) | *_assert_js_gate: '.wake-slider' occupies space with scripts blocked on /device — 1 of the 1 wrapper(s) measured [[278, 53]]* |

Both mutations the plan required (the range-to-number write, and the gate) fail loudly and are reverted; the suite is green afterwards.

## Vacuity: checks that failed the "what would a wrong implementation do?" question

**V1. The error-block clause located its subject by a bare id string, and the input's own `aria-describedby` names that id too.** So `markup.find("wake-interval-s-error")` returned a position *inside the input tag*, and the clause passed against the gauges rendered between the input and its error message — the one arrangement it exists to refuse. Measured: M9b failed **nothing** the first time. Fixed to locate the error paragraph by its own element (`<p class="field-error…" id="wake-interval-s-error"`); M9b now names both positions.

**V2. The slider's width was compared against the number input beside it**, which a range with *no width rule at all* passes — its intrinsic width is ~129px against the field's 96px. Measured: `width: auto` failed nothing. The property under test is "full width", so the comparison is now against the **card's own content box** (278px), and M22 fails naming all three numbers.

**V3. The fixture that proves the absolute figure is itself asserted to produce one** before the sentence is read — otherwise the whole "the figure equals battery.py's return" clause would pass against a card that never prints a figure. Same for the one-day fixture and the singular wording.

## Criteria that did not evaluate as predicted

1. **The plan's Task 1 acceptance criterion about a RISING series ("the sentence contains no negative and no infinite figure") is satisfied structurally rather than by this plan.** There is no mutation of *this* module that can make a rising series produce a number, because `battery_life_estimate()` returns `days_remaining: None` for one — the honesty is inherited from 25-01. M6 therefore had to *fabricate* a figure in the page module to exercise the clause, which is the stronger test and is what is recorded.

2. **"With a stored value below the floor, the form still submits a corrected value" needed a direct state write to set up.** `save_device_config()` raises on 30 (*wake_interval_s must be an int in [60, 3600]*) and `load_device_config()` *drops* an out-of-range stored value, and `env_wake_interval_default()` already clamps to `None`. So the below-floor state cannot be produced through any supported path — the check writes the config file's JSON directly and restores its exact previous bytes, and says so at the call site. The trap is real but is now guarded in **three** places, of which the `value`-attribute guard is the last.

3. **Page keys do not move ten steps, and 25-04's comment about the native convention is slightly wrong.** Measured in Chromium: from 60, `PageUp` moved to **420** — six steps, i.e. **10 % of the band** (3540/10 = 354, rounded to the 60 s step), not ten steps (600). The native rule is a percentage of the range, which coincides with "ten steps" only when the band is about 100 steps wide; 25-04's dial band is ~96 steps, which is why its 150 min looked like both. This control is a *real* native range, so the browser owns the model and the native rule is by definition the one 25-04 was imitating. **No script Page handling was added**: doing so would mean preventing the default on a native range's key press, which is the double-stepping this plan's mirror guard exists to avoid. Arrows (one step) and Home/End (the band's own ends) are asserted; Page is recorded here rather than pinned.

4. **The plan's briefing names `_operate_submit_persist()`; the helper on this tree is `_persist_without_js()`.** Same helper, same contract, used as described.

## Plan assumptions that turned out wrong

1. **"`data-value-format` — omit it for a numeric input; the script writes the number straight in, exactly as before"** (25-04's handoff) was true but insufficient. The slider differs from the dial in a **third** way nobody anticipated: it is a native control, which means the script must *stand aside* rather than steer. Three listener guards, not zero.
2. **The shared `.value-control` class does not fit this control** and is deliberately not worn — see "properties found inert" below.
3. **The plan's `files_modified` omits `companion/layout.py` and `companion/test_companion_app.py`,** both of which had to change: the seam constants have exactly one home, and 25-01's contract registry and its two pins live in that harness. Wave 4 contains this plan alone, so no file was contended.
4. **A second battery-life *name* in a page module is refused by an existing guard.** `wake_battery_life_text()` failed `test_companion_app.py`'s one-home check by name alone. The guard was right about the name and the fix is the rename (`wake_battery_observed_text()`) plus a new, narrower net of my own — **not** an allow-list entry, which would have let a real second estimate in under that name later.

## Properties found inert (or deliberately not adopted)

- **`.value-control` on this wrapper.** It declares `position: relative` (the containing block for an absolutely-placed handle — this control has no handle) and `touch-action: none` (so a touch drag is not claimed by the browser's panning gesture — a native range implements its own). The first is inert here; the second is a position on a gesture the browser already owns, with no way to measure the result in a headless harness. Recorded in the stylesheet at the point a later reader will wonder.
- **`--js-gate-display` on `.wake-slider`.** `block` is the gate's own fallback and a `<div>` is block anyway. Never written.
- **`--value-fraction`.** Still written by the shared `paint()` and unused by this control: a native range paints its own thumb from its own value. Left alone rather than special-cased.
- Both declarations that *were* added (`margin-top`, `width: 100%`) are load-bearing and fail a browser measurement when mutated (M22, M23).

## Measured: the hit target, in this control's own container

At 360 px, `_assert_hit_target()` inside `.wake-slider`, floor 44 px both axes.

| Control | Visual box | **Hit area** | Reach (l, r, u, d) | Clipped |
|---|---|---|---|---|
| `.wake-slider__input` | 278 × 44 | **279 × 45** | (140, 138, 23, 21) | no |

The extra pixel per axis is the browser's own grid snapping, which `_hit_area()`'s docstring records. No override of the shared hit-area register was needed: the range takes its 44 px floor from the global `input, select` rule, unmodified.

## Other recorded measurements (360 px, `/device`)

- **Geometry:** range `278.00 × 44.00` by `getBoundingClientRect()` (never `clientWidth`, which reports 276); card `312.00` wide with a `278.00` content box; the number input `96.00`; wrapper `margin-top: 8px`.
- **Page width:** `body.scrollWidth 360` against `clientWidth 360`, and `documentElement 360 / 360`. Identical numbers to 25-04's recorded Display-page baseline — **but this is the Device page and this is its own baseline**, recorded here for the first time.
- **Drag / keyboard:** drag across 55 % of the track `300 → 3060`; one `ArrowRight` `3060 → 3120` (one 60 s step) with **zero pointer events** and the recorder proving itself; `End → 3600`; `Home → 60`; `PageUp` from 60 `→ 420` (see criterion 3); typing `1800` into the number input moved the range to `1800`.
- **The sentences at three positions:**
  - 300 s — *A plane reaches the frame at most 5 min after it passes.*
  - 3060 s — *…at most 51 min…* + *This setting wakes the frame every 51 min instead of every 5 min.*
  - 60 s (Home) — *…at most 1 min…* + *…every 1 min instead of every 5 min.*
  - 3600 s (End) — *…at most 60 min…*
  - No days figure at any of them (this fixture's series is **rising**: 4080 mV → 4197 mV over 40 days).
- **Scripts blocked:** the gated wrapper has **no box at all** (`bounding_box() → None`, `count → 1`); the freshness gauge measures `278 × 39.19` and the battery gauge `278 × 97.97`, both reading their real saved-value text; the number input still shows `300`.
- **Paint, both themes** (sampled only after the Web Animations `finished` promise):

  | | light | dark |
  |---|---|---|
  | freshness text | `color(srgb 0.090 0.098 0.122 / 0.7)` | `color(srgb 0.945 0.953 0.965 / 0.7)` |
  | battery text | same as freshness | same as freshness |
  | range `accent-color` | `rgb(177, 63, 22)` | `rgb(255, 138, 92)` |
  | range surface | `rgb(238, 232, 222)` | `rgb(28, 34, 45)` |
  | canvas | `rgb(247, 244, 239)` | `rgb(12, 15, 20)` |

  The range's `accent-color` is a **genuine broadening of the stylesheet's exhaustive accent-reservation list**, recorded in place: it arrives from the same global `input, select` declaration that already paints radios and checkboxes, and a slider thumb is a selection affordance of exactly the kind the reservation is for.

## The byte-identical diff (recorded empty)

HEAD's `config_page` was loaded under a second module name and rendered beside the new one; the new output with **only** the appended fragments removed was compared byte-for-byte across six argument shapes:

```
((600,), [])                                  identical=True (382 gauge chars removed)
((30,), [])                                   identical=True (0)
((None,), [])                                 identical=True (0)
((600,), ['errors', 'submitted'])             identical=True (0)
((600,), ['next_wake_clock'])                 identical=True (382)
((3600,), [])                                 identical=True (382)
ALL IDENTICAL: True
```

The durable half lives in `_the_gauges_are_an_addition_and_the_number_input_is_untouched`, which asserts the input's exact opening bytes, the `value` attribute's presence in both directions, B17's label above it, the unit sibling **immediately** after it and the error block still attached, across six shapes — and is exercised by M10 and M9b.

## Re-derived check counts (obtained by RUNNING)

| Harness | Before | After | Δ |
|---|---|---|---|
| `companion/test_config_page.py` | 251 | **256** | +3 (T1), +2 (T2) |
| `companion/test_browser_ux.py` | 71 | **74** | +3 (T3) |
| `companion/test_companion_app.py` | 313 | **313** | +0 — three changes in place: the seam-attribute pin (ten → **fifteen**), the one-`.value`-write pin (strengthened with the mirror's shape), and a third `_NO_JS_CONTROL_REGISTRY` row |
| `companion/test_i18n.py` | 24 | **24** | +0 (eight new catalogue entries, all covered by the existing completeness checks) |
| `companion/test_status_pages.py` | 302 | **302** | +0 |
| `companion/test_view_pages.py` | 164 | **164** | +0 |
| `companion/test_contrast_check.py` | 49 | **49** | +0 |

## Budgets

- `@supports selector(:has(*))` — raw grep **6**, comment-stripped and brace-anchored **1** (unchanged).
- `@keyframes` **4**; `prefers-reduced-motion: reduce` **2**; `no-preference` **1**; `interpolate-size` / `calc-size(` **0** live. No new keyframes, no per-rule reduced-motion block.
- `style.css` stray comment terminators **0**. Deferred `<script src=` on the authenticated shell still **fifteen**; no new script, no new route.
- `value-controls.js` — exactly **one** `.value` assignment, ES5 subset, no backtick, no new forbidden sink.
- No requirement ticked. `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` untouched (CFG-46…CFG-52 belong to 25-08).

## Deviations from plan

### Auto-fixed issues

**1. [Rule 1 — bug] `_set_interval()` timed out on a value that was already stored.**
- **Found during:** Task 3, first browser run.
- **Issue:** the helper filled the field and clicked `.dirty-bar__save`, but the save bar only exists while the form *differs* from what was loaded — so "set it to what it already is" renders no Save control and the click waited thirty seconds for an element that was correctly absent.
- **Fix:** the helper is idempotent and says why.
- **Commit:** `090673d`

**2. [Rule 1 — bug] the paint sample read an interpolation frame.**
- **Found during:** Task 3, first browser run — the check *failed*, claiming the range's surface does not invert.
- **Issue:** the global `input, select` rule declares `transition: background-color .15s ease`, so a `getComputedStyle` taken straight after the theme attribute flip reads a tweened value. It reported the light value in both themes. This is 25-03's own defect in a new place.
- **Fix:** the read waits on the browser's own Web Animations `finished` promise, never a timer. The token does invert (`rgb(238,232,222)` → `rgb(28,34,45)`).
- **Commit:** `090673d`

**3. [Rule 2 — missing critical functionality] the gesture handlers had to stand aside for a native mirror.**
- **Found during:** Task 2, before any check existed.
- **Issue:** `preventDefault()` in the shared `pointerdown` handler cancels a native range's own thumb drag, and the shared `keydown` handler would step the value a second time per arrow press.
- **Fix:** `steeredHere()`, applied to all three listeners, with the reasoning at the definition site. Proven by M16 and by M21's browser failure.
- **Commit:** `c47ad86`

**4. [Rule 3 — blocking] a backtick in a new comment broke the ES5-safety scan.**
- **Found during:** Task 2. `value-controls.js must not contain '\`'` — the scan is deliberately blind to whether a backtick is inside a comment.
- **Fix:** the comment quotes the attribute name in double quotes instead.
- **Commit:** `c47ad86`

### Deliberate departures from plan sentences

**A. The battery gauge's live clause names two cadences rather than a ratio** — argued in full above. `relative_factor` is still consumed, as the guard that decides whether there is anything to say.

**B. `.value-control` is not worn by this control** — argued above and in the stylesheet.

**C. Page keys are the browser's, not the script's** — criterion 3 above.

**D. The card gained one function more than the plan implies.** `wake_battery_relative_template()` and `wake_battery_relative_text()` are separate: the template (with the saved cadence baked in) is what the markup hands the script, and the text is the server's own rendering of it, which exists so the browser check can assert the script says what the server would have said.

## Threat model

Every disposition in the plan's register holds as written.

- **T-25-05-A** (a range widening the accepted interval) — *mitigated*. `min`/`max` are interpolated from `device_config`, asserted against the module rather than against literals (M14); the number input keeps its own constraint validation; `save_device_config()`'s server-side re-check is untouched and still raises on 30.
- **T-25-05-B** (a fabricated out-of-range value blocking the whole form) — *mitigated*. The `value`-attribute guard is byte-identical across six argument shapes, the range renders nothing at all when there is no usable interval, and the case is re-proven end to end in a real browser with 30 s on disk: no `value` attribute, no range, no gauge, and the whole Settings form still saves a corrected value.
- **T-25-05-C** (a battery figure the data cannot support) — *mitigated*, and made structural: the figure comes only from `battery_life_estimate()`'s `falling` branch, no readout template contains the days wording, and no drag position in the browser produced a days figure from the fixture's rising series.
- **T-25-05-D** (a second submitted value) — *mitigated*. The range carries no `name`, asserted directly (M11), and `dirty-state.js`'s own snapshot skips nameless controls.
- **T-25-05-SC** — zero packages installed in any ecosystem.

No new threat surface was found outside the register.

## Known stubs

None.

## Verification

```
PYTHON=server/.venv/bin/python3 bash scripts/run-all-tests.sh   →   FAIL (expected)
```

Exactly **5** failing checks, **by name**, all pre-existing sandbox baseline:

1. `add_entry() returns ADD_FAILED … read-only … (WR-11)` — `server/test_manual_resolutions.py`
2. `delete_entry() returns False … read-only … (WR-11)` — `server/test_manual_resolutions.py`
3. `POST /airlines/resolve … manual_save_failed … (WR-11)` — `companion/test_companion_app.py`
4. `POST /airlines/manual-resolutions/{prefix}/delete … manual_delete_failed … (WR-11)` — `companion/test_companion_app.py`
5. `anomaly_active() runs on every page render and must never raise …` — `companion/test_status_pages.py`

```
companion/test_browser_ux.py     74/74   (263.2s, 0 SKIPs)
companion/test_config_page.py   256/256
companion/test_companion_app.py 311/313  (the two WR-11 above)
companion/test_status_pages.py  301/302  (anomaly_active above)
companion/test_i18n.py            24/24
companion/test_view_pages.py    164/164
companion/test_contrast_check.py  49/49
ruff check .                    All checks passed!
```

No sixth failure. The baseline is unchanged.

## What 25-06, 25-07 and 25-08 inherit

- **`data-value-input`** — a wrapper declaring a native mirror gets **no** gestures from `value-controls.js`. Use it whenever the platform already ships the control; the script's job shrinks to syncing.
- **`data-value-readout` + `-text` / `-scale` / `-base`** — a sentence beside a control, rewritten from a server-rendered translated template. The `-base` value is the one at which it says nothing at all.
- **The honesty split is reusable:** put whatever the server may not be braver about *outside* every readout. A script that only substitutes into templates cannot state what no template contains.
- **25-08's human check:** the battery gauge's WORDING is the item that most needs a human's eye. The developer may accept it, soften it, or drop the absolute branch entirely — and DEVICE-05's measured mAh-per-cycle figure (due 2026-09-23) is the input that would let a later plan add a model-based branch inside `companion/battery.py`.

## Self-Check: PASSED

- `companion/pages/config_page.py` — FOUND
- `companion/layout.py` — FOUND
- `companion/static/value-controls.js` — FOUND
- `companion/static/style.css` — FOUND
- `companion/i18n_fr/display.py` — FOUND
- `companion/test_config_page.py` — FOUND
- `companion/test_companion_app.py` — FOUND
- `companion/test_browser_ux.py` — FOUND
- `fca1507`, `c47ad86`, `090673d` — all FOUND in `git log`
