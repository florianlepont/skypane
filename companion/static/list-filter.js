/*
 * SkyPane companion service — list-filter.js.
 *
 * D-20 (06.6.3-CONTEXT.md): one generic client-side filter, reused by
 * History and Airlines. Like nav-dropdown.js/battery-trend.js before
 * it, this file has no build step, no bundler, no framework and no
 * dependency of any kind, and must stay written to an ES5-safe subset
 * (no let/const/arrow functions/template literals/backticks) so no
 * transpiler is ever needed to ship it. It is served by
 * companion/app.py's LIST_FILTER_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state — it only reads/writes attributes and text content already
 * present in the DOM.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * [data-filter-input] at all — today only History and Airlines do — so
 * the guard below is load-bearing, not defensive noise, matching the
 * project's established convention.
 */
(function () {
  "use strict";

  var input = document.querySelector("[data-filter-input]");
  if (!input) {
    return;
  }

  var countEl = document.querySelector("[data-filter-count]");
  var emptyEl = document.querySelector("[data-filter-empty]");
  var clearBtn = document.querySelector("[data-filter-clear]");

  function applyFilter() {
    // Query fresh on every input event — the two responsive
    // representations (a desktop <tr> and a mobile <li> for the same
    // row) toggle visibility via CSS display, not DOM removal, so both
    // exist simultaneously and both need filtering; a NodeList cached
    // once at load time would miss whichever the current breakpoint
    // isn't currently rendering into view at load.
    var rows = document.querySelectorAll("[data-filter-text]");
    var query = input.value.toLowerCase();
    var total = rows.length;
    var i;
    var row;
    var text;
    var group;
    var matched;
    // Every row also carries data-filter-group. History emits two DOM
    // elements per logical flight (a <tr> and a <li>) sharing the same
    // group value; Airlines emits one element per row, each its own
    // group. Counting distinct groups — not raw elements — keeps the
    // displayed "X of Y shown" accurate on pages with paired
    // representations instead of double-counting them. Each element
    // still gets its own `hidden` toggle below regardless of group,
    // since both representations need independently-correct visibility
    // across breakpoints.
    var totalGroups = {};
    var visibleGroups = {};
    var totalCount = 0;
    var visibleCount = 0;
    for (i = 0; i < total; i++) {
      row = rows[i];
      text = row.getAttribute("data-filter-text") || "";
      group = row.getAttribute("data-filter-group");
      group = "g" + (group === null ? "i" + i : group);
      matched = (query === "" || text.indexOf(query) !== -1);
      row.hidden = !matched;
      if (!totalGroups[group]) {
        totalGroups[group] = true;
        totalCount++;
      }
      if (matched && !visibleGroups[group]) {
        visibleGroups[group] = true;
        visibleCount++;
      }
    }
    if (countEl) {
      countEl.textContent = visibleCount + " of " + totalCount + " shown";
    }
    if (emptyEl) {
      emptyEl.hidden = !(query !== "" && visibleCount === 0);
    }
  }

  input.addEventListener("input", applyFilter);

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      input.value = "";
      applyFilter();
    });
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
