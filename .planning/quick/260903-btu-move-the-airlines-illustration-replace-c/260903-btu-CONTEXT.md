# Quick Task 260903-btu: Move the Airlines illustration-replace control into the lightbox - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Task Boundary

Move the Airlines gallery's illustration-replace control (quick task 260902-v26) from a per-card collapsed `<details>` disclosure under each grid thumbnail into the click-to-enlarge lightbox (quick task 260902-tli) instead. Developer's own words: "je m'attendais à ce que la proposition de remplacement soit disponible une fois qu'on a zoomé sur la photo" (I expected the replacement option to be available once you've zoomed on the photo).

</domain>

<decisions>
## Implementation Decisions

### The per-card disclosure is removed entirely, not duplicated
Confirmed directly with the developer: the replace control lives ONLY inside the enlarged lightbox view now. It does not stay under each small grid thumbnail as well. `_airline_card_html()` stops calling `_replace_control_html()`/rendering `replace_html` in the card markup.

### Technical design, grounded by reading the real current code (not to be re-derived from scratch)
`companion/static/panel-lookup.js` is confirmed, by direct reading, to already have exactly the extension point this needs:
- `image`/`caption`/`note` are looked up ONCE at script-init time via `dialog.querySelector(...)`, and a MANDATORY guard (`if (!image || !caption || !note) return;`) makes the whole script no-op if any is missing — this is why History's page (no replace form) must never gain one of these three elements, and why a NEW replace-related element must NOT be added to this mandatory list (that would break History's lightbox entirely).
- The click handler (`document.addEventListener("click", ...)`) already reads two attributes off the clicked trigger (`data-view-panel-src`, `data-view-panel-caption`) and writes them into the dialog on every click. This is the exact mechanism to extend: a **third, OPTIONAL** attribute (e.g. `data-view-panel-replace-action`) written into a replace-form's `action` attribute inside the dialog — looked up ONCE at init time like the other three, but checked for `null` WITHOUT triggering the mandatory early-return (since it's legitimately absent on History's copy of the dialog).

So the concrete shape: `_airline_card_html()`'s zoom `<button>` gains a new `data-view-panel-replace-action="{un-busted image_url}"` attribute alongside its existing two `data-view-panel-*` attributes (use the UN-busted URL, matching `_replace_control_html()`'s own existing documented reasoning: "a query string on a POST target is pointless"). `airlines_page._lightbox_html()` gains a `<form>` inside the dialog (replacing the file/label/button markup currently in `_replace_control_html()`, minus the `<details>`/`<summary>` wrapper — no need for a collapsed disclosure inside a view the user already deliberately opened) with `action=""` (a real, present attribute placeholder — do not omit it) that the script fills in per-click. `panel-lookup.js` gets exactly one new optional lookup + one new conditional write inside the existing click handler — everything else in the file (the mandatory guard, the ES5-safe discipline, the "never decide from viewport/orientation" standing constraint, the close-button wiring) stays untouched.

### The form's plain-POST-with-redirect behavior is unchanged, just relocated
No new JavaScript submit logic. The form still does a real native `multipart/form-data` POST to `/illustration/{key}.png` and the browser navigates away on submit (closing the dialog naturally, since the whole page reloads) — matching plan 03's original, deliberate "JS-free" design. Do not add a fetch/XHR-based submit or any dialog-stays-open-after-upload behavior; that is out of scope for this relocation.

### History's lightbox must be provably unaffected
History's own `_lightbox_html()` (companion/pages/history_page.py) is not touched. Its rendered dialog carries no replace-form element and no `data-view-panel-replace-action` attribute anywhere, and panel-lookup.js's new optional lookup must resolve to `null`/absent on that page without affecting anything else the script already does there (image src/caption swap, close button, native dialog behavior).

### Claude's Discretion
- Exact visual/markup shape of the replace form now that it lives inside a shared lightbox rather than a per-card `<details>` — a small, minimal, always-visible form (no `<summary>` disclosure needed, since the lightbox itself is already the "I want to look closer/act on this" moment) is the working assumption above, but the planner should verify this reads well against the design system (`sketch-findings-skypane` skill) before finalizing exact markup/classes.
- Whether `_replace_control_html()` is renamed/restructured or replaced outright by new logic inside `_lightbox_html()` — whatever keeps the codebase's existing docstring/naming conventions clearest.
- Cleanup: the per-card `.airline-card__replace`/`.airline-card__replace-form` CSS rules, and every test in `companion/test_status_pages.py`/`companion/test_view_pages.py`/`companion/test_companion_app.py` that asserted the OLD per-card disclosure's presence, need retargeting (not silently left pinning dead markup) onto the new lightbox-based contract. Grep thoroughly — quick task 260902-v26 added real coverage for the old shape that will now be testing something that no longer exists.
- Whether `REPLACE_SUMMARY_TEMPLATE`/`REPLACE_LABEL_TEMPLATE`/`REPLACE_BUTTON_TEXT` (the existing copy constants) carry over as-is into the new lightbox form, or need rewording now that there's no `<summary>` affordance to word — planner's call, but prefer minimal changes to already-approved copy where the meaning still fits.

</decisions>

<specifics>
## Specific Ideas

None beyond the technical design captured above, which came directly from reading `companion/static/panel-lookup.js`, `companion/pages/airlines_page.py`'s current `_replace_control_html()`/`_airline_card_html()`/`_lightbox_html()`, and `companion/pages/history_page.py`'s own `_lightbox_html()` during this discussion pass.

</specifics>

<canonical_refs>
## Canonical References

- `companion/static/panel-lookup.js` — read in full during this discussion; the exact extension point (optional third data attribute, optional fourth dialog-element lookup) is described above from direct reading, not assumption.
- `companion/pages/airlines_page.py` — `_illustration_cache_buster()` (~line 170), `_replace_control_html()` (~line 208), `_airline_card_html()` (~line 263), `_lightbox_html()` (~line 367) — all read in full during this discussion. Note these line numbers will shift once this task's own edits land; re-read fresh during planning, don't trust these as post-edit line numbers.
- `companion/pages/history_page.py`'s own `_lightbox_html()` — must stay working completely unmodified; read it before touching anything shared.
- Quick task `260902-v26`'s plan 03 (`.planning/quick/260902-v26-add-the-ability-to-replace-an-airline-s-/260902-v26-03-SUMMARY.md`) — the original per-card disclosure design being superseded here; useful for understanding what test coverage exists and needs retargeting.
- Quick task `260902-tli`'s own plan (`.planning/quick/260902-tli-add-a-click-to-enlarge-lightbox-to-the-c/260902-tli-PLAN.md`) — the original lightbox-sharing design this task extends.

</canonical_refs>
