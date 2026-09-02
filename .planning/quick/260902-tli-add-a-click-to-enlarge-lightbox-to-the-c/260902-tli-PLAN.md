---
phase: quick-260902-tli
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/pages/airlines_page.py
  - companion/static/style.css
  - companion/static/panel-lookup.js
  - companion/layout.py
  - companion/test_status_pages.py
  - companion/test_view_pages.py
  - companion/test_companion_app.py
autonomous: false
requirements: [REQ-260902-tli-WEB]
must_haves:
  truths:
    - "Clicking an airline card's illustration on a desktop-width viewport opens a lightbox showing that airline's illustration enlarged, with its name as the caption."
    - "On a narrow portrait viewport, clicking/tapping the illustration does nothing at all — no dialog opens, and the tap does not land on a dead interactive target either."
    - "On a phone-sized landscape viewport, clicking the illustration opens the same lightbox."
    - "The Airlines lightbox is driven by the already-shipped companion/static/panel-lookup.js with no behavioural change to that script — the codebase still contains exactly one lightbox mechanism."
    - "The orientation/viewport gate lives entirely in companion/static/style.css; no JavaScript anywhere inspects viewport size or device orientation to decide whether the lightbox opens."
  artifacts:
    - companion/pages/airlines_page.py
    - companion/static/style.css
  key_links:
    - ".airline-card__zoom[data-view-panel-src] -> panel-lookup.js document-level click delegation -> #panel-lookup-dialog"
    - "airlines_page.LIGHTBOX_DIALOG_ID == history_page.LIGHTBOX_DIALOG_ID == panel-lookup.js's getElementById literal"
    - ".lightbox--wide's max-width == illustration_normalize.ILLUSTRATION_TARGET_WIDTH (the served illustrations' own native width — never upscaled past it)"
---

<objective>
Make an Airlines gallery card's illustration click-to-enlarge, by reusing History's already-shipped `<dialog>` lightbox rather than inventing a second one — and gate the trigger off on narrow portrait viewports purely in CSS.

Today `companion/pages/airlines_page.py` renders each illustration as a plain, inert `<img class="airline-card__image">` inside a `.airline-card`. Since quick task 260902-req-02 every one of those images is served through `companion/illustration_normalize.py` at exactly `ILLUSTRATION_TARGET_WIDTH x ILLUSTRATION_TARGET_HEIGHT` (900x263), so the enlarged view has a known, uniform shape to render into — and the card `<img>` already carries that exact `width`/`height`, meaning the enlarged view reuses a byte-identical, already-cached URL and opens with no second network fetch.

The mechanism already exists and is shipped: `companion/static/panel-lookup.js` is emitted on **every** authenticated page (`companion/layout.py` `page_shell()`, sixth script tag), guards on `document.getElementById("panel-lookup-dialog")`, and opens on a **document-level** click whose target has any ancestor carrying `data-view-panel-src`. So a page that emits the same dialog element and puts those two data attributes on a trigger gets the whole interaction with **zero JavaScript logic change**. That is the design this plan implements.

Purpose: the developer's own report — "I expected clicking to show the plane enlarged on desktop, and also on phone but only in landscape mode." A 900x263 silhouette in a ~200px-wide grid card is too small to actually look at; in a narrow portrait viewport an enlarged one is no better, which is why portrait is deliberately excluded rather than accidentally unsupported.
Output: a zoom trigger per card, one shared wide-variant dialog per page, and a single CSS media block that turns the pointer path off on narrow portrait viewports.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@companion/pages/airlines_page.py
@companion/static/panel-lookup.js

Read before starting (all verified live during planning — the line numbers are current):

- `companion/pages/history_page.py` lines 290-308 (`VIEW_PANEL_LABEL`, `LIGHTBOX_DIALOG_ID`, `LIGHTBOX_CAPTION_TEMPLATE`, `LIGHTBOX_NOTE`, the three `_VIEW_PANEL_*_ATTR` constants and the "duplicated, not imported" rationale), lines 418-464 (`_view_panel_button_html()` and `_lightbox_html()`), and lines 855-895 (how `render()` emits the dialog exactly once per page, and only when at least one trigger exists). **This is the pattern to mirror.**
- `companion/pages/__init__.py` — the page-module contract. Note the boundary History's own line 312 comment states: one page module may not import another. That is why the constants below are duplicated into `airlines_page.py` and pinned by a cross-module test, exactly as `ILLUSTRATION_ROUTE_PREFIX` and `UNRESOLVED_LINK_HREF` already are.
- `companion/static/style.css` lines 2878-2948 (the Airlines gallery section, ending at `.airline-card__chip`), lines 3324-3365 (the `.lightbox` section), line 1244-1269 (`button`), 1309-1311 (`button:active`), 1425-1428 (`button:hover`), 438-444 (the global `:focus-visible` floor), and 3130 (`@media (min-width: 960px)` — the file's **only** width breakpoint).
- `companion/layout.py` lines 946-957 — the six unconditional script tags, including the now-stale comment "only History renders #panel-lookup-dialog".
- `companion/test_view_pages.py` lines 1330-1373 — `_lightbox_dom_contract_three_file_guard()`, the existing three-file DOM-contract guard this plan extends.
- `companion/test_status_pages.py` lines 4361-4530 — "Section 2: companion/pages/airlines_page.py", where this plan's Airlines-side checks belong. Note `_every_card_image_source_passes_route_membership_test()` uses a bare `re.findall(r'src="([^"]+)"', rendered)`, which will now also match inside `data-view-panel-src="..."` (harmless — the value passes the same membership test) and will **not** match the dialog's `src=""` (the pattern requires at least one character). Do not "fix" that test; confirm it still passes unchanged.
- `companion/test_companion_app.py` lines 1533-1560 — the panel-lookup.js banned-token / ES5-dialect guard.

Project skill: `Skill("sketch-findings-skypane")` — the companion design system. Relevant here: `.lightbox` is one of the two deliberate floating-overlay exceptions that keep a resting shadow and use `--radius-card`; card-set components use `--radius-control`; the global `:focus-visible` outline is an accessibility floor that is never removed without a replacement.

Harness style: stdlib-only scripts, run as `server/.venv/bin/python3 companion/test_status_pages.py`, exiting 0/1, each assertion registered through the file's own `check(description, fn)` helper. Every test file carries a running check-count comment block near the top (`test_status_pages.py` ~line 66, `test_view_pages.py` ~line 92, `test_companion_app.py` ~line 94) — **append a new line to it** describing this task's additions, following the existing "N + M (task: what was added)" convention. Full suite: `./scripts/run-all-tests.sh`.
</context>

<design_decisions>
Resolved during planning from the real code, so the executor does not re-litigate them:

1. **Airlines shares History's dialog id and attribute contract, and gets no JS change.** `panel-lookup.js` keys on `getElementById("panel-lookup-dialog")` and a document-wide `data-view-panel-src` ancestor walk. Two pages never render simultaneously, so reusing the id creates no duplicate-id condition. The three `lightbox__image` / `lightbox__caption` / `lightbox__note` elements are all mandatory: the script early-returns if any is missing, so Airlines' dialog must carry all three.

2. **The trigger is a real `<button>` wrapping the `<img>`, not the `<img>` itself.** History's trigger is a `<button>`; the codebase's a11y discipline (global `:focus-visible` floor, aria-labelled icon buttons) makes a non-focusable click target the wrong choice. The click delegation walks ancestors from `evt.target`, so a click on the inner image resolves to the button.

3. **The gate is `@media (max-width: 959px) and (orientation: portrait)` setting `pointer-events: none` on the trigger.** Enabled is the default (desktop needs no query, and a browser that does not understand the query degrades to "lightbox works", the benign direction). `959px` is the exact complement of the file's single existing `min-width: 960px` breakpoint — no new magic number is introduced. Both clauses earn their place: the width clause is what keeps "desktop always works" true, the orientation clause is what keeps a small landscape window working. A portrait tablet also falls in the disabled set; that is accepted, it is the same narrow-tall-viewport case, just less extreme.

4. **`pointer-events: none` gates the pointer path only.** CSS cannot remove a tab stop, and this plan adds no JS gate, so a deliberate keyboard activation still opens the dialog in portrait. That is a documented, accepted residue — not a dead click target (there is nothing to tap that swallows a tap), and not a bug: it takes an explicit intentional action on hardware phones essentially never have.

5. **The enlarged view is the same normalized 900x263 image, in a `.lightbox--wide` variant.** `.lightbox`'s stock `max-width: 480px` would render the illustration at 480x140 — barely bigger than the grid card and not worth a modal. The wide variant caps at the illustration's own native width (900px, never upscaled past it) and caps the image at `60vh` so a landscape phone does not have to scroll the dialog.

6. **Caption reuses `CARD_IMAGE_ALT_TEMPLATE`.** `panel-lookup.js` writes the caption attribute into both `caption.textContent` and `image.alt`, so the attribute value must already read correctly as an image alt: `"Air France illustration"` does; a bare airline name does not.
</design_decisions>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Give each Airlines card a zoom trigger and a wide shared dialog, gated in CSS</name>
  <files>companion/pages/airlines_page.py, companion/static/style.css, companion/test_status_pages.py</files>
  <behavior>
    - Every rendered `.airline-card` wraps its `.airline-card__image` in exactly one `.airline-card__zoom` button.
    - That button's `data-view-panel-src` is byte-identical to the image's own `src` (same route prefix, same key, same `.png`).
    - That button's `data-view-panel-caption` equals `CARD_IMAGE_ALT_TEMPLATE % airline_name`, escaped once.
    - That button's `aria-label` equals `ZOOM_LABEL_TEMPLATE % airline_name`, escaped once.
    - The page emits `id="panel-lookup-dialog"` exactly once, carrying the `lightbox` and `lightbox--wide` classes plus all three `lightbox__image` / `lightbox__caption` / `lightbox__note` elements and the close-attribute button.
    - A card whose normalised key is falsy still renders nothing at all (the existing skip discipline is unchanged).
    - style.css declares `.airline-card__zoom` with the base-button neutralizers and `cursor: zoom-in`, declares `.lightbox--wide` with a `max-width` equal to `ILLUSTRATION_TARGET_WIDTH`, and disables the trigger's pointer path inside one `@media (max-width: 959px) and (orientation: portrait)` block — and nowhere else.
  </behavior>
  <action>
In `companion/pages/airlines_page.py`, add module constants immediately below `CARD_IMAGE_ALT_TEMPLATE`, carrying a comment in this module's established voice explaining that they are duplicated from `companion/pages/history_page.py` and from `companion/static/panel-lookup.js` rather than imported — a page module has no import path to a sibling page module (the `companion/pages/__init__.py` boundary) and none at all to a static script — and that a cross-module equality guard in `companion/test_view_pages.py` pins them: `LIGHTBOX_DIALOG_ID` set to the same value History uses; `_VIEW_PANEL_SRC_ATTR`, `_VIEW_PANEL_CAPTION_ATTR`, `_VIEW_PANEL_CLOSE_ATTR` set to the same three attribute names History uses; `ZOOM_LABEL_TEMPLATE = "Enlarge %s illustration"`; and `LIGHTBOX_NOTE_TEMPLATE`, a one-sentence note formatted with the already-imported `ILLUSTRATION_TARGET_WIDTH`/`ILLUSTRATION_TARGET_HEIGHT` (never hand-typed digits) saying the view is shown at the shared frame size every illustration is normalized to, and that it is the same source art the panel itself draws.

In `_airline_card_html()`, build the image URL once into a local variable and interpolate that one variable into both the `<img src>` and the trigger's source attribute, so the two can never drift. Wrap the existing `<img class="airline-card__image" ...>` — unchanged, including its `width`/`height`/`loading`/`decoding`/`alt` — in `<button type="button" class="airline-card__zoom" {src attr}="..." {caption attr}="..." aria-label="...">`. Keep the single-escape-at-point-of-interpolation discipline (T-06.6.4.1-05) for the caption and the aria-label. The `aria-label` is deliberate: it overrides the inner image's alt for the button's accessible name, so a screen reader announces the action, not just the picture.

Add `_lightbox_html()` mirroring History's `_lightbox_html()` element-for-element and class-for-class — same order, same three `lightbox__*` elements, same close-attribute button — with exactly two differences: the dialog carries `class="lightbox lightbox--wide"`, and the note is this module's own formatted `LIGHTBOX_NOTE_TEMPLATE`. Its docstring must state that `panel-lookup.js` writes the image src/alt and the caption text on click and that this function only emits the static note.

In `render()`, append the dialog after the grid, emitted once per page and only when `pairs` is non-empty — the same "no chrome with no data" rule the filter bar already follows.

In `companion/static/style.css`, in the Airlines gallery section directly after `.airline-card__image` (before `.airline-card__name`), add `.airline-card__zoom` as a block-level, full-width, `height: auto`, zero-padding, borderless, background-less button with `border-radius: var(--radius-control)` and `cursor: zoom-in`. Add a `.airline-card__zoom:hover` rule neutralizing the background and border-color, and a `.airline-card__zoom:active` rule setting `transform: none`. Both are load-bearing, not redundant: the base `button:hover` and `button:active` rules are `(0,1,1)` and would out-specify a bare `(0,1,0)` class rule; these two are equal specificity and later in source order, so they win. Comment that reasoning inline, and comment why the press-depress is neutralized (a full-width image nudging 1px against the card's own border reads as a layout glitch, not a button press). Do not touch the global `:focus-visible` outline — this control keeps it.

Immediately after those rules, add the gate: one `@media (max-width: 959px) and (orientation: portrait)` block whose only rule sets `pointer-events: none` on `.airline-card__zoom`. Comment it as the file's first `max-width` query and an intentional exception to the file's mobile-first idiom — it is a disable-override, so enabled must remain the default a non-supporting browser falls back to. Record in that comment: that `959px` is the exact complement of the file's existing `min-width: 960px` breakpoint and is not a new breakpoint; why each clause is present (width keeps desktop always-on, orientation keeps a small landscape window working); that a portrait tablet is deliberately in the disabled set; and that this disables the pointer path only, since a stylesheet cannot remove a tab stop and no script-side gate exists by design.

In the `.lightbox` section, after `.lightbox::backdrop`, add `.lightbox--wide` with `max-width: 900px` (equal specificity to `.lightbox`, so it must come later in source order — say so in the comment, and note that 900 is `illustration_normalize.ILLUSTRATION_TARGET_WIDTH`, pinned by a harness check, so the illustration is never upscaled past its own native width), plus `.lightbox--wide .lightbox__image` setting `width: auto`, `max-width: 100%`, `max-height: 60vh` and auto left/right margins. Comment why `width: auto` rather than inheriting the base rule's `width: 100%`: a `max-height` cap combined with `width: 100%` and `height: auto` would squash the aspect ratio, and 60vh is what keeps the whole dialog on screen on a landscape phone.

Add four checks to `companion/test_status_pages.py`'s Section 2, each registered through `check()`:
(1) every card wraps its image in exactly one `.airline-card__zoom` button whose source attribute is byte-identical to that same card's `<img src>`, whose caption attribute equals `CARD_IMAGE_ALT_TEMPLATE % name` and whose aria-label equals `ZOOM_LABEL_TEMPLATE % name` — assert per-card using the existing `_card_slice()` helper, on at least the same two airlines the neighbouring chip checks already use;
(2) the dialog appears exactly once in the rendered page, carries both the base and wide classes and all three `lightbox__*` elements plus the close attribute, and its note contains the real `ILLUSTRATION_TARGET_WIDTH`/`HEIGHT` values read from `illustration_normalize` (never re-typed);
(3) a style.css guard that strips `/* ... */` comment spans with a non-greedy regex **before** matching (this file is comment-heavy; matching raw text would read prose as declarations), then asserts `.airline-card__zoom` neutralizes the base button rule's height/padding/border/background and declares the zoom cursor, and that the trigger's pointer-events declaration appears exactly once in the whole comment-stripped stylesheet and falls inside the `@media (max-width: 959px) and (orientation: portrait)` block — the desktop path must be impossible to disable by accident;
(4) a cross-file pin that `.lightbox--wide`'s max-width equals `illustration_normalize.ILLUSTRATION_TARGET_WIDTH`, so a future change to the normalized frame size cannot silently leave the dialog capped at a stale width.
Append a line to the file's running check-count comment describing these four.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/ruff check companion/</automated>
  </verify>
  <done>test_status_pages.py passes with four more checks than before; ruff is clean; `_every_card_image_source_passes_route_membership_test` and `_every_card_image_carries_matching_intrinsic_dimensions` still pass unmodified.</done>
</task>

<task type="auto">
  <name>Task 2: Pin the two-page lightbox contract, correct the now-stale "History only" comments, and verify against a real running instance</name>
  <files>companion/static/panel-lookup.js, companion/layout.py, companion/test_view_pages.py, companion/test_companion_app.py</files>
  <action>
`companion/static/panel-lookup.js` gets **comment changes only** — no logic change of any kind, which is the whole point of the design. Update the header block's claim that only History carries the dialog element: both History and the Airlines gallery now do, and the guard clause is what lets one cached script serve every page. Add to the file's standing-constraints paragraph that this script must never decide, from viewport dimensions or from device orientation, whether to open — that gate belongs in the stylesheet, on the Airlines trigger's own rule — and that the harness pins this.

**Do not write the API names `matchMedia` or `innerWidth` into panel-lookup.js**, not even inside that comment: the harness check below greps the file's whole source for them, so naming them in prose would trip the very guard being added. Describe the constraint by concept, as above.
<!-- planner-discipline-allow: matchMedia -->
<!-- planner-discipline-allow: innerWidth -->

In `companion/test_companion_app.py`, extend the existing panel-lookup.js banned-token tuple (~line 1541) with `matchMedia` and `innerWidth`, and extend that check's registered description to say it also pins the CSS-only gate. This is a pre-existing check retargeted in place — not a new check, no count change; note that in the count comment.

In `companion/layout.py`, correct the line 955-956 comment: the sixth script serves every page and both History and Airlines render the dialog element.

In `companion/test_view_pages.py`, import `airlines_page` alongside `history_page` and extend `_lightbox_dom_contract_three_file_guard()` in place so the same six tokens are asserted present in `panel-lookup.js`, in the rendered History page **and** in the rendered Airlines page (`airlines_page.render()` reads nothing from `ctx` — pass a plain dict). Update its registered description to match its widened scope; it stays one check, retargeted, not a new one. Then add exactly one new check asserting the four cross-module constant equalities — dialog id and the three attribute names — between `airlines_page` and `history_page`, with a message naming both sides on failure, mirroring the existing `ILLUSTRATION_ROUTE_PREFIX` equality guard's shape. Append a line to this file's running check-count comment.

Then verify against a real running service, the way quick task 260902-req-02 did (throwaway script under the session scratchpad — **not** committed): start `companion/app.py` on an unused port against a temp state dir with `SKYPANE_COMPANION_PASSWORD` set, authenticate to get a session cookie, then assert on the *served* bytes (not on `render()` output): `GET /airlines` returns HTML containing exactly one `id="panel-lookup-dialog"`, one `.airline-card__zoom` button per card, and `lightbox--wide`; `GET /static/style.css` returns a stylesheet containing the `.airline-card__zoom` rule and the `@media (max-width: 959px) and (orientation: portrait)` gate; `GET /static/panel-lookup.js` returns 200. Record the exact commands and results in the summary — this is the evidence that the wiring survives the real route, not just the renderer.

Finish with the full suite. It is expected green immediately before this task starts; the bar is zero new failures.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_companion_app.py && ./scripts/run-all-tests.sh</automated>
  </verify>
  <done>Both harnesses pass; `./scripts/run-all-tests.sh` reports `Result: PASS` with zero new failures; the live-instance checks above all pass and their commands/outputs are captured in the summary; `git diff companion/static/panel-lookup.js` shows comment lines only.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Developer verifies the three viewport states in a real browser and on a real phone</name>
  <action>Stop and hand over to the developer. Do not self-approve, and do not substitute DevTools device emulation for the real-phone pass on steps 2 and 3 — report exactly which steps were and were not exercised.</action>
  <what-built>Airline illustrations are now click-to-enlarge: each card's image is wrapped in a zoom button that opens the same native `<dialog>` lightbox History already uses, in a wider 900px variant, and one CSS media block turns the pointer path off on narrow portrait viewports.</what-built>
  <how-to-verify>
    Start the real service: `./scripts/run-local-verify.sh`, then open `http://localhost:8080/airlines` (check the port the script actually reports) and sign in.

    1. **Desktop (full-width window):** hover an aircraft — the cursor should become a zoom cursor. Click it. A dialog should open showing that aircraft substantially larger than the card, with the airline's name in the caption ("Air France illustration"), a one-line note, and a Close button. Confirm the enlarged image is not stretched or cropped. Press Escape — it should close (that is the native dialog's own behaviour; no custom key handler exists). Click a second airline — the new dialog should show *that* aircraft, not the previous one.
    2. **Phone portrait:** narrow the window to a phone-portrait shape (~390 x 844 — DevTools device toolbar, or a real phone held upright on the same network). Click/tap an aircraft. **Nothing should happen** — no dialog, no flash, no visible press feedback. Confirm it is genuinely inert rather than a dead button: nothing highlights, and tapping the airline's name below it is equally inert (it never was a target).
    3. **Phone landscape:** rotate the phone, or resize to ~844 x 390. Click/tap the same aircraft. The dialog should open, and the whole dialog — image, caption, note, Close — should fit on screen without the page behind it jumping.
    4. **Both other lightbox users still work:** open History and click a row's "View panel near this time" button — the panel lightbox must behave exactly as before (this plan shares its script and its dialog id, so a regression there is the main risk worth a look).

    A real phone check for steps 2 and 3 is worth more than DevTools emulation here: the gate keys on the device's reported orientation, and past work on this project has had computed-style checks pass while the real device behaved differently.
  </how-to-verify>
  <resume-signal>Type "approved", or describe which of the four steps behaved differently from the above.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| server-rendered HTML → browser DOM | Airline names and image keys are interpolated into new attribute positions (`data-view-panel-caption`, `aria-label`, `data-view-panel-src`) |
| static script → dialog DOM | `panel-lookup.js` copies attribute values off a clicked trigger into the dialog's image src/alt and caption text |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-tli-01 | Tampering | `_airline_card_html()` new attributes | low | mitigate | Every interpolated value passes `escape_html()` exactly once at the point of interpolation, matching the module's existing discipline; the source is `_ILLUSTRATION_TARGETS`, a static curated in-repo list, not request input |
| T-tli-02 | Information disclosure | trigger `data-view-panel-src` | low | accept | The attribute value is the identical, already-public `/illustration/{key}.png` URL the same card's `<img src>` already exposes, still behind the same session-gated route — no new surface |
| T-tli-03 | Tampering | `panel-lookup.js` DOM writes | low | accept | Unchanged behaviour: the script writes only via `src`/`alt`/`textContent`, never a raw-markup sink, and this plan changes no logic in it (`git diff` shows comments only) |
| T-tli-SC | Tampering | package installs | low | accept | No package manager runs; no dependency is added or upgraded by this plan |
</threat_model>

<verification>
- `server/.venv/bin/python3 companion/test_status_pages.py` — passes, four new checks.
- `server/.venv/bin/python3 companion/test_view_pages.py` — passes, one new check plus the widened two-page DOM-contract guard.
- `server/.venv/bin/python3 companion/test_companion_app.py` — passes with the extended banned-token guard.
- `server/.venv/bin/ruff check companion/` — clean.
- `./scripts/run-all-tests.sh` — `Result: PASS`, zero new failures against the green baseline this task starts from.
- Live running-instance HTTP checks (Task 2) — served `/airlines`, `/static/style.css`, `/static/panel-lookup.js` all carry the new contract.
- Blocking human verification (Task 3) — the three-viewport interaction check plus a History non-regression pass.
</verification>

<success_criteria>
- Clicking an airline illustration opens an enlarged view of that illustration on desktop, and on a phone in landscape.
- Clicking it on a phone in portrait does nothing, with no dead interactive target left behind.
- No second lightbox mechanism exists: one dialog id, one script, one set of attribute names, pinned across `airlines_page.py`, `history_page.py`, `panel-lookup.js` and the rendered markup of both pages by harness checks.
- The gate is expressed in one CSS media block and nowhere in JavaScript.
- History's own panel lightbox is unchanged and still works.
</success_criteria>

<source_audit>
| Source | Item | Covered by |
|--------|------|-----------|
| SPEC | Clicking a card's illustration opens a large view of it | Task 1 (trigger + wide dialog) |
| SPEC | Desktop: always works | Task 1 decision 3 (default-enabled; gate is a narrow-portrait override only) |
| SPEC | Mobile portrait: click must NOT open it, no dead click target | Task 1 gate + Task 3 step 2 |
| SPEC | Mobile landscape: works | Task 1 gate's orientation clause + Task 3 step 3 |
| SPEC | Gate in CSS, not JS | Task 1 media block + Task 2 banned-token pin |
| SPEC | Reuse History's `<dialog>` pattern, don't invent a second | Task 1 mirrors `_lightbox_html()`; Task 2 pins the shared contract across both pages |
| SPEC | Build on 260902-req-02's normalized 900x263 frame | Task 1 reuses `ILLUSTRATION_TARGET_WIDTH/HEIGHT` for the note, the dialog cap and the pin |
| CONSTRAINT | Live check against a real running `companion/app.py` | Task 2 (served-bytes checks) + Task 3 (interaction checks) |
| CONSTRAINT | End with `scripts/run-all-tests.sh`, zero new failures | Task 2 verify |
| CONSTRAINT | Single plan, 1-3 focused tasks | 3 tasks (2 auto + 1 checkpoint) |

No unplanned items.
</source_audit>

<output>
Create `.planning/quick/260902-tli-add-a-click-to-enlarge-lightbox-to-the-c/260902-tli-SUMMARY.md` when done.
</output>
