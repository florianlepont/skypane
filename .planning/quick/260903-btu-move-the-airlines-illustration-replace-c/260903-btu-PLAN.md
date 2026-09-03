---
phase: quick-260903-btu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/pages/airlines_page.py
  - companion/static/panel-lookup.js
  - companion/static/style.css
  - companion/test_status_pages.py
  - companion/test_view_pages.py
  - companion/test_companion_app.py
autonomous: false
requirements: [REQ-260903-btu-WEB]
must_haves:
  truths:
    - "Opening an Airlines card's click-to-enlarge lightbox shows, inside that dialog, a file-upload form for replacing that airline's illustration."
    - "No Airlines grid card carries a replace control of any kind any more — the per-card <details> disclosure is gone from the rendered page, from the stylesheet, and from airlines_page.py's module surface."
    - "The lightbox's replace form POSTs to the illustration route of whichever card was clicked, resolved at click time from that card's own trigger attribute, with no cache-busting query string on the POST target."
    - "History's lightbox still opens, still swaps image src/alt and caption, and still closes — and History's rendered page contains zero replace-related markup or attributes."
    - "companion/static/panel-lookup.js gained exactly one optional element lookup and one conditional attribute write; its mandatory three-element guard, its ES5-safe dialect, its no-network/no-timer/no-persistent-state posture and its never-decide-from-viewport-or-orientation constraint are all unchanged."
  artifacts:
    - companion/pages/airlines_page.py
    - companion/static/panel-lookup.js
    - companion/static/style.css
  key_links:
    - ".airline-card__zoom[data-view-panel-replace-action] -> panel-lookup.js click handler -> form.lightbox__replace[action] inside #panel-lookup-dialog"
    - "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR literal == the getAttribute() literal in panel-lookup.js"
    - "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS literal == the querySelector() literal in panel-lookup.js == the .lightbox__replace selector in style.css"
    - "the replace action value == the UN-busted /illustration/{key}.png, while the same trigger's data-view-panel-src stays busted — the two deliberately differ"
    - "panel-lookup.js's mandatory `if (!image || !caption || !note)` guard excludes the new lookup — this is the single line that keeps History's lightbox alive"
---

<objective>
Move the Airlines gallery's illustration-replace control out of the per-card `<details>` disclosure quick task 260902-v26 shipped, and into the shared click-to-enlarge lightbox quick task 260902-tli shipped.

The developer's own words: *"je m'attendais à ce que la proposition de remplacement soit disponible une fois qu'on a zoomé sur la photo"* — the replace affordance belongs at the moment you have deliberately opened a closer look, not stacked under all 27 grid thumbnails at once.

Purpose: one replace form per page instead of 27, reached at the moment the user is already looking closely at the illustration they want to change. The disclosure is **removed, not duplicated** — the control lives only inside the lightbox now.

Output: a single `<form class="lightbox__replace">` inside Airlines' `<dialog>`, whose `action` is written per-click by `panel-lookup.js` from a new optional `data-view-panel-replace-action` attribute on each card's zoom trigger; the retired per-card markup, CSS and test coverage cleaned up rather than left pinning something that no longer exists; and History's own lightbox provably untouched.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260903-btu-move-the-airlines-illustration-replace-c/260903-btu-CONTEXT.md
@companion/pages/airlines_page.py
@companion/static/panel-lookup.js
@companion/pages/history_page.py
</context>

<verified_current_state>
Everything below was re-read from the real working tree at planning time (2026-09-03), not carried over from CONTEXT.md's pre-edit line numbers. Trust these, and re-confirm by reading before editing.

**`companion/static/panel-lookup.js`** (109 lines). Structure:
- lines 1-38: header block comment, which already states the "writes them into the dialog's image src/alt and caption textContent" sink list and the standing no-network/no-timer/no-persistent-state and never-decide-from-viewport-or-orientation constraints.
- line 42-45: `getElementById("panel-lookup-dialog")` guard.
- line 51-53: `showModal` capability guard.
- lines 55-60: the **mandatory** lookup block —
  `var image / var caption / var note` then `if (!image || !caption || !note) { return; }`.
- lines 66-75: `findTriggerAncestor()` ES5 ancestor walk on `data-view-panel-src`.
- lines 77-90: the document-level click handler — reads `data-view-panel-src` and `data-view-panel-caption` off the trigger, writes `image.src`, `image.alt`, `caption.textContent`, then `dialog.showModal()`.
- lines 92-97: the close-button wiring.
- lines 99-108: two "do not add this later" trailing comments.

**`companion/pages/airlines_page.py`** (474 lines). Relevant current facts:
- `ILLUSTRATION_ROUTE_PREFIX = "/illustration/"` (line 49); `CARD_IMAGE_ALT_TEMPLATE = "%s illustration"` (line 54).
- `LIGHTBOX_DIALOG_ID` / `_VIEW_PANEL_SRC_ATTR` / `_VIEW_PANEL_CAPTION_ATTR` / `_VIEW_PANEL_CLOSE_ATTR` (lines 72-75), duplicated-not-imported from `history_page` and pinned equal to it by `test_view_pages._airlines_lightbox_constants_match_history()`.
- `LIGHTBOX_NOTE = ""` (line 95).
- `REPLACE_SUMMARY_TEMPLATE = "Replace %s illustration"` / `REPLACE_LABEL_TEMPLATE = "New image for %s"` / `REPLACE_BUTTON_TEXT = "Upload"` (lines 123-125).
- `_replace_control_html(key, airline_name, action_url)` (lines 208-260) — emits `<details class="airline-card__replace"><summary>…</summary><form class="airline-card__replace-form" method="post" enctype="multipart/form-data" action="…"><label for><input type="file" name="image" accept="image/png" required><button type="submit"></form></details>`, with input id `airline-replace-{key}`.
- `_airline_card_html()` (lines 263-350) — builds `image_url` (un-busted) then `busted_image_url`; the zoom `<button class="airline-card__zoom">` carries `data-view-panel-src="{busted}"` + `data-view-panel-caption` + `aria-label`; line 340 calls `_replace_control_html(key, airline_name, image_url)` and line 350 interpolates it as the card's last child.
- `_lightbox_html()` (lines 367-389) — `<dialog class="lightbox lightbox--wide" id=…>` + `.lightbox__image` + `.lightbox__caption` + `.lightbox__note` + close `<button>`.
- `render()` (lines 444-474) — emits header, filter bar, grid, then `_lightbox_html()` only when `pairs` is non-empty.

**`companion/pages/history_page.py`** — `_lightbox_html()` at lines 449-464, emitting `<dialog class="lightbox" id=…>` with the same three `lightbox__*` elements and close button. **This function is not edited by this plan.**

**`companion/static/style.css`** — the six rules to retire are lines **3042-3098** (a leading `/* quick task 260902-v26 … */` comment block, then `.airline-card__replace`, `.airline-card__replace summary`, `… summary::marker`, `… summary::-webkit-details-marker`, `.airline-card__replace-form`, `.airline-card__replace-form input[type="file"]`). The lightbox section is lines **3491-3563** (`.lightbox`, `.lightbox__image`, `.lightbox__caption`, `.lightbox__note`, `.lightbox__note:empty`, `.lightbox::backdrop`, `.lightbox--wide`, `.lightbox--wide .lightbox__image`).

**Existing test coverage of the OLD shape** — all six are in `companion/test_status_pages.py`, in the block starting at line 4972 (`# quick task 260902-v26: the per-card "replace this image" control.`):
1. `_replace_form_action_matches_route_membership` (4976) — N forms, action membership in `illustrations.target_filenames()`.
2. `_replace_form_declares_post_and_multipart_enctype` (5001).
3. `_replace_form_file_input_ids_are_unique_and_labelled` (5024).
4. `_cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override` (5046) — still valid, needs extending.
5. `_replace_control_escapes_hostile_airline_name` (5088) — asserts `REPLACE_SUMMARY_TEMPLATE`/`REPLACE_LABEL_TEMPLATE` escaped output.
6. `_replace_disclosure_contains_no_revert_or_reset_control` (5119) — regex over `<details class="airline-card__replace">…</details>`.

`companion/test_view_pages.py` and `companion/test_companion_app.py` contain **no** assertions against the old per-card disclosure (verified by grep for `airline-card__replace` / `_replace_control_html` / `REPLACE_*` — zero hits in both). They do contain the shared-lightbox contract checks this plan extends: `_lightbox_dom_contract_three_file_guard` (test_view_pages.py:1341), `_airlines_lightbox_constants_match_history` (1392), and `_panel_lookup_script_es5_safe_and_no_html_write` (test_companion_app.py:1697).

**Check-count bookkeeping (current on-disk values):**
- `companion/test_status_pages.py` — `EXPECTED_CHECK_COUNT = 123` (line 265)
- `companion/test_view_pages.py` — `EXPECTED_CHECK_COUNT = 45` (line 69)
- `companion/test_companion_app.py` — `EXPECTED_CHECK_COUNT = 125` (line 81)

**Runtime facts.** `POST /airlines` is not routed by `companion/app.py` — the POST dispatch falls through to `send_html(404, …)` (app.py line ~1349). The upload route is `POST /illustration/{key}.png`, session-gated, handled by `Handler._handle_illustration_replace()` (app.py line 959), which redirects to `/airlines?flash=…`. The form field name it reads is `image`. Tests are run directly: `python3 companion/test_status_pages.py` (and `scripts/run-all-tests.sh` for the full set).
</verified_current_state>

<design_decision_record>
Derived during planning; the executor implements these, it does not re-derive them.

**The copy constants must change, and CONTEXT.md's "Claude's Discretion" item is resolved here.** Both `REPLACE_SUMMARY_TEMPLATE` ("Replace %s illustration") and `REPLACE_LABEL_TEMPLATE` ("New image for %s") interpolate an airline name. The lightbox is emitted **once per page**, so at render time there is no airline name to interpolate — and `panel-lookup.js` is constrained to exactly one new write (the `action` attribute), so it cannot fill the name in at click time either. The `%s` slot is therefore unfillable and the copy must become airline-agnostic. This is safe because the dialog **already** names the airline: `.lightbox__caption` is written from `data-view-panel-caption`, which is `CARD_IMAGE_ALT_TEMPLATE % airline_name` ("Air France illustration"). A generic label sitting directly under that caption is unambiguous.

Resolution: `REPLACE_SUMMARY_TEMPLATE` and `REPLACE_LABEL_TEMPLATE` are **deleted**; `REPLACE_LABEL_TEXT = "Replace this illustration"` replaces them (it absorbs the summary's job of naming the action, since there is no `<summary>` any more); `REPLACE_BUTTON_TEXT = "Upload"` **carries over byte-identical** — already-approved copy whose meaning still fits exactly.

**Design-system conformance** (checked against the `sketch-findings-skypane` skill, so the executor does not need to re-adjudicate):
- `.lightbox` is one of the two named floating-overlay exceptions (resting shadow, `--radius-card`) — the form lives inside it and adds no new card treatment.
- The form is separated from the viewing content above it by a `1px solid var(--color-border)` top rule. `--color-border` is "structural only — a divider"; this is exactly that role, not an interactive-state signal.
- The `<label>` takes the **existing sub-scale label tier** the retired `.airline-card__replace summary` already used — `font-size: 13px` + `color-mix(in srgb, var(--color-text) 70%, transparent)`. Carried forward verbatim, so no new size and no new colour token enters the stylesheet.
- The native `input[type="file"]` keeps its global 44px touch-target floor (untouched — it is on the "kept" side of the floor register). The `button[type="submit"]` keeps the global 30px primary accent-fill treatment (untouched).
- **No new accent use.** `button[type="submit"]` is already an enumerated member of style.css's exhaustive accent-reservation list in its header comment, so that list needs **no edit**. Do not add one.
- `min-width: 0` on the form and `max-width: 100%` on the file input carry forward from the retired `.airline-card__replace-form` rules — a long uploaded filename's intrinsic content width is still able to push the dialog wide without them.

**Element order inside the dialog:** image → caption → note → **form** → Close button. Close stays last so the dismissal affordance is the stable bottom-most control and the tab order reads "look, act, dismiss". `panel-lookup.js` finds the close button by attribute (`[data-view-panel-close]`), so order is not load-bearing for the script — only for the human.

**`action=""` with JavaScript unavailable.** The empty-string placeholder means "submit to the current URL", i.e. `POST /airlines`, which this app 404s (verified above). That is a clean, harmless degradation — no write to a wrong key, no unauthenticated path — and is the correct behaviour to accept rather than engineer around, matching the JS-free-degradation posture the rest of this codebase already takes (`list-filter.js`'s early return, `panel-lookup.js`'s own guards). Do not add a `<noscript>` or a server-side fallback route.

**The new constants are Airlines-only, NOT part of the History-parity contract.** `test_view_pages._airlines_lightbox_constants_match_history()` pins four constants against `history_page`'s own values. `_VIEW_PANEL_REPLACE_ACTION_ATTR` and `LIGHTBOX_REPLACE_FORM_CLASS` have no `history_page` counterpart by design — **do not add them to that check's `pairs` tuple.** Doing so would fail with an `AttributeError` and, worse, would push the project toward giving History a replace form.
</design_decision_record>

<source_coverage_audit>
CONTEXT.md carries prose decision headings rather than `D-NN` ids, so this audit is keyed on those headings verbatim.

| Source item (CONTEXT.md heading) | Covered by |
|---|---|
| "The per-card disclosure is removed entirely, not duplicated" | Task 1 (markup + module surface), Task 2 (CSS), Task 3 (removal check) |
| "Technical design, grounded by reading the real current code" — third optional data attribute on the zoom trigger | Task 1 |
| "Technical design …" — form inside `_lightbox_html()` with a real `action=""` placeholder | Task 1 |
| "Technical design …" — exactly one new optional lookup + one conditional write in panel-lookup.js, mandatory guard untouched | Task 2, pinned by Task 4 |
| "Technical design …" — un-busted URL as the POST target | Task 1, pinned by Task 3 (extended cache-buster check) |
| "The form's plain-POST-with-redirect behavior is unchanged, just relocated" | Task 1 (no JS submit logic anywhere), Task 2 (script writes only `action`) |
| "History's lightbox must be provably unaffected" | Task 4 (render-level zero-replace-markup check + mandatory-guard check), Task 5 (live `GET /history`), Task 6 (human click) |
| Discretion — visual/markup shape vs. the design system | Resolved in `<design_decision_record>`; implemented in Tasks 1-2 |
| Discretion — rename/restructure `_replace_control_html()` | Resolved: replaced outright by `_lightbox_replace_form_html()` (Task 1) |
| Discretion — CSS + test cleanup, "grep thoroughly" | Tasks 2, 3, 4 (the six retargets are enumerated by name and line number above) |
| Discretion — copy constants carry over or reword | Resolved in `<design_decision_record>`; implemented in Task 1 |

No item is MISSING. No item is deferred.
</source_coverage_audit>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Relocate the replace form from the card into the lightbox (airlines_page.py)</name>
  <files>companion/pages/airlines_page.py</files>
  <behavior>
    - `render({})` contains the string `lightbox__replace` exactly once (one form per page, not per card).
    - `render({})` contains no occurrence of the retired per-card class token, and `airlines_page` has no `_replace_control_html` attribute and no `REPLACE_SUMMARY_TEMPLATE`/`REPLACE_LABEL_TEMPLATE` attribute.
    - `render({})` contains `<input type="file"` exactly once and `<form` exactly once.
    - Every rendered `.airline-card__zoom` button carries `data-view-panel-replace-action="/illustration/{key}.png"` with no `?v=` suffix, for the same key its `data-view-panel-src` points at.
    - With a state_dir holding an Air France override file, that card's `data-view-panel-src` carries `?v={mtime}` while its `data-view-panel-replace-action` does not.
    - The dialog's form tag carries `method="post"`, `enctype="multipart/form-data"` and a literally present `action=""`.
  </behavior>
  <action>
Re-read `companion/pages/airlines_page.py` before editing — line numbers in `<verified_current_state>` are correct as of planning but confirm them.

**1a. Constants.** Next to the existing `LIGHTBOX_DIALOG_ID` / `_VIEW_PANEL_*_ATTR` block, add two new module-level constants:

- `_VIEW_PANEL_REPLACE_ACTION_ATTR = "data-view-panel-replace-action"`
- `LIGHTBOX_REPLACE_FORM_CLASS = "lightbox__replace"`

Write a docstring-quality comment on this pair recording that, unlike the four constants above them, these two are **Airlines-only** and have no `history_page` counterpart — History's dialog deliberately renders neither — so they must never be added to `test_view_pages._airlines_lightbox_constants_match_history()`'s pairs tuple. Also record that both literals are duplicated into `companion/static/panel-lookup.js` (one `getAttribute` literal, one `querySelector` literal) and that `LIGHTBOX_REPLACE_FORM_CLASS` is additionally duplicated into `companion/static/style.css`'s selector — a page module has no import path to a static asset, the same duplicated-not-imported discipline the four constants above already document, and a cross-file guard pins them (Task 4).

**1b. Copy constants.** Delete `REPLACE_SUMMARY_TEMPLATE` and `REPLACE_LABEL_TEMPLATE`. Add `REPLACE_LABEL_TEXT = "Replace this illustration"`. Leave `REPLACE_BUTTON_TEXT = "Upload"` byte-identical. Add `REPLACE_INPUT_ID = "airline-replace-input"` (a single static id is now correct and sufficient — there is exactly one file input on the page, so the old per-key id derivation has nothing left to disambiguate). Update the surrounding comment block to record *why* the two templates died: the shared dialog is emitted once per page, so their `%s` airline slot is unfillable at render time, and the dialog's own caption already names the airline. Keep the existing D-04 negative-requirement note (no revert/reset/restore control anywhere) — it still applies verbatim.

**1c. Replace `_replace_control_html()` with `_lightbox_replace_form_html()`.** Delete the old function outright (do not keep a shim). The new function takes **no arguments** and returns:

a `<form>` with class `LIGHTBOX_REPLACE_FORM_CLASS`, `method="post"`, `enctype="multipart/form-data"` and `action=""`; containing a `<label for="{REPLACE_INPUT_ID}">` carrying `REPLACE_LABEL_TEXT`, an `<input type="file" id="{REPLACE_INPUT_ID}" name="image" accept="image/png" required>`, and a `<button type="submit">` carrying `REPLACE_BUTTON_TEXT`. The `name="image"` field name is what `companion/app.py`'s `Handler._handle_illustration_replace()` reads — it is not free to change.

Its docstring must carry forward the two still-true rationales from the old function's docstring (`accept="image/png"` is a browser-side picker hint only, never trusted server-side — the route parses the real PNG header; and D-04: no revert control, the vendored original stays recoverable by deleting the override file but no user-facing revert is in scope), and must add: `action=""` is a real, present placeholder attribute that `companion/static/panel-lookup.js` overwrites on every trigger click; it is never omitted, because the script writes an existing attribute rather than creating one. Record that with JavaScript unavailable this posts to the page's own URL, which `companion/app.py` 404s — a harmless degradation, deliberately not engineered around, matching this codebase's existing JS-free-degradation posture. Record that no JavaScript submit logic exists anywhere: this stays a real native multipart POST that navigates the browser away and closes the dialog by page reload.

**1d. `_airline_card_html()`.** Delete the `replace_html = _replace_control_html(...)` line and remove `replace_html` from the returned card markup and from that return's `%` tuple (the card's children become: zoom button, name, chips). Add the new attribute to the zoom `<button>`, alongside its existing two, using `_VIEW_PANEL_REPLACE_ACTION_ATTR` and the **un-busted** `image_url` — never `busted_image_url`. Rewrite the existing comment above `busted_image_url` (currently "The form's action (below, in `_replace_control_html()`) deliberately uses this UN-busted image_url…") so it points at the trigger attribute instead of at the deleted function, keeping its reasoning intact: a query string on a POST target is pointless, and the busted/un-busted split between `data-view-panel-src` and the replace action is deliberate, not drift. Update the function docstring's description of what a card contains, and its `state_dir` paragraph (that parameter now feeds only the cache buster, no longer "and to build this card's replace-upload form").

**1e. `_lightbox_html()`.** Insert `_lightbox_replace_form_html()`'s output between the `.lightbox__note` paragraph and the close `<button>`. Update the docstring: it currently claims the dialog mirrors `history_page._lightbox_html()` "element-for-element and class-for-class … with exactly two differences" — that count is now three, and the third is this form, which History deliberately never renders. Also correct the closing sentence: `panel-lookup.js` now writes the image src/alt, the caption text, **and this form's `action` attribute**.

**1f. Do not touch `render()`.** Its `state_dir` read, its `pairs`-empty guards for the filter bar and the lightbox, and its concatenation order all stay exactly as they are.

Every interpolated value continues through `escape_html()` exactly once at the point of interpolation (T-06.6.4.1-05). Note that `image_url` is already built as `"%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))` — do not escape it a second time when interpolating it into the new attribute, which would double-encode.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/ruff check companion/ && server/.venv/bin/python3 -c "
import companion.pages.airlines_page as a, re
assert not hasattr(a, '_replace_control_html'), 'old function survived'
assert not hasattr(a, 'REPLACE_SUMMARY_TEMPLATE') and not hasattr(a, 'REPLACE_LABEL_TEMPLATE'), 'retired copy constant survived'
assert a.REPLACE_BUTTON_TEXT == 'Upload'
h = a.render({})
assert h.count(a.LIGHTBOX_REPLACE_FORM_CLASS) == 1, h.count(a.LIGHTBOX_REPLACE_FORM_CLASS)
assert h.count('<form') == 1 and h.count('<input type=\"file\"') == 1
assert 'airline-card__' + 'replace' not in h, 'retired per-card control survived'
assert h.count('action=\"\"') == 1
assert 'method=\"post\"' in h and 'enctype=\"multipart/form-data\"' in h
acts = re.findall(r'data-view-panel-replace-action=\"([^\"]+)\"', h)
srcs = re.findall(r'data-view-panel-src=\"([^\"]+)\"', h)
assert len(acts) == len(srcs) > 0 and acts == srcs, 'action/src disagree with no override present'
assert all(x.startswith('/illustration/') and x.endswith('.png') for x in acts)
print('OK', len(acts), 'triggers')
"</automated>
  </verify>
  <done>`render({})` emits exactly one replace form, inside the dialog, with a present `action=""`; every zoom trigger carries an un-busted `data-view-panel-replace-action`; no per-card replace markup and no retired copy constant survives anywhere.</done>
</task>

<task type="auto">
  <name>Task 2: The two minimal panel-lookup.js edits, and the stylesheet swap</name>
  <files>companion/static/panel-lookup.js, companion/static/style.css</files>
  <action>
**2a. `companion/static/panel-lookup.js` — exactly two functional edits, nothing else.**

Edit one: **after** the mandatory `if (!image || !caption || !note) { return; }` block (never inside it, never above it), add a single optional lookup:

`var replaceForm = dialog.querySelector(".lightbox__replace");`

Edit two: inside the existing `document.addEventListener("click", ...)` handler, after the three existing writes and **before** `dialog.showModal()`, add one conditional write that, when `replaceForm` is truthy, calls `replaceForm.setAttribute("action", ...)` with the trigger's `getAttribute("data-view-panel-replace-action")` value, `|| ""`-defaulted exactly the way the two existing attribute reads already are.

Use `setAttribute`, not the `form.action` property: the property returns a resolved absolute URL rather than the literal it was given, and is shadowable by a same-named form control. `setAttribute` writes the literal attribute and sidesteps both.

Nothing else in this file changes. Specifically, do not touch: the `getElementById` guard, the `showModal` capability guard, the three mandatory lookups or their guard line, `findTriggerAncestor()`, the existing `image.src` / `image.alt` / `caption.textContent` writes, the close-button wiring, or the two trailing "do not add this later" comments.

**Update the header comment** — it currently enumerates the sinks as "the dialog's image src/alt and caption textContent", which this change makes false. Extend that sentence to also name the replace form's `action` attribute write, and state that this attribute write is an attribute write only, not a markup-parsing sink, so the file's standing sink restriction is unchanged. Add a short paragraph recording that the replace-form lookup is **deliberately optional and deliberately outside the mandatory guard**: History's dialog legitimately renders no such form, and adding this variable to that guard's condition would make the whole script no-op on History — killing History's lightbox entirely. Also record that this file still makes no network call, starts no timer, and holds no persistent state.

**COMMENT-TEXT HAZARD — read before writing any prose here.** `companion/test_companion_app.py`'s `_panel_lookup_script_es5_safe_and_no_html_write()` greps this file's **entire source, comments included**, for every entry in its local `banned` tuple. Open that function and read the real tuple before writing a single comment. Two traps in particular: several entries are ordinary English words matched with a trailing space, so a comment using one of them as a normal verb or article fails the harness; and one entry is the name of a markup-writing sink, which is why the existing header says "a raw-markup DOM sink of any kind" instead of naming it. Describe restrictions by concept, never by naming the banned token. After writing, run that harness (`python3 companion/test_companion_app.py`) before moving on — this failure mode is invisible to a Python-level check.

**2b. `companion/static/style.css` — delete six rules, add one small block.**

Delete the whole retired region (its leading `/* quick task 260902-v26 … */` comment block and all six rules through `input[type="file"] { max-width: 100%; }`). Delete it cleanly and leave **no tombstone comment** behind: Task 3 adds a check that the retired class token appears nowhere in this file, and a comment mentioning it by name would fail that check. <!-- planner-discipline-allow: airline-card__replace -->

Add a new `.lightbox__replace` block in the lightbox section, positioned after `.lightbox--wide .lightbox__image` (last in that section, matching how `.lightbox--wide` documents its own source-order placement). Implement the treatment specified in `<design_decision_record>`: a wrapping flex row with `align-items: center` and a `var(--space-sm)` gap, separated from the content above by `padding-top: var(--space-md)` and a `1px solid var(--color-border)` top rule, with `min-width: 0`; a descendant `label` rule at `font-size: 13px` and `color: color-mix(in srgb, var(--color-text) 70%, transparent)`; and a descendant `input[type="file"]` rule at `max-width: 100%`.

Restyle neither the file input's height (its global 44px floor is kept) nor the submit button (its global 30px accent-fill primary treatment is kept). Introduce no new token and no new colour. Do **not** edit this file's header accent-reservation list — `button[type="submit"]` is already an enumerated member of it, so this change adds no new accent use.

Comment the new block with the reasoning from `<design_decision_record>`: why `--color-border` is the right structural divider here, why the 13px muted label is a carry-forward of the sub-scale label tier the retired disclosure summary already used rather than a new size, and why `min-width: 0` / `max-width: 100%` are load-bearing against a long uploaded filename's intrinsic width.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 -c "
src = open('companion/static/panel-lookup.js').read()
assert src.count('if (!image || !caption || !note)') == 1
guard = [l for l in src.splitlines() if 'if (!image || !caption || !note)' in l][0]
assert 'replaceForm' not in guard, 'the optional lookup leaked into the mandatory guard'
assert src.index('if (!image || !caption || !note)') < src.index('var replaceForm'), 'optional lookup must come after the mandatory guard'
assert src.count('var replaceForm') == 1
assert src.count('setAttribute(\"action\"') == 1
assert src.count('data-view-panel-replace-action') == 1
assert src.count('.lightbox__replace') == 1
css = open('companion/static/style.css').read()
assert 'airline-card__' + 'replace' not in css, 'retired rule or tombstone comment survived in style.css'
assert '.lightbox__replace' in css
print('OK')
" && server/.venv/bin/python3 companion/test_companion_app.py</automated>
  </verify>
  <done>panel-lookup.js has exactly one new optional lookup (after the mandatory guard, never in it) and exactly one new conditional `setAttribute("action", ...)` write; its existing banned-token harness still passes; style.css has zero occurrences of the retired class token and one new `.lightbox__replace` block using no new token.</done>
</task>

<task type="auto">
  <name>Task 3: Retarget the six existing Airlines replace checks onto the lightbox contract</name>
  <files>companion/test_status_pages.py</files>
  <action>
All six live in the block beginning at the `# quick task 260902-v26: the per-card "replace this image" control.` banner (around line 4972). Retarget the first three, fifth and sixth **in place** — same slot, same `EXPECTED_CHECK_COUNT` contribution, no check added or removed — following the convention already documented at line 3809 of this file. Extend the fourth in place. Then add one genuinely new check.

Update that section banner to say the control now lives in the lightbox (quick task 260903-btu), and give each retargeted check's `check()` description text a short "retargeted from the per-card disclosure" note so a future reader can see this coverage moved rather than appeared.

**1 — `_replace_form_action_matches_route_membership`.** The membership guarantee is unchanged but has moved from N form `action` attributes to N trigger attributes. Assert: `render(_ctx(tmp))` contains exactly one `<form class="lightbox__replace"` (use `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS`, not a duplicated literal); and `re.findall` over `data-view-panel-replace-action="([^"]+)"` returns exactly `len(illustrations.target_airline_names())` values, each starting with `airlines_page.ILLUSTRATION_ROUTE_PREFIX`, ending `.png`, and — with the prefix stripped — a member of `set(illustrations.target_filenames())`. Rename the function to match its new subject.

**2 — `_replace_form_declares_post_and_multipart_enctype`.** Now singular. Assert exactly one form tag matching the lightbox form class, and that it carries `method="post"`, `enctype="multipart/form-data"`, **and** a literally present `action=""`. Keep the existing failure message explaining that a missing enctype silently sends the file as a filename string; add one explaining that a missing (as opposed to empty) `action` attribute would leave panel-lookup.js writing an attribute that was never rendered.

**3 — `_replace_form_file_input_ids_are_unique_and_labelled`.** Now: exactly one `<input type="file" id="…">` in the whole rendered page, its id equal to `airlines_page.REPLACE_INPUT_ID`, and that id present in the set of `<label for="…">` targets. Keep the label-association guarantee — that is the accessibility contract, and it is the part that must not be lost in the move.

**4 — `_cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override`.** Keep everything it already asserts and **extend** it with the new invariant this task creates: with Air France's override file present, that card's `data-view-panel-replace-action` equals the **un-busted** `/illustration/{key}.png` while its `data-view-panel-src` and `<img src>` both equal the busted URL — and **no** `data-view-panel-replace-action` value anywhere on the page contains `?v=`. Extend the `check()` description accordingly. This is the single most valuable assertion in this task: the busted/un-busted split is deliberate and reads like a bug to anyone who has not read the reasoning.

**5 — `_replace_control_escapes_hostile_airline_name`.** Keep the monkeypatch-and-restore technique and the two raw-survival assertions verbatim. Replace the two now-deleted-template assertions: assert the escaped `airlines_page.REPLACE_LABEL_TEXT` appears in the rendered page, and assert the hostile name does not appear inside the rendered replace form's own markup at all (the form is now airline-agnostic — nothing interpolates a name into it). Additionally assert that the hostile card's `data-view-panel-replace-action` value contains no raw `<` or `"` — that attribute is the one genuinely new interpolation point this task creates.

**6 — `_replace_disclosure_contains_no_revert_or_reset_control`.** Rename away from "disclosure". Scope the revert-shaped-word scan (`revert`, `reset`, `restore`, `undo`, `original`) to the single lightbox form's own markup, sliced out by regex from the form's opening tag to its `</form>`, and keep the second half of the check as a membership test over the surviving copy constants — now `REPLACE_LABEL_TEXT` and `REPLACE_BUTTON_TEXT`, not the two deleted templates. Keep the existing comment explaining why this is deliberately scoped rather than a bare negative grep over the whole document (D-04).

**NEW check — the retired per-card control is gone from every surface.** One check asserting all three of: the retired class token appears nowhere in `airlines_page.render(_ctx(tmp))`'s output; it appears nowhere in `companion/static/style.css`'s source read from disk; and `airlines_page` exposes no `_replace_control_html`, no `REPLACE_SUMMARY_TEMPLATE` and no `REPLACE_LABEL_TEMPLATE` attribute. Build the searched token by concatenating two fragments at runtime rather than writing it as one literal, so this check's own source cannot satisfy a future whole-repo grep for the retired name. Describe it as pinning that this task left no dead markup, no dead stylesheet rule and no dead module surface behind. <!-- planner-discipline-allow: airline-card__replace -->

**Check count.** `EXPECTED_CHECK_COUNT` goes 123 → 124 (five retargeted in place and one extended in place all contribute zero; the removal check is the single addition). Append to the existing provenance comment on line 265 in its established style, naming this quick task and stating the +1 and that the six 260902-v26 checks were retargeted in place rather than replaced.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/ruff check companion/ && server/.venv/bin/python3 companion/test_status_pages.py</automated>
  </verify>
  <done>`server/.venv/bin/python3 companion/test_status_pages.py` exits 0 with 124/124; no check in the file still references the retired per-card class, `_replace_control_html`, `REPLACE_SUMMARY_TEMPLATE` or `REPLACE_LABEL_TEMPLATE`.</done>
</task>

<task type="auto">
  <name>Task 4: Prove History is unaffected — cross-page and script-source guards</name>
  <files>companion/test_view_pages.py, companion/test_companion_app.py</files>
  <action>
This is the non-regression half of the task, and the constraint that matters most: `panel-lookup.js` and the `.lightbox` block are shared by History and Airlines, so a mistake here silently breaks a page nobody was editing.

**4a. `companion/test_view_pages.py` — two new checks**, placed immediately after `_airlines_lightbox_constants_match_history` (around line 1415) so all the shared-lightbox contract checks stay in one block.

**New check A — History's rendered page carries zero replace-related markup.** This must actually exercise `history_page.render()`, not reason about it. Reuse the fixture shape `_lightbox_dom_contract_three_file_guard` already uses: `_mkstate`, `_seed_gallery` with at least one entry, `_seed_runway_events` with at least one row, then `history_page.render(_history_ctx(tmp, gallery_entries=names))` — the gallery entry is essential, because History only emits its dialog when at least one row carries a trigger, and a fixture with no entries would prove absence for the wrong reason. Assert the rendered History page: contains `id="{history_page.LIGHTBOX_DIALOG_ID}"` exactly once (the dialog really is there — this is what makes the absence assertions meaningful); contains zero occurrences of `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS`; zero of `airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR`; and zero occurrences each of `<form`, `<input type="file"` and `enctype` — the broad negative sweep that catches a replace form arriving under some other name. Reference the Airlines constants by attribute, never as duplicated literals, so a rename cannot leave this check passing vacuously. In the description, say plainly that this exercises a real `history_page.render()` call against a seeded fixture.

**New check B — the three-file contract for the two new names.** Mirroring `_lightbox_dom_contract_three_file_guard`'s style, read `companion/static/panel-lookup.js` from disk and render both pages. For each of `airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR` and `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS`, assert the token appears in the script source, appears in `airlines_page.render({})`'s output, and does **not** appear in the rendered History page. Also assert `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS` appears in `companion/static/style.css` — the fourth file in the chain, and the one whose drift would leave the form functional but unstyled. Note in a comment that these two constants deliberately have no `history_page` counterpart and must never be added to `_airlines_lightbox_constants_match_history`'s pairs tuple.

Leave `_lightbox_dom_contract_three_file_guard` and `_airlines_lightbox_constants_match_history` themselves **unmodified** — their existing six tokens and four constant pairs are all still true.

`EXPECTED_CHECK_COUNT` goes 45 → 47. Extend the provenance comment at line 69 in its established style, naming this quick task and the two checks.

**4b. `companion/test_companion_app.py` — one new check**, placed directly after `_panel_lookup_script_es5_safe_and_no_html_write` (around line 1723), keeping all the panel-lookup.js source-discipline guards together.

Assert, over the script source read from disk: the mandatory guard line appears exactly once; the optional replace-form variable name does **not** appear on that line; the optional lookup's first occurrence in the source comes **after** the mandatory guard's; the optional lookup appears exactly once; and the `setAttribute` write for the `action` attribute appears exactly once. Describe it as pinning the single line that keeps History's lightbox alive — moving the optional lookup into that guard's condition, or above it, would make the whole script no-op on any page that renders no replace form, which is every page except Airlines.

Do **not** modify `_panel_lookup_script_es5_safe_and_no_html_write` or its `banned` tuple — the new code introduces no banned token, and widening that tuple is out of scope.

`EXPECTED_CHECK_COUNT` goes 125 → 126. Extend the provenance comment at line 81 in its established style.

Same comment-text hazard applies while writing any of this: nothing you add to `companion/static/panel-lookup.js` may contain a banned token, and the checks you write here run against that file's whole source.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/ruff check companion/ && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_companion_app.py</automated>
  </verify>
  <done>`test_view_pages.py` exits 0 at 47/47 and `test_companion_app.py` exits 0 at 126/126; a seeded, fully-rendered History page is proven to carry zero replace markup, and panel-lookup.js's mandatory guard is proven to exclude the new optional lookup.</done>
</task>

<task type="auto">
  <name>Task 5: Live verification against a real running companion/app.py</name>
  <files>companion/test_status_pages.py</files>
  <action>
Render-level checks prove what `render()` returns; this task proves what a real HTTP client actually receives from a real subprocess.

**5a. Extend the existing live end-to-end check in place.** `_both_tabs_ok_end_to_end` (around line 5190, inside Section 3's `Harness` block) already starts a real `companion/app.py` subprocess, performs a real login, and fetches tab routes against a seeded database. Add `("/history", "History")` to its `(path, heading)` tuple, and add a per-path branch — mirroring the existing `/health` branch's structure and its "the automated half of verified against a real running service" comment convention:

- For `/airlines`: assert the retired per-card class token appears **zero** times in the real response body (build the token by concatenating fragments at runtime, as in Task 3); assert `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS` appears exactly once; assert `airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR` appears at least once and that no occurrence of its value carries `?v=`; assert `action=""` appears exactly once; assert `<input type="file"` appears exactly once. <!-- planner-discipline-allow: airline-card__replace -->
- For `/history`: assert zero occurrences of `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS`, zero of `airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR`, and zero of `enctype` and `<input type="file"` — the served-HTML twin of Task 4's render-level History guard.

This is an **in-place extension**: same slot, same `EXPECTED_CHECK_COUNT` contribution, **no check added or removed**. Do not change the count set in Task 3.

**5b. Run the server by hand and record the result.** Beyond the harness, start a real instance and look at the served bytes:

Start the service with `./scripts/run-local-verify.sh` (it sets `SKYPANE_COMPANION_PASSWORD` and a state dir for you), log in over HTTP, then fetch `/airlines` and `/history` with the session cookie. The `Harness` / `_login` helpers at lines 347-430 of `companion/test_status_pages.py` show the exact login POST and cookie handling this app needs — read them rather than guessing. Confirm by inspecting the served HTML:

1. `/airlines` contains **no** per-card replace control.
2. `/airlines` contains exactly one `<form class="lightbox__replace" … action="">`, inside the `<dialog>`.
3. Every `.airline-card__zoom` button carries `data-view-panel-replace-action` pointing at `/illustration/{key}.png` with no query string.
4. `GET /static/panel-lookup.js` returns 200 and its body contains both new literals.
5. `/history` contains its dialog and zero replace-related markup or attributes.

Then stop the server and remove the scratch directory.

**5c. State the limit explicitly in the SUMMARY.** Everything above is served-HTML and source level. Nothing in this repository can execute `panel-lookup.js`: this project is stdlib-only Python with no JavaScript test infrastructure, no bundler, and a standing no-build-step constraint, and no browser-automation tooling is configured for it (there is no `.mcp.json`, and adding a DOM-simulation dependency would violate the project's own discipline for a quick task). So the one behaviour that stays unproven by automation is **the click itself**: that clicking a card's zoom trigger causes the script to write that card's URL into the form's `action` before the dialog opens.

What the automated layer *does* pin is every input to that behaviour — the attribute is rendered on every trigger with the right value, the form and its `action` placeholder exist in the dialog, the lookup runs after the mandatory guard, the write exists exactly once, and the four files agree on both literals. The residual risk is confined to the runtime click, which Task 6 covers. Write this paragraph into the SUMMARY verbatim in substance; do not soften it into "verified in a real browser".
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 companion/test_status_pages.py && ./scripts/run-all-tests.sh</automated>
  </verify>
  <done>`test_status_pages.py` still exits 0 at 124/124 with the live check now also fetching `/history` and asserting the served `/airlines` and `/history` bodies; the manual real-server run is done and its five observations recorded in the SUMMARY alongside the explicit statement of what still needs a real browser.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 6: Developer confirms the per-click action rewrite in a real browser</name>
  <action>Stop and hand over to the developer. Do not self-approve. Step 4 below is the entire reason this checkpoint exists — it is the one behaviour no harness in this repo can reach (Task 5c). Report exactly which steps were and were not exercised, and do not substitute a source-level or served-HTML argument for step 4.</action>
  <what-built>The Airlines illustration-replace control moved out of the per-card `<details>` disclosure and into the shared click-to-enlarge lightbox. The disclosure is gone from every card. Each card's zoom trigger now carries the target upload URL, and `panel-lookup.js` writes it into the dialog's form `action` on click. History's lightbox is untouched.</what-built>
  <how-to-verify>
Only a real browser can confirm the click-time attribute write — see Task 5c for why no automated layer in this repo can. Please check these six things.

1. Start the real service: `./scripts/run-local-verify.sh`, then open `http://localhost:8080/airlines` (check the port the script actually reports) and sign in. Open **Airlines**.
2. Confirm **no** grid card shows a "Replace … illustration" disclosure under its thumbnail any more.
3. Click one card's illustration — pick an airline you can recognise, e.g. Air France. The lightbox should open showing the enlarged illustration, its caption, and — below a thin divider — a "Replace this illustration" label, a file picker, and an **Upload** button.
4. **The critical check.** With the dialog open, open your browser's devtools element inspector on that form and read its `action` attribute. It must be `/illustration/{key}.png` for **the card you clicked** — not empty, and not another airline's key. Then press Escape, click a *different* card, and re-read the attribute: it must now show the *second* card's key. This is the one behaviour no test in the repo can reach.
5. Actually upload a PNG through it. The browser should navigate away, the page reload, a success banner appear, and the grid show the new image immediately (not the old one).
6. Open **History**, click any row's "View panel near this time" button. Its lightbox must still open, show the panel image and its caption, and close on both the Close button and Escape — and it must show **no** upload form.

If step 4 shows an empty or stale `action`, the script's per-click write is not reaching the form; report what you saw and which card you clicked.
  </how-to-verify>
  <resume-signal>Type "approved", or describe which step failed and what you observed.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → companion HTTP service | `POST /illustration/{key}.png` carries an attacker-shaped multipart body; session-gated by `require_session()` before any parsing |
| server-rendered HTML → panel-lookup.js | the script reads attributes off rendered DOM and writes one back into a form's submit target |
| curated airline list → rendered attribute values | `illustrations.target_variants_by_airline()` values reach a new HTML attribute |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-btu-01 | Tampering | `data-view-panel-replace-action` on `.airline-card__zoom` | medium | mitigate | Value is `"%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(normalise_airline_key(name)))` — already escaped once at construction and never re-escaped (Task 1e note on double-encoding). Pinned by the retargeted hostile-name check in Task 3, which additionally asserts the attribute value carries no raw `<` or `"`. |
| T-btu-02 | Tampering | `panel-lookup.js`'s new `setAttribute("action", ...)` write | medium | mitigate | The written value originates only from a same-page, server-rendered attribute — never from the URL, `location`, storage or user input. `setAttribute` writes a literal attribute, not markup; the file's no-raw-markup-sink posture is unchanged and its banned-token harness still passes (Task 2 verify). |
| T-btu-03 | Elevation of Privilege | `action=""` placeholder with JS unavailable | low | accept | Submits to `/airlines`, which `companion/app.py`'s POST dispatch does not route and 404s (verified). No write to a wrong key, no unauthenticated path, no data loss. Documented in `_lightbox_replace_form_html()`'s docstring rather than engineered around. |
| T-btu-04 | Denial of Service | oversized upload through the relocated form | medium | transfer | Unchanged from quick task 260902-v26 — the request size cap, PNG-header parse and landscape/transparency validation all live in `Handler._handle_illustration_replace()`, which this plan does not touch. Relocating the form changes no server-side control. |
| T-btu-05 | Information Disclosure | History gaining an upload affordance by shared-component drift | high | mitigate | Task 4's render-level and Task 5's served-HTML guards both assert zero `<form` / `<input type="file"` / `enctype` / replace-class / replace-attribute occurrences on a fully-seeded History page. |

No package-manager install of any kind occurs in this plan, so no supply-chain (`-SC`) row applies and no legitimacy checkpoint is required.
</threat_model>

<verification>
All commands run from the repo root, using this project's own interpreter (`server/.venv/bin/python3`), never a bare `python3`.

1. `server/.venv/bin/python3 companion/test_status_pages.py` → 0, 124/124.
2. `server/.venv/bin/python3 companion/test_view_pages.py` → 0, 47/47.
3. `server/.venv/bin/python3 companion/test_companion_app.py` → 0, 126/126.
4. `server/.venv/bin/ruff check companion/` → clean.
5. `./scripts/run-all-tests.sh` → all harnesses pass, coverage threshold met (the shared `layout.py` / `style.css` / `panel-lookup.js` surface means the config-page and contrast harnesses are also in scope for collateral damage).
6. Zero occurrences of the retired per-card class token in `companion/static/style.css`, in `airlines_page.render()`'s output, and in a real `GET /airlines` response body.
7. Zero replace-related markup or attributes in a real `GET /history` response body and in a seeded `history_page.render()` output.
8. `git grep` for `_replace_control_html`, `REPLACE_SUMMARY_TEMPLATE` and `REPLACE_LABEL_TEMPLATE` outside `.planning/` returns nothing.
9. Task 6's human browser pass approved — specifically its step 4, the per-click `action` rewrite, which no automated layer in this repo can reach.
</verification>

<success_criteria>
- The Airlines grid shows no per-card replace disclosure; the replace form exists exactly once per page, inside the lightbox.
- Opening a card's lightbox and inspecting its form shows `action="/illustration/{that card's key}.png"`, with no cache-busting query string, and it changes when a different card is opened.
- Uploading through the relocated form still performs a real native multipart POST, redirects with a flash, and shows the new image immediately.
- History's lightbox opens, swaps, and closes exactly as before, and its page carries zero replace-related markup or attributes.
- `panel-lookup.js` grew exactly one optional lookup and one conditional attribute write; its mandatory guard, ES5-safe dialect, banned-token cleanliness, no-network/no-timer/no-persistent-state posture and never-decide-from-viewport-or-orientation constraint all survive unchanged.
- No test anywhere still asserts the retired per-card shape; every one of the six 260902-v26 checks was retargeted or extended in place, and all three `EXPECTED_CHECK_COUNT` values carry a provenance comment naming this quick task.
- `bash scripts/run-all-tests.sh` passes.
</success_criteria>

<output>
Create `.planning/quick/260903-btu-move-the-airlines-illustration-replace-c/260903-btu-SUMMARY.md` when done, including Task 5c's explicit statement of what remains unproven by automation and Task 6's human verification result.
</output>
