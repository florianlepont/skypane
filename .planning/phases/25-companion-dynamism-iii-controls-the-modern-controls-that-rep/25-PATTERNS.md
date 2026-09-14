# Phase 25 — Pattern Map

**Purpose:** for every file this phase creates or modifies, the closest existing
analog in this codebase, with the concrete excerpt an executor should copy rather
than re-derive. **Nothing in this phase needs a new interaction idiom.** Every one
of the five controls is a variation on a shape this app already ships.

**Read this before writing any control.** Every rule below was paid for once
already.

> **Every line number below is stale by construction.** Plan 23-10 is editing
> `config_page.py`, `style.css`, `theme-preview.js`, `airlines_page.py` and three
> test files in this same tree, and Phase 24 lands before this phase runs.
> Re-grep before quoting. The *shapes* below are stable; the coordinates are not.

---

## 1. The no-JS control, shape A: the hidden native input inside a whole-element label

**Used by:** D16 (runway map), D5 (theme carousel). Four live consumers already.

```python
# Source: companion/pages/config_page.py, runway_fieldset() (abridged)
'<label class="%s"%s>'
'<input type="radio" name="tracked_runway" value="%s" class="visually-hidden" '
'form="%s"%s>'
'<span class="runway-card__number">%s</span>'
"%s"
'<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
"</label>"
```

Five properties to carry forward, each load-bearing:

1. **`class="visually-hidden"`, never `display: none`.** A `display:none` radio is
   not focusable and not in the tab order — selection would stop working with
   scripts blocked, which is the whole point of the idiom.
2. **`form="settings-form"` on every input**, because these groups render as
   *siblings* of the form rather than descendants (HTML forbids nesting one
   `<form>` in another, and the instant-switch forms needed their own). The
   attribute is a no-op when the group *is* nested, so it is always correct.
3. **Selection state is computed server-side** (`--selected`) **and** live
   (`:has(input:checked)`), never one or the other. The server-rendered class is
   the no-`:has()` fallback plus the "this is what is saved" marker.
4. **The check glyph is in every card's markup**; CSS reveals it on the selected
   one. No second server-side conditional.
5. **The wrapping label is the hit target**, which is what puts the hidden input in
   the design system's **exempt-by-delegation** touch-target category. That
   exemption is only valid while the label exceeds 44 px in both axes — **measure
   it, do not inherit the claim.**

The group wrapper, verbatim:

```python
row_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
    escape_html(RUNWAY_GROUP_HEADING_ID), _describedby_attr(RUNWAY_SECTION_CAPTION_ID))
```

`role="radiogroup"` + `aria-labelledby` (the group's own `<h2>`, since these groups
deliberately carry no `<fieldset>`/`<legend>`) + `aria-describedby` (the caption).
A `<legend>` outside a `<fieldset>` is invalid markup with no group semantics —
that is why the `<h2>` carries the name. Keep the triple; do not re-derive it.

---

## 2. The no-JS control, shape B: a `type="button"` that writes into the form

**Used by:** D17 (the dial's handles), D18 (the slider), D5 (the ◀ ▶ pager).

```javascript
// Source: companion/static/dirty-state.js:161-179 (abridged)
function attachPresetClickHandler(button) {
  button.addEventListener("click", function () {
    var start = button.getAttribute("data-preset-start");
    var end = button.getAttribute("data-preset-end");
    if (start !== null && form.elements["quiet_hours_start"]) {
      form.elements["quiet_hours_start"].value = start;
    }
    if (end !== null && form.elements["quiet_hours_end"]) {
      form.elements["quiet_hours_end"].value = end;
    }
    notifyDirty();
  });
}
```

Four things to copy:

- **The enhancement never holds the value.** It writes into
  `form.elements[<name>]` and stops. There is no parallel state to drift.
- **`type="button"`**, so it cannot accidentally submit. The existing quiet-hours
  presets are documented as "simply inert" with scripts blocked for exactly this
  reason.
- **Every element access is guarded** (`&& form.elements[...]`). A control that
  throws on a page where its field is absent breaks every later listener in the
  same script.
- **It notifies the dirty state** after writing, or the save bar will not know the
  form changed — which would mean a user drags a handle, sees no Save, and loses
  the change. `notifyDirty()` is `dirty-state.js`-internal; a *different* script
  must instead dispatch the event the dirty-state listener already binds, or the
  new control must live in `dirty-state.js`. **Decide and state which** — this is
  the single most likely silent defect in D17 and D18.

---

## 3. The `.js` gate — how an affordance that needs script avoids rendering without it

```javascript
// Source: companion/static/nav-dropdown.js:28-31
// .js .mobile-nav clipping rule (and any other .js-scoped rule a
// later phase adds) …
document.documentElement.className += " js";
```

```css
/* Source: companion/static/style.css:1078 */
.js .mobile-nav { … }
```

**The rule, and the direction matters:** hide the script-only affordance **by
default** and reveal it under `.js`. The reverse (render it, then hide it under
`.js`) flashes the dead control on every page load, and shows it permanently to a
user whose script failed to run.

Two caveats every plan must carry:

- `.js` is added by `nav-dropdown.js`, which is on the **authenticated shell only**.
  Every control in this phase is behind auth, so this is fine — but a future
  pre-auth control cannot rely on it.
- The class lands at script-execution time, after first paint. Anything sized by
  the gate must not cause layout shift when it appears; reserve the space or place
  the gated affordance where reflow is invisible.

---

## 4. `companion/static/value-controls.js` — NEW (the phase's only new script)

**Role:** steer a continuous value with pointer and keyboard, and write it into the
native input the form posts.
**Data flow:** pointer/key → clamp+round → `input.value` → dirty notification →
ordinary form submit.

### Closest analog for the file's *shape*: `companion/static/quick-switch.js` (the newest script, 23-07)

Copy its skeleton, not its content:

```javascript
/* ES5 subset: no let/const, no arrows, no template literals, no backticks. */
(function () {
  "use strict";
  var switches = document.querySelectorAll("[data-quick-switch]");
  if (!switches.length) { return; }          // no-op on every other page
  …
})();
```

Three conventions visible here and binding on the new file:

- **The guard clause first.** Every script in this app is served on every
  authenticated page and must be a no-op where its subject is absent. This is what
  makes one shell registration safe.
- **ES5 subset, pinned per file by name.** `innerHTML`, `insertAdjacentHTML`,
  `document.write`, `eval`, arrow functions, `let`, `const` and backticks are all
  banned and asserted. The one sanctioned DOM-swap mechanism elsewhere in this app
  is `DOMParser` + `importNode` + `replaceChild`; this script should need none of
  it, because it writes values, not markup.
- **`"use strict"` inside the IIFE.**

### The three taxes a new script owes (pay all three in 25-01)

```python
# Source: companion/app.py:211-226 (the pattern, repeated 16 times)
SUBMIT_GUARD_SCRIPT_ROUTE = "/static/submit-guard.js"
# … companion/layout.py's own *_SCRIPT_SRC constant must equal this exactly
RELATIVE_TIME_SCRIPT_ROUTE = "/static/relative-time.js"
QUICK_SWITCH_SCRIPT_ROUTE = "/static/quick-switch.js"
```

1. **A route constant in `app.py` + a matching `*_SCRIPT_SRC` in `layout.py`**,
   plus the thin handler branch. There is no catch-all `/static/` handler.
2. **The deferred-script pin**, `companion/test_companion_app.py`'s
   `_fourteen_deferred_scripts_before_closing_body` — **retargeted IN PLACE with a
   stated reason**, never deleted. The check's own comment block shows the format,
   used four times already ("Retargeted a FOURTH time, in place, by 23-07-PLAN.md
   Task 1 (D2/CFG-36): quick-switch.js is the fourteenth…"). Note the check also
   asserts the **login shell still emits exactly one** script — a new
   shell-registered script must be added to that exclusion list too.
3. **The i18n fallback-literal scan.** `companion/test_i18n.py` Check 6 demands a
   French catalogue entry for every `var ALL_CAPS = "literal"` and
   `|| "literal"` in a script. Any user-visible string the new script can produce
   needs its French sibling.

### The one genuinely new thing: a continuous value's keyboard model

This app has no precedent — every existing control is a radio, a checkbox, a
button or a native text/time/number input. So the plan **states the keys** rather
than leaving them to the executor. The native `<input type="range">` D18 uses
already supplies its own model (arrows ± step, Page ± large step, Home/End); D17's
custom handles must **match it**, because two sliders on two settings pages with
different key semantics is precisely the drift this project keeps paying for.

---

## 5. `companion/pages/config_page.py` — MODIFIED (plans 25-03, 25-04, 25-05, 25-06)

**Role:** page module; owns Display's and Device's server-rendered markup.

### The group wrapper every settings group shares

```python
'<div class="theme-status" %s="%s">'
'<h2 class="text-heading" id="%s">%s</h2>'
'<p class="text-label section-caption" id="%s">%s</p>'
…
```

`DIRTY_SECTION_ATTR` (`data-dirty-section`) is what makes the group one unit
`dirty-state.js` can address; the `<h2 class="text-heading">` is the group's
accessible name (no `<fieldset>`/`<legend>`); `.section-caption` deliberately
carries **no margin of its own** — do not "complete" that rule.

### The escaping discipline, universal in this file

**Translate first, escape once**, at the display site:

```python
label = i18n.t(device_config.runway_label(runway_id))
… escape_html(label) …
```

Every interpolated value goes through `escape_html()`. Registry text
(`device_config.RUNWAYS`/`THEMES` labels) stays untranslated at the source and is
translated at the display site; `companion/i18n_fr/registry.py` supplies the
French.

### The `value`-attribute guard that must survive D18

```python
# Source: companion/pages/config_page.py, wake_interval_group() (abridged)
value_attr = (
    ' value="%d"' % current_wake_interval_s
    if (
        isinstance(current_wake_interval_s, int)
        and not isinstance(current_wake_interval_s, bool)
        and device_config.WAKE_INTERVAL_MIN_S <= current_wake_interval_s <= device_config.WAKE_INTERVAL_MAX_S
    ) else "")
```

The recorded reason, which D18 must not undo: **an out-of-range `value` on a
native numeric input fails HTML5 constraint validation and blocks submission of
the *entire* Settings form**, not just this field — and that is a live risk,
because `deploy/skypane.env.example` ships `SKYPANE_SLEEP_S=30`, below the 60 s
floor. The bool exclusion is mandatory because `isinstance(True, int)` is true.
A slider added beside this input must inherit the same bounds from
`device_config`, **read from the module, never re-typed as literals**.

### B14's visible 24 h sibling, which D17 must preserve

```python
# Source: companion/pages/config_page.py, _normalised_time_html()
return ' <span class="text-label field-inline-value" aria-hidden="true">%s</span>' % escape_html(value)
```

Its docstring records why it exists: a native time control formats itself from the
**browser's** locale, so a browser in en-US renders the stored "23:00" as
"11:00 PM" — directly beside a preset button labelled "Night (23:00-07:00)". One
value, two notations. `aria-hidden` because the input announces its own value
natively; **the visual duplication is the point and the aural duplication is not.**
D17's own "23:00 → 07:00 · 8 h" readout takes the identical treatment for the
identical reason.

### The ONE chip-grid renderer, and its four call sites

```python
def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None, leading_chip_html=""):
```

D5 must extend this **one** function (or wrap its output), never fork it. The four
call sites differ only in the radio group's `name`, which chip is checked, the
wrapper class/attribute, and an optional leading non-theme chip. A fifth seam is
acceptable; a second renderer is not.

---

## 6. `companion/static/style.css` — MODIFIED (plans 25-01, 25-03, 25-04, 25-05, 25-06, 25-07)

### The ONE feature query — the phase's largest risk

```css
/* Source: companion/static/style.css:2883 */
@supports selector(:has(*)) {
  .theme-chip:has(input:checked) { … }
  .runway-card:has(input:checked) { … }
  …
}
```

Two named checks assert the block count is exactly **one**
(`test_config_page.py:4002`, `:4232`), and the specificity arithmetic at
`style.css:2323-2345` is marked **"verified, not to be re-derived"**. The rule:
**a new live-selection rule joins the block at `style.css:2883`. It never opens a
second one.** Any diff introducing the literal `@supports selector(:has(*)) {` is
the defect. An unsupported `:has()` invalidates the whole selector list it appears
in — which is *why* every such rule is quarantined in one feature query.

### The paint idiom: `currentColor` + a theme token

```css
/* Source: companion/static/style.css (the .sparkline* block, abridged) */
.sparkline-line { stroke: currentColor; stroke-width: 2; stroke-linecap: round; fill: none; }
.sparkline-axis { fill: var(--color-border); }
```

The SVG inherits `color` from its container, the container's colour is a theme
token, and the drawing is therefore correct in both themes with no second rule and
no media query. **A literal hex breaks this; so does a shape with no rule at all,
which paints SVG-default black** — invisible in dark mode. D16's map and D17's arc
both inherit this exactly.

### The hit-area synthesis for a small control

```css
/* Source: companion/static/style.css — .copy-btn / .row-toggle */
/* Icon-only button: visual 22x22, real 44x44 hit area */
… position: relative; …
::before { content: ""; position: absolute; inset: -11px; }
```

22 + 11×2 = 44. **This is the pattern** for D17's dial handles and D5's pager
buttons — not a `min-height` on the visual box, which would change the drawing.
Two controls already use it (`.copy-btn`, `.row-toggle`); these would be the third
and fourth, which is a register *extension*, not a new mechanism.

### The reduced-motion rule

```css
/* Source: companion/static/style.css:311-317 */
*, *::before, *::after { /* under prefers-reduced-motion: reduce */ }
```

The global block covers every plain transition and animation on a real element.
**Do not add a per-rule `@media (prefers-reduced-motion: reduce)` block** — the
design system records that as "dead code, not a safety net", and the block count is
watched. The one documented exception is view-transition pseudo-elements, which
this phase does not touch.

### Hard constraint

`style.css` is pinned at **zero stray comment terminators** by
`companion/test_status_pages.py`. Every new comment goes *inside* a block comment.
A stray `*/` silently dropped a whole rule for four plans once; that check exists
because of it.

---

## 7. `companion/pages/airlines_page.py` — MODIFIED (plan 25-07)

### The upload form, which must not change

```python
# Source: companion/pages/airlines_page.py, _resolve_upload_form_html() (abridged)
'<form method="post" enctype="multipart/form-data" action="%s">'
'<input type="file" id="%s" name="image" accept="image/png" required>'
'<button type="submit">%s</button>'
"</form>"
```

Two structural facts a drop zone must respect:

- **`action=""` on the dialog copy is a real, present placeholder attribute**,
  never omitted, because `panel-lookup.js` overwrites an existing attribute by
  `setAttribute` rather than creating one. Both the replace form and the resolve
  upload form document this rule.
- **`id_suffix` exists because two copies of this markup coexist** (the dialog and
  the no-JS fallback), and HTML requires document-unique ids. `_manual_delete_form_html()`
  deliberately has **no** `id_suffix` because its output names no id at all — its
  docstring warns a future editor not to "fix" that asymmetry. A drop zone added to
  both copies inherits the same discipline.

### The parser boundary, unchanged

```python
# Source: companion/app.py:104, :1445-1446
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024
raw = self.rfile.read(min(length, MAX_ILLUSTRATION_UPLOAD_BYTES + 1))
if length > MAX_ILLUSTRATION_UPLOAD_BYTES:
```

The cap is enforced **before the body is read**, and
`parse_single_uploaded_file()` **discards the client-declared filename entirely**.
Drag-and-drop changes the **affordance**, not the parser. A drop assigns to
`input.files` via `DataTransfer`, so the bytes travel the identical path whether
the file was dropped or chosen.

### The normaliser, which stays the sole authority

```python
# Source: companion/illustration_normalize.py (docstring, abridged)
"""… This module must never become a second implementation for that same
measurement to drift against; it may only ever import the one at
server/plane/render.py."""
```

The module's own docstring states the failure mode a client-side canvas crop would
recreate: a *second, differently-thresholded measurement silently drifting from the
first*, which is the debug session that produced this module. **A client crop is
not a smaller version of this risk; it is the same risk with a less trustworthy
implementation.**

---

## 8. The harnesses — MODIFIED (every plan)

### The check idiom

```python
# Source: companion/test_status_pages.py:1093-1102
def check(name, fn):
    try:
        ok, reason = fn()
    except Exception as exc:  # never let an exception be swallowed into a pass
        ok, reason = False, "exception: %r" % (exc,)
    results.append((name, ok))
```

**The failure message names the offending thing**, not just "assertion failed",
and **boundaries are asserted AT the boundary**, not near it.

### The scripts-blocked helper — already factored, do not rebuild it

```python
# Source: companion/test_browser_ux.py:702
def _no_js_page(browser, base_url, route, viewport=None, sign_in=True):
    """A scripts-blocked browser context, signed in, landed on `route`.

    The one place in this file that blocks scripts. … 23-RESEARCH.md's
    Wave 0 gap list names five more controls that each need one; a
    transcribed sequence is a sequence that can be transcribed WRONG, and
    a scripts-blocked proof that quietly ran with scripts enabled would
    pass while proving nothing. …

    Pass VIEWPORT_MIN_SUPPORTED to measure a scripts-blocked control at
    the 360px contract floor."""
```

**This helper was written for this phase.** Its docstring names "five more
controls" — they are D16, D17, D18, D5 and D19. Every control plan calls it; none
writes a second scripts-blocked context.

### The viewport constants

```python
# Source: companion/test_browser_ux.py:585-600
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}   # the contract floor
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 900}
VIEWPORT_WIDTH_NARROW = 320                              # out of contract, kept
```

### `EXPECTED_CHECK_COUNT`

```python
# Source: companion/test_browser_ux.py:516-539 (the tail of the assignment chain)
EXPECTED_CHECK_COUNT = 50
EXPECTED_CHECK_COUNT = 51
EXPECTED_CHECK_COUNT = 53
```

The file carries the **whole history** as successive assignments, each with a
comment naming the plan and task that moved it. **Append a new last assignment;
never edit an earlier one; never compute the new value by arithmetic — run the
harness and read it.**

---

## 9. `companion/i18n_fr/` — MODIFIED (every control plan)

One module per page, so two plans editing different pages never collide. Every new
caption, `<title>`, `aria-label`, `aria-valuetext` template and **JS fallback
literal** needs its French sibling. `companion/test_i18n.py` sweeps `app.py`, HTML
attribute literals **and** script fallback literals — the third is the one a plan
adding a script forgets.

---

## Anti-patterns this phase must not commit

| Anti-pattern | Why it is wrong here | Do instead |
|---|---|---|
| A control whose only writer is `fetch` or a script variable | Fails D-09, a locked developer decision; the setting becomes unsavable with scripts blocked | the server renders the native input; the enhancement writes into it |
| A script-only affordance rendered unconditionally | The Pitfall-3 defect: it renders and silently does nothing | hide by default, reveal under the existing `.js` class |
| Revealing by default and hiding under `.js` | Flashes a dead control on every load, and shows it forever if the script fails | the other direction |
| A second `@supports selector(:has(*))` block | Two named checks fail; the "verified, not to be re-derived" specificity arithmetic has to be re-derived | add rules **inside** the one block |
| A `role="slider"` on a native `<input type="range">` | Double role; the native element already exposes the slider semantics | `aria-label` + `aria-describedby` only |
| A `role="status"` readout that updates as a handle drags | Re-announces on every step — the exact defect Phase 23 learned with its switches | `aria-valuetext` on the handle; the visible readout is `aria-hidden` |
| A client-side crop that "matches" the server normaliser | A second implementation of one measurement — the drift the normaliser's own docstring exists to prevent | preview the *chosen file* framed by CSS; the server stays the authority |
| A `<dialog>` as the only route to the full theme grid | Cannot be opened without script — eighteen themes behind a dead control | a native `<details>` disclosure |
| An overlay drawer, in any control | Three recorded rejections plus a locked Phase 22 decision, one from real-device testing | stop and say so; do not fall back to it |
| Sticky day headers | Struck twice; every flight row already carries its date | nothing — this phase does not touch it |
| Re-typing `60`/`3600` beside the slider | Two bounds that can drift from `save_device_config()`'s own re-check | read `device_config.WAKE_INTERVAL_MIN_S`/`MAX_S` |
| An absolute "≈ N days" from an unmeasured per-wake cost | The dishonest-state defect Phase 22's X2/B2/B3 arc removed; DEVICE-05 is still deferred | derive from observed slope, or say "not enough history yet" |
| Removing `_normalised_time_html()`'s visible 24 h sibling | Reopens B14, fixed in 22-10 | keep it; the dial's own readout takes the same treatment |
| A page module importing another page module | Forbidden by `companion/pages/__init__.py` | `battery.py` / `layout.py` / `frame_state.py` / `draw.py` |
| A new `@keyframes` or a per-rule reduced-motion block | The motion budget is two tokens and the existing keyframes; the global block already covers plain transitions | reuse `skypane-fade-in` / `skypane-bar-arrive` |
| Two writers of one file in one wave | This project's wave rule, and the reason Phase 23 needed 9 waves for 11 plans | serialise the wave |
