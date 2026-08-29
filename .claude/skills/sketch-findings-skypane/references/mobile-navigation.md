# Mobile Navigation

## Design Decisions

**Winning variant: Sketch 002, Variant C ("Header dropdown")**

Replaces the current horizontal-scroll `.nav-bar` strip (below 960px) — real-device testing during 06.5-03 found it hides most tabs behind an undiscoverable swipe, even after the 06.3 crush-bug fix (commit `b90ed88`).

- **Trigger:** a hamburger icon button (☰, 24×24 inline SVG, three horizontal lines) placed where the theme-picker/nav-bar used to sit in the header, right-aligned.
- **Open behavior:** tapping the hamburger expands a panel directly below the header, **pushing page content down** rather than covering it (no backdrop, no full-screen takeover). Implemented via `max-height` transition on the dropdown container (`max-height: 0` → `max-height: 420px`, `overflow: hidden`, `transition: max-height .22s ease`) rather than `display`/`height:auto` (which can't transition).
- **Content inside the dropdown:** the 5 nav links (Config/Health/Airlines/History/Preview) stacked vertically, each a real link with 44px+ min-height tap target, THEN the theme picker (Auto/Light/Dark) below the nav links as a row of 3 buttons — this is where the theme picker relocates to once it's no longer squeezed into the header row (the 06.3 crush-bug's root cause).
- **Close behavior:** tapping the hamburger again toggles it closed (same button, same click handler, checks current state). Escape key also closes it (global keydown listener).
- **Accessibility:** hamburger button carries `aria-expanded`, kept in sync on both open and close.

## CSS Patterns

```css
.dropdown{
  position:absolute; top:100%; left:0; right:0;
  background:var(--color-dominant);
  z-index:20;
  box-shadow:0 8px 20px rgba(0,0,0,0.1);
  border-bottom-left-radius:var(--radius-card);
  border-bottom-right-radius:var(--radius-card);
  max-height:0; overflow:hidden;
  transition:max-height .22s ease;
}
.dropdown.open{ max-height:420px; }
.dropdown__nav{ display:flex; flex-direction:column; padding:var(--space-sm); }
```

The header needs `position:relative` (or the dropdown's containing block won't be the header) — see sketch source for the full header wrapper.

## HTML Structures

```html
<header class="site-header" style="position:relative">
  <span class="site-title">SkyPane</span>
  <button class="hamburger-btn" aria-label="Open menu" aria-expanded="false"
          onclick="/* toggle .open on the dropdown + sync aria-expanded */">
    <svg><use href="#icon-hamburger"/></svg>
  </button>
  <div class="dropdown" id="mobile-nav-dropdown">
    <nav class="dropdown__nav">
      <a class="nav-link" href="/config">Config</a>
      <a class="nav-link nav-link--active" href="/health">Health</a>
      <!-- ... -->
    </nav>
    <div class="theme-row">
      <button class="theme-btn theme-btn--active">Auto</button>
      <button class="theme-btn">Light</button>
      <button class="theme-btn">Dark</button>
    </div>
  </div>
</header>
```

In the real `companion/layout.py`, this replaces `_nav_html()`'s horizontal `.nav-bar` rendering below 960px — the desktop sidebar nav (`sidebar_nav()`, >=960px) is untouched by this change. The existing dual-copy pattern (both nav renderings always in the DOM, CSS decides visibility) should extend naturally: the dropdown becomes a third rendering mode for the <960px range specifically, not a replacement for the sidebar.

**Real implementation note:** this needs actual JS (not just CSS `:checkbox-hack` or `:target`) since the toggle also needs to sync `aria-expanded` — a small addition to whatever inline `<script>` pattern the project already uses (see `companion/static/battery-trend.js` from Phase 06.5 for the project's established vanilla-JS, `"use strict"`, IIFE style).

## What to Avoid

- **Variant A ("Full-screen overlay")** — rejected. Full context switch away from the page felt like overkill for a 5-item nav; also duplicates the site title/close-button chrome unnecessarily.
- **Variant B ("Slide-in drawer")** — rejected. The backdrop-dimming pattern is a familiar native-app idiom but adds more moving parts (backdrop element, click-outside-to-close logic) than the header-dropdown needs for a menu this small.
- Do not use `position:fixed` for the dropdown — it needs to sit in normal flow relative to the header so it pushes content down (the whole point of picking C over A/B). `position:absolute` on the dropdown plus `position:relative` on the header is correct and sufficient here (unlike `position:fixed`, `absolute` IS contained by the nearest positioned ancestor without needing a `transform`/`filter` trick).

## Origin
Synthesized from sketch: 002 (mobile-hamburger-nav), winner: Variant C
Source file available in: `sources/002-mobile-hamburger-nav.html`
