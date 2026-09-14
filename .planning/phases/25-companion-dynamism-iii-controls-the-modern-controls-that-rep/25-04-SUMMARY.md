---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 04
subsystem: ui
tags: [quiet-hours, dial, svg, aria-slider, no-js, value-controls, css-transform, i18n]

requires:
  - phase: 25-01
    provides: "the .js gate, the shared .value-control/.control-hit-area vocabulary, value-controls.js and the executable no-JS control contract"
  - phase: 25-02
    provides: "_persist_without_js(), _operate_with_keyboard(), _assert_hit_target(), _assert_js_gate(), _no_js_page(cookies=)"
  - phase: 25-03
    provides: "the runway map's precedent for a hand-written <svg> built from draw.py primitives, and the recorded 360px page-width baseline"
provides:
  - "config_page.quiet_window_span() — the wrapping-midnight arithmetic, as one triple the arc and the words are both read off"
  - "a SERVER-DRAWN 24h ring showing the saved quiet window with no script involved"
  - "two .js-gated drag handles, each a real <button role=\"slider\"> announcing its own input's HH:MM"
  - "value-controls.js's clock codec (minutes <-> HH:MM) and its repaint-from-elsewhere listeners — both inherited by 25-05"
  - "_NO_JS_CONTROL_REGISTRY's first rows"
affects: [25-05, 25-08]

tech-stack:
  added: []
  patterns:
    - "polar placement with no trigonometry: translate(-50%,-50%) rotate(f*1turn) translateY(-r) rotate(f*-1turn)"
    - "a value-control codec attribute (data-value-format) so one script steers both numeric and HH:MM native inputs"
    - "a script that paints from a native input repaints on change/input/click, because assigning to .value fires nothing"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/static/value-controls.js
    - companion/layout.py
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py

key-decisions:
  - "The two <input type=\"time\"> fields stay visible and stay what the form posts; the dial is an addition, and B14's visible 24h siblings survive byte-identical"
  - "The arc is server-drawn and outside the gate; only the two handles are gated, so the fallback is a correct picture rather than an absence"
  - "The readout is aria-hidden and is NOT a live region (CFG-52) — aria-valuetext on the focused handle is the announcement path"
  - "The keyboard model is the native <input type=\"range\"> one (arrows 1 step, Page 10 steps, Home/End), so Page is 150 min and not the plan's 60"
  - "No minimum separation in value; z-order is document order, so the END handle wins an overlapping pointer-down, and the start handle stays its own tab stop"
  - "The dial is 176px, not 128px, because two 44px targets cannot both clear the floor on a 128px ring until the ends are ~4h49 apart"
  - "layout.VALUE_CONTROL_TEXT_TOKEN corrected from \"{}\" to \"#\" — \"{}\" fails the French-render artefact scan"

patterns-established:
  - "One span triple: the drawn sweep is derived from the returned minute count inside one function, so the picture and the words cannot disagree"
  - "Cross-file agreement asserted by RECONSTRUCTION: the dial's span length is rebuilt from what server.device_config has left at five shared instants, on both sides of midnight"
  - "A shared hit-area register entry may be overridden upward (never downward) when an element is placed at a fractional pixel position"

requirements-completed: []

duration: 111min
completed: 2026-09-14
---

# Phase 25 Plan 04: D17's Quiet-Hours Dial Summary

**A 24-hour ring that draws the saved quiet window correctly before any script has run, with two drag handles that exist only where they can work — and whose four browser checks found four real defects, including a preset that moved both time inputs and left both handles where they were.**

## Performance

- **Duration:** 111 min (first commit 11:11:04Z, last 13:02:07Z)
- **Tasks:** 4/4
- **Files modified:** 8
- **Commits:** 4, one per task

## Task Commits

1. **Task 1: the wrapping-midnight arithmetic** — `2ec4d65` (feat)
2. **Task 2: the server-drawn ring** — `cee87b5` (feat)
3. **Task 3: the two handles, gated** — `1a9007d` (feat)
4. **Task 4: measured at 360px, by keyboard, scripts off** — `1259db2` (test)

## The decision that mattered most

**The two handles are not a control that holds a value — they are a layer over two inputs that do.** Everything downstream falls out of that: the arc is server-drawn (so scripts-blocked is a correct picture, not an absence); the handles are painted from `--value-fraction` written by the server from the saved value; `aria-valuetext` is the field's own HH:MM; and a preset that writes into those two fields is supposed to move the handles for free.

That last clause is where the decision earned itself. **It did not work for free, and only a browser check could have known.** Assigning to `.value` from script fires no event of any kind, so `dirty-state.js`'s preset handler was completely silent: it moved both time inputs and left both handles exactly where they were. The fix stayed inside the decision rather than around it — `value-controls.js` now repaints on `change`, `input` and `click`, learning nothing whatsoever about presets to do it, and `dirty-state.js` is untouched (25-01's recorded answer to the cross-file question stays true). The `click` listener is ordering-safe by the DOM's own event model, not by luck: the preset's handler is bound to the *button*, so it has already run by the time the click reaches `document`.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 — missing critical functionality] value-controls.js could not steer a native `<input type="time">` at all**

- **Found during:** Task 3, before any check existed
- **Issue:** 25-01's script writes `String(value)` — a number — into the named field. A time input holds `"HH:MM"` and **silently discards** anything else, so the first arrow press would have emptied the field the form posts, with no error anywhere. The plan's own "hidden synced input" alternative was refused outright by the plan itself (the time inputs stay visible and stay what posts).
- **Fix:** a codec seam — `data-value-format="clock"` (`layout.VALUE_CONTROL_FORMAT_ATTR`/`VALUE_CONTROL_FORMAT_CLOCK`), `fieldToNumber()`/`numberToField()`, applied at the three points that touch the field: the read in `currentValue()`, the write in `steer()`, and the `aria-valuetext` substitution in `paint()`.
- **Files:** `companion/static/value-controls.js`, `companion/layout.py`
- **Commit:** `1a9007d`
- **Still one script.** This is a seam on the existing file, not a second one. 25-05 inherits it and simply omits the attribute.

**2. [Rule 1 — bug] `paint()` announced on the wrapper, not on the focusable handle**

- **Found during:** Task 3
- **Issue:** `role="slider"` and its `aria-value*` belong on the element a keyboard visitor lands on. With them on the wrapper and a `<button>` inside taking the focus, a screen reader would read the *saved* value on every step of a drag that had already moved somewhere else.
- **Fix:** `paint()` resolves `wrapper.querySelector("[data-value-handle]") || wrapper`. `--value-fraction` still goes on the wrapper (geometry stays in CSS).
- **Commit:** `1a9007d`; proven by **M30**.

**3. [Rule 1 — bug] `layout.VALUE_CONTROL_TEXT_TOKEN` was `"{}"`, which no consumer can use**

- **Found during:** Task 3, by `companion/test_i18n.py` Check 3 failing on `GET /display?lang=fr`
- **Issue:** these templates reach the browser as attribute values on a rendered page, and Check 3 scans every French render for a stray `%s`/`%d`/`{}` — the real failure mode of a mistyped catalogue key. `layout.py`'s own `RELATIVE_QUANTITY_MARK` records this exact lesson, and chose `"#"` for it; 25-01 chose `"{}"` anyway.
- **Fix:** corrected in place to `"#"` on both sides, with the reasoning written into both files. A check now refuses `"{}"`/`"%s"`/`"%d"` as the token.
- **Commit:** `1a9007d`

**4. [Rule 1 — bug] the script steered from a synthetic, coordinate-less pointer event**

- **Found during:** Task 4
- **Issue:** `el.dispatchEvent(new PointerEvent("pointerdown"))` carries `clientX/clientY` of `0,0` — the top-left corner of the viewport — so steering from one yanks a real saved setting to whatever angle the screen corner happens to be at, **from any script on the page**. Measured: `_operate_with_keyboard()`'s own recorder self-test moved the quiet window from 23:15 to 22:30 while proving itself alive.
- **Fix:** `untrusted(evt)` — `evt.isTrusted === false` (compared against `false`, not negated, so a browser without the property does not refuse every real drag) — guarding both `pointerdown` and `pointermove`. This is correct on its own terms, not test scaffolding.
- **Commit:** `1259db2`

**5. [Rule 1 — bug] the handle's hit target measured 43×43, one pixel under the floor**

- **Found during:** Task 4
- **Issue:** `.control-hit-area` synthesises **exactly** 44 (22 + 11 + 11), which is right for every grid-aligned consumer. This handle is carried round a circle by a rotate/translate pair, so it lands at a *fractional* pixel position and the browser snaps its hit region to the grid.
- **Fix:** `.quiet-dial__handle::before { inset: -12px; }` — 46 declared, measuring 45×45. A hit-area **gain**, never a trade, and scoped to this component rather than loosening the shared register entry.
- **Commit:** `1259db2`

**6. [Rule 2 — the audit's own clause] a preset moved both inputs and neither handle** — described above. **Commit:** `1259db2`.

### Deliberate departures from plan sentences

**A. Page keys move 150 minutes, not 60.** The plan's behaviour line asked for `Page ±60`; the same plan's binding constraint says the model *must* match the native `<input type="range">` one that 25-05 will inherit. They cannot both hold. Ten steps of 15 minutes is 10.4% of the day, which is precisely what a native range control's Page keys do, and a per-control page size would have been a second keyboard model on a second settings page. The stronger constraint won; the plan sentence is recorded here rather than quietly satisfied.

**B. There is no minimum separation between the handles.** The plan asked for "a minimum separation, a z-order, and which handle wins a pointer-down in the overlap". Two of the three are answered as asked; the first is answered *no*, deliberately. A zero-length window is a real, defined state — `seconds_until_quiet_hours_end()`'s own docstring calls it never-active and means it — so refusing it here would make a state reachable by typing unreachable by dragging, which is a worse card and not a safer one. What replaces it: z-order is **document order** (no `z-index` anywhere, asserted), the END handle is emitted second and therefore wins an overlapping pointer-down, and that is **sufficient** rather than arbitrary — recovering needs only one end draggable, moving it separates the pair, and the start handle stays its own tab stop whatever it is painted under (measured: focusable at 15 minutes' separation, where its centre hit-tests to the end handle).

**C. The dial is 176px, not the 128px it was first built at.** Geometry, not taste: each hit target is a 46px box, so neither may intrude within 22px of the other's centre, which needs ~45px between centres on one axis — 45·√2 of chord in the worst (45°) orientation. On a 128px ring (r=54) that is ≈ **4h49**; on 176px (r=78) it is ≈ **3h12**. The plan's "ends close together" measurement is therefore taken at four hours, inside the reachable band and a window a person really sets, with the arithmetic written into the check.

**D. Two registry rows, not one.** `_NO_JS_CONTROL_REGISTRY`'s comment anticipates "exactly one row" per control plan. A row names one *field*; this control holds two values in two separate native inputs. Registering one would have left the other end's contract entirely unproven.

**E. `VALUE_CONTROL_FRACTION_PROPERTY` was written and removed.** A CSS custom property's name begins with two hyphens, which matches none of `test_i18n.py`'s identifier exclusions, so the D-05 scan reads it as untranslated copy and fails (measured). The name now lives inline in the one markup template that emits it — the same place `style="background:%s"` already lives — and a check pins it across all three files it travels through, which is a stronger guard than a constant two of the three could not have read anyway.

## Plan assumptions that turned out wrong

1. **"The three presets ... already write into the two fields; the dial reads from the fields, so this works for free."** It does not. Reading from the fields makes *steering* correct; it does nothing for *painting*, and writing `.value` from script fires no event. Cost: one generic listener trio in the shared script.
2. **"`_operate_with_keyboard()` is a helper you call."** It is, but its recorder self-test fires a synthetic `pointerdown` **after** the measurement and before the caller reads anything — which mutated this control. The control was wrong to accept that event; the helper is unchanged.
3. **"D17's dial and D18's slider differ only in `data-value-geometry`, a twelve-line switch"** (briefing). They differ in two attributes: geometry *and* the value codec. A time input is not a numeric input.
4. **`grep -c '@supports selector(:has(*))'` returns 6** on this tree (as the briefing said); brace-anchored and comment-stripped it is **1**, which is the number that matters and which an existing 25-03 check already pins. Not duplicated here.

## Vacuity: checks that failed the "what would a wrong implementation do?" question

**V1. The server-agreement clause probed only one side of midnight.** `seconds_until_quiet_hours_end()` answers a wrapping window through **two** branches. With only after-midnight probes, mutating its `timedelta(days=1)` to `days=2` changed **nothing**. Fixed by probing five instants across three windows, on both sides of midnight; the mutation now fails loudly (M6).

**V2. "The arc is present with scripts blocked" counted DOM elements.** `locator.count()` counts elements whatever their box is, so it passed against the arc moved behind the gate — *the exact refactor the clause exists to notice*. Fixed to measure the rendered box; M33 now fails.

**V3. M28 (`paint()` writes to the wrapper) failed nothing in the static harness.** Correctly so — it is a runtime property. Closed in Task 4: the browser check asserts the **handle's** `aria-valuetext` equals the input's value after a drag, and that the wrapper carries no `aria-valuenow`. M30 confirms.

## Every mutation, with its quoted failure

Each was applied to exactly one line, the changed line confirmed by grep *after* substitution (a `count(old) == 1` assertion plus a re-read — the "mutated a comment" trap), then reverted with `git checkout-index -f --` and `__pycache__` cleared.

### Task 1 — `config_page.py` / `test_config_page.py`

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M1 | `(end - start) % 1440` → `abs(end - start)` (line 2254) | *23:00→07:00 is 480 minutes forward through midnight, and quiet_window_span() returns 960 — an `end - start` implementation returns -960 here* |
| M2 | sweep computed separately from minutes | *00:37→00:00: sweep_fraction 0.0256… is not minutes/1440 (0.9743…) — the drawn arc and the printed duration are two computations and can disagree* |
| M3 | equal ends become a whole day (`… or 1440`, line 2254, re-verified) | *12:00→12:00 is 0 minutes forward through midnight, and quiet_window_span() returns 1440* |
| M4 | unparseable returns a zero span | *expected quiet_window_span('', '07:00') to be None — the render-nothing signal, not a fabricated window* |
| M5 | the hour/minute range check dropped (`if False:`) | *expected quiet_window_span('99:99', '07:00') to be None* |
| M6 | `server/device_config.py`'s wrap branch drifts (`days=1` → `days=2`) | *the dial and server.device_config disagree about 23:00→07:00: the server has 113400 seconds left at local 23:30, and the dial's 480-minute span with 30 minutes elapsed implies 27000* — **no failure before V1 was fixed** |
| M7 | `_normalised_time_html()` grows its own stricter regex | *quiet_window_minute_of_day('23:59') parses but _normalised_time_html('23:59') renders nothing — the arc and B14's visible 24h sibling have drifted into two parse disciplines* |

### Task 2 — the ring

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M8 | the arc ignores the window's start (line 2421) | *23:00→07:00: the arc is rotated -90.0000°, but a window starting at 0.958333 of the way round from twelve o'clock needs 255.0000°* |
| M9 | a fixed third of the ring is drawn (line 2415) | *07:00→23:00 draws 0.3333 of the ring, not the 0.6667 its 960-minute span asks for — recomputed from the emitted r=54 and stroke-dasharray='113.0973 226.1947'* |
| M10 | a zero-length window is drawn as a window | *a zero-length window emitted an arc — a zero-length dash is a DOT under a round cap, so 'no window' would read as a few minutes* |
| M11/M11b | the arc/readout read the STORED window, not the submitted one | *a value that is not a time drew an arc* / *the rejected-save readout does not echo the submitted window* |
| M12 | the readout becomes `role="status"` (emitter line 2491 confirmed, **not** the docstring line 2469 that also names it) | *the readout is not aria-hidden — both time inputs already announce their own values natively and this would say the same thing twice (' role="status"')* |
| M13 | the duration becomes a second ladder | *the readout says '23:00 → 07:00 · 9h'; the span it is drawn from is 480 minutes, which this app's one duration ladder names '23:00 → 07:00 · 8h'* |
| M14 | the ring moved below the End field | *the card's order is [('caption', 103), ('presets', 365), ('start', 749), ('end', 981), ('dial', 1186)] — the ring is an addition between the caption and the presets, never a reordering* |
| M15 | the arc's stroke becomes `#808080` | *.quiet-dial__arc paints from '\n  stroke: #808080;\n' rather than --color-text* |
| M16 | the day-ring rule deleted | *the dial emits the class 'quiet-dial__day', which has no selector in style.css* |
| M17 | a CSS `stroke-width` added to the arc | *.quiet-dial__arc declares stroke-width in CSS, which beats the presentation attribute the emitter derives from its own size constants* |
| M18 | a class renamed in Python only | *the dial emits the class 'quiet-dial__window', which has no selector in style.css* |
| M19 | the day ring loses `fill="none"` | *a stroked shape with no explicit fill … the SVG default is a filled black disc across the middle of the card* |

### Task 3 — the handles

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M20 | the wrapper loses the gate class | *an element carries data-value-control outside the 'js-gate' gate: `<div class="value-control quiet-dial__handles " …>`* |
| M20b | the same, against 25-01's contract | *the quiet-hours dial's start handle (D17) (25-04-PLAN.md Task 3): an element carries data-value-control OUTSIDE the 'js-gate' gate … which is the control that renders and does nothing* |
| M21 | the handle becomes a bare `<div>` | *the quiet_hours_start wrapper's handle is not a `<button>`* |
| M22 | `aria-valuetext` announces the minute count | *the quiet_hours_start handle is missing 'aria-valuetext="23:00"' — … aria-valuetext="1380"* |
| M23 | the clock codec attribute dropped from the markup | *the quiet_hours_start wrapper does not carry data-value-format='clock'* |
| M24 | the script stops reading the clock codec | *value-controls.js never compares against '=== "clock"', so the markup's own value is read by nothing* |
| M25 | the server paints no initial position | *the quiet_hours_start wrapper paints no initial position* |
| M26 | the handle radius drifts from the drawn ring | *the handle rides a radius of '--quiet-dial-radius: 40px'; the ring's own stroke centre line is 54px* |
| M27 | the handle layer stops being pointer-transparent | *.quiet-dial__handles does not declare `pointer-events: none` — with two full-size layers stacked over one ring, the upper one otherwise claims every press* |
| M28 | `paint()` writes the ARIA back onto the wrapper | **no failure in the static harness** — a runtime property; see V3 and M30 |

### Task 4 — the browser

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M29 | the handle's write into the native input disabled | *dragging the start handle to six o'clock on the ring put '23:00' into quiet_hours_start; the bottom of a 24h dial is 12:00* |
| M30 | `paint()` announces on the wrapper | *the handle announces '23:00' while its own input now holds '12:00' — a screen-reader visitor is being told the value it had before the drag* |
| M31 | the repaint-from-elsewhere listeners removed | *a preset click left the handles at ['0.500347', '0.542043'] (they were at ['0.500347', '0.542043']) … one that did not is holding a value of its own* |
| M32 | the handle layer rendered outside the gate | *_assert_js_gate: '.quiet-dial__handles' occupies space with scripts blocked on /display — 2 of the 2 wrapper(s) measured [[176, 176], [176, 176]]* |
| M33 | the arc moved behind the `.js` gate | *the quiet arc is in the scripts-blocked document but occupies no space (None) — rendered is not drawn* (**passed** before V2 was fixed) |
| M34 | an hour label loses its centring pull-back | *the 0 label is 7.79px off the axis it is meant to be centred on — the half-of-itself pull-back is not being applied* |
| M35 | the window paints the same token as the whole day | *light: the whole day and the quiet window paint identically ('rgb(223, 215, 200)') — the ring shows nothing* |

## Properties found inert (written, measured, deleted)

- **`.quiet-dial { max-width: 100%; }`** — the dial is narrower than its card at the 360px floor in every state; deleted before it was ever committed.
- **`.quiet-dial__ring { width: 100%; height: auto; }`** — the canvas carries its own intrinsic `width`/`height` attributes and its parent is exactly that wide. Deleted; the rule keeps only `display: block`, which is load-bearing (an inline `<svg>` leaves a baseline descender gap) and is asserted as a computed value.
- **`.quiet-dial__day/__arc { fill: none; }`** — both shapes already carry `fill="none"` as presentation attributes, which they must (a stroked circle with no fill declared takes the format's default black). A CSS restatement is 25-03's `stroke-width: 1` defect exactly; never written.
- **`.quiet-dial__handle { position: absolute; }`** — already won from the shared `.value-control__handle` rule. Not redeclared; instead a check pins the **source order** of the two shared rules, which both declare `position` at equal (0,1,0) specificity.

Every remaining declaration this plan added was mutated and failed something: M15/M16/M17/M26/M27/M34/M35 cover the paints, the radius, the pointer discipline and the label placement; the dial's `width`, `margin`, the readout's margins and `text-align`, and the `display: block` are each asserted as measured computed values or measured positions in the 360px browser check.

## Measured: the hit target, in this control's own container

All at 360 px, `_assert_hit_target()` in `.quiet-dial`, floor 44 px both axes.

| Window | Handle | Visual box | **Hit area** | Reach (l, r, u, d) |
|---|---|---|---|---|
| 23:00→07:00 (far) | start | 22 × 22 | **45 × 45** | (23, 21, 22, 22) |
| 23:00→07:00 (far) | end | 21.99998 × 22 | **45 × 45** | (23, 21, 23, 21) |
| 23:00→03:00 (close) | start | 22 × 22 | **45 × 45** | (23, 21, 22, 22) |
| 23:00→03:00 (close) | end | 22 × 22 | **45 × 45** | (23, 21, 23, 21) |
| 23:00→23:15 (overlapping) | end | 22 × 22 | **45 × 45** | — |
| 23:00→23:15 (overlapping) | start | — | **occluded** (hit-tests to the end handle) — and still focusable | — |

The fractional `21.99998` is the transform landing off the pixel grid; it is exactly why the `::before` inset is `-12px` here. Before that change the same measurement read **43 × 43**.

## Other recorded measurements

- **Page at 360 px:** `documentElement.scrollWidth 360` against `clientWidth 360` — identical to 25-03's recorded number, so the ring added no sideways scroll.
- **The drawing:** `176.00 × 176.00` by `getBoundingClientRect()` (never `clientWidth`); `display: block`; dial centre `180` against card content centre `180`; readout margins `0px` / `16px`; readout text centre `180` against its box centre `180`.
- **The four anchor hours**, offsets from the dial's centre: `00 (0, −50.05)`, `06 (+57.34, 0)`, `12 (0, +50.05)`, `18 (−57.34, 0)` — each on its own axis to within 0 px.
- **Paint, both themes** (none is the SVG default; every one inverts):

  | | light | dark |
  |---|---|---|
  | day ring | `rgb(223, 215, 200)` | `rgb(42, 48, 64)` |
  | quiet arc | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |
  | hour labels | 30 % of text | 30 % of text (inverted) |
  | grip fill | `rgb(247, 244, 239)` | `rgb(12, 15, 20)` |
  | grip edge | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |

  (The arc was first drawn at 55 % ink and the labels at 55 % too, which made the subject and its own context identical. The arc is now full ink and the labels 30 % — the same context strength the airfield diagram uses — and a check asserts the labels stay weaker than the arc.)
- **Drag/keyboard:** dragged to `12:00` and stored `12:00`; one ArrowRight `23:00 → 23:15`; End `→ 23:59`; Home `→ 00:00`; a preset click moved both fractions (`0.500347, 0.542043` → `0.33356…, 0.75052…`); readout `23:00 → 07:00 · 8h`.

## The byte-identical diff (recorded empty)

The pre-task `quiet_hours_group()` was loaded from `HEAD` under a second module name and rendered beside the new one; the new output with **only** the two new fragments removed was compared byte-for-byte, across five argument shapes:

```
(('23:00', '07:00'), [])                      identical=True
(('08:00', '18:00'), [])                      identical=True
(('', ''), [])                                identical=True
(('23:00', '07:00'), ['errors', 'submitted']) identical=True
(('23:00', '07:00'), ['delay_sentence'])      identical=True
ALL IDENTICAL: True
```

Both `<input type="time">` elements, both `_normalised_time_html()` siblings, the three presets and the caption (with its computed delay sentence) are therefore unchanged, including on the D-07 rejected-save path and the empty-window path. The durable half of that proof lives in `_the_ring_is_an_addition_and_the_four_controls_are_untouched` and is exercised by M14.

## Re-derived check counts (obtained by RUNNING)

| Harness | Before | After | Δ |
|---|---|---|---|
| `companion/test_config_page.py` | 245 | **251** | +1 (T1), +3 (T2), +2 (T3) |
| `companion/test_browser_ux.py` | 68 | **71** | +3 (T4) |
| `companion/test_companion_app.py` | 313 | **313** | +0 — two checks retargeted in place (registry rows; the tenth seam attribute) |
| `companion/test_i18n.py` | 24 | **24** | +0 |
| `companion/test_status_pages.py` | 302 | **302** | +0 |
| `companion/test_view_pages.py` | 164 | **164** | +0 |

## Budgets

- `@supports selector(:has(*))` — raw `grep -c` **6**, brace-anchored and comment-stripped **1** (already pinned by 25-03's check; not duplicated).
- `@keyframes` — **4** live (`^@keyframes`), one further mention in a pre-existing comment. No new keyframes; no per-rule reduced-motion block (**3**, unchanged).
- `interpolate-size` / `calc-size(` — 0 live, 2 comment mentions only.
- `style.css` stray comment terminators — **0**.
- `value-controls.js` — exactly **1** `.value` assignment; 0 backticks; ES5 subset; no new forbidden sink.
- No requirement ticked; `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` untouched.

## Criteria that did not evaluate as predicted

- **"Four hit-area measurements … each at least 44px in both axes."** Satisfied at the two windows measured — but *not* satisfiable at every separation, and that is geometry rather than a defect. Recorded as departure **C**, with the threshold computed, the dial resized, and the genuinely overlapping case measured and answered rather than avoided.
- **"Keyboard: … Page keys 60."** Not implemented as written — departure **A**.
- **"Each of 25-03..25-07 appends exactly one row"** to the no-JS registry — two rows, departure **D**.

## Verification

```
./scripts/run-all-tests.sh   →   FAIL (expected)
```

Exactly **5** failing checks, **by name**, all pre-existing sandbox baseline:

1. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created … (WR-11)` — `server/test_manual_resolutions.py`
2. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)` — `server/test_manual_resolutions.py`
3. `POST /airlines/resolve redirects with the manual_save_failed flash key … (WR-11)` — `companion/test_companion_app.py`
4. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)` — `companion/test_companion_app.py`
5. `anomaly_active() runs on every page render and must never raise …` — `companion/test_status_pages.py`

`companion/test_browser_ux.py` 71/71, **0 SKIPs**. `ruff check .` clean.

## Known stubs

None.

## Threat flags

None. The dial submits nothing; it writes into two inputs that post through the existing `POST /settings` with its unchanged session gate. `T-25-04-A` is mitigated by the clamp plus the server's unchanged HH:MM gate; `T-25-04-B` by `escape_html()` on every interpolation and the reused `_HHMM_RE` parse discipline; `T-25-04-C` by `quiet_window_span()` returning the render-nothing signal rather than raising, asserted against thirteen hostile inputs including a non-string object.

## What 25-05 inherits

- `data-value-format` — **omit it** for a numeric `<input type="number">`; the script writes the number straight in, exactly as before.
- The keyboard model is unchanged and shared: arrows one step, Page ten steps, Home/End to the ends. Do not add a page-size attribute.
- `paint()` now announces on `[data-value-handle]` when the wrapper has one — put `role="slider"` and the `aria-value*` on the handle, not the wrapper.
- The repaint listeners (`change`/`input`/`click`) are generic; a slider whose field is written by something else follows for free.
- `layout.VALUE_CONTROL_TEXT_TOKEN` is `"#"`. Do not reintroduce `"{}"`.
- `--value-fraction` has no Python constant on purpose; emit it inline in the markup template.
- `.control-hit-area`'s `-11px` inset synthesises *exactly* 44. If the control is placed at a fractional pixel position, override the inset upward in the component's own rule.

## Self-Check: PASSED

- `companion/pages/config_page.py` — FOUND
- `companion/static/style.css` — FOUND
- `companion/static/value-controls.js` — FOUND
- `companion/layout.py` — FOUND
- `companion/i18n_fr/display.py` — FOUND
- `companion/test_config_page.py` — FOUND
- `companion/test_companion_app.py` — FOUND
- `companion/test_browser_ux.py` — FOUND
- `2ec4d65`, `cee87b5`, `1a9007d`, `1259db2` — all FOUND in `git log`
