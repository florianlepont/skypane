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
 * 22-09-PLAN.md Task 1 (X5): two changes, both of which keep every
 * standing constraint above intact.
 *
 * 1. The toggle is icon-only, so this file no longer writes a visible
 *    label. It swaps the button's ACCESSIBLE NAME instead — reading the
 *    two translated, server-escaped strings out of data-show-label/
 *    data-hide-label and writing them into aria-label. Still an
 *    attribute write and a class toggle, still no markup-writing sink.
 * 2. The whole row is clickable as an enhancement: one delegated
 *    listener per summary row forwards a click to that row's own toggle
 *    button, UNLESS the click landed on something interactive in its
 *    own right (a link, a button, an input, a select, a textarea, a
 *    label or a summary). That early return is what stops this handler
 *    ever swallowing or redirecting a real control's activation
 *    (T-22-32) — including the row's own toggle button, whose own
 *    listener handles it.
 *
 *    The pointer cursor that advertises the clickable row is applied by
 *    THIS file, via the same class-at-load idiom the collapse below
 *    already uses (ROW_CLICKABLE_CLASS), never server-side: with
 *    scripts blocked a row does nothing, and a page that showed a
 *    pointer over it would be lying.
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

  // The class this file itself adds to every summary row at load — the
  // ONLY thing style.css's own `cursor: pointer` rule is keyed on.
  var ROW_CLICKABLE_CLASS = "flight-row--clickable";

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
    var name;
    if (collapsed) {
      target.className = target.className.replace(
        /\s*flight-detail-row--collapsed/, "");
      toggle.setAttribute("aria-expanded", "true");
      name = toggle.getAttribute("data-hide-label");
    } else {
      target.className += " flight-detail-row--collapsed";
      toggle.setAttribute("aria-expanded", "false");
      name = toggle.getAttribute("data-show-label");
    }
    if (name) {
      toggle.setAttribute("aria-label", name);
    }
  }

  for (i = 0; i < toggles.length; i++) {
    (function (toggle) {
      toggle.addEventListener("click", function () {
        handleClick(toggle);
      });
    })(toggles[i]);
  }

  // Returns true when `node`, or any ancestor of it up to (but not
  // including) `row`, is itself an interactive element.
  function isInteractiveTarget(node, row) {
    while (node && node !== row) {
      if (node.tagName && INTERACTIVE_TAGS[node.tagName]) {
        return true;
      }
      node = node.parentNode;
    }
    return false;
  }

  var rows = document.querySelectorAll("[data-flight-row]");
  for (i = 0; i < rows.length; i++) {
    (function (row) {
      var toggle = row.querySelector("[data-row-toggle]");
      if (!toggle) {
        return;
      }
      row.className += " " + ROW_CLICKABLE_CLASS;
      row.addEventListener("click", function (event) {
        if (isInteractiveTarget(event.target, row)) {
          return;
        }
        handleClick(toggle);
      });
    })(rows[i]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
