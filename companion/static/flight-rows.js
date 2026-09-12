/*
 * SkyPane companion service — flight-rows.js.
 *
 * D-15/R-12 (21-CONTEXT.md, 21-UI-SPEC.md §F): collapses the Flights
 * desktop table's per-row expandable detail rows. Like nav-dropdown.js/
 * battery-trend.js/theme-preview.js before it, this file has no build
 * step, no bundler, no framework and no dependency of any kind, and
 * must stay written to an ES5-safe subset (var-only declarations, no
 * arrow functions, no template-literal syntax) so no transpiler is
 * ever needed to ship it. It is served by companion/app.py's
 * FLIGHT_ROWS_SCRIPT_ROUTE, mirroring the existing /static/style.css
 * route.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state, and must never use any markup-writing DOM sink at all,
 * matching theme-preview.js's own rule. The only DOM writes this file
 * ever makes are a class toggle, an aria-expanded flip, and a button
 * label swap via the text-only content property — never a sink that
 * parses a string as HTML.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * .flight-detail-row at all — today only Flights does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns).
 *
 * No-JS floor (D-15, locked): every .flight-detail-row is rendered
 * VISIBLE by companion/pages/history_page.py, with no hidden
 * attribute and no inline style. This file is the ONLY thing that ever
 * hides one — on load, it adds flight-detail-row--collapsed to every
 * such row. This is a deliberate, narrow, per-script class-at-load
 * pattern, never a page-wide ".js" class: a page where scripts run in
 * general but THIS script specifically is blocked by a stricter CSP
 * directive than the rest of the app must still show every detail row,
 * which a page-wide ".js" class keyed elsewhere would not guarantee.
 * Do not key this file's own reveal-on-click behaviour off any class
 * other than the one it itself adds here.
 */
(function () {
  "use strict";

  var detailRows = document.querySelectorAll(".flight-detail-row");
  var toggles = document.querySelectorAll("[data-row-toggle]");
  if (!detailRows.length || !toggles.length) {
    return;
  }

  var i;
  for (i = 0; i < detailRows.length; i++) {
    detailRows[i].className += " flight-detail-row--collapsed";
  }

  function handleClick(toggle) {
    var targetId = toggle.getAttribute("aria-controls");
    var target = targetId ? document.getElementById(targetId) : null;
    if (!target) {
      return;
    }
    var collapsed = target.className.indexOf("flight-detail-row--collapsed") !== -1;
    if (collapsed) {
      target.className = target.className.replace(
        /\s*flight-detail-row--collapsed/, "");
      toggle.setAttribute("aria-expanded", "true");
      toggle.textContent = toggle.getAttribute("data-less-text") || toggle.textContent;
    } else {
      target.className += " flight-detail-row--collapsed";
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = toggle.getAttribute("data-more-text") || toggle.textContent;
    }
  }

  for (i = 0; i < toggles.length; i++) {
    (function (toggle) {
      toggle.addEventListener("click", function () {
        handleClick(toggle);
      });
    })(toggles[i]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
