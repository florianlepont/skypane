# Phase 27 — Research

**Phase:** 27 — Companion review feedback: the defects and the noise the developer found on the real app
**Researched:** 2026-09-14
**Method:** direct reading of the shipped tree on `claude/companion-review-feedback` (based on `main`,
phases 23/24/25 merged and deployed). No web research: every question this phase asks is a question
about *this* codebase.

---

## 0. One correction to the brief, found by reading

The brief and CONTEXT.md name the save-to-disk proof helper **`_operate_submit_persist()`**. **That
function does not exist under that name.** The real helper is:

```
companion/test_browser_ux.py:1589   def _persist_without_js(browser, base_url, route, field, value, read_back, ...)
companion/test_browser_ux.py:1761   def _persist_once(...)          # the inner GET→operate→submit→GET sequence
companion/test_browser_ux.py:1673   (the file-input variant, added by 25-07)
```

25-02 gave `_persist_without_js()` its `operate` callback — that is the "operate-submit-persist" shape
the brief is naming, and `companion/test_browser_ux.py:685` refers to it in prose as "25-02's
operate-submit-persist". **Every plan must call the real name.** A plan that writes
`_operate_submit_persist()` will not run.

---

## 1. The defect: why the arc and the caption cannot follow the handles

### 1.1 What is actually on the page

Three surfaces describe the quiet-hours window, and they are produced by three unrelated mechanisms:

| Surface | Produced by | Updated client-side? |
|---|---|---|
| Two `<input type="time">` (`quiet_hours_start`, `quiet_hours_end`) | server, `quiet_hours_group()` (`config_page.py:2982`) | **yes** — `value-controls.js` `writeValue()` |
| Two handles, each `<div class="value-control …" style="--value-fraction: …">` | server, `quiet_dial_handles_html()` (`config_page.py:2859`) | **yes** — `paint()` rewrites `--value-fraction` on **the wrapper** |
| The arc — one `<circle class="quiet-dial__arc">` with `stroke-dasharray` + `transform="rotate(…)"` as **presentation attributes** | server, `quiet_dial_svg()` (`config_page.py:2695`) | **NO** |
| The caption — `<p class="time-value quiet-dial__readout" aria-hidden="true">23:00 → 07:00 · 8 h</p>` | server, `quiet_dial_readout_html()` (`config_page.py:2941`) | **NO** |

### 1.2 The structural cause, confirmed in source

`value-controls.js` `paint()` (`companion/static/value-controls.js:491`) ends with:

```js
wrapper.style.setProperty(FRACTION_PROPERTY, String((value - bounds.min) / span));
```

`FRACTION_PROPERTY` is `--value-fraction` and it is written **on the wrapper** — and each handle has
its own wrapper. The file's own header states the design intent plainly: *"This file never holds a
value… no map keyed by element, no cached number."* **One wrapper, one value.** There is no element in
the model that knows both values, so there is nothing an arc or a span sentence could be a function
of. This is not a bug in `paint()`; it is the absence of a pair in the model.

Two more constraints the file states about itself and which any fix must respect:

- *"This file writes no copy."* `aria-valuetext` and every readout are filled from a **server-rendered,
  already-translated template** with one token substituted. A French reader can never be dropped into
  English by touching a control.
- *"25-05's battery gauge prints an absolute 'days left' figure only when the device's OWN observed
  history supports one, and that sentence is rendered by the server, OUTSIDE every readout, and never
  touched here."* The honesty corollary.

### 1.3 The existing readout seam — the thing that already solves half of this

`paintReadouts()` (`value-controls.js:468`) is the file's answer to "a sentence about the value":

- found by the **field's name** (`data-value-readout="quiet_hours_start"`), deliberately **not** by
  containment, because readouts must be correct with scripts blocked and the wrapper is `.js`-gated;
- the wording is `data-value-readout-text`, a server-rendered translated template with a token;
- `data-value-readout-base` — **a readout whose value equals its declared base says NOTHING**, which is
  the state every page load renders.

That last rule is directly reusable, and it is the precedent for the "say nothing rather than lie"
option below.

### 1.4 Option A — a CSS-only representation both handles feed (RECOMMENDED for the arc)

Add to `value-controls.js` one small, generic capability: **a wrapper may declare that it also
publishes its fraction, under a named custom property, on the nearest ancestor carrying a pair
marker.** Two new attributes, no new file, no new route:

```
data-value-pair            (on the shared ancestor — .quiet-dial)
data-value-pair-property   (on each wrapper: "--quiet-start-fraction" / "--quiet-end-fraction")
```

`paint()` gains three lines: after writing its own `--value-fraction`, if the wrapper declares a pair
property, walk to the nearest `[data-value-pair]` ancestor (`ancestorWith()` already exists,
`value-controls.js:~250`) and `setProperty()` there too. **Still no parallel state**: the value written
is the value just read back off the native field, exactly like the mirror.

The server emits the same two properties as the ancestor's initial inline style, from the same
`quiet_window_span()` triple that draws the arc. So **at rest the CSS-driven geometry and the
presentation-attribute geometry are the same numbers**, which is itself an assertable property.

Then the arc is drawn from those two properties in CSS. The `<circle>` keeps its server-rendered
`stroke-dasharray`/`transform` **unchanged** — that is the no-JS floor and the saved-value authority —
and a `.js`-scoped rule overrides them. This works precisely because of the fact `quiet_dial_svg()`'s
own docstring already records: *"a CSS stroke-width of any specificity beats a presentation
attribute."* The same is true of `stroke-dasharray` and of `transform`.

**The geometry, and the one hard part.** The sweep is `(end − start) mod 1`; the arc wraps
(23:00→07:00 gives `0.2917 − 0.9583 = −0.667`, which must read as `0.333`). Three ways to get it:

1. **`pathLength="1"` + `mod()`.** Put `pathLength="1"` on the `<circle>` so dash units are fractions
   of the circumference regardless of radius, then
   `stroke-dasharray: calc(mod(var(--quiet-end-fraction) - var(--quiet-start-fraction), 1)) 1;` and
   `transform: rotate(calc(-90deg + var(--quiet-start-fraction) * 360deg))`. CSS `mod()` is Values 4,
   shipped in Chrome 125 / Firefox 118 / Safari 15.4. **Cleanest, and no JS arithmetic at all.**
   Risk: the harness Chromium's version must support `mod()` — **verify by running before committing
   to it** (`CSS.supports('width', 'calc(mod(1,1) * 1px)')`).
2. **Publish the sweep itself as a third property.** The script already knows both values at paint
   time; computing `(end − start + 1) % 1` in JS is two lines and is arithmetic on values, not copy.
   No `mod()` dependency. **This is the safe fallback and needs no CSS feature at all.**
3. Layered conic-gradients — rejected: a conic-gradient is a background, not a stroke, so it cannot
   reuse the ring's stroke width, cap or token colour, and a wrapping window needs two layers.

**Recommendation (provisional): option A with sub-option 2** — the script publishes
`--quiet-start-fraction` and `--quiet-sweep-fraction` on the shared ancestor; CSS draws with
`pathLength="1"`, `stroke-dasharray` and `transform`. Sub-option 1 is strictly nicer and should be
adopted **if and only if** a run proves `mod()` resolves in the harness browser. Either way the
server's presentation attributes stay and stay authoritative with scripts blocked.

### 1.5 Option B — the script recomputes the SVG geometry (REJECTED for the caption, tolerable for the arc)

For the **arc**, B is merely redundant with A: it would have the script write
`setAttribute("stroke-dasharray", …)`, re-deriving `draw.unit_circle_dash_array()` in JS — a second
implementation of a drawing primitive this codebase deliberately centralises in `companion/draw.py`.

For the **caption** B is worse than redundant, it is **forbidden by the file's own contract**. The
caption is `"%s → %s · %s"` where the third slot is `layout.duration_text()` — this app's **one**
length-of-time ladder, translated, coarse by construction. `quiet_dial_readout_html()`'s docstring
names the reason: *"a second duration ladder in a page module is precisely the drift that ladder exists
to prevent."* A duration ladder in a **script** is the same drift with a language boundary added, and
`value-controls.js` says four separate times that it writes no copy.

### 1.6 The caption — three options, none free

| # | Shape | Verdict |
|---|---|---|
| C1 | Split the caption into three elements: the two endpoints become ordinary `data-value-readout`s (the existing seam, one token each, zero new machinery); the **duration** segment carries `data-value-readout-base` set to the saved span, so it **blanks itself** the moment the pair moves and is re-rendered by the server on save | **RECOMMENDED (provisional).** Reuses two shipped mechanisms verbatim. Honest by construction: it never states a duration it cannot support — exactly D18's rule applied to a different sentence. Cost: the duration visibly disappears during a drag. |
| C2 | Server emits the ladder's **thresholds** and one translated template **per unit** on the element; the script picks a unit by arithmetic and substitutes one number | Keeps the duration live and still writes no copy — but it moves the ladder's *shape* into JS even though its words stay in Python. More machinery for one sentence. Hold as the fallback if C1's blanking is rejected in review. |
| C3 | Leave the caption stale | **This is the shipped defect.** Refused. |

### 1.7 The ONE check (this is the phase's centrepiece)

Not three checks. **One** check, in `companion/test_browser_ux.py`, whose whole subject is *agreement*:

1. Load Settings. Record the pre-interaction pair.
2. Interact — a real drag on the end handle, **and** separately a preset press (both paths were
   reported working for the handles and broken for the arc, so both must be covered by the same
   agreement assertion).
3. Decode **four surfaces into one canonical `(start_minute, end_minute)` pair**:
   - the two native inputs' `.value`;
   - the two handles' `aria-valuenow`;
   - the arc's **resolved** geometry, read with `getComputedStyle` (the custom properties on
     `[data-value-pair]`, and the resolved `stroke-dasharray`/`transform` on `.quiet-dial__arc`),
     converted back to minutes;
   - the caption's `textContent`, parsed back to two clock times.
4. Assert **the set of the four decoded pairs has exactly one member** — and that that member is the
   pair the interaction *requested*, and that it **differs from** the pre-interaction pair.

Why the last two clauses matter: without "equals what was requested" the check passes on a page that
froze all four surfaces together; without "differs from before" it passes on a no-op interaction. Those
are the vacuity answers.

**The mutation that proves it:** delete the pair publication from `paint()` (or the `.js` CSS override).
The handles still move, the fields still hold the new value, the value still saves — and this check
**fails**, naming which surface disagreed. That is the shipped defect, reproduced on demand. This is
the single most important mutation in the phase and its failure message must be quoted in the plan.

---

## 2. Correction 1 — no save button. The three things that must be settled

### 2.1 What exists today

| Piece | Where |
|---|---|
| `dirty-state.js`, 598 lines — delegated `change`/`input` listeners filtered to `e.target.form === form` (22-01's B1 fix), the `.dirty-bar`, the section-aware `[data-dirty-count]` copy, the private `notifyDirty()` | `companion/static/dirty-state.js` |
| `STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"` on the real submit; the CSS contract `.js [data-static-save-fallback] { display: none; }` landed by 06.6.4.1-01, later narrowed to `.dirty-ready.dirty-shown [data-static-save-fallback]` | `config_page.py:758`, `style.css:1552–1568`, emitted at `config_page.py:5175` |
| Six translated connector words + a seventh progress word, all as `data-*` attributes on `.dirty-bar` with documented English fallbacks | `config_page.py:762–800` |
| The leave-guard / confirm surface | `companion/static/submit-guard.js`, `companion/static/confirm-submit.js` |

### 2.2 **The auto-save model already exists on this page — it is `quick-switch.js`**

This is the single most useful finding for correction 1, and it answers D-08, D-09 and D-26 together.

`companion/static/quick-switch.js` is already an auto-save: press → optimistic apply → `fetch` POST →
**204 and nothing else confirms** → otherwise `rollBack()` + `announceFailure()`. The server half is
already generic, not switch-specific:

```
companion/app.py:1287   _send_no_content()          # 204, no body, no Location (23-07 Task 1)
companion/app.py:1317   _is_quick_fetch()           # header X-Requested-With == "quick-switch"
```

and the failure vocabulary is already translated and already generic:

```
quick-switch.js:124  TOAST_ATTR        = "data-quick-toast"
quick-switch.js:125  FAILED_TEXT_ATTR  = "data-quick-failed-text"   # read off <body>, server-translated
quick-switch.js:139  FAILED_TEXT       = "Couldn't change that — please try again."   # documented fallback
```

**So the answers are:**

- **D-08 (what a failed auto-save does):** reuse `announceFailure()`'s toast verbatim — same
  `[data-quick-toast]` element, same `data-quick-failed-text` copy, same timer. **No second failure
  vocabulary is invented**, because the first one is already the right one and is already translated.
  The settings analogue of "roll back the flip" is "the field keeps the user's text and the page is not
  claimed saved" — the status region must go back to *not* saying "Sauvegardé".
- **D-09 (what happens to the three `role="switch"` controls):** **nothing changes about them, and that
  is the point.** They are not a second save model that auto-save must be reconciled with — they are the
  model the settings form now adopts. One save model on the page, stated as: *optimistic apply, POST,
  204-confirms, anything else rolls back and raises the one generic toast.* The switches keep their own
  `/quick/*` routes.
- **D-26 (no new script):** the auto-save driver is **`dirty-state.js` itself**. It already owns the
  delegated `change`/`input` listeners on the settings form — the exact hook auto-save needs — and it
  already owns the region that announces save state. Repurposing the file that is being retired as a
  *bar* into the file that drives the *save* costs **no new file, no new route, no pin move**. The
  deferred-script pin stays at **15**.

### 2.3 **D-11 — how the no-JS floor is kept BY CONSTRUCTION**

This is the phase's most dangerous change and the construction must be stated in one sentence:

> The native `<button type="submit" data-static-save-fallback>` is emitted by
> `config_page.py`'s settings-form builder **unconditionally, on every render, with no condition of
> any kind on its presence** — script only ever *hides* it, and hiding is a CSS rule that cannot
> execute when scripts do not run (the `.js` class is added by `nav-dropdown.js`'s first statement).

That is the "by construction" half: **there is no code path that omits the submit.** The rule change
is only a *simplification* of the visibility rule — from
`.dirty-ready.dirty-shown [data-static-save-fallback]` (which requires the script to have *decided*
to hide it, and which is why a big accented button greets every fresh load) back to the plain
`.js [data-static-save-fallback] { display: none; }` shape 06.6.4.1-01 originally landed. Under
auto-save there is no "dirty" state to gate on, so the two extra classes have nothing left to mean.

**And the proof is a save, not a render.** `_persist_without_js()` with scripts blocked, at 360 px, in
both shipped languages: GET → operate → submit through the real form → **second GET, value read back
off the state directory**. A check that merely asserts the button is *present* is the exact vacuity
this phase exists to refuse.

**D-07 — the superseded contract is amended, not deleted.** `style.css:1552–1568` carries a long
comment block explaining why `.dirty-shown` was added. That block stays and gains a dated paragraph
naming what replaced it (auto-save, Phase 27), so a reader finds the history rather than a hole. This
matters doubly here because of D-30: **`test_config_page.py` locates rules by the FIRST occurrence of
a literal in `style.css`** — so the amended comment must not quote any other rule's selector.

### 2.4 **D-10 — the leave-guard and "Annuler"**

With auto-save there is no pending edit, so:
- the **leave-guard** has nothing to guard and is retired. But `submit-guard.js` and
  `confirm-submit.js` also serve **destructive** confirmations (calendar disconnect, deletes) — the
  plan must separate "guard against leaving with unsaved edits" (retire) from "confirm a destructive
  action" (**keep**). Retiring the wrong half would remove a real safety net.
- **"Annuler"** is removed wherever it means "discard the pending edit". Where it means "close this
  dialog" it stays. Same separation, same care.

---

## 3. Correction 2 — the title inventory, measured

`grep`-derived, on `companion/pages/config_page.py`:

| Form | Shape | Count |
|---|---|---|
| **A — title INSIDE the card** | `<div class="theme-status\|page-section" data-dirty-section="…"><h2 class="text-heading">…</h2><p class="text-label section-caption">…</p>…</div>` | **8** |
| **B — title ABOVE the card** | `layout.section_intro_html(section_id, heading, description)` → `<div class="section-intro"><h2 id class="text-heading">…</h2><p …></p></div>`, followed by sibling card(s) | **3** |
| Unclassified `<h2 class="text-heading">` in the same file (poll section, others) | — | **2** (13 total minus 8 A minus 3 B) |

**These counts are provisional and must be re-derived by an executable inventory in the plan's first
task** — the regex above matches a formatting convention, not a grammar. The plan states the count
before it chooses.

**Note the asymmetry that makes this a real choice, not a style preference:** form B
(`section_intro_html`) is a **shared** helper also used by `health_page.py` (2 call sites,
`health_page.py:4273, 4294`) whose *structural checks match its markup literally* — its docstring says
so: *"this builder must never drift from that shape."* So **form B cannot be changed**; the only
available move is to convert the form-A cards to form B, or to leave B alone and convert B's *config*
call sites to A. Provisional recommendation: **converge on form A (title inside the card)** — it is the
majority (8 vs 3), it is what every settings *card* already does, and it leaves the shared helper and
Health's pinned checks untouched. The 3 config-page `section_intro_html` call sites are **supersection**
intros rather than cards, so the plan must first decide whether a supersection intro is even the same
thing as a card title; if it is not, the honest answer is that there is **one** title form for cards
already and the inconsistency the developer saw is elsewhere — which the executable inventory will settle.

---

## 4. Correction 3 — the runway map's footprint

| Surface | Measure |
|---|---|
| `config_page.py` | `runway_map_svg()`, `runway_bearing_deg()`, 9 `RUNWAY_MAP_*` constants (`config_page.py:2004–2130`) |
| `style.css` | **7** occurrences of `runway-map` |
| Checks | **45** lines across `test_browser_ux.py` and `test_config_page.py` |
| **Stays** | the three `runway-*.png` photographs, `RUNWAY-IMAGES.md`, their session-gated route, their slot in each card |
| **Stays** | the three native radios `<input type="radio" name="tracked_runway" class="visually-hidden" form="settings-form">` — **untouched**, exactly as they were before 25-03 wrapped a drawing round them |

The removal is genuinely clean *because* CFG-47's strongest clause was true: the map was a drawing
wrapped around radios that already worked. Take the drawing away and the control is intact.

**The three checks that must come out** (named, per D-16): every check asserting `runway-map` classes,
`runway_bearing_deg()`'s registry parsing, and the runway hit-area measurement that measured the
*map strip* (90×201 / 89×197 / 88×197 — those numbers describe a card that will no longer exist). The
radios' **own** persistence check (`'3'` → `'06-24'` → `'3'` with scripts blocked, in both languages)
**must NOT come out** — it never depended on the map and it is the proof the control still works.
`EXPECTED_CHECK_COUNT` for both harnesses re-derived by **running**.

**CFG-47's retirement mechanism** (D-15): the row at `REQUIREMENTS.md:73` keeps its `[x]` and its text
and gains a `— RETIRED (Phase 27)` marker with the reason; the ledger row at `REQUIREMENTS.md:199`
gains a closing paragraph recording that the requirement was **met as worded and then withdrawn as a
product decision**, which is a different fact from "not met" and must not be collapsed into one. The
D16 section at `REQUIREMENTS.md:568` gets the same treatment. Nothing is deleted.

---

## 5. Correction 4 — cutting text without weakening a refusal

Three targets:

- `WAKE_INTERVAL_SECTION_CAPTION` (`config_page.py:518`) — the slider's explanatory paragraph.
- `wake_gauges_html()` (`config_page.py:3441`) — "the two gauges, as two muted sentences".
- `quiet_hours_group()`'s caption (`config_page.py:3140–3155`), which is
  `QUIET_HOURS_SECTION_CAPTION + " " + delay_sentence`.

**The honesty contract that must survive the cut**, stated in three places in the tree
(`value-controls.js` header, `wake_gauge_interval_s()`'s docstring at `config_page.py:3179`,
`wake_gauges_html()`): the battery gauge prints an absolute "days left" figure **only when the device's
own observed history supports one**, and when it does not it prints **no figure at all** rather than a
plausible one. A shorter sentence that starts naming a number is a **regression**, not a cut.

The executable form of "shortened without weakening": keep the existing check that, with a battery
history that cannot support a figure, the rendered card contains **no** days figure — and add to it
that the shortened copy is *shorter* (a length assertion on the rendered text) so the cut is proven to
have happened rather than asserted in prose. Two facts, one check, on the same rendering.

Also note: `delay_sentence` defaults to `i18n.t(frame_state.DELAY_UNKNOWN)` — cutting the Quiet hours
paragraph must not accidentally cut the *delay* sentence, which carries real state, not explanation.

---

## 6. Correction 5 — the carousel, and Display's height

`_theme_carousel_html(grid_html)` (`config_page.py:1483`) is **already a pure presentation wrapper**
— its own docstring says so — and returns:

```python
return '<div class="theme-carousel">%s%s%s%s</div>' % (disclosure_html, grid_html, pagers_html, dots_html)
```

**"Voir tous les thèmes" is `disclosure_html`, and it is FIRST.** Moving it below the strip is a
reorder of that one format string in one shared helper: `grid_html, pagers_html, dots_html,
disclosure_html`. One change, correct for every grid that uses it — which is the point of extending it.

Extending to the other three grids is: give arrivals, calendar and rules the same
`theme-chip-grid--strip` modifier + `_theme_carousel_html()` wrap that departures already has
(`config_page.py:1835–1851`).

**THE TRAP, and it is a real one.** `THEME_CAROUSEL_STRIP_ID = "theme-carousel-strip"`
(`config_page.py:253`) is a **single `id`**, and it is *both* the strip's id *and* what the two pagers
point at (`aria-controls` / the pager's target). Four carousels on one page would render **four
elements with the same id** — invalid HTML, and every pager would drive the first strip. The helper
must take a per-usage id (the four usages already have distinct constants:
`COLOUR_USAGE_DEPARTURES` and its siblings). The plan must name this explicitly; it is the difference
between "extend the carousel" and "break the page".

**The height prediction (D-21).** 25-06 measured **3743 px at 390 px** against X6's **2600 px** target
and recorded that the remainder is *four more cards, not a grid*. Folding three more grids into
scroll-snap strips removes three grid heights. The departures grid folded into a strip is the only
measured precedent available; the plan must state a predicted figure **before** measuring. Reasoning to
put in the plan: three grids of 18 chips each, folded to one row, is the same saving the first grid
already made, times three — so the honest prediction is **3743 px minus roughly three times the
departures saving**, and the plan should state that number as a range with its arithmetic shown, and
say plainly whether it expects to reach 2600 px. **The value of the prediction is that it can be
wrong**; a closing plan reporting 3100 px against a stated 2900 px is information, and 3100 px against
nothing is not.

---

## 7. Correction 6 — the Frame strip link, without forking

`layout.frame_strip_html(ctx, return_to, next_wake_iso=None)` (`layout.py:3443`) is the **shared**
component. Its quiet cell (`layout.py:3587–3606`) builds:

- `quiet_label_html` — the moon icon + "Quiet hours";
- `quiet_state_row_html` — `quick_switch_state_html(...)` with the on-text
  `QUICK_ACTION_QUIET_ON_TEMPLATE % (quiet_start, quiet_end)`, plus the `role="switch"` button;
- `delay_caption_html` — passed into `_frame_strip_cell_html()`'s **`caption_row_html`** slot.

So **a caption slot already exists on that cell and is already used.** The link belongs there, appended
to the delay caption, as a normal anchor to the Settings route plus the Quiet hours heading's fragment.
One change, in the one shared write site, correct on Home *and* on Display — which is exactly D-23.

**The one decision the plan must make:** on the Settings page the strip renders on the page the link
points *at*, so the anchor is a same-page jump. Options: (a) always a real anchor — simplest, and a
same-page jump to the card is genuinely useful, it scrolls; (b) render a span with no href when the
reader is already there — the shape CFG-57 proposes, but CFG-57 is **Phase 26, planned and not
executed**, so that precedent is *not shipped* and this phase must not depend on it. **Provisional:
(a), always an anchor.** It needs no new plumbing, it is never wrong, and it does not borrow from an
unexecuted phase.

---

## 8. The two carried-in findings

- **The legend (D-24).** `departing_index == arriving_index` for 18 of 18 themes — `test_config_page.py`
  already knows this (`test_config_page.py:11517`: *"`departing_index == arriving_index`, and the
  eighteen resolve to…"*). The shipped "Departures · Arrivals" legend names two swatches that are
  never different. **Recommend IN**: it is the same defect class as correction 4 (copy claiming a
  distinction the data does not carry), it sits inside the colour grids correction 5 is already
  rewrapping, and the fix is to stop naming two things where the registry has one. The check must
  assert the **relationship** — *the legend names as many swatches as the registry has distinct
  colours* — not the literal new string, so it self-corrects if a future theme ever does differ.
- **`.copy-btn` (D-25).** Declared at `style.css:2714`; the comment at `style.css:1169` records that
  `.row-toggle` reuses its values verbatim and *"recomputes the 44 from the declared box and inset"*.
  The measured 34×26 is in a **Flights detail row**. **Recommend IN**: an already-measured failure
  against a standing floor, a correction not a capability, and `_assert_hit_target()` already exists.
  **The trap:** `.row-toggle` reuses `.copy-btn`'s values verbatim — changing `.copy-btn` moves
  `.row-toggle` too. The plan must measure **both**, in their own containers, or fix `.copy-btn` in a
  way scoped to the Flights detail row.

---

## 9. Validation Architecture

The phase's own instrumentation rule, and it is this phase's lesson in executable form:

> **Assert relationships, not just endpoints.** Where two or more rendered surfaces are functions of
> the same underlying value, the check decodes every surface into one canonical value and asserts the
> set has one member — never one check per surface.

Applied:

| # | Subject | Surfaces that must agree | Harness |
|---|---|---|---|
| V1 | The quiet-hours window after an interaction | fields, handles, arc geometry, caption | `test_browser_ux.py` |
| V2 | Auto-save | the status region's text, the value **on disk**, and the absence of any save button under `.js` | `test_browser_ux.py` |
| V3 | The no-JS floor under auto-save | the submit renders **and** the value reaches disk through it, scripts blocked, both languages, 360 px | `test_browser_ux.py` (`_persist_without_js`) |
| V4 | Auto-save failure | the toast's text **and** the status region not claiming "Sauvegardé" — one check, one induced failure | `test_browser_ux.py` |
| V5 | Title form | the inventory count **equals** the count of the chosen form, i.e. the other form's count is zero | `test_config_page.py` |
| V6 | Runway after the map's removal | the radios still save to disk with scripts blocked **and** no `runway-map` class resolves anywhere | `test_browser_ux.py` + `test_config_page.py` |
| V7 | The shortened battery copy | no days figure when the history cannot support one **and** the text is shorter than before | `test_config_page.py` |
| V8 | Four carousels | four distinct strip ids **and** each pager drives its own strip | `test_config_page.py` |
| V9 | Display height | one measurement at 390 px, reported against the plan's **stated** prediction | `test_browser_ux.py` |
| V10 | The Frame strip link | present on **both** pages that render the strip, from the **one** write site | `test_status_pages.py` / `test_config_page.py` |
| V11 | Hit areas | `.copy-btn` **and** `.row-toggle`, each in its own container | `test_browser_ux.py` |

**Baselines to re-derive by running, never by arithmetic:**
`test_browser_ux.py` 81 · `test_companion_app.py` 314 · `test_config_page.py` 259 ·
`test_status_pages.py` 305 · `test_i18n.py` 24 · `test_view_pages.py` 164 · `test_contrast_check.py` 49.
Sandbox baseline: exactly **5** failing checks, verified **by NAME**.

---

## 10. Open questions carried into the plans as provisional decisions

| # | Question | Provisional answer | Why it is provisional |
|---|---|---|---|
| Q1 | `mod()` or a script-published sweep? | script-published sweep | needs one run in the harness browser to know if `mod()` resolves |
| Q2 | Caption: blank the duration while dirty (C1) or a per-unit template (C2)? | C1 | C1 reuses two shipped mechanisms; the disappearing duration is a visual judgement only the developer can make |
| Q3 | Which title form wins? | form A (inside the card), 8 vs 3 | the executable inventory may show the 3 are supersections, not cards, in which case there is no inconsistency to fix |
| Q4 | Frame strip link on the page it points at | always a real anchor | the span-with-no-href precedent belongs to unexecuted Phase 26 |
| Q5 | Are D-24 and D-25 in scope? | both IN | neither was asked for by the developer in this review |
| Q6 | Predicted Display height | stated as a range with arithmetic shown | the point is that it can be wrong |

---

*Researched: 2026-09-14 — by direct reading of the shipped tree, no external sources.*
