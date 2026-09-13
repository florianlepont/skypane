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
 *
 * 23-08-PLAN.md Task 1 (D7/CFG-37): Flights joined companion/static/
 * freshness.js's refresh loop, which replaces the row list and the
 * count element from a second fetch of the same page. Two consequences,
 * both handled below and neither optional:
 *
 * 1. THE COUNT ELEMENT IS LOOKED UP FRESH, inside applyFilter(),
 *    instead of once at load. A reference captured at load is detached
 *    the moment the first swap replaces that span, and every keystroke
 *    after it would update a node no longer in the document — the count
 *    would simply freeze, with nothing anywhere reporting it. This is
 *    also what lets the count BE a swap region at all: the swap
 *    registry in companion/layout.py excludes every element this file
 *    still captures at load (the input, Clear, the empty-state block
 *    and the set hooks) for exactly the reason this paragraph describes,
 *    and the count is the one that stepped out of that category.
 *
 * 2. THE FILTER IS RE-APPLIED AFTER A SWAP. The server renders the list
 *    UNFILTERED — it knows nothing about a query typed into this page —
 *    so a refresh arriving while a query is in the box would hand back
 *    every row, visible, with a count to match, silently undoing what
 *    the reader asked for. Re-running the one existing applyFilter()
 *    when the loop announces a swap is the whole fix; there is still
 *    exactly one filtering implementation in this file.
 *
 * Neither adds a network call, a timer or any persisted state, and the
 * count's TEXT is still built the one way it always was, from the
 * server-rendered translated template.
 */
(function () {
  "use strict";

  var input = document.querySelector("[data-filter-input]");
  if (!input) {
    return;
  }

  // 23-08-PLAN.md Task 1: deliberately NOT captured here, unlike its
  // three siblings below — see this file's own header for why the
  // count is the one element that had to stop being cached.
  //
  // The attribute name is the literal and the selector is built from
  // it, rather than the bracketed form being written out: that is this
  // codebase's own JS idiom (freshness.js's PENDING_ATTR/
  // PENDING_SELECTOR pair, and FADE_IMAGE_CLASS/FADE_IMAGE_SELECTOR
  // beside it), and companion/test_i18n.py's Check 6 reads a bracketed
  // lowercase string in an ALL-CAPS JS constant as untranslated
  // user-facing copy. It is a wire name, not copy, and the idiom says so.
  var COUNT_ATTR = "data-filter-count";
  var COUNT_SELECTOR = "[" + COUNT_ATTR + "]";
  // companion/static/freshness.js's post-swap announcement. Listened
  // for, never dispatched from here.
  var SWAPPED_EVENT = "skypane-regions-swapped";
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
    var countEl = document.querySelector(COUNT_SELECTOR);
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

  // 23-08-PLAN.md Task 1: re-apply the one existing filter after the
  // refresh loop has swapped the list in. Registered on document, after
  // the [data-filter-input] guard above, so a page with no filter never
  // listens at all.
  document.addEventListener(SWAPPED_EVENT, applyFilter);

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
