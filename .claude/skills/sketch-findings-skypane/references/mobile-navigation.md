# Mobile Navigation

## Design Decisions

**Winning variant, origin: Sketch 002, Variant C ("Header dropdown").** Replaced the horizontal-scroll `.nav-bar` strip (below 960px) that real-device testing during 06.5-03 found hid most tabs behind an undiscoverable swipe, even after the earlier crush-bug fix (commit `b90ed88`). The winning-variant framing and the real-device origin story are both still true and both still explain the choice of a push-down dropdown over a full-screen or slide-in variant — see What to Avoid below. What did not survive intact is almost every implementation detail: the sketch's class names and positioning mechanism never shipped as drafted.

**Real shipped classes.** The toggle button is `#site-nav-toggle` (`class="site-nav-toggle"`, id constant `NAV_TOGGLE_ID` in `companion/layout.py`). The panel is `#mobile-nav` (`class="mobile-nav"`, id constant `MOBILE_NAV_ID`). Its nav region is `.mobile-nav__nav`, its links are `.mobile-nav__link` (active modifier `.mobile-nav__link--active`), and its footer region is `.mobile-nav__footer`. None of the sketch's own SUPERSEDED names — `.dropdown`, `.dropdown__nav`, `.nav-link`, `.hamburger-btn`, `.theme-row`, `.theme-btn` — exist anywhere in the shipped stylesheet or markup; they never shipped as drafted. An implementer reaching for any of those names today would be styling nothing.

**The real in-flow push-down mechanism, and the reversal it represents.** The panel is `flex-basis: 100%` on `.site-header`'s own wrapping flex row (`.site-header { display: flex; flex-wrap: wrap; ... }`) — this is what forces `.mobile-nav` onto its own full-width row directly below the title/toggle row, *while staying in normal document flow*. An earlier version of this rule used `position: absolute` on `.mobile-nav` SUPERSEDED for the same visual goal — this is a genuine, real reversal, not a hypothetical: absolute positioning removes an element from flow entirely, so it could only ever *overlay* page content, never *push* it down, no matter how the CSS was tuned. Real-device verification during 06.6.1 found exactly this defect (documented in `06.6.1-06-SUMMARY.md`) and it was fixed by switching to the in-flow `flex-basis` mechanism described above. Do not reintroduce `position: absolute` for this component under any framing of "simplifying" the layout — it reopens a defect that was already found and fixed on real hardware, not merely a style preference reverted.

**Clipping is `.js`-gated; the base rule is the no-JS floor.** The panel's *visual* open/closed clipping (`max-height: 0; overflow: hidden; transition: max-height .22s ease;`, then `.mobile-nav--open { max-height: 420px; }`) lives entirely under a `.js .mobile-nav` selector — scoped to the `.js` class `nav-dropdown.js` adds to `<html>` unconditionally as its very first statement. Without that class ever appearing (no JavaScript, or the script failing to load), the base `.mobile-nav` rule alone applies, rendering the panel in its natural, unclipped, fully visible document flow — this is the no-JS floor (UXA-12), not an oversight. The `.js`-scoped rule and the base rule must never be edited independently of one another.

**Where `aria-expanded` and `hidden` are actually managed.** Both live entirely in `companion/static/nav-dropdown.js`, never in CSS and never server-side beyond the initial render. `aria-expanded` on the toggle is the single source of truth for open/closed state — the CSS open-state class (`.mobile-nav--open`) and the panel's native `hidden` property are both *derived from* `aria-expanded` inside one `setOpen(next)` function, never set independently elsewhere in the file. This is what makes it structurally impossible for the visual state and the announced accessibility state to diverge. `panel.hidden = true` is set explicitly on script load (matching the server-rendered `aria-expanded="false"` baseline) so a keyboard/screen-reader user cannot land on an invisible, still-tabbable panel before the first toggle.

**Panel surface and shadow.** `.mobile-nav` uses `background: var(--color-secondary)` (the elevated/nav surface, not the primary card surface) and `box-shadow: var(--shadow-card-hover)` unconditionally at rest — this is a floating-overlay exception to the hairline-at-rest card contract (see `references/control-density.md`), appropriate since the dropdown genuinely floats over the content below it once open.

**Link geometry.** `.mobile-nav__link` is `height: 32px` with `font-size: var(--font-label-size)` (14px) — it does **not** carry a 44px tap-target floor; that floor was traded away in the same 06.6.4 (D-05) pass that resized `.sidebar-link` to match, so the two nav renderings stay visually and dimensionally identical. `font-family` is explicitly `var(--font-ui)` (sans), stated in code as a deliberate boundary: the sketch prototype rendered these links in serif at 18px, and that detail was never carried into the shipped contract.

**Current tab set, count, and the renamed/retired entries.** Four tabs, in order: Settings, Health, Airlines, History. This was five (Config, Health, Airlines, History, Preview) SUPERSEDED — 06.6.4.1 (D-26) renamed "/config"/"Config" to "/settings"/"Settings" (the old path 404s by design, no redirect), and 06.6.4.1 (D-22, still open) retired the standalone Preview tab outright, absorbing its content into History. Both nav renderings (`sidebar_nav()` and `_mobile_nav_html()` in `companion/layout.py`) consume the same `NAV_TABS`/`_nav_links()` iteration, so the two can never disagree on the tab set.

**Footer region.** `.mobile-nav__footer` groups the theme picker (`_theme_form_html()`'s output) with the Sign out control (`_logout_form_html()`) inside one region, separated from the nav links by a hairline (`border-top: 1px solid var(--color-border)`) — this is where the theme picker relocates once it is no longer squeezed into the header row, matching the sidebar's own `.sidebar-footer` grouping (06.6.2-05, D-17). It is not, as an earlier draft of this file implied, a theme-picker-only slot — Sign out lives in the same footer region.

## CSS Patterns

```css
/* Toggle + panel, base rule */
.site-nav-toggle {
  margin-left: auto;
  min-height: 44px; min-width: 44px;   /* toggle keeps the 44px floor */
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}
.site-nav-toggle[aria-expanded="true"] {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

/* In-flow push-down: flex-basis on the wrapping header row, NOT the SUPERSEDED position: absolute approach */
.site-header { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-lg); }
.mobile-nav {
  flex-basis: 100%;
  background: var(--color-secondary);
  box-shadow: var(--shadow-card-hover);
  border-bottom-left-radius: var(--radius-card);
  border-bottom-right-radius: var(--radius-card);
}

/* Clipping is .js-gated; unscoped base rule above is the no-JS floor */
.js .mobile-nav {
  max-height: 0;
  overflow: hidden;
  transition: max-height .22s ease;
}
.js .mobile-nav--open { max-height: 420px; }

.mobile-nav__link {
  height: 32px;
  font-size: var(--font-label-size);
  font-family: var(--font-ui);
}
.mobile-nav__link--active {
  color: var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
  font-weight: var(--weight-semibold);
}

.mobile-nav__footer {
  border-top: 1px solid var(--color-border);
}
```

## HTML Structures

```html
<header class="site-header">
  <span class="site-title">SkyPane</span>
  <button type="button" id="site-nav-toggle" class="site-nav-toggle"
          aria-label="Open menu" aria-expanded="false" aria-controls="mobile-nav">
    <svg class="icon" ...><use href="#icon-hamburger"></use></svg>
  </button>
  <div id="mobile-nav" class="mobile-nav">
    <nav class="mobile-nav__nav" aria-label="Primary navigation">
      <a class="mobile-nav__link mobile-nav__link--active" href="/settings">Settings</a>
      <a class="mobile-nav__link" href="/health">Health</a>
      <a class="mobile-nav__link" href="/airlines">Airlines</a>
      <a class="mobile-nav__link" href="/history">History</a>
    </nav>
    <div class="mobile-nav__footer">
      <form class="theme-form" method="post" action="/ui-theme">...</form>
      <form method="post" action="/logout" class="logout-form">
        <button type="submit">Sign out</button>
      </form>
    </div>
  </div>
</header>
```

`companion/layout.py`'s `_mobile_nav_html()` is this markup's single write site, fed by `_nav_links()` — the same shared iteration `sidebar_nav()` (the `>=960px` vertical rendering) consumes, so the two nav renderings can never structurally diverge. `companion/static/style.css`'s `>=960px` media query is the only thing that decides which of the two copies is visible; both are always present in the DOM.

**Real implementation:** `companion/static/nav-dropdown.js` — vanilla ES5-safe JS (`"use strict"` IIFE, no `let`/`const`/arrow functions/template literals), matching this project's established no-build-tool JS convention.

## What to Avoid

- **Full-screen overlay** (sketch Variant A) — still rejected. A full context switch away from the page is overkill for a 4-item nav; it also duplicates the site title/close-button chrome unnecessarily.
- **Slide-in drawer with a dimming backdrop** (sketch Variant B) — still rejected. The backdrop-dimming pattern is a familiar native-app idiom but adds more moving parts (a backdrop element, click-outside-to-close logic) than the header-dropdown needs for a menu this small.
- **`position: absolute` on `.mobile-nav`** — this is the corrected entry: the sketch originally recommended this (with `position: relative` on the header), and it shipped that way first. It is now a recorded real defect (SUPERSEDED, see above), not a viable alternative — it can only overlay, never push. Use the in-flow `flex-basis: 100%` mechanism instead.

## Origin
Synthesized from sketch: 002 (mobile-hamburger-nav), winner: Variant C. Corrected against the shipped implementation (`companion/layout.py`, `companion/static/style.css`, `companion/static/nav-dropdown.js`) per 06.6.1 (D-06, real-device fix documented in `06.6.1-06-SUMMARY.md`), 06.6.2-05 (D-17, footer grouping), 06.6.4 (D-05, link density), and 06.6.4.1 (D-22, D-26, tab rename/retirement, still open) — quick task 260901-t00.
Source file available in: `sources/002-mobile-hamburger-nav.html` (historical artifact, byte-identical, not current-reality documentation).
