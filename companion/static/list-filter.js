/*
 * SkyPane companion service — list-filter.js.
 *
 * One generic client-side filter, reused by History and Airlines. No
 * build step, ES5-safe subset. Inert on a page with no
 * [data-filter-input]. Served by companion/app.py's
 * LIST_FILTER_SCRIPT_ROUTE. No network call, timer, or persistent
 * state: only DOM attributes/text. The count text uses the
 * [data-filter-count] element's own server-rendered, translated
 * template. Flights joined freshness.js's refresh loop, so the count
 * element is looked up fresh each run rather than cached, and the
 * filter re-applies after every swap since the server renders the list
 * unfiltered.
 */
(function () {
  "use strict";

  var input = document.querySelector("[data-filter-input]");
  if (!input) {
    return;
  }

  // Deliberately not captured here, unlike its siblings below — the
  // count is the one element that must be looked up fresh (see header).
  var COUNT_ATTR = "data-filter-count";
  var COUNT_SELECTOR = "[" + COUNT_ATTR + "]";

  // The stylesheet's existing changed-value animation class. Applied to
  // the element, never to its number: text is written before the
  // class, so the displayed value is correct at the animation's first
  // frame.
  var COUNT_CHANGED_CLASS = "is-fading-in";
  // freshness.js's post-swap announcement. Listened for, never
  // dispatched from here.
  var SWAPPED_EVENT = "skypane-regions-swapped";
  var emptyEl = document.querySelector("[data-filter-empty]");
  var clearBtn = document.querySelector("[data-filter-clear]");
  var setButtons = document.querySelectorAll("[data-filter-set]");

  function applyFilter() {
    // Query fresh on every input event: the desktop <tr> and mobile
    // <li> for the same row both exist simultaneously (CSS toggles
    // which is visible), so a NodeList cached at load would miss
    // whichever the current breakpoint is not rendering.
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
    // Every row also carries data-filter-group: History emits a <tr>
    // and a <li> per logical flight sharing one group value. Counting
    // distinct groups, not raw elements, keeps "X of Y shown" accurate
    // instead of double-counting the paired representations.
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
      // A Flights summary row's sibling .flight-detail-row is a
      // separate element sharing the same group value via
      // id="flight-detail-{group}", looked up by id rather than DOM
      // adjacency; a page with none (Airlines, the mobile <li>) is
      // unaffected by the guard below.
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
      var countText = countTemplate
        .replace("%d", String(visibleCount))
        .replace("%d", String(totalCount));
      // Only on a real change: this runs on every keystroke and every
      // swap, and animating an unchanged sentence would be motion with
      // no information.
      if (countEl.textContent !== countText) {
        countEl.textContent = countText;
        if (countEl.classList) {
          // Removed, reflowed, re-added: reading a layout property in
          // between forces the removal to take effect before the
          // re-add, which a bare remove+add would otherwise coalesce.
          countEl.classList.remove(COUNT_CHANGED_CLASS);
          void countEl.offsetWidth;
          countEl.classList.add(COUNT_CHANGED_CLASS);
        }
      }
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

  // querySelectorAll (plural): more than one summary-line-style
  // element could legitimately exist on a page, unlike clearBtn above.
  for (var si = 0; si < setButtons.length; si++) {
    (function (setBtn) {
      setBtn.addEventListener("click", function () {
        input.value = setBtn.getAttribute("data-filter-set") || "";
        applyFilter();
      });
    })(setButtons[si]);
  }

  // Re-apply the filter after the refresh loop has swapped the list in.
  document.addEventListener(SWAPPED_EVENT, applyFilter);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
