# Phase 14: Resolve an unidentified flight from the gallery lightbox - Pattern Map

**Mapped:** 2026-09-06
**Files analyzed:** 6 modified (no new files — presentation-layer only, per CONTEXT.md/RESEARCH.md)
**Analogs found:** 6 / 6 (every analog is inside the very file being modified, or its documented sibling)

## File Classification

| Modified File | Role | Data Flow | Closest Analog (same file unless noted) | Match Quality |
|---|---|---|---|---|
| `companion/pages/airlines_page.py` — new `_gap_card_html()` | component (server-rendered card) | request-response (CRUD-adjacent: reads poll state) | `_airline_card_html()` :494-584 | exact (same file, same role, sibling card shape) |
| `companion/pages/airlines_page.py` — new gap-block head-of-grid assembly | component (list composition) | transform (sort + cap over server state) | `_gallery_grid_html()` :587-598 + `health_page.unresolved_rows()` :1860 sort key | exact for composition shape; `health_page` for the sort key itself |
| `companion/pages/airlines_page.py` — `_lightbox_html()` extension (resolve-name/upload/delete forms) | component (dialog markup) | request-response | `_lightbox_replace_form_html()` :420-491, `_lightbox_html()` :601-639 | exact — this is literally extending the same function/dialog |
| `companion/pages/airlines_page.py` — shared resolve-form render functions (called from dialog AND `_resolve_section_html()`) | service-like helper (pure render fn, called twice) | transform | `_manual_delete_action()` :956-961 (one string-builder, two call sites: `_manual_resolution_row_html()` :1046-1050 and `_manual_resolution_cards_html()` :1116-1120) | exact — this is the project's own precedent for "one function, two call sites with differing action" |
| `companion/pages/airlines_page.py` — chip + `data-filter-text` additions on existing/absorbed cards | component | transform | `_airline_card_html()`'s chip block :569-575 and `_manual_superseded_marker_html()` :964-975 | exact |
| `companion/pages/airlines_page.py` — summary/overflow caption lines | component | transform | `_filter_bar_html()` :657-691 (caption register), `_manual_resolutions_section_html()`'s superseded_caption :1160-1162 | exact |
| `companion/pages/airlines_page.py` — **removal** of `_manual_resolution_table_html()`/`_manual_resolution_cards_html()`/`_manual_resolutions_section_html()` | dead-code removal | — | `_manual_resolution_rows()` :992-1024 is the one part that MUST survive, consumed not re-derived | n/a — deletion, not creation |
| `companion/static/panel-lookup.js` — imageless open (D-02) | utility (DOM toggle) | event-driven | existing `image.src = src;` line :99, MUST become a branch (see Shared Patterns) | role-match, mechanism documented as anti-pattern to avoid |
| `companion/static/panel-lookup.js` — form toggle by `data-view-panel-mode` (D-03) | utility (DOM toggle) | event-driven | `replaceForm` optional-lookup pattern :75, :110-113 | exact |
| `companion/static/panel-lookup.js` — `<a>` interception (D-12) | utility (event delegation) | event-driven | `findTriggerAncestor()` :81-90 + click listener :92-115 | exact — only needs `preventDefault()` added inside the existing handler |
| `companion/static/panel-lookup.js` — load-time auto-open (D-13/D-14) | utility (init-time DOM read) | event-driven (new: load-triggered, not click-triggered) | none in this file (first non-click entry point) — closest sibling shape is `list-filter.js`'s own guarded init-time `querySelector` calls :27-34 | no analog found (see below) |
| `companion/static/list-filter.js` — `[data-filter-set]` hook (D-11) | utility (DOM event wiring) | event-driven | `clearBtn`/`[data-filter-clear]` lookup + handler :34, :90-95 | exact |
| `companion/pages/health_page.py` — Resolve link target (no change to shape, D-13 consumes existing link) | component | request-response | `RESOLVE_LINK_HREF_TEMPLATE`/`RESOLVE_LINK_ARIA_TEMPLATE` :2006-2007, used at :2046-2047 and :2154-2155 | exact (untouched — confirms the URL contract this phase's auto-open reads) |
| `companion/static/style.css` — `.airline-card__placeholder`, `a.airline-card`, `.lightbox__resolve-name`/`.lightbox__delete`, `.manual-summary` | config/style | — | `.airline-card` :3624-3630, `.airline-card__image` :3661-3669, `.lightbox__replace` :4409-4413/:4431-4432 (multi-selector group extension), `.filter-bar [data-filter-clear]` :2759-2780 | exact |
| `companion/test_status_pages.py` — new gap-card/chip/summary/overflow render checks | test | request-response (render-string assertion) | existing `airlines_page` checks in this file (149 today) — pattern is `check(name, fn)` calling `airlines_page.render(ctx)` and asserting substrings | exact |
| `companion/test_view_pages.py` — extend `_lightbox_dom_contract_three_file_guard()` | test | source+render assertion | `_lightbox_dom_contract_three_file_guard()` :1712-1761, `_airlines_lightbox_constants_match_history()` :1763-1786 | exact |

## Pattern Assignments

### `_gap_card_html()` (new function, `airlines_page.py`)

**Analog:** `_airline_card_html()` (lines 494-584)

**Imports pattern** — no new imports; this file already imports `escape_html`, `layout`, `illustrations`, `manual_resolutions`, `enrich`, `poll_loop` at module top (verify against existing header, do not add a new dependency per CONTEXT.md's phase boundary).

**Core pattern to copy** (escape-once discipline, `data-filter-text`/`data-filter-group` construction):
```python
# Source: companion/pages/airlines_page.py, _airline_card_html(), lines 576-584
filter_text = escape_html(
    airline_name.lower() if isinstance(airline_name, str) else str(airline_name).lower())
return (
    '<div class="airline-card" data-filter-text="%s" data-filter-group="%d">'
    "%s"
    '<p class="airline-card__name">%s</p>'
    "%s"
    "</div>"
) % (filter_text, index, zoom_html, escape_html(airline_name), chips_html)
```
For the gap card: swap the outer `<div>` for a real `<a href="/airlines?resolve={prefix}">` per D-12/UI-SPEC's exact markup shape (UI-SPEC.md lines 244-255), swap `data-filter-group="%d"` (raw int) for a **string-prefixed** group value (`"gap%d" % i`, never a bare integer — RESEARCH.md Pitfall 4, confirmed against `list-filter.js`'s `"g" + group` string-concat at line 68 of that file, which never assumes numeric). Every new `data-view-panel-*` attribute value must still go through the same one-time `escape_html()` at the interpolation point (T-06.6.4.1-05, restated in this function's own docstring lines 500-506).

**Sort/threshold/cap to reuse, not reinvent:**
```python
# Source: companion/pages/health_page.py, unresolved_rows() sort (exact line not re-printed;
# grep-verified at the return statement following the loop, sort key:)
rows.sort(key=lambda row: (-row[1], row[0]))
```
`airlines_page.py` cannot import `health_page` (sibling page module — UI-SPEC line 262 states this explicitly), so this key is **duplicated verbatim**, not imported, matching this file's own existing duplicated-not-imported discipline for `LIGHTBOX_DIALOG_ID`/`_VIEW_PANEL_*_ATTR` (see `test_view_pages.py`'s `_airlines_lightbox_constants_match_history()` below).

---

### `_lightbox_html()` extension — resolve-name / resolve-upload / delete forms (`airlines_page.py`, lines 601-639)

**Analog:** `_lightbox_replace_form_html()` (lines 420-491) and the dialog's own element-order docstring (lines 614-619)

**Core pattern:** the existing dialog element order is image → caption → note → replace form → Close (docstring lines 614-619). Insert the new optional forms into that same flat concatenation, each with its own `action=""` placeholder exactly like the replace form's own:
```python
# Source: companion/pages/airlines_page.py, _lightbox_replace_form_html(), lines 471-472
'<form class="%s" method="post" enctype="multipart/form-data" action="">'
```
`action=""` is a **real, present placeholder attribute, never omitted** (docstring lines 430-433) — `panel-lookup.js` overwrites it via `setAttribute` on every click. The new resolve-upload and delete forms in the dialog must follow this identical placeholder-then-`setAttribute` contract, not a template-string injected at render time.

**Dialog assembly to extend:**
```python
# Source: companion/pages/airlines_page.py, _lightbox_html(), lines 627-639
return (
    '<dialog class="lightbox lightbox--wide" id="%s">'
    '<img class="lightbox__image" src="" alt="">'
    '<p class="lightbox__caption text-label mono"></p>'
    '<p class="lightbox__note text-body">%s</p>'
    "%s"
    '<button type="button" %s>Close</button>'
    "</dialog>"
) % (
    LIGHTBOX_DIALOG_ID, escape_html(LIGHTBOX_NOTE),
    _lightbox_replace_form_html(),
    _VIEW_PANEL_CLOSE_ATTR,
)
```
UI-SPEC's binding order (line ~130 of UI-SPEC.md) adds heading, manual-note, resolve-context, resolve-name form, resolve-upload-zone, delete form into this same `%s`-concatenation shape, all before Close — Close stays last (docstring lines 615-619: "the dismissal affordance is the stable bottom-most control").

---

### Shared render function, called from both dialog and no-JS fallback (Claude's Discretion #1, binding)

**Analog — the exact existing precedent for "one function, two call sites with a differing `action`":**
```python
# Source: companion/pages/airlines_page.py, _manual_delete_action(), lines 956-961
def _manual_delete_action(prefix):
    """The delete form's `action` attribute for `prefix`, built once here
    so the desktop `<tr>` and the mobile `<li>` can never diverge into
    building two different strings for the same row.
    """
    return "%s%s%s" % (MANUAL_DELETE_ROUTE_PREFIX, escape_html(prefix), MANUAL_DELETE_ROUTE_SUFFIX)
```
Two call sites, differing surrounding markup, same action-string builder:
```python
# Source: _manual_resolution_row_html(), lines 1046-1050 (desktop <tr>)
delete_form = (
    '<form method="post" action="%s">'
    '<button type="submit">%s</button>'
    "</form>"
) % (_manual_delete_action(prefix), DELETE_BUTTON_TEXT)
```
```python
# Source: _manual_resolution_cards_html(), lines 1116-1120 (mobile <li>) — byte-identical shape
delete_form = (
    '<form method="post" action="%s">'
    '<button type="submit">%s</button>'
    "</form>"
) % (_manual_delete_action(prefix), DELETE_BUTTON_TEXT)
```
**Apply this exact shape** to `_resolve_name_form_html(prefix_value, id_suffix)`, `_resolve_upload_form_html(action, id_suffix)`, `_resolve_context_html(row, id_suffix)` (extended with an `id_suffix` param per UI-SPEC's Component Inventory table) and `_manual_delete_form_html(action)` — one function per form, called once with real values for the no-JS fallback (`_resolve_section_html()`, unchanged call site) and once with placeholder values + `-dialog` id suffix for the dialog. UI-SPEC lines 123-136 give the exact signature table; this project precedent is what proves the pattern is not novel to this phase.

**Existing no-JS fallback content to extract into the new shared functions** (currently inline in `_resolve_section_html()`, lines 809-947): the Step A name-field block (lines 877-890), the Step A form wrapper (lines 891-897), the Step B upload-zone block (lines 920-937) — these three inline blocks are exactly what must be lifted into standalone functions accepting `id_suffix`, per UI-SPEC's Component Inventory table. `_resolve_context_html()` (lines 761-790) already exists as a standalone function and only needs the `id_suffix`/five-new-class-per-`<dd>` extension, not a full extraction.

**`_manual_resolution_rows()` (lines 992-1024) is the single source of `superseded`/`needs_artwork` — consume, do not re-derive** (RESEARCH.md Pitfall 6, Phase 14 CONTEXT.md's own "consumed, not re-derived" instruction). Thread its returned tuples straight into the new gap/manual-card chip renderer and into the dialog's `manual` attribute value — never re-call `enrich.static_airline_name_for_prefix()` or `illustrations.resolved_illustration_path()` a second time at a different call site.

---

### `panel-lookup.js` — imageless open (D-02)

**Anti-pattern to avoid (the current line that must change):**
```javascript
// Source: companion/static/panel-lookup.js, line 99 (existing, click handler)
image.src = src;
```
**Required fix (RESEARCH.md Pitfall 1, MDN-sourced):** branch on whether `src` is non-empty; when empty, `image.hidden = true; image.removeAttribute("src"); image.removeAttribute("alt");` — never `image.src = ""`. When non-empty, restore `image.hidden = false;` before setting `src`/`alt` as today. No new CSS needed for `.lightbox__image[hidden]` — `style.css` never overrides `[hidden]` for a bare element selector (verified: only `.dirty-bar[hidden]`/`.refresh-pill[hidden]` get bespoke treatment), so the UA default `display: none` applies unmodified.

### `panel-lookup.js` — optional-element pattern to extend three more times (D-03, D-09)

**Exact precedent (this is the template, copy verbatim shape):**
```javascript
// Source: companion/static/panel-lookup.js, lines 71-75
// Quick task 260903-btu: optional, looked up once like the three
// above, but excluded from their guard on purpose — History's page
// never renders this form, and that is a legitimate, expected state,
// not a missing-element error.
var replaceForm = dialog.querySelector(".lightbox__replace");
```
And its usage inside the click handler:
```javascript
// Source: companion/static/panel-lookup.js, lines 110-113
if (replaceForm) {
  var replaceAction = trigger.getAttribute("data-view-panel-replace-action") || "";
  replaceForm.setAttribute("action", replaceAction);
}
```
Repeat this exact shape for `resolveNameForm = dialog.querySelector(".lightbox__resolve-name")`, `resolveUploadForm = dialog.querySelector(".resolve-upload-zone")` (or `.lightbox__resolve-upload` per UI-SPEC naming), and `deleteForm = dialog.querySelector(".lightbox__delete")` — each guarded independently at the point of use, never folded into the mandatory `if (!image || !caption || !note)` guard at line 67.

**Mode-toggle addition** (new, no direct precedent in this file, but explicitly specified in RESEARCH.md Pattern 2 and UI-SPEC's Visibility toggle table):
```javascript
// Illustrative shape from RESEARCH.md, mirrors the existing replaceForm idiom
var mode = trigger.getAttribute("data-view-panel-mode") || "";
if (resolveNameForm) { resolveNameForm.hidden = (mode !== "gap"); }
if (resolveUploadForm) { resolveUploadForm.hidden = (mode !== "needs-artwork"); }
```
`manual` (`.lightbox__delete`, `.lightbox__manual-note`) is an **orthogonal** second attribute read the same way, per UI-SPEC's two visibility tables (mode-governed vs. manual-governed) — do not fold `manual` into the `mode` branch.

**Correctness rule (UI-SPEC line 177, restated as the single highest-risk detail):** every one of the new `data-view-panel-*` attributes must be copied on **every** open using the existing `attr || ""` idiom — never conditionally skipped — because the dialog's DOM is reused across clicks and a skipped write leaks the previous click's content.

### `panel-lookup.js` — `<a>` interception (D-12)

The existing `findTriggerAncestor()` (lines 81-90) already walks ancestors for `data-view-panel-src`, and needs zero change — an `<a>` naturally has this attribute since D-12 makes the gap card's whole element the trigger. Inside the click handler (lines 92-115), add `evt.preventDefault();` immediately after the trigger is confirmed non-null, unconditionally (a plain click on an art-card `<button>` trigger is unaffected since `preventDefault()` on a button click is a no-op for navigation purposes).

### `panel-lookup.js` — load-time auto-open (D-13/D-14) — genuinely new, no in-file analog

**No analog found** for this specific shape (first non-click entry point into this script since it shipped, confirmed by RESEARCH.md's own "State of the Art" table). The closest structural precedent for "guarded init-time DOM read, not an event handler" is `list-filter.js`'s own init-time `querySelector` calls:
```javascript
// Source: companion/static/list-filter.js, lines 27-34
var input = document.querySelector("[data-filter-input]");
if (!input) {
  return;
}
var countEl = document.querySelector("[data-filter-count]");
var emptyEl = document.querySelector("[data-filter-empty]");
var clearBtn = document.querySelector("[data-filter-clear]");
```
**Required factoring (RESEARCH.md Pitfall 2, mandatory):** extract the click handler's populate-and-open logic (lines 97-114 of `panel-lookup.js`) into one function taking a trigger node as its only argument; call it from the click listener (passing `findTriggerAncestor(evt.target)`) and, once at script init, from `document.querySelector('[data-view-panel-resolve-prefix="' + value + '"]')` where `value` comes from parsing `location.search`'s `resolve` param. If no matching element exists in the DOM, do nothing (Pattern 3 — never re-validate client-side; the server-rendered fallback section already tells the honest story).

### `list-filter.js` — `[data-filter-set]` hook (D-11, RESEARCH.md Pitfall 5, required not optional)

**Analog — the exact shape to mirror:**
```javascript
// Source: companion/static/list-filter.js, lines 34, 90-95
var clearBtn = document.querySelector("[data-filter-clear]");
...
if (clearBtn) {
  clearBtn.addEventListener("click", function () {
    input.value = "";
    applyFilter();
  });
}
```
Add, following this identical idiom:
```javascript
var setButtons = document.querySelectorAll("[data-filter-set]");
// on click: input.value = el.getAttribute("data-filter-set"); applyFilter();
```
This is a `querySelectorAll` (plural) unlike `clearBtn`'s singular `querySelector`, since more than one summary-line-style element could theoretically exist — degrade identically to every other optional lookup in this file (a page without `[data-filter-set]`, i.e. History, is unaffected — same guard-on-absence discipline as the whole file's own header comment, lines 13-22).

---

### `style.css` — new selectors, exhaustive list (UI-SPEC's own inventory, verified against current source)

**`.airline-card` base rule to extend for the `<a>` variant:**
```css
/* Source: companion/static/style.css, lines 3624-3636 */
.airline-card {
  background: var(--color-dominant);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  box-shadow: none;
  padding: var(--space-sm);
}
.airline-card:hover,
.airline-card:focus-within {
  border-color: transparent;
  box-shadow: var(--shadow-card-hover);
}
```
Add (new rule, class selector not tag selector so it applies regardless of `<div>` vs `<a>`): `a.airline-card { display: block; color: inherit; text-decoration: none; }` — no change needed to the hover/focus-within rule above, since `:focus-within` already matches an `<a>` receiving focus per spec.

**`.airline-card__image`'s reserved-box idiom to mirror for `.airline-card__placeholder`:**
```css
/* Source: companion/static/style.css, lines 3661-3669 */
.airline-card__image {
  width: 100%;
  height: auto;
  aspect-ratio: 450 / 132;
  object-fit: contain;
  display: block;
  border-radius: var(--radius-control);
  margin-bottom: var(--space-sm);
}
```
New `.airline-card__placeholder` reuses the identical `aspect-ratio: 450/132` (keeps grid rows aligned) plus a dashed border and `background: var(--color-canvas)` (the one-level-down surface token, UI-SPEC's own genuinely-new visual idea) — see UI-SPEC Component Inventory table for the full declaration block.

**`.lightbox__replace`'s multi-selector-group extension idiom — the exact precedent for adding `.lightbox__resolve-name`/`.lightbox__delete` to the same rule rather than duplicating it:**
```css
/* Source: companion/static/style.css, lines 4409-4413, extended already once at 4425-4432 */
.lightbox__replace {
  display: block;
  padding-top: var(--space-md);
  min-width: 0;
}
/* Phase 13 already extended a *sibling* rule (.lightbox__replace-zone) this same way: */
.lightbox__replace-zone,
.resolve-upload-zone {
  display: flex;
  flex-direction: column;
  ...
}
```
Add `.lightbox__resolve-name, .lightbox__delete` to `.lightbox__replace`'s own selector list (making a 3-way group), not a new duplicated rule — matches this file's own established convention, restated in UI-SPEC's Component Inventory table.

**`.manual-summary`'s analog — copy `.filter-bar [data-filter-clear]`'s declarations verbatim (not scoped under `.filter-bar` since the summary line sits below it, not inside it):**
```css
/* Source: companion/static/style.css, lines 2759-2780 */
.filter-bar [data-filter-clear] {
  height: auto; min-height: 0; min-width: 0; padding: 0;
  background: none; border: none; box-shadow: none; border-radius: 0;
  font-family: var(--font-ui); font-size: 12px; font-weight: var(--weight-regular);
  letter-spacing: normal; color: color-mix(in srgb, var(--color-text) 70%, transparent);
  text-decoration: underline; text-underline-offset: 2px; cursor: pointer;
}
.filter-bar [data-filter-clear]:hover { color: var(--color-text); }
```
New `.manual-summary` gets the identical property list under its own class selector (unscoped), plus the identical `:hover` rule — UI-SPEC line 154 states this exactly.

**Dead code after removal** (do in the same task, not a separate cleanup pass, to avoid an orphaned selector lingering): `.manual-resolution__status--superseded`'s declarations become dead once `_manual_resolutions_section_html()`/the table/card-list functions are deleted — UI-SPEC line 61 flags this explicitly as "Wave cleanup, not a UI-SPEC concern" but it belongs in the same removal task as the Python functions.

---

### `companion/pages/health_page.py` — no change, confirm the contract only

**Analog (already correct, do not touch):**
```python
# Source: companion/pages/health_page.py, lines 2006-2007
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_ARIA_TEMPLATE = "Resolve prefix %s"
```
Used at lines 2046-2047 (desktop) and 2154-2155 (mobile) — Phase 13's D-10 "no `<form>`, no `<button>`" on Health still holds. This phase's only relationship to this file is that D-13's auto-open answers the URL this constant already produces.

---

## Shared Patterns

### Escape-once discipline (T-06.6.4.1-05)
**Source:** every interpolation site in `airlines_page.py` (e.g. `_airline_card_html()` lines 532, 548, 564-566, 576-577; `_manual_delete_action()` line 961)
**Apply to:** every new interpolated value in gap-card/chip/summary/overflow rendering — the prefix, callsign, and every copy template argument goes through `escape_html()` exactly once, at the point of interpolation, never re-escaped (already-safe markup from `layout.concise_timestamp_html()` is the one documented exception, interpolated verbatim).

### Optional element, gracefully absent (`panel-lookup.js`)
**Source:** `panel-lookup.js` lines 71-75, 110-113 (`replaceForm`)
**Apply to:** every one of this phase's new dialog elements (`.lightbox__resolve-name`, `.resolve-upload-zone`/`.lightbox__resolve-upload`, `.lightbox__delete`) — looked up once outside the mandatory `image`/`caption`/`note` guard (line 67), each guarded independently at the point of use.

### One rendering function, two call sites with differing `action`
**Source:** `_manual_delete_action()` (lines 956-961) + its two consumers (lines 1046-1050, 1116-1120)
**Apply to:** `_resolve_name_form_html()`, `_resolve_upload_form_html()`, `_resolve_context_html()`, `_manual_delete_form_html()` — one function each, called once for the no-JS fallback (real values) and once for the dialog (placeholder values + `-dialog` id suffix where the function has id-bearing children).

### Validate-then-join over server-derived state, never over the query string
**Source:** `unresolved_row_for_prefix()` (lines 700-758), consumed unchanged by `_resolve_section_html()` (lines 809-947)
**Apply to:** D-13's auto-open — `location.search`'s `resolve` value is used only to find a DOM element the server already rendered; the script never itself re-validates whether a prefix is live, resolved, or stale.

### No-network-call invariant (script header comment, both `.js` files)
**Source:** `panel-lookup.js` lines 14-22, `list-filter.js` lines 13-16
**Apply to:** the `image.src = ""` anti-pattern fix (D-02) is the one place this phase could accidentally violate this standing constraint — `removeAttribute("src")` is the required fix, not a stylistic preference.

## No Analog Found

| File/Behavior | Role | Data Flow | Reason |
|---|---|---|---|
| `panel-lookup.js` load-time auto-open entry point (D-13/D-14) | utility | event-driven (load-triggered) | First non-click entry point into this script since it shipped (confirmed via RESEARCH.md's own "State of the Art" table) — closest structural precedent is `list-filter.js`'s guarded init-time `querySelector` pattern (lines 27-34), used above as the nearest available shape, but the actual "read `location.search`, find element, run shared populate function" logic has no prior instance in this codebase. Planner should treat RESEARCH.md's Pitfall 2 and UI-SPEC's "D-13/D-14 auto-open" section (lines 199-201) as the authoritative spec for this piece, not a codebase analog. |

## Metadata

**Analog search scope:** `companion/pages/airlines_page.py`, `companion/pages/health_page.py`, `companion/static/panel-lookup.js`, `companion/static/list-filter.js`, `companion/static/style.css`, `companion/test_view_pages.py`, `companion/test_status_pages.py` (all read directly, no directory-wide glob needed — CONTEXT.md/RESEARCH.md already named the exact file set and this is a presentation-layer-only, no-new-file phase)
**Files scanned:** 7
**Pattern extraction date:** 2026-09-06
