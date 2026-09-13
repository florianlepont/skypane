# Phase 25: Companion dynamism III — "Controls" — Research

**Phase:** 25 — Companion dynamism III — "Controls": the modern controls that replace bare fields
**Researched:** 2026-09-13
**Depends on:** Phase 23 (executing — 23-10 in flight at the time of writing), Phase 24 (planned, NOT executed)
**Requirements:** CFG-46 … CFG-52 (assigned by this phase, see below)

---

## Summary

This phase replaces five bare form fields with purpose-built controls. Unlike
Phase 24 — where the artefact was a *picture* and the no-JS floor was satisfied
for free, because a server-rendered SVG arrives complete — **every artefact here
is a control, and a control that does not work is not a cosmetic shortfall but a
broken setting.** That single asymmetry is what shapes every plan below.

Four findings, each established by reading this tree rather than by reasoning
from the roadmap text:

1. **The no-JS floor has exactly one safe shape in this codebase, and it already
   exists four times over.** It is *not* "the control degrades gracefully". It is:
   **the native input that the form actually posts is rendered unconditionally by
   the server, and the new control is a layer above it that writes into it.**
   `.runway-card`/`.theme-chip`/`.frame-colours__row` are three live instances
   (a visually-hidden native `<input>` inside a `<label>` that is the whole hit
   target — selection works natively, with zero script); `dirty-state.js`'s quiet-
   hours presets are the fourth (a `type="button"` that writes into
   `form.elements["quiet_hours_start"]`, inert and harmless with scripts blocked).
   Every control in this phase must be one of those two shapes. A control whose
   only writer is `fetch`, or whose value lives only in a script, fails D-09 —
   and D-09 is a locked developer decision (`22-CONTEXT.md:133-135`), not a
   preference.

2. **The second half of the no-JS floor is `.js`, and it is already wired.**
   `nav-dropdown.js:31` does `document.documentElement.className += " js"` and
   `style.css:1078` consumes it as `.js .mobile-nav`. This is the mechanism that
   makes the *converse* defect unreachable: an affordance that can only work with
   a script (a drag handle, a drop zone, a ◀ ▶ pager) must be inside a wrapper
   that is `display: none` until `.js` is present. **Pitfall 3 from 23-RESEARCH
   ("an enhancement that renders but does nothing without script") is defeated by
   this one already-shipped class**, and no plan needs to invent it.
   *Caveat the plans must carry:* `.js` is added by `nav-dropdown.js`, so it is
   present only on the authenticated shell, and it is added at script-execution
   time, so a rule that *hides* under `.js` will flash. Hide by default and
   *reveal* under `.js` — never the reverse.

3. **This phase adds exactly ONE static script, and the arithmetic is written
   down rather than discovered.** The naive reading of the roadmap is five new
   controls → four or five new scripts (23-RESEARCH.md's coupling #13 predicted
   "six to eight"). The measured answer is one:
   - **D16 (runway map) needs no script at all.** It is the existing
     `.runway-card` radio group re-laid-out over one SVG; selection is native.
   - **D17 (dial) and D18 (slider)** are the same behaviour — steer a continuous
     value with pointer and keyboard, write it into the native input the form
     posts — so they share **one** new file.
   - **D5 (carousel)** grows `theme-preview.js`, which already listens to the
     theme radios and already reads `data-preview-src` off the changed radio's
     parent `<label>`. A carousel that moves the same radio group is that
     script's own subject.
   - **D19 (drop zone)** grows `panel-lookup.js`, which already owns the
     lightbox's upload forms and already rewrites their `action` by
     `setAttribute`.
   Each plan states its own answer to "new file or grow an existing one" and why.
   The one new file costs the three taxes 23-RESEARCH.md names (the deferred-script
   pin, the i18n fallback-literal scan, the route + ES5/forbidden-sink guard), and
   **25-01 pays all three in one place** rather than spreading them over four plans.

4. **Two of the five controls are re-scopes, not builds, and a plan that misses
   this will re-derive shipped work.** D17's stated "fixes B14" is already fixed
   (22-10 shipped `_normalised_time_html()`, the visible 24 h sibling beside each
   native time input) — the dial must **preserve** it. D5 is explicitly X6's
   deferred half: 22-10 already converted the whole Display page to
   `.theme-chip--compact` and recorded that the page-height target "is NOT met and
   cannot be by density alone — folding the grid behind the big preview is D5,
   Phase 23". So D5's success criterion is a **measured page height**, not a
   carousel's existence.

---

## Project Constraints (binding on every plan; each plan restates the ones it can violate)

- **CSP is `script-src 'self'`** (`companion/app.py:141-145`, asserted by exact
  equality at `test_companion_app.py`) — no inline script, no nonce. Every new
  static script needs **its own route constant and handler** in `companion/app.py`
  (there is no catch-all `/static/` handler; the pattern is repeated 16 times) and
  moves the deferred-script pin. **Current pin: fourteen** deferred scripts on the
  authenticated shell (`_fourteen_deferred_scripts_before_closing_body`,
  `companion/test_companion_app.py:4398-4477`), against **sixteen** `.js` files on
  disk — `login-card.js` is login-shell-only and `battery-trend.js` is emitted by
  Health's body. **Re-read that check before editing it**; Phase 23's outstanding
  plans may move it again. This phase moves it to fifteen, once, in 25-01.
- **The no-JS floor (D-09) is absolute** and this is the phase most at risk from
  it. Every control states its fallback as an **executable check**, not a promise:
  a `_no_js_page()` render, a real form submission, and an assertion that the
  value **persisted**. "It renders" is not the check; "it saves" is.
- **Minimum supported viewport 360 px**, no horizontal scrollbar on the page body.
  320 px assertions already in `test_browser_ux.py` stay — they pass and cost
  nothing.
- **Motion tokens** `--motion-fast` (180 ms) / `--motion-slow` (2 s) only;
  `interpolate-size` and `calc-size(` are **banned** (Chromium-only);
  `prefers-reduced-motion: reduce` is handled by the global block at
  `style.css:311-317` for plain transitions and must **not** be duplicated per
  rule. Reuse `@keyframes skypane-fade-in` / `.is-fading-in` and
  `skypane-bar-arrive` — **declare no new keyframes**.
- **Exactly ONE `@supports selector(:has(*))` block** (`style.css:2883`), pinned by
  two checks (`test_config_page.py:4002`, `:4232`). The specificity arithmetic at
  `style.css:2323-2345` is marked "verified, not to be re-derived". **D5 is the
  single largest threat to this** and D16 the second.
- **`style.css` is guarded at zero stray comment terminators** by
  `companion/test_status_pages.py`. Every new comment goes *inside* a block comment.
- **One writer per file per wave.** This project's rule, and the reason Phase 23
  needed 9 waves for 11 plans and Phase 24 needs 7 for 9.
- **Every check is mutation-tested** and must survive the vacuity question ("what
  would a *wrong* implementation do?"). `EXPECTED_CHECK_COUNT` is re-derived by
  **running** the harness, never by arithmetic, and appended as a new last
  assignment citing the plan and task.
- **Sandbox baseline is exactly 5 failing checks** (4 × WR-11 read-only, 1 ×
  `anomaly_active()`), verified by check **NAME**, never by failing-file count.
- **A page module may never import another page module**
  (`companion/pages/__init__.py`). Anything shared lives in `companion/battery.py`,
  `companion/layout.py`, `companion/frame_state.py`, `companion/draw.py` (Phase 24).
- **French parity** — `companion/i18n_fr/` carries a module per page;
  `companion/test_i18n.py` enforces it across `app.py`, HTML attribute literals and
  JS fallback literals (`var ALL_CAPS = "literal"` and `|| "literal"`).
- **Accessibility is load-bearing for this phase specifically.** Phase 23 shipped
  three real `role="switch"` controls and learned that a `role="status"` region
  **re-announces identical text on every keystroke unless gated**. Every control
  here declares its role, its keyboard interaction and its announced value **in
  the plan**, not at execution time.
- **The design authority is `Skill("sketch-findings-skypane")`**, not this file.
  Where the two disagree, the skill wins and this file is wrong.

### Two standing refusals that must not reappear

- **The overlay drawer.** Refused three times in
  `references/mobile-navigation.md:122-126` (full-screen overlay; slide-in drawer
  with dimming backdrop; `position: absolute` on `.mobile-nav`, the last
  established by **real-device testing** during 06.6.1-06) and locked again by
  `22-CONTEXT.md:137-141` D-10. **D5's "full grid behind a dialog" must not become
  a drawer**, and no control in this phase may introduce one.
- **Sticky day headers.** Struck by Phase 22's T4 and again by Phase 23's D7
  decision — every flight row already carries its own date. Nothing in this phase
  revisits it.

---

## User Constraints

### No CONTEXT.md exists for this phase

`/gsd-discuss-phase 25` was not run. The developer is unavailable for this
planning run, so **every decision that would have been an `AskUserQuestion` is
recorded in "Open decisions" below with its real trade-offs and a recommendation,
and is marked PROVISIONAL.** Plans proceed on the recommended option, clearly
flagged. Phases 23 and 24 both set this precedent.

**This phase must not be executed before the developer has seen Phases 23 and 24
on screen.** That is the developer's own instruction and it is sound: this phase
creates several new components, and a new component built on an unreviewed
foundation is the expensive kind of rework.

### Locked — from `22-CONTEXT.md` (still binding)

- **D-09** the regression floor and the no-JS floor (quoted above).
- **D-10** no overlay drawer, and *stop rather than fall back to it*.
- **D-11** sequencing is by dependency wave, never by calendar. **No durations,
  dates, week numbers or day estimates in any PLAN.md.**
- **D-12.1** absent-checkbox semantics: `display_enabled`/`quiet_hours_enabled`
  resolve absent → *leave unchanged*; `led_enabled` and the two notification
  checkboxes keep absent → `False`. A control that posts a partial body can
  silently switch off whatever it omits **within the same scope**.

### Locked — from `sketch-findings-skypane` (design authority)

- **360 px is the contract floor**; 320 px is out of contract but its existing
  assertions stay.
- **The touch-target register has four categories** — kept, traded, relocated,
  and **exempt-by-delegation**. `input.visually-hidden, select.visually-hidden`
  clears both 44 px minimums for a control whose wrapping `<label>` is the real
  hit target. **D16's runway map and D5's carousel are the fifth and sixth
  consumers of exempt-by-delegation, not new categories** — provided the label is
  ≥ 44 px in both axes, which each plan must *measure*.
- **`.copy-btn`/`.row-toggle`'s `::before` hit-area synthesis** (22 × 22 visual
  box, `inset: -11px`, real 44 × 44) is **the** pattern for a small control that
  needs a real hit area. D17's dial handles and D5's pager buttons reuse it rather
  than inventing a floor.
- **Accent reservation**: the exhaustive list lives in `style.css`'s own header
  comment. A new accent consumer must be added **there** first. The selected
  runway card's and selected theme chip's border/check/wash are already on it —
  D16 and D5 inherit those entries rather than adding new ones.
- **`.theme-chip--compact` is a SIZE-ONLY modifier declaring no selected-state
  rule of any kind**, and is now Display's only chip density. D5 must not give it
  one.
- **The compact `empty_state()` variant** exists (22-12) — reuse it.
- **Do not reintroduce the `>=960px` two-column `.config-form` grid** (removed by
  06.6.4.1 D-01).

### Claude's Discretion

Control geometry, emitter naming, the wave split, the exact keyboard step sizes,
and the internal structure of the new script — subject to every contract above.

### Deferred / Out of scope

- **A client-side canvas crop that reproduces `illustration_normalize.py`.** See
  Decision 5. The server stays the sole authority.
- **Animating the new controls beyond the two motion tokens.** No new keyframes.
- **Anything that reopens the overlay drawer or sticky headers.**
- D23's command palette, D24's guided first run, D15's share — Phase 26.

---

## Phase Requirements

| ID | Requirement (abridged) | Served by |
|----|------------------------|-----------|
| CFG-46 | The no-JS control contract, made executable once, plus the phase's one new script and the shared control vocabulary | 25-01, asserted by every control plan, closed by 25-08 |
| CFG-47 | D16 — the runway picked on one drawn map of Orly | 25-03 |
| CFG-48 | D17 — the 24 h quiet-hours dial | 25-04 |
| CFG-49 | D18 — the wake-interval slider with its two honest gauges | 25-05 |
| CFG-50 | D5 — the theme carousel, judged by Display's measured height | 25-06 |
| CFG-51 | D19 — drag-and-drop artwork with a preview that never becomes an authority | 25-07 |
| CFG-52 | The phase's regression floor: keyboard, touch target, 360 px, both themes, scripts blocked, motion budget, design system in step | 25-02, asserted by every plan, closed by 25-08 |

---

## Architectural Responsibility Map

| Concern | Owner today | Owner after this phase |
|---------|-------------|------------------------|
| Runway choice markup | `config_page.runway_fieldset()` — three `.runway-card` labels, each with an optional 338–371 KB `<img>` | unchanged function, rewritten body: one drawn SVG map, the same three native radios |
| The three `runway-*.png` photographs | `companion/static/`, served by `RUNWAY_IMAGE_ROUTE_PREFIX` | **unchanged and still served** — the map is a new drawing, not a replacement of that route (see Risk 2) |
| Quiet-hours values | two `<input type="time">` in `quiet_hours_group()`, `form="settings-form"` | **unchanged — they remain the submitting controls.** The dial is a layer above them |
| Quiet-hours presets | `dirty-state.js:161-179` writes into `form.elements[...]` | unchanged; the dial writes into the *same* two fields by the *same* mechanism |
| Wake interval value | `<input type="number" name="wake_interval_s">` in `wake_interval_group()` | **unchanged — it remains the submitting control.** The slider steers it |
| Battery-life arithmetic ("≈ N days") | **nothing — does not exist** | `companion/battery.py` (extended; Phase 24's CFG-39 owns the module, this phase adds the life estimate) |
| Freshness arithmetic ("a plane appears at most N min after passing") | `server/wake.py` owns cadence | derived in `companion/battery.py`'s sibling helper or read from `wake.py`; **never re-derived in a page module** |
| Theme choice markup | `config_page._theme_chip_grid_html()` — the ONE chip-grid renderer, four call sites | unchanged function and unchanged call sites; the *departures* grid gains a carousel presentation around it |
| Live theme preview | `theme-preview.js` + `_theme_live_preview_html()` | same script, extended to drive the carousel |
| Artwork upload | `airlines_page._resolve_upload_form_html()` / `_lightbox_replace_form_html()`, `<input type="file">` | unchanged forms; a drop zone and a preview are layered on |
| Image normalisation | `companion/illustration_normalize.py` (imports `server.plane.render._opaque_bbox()`) | **unchanged, and still the sole authority** |
| Continuous-value control behaviour | nothing | **`companion/static/value-controls.js`** (new — the phase's only new script) |

---

## The D-item dossier

### D16 — the runway picked on one SVG map of Orly (CFG-47)

**What exists.** `runway_fieldset()` renders three `<label class="runway-card">`,
each wrapping `<input type="radio" name="tracked_runway" class="visually-hidden"
form="settings-form">`, a `.runway-card__number` span, an optional `<img
class="runway-card__image" src="/runway-image/{id}.png">`, and a
`.runway-card__check` glyph. The row carries `role="radiogroup"` +
`aria-labelledby` + `aria-describedby`. Selection state is server-rendered
(`runway-card--selected`) **and** live (`:has(input:checked)` inside the one
feature-query block). `device_config.RUNWAY_IDS` is exactly three:
`"3"` (07/25), `"06-24"`, `"02-20"`.

**What the audit asks for.** "Pick the runway on one SVG map of Orly (reuse
`runway-*.png` drawings): tracked runway in accent, tap to select, label animates
below; one 300 px object on phone."

**The correction that matters.** The three `runway-*.png` files are **338–371 KB
photographs/drawings, not vectors** (23-RESEARCH.md, D16 row). "Reuse" therefore
means **redrawing Orly's three runways as SVG geometry in Python**, not embedding
them. This is a genuine new drawing and it must be honest: Orly has three
runways, their real bearings are 07/25, 06/24 and 02/20, and a map that draws
them at invented angles is a decoration pretending to be a diagram.

**Mechanism (no script).** One `<svg>` inside the existing `.runway-row`, with
one `<label>` **per runway overlaying its strip** — each label still wrapping the
same visually-hidden native radio. Selection is native (a radio group's arrow
keys move selection with zero script), the selected state comes from the rules
already inside the one `@supports` block plus the server-rendered `--selected`
class, and the "label animates below" is a plain `transition` already covered by
the global reduced-motion block.

**The two traps.**
1. **A `<label>` overlaying an SVG shape must still be ≥ 44 px in both axes.** A
   runway strip is long and thin; at 360 px, a 2-px-wide strip's label is not a
   touch target. The label must be a padded box around the strip (or the strip's
   hit area synthesised by `::before`, the `.copy-btn` pattern), and it must be
   **measured**, not asserted.
2. **The `:has()` block.** The selected-strip paint joins the existing four rules
   inside `style.css:2883`. Any diff introducing a second
   `@supports selector(:has(*)) {` fails two named checks.

**Accessibility.** The `role="radiogroup"` + `aria-labelledby` +
`aria-describedby` triple already on `.runway-row` is kept verbatim. The SVG
itself is `aria-hidden` and `focusable="false"` — the accessible names come from
the three labels, exactly as today. Announced value: the runway's registry label
(`device_config.runway_label()`), unchanged.

**No-JS fallback (one line):** *the three native radios are the control — the map
is their presentation, so with scripts blocked the runway is still chosen and
saved by the ordinary form.*

---

### D17 — the 24 h quiet-hours dial (CFG-48)

**What exists.** `quiet_hours_group()` renders: heading, caption (whose second
sentence is the computed delay sentence from `frame_state.delay_sentence_template()`),
three `type="button"` presets carrying `data-preset-start`/`-end`/`-enabled`
(written into the form by `dirty-state.js:161-179`), then `Start` and `End`
`<input type="time" required lang="{site_lang}" form="settings-form">`, each
followed by `_normalised_time_html()`'s **visible 24 h sibling** — which is B14's
shipped fix and must survive.

**What the audit asks for.** "24 h dial for quiet hours: two draggable handles on
a ring, the quiet arc draws itself, '23:00 → 07:00 · 8 h'; presets move the
handles; hidden synced `<input type="time">` for submission and no-JS; fixes B14."

**Three corrections.**
1. **B14 is already fixed.** The dial must preserve `_normalised_time_html()`, not
   re-derive it. A dial that removes the visible 24 h text reopens a closed defect.
2. **"Hidden synced input" is the wrong half to hide here.** The audit's phrase
   assumes the dial replaces the time inputs. It must not: a native
   `<input type="time">` is the only control on this page that a user can *type*
   into, and typing 23:00 is faster and more precise than dragging a handle to it.
   **The time inputs stay visible and stay the submitting controls.** The dial is
   an additional affordance above them, and it is the *dial* that lives inside the
   `.js`-gated wrapper.
3. **The arc is server-rendered; only the dragging is script.** With scripts
   blocked the user still sees a correct picture of the saved window — because the
   server knows `quiet_hours_start`/`quiet_hours_end` and can draw the arc from
   them. This is the same reasoning Phase 24 used for every drawing, applied to
   the static half of a control.

**Geometry.** A 24 h ring is aspect-locked, so it uses the **`viewBox` scheme**
(Phase 24's Risk 2 table), with an explicit size route so it cannot fall back to
the SVG default 300 × 150 (`layout.icon_html()`'s own docstring records that trap).
Its labels stay **outside** the SVG as HTML, the preferred escape from the
viewBox-containment rule.

**The hardest problem in the phase: a drag handle at 360 px.** 23-RESEARCH.md
names this explicitly. At 360 px the card's inner width is roughly 320 px; a ring
that fits leaves handles a few tens of pixels apart at a 23:00 → 00:30 window.
The plan must state a **minimum handle separation** and what happens below it, and
the handle's hit area must be the `::before` synthesis (`inset: -11px` around a
22 px box), not the drawn circle. **Measured at 360 px, not asserted.**

**Accessibility.** Each handle is a real `<button type="button">` inside the
`.js`-gated wrapper (never a bare `<div>`), carrying
`role="slider"` + `aria-valuemin="0"` + `aria-valuemax="1439"` +
`aria-valuenow` + `aria-valuetext` (the **local HH:MM**, not the raw minute
count) + an `aria-label` naming which end it is. Keyboard: `ArrowLeft`/`Right`
± 15 min, `PageUp`/`PageDown` ± 60 min, `Home`/`End` to the day's ends — stated
in the plan so it is not invented at execution time.
**The announcement gate Phase 23 learned:** the "23:00 → 07:00 · 8 h" readout must
**not** be a `role="status"` live region, because dragging fires it continuously
and a screen reader would read the same phrase on every pixel. The handle's own
`aria-valuetext` is what announces — that is the native, debounced path. The
readout is `aria-hidden`, exactly as `_normalised_time_html()`'s sibling already is.

**No-JS fallback (one line):** *the two native `<input type="time">` fields remain
visible and remain what the form posts, and the server-drawn arc still shows the
saved window — only the drag handles are withheld.*

---

### D18 — the wake-interval slider with two gauges (CFG-49)

**What exists.** `wake_interval_group()` renders a `<label for>` above an
`<input type="number" id name="wake_interval_s" min max placeholder>` with a
`.field-inline-value` unit sibling. `device_config.WAKE_INTERVAL_MIN_S = 60`,
`WAKE_INTERVAL_MAX_S = 3600` — so the audit's "1–60 min" is correct, but **the
field is in seconds** and the wire format must stay seconds.

Three properties of that function are load-bearing and a slider must not break
any of them:
- The `value` attribute is emitted **only** for a non-bool int inside the
  inclusive bounds. An out-of-range `value` fails HTML5 constraint validation and
  **blocks submission of the entire Settings form** — a live risk, because
  `deploy/skypane.env.example` ships `SKYPANE_SLEEP_S=30`, below the floor.
- On a rejected save the **raw submitted string** is echoed verbatim, deliberately
  bypassing that guard (D-07).
- B17's layout fix put the label *above* the control rather than wrapping it.

**Mechanism.** Add `<input type="range" min="60" max="3600" step="…">` with **no
`name` attribute** (so it can never submit and can never become a second source of
truth), inside the `.js`-gated wrapper, synced both ways with the number input by
`value-controls.js`. The number input is untouched and remains the poster.

**The two gauges, and the honesty problem.**
- *Freshness*: "a plane appears at most N min after passing." This is derivable
  and true — it is the wake interval itself, expressed the way a person
  experiences it. It must be computed from the **same** value the field holds and
  named as a bound ("at most"), not a typical.
- *Battery life*: "≈ 38 days." **This figure does not exist anywhere in the
  codebase.** `companion/battery.py` is 38 lines and contains only
  `battery_percent()`. A days-remaining estimate needs a per-wake energy cost,
  which this project has never measured — DEVICE-05's multi-day discharge run is
  *still deferred* (ROADMAP Phase 5). **A number invented from an unmeasured
  per-wake cost is exactly the dishonest-state defect Phase 22's X2/B2/B3 arc
  existed to remove.**
  The honest construction, and the one recommended: derive the estimate from the
  **observed** battery slope over `history_db.daily_battery_averages()` at the
  **cadence currently in force**, and present the slider's effect as a **relative**
  statement against that observation ("about twice as long as now" / "about half"),
  with an absolute figure shown **only** when there is enough observed history to
  support it, and an explicit "not enough history yet" state otherwise. The gauge
  must name what it is: an estimate from this device's own recent behaviour, not a
  datasheet figure. See Decision 3 — this is PROVISIONAL and it is the phase's
  most consequential open question.

**Accessibility.** A native `<input type="range">` is already a slider with full
keyboard support and a native `aria-valuenow`; **do not add `role="slider"` to it**
— that is the classic double-role error. Give it an `aria-label` and point
`aria-describedby` at the two gauges' text. The gauges themselves are plain text,
`aria-hidden` only if the number input's own value already announces them (it does
not — they are new information), so they are **not** hidden, and they are **not**
a live region either: they change on every slider step and would flood. The plan
states this explicitly.

**No-JS fallback (one line):** *the `<input type="number">` is untouched and still
the only thing that posts; the slider and the live gauges are withheld, and the
gauges' server-rendered values for the saved interval are still shown.*

---

### D5 — the theme carousel (CFG-50)

**What exists.** `_theme_chip_grid_html()` is the ONE chip-grid renderer, called
four times (departures `theme`, arrivals `theme_arriving`, calendar
`calendar_theme_id`, rule-add `rule_theme_id`), the last three compact. Each chip
is a `<label class="theme-chip">` wrapping a visually-hidden radio, a lazily-loaded
`<img class="theme-chip__preview" width="320" height="120">`, name, two swatch
dots, and a check glyph. `theme-preview.js` reads `data-preview-src` off the
changed radio's parent `<label>` to update the big live preview. The entire
selected-state treatment lives inside the **one** `@supports selector(:has(*))`
block with specificity arithmetic marked "verified, not to be re-derived".

**What the audit asks for.** "Theme picker as a carousel: big live preview with
◀ ▶ (keyboard, swipe), a row of 24 px colour dots, theme name; full grid behind
'See all themes' in a dialog. Display page drops below 1 500 px."

**The success criterion is the height, not the carousel.** 22-10 recorded that
X6's page-height target "is NOT met and cannot be by density alone". So this
plan's acceptance must include a **measured** Display page height, before and
after, at 390 px — and if the target is not met, the plan says so rather than
declaring victory on the carousel's existence.

**Mechanism, and why it needs almost no script.**
- The carousel is the **same radio group**, laid out as a horizontal
  **CSS scroll-snap** strip. Swipe is then native. Keyboard is native — arrow keys
  move selection *within a radio group* by default, and the browser scrolls the
  focused radio's label into view.
- The ◀ ▶ buttons are the only part that needs script (they call
  `scrollBy`/`scrollIntoView`), so they live inside the `.js`-gated wrapper, in
  `theme-preview.js`.
- "Full grid behind *See all themes*" is a **native `<details>`/`<summary>`
  disclosure**, not a dialog. A `<dialog>` cannot be opened without script, which
  would put eighteen themes behind a control that does nothing with scripts
  blocked — the exact Pitfall-3 defect. `<details>` works natively, already has a
  shipped chevron treatment (22-15 T3) and an existing disclosure sweep in the
  harness. **This is a deliberate deviation from the audit's word "dialog" and it
  is recorded as a decision, not a silent substitution** (Decision 4).

**The `:has()` trap, restated because it is the largest risk in the phase.** A
carousel that wants its own "current slide" state is one careless `@supports` away
from failing `test_config_page.py:4002` **and** `:4232`. The rule is: **a new
selectable-state rule joins the existing block at `style.css:2883`; it never opens
a second one.** And `.theme-chip--compact` must stay size-only — giving it a
selected-state rule would break the design system's recorded contract.

**Accessibility.** The grid keeps `role="radiogroup"`. The ◀ ▶ buttons are
`<button type="button">` with real labels ("Previous theme" / "Next theme") and
`aria-controls` pointing at the strip; they must **not** be `aria-hidden`
decorations, and they must not steal the radio group's own arrow-key semantics.
The dots row is `aria-hidden` — it duplicates the chips' own state.

**No-JS fallback (one line):** *the chip grid is the control and every chip is a
native radio, so the strip still scrolls, still selects and still saves with
scripts blocked; only the ◀ ▶ buttons are withheld.*

---

### D19 — drag-and-drop artwork with an instant preview (CFG-51)

**What exists.** Two upload forms, both `method="post"
enctype="multipart/form-data"` with `<input type="file" name="image"
accept="image/png" required>` and a submit button:
`_lightbox_replace_form_html()` (action rewritten by `panel-lookup.js`) and
`_resolve_upload_form_html()` (two call sites, one no-JS fallback with a real
action and one dialog copy with `action=""` rewritten by the same script).
`MAX_ILLUSTRATION_UPLOAD_BYTES = 4 MB` (`app.py:104`), enforced before the body is
read (`app.py:1445-1446`); `parse_single_uploaded_file()` **discards the
client-declared filename entirely**. `companion/illustration_normalize.py` crops
to painted content and re-centres into one shared frame, importing
`server.plane.render._opaque_bbox()` rather than reimplementing it — its own
docstring records that a *second, differently-thresholded* measurement silently
drifting from the first is precisely the debug session that created it.

**What the audit asks for.** "Drag-and-drop artwork upload with instant preview,
progress bar, client-side `<canvas>` crop matching `illustration_normalize.py`
(transparent, 450×132, centred); two cards per row on phone, aircraft types on
hover."

**Three clauses recommended for removal, each with its ground.**
1. **The canvas crop.** A client crop that "matches" the server is a second
   implementation of a contract whose own module docstring says the second
   implementation is the failure mode. 23-RESEARCH.md reaches the same verdict
   from the security side (V5/V12: the client crop must never become a trusted
   input). **Recommendation: no canvas at all.** The preview is an `<img>` from
   `URL.createObjectURL()` placed in a box with the *same aspect ratio* as the
   output frame and `object-fit: contain`, labelled as a framing preview. It shows
   the user what they picked and how it will be framed, with zero pixel code and
   zero drift surface. (Decision 5.)
2. **The progress bar.** `XMLHttpRequest.upload.onprogress` is real machinery for
   a ≤ 4 MB upload to a household server. `submit-guard.js` already disables a
   form's submit button on submit, app-wide. **Recommendation: reuse that**, and
   add a "Uploading…" label rather than a bar. (Decision 5.)
3. **"Aircraft types on hover"** is a tooltip, and this project converted its
   tooltips to full local timestamps behind copy controls under CFG-28 precisely
   because hover is unreachable by touch. **Recommendation: render the aircraft
   types as visible card text**, or drop the clause. (Decision 5.)

**Mechanism.** The existing `<input type="file">` + submit button are untouched
and remain the submitting path. A drop zone is layered over the existing
`.resolve-upload-zone` / `.lightbox__replace-zone` wrappers, inside the `.js`
gate, listening for `dragover`/`drop` and assigning to `input.files` via
`DataTransfer` — which keeps the **native input** as the value holder, so the
submitted bytes travel the same path whether the file was dropped or chosen.

**Security posture (unchanged, and each plan restates it).** The server normalises
unconditionally; the client-declared filename is still discarded; the 4 MB cap is
still enforced before the body is read; the drop zone changes the **affordance**,
not the parser.

**No-JS fallback (one line):** *the file input and its submit button are the
control and are rendered unconditionally, so artwork is still chosen and uploaded
with scripts blocked; only the drop target and the preview are withheld.*

---

## The no-JS control contract (what CFG-46 makes executable)

Derived from Pitfall 3 and from the four shapes already in this tree. A plan may
only deviate with a written reason in its own SUMMARY.

1. **The server renders the submitting control unconditionally.** Every value this
   phase can change is held by a native `<input>`/`<select>` that the server emits
   on every render, regardless of scripts. There is no path in which a setting's
   only writer is a script.
2. **The enhancement writes into that control; it never holds the value.** A
   handle, a slider, a drop zone or a pager sets `input.value` / `input.files` /
   `input.checked` and fires the form's existing dirty-state notification. No
   parallel state.
3. **An affordance that cannot work without script does not render without
   script.** It lives inside a wrapper hidden by default and revealed under the
   existing `.js` class — never the reverse, which flashes.
4. **Every control's fallback is proven by submission, not by rendering.** The
   check is: open the page through `_no_js_page()`, operate the native control,
   submit the real form, reload, assert the value **persisted**. A check that only
   asserts "the input is present" is vacuous — a broken control would pass it.
5. **Every control is operable by keyboard**, with its keys named in its plan, and
   its announced value is `aria-valuetext`/the native control's own — never a
   `role="status"` region that re-announces on every keystroke.
6. **Every hit area is ≥ 44 px in both axes at 360 px**, or it is a named entry in
   the design system's touch-target register with a stated justification. Measured
   in a real browser.
7. **Colour comes from a theme token through a class.** A control correct only in
   light mode is a **defect**, not a polish item.

---

## Risk 1 — the phase's own dependencies are not yet on disk

Phase 25 depends on Phase 23 (executing: 23-10 in flight, 23-11 outstanding) and
inherits facts from Phase 24 (**planned, not executed**). Concretely:

- `companion/draw.py` **does not exist yet** — Phase 24 creates it. D17's arc and
  D16's map should use it if it is there when this phase executes, and each plan
  must therefore state its dependency as a **command to re-run**, not a fact.
- `companion/battery.py`'s gauge fraction and threshold are **Phase 24's CFG-39
  work**. D18's life estimate extends the same module; it must not create a
  second one.
- `test_browser_ux.py`'s **theme switch helper is 24-02's**. This harness has
  never once switched theme. If this phase needs it — and CFG-52 does — it
  **depends on 24-02 rather than building a second one**.
- Every line number and `grep -c` baseline quoted in a plan is stale by
  construction. **State baselines as commands to re-run**, exactly as 23-01 and
  24-01 did.

**Mitigation, and it is structural:** every plan's `<interfaces>` block opens with
the commands that re-derive its own baselines, and no plan quotes a count as a
fact.

## Risk 2 — replacing a photograph with a drawing is a claim about reality

The three `runway-*.png` files are real imagery of Orly. A hand-drawn SVG map is a
*model*, and a model drawn from memory would put runways at angles they do not
have. Two honest options:
- **(a)** Draw the three runways from their actual designators (07/25 ≈ 070°/250°,
  06/24 ≈ 060°/240°, 02/20 ≈ 020°/200°) — the designators *are* the bearings, to
  the nearest ten degrees, by ICAO convention. This is derivable from
  `device_config.RUNWAYS`' own labels with no external source, and it is
  self-documenting.
- **(b)** Keep the photographs as the card imagery and make only the *selection
  affordance* a map.

**Recommendation: (a)**, because the bearings come from data already in the repo
and because a diagram whose geometry is derived from its own labels cannot drift
from them. The plan must state that the map is schematic — relative bearings and
relative lengths, not a survey — and the caption must not imply a scale drawing.
The PNG route stays served either way (Decision 2).

## Risk 3 — "correct in light mode only", again

Phase 24 adds four drawings and a guard against unpainted/hard-coded shapes. This
phase adds five **controls**, whose failure modes are the same plus two more:
a `:hover`-only affordance (unreachable by touch) and a focus ring that vanishes
against the new surfaces. `companion/test_contrast_check.py` already computes
contrast for this app's tokens and is where a new colour **pair** goes. The global
focus floor is already inside the one `@supports` block (22-15 T15) and every new
interactive element inherits it — a plan that adds its own focus rule is
duplicating a solved problem.

## Risk 4 — a parallel agent is editing this tree right now

At the time of writing, plan **23-10** is executing in this same working tree and
owns `companion/static/style.css`, `companion/static/theme-preview.js`,
`companion/pages/{config,home,history,airlines}_page.py`,
`companion/test_config_page.py`, `companion/test_view_pages.py` and
`companion/test_browser_ux.py`. **Phase 25 cannot begin until Phase 23 closes**
(its own `Depends on`), so this is not a merge risk for execution — but it is a
staleness risk for every baseline quoted here. See Risk 1's mitigation.

---

## Validation Architecture

**What must be validated, and by what instrument:**

| Dimension | Instrument | Where |
|-----------|-----------|-------|
| The no-JS contract holds for every control (operate → submit → **persist**) | real Chromium via `_no_js_page()`, scripts blocked | `companion/test_browser_ux.py` |
| A JS-only affordance does not render without script | real Chromium, scripts blocked: the `.js`-gated wrapper is absent from the layout | `companion/test_browser_ux.py` |
| Every control is keyboard-operable, with its named keys | real Chromium, keyboard only, no pointer events | `companion/test_browser_ux.py` |
| Hit areas ≥ 44 px in both axes at 360 px | real Chromium `getBoundingClientRect()` at `VIEWPORT_MIN_SUPPORTED` | `companion/test_browser_ux.py` |
| 360 px, no horizontal body scrollbar, with every control present | real Chromium, `document.body.scrollWidth` vs `clientWidth` | `companion/test_browser_ux.py` |
| Legible in both themes | real Chromium in each theme (24-02's helper) | `companion/test_browser_ux.py` |
| The `@supports selector(:has(*))` block count stays exactly ONE | stylesheet source scan | `companion/test_config_page.py` (two existing checks) |
| The deferred-script pin moves exactly once, to fifteen | rendered-shell scan | `companion/test_companion_app.py` |
| The new script is served, ES5-subset, and free of forbidden sinks | route + source scan (existing per-file pattern) | `companion/test_companion_app.py` |
| Markup contracts (roles, `form=` association, the preserved B14 sibling, the untouched number-input guard) | direct unit assertions on each builder's return | `companion/test_config_page.py` |
| Airlines' upload forms unchanged in action/enctype/parser path | direct unit assertions | `companion/test_status_pages.py` |
| Motion budget unmoved; no new keyframes; no new reduced-motion block | existing 23-01 guard | `companion/test_companion_app.py` |
| French parity | existing i18n sweep, including JS fallback literals | `companion/test_i18n.py` |
| Display's measured page height (D5's actual success criterion) | real Chromium at 390 px, before/after recorded | `companion/test_browser_ux.py` |

**Sampling adequacy (the Nyquist question).** Each control must be asserted at
**at least** these states, because each is a real state of this deployment:
scripts on / scripts blocked; keyboard-only / pointer; light / dark; 360 px /
390 px / 1280 px; and — per control — the empty or unset value (no quiet-hours
window saved, no wake interval saved, no artwork uploaded, a runway id absent from
`images_available`), the boundary value (`WAKE_INTERVAL_MIN_S` and `MAX_S`
exactly; a quiet window that **wraps midnight**; a window whose two ends are
equal), and the rejected-save echo path. A check that only exercises a comfortable
value is vacuous for most of the states this app actually reaches.

**The wrapping-midnight case deserves naming on its own:** the default window is
23:00 → 07:00, which wraps. A dial that assumes `end > start` draws an 8-hour arc
as a 16-hour one, and a freshness gauge that assumes it draws the wrong bound.
This is the single most likely arithmetic defect in the phase.

---

## Recommended plan shape

Eight plans, seven waves. Wave 1 is parallel (two plans, disjoint files); the rest
are serial because `companion/pages/config_page.py` is written by four plans and
`companion/static/style.css` by six, and this project's rule is **one writer per
file per wave**.

| Plan | Wave | Owns | Depends on |
|------|------|------|-----------|
| 25-01 | 1 | `companion/static/value-controls.js` (new), `companion/app.py`, `companion/layout.py`, `companion/static/style.css` (shared control vocabulary), `companion/battery.py`, `companion/test_companion_app.py` | — |
| 25-02 | 1 | `companion/test_browser_ux.py` (the contract helpers; zero net checks) | — |
| 25-03 | 2 | D16 — `config_page.py`, `style.css`, `i18n_fr/config.py`, `test_config_page.py`, `test_browser_ux.py` | 25-01, 25-02 |
| 25-04 | 3 | D17 — `config_page.py`, `style.css`, `value-controls.js`, `i18n_fr/config.py`, `test_config_page.py`, `test_browser_ux.py` | 25-01, 25-03 |
| 25-05 | 4 | D18 — `config_page.py`, `style.css`, `value-controls.js`, `i18n_fr/config.py`, `test_config_page.py`, `test_browser_ux.py` | 25-01, 25-04 |
| 25-06 | 5 | D5 — `config_page.py`, `style.css`, `theme-preview.js`, `i18n_fr/config.py`, `test_config_page.py`, `test_browser_ux.py` | 25-01, 25-05 |
| 25-07 | 6 | D19 — `airlines_page.py`, `style.css`, `panel-lookup.js`, `i18n_fr/airlines.py`, `test_status_pages.py`, `test_browser_ux.py` | 25-01, 25-02 |
| 25-08 | 7 | the design system, the coverage ledger, the decision list, the phase gate | all |

*25-07 (D19) is the one control plan that touches neither `config_page.py` nor the
settings form. It is placed in wave 6 only because it writes `style.css`; if a
future executor wants more parallelism, the honest way to get it is to give D19 its
own stylesheet section landed by 25-01, not to break the one-writer rule.*

---

## Open decisions recorded for the developer (all PROVISIONAL)

1. **The phase's script budget: ONE new file.** `companion/static/value-controls.js`
   serves D17's dial and D18's slider (one behaviour: steer a continuous value,
   write it into the native input the form posts). D5 grows `theme-preview.js`,
   D19 grows `panel-lookup.js`, D16 needs none.
   *Alternatives:* two new files (one per control — clearer file names, two sets of
   the three taxes, two copies of the same clamp/round/keyboard code); or zero new
   files by growing `dirty-state.js`, which already writes into these exact fields
   for the quiet-hours presets — cheapest in taxes, but it puts a drag interaction
   inside the save-bar script, whose subject it is not.
   *Plans proceed on one new file.*
2. **D16 keeps the three `runway-*.png` photographs served.** The map is an
   addition; the existing `/runway-image/{id}.png` route, its session gate and its
   `images_available` fallback all stay. *Alternative:* delete the route and the
   three 338–371 KB files, saving ~1 MB of repo and one route — but throwing away
   real imagery for a schematic is not obviously an improvement, and it is
   irreversible in a way the addition is not. *Plans proceed on keeping them.*
3. **D18's battery-life gauge is relative-with-a-conditional-absolute, not a flat
   "≈ 38 days".** The per-wake energy cost has never been measured (DEVICE-05's
   discharge run is still deferred), so an absolute figure computed from an assumed
   cost would be invented. The recommendation derives the estimate from this
   device's own observed slope at the cadence in force, states the slider's effect
   relatively, and shows an absolute figure only when the observed history supports
   it — with an explicit "not enough history yet" state otherwise.
   *Alternatives:* (a) ship the absolute figure from an assumed per-wake cost —
   rejected, it is the dishonest-state defect Phase 22 spent a phase removing;
   (b) drop the battery gauge entirely and ship only the freshness gauge — honest
   and much cheaper, and a legitimate choice if the developer would rather wait for
   real discharge data. **This is the phase's most consequential open question.**
   *Plans proceed on the relative-with-conditional-absolute construction.*
4. **D5's "full grid" goes behind a native `<details>` disclosure, not a
   `<dialog>`.** A `<dialog>` cannot be opened without script, which would hide
   eighteen themes behind a control that does nothing with scripts blocked.
   `<details>` is native, already has a shipped chevron treatment and an existing
   harness sweep. *Alternative:* a `<dialog>` with the `<details>` as its own no-JS
   fallback — two renderings of one grid, and a duplicate-id surface.
   *Plans proceed on `<details>`.* **Note this is a deliberate deviation from the
   audit's wording and is recorded as such.**
5. **D19 sheds three of the audit's clauses:** no client-side canvas crop (the
   server's normaliser is the sole authority and its own docstring names the
   second-implementation drift as the failure it exists to prevent); no progress
   bar (`submit-guard.js` already disables on submit — reuse it with an
   "Uploading…" label); no hover-only aircraft types (hover is unreachable by
   touch, the same ground CFG-28 used). *Alternative:* build all three as
   specified. *Plans proceed on the reduced scope, with each removal stated in the
   plan rather than silently dropped.*
6. **D5's success is measured as Display's page height at 390 px**, recorded
   before and after, because 22-10 already established that density alone cannot
   reach X6's target. If the carousel does not reach it either, the plan reports
   the number rather than declaring the item done.
7. **No CONTEXT.md** — this phase was planned without `/gsd-discuss-phase`. Every
   decision above would normally have been the developer's.
8. **No UI-SPEC.md.** Phases 23 and 24 were both planned without one, and
   `22-UI-SPEC.md` already carries rows for D16/D17/D18/D19 (`:629-632`); the
   `sketch-findings-skypane` skill is the standing authority. 23-RESEARCH.md
   nonetheless observed that "this is the phase most likely to need its own UI
   spec, as Phase 22 had". *Plans proceed against the skill plus `22-UI-SPEC.md`;
   if the developer wants a dedicated spec, `/gsd-ui-phase 25` before execution is
   the cheap moment to add one.*

---

*Research completed: 2026-09-13*
*Method: direct reading of this tree, plus the inherited findings of 23-RESEARCH.md
and 24-RESEARCH.md. No web research was needed — every question this phase raises
is answered by code already in the repository or by a decision already recorded in
`.planning/`.*
