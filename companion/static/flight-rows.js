/*
 * SkyPane companion service — flight-rows.js.
 *
 * Collapses the Flights desktop table's per-row expandable detail
 * rows, and makes the whole summary row clickable as an enhancement
 * over its toggle button. No build step, ES5-safe subset. Inert on a
 * page with no .flight-detail-row (today only Flights). Served by
 * companion/app.py's FLIGHT_ROWS_SCRIPT_ROUTE. No markup-writing DOM
 * sink: the only writes are a class toggle, an aria-expanded flip, and
 * an aria-label swap.
 *
 * No-JS floor: every .flight-detail-row is rendered visible by
 * companion/pages/history_page.py, with no hidden attribute or inline
 * style. This file is the only thing that ever collapses one, via a
 * class it adds itself at load — never a page-wide ".js" class, so a
 * page where this specific script is blocked by a stricter CSP
 * directive still shows every row.
 *
 * Flights joined freshness.js's refresh loop, so the table is replaced
 * wholesale from a second fetch several times an hour. Listeners are
 * therefore delegated on document rather than bound per element (a
 * per-element listener would not survive a swap), and the collapsed
 * state is re-derived after every swap from this file's own in-memory
 * record of open rows, keyed by the row's stable event identity
 * (layout.REFRESH_ROW_ID_ATTR) rather than its position, since a new
 * detection at the top renumbers every row below it.
 */
(function () {
  "use strict";

  // The class this file adds to every summary row — the only thing
  // style.css's own pointer-cursor rule is keyed on.
  var ROW_CLICKABLE_CLASS = "flight-row--clickable";

  // The collapse itself. Added by this file and by nothing else.
  var COLLAPSED_CLASS = "flight-detail-row--collapsed";
  var COLLAPSED_PATTERN = /\s*flight-detail-row--collapsed/g;

  // Added to the document element once, on load, as the one signal
  // this script is live; style.css keys the detail row's height
  // animation on it, so a scripts-blocked page (where every row is
  // already open) gets no transition and no entry animation.
  var LIVE_CLASS = "flight-rows-live";

  // companion/layout.py's REFRESH_ROW_ID_ATTR, the row's stable event
  // identity, pinned equal by companion/test_status_pages.py.
  var ROW_ID_ATTR = "data-flight-id";

  // companion/static/freshness.js's post-swap announcement. Listened
  // for, never dispatched from here.
  var SWAPPED_EVENT = "skypane-regions-swapped";

  // Tag names that are interactive in their own right. A click that
  // landed on one of these (or inside one, e.g. the <span> inside the
  // toggle button) is that control's own activation and must never be
  // re-routed into a row expand/collapse.
  var INTERACTIVE_TAGS = {
    A: true, BUTTON: true, INPUT: true, SELECT: true,
    TEXTAREA: true, LABEL: true, SUMMARY: true
  };

  var detailRows = document.querySelectorAll(".flight-detail-row");
  var toggles = document.querySelectorAll("[data-row-toggle]");
  if (!detailRows.length || !toggles.length) {
    return;
  }

  // The rows this page view has open, by event identity. Empty at load:
  // every detail row starts collapsed, which is what syncRows() below
  // derives from an empty record on its very first call.
  var openRows = {};

  function detailFor(toggle) {
    var targetId = toggle.getAttribute("aria-controls");
    return targetId ? document.getElementById(targetId) : null;
  }

  // The one place the open/closed state is written. Both directions and
  // both elements, so a caller can never move one and forget the other:
  // the row's class, the button's aria-expanded, and the button's
  // accessible name, which is the only name it has (the control is
  // icon-only).
  function applyState(toggle, detail, open) {
    var name;
    if (open) {
      detail.className = detail.className.replace(COLLAPSED_PATTERN, "");
      toggle.setAttribute("aria-expanded", "true");
      name = toggle.getAttribute("data-hide-label");
    } else {
      if (detail.className.indexOf(COLLAPSED_CLASS) === -1) {
        detail.className += " " + COLLAPSED_CLASS;
      }
      toggle.setAttribute("aria-expanded", "false");
      name = toggle.getAttribute("data-show-label");
    }
    if (name) {
      toggle.setAttribute("aria-label", name);
    }
  }

  function handleClick(toggle) {
    var detail = detailFor(toggle);
    if (!detail) {
      return;
    }
    // It was collapsed, so this activation opens it.
    var open = detail.className.indexOf(COLLAPSED_CLASS) !== -1;
    var rowId = detail.getAttribute(ROW_ID_ATTR);
    if (rowId) {
      if (open) {
        openRows[rowId] = true;
      } else {
        delete openRows[rowId];
      }
    }
    applyState(toggle, detail, open);
  }

  // Idempotent, and called both at load and after every swap. At load
  // it is what collapses a server-rendered page; after a swap it is
  // what stops one unfolding the whole table.
  function syncRows() {
    var current = document.querySelectorAll("[data-row-toggle]");
    var i;
    for (i = 0; i < current.length; i++) {
      var toggle = current[i];
      var detail = detailFor(toggle);
      if (!detail) {
        continue;
      }
      var rowId = detail.getAttribute(ROW_ID_ATTR);
      applyState(toggle, detail, !!(rowId
        && Object.prototype.hasOwnProperty.call(openRows, rowId)));
    }
    var rows = document.querySelectorAll("[data-flight-row]");
    for (i = 0; i < rows.length; i++) {
      if (rows[i].className.indexOf(ROW_CLICKABLE_CLASS) === -1) {
        rows[i].className += " " + ROW_CLICKABLE_CLASS;
      }
    }
  }

  // Returns true when the clicked node, or any ancestor of it up to
  // (but not including) the row, is itself an interactive element.
  function isInteractiveTarget(node, row) {
    while (node && node !== row) {
      if (node.tagName && INTERACTIVE_TAGS[node.tagName]) {
        return true;
      }
      node = node.parentNode;
    }
    return false;
  }

  if (document.documentElement) {
    document.documentElement.className += " " + LIVE_CLASS;
  }
  syncRows();

  // One listener, on document, for both behaviours: the walk up from
  // the click target answers both "was this a toggle" and "which row"
  // in a single pass, so a click on the toggle takes the first branch
  // and never also reaches the whole-row branch.
  document.addEventListener("click", function (event) {
    var node = event.target;
    var toggle = null;
    var row = null;
    while (node && node.getAttribute) {
      if (!toggle && node.getAttribute("data-row-toggle") !== null) {
        toggle = node;
      }
      if (node.getAttribute("data-flight-row") !== null) {
        row = node;
        break;
      }
      node = node.parentNode;
    }
    if (toggle) {
      handleClick(toggle);
      return;
    }
    if (!row || isInteractiveTarget(event.target, row)) {
      return;
    }
    var rowToggle = row.querySelector("[data-row-toggle]");
    if (rowToggle) {
      handleClick(rowToggle);
    }
  });

  document.addEventListener(SWAPPED_EVENT, syncRows);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
