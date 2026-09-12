/*
 * SkyPane companion service — theme-preview.js.
 *
 * D-22..D-24 (20-CONTEXT.md): swaps the large live theme preview's
 * <img src> to match whichever chip is currently selected in the theme
 * chip grid. Like nav-dropdown.js/battery-trend.js/dirty-state.js
 * before it, this file has no build step, no bundler, no framework and
 * no dependency of any kind, and must stay written to an ES5-safe
 * subset (no let/const/arrow functions/template literals/backticks) so
 * no transpiler is ever needed to ship it. It is served by
 * companion/app.py's THEME_PREVIEW_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state, and must never use any HTML-writing DOM sink at all, matching
 * the CSP's own "no inline script, no on* attribute" rule (D-32) with
 * this file's own "no markup-building sink" rule. The only DOM write
 * this file ever makes is one <img>'s "src" property, assigned from a
 * server-rendered data-preview-src attribute — never a string this
 * file builds itself.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * .theme-live-preview at all — today only Display does (20-11) — so
 * the guard below is load-bearing, not defensive noise, matching the
 * project's established convention (nav-dropdown.js/battery-trend.js's
 * own early returns).
 *
 * No-JS floor (D-24): the live preview's initial "src" is already
 * server-rendered from the currently-saved theme when the page loads
 * (companion/pages/config_page.py's own markup, 20-11) — this file only
 * ever REPLACES that "src" in response to a later chip selection. A
 * browser with JavaScript disabled simply never runs this file at all,
 * and the preview still shows the saved theme's live render, exactly as
 * D-24 requires. Nothing here needs a degraded-mode branch.
 */
(function () {
  "use strict";

  var preview = document.querySelector(".theme-live-preview img");
  var grid = document.querySelector(".theme-chip-grid");
  if (!preview || !grid) {
    return;
  }

  // Event delegation on the grid container (matching dirty-state.js's
  // own change-event-on-the-form idiom), never one listener per chip —
  // a chip grid can carry 18 radio inputs, and this file must not
  // register 18 listeners for the same one behaviour.
  grid.addEventListener("change", function (evt) {
    var input = evt.target;
    // Guard against a "change" event bubbling from something other
    // than a radio input (defence in depth — nothing else inside a
    // .theme-chip-grid currently fires "change", but this file must
    // not assume that never changes).
    if (!input || input.type !== "radio") {
      return;
    }
    // config_page._theme_chip_grid_html() wraps each radio directly in
    // its own <label>, which is where the server renders
    // data-preview-src (20-UI-SPEC.md §H) — the input's own parentNode
    // is always that label in this exact markup shape.
    var chip = input.parentNode;
    if (!chip || !chip.getAttribute) {
      return;
    }
    var src = chip.getAttribute("data-preview-src");
    // Ignore an empty or missing attribute (D-24) — never clear or
    // blank the preview on a chip that carries no live-preview source.
    if (!src) {
      return;
    }
    preview.src = src;
  });

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
