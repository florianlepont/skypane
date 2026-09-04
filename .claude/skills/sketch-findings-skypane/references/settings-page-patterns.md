# Settings Page Patterns

## Design Decisions

### The Theme group is a chip grid, not a fieldset (06.6.4.1.1-05)

Settings renders zero `<fieldset>` and zero `<legend>` elements anywhere on the page — all four groups (Theme, Runway, Diagnostic LED, Poll) are named by an `<h2 class="text-heading">` at one consistent heading level, D-04/D-05 (06.6.3) having already dropped `<fieldset>` from Theme and Runway before this phase.

`theme_fieldset()`'s multi-theme branch (`len(device_config.THEME_IDS) > 1`, the normal case) emits a `.theme-status` card — the same wrapper Runway and Diagnostic LED use — holding a `.theme-chip-grid` of one `.theme-chip` per registry entry: a real rendered `/theme-preview/{id}.png` preview, two real-palette swatch dots, and the theme name, replacing what used to be 16 stacked 44px native radios. See `SKILL.md`'s `<design_direction>` Cards paragraph and `references/control-density.md` for the chip's own selectable-card mechanism (reused verbatim from `.runway-card`) and its selected-state treatment (border, check glyph, and — since 06.6.4.1.1-06 — a background wash). The single-theme fallback branch (`len() == 1`) is unaffected: it still renders the plain read-only `.theme-status__row` swatch-plus-label line, no chip grid needed for a one-option "choice."

### The flash-banner slot (06.6.4.1.1-04, D-17)

The flash banner (the "Saved — ..." confirmation) renders directly below `page_header()`'s own markup, not above the page title — so saving no longer shifts the title down the page. `body` is one opaque pre-built string by the time `layout.page_shell()` receives it, so there is no structural handle on "just after the header"; `page_header()` instead leaves `layout.FLASH_SLOT_MARKER` (`"<!--flash-slot-->"`) as a literal handle at exactly that point, appended after its own closing `</div>`.

`page_shell()` resolves the marker in two branches:
- **A page built on `page_header()`** (every authenticated page, including Settings) carries the marker in `body`; the flash banner is spliced in at that exact point and the banner's old pre-body slot is cleared so it is not emitted twice.
- **A page that does NOT use `page_header()`** (login, 404, and any future bare page) has no marker in `body` at all; the flash banner keeps rendering in its original before-body slot, so no such caller needs to change and none silently loses its banner. This is the documented fallback the marker's own contract explicitly names.

An unconditional second `replace()` on the marker string guarantees it never reaches the browser on any path — flash or no-flash, marker-carrying or not.

### The one-caption-per-section rule

Every section on the Settings page (`/settings`, `companion/pages/config_page.py`) renders exactly one muted caption sentence directly under its heading, before its control — Theme, Runway, Diagnostic LED, and Poll: four sections, four captions, zero heading-without-caption sections. That invariant is what a future edit would most easily break silently, since nothing stops a section rendering with no caption at all.

Markup shape: `<p class="text-label section-caption">{escaped caption text}</p>`. The two classes deliberately **compose** rather than either restating the other — `.text-label` already supplies `var(--font-label-size)` (14px), so `.section-caption` declares only colour (`color-mix(in srgb, var(--color-text) 70%, transparent)` — this file's one existing muted-secondary strength, not a new value). The markup always carries both classes together; a caption with only `.section-caption` and no `.text-label` would render at the browser's default paragraph size.

What the rule deliberately does *not* declare, and why the absence is a decision rather than an omission: `.section-caption` carries no `margin` of its own. Unlike the heading-rhythm rule (`h1, h2, h3, .text-heading { margin: 0 0 var(--space-sm); }`), this role keeps the user-agent default paragraph margin — the description/helper paragraphs it replaced already relied on that default, and the validated typography sketch was measured against it. Do not "complete" this rule by adding a margin.

This shape replaced an earlier description-above / helper-below paragraph pair: each group used to render a description sentence above its control (`THEME_SECTION_DESCRIPTION`/`RUNWAY_SECTION_DESCRIPTION`) *and* a helper sentence below it (`THEME_HELPER_TEXT`/`RUNWAY_HELPER_TEXT`/`LED_HELPER_TEXT`) — Theme and Runway rendered both, LED escaped the doubling but kept its lone paragraph un-muted and positioned after its control instead of before. All five of those constants are retired outright; each group now carries exactly one caption.

The four constants (`THEME_SECTION_CAPTION`, `RUNWAY_SECTION_CAPTION`, `LED_SECTION_CAPTION`, `POLL_SECTION_CAPTION`) live in one named family, contiguous in `companion/pages/config_page.py`, each with the developer-validated copy verbatim.

One section's caption is consumed by a two-branch renderer: `poll_trigger_section(cooldown_remaining)` has an enabled (zero-cooldown) branch and a disabled (cooldown-active) branch, and `caption_html` is computed once above the `if cooldown_remaining > 0:` split so it is interpolated as the first element of *both* return expressions — the same computed-once-reused-by-both-branches idiom `theme_fieldset()` already established for its own read-only/editable branch split. A caption emitted on only one branch would silently disappear for the whole cooldown window; this is why the constant is computed once outside the branch rather than inlined into each return.

### The floating save bar — a worked example

This component iterated four times in a single session, which makes it the best available case study for how a pattern in this app actually gets settled. The mechanics below are stated as the CURRENT contract first and completely; the four-iteration history follows as a separate, clearly-marked-historical list.

**Current mechanics.** `.dirty-bar` is a `<div data-dirty-bar hidden role="status">` emitted by `config_page.render()` as the **last** element on the page — a sibling of `<form id="settings-form">`, not a descendant of it, submitting its Save button via `<button type="submit" form="settings-form">` (a cross-DOM form association) rather than native nesting.

- **Surface, border, radius.** `background: var(--color-dominant)` (the same card surface every other card on the page uses, not the receding `--color-secondary` an earlier iteration used), a full `1px solid var(--color-border)` border on all four sides, `border-radius: var(--radius-card)` (10px — the floating-overlay radius, not the 8px card-set radius; see `references/control-density.md`'s radius pairing note).
- **The two-layer shadow.** `box-shadow: var(--shadow-card-hover), 0 12px 32px rgba(18, 21, 27, 0.16);` — two layers, not one. The first layer is the real `--shadow-card-hover` token, which carries its own dark-mode and `[data-ui-theme]` variants automatically; the second, larger layer is a raw `rgba()` literal, consistent with this file's existing raw-rgba shadow precedent (`button[type="submit"]`'s own inset-highlight declarations), and exists to push the card visibly further off the page than a card-hover shadow alone achieves. `.lightbox` is this file's other precedent for a floating element carrying a resting (not hover-revealed) shadow, for the same reason: both are floating overlays, not page-flow cards.
- **Positioning, per breakpoint.** Below 960px the bar is full-width, in normal document flow (`margin-top: var(--space-md)`), immediately after the form's own always-rendered bottom Save Settings button. At `>=960px` it becomes `position: fixed` — not `sticky` (see history below) — with `bottom: var(--space-lg)`.
- **Reproducing the content column's geometry.** `left: calc(240px + var(--space-xl) + var(--space-md))`, `right: var(--space-md)`. The `240px` and `var(--space-xl)` pair is a **duplicated-not-imported must-equal value** — it has to stay equal to `.dashboard-shell`'s `grid-template-columns` first track (`240px`) and `column-gap` (`var(--space-xl)`); there is no shared token for either, so the pair is guarded by a harness check instead of a shared variable. The trailing `var(--space-md)` is the inset from the content column's own edge.
- **Sizing.** `width: fit-content; max-width: calc(min(1440px, 100%) - var(--space-md) * 2); margin: 0 auto;` — the bar sizes to its own content (the changed-sections label plus the two buttons), not the full column width. `margin: 0 auto` is the classic auto-margin-centring trick for a positioned box, which requires a definite `width` to engage — this is why `width: fit-content` is set explicitly rather than left unset.
- **Why the max-width is reduced, not just copied.** For a `position: fixed` box, `100%` resolves against the *viewport*, not the content column. Left as the bare `min(1440px, 100%)` `.dashboard-main` itself uses, once the viewport passes roughly 1712px (240px sidebar + 32px gap + 1440px cap) the `1440px` half of the `min()` alone would size the box — flush with the content column on both sides, silently cancelling the visible inset at exactly the widths (e.g. a 16-inch MacBook Pro's 1728px default logical width) where it matters most. Reducing the cap by twice the inset (`- var(--space-md) * 2`) keeps the inset visible past that width too.
- **Centring mechanism dependency.** `margin: 0 auto`'s centring only works because `width: fit-content` gives the box a definite width to centre within its `left`/`right` positioning region — removing the `width` declaration silently disables the centring.
- **Bottom inset.** `var(--space-lg)` (24px), not `var(--space-md)` (16px) — a deliberately larger gap from the viewport edge, which reads as more clearly "floating" rather than merely "shorter."
- **No `z-index`, and why.** This is the last positioned element in document order and nothing it overlaps creates a competing stacking context, so a `z-index` here would be an unearned magic number. If a future overlap appears, add one then, with a stated reason — do not add one preemptively.
- **Hidden-state specificity collision.** `.dirty-bar[hidden] { display: none; }` exists because the base rule's `display: flex` (author stylesheet) always beats the user-agent stylesheet's `[hidden] { display: none }` regardless of source order — without this override, `dirty-state.js`'s native `hidden` property toggle would have no visible effect and the bar would render even when the form isn't dirty.
- **JS-only-affordance rule.** `.js [data-static-save-fallback] { display: none; }` hides the form's own always-rendered bottom Save Settings button once `.js` (added unconditionally by `nav-dropdown.js`'s first statement) proves script is running — so the dirty-state bar is the sole visible save affordance rather than both showing at once. Without JS, the bottom button remains the only way to save; this is the no-JS floor (D-06 graceful degradation), not a decoration.

**How it got here (history, each line SUPERSEDED — none of this describes current behaviour):**

1. quick task 260901-re6 — the bar moved from a genuine descendant of `<form>` (sticky positioned, submitting via normal DOM nesting) to a sibling emitted last on the page, `position: fixed` instead of `sticky` SUPERSEDED. `position: sticky`'s containing block is the nearest scrolling ancestor's *box*, which was the short three-section `<form>` — so the bar stopped sticking at the form's own bottom edge instead of the viewport's, visibly detaching above the Poll section on a page much taller than the form. `position: fixed` is immune to that regardless of any ancestor's height.
2. quick task 260901-re6 (same task, styling half) — the bar's surface moved from `--color-secondary` (a receding, secondary-looking strip) to `--color-dominant` SUPERSEDED, with a single top hairline and an upward-only box-shadow (a y-negated `--shadow-card-hover` literal).
3. quick task 260901-s5o — the bar restyled from a flush, square-cornered, top-hairline-only docked toolbar into a floating, inset, rounded pop-up card SUPERSEDED: a full four-side border replaced the top-only hairline, the shadow became a real token (`--shadow-card-hover`) plus one ambient rgba layer instead of the hand-rolled upward-only literal, and the `>=960px` rule gained a symmetric `var(--space-md)` inset on `bottom`/`right`/`left` with a correspondingly reduced `max-width`.
4. Direct follow-up commit `e87d46d` (non-GSD, developer feedback after seeing 260901-s5o live) — `width: fit-content` replaced an implicit full-column stretch SUPERSEDED (the previous rule set `right` with no `width`, which per CSS2.1's abs/fixed sizing rules — `width: auto` plus both `left` and `right` non-`auto` — stretched the box to fill the entire positioning region, exactly as wide as `.dashboard-main`); the ambient shadow layer deepened from `0 8px 24px / .10` SUPERSEDED to `0 12px 32px / .16`; `bottom` grew from `var(--space-md)` to `var(--space-lg)` SUPERSEDED; and the `>=960px` padding override was dropped entirely SUPERSEDED (it only existed to align a full-width bar with the content gutter — once the bar is compact, the base rule's ordinary `padding: var(--space-md)` applies unmodified).

Two things this history section must get right because they are the parts most likely to be reintroduced wrongly, both already covered above: the duplicated-not-imported `240px`/`column-gap` must-equal geometry (guarded by a harness check, not a shared variable), and the reason the width cap is *reduced* rather than left copied from `.dashboard-main` (a fixed-position box's `100%` resolves against the viewport, not the content column).

## CSS Patterns

```css
/* Section caption — composes with .text-label, adds colour only */
.section-caption {
  color: color-mix(in srgb, var(--color-text) 70%, transparent);
}

/* Save bar, base rule (all widths) */
.dirty-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-dominant);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-md);
  box-shadow: var(--shadow-card-hover), 0 12px 32px rgba(18, 21, 27, 0.16);
}
.dirty-bar[hidden] { display: none; }
.js [data-static-save-fallback] { display: none; }

/* Save bar, >=960px: fixed, inset, content-sized */
@media (min-width: 960px) {
  .dirty-bar {
    position: fixed;
    bottom: var(--space-lg);
    left: calc(240px + var(--space-xl) + var(--space-md));
    right: var(--space-md);
    width: fit-content;
    max-width: calc(min(1440px, 100%) - var(--space-md) * 2);
    margin: 0 auto;
  }
}
```

## HTML Structures

```html
<!-- One caption per section, directly under the heading -->
<div class="theme-status" data-dirty-section="Theme">
  <h2 class="text-heading">Theme</h2>
  <p class="text-label section-caption">Panel colors for departing/arriving flights...</p>
  <!-- control -->
</div>

<!-- Save bar: sibling of the form, cross-DOM submission via form= -->
<form id="settings-form" data-dirty-form method="post" action="/settings">
  <!-- sections -->
  <button type="submit" data-static-save-fallback>Save Settings</button>
</form>
<div class="dirty-bar" data-dirty-bar hidden role="status">
  <span data-dirty-count>Unsaved changes</span>
  <button type="submit" class="dirty-bar__save" form="settings-form">Save settings</button>
  <button type="button" class="dirty-bar__cancel" data-dirty-cancel>Cancel</button>
</div>
```

## What to Avoid

- Re-docking the bar: any return to a top-only hairline, squared corners, an upward-only shadow, or full-column width — all four are recorded historical states above, not alternatives still on the table.
- Reintroducing `position: sticky` for the `>=960px` rule — its containing-block behaviour is exactly the bug `position: fixed` fixed.
- Adding a `z-index` to `.dirty-bar` without a stated reason — none is needed today, and one added preemptively is an unearned magic number.
- Adding a Settings-specific caption CSS rule instead of reusing the existing `.text-label.section-caption` pair.
- Reintroducing the `>=960px` two-column `.config-form` grid — removed outright by 06.6.4.1 (D-01); do not restore it while "fixing" Settings' layout.

## Origin
Synthesized from: 06.6.3-companion-per-page-redesign (D-03, the original dirty-state bar), 06.6.4.1-companion-page-by-page-ia-consolidation (D-01, D-03, D-04, D-26, closed), quick tasks 260901-qif/260901-re6/260901-s5o, direct commit `e87d46d`, and 06.6.4.1.1-04/06.6.4.1.1-05 (D-01 through D-08/D-17: the theme-chip grid, and the flash-slot move below `page_header()`), cross-checked against `companion/pages/config_page.py` / `companion/static/style.css` / `companion/static/dirty-state.js` / `companion/layout.py` read live at execution time (quick task 260901-t00, updated 06.6.4.1.1-06).
