---
phase: quick-260903-btu
plan: 01
status: complete
---

# Quick Task 260903-btu: Move the Airlines illustration-replace control into the lightbox

## What was built

The Airlines gallery's illustration-replace control moved out of the per-card `<details>` disclosure (quick task 260902-v26) and into the shared click-to-enlarge lightbox (quick task 260902-tli), at the developer's explicit request ("je m'attendais à ce que la proposition de remplacement soit disponible une fois qu'on a zoomé sur la photo"). One replace form now exists per page instead of 27, reached only when the user has deliberately opened a closer look. History's own lightbox is provably untouched.

**Task 1** (`companion/pages/airlines_page.py`, commit `97c6dc1`):
- `_replace_control_html()` deleted outright, replaced by `_lightbox_replace_form_html()` (no arguments, called once from `_lightbox_html()`).
- Two new constants: `_VIEW_PANEL_REPLACE_ACTION_ATTR = "data-view-panel-replace-action"` and `LIGHTBOX_REPLACE_FORM_CLASS = "lightbox__replace"` — Airlines-only, no `history_page` counterpart, documented as never to be added to `test_view_pages.py`'s cross-module constant-equality check.
- `REPLACE_SUMMARY_TEMPLATE`/`REPLACE_LABEL_TEMPLATE` (both `%s`-airline-name templates) deleted — unfillable now that the form is emitted once per page, not once per card. Replaced by airline-agnostic `REPLACE_LABEL_TEXT = "Replace this illustration"` and a single static `REPLACE_INPUT_ID = "airline-replace-input"`. `REPLACE_BUTTON_TEXT = "Upload"` carries over byte-identical.
- Every card's zoom trigger gained `data-view-panel-replace-action="{un-busted image_url}"`, alongside the existing `data-view-panel-src`/`-caption` — deliberately un-busted, matching the existing "a query string on a POST target is pointless" reasoning.
- `_lightbox_html()` gained the replace form between `.lightbox__note` and the Close button, with a literal `action=""` placeholder.

**Task 2** (`companion/static/panel-lookup.js`, `companion/static/style.css`, commit `7419f94`):
- panel-lookup.js: exactly one new optional lookup (`var replaceForm = dialog.querySelector(".lightbox__replace");`), placed after the mandatory three-element guard, never inside it — the single line that keeps History's lightbox alive. Exactly one new conditional write, `replaceForm.setAttribute("action", trigger.getAttribute("data-view-panel-replace-action") || "")`, added before `dialog.showModal()`. `setAttribute` used deliberately over the `form.action` property (which resolves to an absolute URL and is shadowable by a same-named form control). Nothing else in the file changed.
- style.css: the six retired `.airline-card__replace*` rules deleted with no tombstone comment; a new `.lightbox__replace` block added after `.lightbox--wide .lightbox__image`, carrying forward the retired disclosure's own sub-scale label tier (13px, 70%-muted color-mix) and `min-width: 0`/`max-width: 100%` load-bearing pair — no new size, no new colour token, no accent-reservation-list edit (`button[type="submit"]` was already an enumerated member).

**Task 3** (`companion/test_status_pages.py`, commit `62a299a`):
- The six 260902-v26 replace-form checks retargeted or extended in place onto the lightbox contract (membership, method/enctype/present-action, unique labelled file-input id, cache-buster absent/present-and-mtime-keyed with the new un-busted-replace-action invariant, hostile-name escaping, no-revert-control) — zero count change across all six.
- One new check added: the retired per-card control is gone from `render()`'s output, from `style.css` read from disk, and from `airlines_page`'s own attribute surface.
- `EXPECTED_CHECK_COUNT` 123 → 124.

**Task 4** (`companion/test_view_pages.py`, `companion/test_companion_app.py`, commit `31cc287`):
- `test_view_pages.py`: two new checks — a real, seeded `history_page.render()` call proves the dialog renders exactly once and carries zero occurrences of the replace-form class, replace-action attribute, `<form`, file input, or `enctype`; and a three-file (panel-lookup.js/airlines_page/style.css) plus History-absence contract for the two new Airlines-only constants. `EXPECTED_CHECK_COUNT` 45 → 47.
- `test_companion_app.py`: one new check pinning that the optional replace-form lookup stays strictly after the mandatory guard and never appears on the guard's own line. `EXPECTED_CHECK_COUNT` 125 → 126. The existing banned-token harness left unmodified.

**Task 5** (`companion/test_status_pages.py`, commit `4aeaf64`, plus a manual live-server pass):
- `_both_tabs_ok_end_to_end()` extended in place to also fetch `/history`, with per-path branches: `/airlines`'s real response body asserted to carry zero retired-per-card markup, exactly one `lightbox__replace` form, at least one un-busted `data-view-panel-replace-action`, exactly one `action=""` and one file input; `/history`'s real response body asserted to carry zero occurrences of the replace-form class, replace-action attribute, `enctype`, or file input. In-place extension, no `EXPECTED_CHECK_COUNT` change.
- Manual pass against a real running `companion/app.py` (`./scripts/run-local-verify.sh`, real login, real HTTP fetches, then stopped and the scratch state directory removed): all five plan-specified observations confirmed —
  1. `/airlines` contains zero occurrences of the retired per-card class token.
  2. `/airlines` contains exactly one `<form class="lightbox__replace" method="post" enctype="multipart/form-data" action="">`, inside the dialog.
  3. All 27 `.airline-card__zoom` buttons carry `data-view-panel-replace-action="/illustration/{key}.png"` with no `?v=` query string (verified 27/27, zero cache-busted).
  4. `GET /static/panel-lookup.js` returned 200 and its body contained both `data-view-panel-replace-action` and `lightbox__replace`.
  5. `/history` (re-fetched after seeding one gallery entry + one runway event so the dialog actually renders) contains its `#panel-lookup-dialog` exactly once and zero occurrences of `lightbox__replace`, `data-view-panel-replace-action`, `enctype`, or `<input type="file"`.

## What remains unproven by automation (Task 5c)

Nothing in this repository can execute `panel-lookup.js`: this project is stdlib-only Python with no JavaScript test infrastructure, no bundler, and a standing no-build-step constraint, and no browser-automation tooling is configured for it. The one behaviour that stays unproven by any automated layer here is **the click itself** — that clicking a card's zoom trigger actually causes the script to write that card's URL into the form's `action` attribute before the dialog opens, and that the attribute changes correctly when a different card is clicked next.

What the automated layer above *does* pin is every input to that behaviour: the attribute is rendered on every trigger with the correct, un-busted value (render-level, three-file cross-module, and live served-HTML checks); the form and its `action=""` placeholder exist in the dialog; the optional lookup runs strictly after the mandatory guard, never inside it; the `setAttribute` write exists exactly once; and all four files (airlines_page.py, panel-lookup.js, style.css, and History's own render output) agree. The residual risk is confined entirely to the runtime click, which only a real browser can exercise — Task 6, below.

## Verification

- `companion/test_status_pages.py`: 124/124.
- `companion/test_view_pages.py`: 47/47.
- `companion/test_companion_app.py`: 126/126.
- `ruff check companion/`: clean, throughout every task.
- `./scripts/run-all-tests.sh`: `Result: PASS`, fully green, zero regressions.
- `git grep` for `_replace_control_html`/`REPLACE_SUMMARY_TEMPLATE`/`REPLACE_LABEL_TEMPLATE` outside `.planning/`: the only remaining occurrences are (a) the doc comment in `airlines_page.py` explaining *why* the two templates were retired, and (b) the new Task 3 check that asserts `airlines_page` no longer exposes them (`hasattr` membership test) — both are documentary/negative-assertion references, not surviving dead code.

## Task 6 checkpoint — pending

Task 6 is a blocking `checkpoint:human-verify` gate and was **not** run by this executor. It requires a real browser: opening the Airlines lightbox, inspecting the replace form's live `action` attribute via devtools after clicking one card, confirming it changes when a different card is clicked, performing a real upload through it, and confirming History's lightbox still opens/closes with no upload form. This is the one behaviour Task 5c documents as unreachable by any automated layer in this repo. Awaiting the developer's real-browser pass per the plan's six-step verification list.

## Self-Check: PASSED

All files (`companion/pages/airlines_page.py`, `companion/static/panel-lookup.js`, `companion/static/style.css`, `companion/test_status_pages.py`, `companion/test_view_pages.py`, `companion/test_companion_app.py`, this SUMMARY.md) confirmed present on disk. All five task commits (`97c6dc1`, `7419f94`, `62a299a`, `31cc287`, `4aeaf64`) confirmed present in `git log`.
