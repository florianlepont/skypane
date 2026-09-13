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
 * label swap through attributes — never a sink that parses a string as
 * HTML.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * .flight-detail-row at all — today only Flights does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns).
 *
 * 22-09-PLAN.md Task 1 (X5): two changes, both of which keep every
 * standing constraint above intact.
 *
 * 1. The toggle is icon-only, so this file no longer writes a visible
 *    label. It swaps the button's ACCESSIBLE NAME instead — reading the
 *    two translated, server-escaped strings out of data-show-label/
 *    data-hide-label and writing them into aria-label. Still an
 *    attribute write and a class toggle, still no markup-writing sink.
 * 2. The whole row is clickable as an enhancement: a click is forwarded
 *    to that row's own toggle button, UNLESS the click landed on
 *    something interactive in its own right (a link, a button, an
 *    input, a select, a textarea, a label or a summary). That early
 *    return is what stops this handler ever swallowing or redirecting a
 *    real control's activation (T-22-32) — including the row's own
 *    toggle button, whose own branch handles it.
 *
 *    The pointer cursor that advertises the clickable row is applied by
 *    THIS file, via the same class-at-load idiom the collapse below
 *    already uses (ROW_CLICKABLE_CLASS), never server-side: with
 *    scripts blocked a row does nothing, and a page that showed a
 *    pointer over it would be lying.
 *
 * --- 23-08-PLAN.md Task 1 (D7/CFG-37): the list moves under this file
 * --- now, and that changes two things ---------------------------------
 *
 * Flights joined companion/static/freshness.js's refresh loop, so the
 * table and the card list are REPLACED WHOLESALE from a second fetch of
 * the same page, several times an hour, while this file is running.
 * Everything below that used to happen once, at load, had to stop being
 * a one-time act:
 *
 * 1. THE LISTENERS ARE DELEGATED. One click listener on document,
 *    walking up from the click target, instead of one listener per
 *    toggle and one per row bound at load. A per-element listener
 *    binds to a NODE, and every swapped-in row is a different node —
 *    the rows would still be there, still look right, and do nothing at
 *    all. Delegation covers the rows that exist now and the rows that
 *    arrive later, with no re-binding pass to forget.
 *
 * 2. THE COLLAPSED STATE IS RE-DERIVED AFTER EVERY SWAP, from this
 *    file's own record of which rows are open, keyed by the row's
 *    stable EVENT identity (layout.REFRESH_ROW_ID_ATTR). The server
 *    renders every detail row VISIBLE and carries no open/closed state
 *    at all — that is the no-JS floor below, and it is not negotiable —
 *    so a swap arrives with every row expanded and every toggle reading
 *    aria-expanded="false". Without the re-derive, one refresh would
 *    silently unfold the whole table.
 *
 *    Keyed by EVENT identity rather than by the flight-detail-N id,
 *    deliberately: that id is the row's POSITION in one render, and a
 *    new detection arriving at the top renumbers every row below it. A
 *    position-keyed record would reopen the wrong row — the one that
 *    inherited the number — which is worse than closing it.
 *
 *    The open-row record is in-memory, per page view, and dies with the
 *    document. The standing "no persistent state" constraint above is
 *    about storage that outlives the page (cookies, localStorage, a
 *    server round trip); this is the same kind of state the DOM class
 *    it mirrors already is.
 *
 * The hook is companion/static/freshness.js's own post-swap
 * announcement (SWAPPED_EVENT below). This file asks for nothing and is
 * told nothing about what changed: it simply re-derives what it owns.
 *
 * No-JS floor (D-15, locked): every .flight-detail-row is rendered
 * VISIBLE by companion/pages/history_page.py, with no hidden
 * attribute and no inline style. This file is the ONLY thing that ever
 * hides one — it adds flight-detail-row--collapsed to every such row.
 * This is a deliberate, narrow, per-script class-at-load pattern, never
 * a page-wide ".js" class: a page where scripts run in general but THIS
 * script specifically is blocked by a stricter CSP directive than the
 * rest of the app must still show every detail row, which a page-wide
 * ".js" class keyed elsewhere would not guarantee. Do not key this
 * file's own reveal-on-click behaviour off any class other than the
 * ones it itself adds here.
 */
(function () {
  "use strict";

  // The class this file itself adds to every summary row — the ONLY
  // thing style.css's own pointer-cursor rule is keyed on.
  var ROW_CLICKABLE_CLASS = "flight-row--clickable";

  // The collapse itself. Added by this file and by nothing else.
  var COLLAPSED_CLASS = "flight-detail-row--collapsed";
  var COLLAPSED_PATTERN = /\s*flight-detail-row--collapsed/g;

  // 23-08-PLAN.md Task 1: the class this file adds to the document
  // element once, on load, as the ONE signal that this script is live.
  // style.css keys the detail row's height animation on it, and that is
  // the whole reason it exists: with scripts blocked every detail row is
  // already open and must simply BE open, with no transition and no
  // @starting-style entry animation running over a page nobody is
  // interacting with.
  var LIVE_CLASS = "flight-rows-live";

  // companion/layout.py's REFRESH_ROW_ID_ATTR — the row's stable EVENT
  // identity, the key the open-row record below is written against.
  // Duplicated rather than imported, like every cross-file literal in
  // these scripts, and pinned equal by companion/test_status_pages.py.
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

  // ONE listener, on document, for both behaviours. The walk up from
  // the click target answers both questions in a single pass: did this
  // land on a toggle, and which summary row is it inside. A click on
  // the toggle takes the first branch and toggles exactly once — the
  // whole-row branch is never reached for it, which is what the "a
  // click on the toggle toggles exactly ONCE" contract needs.
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

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
