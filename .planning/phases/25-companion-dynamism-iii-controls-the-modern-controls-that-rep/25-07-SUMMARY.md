---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 07
subsystem: companion-airlines
tags: [drag-and-drop, upload, no-js-floor, csp, control, mutation-testing]
requires:
  - "companion/layout.py::JS_GATE_CLASS + style.css's `.js-gate` rule (25-01)"
  - "companion/test_companion_app.py::_NO_JS_CONTROL_REGISTRY (25-01)"
  - "companion/test_browser_ux.py::_no_js_page(cookies=...) / _assert_js_gate / _assert_hit_target / _in_both_themes / _assert_no_page_overflow (25-02, 24-02)"
  - "companion/app.py::MAX_ILLUSTRATION_UPLOAD_BYTES + parse_single_uploaded_file (plan 02, unchanged)"
  - "companion/illustration_normalize.py::ILLUSTRATION_TARGET_SIZE (unchanged, not one line)"
  - "companion/static/panel-lookup.js's existing ownership of both upload forms' action rewriting"
provides:
  - "companion/pages/airlines_page.py::_upload_drop_html (one definition, three call sites)"
  - "companion/pages/airlines_page.py::UPLOAD_DROP_* vocabulary + MANUAL_UPLOAD_FORM_ID + REPLACE_FORM_ID"
  - "companion/static/panel-lookup.js's drop handling (uploadRefusal / applyDroppedFiles / reviewChosenFile)"
  - "companion/static/style.css::.upload-drop / __note / __preview / __image / __message"
  - "companion/test_browser_ux.py::_upload_without_js (the file-input variant of 25-02's persist helper)"
  - "companion/test_browser_ux.py::_drop_files (a TRUSTED file drop, via CDP)"
  - "companion/test_browser_ux.py::_upload_zone_state / _drop_zone_paint / _await_upload_zone"
affects:
  - "25-08 (the phase gate: the three removed D19 clauses are the item the developer most needs to see)"
tech-stack:
  added: []
  patterns:
    - "a drop assigns to the form's own input via DataTransfer, so there is one upload path, not two"
    - "one validator with two callers cannot diverge; two validators with one comment can"
    - "a courtesy check refuses only what it positively knows is wrong and hands the rest to the real gate"
    - "a mutation suite without a null control cannot tell a load-bearing property from layout jitter"
key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/static/panel-lookup.js
    - companion/static/style.css
    - companion/i18n_fr/airlines.py
    - companion/test_status_pages.py
    - companion/test_companion_app.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py
decisions:
  - "the preview is a FileReader data: URL, not an object URL — MEASURED: this app's own img-src 'self' data: CSP blocks a blob: image, and no security header was widened for a thumbnail"
  - "the drop keeps its evt.isTrusted refusal AND is still measured end to end, because Chromium's DevTools protocol dispatches a genuinely trusted file drop"
  - "one shared uploadRefusal() runs on both the drop and the picker path; the drop declines to act, the picker's own choice is never removed"
  - "the stored file is deleted between the picked and the dropped upload, or the byte comparison passes on the file left behind"
  - "`width: 100%` on .upload-drop was removed after measuring it inert against a comment-only null mutation"
metrics:
  duration: ~5h
  completed: 2026-09-14
  checks_added: 7
  mutations_run: 55
---

# Phase 25 Plan 07: D19's artwork drop zone Summary

A drop target over two upload forms that did not change: a dropped file is assigned to
the form's own `<input type="file">` through a `DataTransfer`, so dropped and picked
bytes travel one path with one size cap and one parser — proven by uploading the same
source file twice, once each way, and comparing what landed on disk.

---

## The decision that mattered most

**The preview is a `data:` URL from a `FileReader`, not an object URL — and that was a
measurement, not a preference.**

The plan said plainly: "Render the preview from `URL.createObjectURL()` … and revoke the
object URL when it is replaced or the dialog closes." Before writing it I ran the API
against the real app, and Chromium answered:

```
RESULT {'url': 'blob:http://', 'blob': 'ERROR', 'data': 'loaded 1'}
CONSOLE ["Loading the image 'blob:http://127.0.0.1:44915/8068…' violates the following
         Content Security Policy directive: \"img-src 'self' data:\". The action has
         been blocked."]
```

`companion/app.py`'s `CONTENT_SECURITY_POLICY` is `img-src 'self' data:`. A `blob:` URL is
matched by neither, so the preview would simply never have rendered — and the plan's own
acceptance criterion ("`createObjectURL` is paired with `revokeObjectURL` — asserted by
source scan") would have passed against a broken preview, because a pair of calls is a
pair of calls whether or not the image ever loads.

There were two ways out and only one of them is right for this control. Adding `blob:` to
`img-src` would widen a security header so a thumbnail can render — in the one control on
this page that accepts bytes from outside the app, whose own threat model says this plan
"neither adds nor widens a route". `data:` is *already* allowed, for the inline favicon
`companion/layout.py` emits. So the preview reads the file with a `FileReader` and assigns
a `data:` URL, **`companion/app.py` is untouched by one line**, and the object-URL leak the
plan worried about does not exist to leak: there is no object URL. The same lifetime
discipline applies to what replaced it — the `<img>`'s `src` is *removed* (not merely
hidden) on every replacement, on every refusal, and when the dialog closes, and a browser
check now fails if it is not.

The runner-up decision is the one that made the whole task measurable: **the drop keeps its
`evt.isTrusted` refusal AND is still measured end to end.** Every drop a page script can
construct is untrusted, so the obvious harness recipe (build a `DataTransfer` in-page,
dispatch a synthetic `drop`) would only ever have measured the refusal — which is why the
guard and the proof usually trade against each other. Chromium's DevTools protocol
`Input.dispatchDragEvent` carries a real `files` list through the same input pipeline a
pointer uses; measured on this tree the handler sees `isTrusted: true` and
`dataTransfer.files.length === 1`. So the same check now measures the real gesture *and*
proves the fake one inert.

---

## Where the drop path's validation lives, and why it cannot diverge from the picker's

This is the plan's security question and it has a structural answer, not a procedural one.

**There is exactly one validator, `uploadRefusal(zone, files)` in
`companion/static/panel-lookup.js`, and exactly two callers** — `applyDroppedFiles()` (the
drop) and `reviewChosenFile()` (the picker's `change`). Neither has a validation branch of
its own. `companion/test_companion_app.py` asserts, by source scan, that the definition
appears exactly once and that `= uploadRefusal(zone, files);` appears exactly twice; a path
that reached the input without passing through it, or a second definition, fails there.
Mutation `T2-M4` removed one of the two calls and the guard said so.

**The real gate is the server, and it is the same server for both paths, because there is
only one path.** A drop constructs a `DataTransfer`, adds the `File`, and assigns it to the
form's own `<input type="file">`. From that point there is nothing left to keep in sync:
the same multipart POST to the same route, `MAX_ILLUSTRATION_UPLOAD_BYTES` enforced
*before* the body is read, `parse_single_uploaded_file()` discarding the client-declared
filename, `illustrations.validate_illustration_file()` reading the real PNG header, and
`illustration_normalize.py` doing the crop — all unchanged by this plan (`git diff` against
the plan's base commit is **empty** for `companion/app.py` and for
`companion/illustration_normalize.py`).

**The client-side check is a courtesy and says so in the file**, in a comment addressed at
a future reader who might relax a server check on the strength of it. It refuses only what
it *positively* knows is wrong: a `file.type` that is present and is not `image/png`, a
size over the cap, more than one file, or no file at all. A browser that reports **no** type
is handed to the server — failing open toward the real check is the correct direction for a
courtesy, and it is what stops this refusing a legitimate PNG the picker would have taken.

**The cap is the app's own number, never retyped.** `airlines_page._max_upload_bytes()`
imports `MAX_ILLUSTRATION_UPLOAD_BYTES` from `companion/app.py` (inside the function —
`app.py` imports this module, so a module-level import would be a cycle) and renders it into
`data-upload-drop-max-bytes`. The browser check reads the cap *back out of the page* and
refuses to run its oversized case unless the fixture genuinely exceeds it.

**The one asymmetry, stated rather than hidden.** On the drop path the file is refused
*before* anything is assigned (a source-scan clause asserts the refusal textually precedes
the assignment). On the picker path the same validator runs and the same message appears,
but `input.files` is never touched. That is principled: a drop is the script's own act, so
declining to perform it is the script doing nothing; a pick is the visitor's act through
the browser's own control, and silently discarding their choice would be the script undoing
a person's input to spare them a server error it is not entitled to predict. In both cases
the bytes that reach the server reach it through the identical form. A browser check now
pins that direction too — a refused drop must leave an already-chosen file alone.

---

## The three clauses D19 asked for that were deliberately NOT built

Each is restated here, with its ground, so the developer can reverse any of them knowingly.

1. **No client-side canvas crop.** `companion/illustration_normalize.py`'s own docstring
   records that a *second, differently-thresholded measurement silently drifting from the
   first* is the debug session (`illustration-crop-text-margin`) that created it, and that
   the module "must never become a second implementation for that same measurement to drift
   against". A browser-side crop that "matches" it is exactly that second implementation, in
   a language the server cannot check, on a machine it cannot trust. The absence is
   asserted: `panel-lookup.js` names no `getContext`, `drawImage`, `toBlob`, `toDataURL`,
   `OffscreenCanvas` or `createImageBitmap`, comments included.
2. **No progress bar.** `companion/static/submit-guard.js` already disables a form's submit
   button on submit, app-wide. A 4 MB cap against a household server needs the word
   "Uploading…", not `XMLHttpRequest.upload.onprogress`.
3. **No hover-only aircraft types.** Hover is unreachable by touch — the ground CFG-28 used
   when it moved this app's tooltips out from behind hover. The drop zone's own drag state
   follows the same rule: it rides on `[data-upload-drop-active]`, and a harness clause
   fails if any `.upload-drop` rule uses `:hover`.

---

## What was built

### Task 1 — the markup and the paint, over forms that did not change

`_upload_drop_html(input_id)` — one definition, three call sites (both copies of
`_resolve_upload_form_html()` and the single `_lightbox_replace_form_html()`), because a
drop zone rendered twice from two definitions is two drop zones that can disagree. It emits
a gated `<section>` carrying the hint, a reserved preview box, the framing caption and an
empty message element, with the three refusal messages rendered **already translated** as
data attributes so the script writes no copy of its own (25-01's `value-controls.js` set
that precedent; `companion/i18n_fr/airlines.py` gained the six new strings).

Three properties worth naming:

- **The forms did not change.** A harness check pins, byte-for-byte against *retyped
  pre-25-07 literals* (never against whatever the builder currently emits, which would only
  restate itself), each rendering's `<input type="file" id="…" name="image"
  accept="image/png" required>`, its single bare `<button type="submit">`, its hint
  paragraph, its `method`/`enctype`/`action` — including the dialog copies' empty
  placeholder — and that each contains exactly one `<form>`. **The one addition is an `id`
  on each form**, carrying the existing `id_suffix` where one exists, so 25-01's registry
  can *declare* this control's form association rather than guess it. That is the only
  attribute this plan added to either form tag and it is recorded here because "byte-
  identical" was the criterion.
- **The preview box reserves `illustration_normalize.py`'s own frame**, through an inline
  `--upload-preview-ratio` computed from `ILLUSTRATION_TARGET_WIDTH/HEIGHT` (already
  imported by this module for the gallery's `<img>` dimensions). `style.css` reads it with
  **no fallback value**: a fallback would keep the box the right shape after the inline
  property stopped being rendered, which masks the deletion of the live value rather than
  guarding it. Measured at 360 px, at rest, before any image exists: **3.4098:1** against
  the module's **3.4091:1**.
- **No `<div>` anywhere in the added markup**, and that is load-bearing.
  `test_status_pages.py`'s replace-zone contract matches `<div class="lightbox__replace-
  zone">.*?</div>` **non-greedily**, so a nested `<div>` would truncate its capture and make
  a correct page fail a check about element order. `<section>`/`<figure>`/`<p>` say more
  about this markup anyway, and both call sites carry a comment pointing at the reason.

### Task 2 — the drop handling, in the file that already owns these forms

`panel-lookup.js` grew by 283 lines and its header says why: Phase 25's budget was one new
script and 25-01 spent it, and a second file here would pay a route in `app.py`, a src in
`layout.py` and a move of the deferred-script pin for one listener on forms this file
already owns (it rewrites both of their `action` attributes on every trigger click).
`ls companion/static/*.js | wc -l` is **17**, unchanged; the deferred-script pin is still
fifteen; `value-controls.js` is untouched.

The block sits **above** the dialog guard, with a comment explaining the choice: the drop
affordance is revealed by the `.js` gate, and that class is set by `nav-dropdown.js`
entirely independently of this file, so an early return below would leave a visible, inert
drop target — the exact "renders and does nothing" defect the gate exists to prevent. The
one hook that genuinely needs the dialog (clearing previews on `close`) is wired inside the
guarded region.

The file's three standing constraints survive the growth — no network call, no timer, no
persistent state, nothing through a raw-markup sink — and it gained a fourth, stated as
absolutely: no canvas code of any kind. A `FileReader` is none of the first three: it reads
a file the visitor themselves handed to this document, for the preview and nothing else.

### Task 3 — the proof, in a real browser

`_upload_without_js()` is the **stated file-input variant** of 25-02's persist helper, and
the plan was right to anticipate one: `_persist_without_js()` operates its control by
assigning to `.value`, which the browser forbids on `<input type="file">` — a restriction
no amount of parameterising gets around. Everything else is 25-02's discipline unchanged: it
runs inside `_no_js_page()` (this file's one scripts-blocked call site stays one), and **the
verdict is the value read back off disk**, never off the page, because a POST this app
rejected redirects to a page that looks exactly like success (there is a named flash key for
it). It adds the clause the field case has no counterpart for: the illustration route serves
the artwork back afterwards, measured as an *image at
`illustration_normalize.ILLUSTRATION_TARGET_SIZE`* rather than as "200 plus a byte count".

---

## Measurements

All taken on this tree, at the stated viewport, through a real Chromium.

| Measurement | Value |
|---|---|
| `.js` gate, scripts blocked (360 px) | `boxes [[0, 0]]`, `candidates 0`, `tabbable_on_page 74` |
| `.js` gate, scripts enabled | `boxes [[246, 157.95]]`, `revealed 1` |
| Hit target, **this control's own container**, 360 px | visual `240.25 × 154.26`, **hit `241 × 154`**, reach `(120, 120, 76, 77)`, not clipped |
| `documentElement.scrollWidth / clientWidth` on Airlines at 360 px | `360 / 360` — no sideways scroll |
| Preview box at rest, before any image | `225.72 × 66.20` → **3.4098:1** vs the module's **3.4091:1** |
| Preview after a drop | `naturalWidth/Height [1200, 300]` — the source file's own size, src scheme `data` |
| Drag state, sampled **between `dragOver` and `drop`** | `active_during_drag: True`, `active_after_drop: False` |
| Zone paint at rest → mid-drag (light) | background `rgba(0,0,0,0)` → `rgb(238,232,222)`; preview border `dashed rgb(223,215,200)` → `solid rgb(23,25,31)` |
| Light theme | canvas `rgb(247,244,239)`, note `srgb 0.09 0.098 0.122 / 0.7`, frame `rgb(223,215,200)`, surface `rgb(255,255,255)`, message `rgb(190,18,60)` |
| Dark theme | canvas `rgb(12,15,20)`, note `srgb 0.945 0.953 0.965 / 0.7`, frame `rgb(42,48,64)`, surface `rgb(21,25,34)`, message `rgb(251,113,133)` |
| Refusal message contrast against the page canvas | **5.73:1** light, **7.13:1** dark (both over WCAG AA 4.5) |
| Scripts-blocked upload | stored **1833 bytes** on disk; route served an image at `(450, 132)` |
| Picked vs dropped, same source file | stored bytes **identical**; in-input size `1833 == 1833` |

**The fixture was restored.** Every one of the three checks deletes the override file it
wrote in its own `finally`, the block runs on its **own isolated `Harness()`** (seeded with
a Step-B manual entry) rather than the shared fixture forty other checks depend on, and that
harness and its temp art directory are torn down at the end. A guard at the top of the
equivalence check fails loudly if stored artwork is on disk when it starts.

---

## Mutation testing — 55 mutations

Every one was applied to the file on disk, the **real diff printed with its line numbers**
so the line actually changed was confirmed rather than assumed, then reverted with
`git checkout-index -f --` and `__pycache__` cleared.

### Task 1 — eleven, against `companion/test_status_pages.py`, all RED

| # | Mutation | Quoted failure |
|---|---|---|
| M1 | drop `required` from the file input | *"the lightbox replace form: expected exactly one `<input type="file" id="airline-replace-input" name="image" accept="image/png" required>` — the drop zone changes the affordance, never the control the form posts"* |
| M2 | remove the replace form's new `id` | *"the lightbox replace form: expected `id="airline-replace-form"` in the form's opening tag `<form class="lightbox__replace" method="post" enctype="multipart/form-data" action="">`…"* |
| M3 | drop the `id_suffix` from the upload form's id | *"the Airlines page emits duplicate id(s) `['manual-illustration-form']` — HTML requires every id to be document-unique, and adding markup to a form that exists twice is exactly how that breaks (this is what `id_suffix` is for)"* |
| M4 | render the wrapper without `JS_GATE_CLASS` | *"an element carries data-upload-drop OUTSIDE the 'js-gate' gate — `<section class="upload-drop " data-upload-drop …>`. A drop target that cannot receive a drop must not advertise one…"* |
| M5 | move the drop zone before the submit button | *"the no-JS fallback upload form: the drop zone renders BEFORE the submit button — it is an enhancement appended to a working form, not a layer spliced into it"* |
| M6 | reserve `900 / 263` (the real superseded frame) instead of the module's | *"the preview box reserves (900, 263) but companion/illustration_normalize.py's output frame is (450, 132) — a preview promising a shape the server does not produce is the SECOND measurement that module's own docstring exists to forbid"* |
| M7 | give `var(--upload-preview-ratio)` a fallback | *"companion/static/style.css gives --upload-preview-ratio a FALLBACK value — a fallback would keep the box the right shape even after the inline property stopped being rendered, masking the deletion of the live value rather than guarding against it"* |
| M8 | turn the drag-state rule into `:hover` | *"`.upload-drop:hover` is a :hover rule — the drag state must be reachable by touch, which is why it rides on [data-upload-drop-active] instead (the ground CFG-28 used for this app's tooltips)"* |
| M9 | replace a theme token with `rgb(190, 18, 60)` | *"`.upload-drop__message` declares the colour literal 'rgb(' — every colour in this block must come from a theme token so both themes stay load-bearing"* |
| M10 | rename `.upload-drop__note` to `.upload-drop__notes` | *"companion/static/style.css declares no `.upload-drop__note` selector on a boundary"* |
| M11 | delete both `[data-upload-drop-active]` rules | *"companion/static/style.css declares no [data-upload-drop-active] rule — the drag state would have nowhere to paint"* |

**M9 caught me first, exactly as trap 1 predicts.** The first attempt anchored on the bare
declaration `color: var(--color-status-error);\n}` — and style.css's **first** such
occurrence is at line **745**, an unrelated rule. The mutation applied, the diff looked
perfectly right, and the harness stayed green because the rule I meant to break was never
touched. Re-anchored on the whole `.upload-drop__message` rule, the diff reported
`@@ -7965 +7965 @@` — my own block — and the check went red with the message above.

### Task 2 — seven, against `companion/test_companion_app.py`, all RED

| # | Mutation | Quoted failure |
|---|---|---|
| T2-M1 | add a canvas crop before the preview | *"panel-lookup.js names 'getContext' — no canvas API may appear in this file. The crop belongs to companion/illustration_normalize.py alone, whose own docstring forbids a second implementation of the measurement it owns"* |
| T2-M2 | delete `input.files = transfer.files` | *"panel-lookup.js never assigns a DataTransfer's files to the form's own file input — that assignment IS the design: it is what makes a dropped file and a picked file travel one path, with one size cap and one parser"* |
| T2-M3 | add a second `new DataTransfer()` | *"expected exactly one `new DataTransfer()` in panel-lookup.js, got 2 — two would be two ways into the same input"* |
| T2-M4 | make the picker path skip the validator | *"expected uploadRefusal() to be called exactly twice (once from the drop path, once from the picker path), got 1 — a path that reaches the input without passing through it is a path that validates differently"* |
| T2-M5 | move the refusal after the assignment | *"panel-lookup.js assigns the dropped file BEFORE consulting the validator — the refusal has to happen first or it refuses nothing"* |
| T2-M6 | delete the `isTrusted` guard | *"panel-lookup.js's drop handler does not refuse an untrusted event — a script running in this document could otherwise dispatch a drop carrying a DataTransfer it built itself"* |
| T2-M7 | preview through an object URL | *"panel-lookup.js names createObjectURL — an object URL is a blob: URL, and this app's Content-Security-Policy (img-src 'self' data:) blocks a blob: image. Either the preview is broken or the policy was widened for it"* |

### Task 3 — seven behavioural, against `companion/test_browser_ux.py`, all RED

| # | Mutation | Quoted failure |
|---|---|---|
| T3-M1 | drop path skips the validator | *"a zero-files drop was refused silently — a drop target that declines without saying so is indistinguishable from one that is broken"* |
| T3-M2 | multiply the size cap by 1000 | *"a oversized drop assigned 1 file(s) to the form's input — the refusal has to happen BEFORE the assignment or it refuses nothing ({… 'name': 'oversized.png', 'size': 5769336 …})"* |
| T3-M3 | allow several files at once | *"a several drop assigned 1 file(s) to the form's input — the refusal has to happen BEFORE the assignment or it refuses nothing"* |
| T3-M4 | stop removing the preview's `src` | *"a refused drop left the previous preview's 'data' src on the `<img>` … — the decoded file stays in the document for as long as the page does"* |
| T3-M5 | delete the `isTrusted` guard | *"a synthetic (isTrusted: false) drop reached the handler and produced 'Only PNG images can be dropped here.' — the only way into it should be a gesture a person performed"* |
| T3-M6 | **a deliberate client-side transform** (drop a File built from `slice(0, size - 1)`) | *"the picked file measured 1833 bytes in the input and the dropped one 1832 — the script altered the file on the way in"* |
| T3-M38 | harness-side: perturb `picked_bytes` | *"the SAME source file stored 1834 bytes when picked and 1833 when dropped — a second transform crept into the drop path, which is exactly the drift no client-side crop was written to avoid"* |

### Task 3 — twenty-nine CSS declarations, plus a null control

Every declaration this plan adds to `style.css` was mutated and the **rendered** result
re-measured in a real browser (one app process, a fresh browser context per measurement so
the 300 s cache header cannot serve a stale stylesheet), at rest, with a file chosen, and
with a refusal message showing.

**All twenty-nine moved their own named measurement.** The load-bearing ones and what
moved: `--js-gate-display` (`display: flex → block`, zone height `157 → 140`),
`flex-direction` (the whole zone laid out in a row; preview `229 → 59` wide), `gap`
(`row-gap: 8px → normal`, height `157 → 139`), `padding` (preview width `230 → 246`),
`.upload-drop__note`'s `margin` (`0 → 13px 0`, zone height `157 → 206`), `font-size`
(`13 → 16px`), `color` (`…/0.7 → rgb(23,25,31)`); `.upload-drop__preview`'s `margin`
(`0 → 16px 40px` — the `<figure>` UA margin), `width`, `aspect-ratio` (`450 / 132 → auto`,
box `67.4 → 57.9`), `overflow` (`hidden → visible`), `border`, `border-radius` (`8 → 0`),
`background`; `.upload-drop__image`'s `display`, `width` (box `227 → 1369`), `height`,
`object-fit` (`contain → fill`); `.upload-drop__message`'s `margin`, `font-size`,
`font-weight`, `color`; and both `:empty`/`:not([hidden])` selectors.

Four of them are drag-state only and the wide sweep could not see them at all, because it
never entered a drag. Re-measured **while the browser was in a drag** (CDP `dragEnter` +
`dragOver`, sampled before `drop`): `[data-upload-drop-active] background`
`rgb(238,232,222) → rgba(0,0,0,0)`, `border-style` `solid → dashed`, `border-color`
`rgb(23,25,31) → rgb(223,215,200)`, and `.upload-drop`'s own `border-radius` `8px → 0px`.
The last of those is **load-bearing but only in paint** — it rounds the drag-state wash and
moves no geometry; it is recorded as such rather than claimed as a layout property.

Two selector mutations deserve their own line because they are the traps this file already
documents: `.upload-drop__image:not([hidden])` → `.upload-drop__image` made the preview
`<img>` paint at `display: block` **while still carrying the `hidden` attribute** — the
exact specificity tie `.resolve-upload-zone:not([hidden])` exists for — and deleting
`.upload-drop__message:empty` made an empty message element take up a real box.

**The null control is the reason any of that can be believed.** A mutation that edits only
a *comment* inside the block reported **14 measurements moved** — every one of them a
sub-pixel-to-4-pixel geometry jitter in the dialog's own width. Without it, every mutation
in the sweep would have looked RED for the wrong reason. The named computed properties
above moved for the null control **not at all**, which is what separates signal from
layout noise here.

---

## Checks that failed the vacuity question, and what changed

1. **The `--upload-preview-ratio` fallback clause was unreachable.** The "style.css reads
   the property" clause tested for the exact string `var(--upload-preview-ratio)`. Adding a
   fallback changes that string, so mutation M7 tripped the *wrong* clause — right verdict,
   wrong reason, and the fallback clause could never fire. Matched with either terminator
   (`[,)]`) instead; M7 then failed with the message it was written for.
2. **`uploadRefusal(...)` was counted three times, not two.** The caller count matched the
   **definition line** as well, and failed a correct implementation. Anchored on
   `= uploadRefusal(zone, files);`.
3. **The preview-release clause could not fire.** Asserting "no `src` after a refusal"
   inside the four floor cases proved nothing, because none of them had a preview on screen
   to release — mutation T3-M4 came back **GREEN**. A fifth sequence was added (drop a valid
   file, *then* drop a wrong-type one) and T3-M4 went red with the message above. The same
   sequence added a clause worth having on its own: a refused drop must leave a file the
   visitor already chose alone.
4. **The byte-equality clause is the weakest of the three equivalence clauses, and that is
   now recorded rather than assumed.** The realistic transform mutation (T3-M6) did **not**
   trip it: the server re-encodes every upload through Pillow, which absorbed a one-byte
   truncation and produced byte-identical output. The clause that bit was the in-input file
   **size** comparison. Byte equality was proven able to fire at all by a harness-side
   mutation (T3-M38). The honest statement is that this control is protected from a
   client-side transform by three things in this order: the static absence of every canvas
   API, the in-input size comparison, and — for a transform that changes pixels — the byte
   comparison.
5. **The oversized fixture is proved oversized before it is used**, against the cap read
   back out of the page (the app's own number), because an "oversized" file that is not
   actually over the cap measures nothing while reading exactly like a passing check.

---

## Criteria that did not evaluate as predicted, and plan assumptions that were wrong

1. **`URL.createObjectURL()` is unusable here** — the plan's central preview mechanism and
   one of its acceptance criteria. Measured, blocked by this app's own CSP; see the decision
   above. The criterion "`createObjectURL` is paired with `revokeObjectURL`" was replaced by
   a **stronger** one: the file names `createObjectURL` nowhere at all, and a browser check
   asserts the preview's `src` is *removed* on replacement, refusal and dialog close.
2. **`page.request` does not carry the browser context's session cookie** on this tree's
   Playwright, despite being documented as sharing the cookie jar. An authenticated fetch
   through it follows the redirect to `/login` and returns **200 with a 1493-byte HTML
   page** — a "served the artwork, status 200" assertion would have passed against the login
   screen. `_upload_without_js()` navigates instead, and its docstring records the
   measurement.
3. **A successful upload hides the control that performed it.** Once artwork exists the
   manual entry leaves `needs-artwork`, and `panel-lookup.js` hides the dialog's upload zone
   in every other mode — so the equivalence check's *second* upload had nowhere to happen.
   The fix is also what makes the comparison mean anything: the stored file is deleted
   between the two uploads. This was diagnosed only after `_await_upload_zone()` was written
   to say **why** a gate did not open (the `.js` class, the dialog's `open`, the zone's
   `hidden`, and every card's resolve mode) instead of timing out with a rectangle.
4. **`from server.plane import manual_resolutions` was already imported** in
   `test_status_pages.py`; the plan's interface re-measurement did not catch it and `ruff`
   did. Removed.
5. **The `@supports selector(:has(*))` criterion is only meaningful brace-anchored.** A bare
   `grep -c` of that string returns **6** on this file (five of them prose). Brace-anchored
   it is **1** and stayed 1. This plan's own CSS comment deliberately does not spell out the
   keyframes at-rule keyword either, for the same reason trap 13 names.

---

## Properties found inert

**One**, and it was removed rather than documented: `.upload-drop { width: 100% }`. The
wrapper is a block-level `<section>` inside the upload form, so it already fills that form's
content box. Removing the declaration moved the rendered width by **0.00 px** at 1280 and
left it *exactly equal* to the form's inner width, while the comment-only null mutation
moved the same measurement by 0.01 px. A declaration that cannot be told from the null
control is dead code. The same mutation on `.upload-drop__preview { width: 100% }` moved the
rendering by ~1.9 px — well outside the null control's 0.01 px — so that one stays, and the
stylesheet now carries a comment recording both results.

---

## Re-derived counts, obtained by RUNNING

| Harness | Before | After |
|---|---|---|
| `companion/test_browser_ux.py` | 78 | **81** (81/81, 0 SKIP) |
| `companion/test_status_pages.py` | 302 | **305** (304/305 — the one baseline `anomaly_active()` failure) |
| `companion/test_companion_app.py` | 313 | **314** (312/314 — the two baseline WR-11 failures) |
| `companion/test_view_pages.py` | 164 | 164 (one check retargeted in place, no count change) |
| `companion/test_config_page.py` | 259 | 259 |
| `companion/test_i18n.py` | 24 | 24 |
| `companion/test_contrast_check.py` | 49 | 49 |

Structural pins, all unchanged: `ls companion/static/*.js | wc -l` = **17**;
brace-anchored `@supports selector(:has(*))` blocks = **1**; `@keyframes` = **5**; deferred
scripts on the authenticated shell = **fifteen** (its own check passes).

`companion/illustration_normalize.py`, `companion/app.py`, `companion/layout.py` and
`companion/static/value-controls.js` are **unchanged by one line** against the plan's base
commit `95f45f1`, verified by `git diff --stat`. `.planning/STATE.md`, `ROADMAP.md` and
`REQUIREMENTS.md` were not touched — CFG-46…CFG-52 belong to 25-08.

**Full suite:** `PYTHON=server/.venv/bin/python3 bash scripts/run-all-tests.sh` →
**exactly the 5 sandbox baseline failures, verified BY NAME**:

1. `POST /airlines/resolve … manual_save_failed flash key … state dir is read-only` (WR-11)
2. `POST /airlines/manual-resolutions/{prefix}/delete … manual_delete_failed …` (WR-11)
3. `add_entry() returns ADD_FAILED … parent directory is read-only` (WR-11)
4. `delete_entry() returns False … state dir goes read-only mid-write` (WR-11)
5. `anomaly_active() runs on every page render and must never raise`

No sixth. `ruff check .` clean. `companion/test_browser_ux.py` does not SKIP.

---

## A process failure worth recording

**I hit trap 15 myself, in the direction it warns about.** The Task 1 mutations were run
against a staged tree, correctly. The first Task 2 mutation was run against an **unstaged**
one — and `run_mut.sh`'s revert step, `git checkout-index -f --`, restored
`panel-lookup.js` from the index, deleting the entire Task 2 implementation in one step.
Nothing was lost permanently (it was re-applied and the harnesses re-run from scratch), but
the lesson is exactly the one the trap states and it cost a full re-write: **stage before
you mutate, every time, not the first time.**

---

## Known stubs

None. Every element this plan renders is filled by either the server or the script, and the
one element rendered empty (`.upload-drop__message`) is collapsed by `:empty` until there is
something to say.

---

## Self-Check: PASSED

Files claimed created/modified, verified on disk:

```
FOUND: companion/pages/airlines_page.py
FOUND: companion/static/panel-lookup.js
FOUND: companion/static/style.css
FOUND: companion/i18n_fr/airlines.py
FOUND: companion/test_status_pages.py
FOUND: companion/test_companion_app.py
FOUND: companion/test_view_pages.py
FOUND: companion/test_browser_ux.py
```

Commits claimed, verified in `git log`:

```
FOUND: ff2c374  feat(25-07): a drop target that appears only where it can work
FOUND: f5a9357  feat(25-07): a gesture added, and a second crop conspicuously absent
FOUND: 93df2c1  test(25-07): dropping and picking proven the same act, in a real browser
```
