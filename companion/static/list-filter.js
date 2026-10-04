/*
 * SkyPane companion service — list-filter.js.
 *
 * One generic client-side filter, reused by Flights, Airlines and
 * Health's unresolved-prefix list. No
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
  var clearButtons = document.querySelectorAll("[data-filter-clear]");
  var setButtons = document.querySelectorAll("[data-filter-set]");
  // Optional segmented chips: radios whose value is a row's
  // data-filter-kind ("" is every row). Absent on a plain search bar.
  var chipInputs = document.querySelectorAll("[data-filter-chip]");
  var CHIP_COUNT_SELECTOR = "[data-filter-chip-count]";
  var ZERO_CLASS = "is-zero";
  // Set on the bar while the search holds text, so the collapsed search
  // stays open without a :has() selector.
  var ACTIVE_ATTR = "data-filter-active";
  var bar = input.closest ? input.closest(".filter-bar") : null;

  function selectedKind() {
    for (var k = 0; k < chipInputs.length; k++) {
      if (chipInputs[k].checked) {
        return chipInputs[k].value;
      }
    }
    return "";
  }

  // Distinct-group tally for one chip: rows matching the query and the
  // chip's kind, each logical flight counted once.
  function tallyChip(rows, query, kind) {
    var seen = {};
    var n = 0;
    for (var r = 0; r < rows.length; r++) {
      var rowKind = rows[r].getAttribute("data-filter-kind") || "";
      var text = rows[r].getAttribute("data-filter-text") || "";
      if (kind !== "" && rowKind !== kind) {
        continue;
      }
      if (query !== "" && text.indexOf(query) === -1) {
        continue;
      }
      var rg = rows[r].getAttribute("data-filter-group");
      var key = "g" + (rg === null ? "i" + r : rg);
      if (!seen[key]) {
        seen[key] = true;
        n++;
      }
    }
    return n;
  }

  // A day header with no visible row under it would read as an empty
  // section: hide it until a row of its day shows again. Walks the
  // siblings up to the next header; a Flights detail row (no
  // data-filter-text) between rows is skipped.
  function syncDayHeaders() {
    var heads = document.querySelectorAll("[data-filter-day]");
    for (var h = 0; h < heads.length; h++) {
      var sib = heads[h].nextElementSibling;
      var any = false;
      while (sib && !sib.hasAttribute("data-filter-day")) {
        if (sib.hasAttribute("data-filter-text") && !sib.hidden) {
          any = true;
          break;
        }
        sib = sib.nextElementSibling;
      }
      heads[h].hidden = !any;
    }
  }

  function paintChips(rows, query) {
    for (var c = 0; c < chipInputs.length; c++) {
      var chip = chipInputs[c];
      var label = chip.closest ? chip.closest("label") : chip.parentNode;
      var countEl = label ? label.querySelector(CHIP_COUNT_SELECTOR) : null;
      var n = tallyChip(rows, query, chip.value);
      if (countEl) {
        countEl.textContent = String(n);
      }
      if (label && label.classList) {
        if (n === 0) {
          label.classList.add(ZERO_CLASS);
        } else {
          label.classList.remove(ZERO_CLASS);
        }
      }
    }
  }

  function applyFilter() {
    // Query fresh on every input event: the desktop <tr> and mobile
    // <li> for the same row both exist simultaneously (CSS toggles
    // which is visible), so a NodeList cached at load would miss
    // whichever the current breakpoint is not rendering.
    var rows = document.querySelectorAll("[data-filter-text]");
    var query = input.value.toLowerCase();
    var kind = selectedKind();
    var rowKind;
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
      rowKind = row.getAttribute("data-filter-kind") || "";
      matched = (query === "" || text.indexOf(query) !== -1)
        && (kind === "" || rowKind === kind);
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
        || "# of # shown";
      var countText = countTemplate
        .replace("#", String(visibleCount))
        .replace("#", String(totalCount));
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
    if (chipInputs.length) {
      paintChips(rows, query);
    }
    syncDayHeaders();
    if (bar) {
      if (query !== "") {
        bar.setAttribute(ACTIVE_ATTR, "");
      } else {
        bar.removeAttribute(ACTIVE_ATTR);
      }
    }
    if (emptyEl) {
      emptyEl.hidden = !((query !== "" || kind !== "") && visibleCount === 0);
    }
  }

  input.addEventListener("input", applyFilter);

  for (var ci = 0; ci < chipInputs.length; ci++) {
    chipInputs[ci].addEventListener("change", applyFilter);
  }

  // querySelectorAll: the inline clear and the empty state's own Clear
  // button are both [data-filter-clear]. The inline one clears the
  // search text; the empty state's (also [data-filter-clear-all]) resets
  // the chips to "All" too, since a chip can be what emptied the list.
  function resetAllChips() {
    for (var rc = 0; rc < chipInputs.length; rc++) {
      chipInputs[rc].checked = (chipInputs[rc].value === "");
    }
  }
  for (var bi = 0; bi < clearButtons.length; bi++) {
    (function (clearBtn) {
      clearBtn.addEventListener("click", function () {
        input.value = "";
        var clearAll = clearBtn.hasAttribute("data-filter-clear-all");
        if (clearAll) {
          resetAllChips();
        }
        applyFilter();
        // Keep the keyboard out of the way after the empty state's reset.
        if (!clearAll) {
          input.focus();
        }
      });
    })(clearButtons[bi]);
  }

  // querySelectorAll (plural): more than one summary-line-style
  // element could legitimately exist on a page.
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
