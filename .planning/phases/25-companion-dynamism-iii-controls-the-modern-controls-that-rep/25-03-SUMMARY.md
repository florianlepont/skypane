---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 03
subsystem: ui
tags: [svg, radiogroup, no-js, has-selector, theme-tokens, playwright, touch-target]

requires:
  - phase: 25-01
    provides: the shared control vocabulary in style.css, the `.js` gate (used by nothing here), the executable no-JS control contract
  - phase: 25-02
    provides: _persist_without_js(), _operate_with_keyboard(), _assert_hit_target(), _in_both_themes(), _no_js_page(cookies=)
  - phase: 24-01
    provides: companion/draw.py — the shared SVG geometry/emission primitives and the drawing contract
provides:
  - a schematic Orly runway map inside every runway card, drawn from device_config.RUNWAY_IDS and the designators in its own labels
  - runway_bearing_deg() — a designator parser that reads the LABEL before the id, so a drawing cannot contradict the text printed beside it
  - the map's paint through theme tokens, with its live selected state inside the one @supports selector(:has(*)) block and zero new accent consumers
  - a `cookies` passthrough on _persist_without_js(), so a scripts-blocked save can be proven in both shipped languages through the one java_script_enabled=False call site
affects: [25-04, 25-05, 25-06, 25-07, 25-08]

tech-stack:
  added: []
  patterns:
    - "A control that needs no enhancement needs no gate: D16 ships zero script and uses none of 25-01's `.js` gate"
    - "Geometry parsed from the registry's own user-facing label, never typed — the drawing cannot drift from its labels"
    - "A drawing's selected state joins the ONE feature query and pays for it in INK, not in a reserved accent"
    - "Sample a transitioning property only after the Web Animations `finished` promise, never at a guessed instant"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_browser_ux.py

key-decisions:
  - "Every card draws the WHOLE airfield with its own runway picked out, rather than one strip each or one shared canvas with floated labels — the only shape that is both a map and a 44px touch target"
  - "The bearing is parsed from the registry LABEL before the id, because Orly's first entry is keyed '3' (an ADP number) and labelled 'Runway 3 (07/25)'"
  - "The caption claims relative bearings and north-up, and deliberately does NOT claim relative lengths — the registry carries no length"
  - "The selected strip pays in ink (30% -> 55% -> solid --color-text), never in accent, so the header comment's exhaustive accent-reservation list is unchanged"
  - "The three runway photographs keep their slot, their route and their files; the map sits above them"

patterns-established:
  - "Mutation-drive the SOURCE ORDER of a fallback chain, not only its result: a registry where the two sources disagree is the only thing that pins 'label before id'"
  - "Scope an attribute assertion to the opening tag — `width=` on an <svg> is satisfied by its <rect> children"
  - "Compare a drawing against its container's CONTENT box, normalised for the container's own transform — the border box is 34px wider and passes an overflowing drawing"

requirements-completed: []

duration: 78min
completed: 2026-09-14
---

# Phase 25 Plan 03: D16's Runway Map Summary

**Three runway photographs became a schematic airfield map whose bearings are parsed from the designators in the registry's own labels — wrapped around exactly the native radiogroup that was already there, with zero new script, zero new accent, and the save proven by reaching disk with scripts blocked in both languages.**

## Performance

- **Duration:** 78 min
- **Started:** 2026-09-14T09:37Z
- **Completed:** 2026-09-14T10:55Z
- **Tasks:** 3 of 3
- **Files modified:** 5

## Task Commits

1. **Task 1: The schematic map, drawn from the registry's own designators** — `03c899a` (feat)
2. **Task 2: The map's paint and its selected state, inside the one feature query** — `72f2b91` (style)
3. **Task 3: The map measured where it has to be correct** — `f763b17` (test)

## The decision that mattered most

**Every card draws the whole airfield, not just its own runway.**

The plan's own wording admits two readings — "one SVG containing one strip per
entry, each wrapped in the existing `.runway-card` label shape" — and the
difference between them is the difference between a map and three unrelated
marks. An `<svg>` cannot contain a `<label>` or an `<input>`, so a single shared
canvas with three labels floated over it was the only way to get one literal
drawing, and it would have put all three touch targets on absolutely-positioned
overlays at 360 px. That is precisely the hit-area failure Task 3 exists to
measure, engineered in deliberately.

The other reading — each card draws one strip — keeps the control intact but
answers none of the objective's question. Three strips side by side still do not
say where these runways *are* relative to each other.

So each `.runway-card` carries a complete map of all three runways with its own
picked out, and comparing cards compares highlights on one shared picture. The
markup cost is n² strips (9 today, 16 with a fourth runway) of about 120 bytes
each. The measured consequence is the opposite of a cost: the cards got taller,
so the hit areas went from 25-02's pre-map **88 × 138** to **90 × 201 / 89 × 197
/ 88 × 197**.

This also produced the cleanest separation in the change. `runway-map__strip--this`
says *"this card's runway"* and is present on every card, selected or not;
selection is the label's own state. That is why `runway_fieldset(None)` renders a
map with nothing claimed instead of defaulting to one, and the check that proves
it is the same check that proves the class did not quietly become a selection
marker.

## What was measured

### Scripts blocked, 360 px, both shipped languages — the verdict is disk

```
en: {'field': 'tracked_runway', 'set': '06-24', 'held': '06-24',
     'reloaded': '06-24', 'stored': '06-24', 'before': '3', 'restored': '3'}
fr: {'field': 'tracked_runway', 'set': '06-24', 'held': '06-24',
     'reloaded': '06-24', 'stored': '06-24', 'before': '3', 'restored': '3'}
disk after both: 3
```

`'3'` → `'06-24'` → `'3'`, twice, through the real form's visible Save, read back
from the state directory after a genuine second GET. Nine maps and twenty-seven
strips render on that scripts-blocked page — asserted *after* the save, so the
rendering can never stand in for it.

### Hit areas, measured in this container and not inherited from a class

| Runway | visual box | **hit area** | reach (l, r, u, d) |
|--------|-----------|--------------|--------------------|
| `3` | 89.07 × 200.29 | **90 × 201** | (45, 44, 100, 100) |
| `06-24` | 87.34 × 196.36 | **89 × 197** | (45, 43, 98, 98) |
| `02-20` | 87.33 × 196.36 | **88 × 197** | (44, 43, 98, 98) |

All three clear the 44 px floor in both axes with room to spare, so
`control-density.md`'s **exempt-by-delegation** category keeps its precondition
and needs no new register entry. Trap 4 was taken seriously: this is
`_assert_hit_target()`'s real `elementFromPoint` probing in the runway row, not
`.control-hit-area`'s declared arithmetic borrowed from elsewhere.

### The drawing inside its card, and the page at 360 px

```
map 53.33 × 53.33  in a card CONTENT box of 53.33  (card border box 87.33)
map 53.34 × 53.34  in a card CONTENT box of 53.34  (card border box 87.34)
map 53.33 × 53.33  in a card CONTENT box of 53.33  (card border box 87.33)
display: block, margin-bottom: 8px
documentElement.scrollWidth 360 against clientWidth 360
```

### Paint, settled, in both themes

| | light | dark |
|---|---|---|
| context strip | `color(srgb 0.0902 0.0980 0.1216 / 0.3)` | `color(srgb 0.9451 0.9529 0.9647 / 0.3)` |
| own strip, unselected card | `color(srgb 0.0902 0.0980 0.1216 / 0.55)` | `color(srgb 0.9451 0.9529 0.9647 / 0.55)` |
| own strip, selected card | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |
| airfield ring (stroke) | `rgb(223, 215, 200)` | `rgb(42, 48, 64)` |

Eight values, none the SVG default, three different paints within each theme and
every one of them different between the themes. That is the floor, not the
ceiling: "not black" alone would pass against a drawing where all three strips
are the same flat grey.

### Keyboard only, with the pointer-free claim measured

```
saved on disk: 3   expected next: 06-24
{'keys': ['ArrowDown'], 'group': '06-24', 'active_value': '06-24',
 'pointer_events': [], 'recorder_proved': 1}
{'keys': ['ArrowDown', 'ArrowDown', 'ArrowUp'], 'group': '06-24',
 'pointer_events': [], 'recorder_proved': 1}
```

**Before (25-02, pre-map):** `'3'` → `'06-24'`, `pointer_events: []`,
`recorder_proved: 1`.
**After (this plan, post-map):** identical. The map was asked whether it *broke*
anything, and it did not.

And the live state, in the only configuration where the feature query earns its
place — one card checked by the keyboard, a different one saved, a third neither:

```
chosen (live)    rgb(23, 25, 31)
saved not live   color(srgb 0.0902 0.0980 0.1216 / 0.55)
neither          color(srgb 0.0902 0.0980 0.1216 / 0.55)
disk still: 3
```

## Re-derived counts, obtained by running

| Harness | before | after |
|---------|--------|-------|
| `companion/test_config_page.py` | 240 | **245** (+4 Task 1, +1 Task 2) |
| `companion/test_browser_ux.py` | 65 | **68** (+3 Task 3) |

CSS baselines, measured before touching the file and **unmoved** after:
`@keyframes` **4**, `@media (prefers-reduced-motion: reduce)` **3**,
`@supports selector(:has(*)) {` **1** (raw and comment-stripped).

Trap 2 was live on this tree: `grep -c '@supports selector(:has(\*))'` returns
**6**, not the 5 the briefing recorded — wave 1 added a sixth comment paragraph
quoting the at-rule. With the opening brace it is **1**, which is what both named
checks measure. The count moved between the briefing and this plan without
anything breaking, which is exactly why the brace-anchored form is the one to
use.

## Mutation testing

Every check below was reverted and proven to fail. Each mutation was confirmed to
have changed the line intended (the mutator prints the changed line numbers and
the before/after text, because trap 1 — `str.replace` hitting a comment that
quotes the constant — is silent when it happens).

### Task 1

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M1 | parse the id before the label | *an entry keyed '31-13' and labelled 'Runway 9 (07/25)' is drawn at 130 — its LABEL states 70, and a drawing that contradicts the label printed beside it is the whole defect this parse exists to make unreachable* |
| M2 | each map draws only its own runway | *expected 9 strips (3 cards x 3 registry entries), got 3* |
| M3 | drop `focusable="false"` | *expected the map's own `<svg>` tag to carry focusable="false"* |
| M4 | the own-runway class follows selection instead of the card | *expected exactly one own-runway strip per card (3), got 1* **and** *with nothing selected the own-runway strips vanished — that class marks which runway a card IS, never which one is chosen* |
| M5 | drop the reciprocal-pair requirement | *12/19 is not a reciprocal designator pair (they differ by 7, not 18) and was parsed as a bearing anyway* |
| M6 | raise instead of falling back (T-25-03-D) | *exception: ValueError('north-field')* |
| M7 | a colour decided in Python | *the map emits the colour '#1B4F72' — a colour decided in Python is correct in ONE theme and is invisible to companion/test_contrast_check.py* |
| M8 | drop the `<svg>`'s width/height | *expected the map's own `<svg>` tag to carry an explicit size route (width=), got '`<svg class="runway-map" viewBox="0 0 64 64" data-w="64" data-h="64" aria-hidden="true" focusable="false">`'* |
| M9 | the caption drops its schematic clause | *1 string(s) scanned from the D-05 module set have no companion.i18n_fr.CATALOG entry* **and** *1 CATALOG key(s) are never produced by the D-05 module scan* |

### Task 2

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M10 | the strip takes a stylesheet colour literal | *.runway-map__strip { must take its colour from var(--color-text) — a literal is correct in one theme only and is invisible to companion/test_contrast_check.py* |
| M11 | drop the strip's transition | *.runway-map__strip must declare the transition on its base rule, where it animates the live selected state and its no-:has() fallback from one declaration* |
| M12 | drop `max-width` | *.runway-map must declare 'max-width:' — its intrinsic size is wider than a runway card at the 360px contract floor* |
| M13 | drop `height: auto` | *.runway-map must declare 'height: auto;' …* |
| M14 | the airfield ring loses its token | *.runway-map__field { must take its colour from var(--color-border) …* |
| M15 | open a SECOND feature query | *expected exactly one '@supports selector(:has(\*)) {' block (the live-selection-state one …), got 2* **and** *expected exactly one @supports selector(:has(\*)) block, got 2* |
| M16 | live rule and fallback disagree | *the live selected strip and its --selected fallback must declare the same paint, got 'fill: var(--color-text);' against 'fill: color-mix(in srgb, var(--color-text) 80%, transparent);'* |
| M17 | the map paints a reserved accent | *.runway-map__strip--this { must take its colour from var(--color-text) …* |
| M18 | a class the markup emits has no rule | *the map emits class 'runway-map__field' and companion/static/style.css declares no selector for it — a class with no rule paints nothing at all* |
| M19 | a new `@keyframes` joins the file | *expected the @keyframes count to stay at 4, got 5* |

### Task 3 (the browser harness, ~3 min per run)

| # | Mutation | Quoted failure |
|---|----------|----------------|
| M20 | **the radios lose `form="settings-form"`** | *exception: AssertionError("_persist\_without\_js: the 'tracked_runway' control on /display belongs to no `<form>`, so with scripts blocked there is nothing that can post it at all")* |
| M21 | drop the `max-width` that keeps the drawing inside its card | *a map measures 64.00px inside a 53.33px card CONTENT box — the drawing is wider than the space the card has for it* |
| M22 | the radiogroup becomes a checkbox group | *one ArrowDown from '3' selected '3', expected the registry's next entry '06-24' — the map broke native radiogroup navigation* |
| M23 | delete the live `:has(input:checked)` strip rule | *the card the keyboard chose and the card that is merely SAVED paint their own strip identically ('color(srgb 0.0902 0.0980 0.1216 / 0.55)') — the live :has(input:checked) rule is doing nothing, and the map is showing the stored value rather than the visitor's choice* |
| M24 | saved-but-not-live no longer clears the full-ink strip | *the card the keyboard chose and the card that is merely SAVED paint their own strip identically ('rgb(23, 25, 31)') …* |

M20 is the mutation the plan asked for by name. It proves the no-JS check tests
**saving** and not rendering: the map still draws perfectly with the mutation in
place, and the check fails anyway.

## Checks that failed the vacuity question, and what was done

Four, and every one of them was found by running a mutation that was *supposed*
to fail and did not.

**1. The label-before-id order was inert against the shipped registry (M1).**
The first version of the bearing check asserted only that runway `'3'` is not
drawn at 030. It cannot be: `"3"` carries no reciprocal pair, so it parses as
nothing under *either* source order and falls through to the label regardless.
Swapping the two sources changed no angle at all. The check was strengthened with
a registry where the two sources genuinely disagree — id `31-13`, label
`Runway 9 (07/25)` — and now pins the order. The original clause is kept anyway:
it guards a different future implementation (`int(id) * 10`), which the new case
would not catch.

**2. `"width=" in svg` was satisfied by the `<rect>` children (M8).** Removing
the `<svg>`'s own `width`/`height` attributes failed nothing, because every strip
declares its own `width="6"`. The assertions are now scoped to the opening tag.

**3. The drawing was compared against the card's BORDER box (M21).** A runway
card is ~87 px wide and its content box is ~53 px. Removing `max-width` renders
the map at its intrinsic 64 px — overflowing the content box by 11 px, and still
comfortably inside the 87 px border box, so the check passed. It now reads
`getBoundingClientRect()` minus padding and border, normalised by the card's own
transform scale (see below). With that, 64.00 against 53.33 fails.

**4. Deleting the live `:has()` rule changed nothing a first-paint measurement
could see (M23).** At rest the saved card *is* the checked card, so the
no-`:has()` fallback paints the identical thing. The check now pulls the two
apart with the keyboard — one card checked, a different one saved, a third
neither — which is the only state in which the feature query earns its place. The
same three samples caught M24.

## Things that did not evaluate as predicted

**1. The paint check read an interpolation frame, and reported a theme that does
not invert.** First run of Task 3:

> `the selected paint is 'rgb(23, 25, 31)' in BOTH themes — it is not coming from a token that inverts, so one of the two themes is wrong`

The strips carry `transition: fill var(--motion-fast)` (180 ms). Switching the
theme starts that transition on every strip, and `getComputedStyle` immediately
afterwards returns a frame mid-flight: the dark sample read **rgb(41, 43, 49)**
for a strip whose settled dark value is **rgb(241, 243, 246)** — about 8% of the
way along. The `color-mix` samples gave it away by changing colour space
(`color(srgb …)` settled, `oklab(…)` mid-interpolation). Fixed by awaiting the
Web Animations `finished` promise on the strips, which is the browser's own
signal that the transition is over — never a timer, and an element with nothing
running returns an empty list and resolves at once, so this cannot hang or flake.

This is standing constraint 5 caught in the act, and it is worth noting the
constraint's converse: the intermittent-red risk here was *zero* and the
always-red risk was 100%, because the sample was taken in the same task as the
transition. A transition added by a *different* plan would have made this a
flake.

**2. `clientWidth` is an integer and the rounding alone failed a correct
drawing.** After fixing (3) above, the first content-box form used
`card.clientWidth - paddingLeft - paddingRight` and reported:

> `a map measures 54.41px inside a 53.00px card CONTENT box`

The map was correct; `clientWidth` had rounded 86.41 down to 85. The current form
reads `getBoundingClientRect()` and divides both the card's rect and the map's
rect by the card's own transform scale — because a *selected* card carries
`transform: scale(1.02)`, so its rect is in a scaled space while its padding and
border are not. With that, the numbers agree exactly: **53.33 in 53.33**.

**3. Counting `getAnimations()` right after a theme switch found zero.** The
transition-liveness probe counted before any style recalculation had created the
transitions. It now awaits one `requestAnimationFrame` — a real browser callback,
not a timer — and counts a running transition on every strip.

## Plan assumptions that turned out wrong

**1. "grep -c '@supports selector(:has(\*))' returns 5."** It returns **6** on
this tree. One real block, five comment paragraphs. The briefing's own advice
(anchor on the opening brace) is what made this a footnote rather than a failure.

**2. "relative bearings and relative lengths, not a survey."** The plan's Task 1
action asks the caption to claim relative *lengths*. `device_config.RUNWAYS`
carries no length for any entry — only `label`, `tag_text` and `empty_heading` —
so there is nothing to derive one from, and inventing plausible lengths would be
the same dishonest-state defect the sentence is trying to prevent. **Every strip
is drawn the same length and the caption claims only relative bearings, north
up, not to scale.** This is a deliberate departure from a plan sentence, recorded
rather than quietly adjusted.

**3. "draw.py's viewBox helper, if it landed."** `companion/draw.py` landed and
is used — every shape in the map comes from `draw.circle()`/`draw.rect()`, so the
escaping and the refuse-a-paint-decided-in-Python guard apply to all of them.
But `draw.unit_canvas()` emits the viewBox, the intrinsic size and `aria-hidden`
and **not `focusable`**, which the plan requires by name. The `<svg>` element is
therefore hand-written and its shapes are not. Recorded as an interface gap for a
future plan that wants to close it; `draw.py` is not this plan's file to edit.

**4. "the hit area is the thing at risk."** It was not, and the reason is the
decision at the top: because every card draws the whole airfield, the cards got
*taller*, and the narrowest measurement (88 × 197) clears the floor by a factor
of two in one axis and four in the other. The real 360 px risk turned out to be
the opposite one — an intrinsically-64 px drawing inside a 53 px content box —
and it is the one the mutations kept finding.

## Properties found inert, or load-bearing but unchecked

**Inert, and deleted: `stroke-width: 1` on `.runway-map__field`.** One user unit
is the SVG default, so the declaration changed nothing. It was written, mutated,
measured to break nothing, and removed — along with the part of the comment that
would have claimed it mattered. The comment now records that it was removed and
why, so the next reader does not re-add it.

**Load-bearing and now checked in the browser rather than in the stylesheet:**
`display: block` (an inline `<svg>` sits on a text baseline and leaves a
descender gap) and `margin-bottom` are asserted as *computed* values at 360 px,
not as declarations. That is the trap-4 discipline applied to two properties that
would otherwise have been "declared and assumed".

**Load-bearing and proven live: the `transition`.** It is not enough that the
rule declares one — a theme switch is measured to put a running animation on
every strip. Ironically the transition proved itself twice: once through that
check, and once by breaking the *paint* check before it was settled properly.

**Deliberately not added, and recorded so it is a choice rather than an
oversight:** a north marker inside the map. A tick at the top of the ring with no
letter beside it is ambiguous, and SVG `<text>` inside a viewBox scales with the
box and owes `draw.py`'s contract rule 5. The caption carries "north up" instead,
which is where text belongs.

## Does the map need script?

**No, and nothing during execution suggested otherwise.** The three native radios
were already a complete control: arrow-key navigation, a native selected state
and form submission all come from the browser. This plan wrapped a drawing around
them and used **none** of 25-01's `.js` gate — the phase's one-new-script budget
(`value-controls.js`) is untouched. The only mechanism that needed adding at all
was CSS, and the only thing CSS needed that a plain selector could not give was
`:has()`, which already had its one quarantined block.

## Standing constraints, each accounted for

| Constraint | Status |
|---|---|
| No-JS floor is absolute | Proven by **saving to disk**, at 360 px, in `en` and `fr`; M20 proves the check tests saving |
| Both themes load-bearing and measurable | Eight settled values recorded; every one differs between themes |
| Assert the FLOOR, not only the ceiling | context ≠ own ≠ selected within each theme; all three differ across themes; hit areas measured on all three cards |
| Mutate every CSS property added | M10–M19, M21, M23, M24; `stroke-width` found inert and deleted |
| Never sample at a guessed instant | The `finished` promise and `requestAnimationFrame`, never a timer — and it was the defect, not a precaution |
| Stage before mutating; `git checkout-index -f --`; clear `__pycache__` | The mutation runner does all three on every mutation, including in its `finally` |
| Mutation testing mandatory | 24 mutations, every failure message quoted above |
| Vacuity discipline | Four blind checks found and strengthened |
| `EXPECTED_CHECK_COUNT` re-derived by RUNNING | 240 → 245 and 65 → 68, both run |
| Sandbox baseline exactly 5 failing checks | Verified by name, before and after (below) |
| style.css guards; 360 px; motion budget | Zero stray terminators; `scrollWidth 360 / clientWidth 360`; 4 keyframes, 3 reduced-motion blocks, 1 feature query; no `interpolate-size`, no `calc-size(` |
| The three `runway-*.png` stay served | All three still on disk at their original sizes; the rendered `<img>`s report `naturalWidth` 1672 and `naturalHeight` 941/940 through the session-gated route |
| Tick no requirement | `requirements-completed: []`; `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` untouched |
| Design authority | No overlay drawer, no sticky day headers; the map reuses the existing selectable-card component wholesale |
| No model identifier in a pushed artifact | Trailers only |

## Threat register disposition

| Threat ID | Disposition | How |
|-----------|-------------|-----|
| T-25-03-A | mitigate | `handle_post()`'s whitelist-membership gate is untouched; no change to validation |
| T-25-03-B | mitigate | Every interpolation goes through `escape_html()`; asserted against a registry label containing `<script>"x"</script>`, and the map itself interpolates no registry string at all — only integers derived from one |
| T-25-03-C | accept | `/runway-image/{id}.png` unchanged and still session-gated; measured serving all three PNGs |
| T-25-03-D | mitigate | `runway_bearing_deg()` returns a stated fallback and never raises; M6 (raise instead) fails the check |
| T-25-03-SC | n/a | Zero packages installed in any ecosystem |

## Full suite

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` → **exactly the 5
baseline failures, verified by name**, unchanged from the pre-plan baseline:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … (WR-11)` — `companion/test_companion_app.py`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)` — `companion/test_companion_app.py`
3. `anomaly_active() runs on every page render and must never raise …` — `companion/test_status_pages.py`
4. `add_entry() returns ADD_FAILED (never raises) … (WR-11)` — `server/test_manual_resolutions.py`
5. `delete_entry() returns False (never raises) … (WR-11)` — `server/test_manual_resolutions.py`

`companion/test_browser_ux.py` runs and does **not** SKIP (68/68, ~180 s).
`ruff check .` clean.

## Known Stubs

None.

## Self-Check: PASSED

- `companion/pages/config_page.py` — FOUND
- `companion/static/style.css` — FOUND
- `companion/i18n_fr/display.py` — FOUND
- `companion/test_config_page.py` — FOUND
- `companion/test_browser_ux.py` — FOUND
- `companion/static/runway-3.png`, `runway-06-24.png`, `runway-02-20.png` — FOUND, unchanged
- `03c899a` — FOUND
- `72f2b91` — FOUND
- `f763b17` — FOUND
