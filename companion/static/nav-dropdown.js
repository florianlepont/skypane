/*
 * SkyPane companion service — nav-dropdown.js.
 *
 * This is the project's second JavaScript file, and — as of this phase
 * (06.6.1) — the last one. Like companion/static/battery-trend.js before
 * it, it has no build step, no bundler, no framework and no dependency of
 * any kind. It is served by companion/app.py's NAV_SCRIPT_ROUTE,
 * mirroring the existing /static/style.css and /static/battery-trend.js
 * routes, and must stay written to an ES5-safe subset (no let/const/arrow
 * functions/template literals) so no transpiler is ever needed to ship
 * it.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state.
 *
 * This file reads and writes attributes and class names only — it never
 * touches element content and never writes markup of any kind. Because no
 * HTML-producing DOM sink exists here, no escaping function is needed,
 * for the same reason battery-trend.js's own header states.
 */
(function () {
  "use strict";

  // This script is served to every page on the site (a single cached
  // static asset, not re-emitted per page). This early return is
  // load-bearing, not defensive noise, matching battery-trend.js's own
  // documented reasoning: the login/404/preview-error page_shell() calls
  // render no dropdown at all (no request ctx to draw one from), so this
  // file must do nothing on a page whose header has not rendered one.
  var toggle = document.getElementById("site-nav-toggle");
  var panel = document.getElementById("mobile-nav");
  if (!toggle || !panel) {
    return;
  }

  // Mirrors companion/layout.py's MOBILE_NAV_OPEN_CLASS literal — the
  // three-file DOM contract guard (06.6.1-05 Task 3) reads this file from
  // disk and asserts that constant's value appears here.
  var OPEN_CLASS = "mobile-nav--open";

  function isOpen() {
    // aria-expanded is deliberately the single source of truth for the
    // open state — the CSS open-state class below is derived from it,
    // never the other way round. That is what makes it structurally
    // impossible for the visual state and the announced state to
    // diverge, which is the specific failure this pattern exists to
    // prevent.
    return toggle.getAttribute("aria-expanded") === "true";
  }

  function setOpen(next) {
    toggle.setAttribute("aria-expanded", next ? "true" : "false");
    // battery-trend.js avoided classList because it operated on an
    // SVGElement, where className is an SVGAnimatedString rather than a
    // plain string. This file operates on an HTMLElement, where classList
    // is universally available and unambiguous — a deliberate, reasoned
    // difference from the sibling file, not an inconsistency.
    if (next) {
      panel.classList.add(OPEN_CLASS);
    } else {
      panel.classList.remove(OPEN_CLASS);
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(!isOpen());
  });

  // Scoped to only act while the dropdown is open, and only for the
  // Escape key: an unconditional global handler would swallow Escape from
  // any future dialog on the page. Returning focus to the toggle is what
  // stops a keyboard user being stranded inside a panel that just
  // collapsed.
  document.addEventListener("keydown", function (evt) {
    if (!isOpen()) {
      return;
    }
    if (evt.key === "Escape") {
      setOpen(false);
      toggle.focus();
    }
  });

  // No touchstart/touchend listeners are registered here: a tap
  // synthesises a click in every mobile browser this project targets, and
  // duplicate handlers risk double-firing — battery-trend.js already
  // documents this exact reasoning; cited here rather than re-derived.

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer attribute,
  // so this file only ever runs after parsing. Do not add one later.
})();
