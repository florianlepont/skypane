# Phase 27 — Pattern Map

**Method:** every file this phase touches, paired with the closest existing analog in the tree and the
excerpt that fixes the shape. Nothing here is invented — this phase is corrections, so for almost every
change there is already a shipped thing it must look like.

---

## 1. `companion/static/value-controls.js` — publishing a fraction to a shared ancestor

**Analog: the MIRROR, already in this file.** The mirror is the precedent for "write somewhere other
than the wrapper, downstream of the field, from inside `paint()`":

```js
// value-controls.js:~505, inside paint()
// THE MIRROR FOLLOWS THE FIELD, NEVER THE OTHER WAY ROUND. It is
// written here, in the paint, from the value just read back off the
// field …
writeValue(mirrorFor(wrapper), numberToField(wrapper, value));
```

**Analog for the ancestor walk:** `ancestorWith(el, attr)` already exists in this file and is already
used to find the wrapper from a handle. The pair publication reuses it verbatim — no second walker.

```js
function ancestorWith(el, attr) {
  var node = el;
  while (node && node.getAttribute) {
    if (node.hasAttribute(attr)) { return node; }
    node = node.parentNode;
  }
  return null;
}
```

**Analog for the attribute naming:** every seam in this file is `data-value-*` declared on the wrapper
and read with `getAttribute` (`FIELD_ATTR`, `FORM_ATTR`, `GEOMETRY_ATTR`, `FORMAT_ATTR`, `INPUT_ATTR`,
`READOUT_ATTR`). The new pair seam must follow it exactly: `data-value-pair` on the ancestor,
`data-value-pair-property` on the wrapper.

**Constraint the analogs encode:** ES5-safe subset (no arrow functions, no `let`/`const`, no template
literals), no dependency, no build step. Stated in the file header.

---

## 2. The caption — `paintReadouts()` is the analog, and it already blanks itself

```js
// value-controls.js:468
var base = numberOrNull(readout.getAttribute(READOUT_BASE_ATTR));
if (base !== null && base === value) {
  readout.textContent = "";
  continue;
}
readout.textContent = template.split(TEXT_TOKEN).join(String(readoutQuantity(readout, value)));
```

Two shipped behaviours reused whole: **(a)** a readout is found by the *field's name*, not by
containment, so it can live outside the `.js` gate and stay correct with scripts blocked; **(b)** a
readout whose value equals its declared base **says nothing**. (b) is exactly the mechanism the
duration segment needs — say nothing rather than state a duration that is no longer true.

---

## 3. The arc — `quiet_dial_svg()` and its own stated CSS-beats-attribute fact

```python
# config_page.py:2695, quiet_dial_svg() docstring
# `stroke-width` is a presentation attribute too, and deliberately not
# a stylesheet declaration — a CSS stroke-width of any specificity
# beats a presentation attribute, which would flatten the geometry the
# constants above derive.
```

This is the whole mechanism of the fix, written down by the author who was guarding against it:
**a `.js`-scoped CSS rule overrides a presentation attribute.** So the server keeps emitting
`stroke-dasharray` and `transform` (the saved value, the no-JS floor, authoritative) and a `.js` rule
takes over once script proves it is running.

**Analog for the ring itself:** `draw.unit_circle_dash_array(fraction, radius)` and `draw.circle()` —
`companion/draw.py` is the one drawing module and the one place a paint decision may be made. The arc's
*geometry constants* stay in Python; only the *two fractions* become live.

---

## 4. Auto-save — `quick-switch.js` is the analog, end to end

| Need | Shipped analog |
|---|---|
| optimistic apply from one boolean | `applyState(control, region, form, on)` — *"the flip and the rollback are therefore the SAME operation with a different argument"* |
| the POST | `window.fetch(form.action, {method:"POST", credentials:"same-origin", redirect:"manual", headers:{"X-Requested-With": FETCH_HEADER_VALUE}})` — the form's **own** server-rendered action, never an assembled URL |
| what confirms | **204 and nothing else.** `if (response.status === 204) { … } rollBack(...)` |
| the failure copy | `announceFailure()` → `[data-quick-toast]`, text from `<body data-quick-failed-text>` (server-translated), English fallback documented in the file |
| the server half | `companion/app.py:1287 _send_no_content()` and `:1317 _is_quick_fetch()` |
| the change hook | `dirty-state.js`'s delegated document-level `change`/`input` listeners filtered to `e.target.form === form` (22-01's B1 fix) |

**The excerpt that fixes the failure contract:**

```js
// quick-switch.js:~314
// 204 and nothing else confirms. A 2xx that is not the negotiated
// no-content answer, a 4xx/5xx, and the opaque redirect above all
// fall to the same rollback, because none of them is the server
// saying it saved.
```

**Analog for the translated-attribute-with-English-fallback idiom** (needed for "Sauvegarde…" /
"Sauvegardé"): `config_page.py:762–800` — six connector words plus a seventh progress word, each a
`data-*` attribute on the bar with the script's documented English fallback equal to the constant's own
English value, *"so the two can never silently disagree"*. The two new status words follow this exactly.

---

## 5. The no-JS floor — the shipped rule and the shipped proof

```python
# config_page.py:753
# STATIC_SAVE_FALLBACK_ATTR is read by a `.js`-gated rule in
# companion/static/style.css (`.js [data-static-save-fallback] {
# display: none; }`, landed by 06.6.4.1-01). Neither file imports this
# module — the values must be kept equal by hand.
```

The **original** rule is the target shape. `style.css:1568`'s `.dirty-ready.dirty-shown
[data-static-save-fallback]` is the narrowing this phase reverses.

**The proof analog:** `companion/test_browser_ux.py:1589 _persist_without_js(browser, base_url, route,
field, value, read_back, …)` with 25-02's `operate` callback, and `_persist_once()` at `:1761` which is
the GET → operate → submit → **second GET, read back off the state directory** sequence. Its own error
strings all begin `"_persist_without_js: …"` and name the field — that message shape is the analog for
every new failure message in this phase.

**The one context rule:** `grep -n 'java_script_enabled' companion/test_browser_ux.py` must return
exactly one line. `_no_js_page()` is the only place scripts are blocked; compose with it, never open a
second context.

---

## 6. Card titles

| Form | Excerpt | Count |
|---|---|---|
| A — inside | `'<div class="theme-status" %s="%s">' '<h2 class="text-heading">%s</h2>' '<p class="text-label section-caption" id="%s">%s</p>'` | 8 |
| B — above | `layout.section_intro_html()` → `'<div class="section-intro">' '<h2 id="%s" class="text-heading">%s</h2>' '<p class="text-label section-caption">%s</p>' '</div>'` | 3 |

**The constraint the analog carries:** `section_intro_html()`'s docstring — *"keeps the same attribute
order (`id` then `class`) … health_page.py's own pinned structural checks already match literally — this
builder must never drift from that shape."* Form B is **not editable**.

---

## 7. The carousel

```python
# config_page.py:1617
return '<div class="theme-carousel">%s%s%s%s</div>' % (
    disclosure_html, grid_html, pagers_html, dots_html)
```

Reorder to `grid_html, pagers_html, dots_html, disclosure_html`. **The id trap:**
`THEME_CAROUSEL_STRIP_ID = "theme-carousel-strip"` (`config_page.py:253`) is a single literal used as
the strip's `id` *and* as the pagers' target — four carousels need four ids. The analog for
per-instance ids in this file is the `id_suffix="-dialog"` convention `airlines_page.py` uses for its
duplicated forms (`_resolve_context_html(None, None, id_suffix="-dialog")`).

---

## 8. The Frame strip

```python
# layout.py:3603
quiet_cell_html = _frame_strip_cell_html(
    "quick-action quick-action--%s" % ("on" if is_quiet_on else "off"),
    quiet_label_html, quiet_state_row_html, delay_caption_html,
    extra_attrs=QUICK_SWITCH_REGION_ATTR)
```

`_frame_strip_cell_html(extra_class, label_row_html, state_row_html, caption_row_html, …)`
(`layout.py:3402`) — **the caption slot already exists and is already used.** The link is appended
there, at this one write site. `frame_strip_html()` is called from Home and from Display; there is one
write site and it must stay one.

---

## 9. Hit areas

```
style.css:1169   * Every value here is `.copy-btn`'s own, reused VERBATIM rather than …
style.css:1176   * `.copy-btn`'s and recomputes the 44 from the declared box and inset,
style.css:2714   .copy-btn {
```

`.row-toggle` reuses `.copy-btn`'s values **verbatim**. Any change to `.copy-btn` moves `.row-toggle`.
Both must be measured with `_assert_hit_target()` **in their own container** — three shipped proofs
exist as precedent (`.copy-btn` 34×26, a handle 43×43, a pager 30×45), and the runway proof
(90×201 / 89×197 / 88×197) is the one that goes away with the map.

---

## 10. Requirements ledger — retire-in-place

**Analog:** `REQUIREMENTS.md`'s own existing re-scope prose, e.g. CFG-47's ledger row, which records
*"Ticked, as worded, with one word re-scoped and the ground stated"* rather than collapsing a
deviation into a tick. The same voice is used for the retirement: **met as worded, then withdrawn as a
product decision** — a different fact from "not met", and it must not be collapsed into one.

Also the precedent at the file's foot: *"RER-01/02/03 and DEVICE-01/02 moved to v2 Requirements
(2026-08-11) — no longer mapped to a v1 phase"* — movements are recorded as dated sentences, never as
deletions.
