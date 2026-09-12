/*
 * SkyPane companion service — list-filter.js.
 *
 * D-20 (06.6.3-CONTEXT.md): one generic client-side filter, reused by
 * History and Airlines. Like nav-dropdown.js/battery-trend.js before
 * it, this file has no build step, no bundler, no framework and no
 * dependency of any kind, and must stay written to an ES5-safe subset
 * (var-only declarations, no arrow functions, no template-literal
 * syntax) so no transpiler is ever needed to ship it. It is served by
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
 *
 * Phase 14 (14-03-PLAN.md, RESEARCH.md Pitfall 5): one more optional,
 * guarded lookup, [data-filter-set], lets an element elsewhere on the
 * page (Airlines' clickable manual-resolution summary line) set the
 * filter input's value and re-run this file's one applyFilter() — the
 * identical "set a value, re-run the filter" pattern [data-filter-clear]
 * already establishes, never a second filtering implementation. A page
 * with no [data-filter-set] element (History) is unaffected: the lookup
 * returns an empty list and no listener is attached.
 *
 * D-06 (20-11-PLAN.md Task 3): the live "X of Y shown" count text is
 * built from the [data-filter-count] element's own data-filter-count-
 * template attribute — server-rendered and translated, with both "%d"
 * placeholders left unformatted for this file to fill in at each
 * keystroke — instead of hardcoding the English words "of"/"shown"
 * here. A short, hardcoded fallback covers an un-updated caller whose
 * markup does not yet carry the attribute.
 *
 * D-15/R-12 (21-03-PLAN.md Task 3): applyFilter() also hides/shows a
 * Flights summary row's sibling .flight-detail-row (looked up by
 * id="flight-detail-{group}", never by DOM adjacency) in lockstep with
 * the summary row, so filtering out a row never leaves its detail row
 * visible underneath a hidden summary row. Guarded — a page with no
 * such element (Airlines, the mobile <li>) is unaffected.
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
  var setButtons = document.querySelectorAll("[data-filter-set]");

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
    var rawGroup;
    var group;
    var matched;
    var detail;
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
      rawGroup = row.getAttribute("data-filter-group");
      group = "g" + (rawGroup === null ? "i" + i : rawGroup);
      matched = (query === "" || text.indexOf(query) !== -1);
      row.hidden = !matched;
      // 21-03-PLAN.md Task 3 (D-15/R-12): a Flights summary row's
      // sibling .flight-detail-row is a SEPARATE element (its own <tr>,
      // not a DOM descendant of this one) sharing the same group value
      // via id="flight-detail-{group}" — looked up by id, never by DOM
      // adjacency, so a page whose rows are reordered or whose detail
      // row is missing entirely (every other [data-filter-text]
      // consumer: Airlines, the mobile <li>) is unaffected by the
      // `if (detail)` guard below.
      if (rawGroup !== null) {
        detail = document.getElementById("flight-detail-" + rawGroup);
        if (detail) {
          detail.hidden = !matched;
        }
      }
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
      var countTemplate = countEl.getAttribute("data-filter-count-template")
        || "%d of %d shown";
      countEl.textContent = countTemplate
        .replace("%d", String(visibleCount))
        .replace("%d", String(totalCount));
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

  // Phase 14 (14-03-PLAN.md): querySelectorAll (plural), not
  // querySelector — more than one summary-line-style element could
  // legitimately exist on a page, unlike the single clearBtn above.
  // Each matched element sets the filter input's value from its own
  // data-filter-set attribute and re-runs the one existing
  // applyFilter() — no second filtering path, no query-string read, no
  // persisted state, no network call, no timer.
  for (var si = 0; si < setButtons.length; si++) {
    (function (setBtn) {
      setBtn.addEventListener("click", function () {
        input.value = setBtn.getAttribute("data-filter-set") || "";
        applyFilter();
      });
    })(setButtons[si]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
