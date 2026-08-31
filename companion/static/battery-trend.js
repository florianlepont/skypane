/*
 * SkyPane companion service — battery-trend.js.
 *
 * This is the project's only JavaScript file, and phase 06.5 is the only
 * phase that authorises adding one (06.5-RESEARCH.md: "the central research
 * question (no-JS vs. scoped-JS) resolves to: use a small, scoped, external
 * vanilla-JS file"). It has no build step, no bundler, no framework and no
 * dependency of any kind. It is served by companion/app.py's SCRIPT_ROUTE
 * (mirroring the existing /static/style.css route) and must stay written to
 * an ES5-safe subset so no transpiler is ever needed to ship it.
 *
 * This file must never introduce a network call, a timer, or any
 * persistent state — its entire job is reading attributes already present
 * in the DOM and writing one line of text in response to user input.
 *
 * D-02 (06.5-CONTEXT.md) requires that hovering or tapping a chart point
 * reveal its exact reading and timestamp. The revealed reading is written
 * through the readout element's `textContent` property, specifically so
 * that no HTML-writing DOM sink is ever needed here — which is why this
 * file needs no escaping function at all (06.5-RESEARCH.md, Security
 * Domain, ASVS V5).
 */
(function () {
  "use strict";

  // This script is served to every page on the site (it is a single
  // cached static asset, not re-emitted per page), and it ships one wave
  // ahead of the markup that references it (plan 06.5-02). Most pages have
  // no readout element at all, so this early return is load-bearing, not
  // defensive noise: without it this file would need to special-case
  // "page has no chart" instead of just doing nothing.
  var readout = document.getElementById("battery-readout");
  if (!readout) {
    return;
  }

  var points = document.querySelectorAll(".sparkline-hit");
  if (points.length === 0) {
    return;
  }

  function reveal(point) {
    // Use getAttribute(), not the `dataset` property: 06.5-RESEARCH.md's
    // Pattern 1 sketch used `dataset`, but `dataset` on SVGElement (as
    // opposed to HTMLElement) has a narrower support floor than
    // getAttribute(), which is universal. Deliberate deviation from the
    // research sketch, kept for that one reason.
    var mv = point.getAttribute("data-mv");
    var ts = point.getAttribute("data-ts");
    if (mv === null || ts === null) {
      return;
    }
    readout.textContent = mv + " mV — " + ts;

    // Mark exactly one point as active: the one just revealed, toggled on;
    // every other point, toggled off.
    for (var j = 0; j < points.length; j++) {
      _toggleActive(points[j], points[j] === point);
    }
  }

  function _toggleActive(el, isActive) {
    var cls = " sparkline-hit--active";
    var current = " " + el.className + " ";
    var has = current.indexOf(" sparkline-hit--active ") !== -1;
    if (isActive && !has) {
      el.className = el.className + cls;
    } else if (!isActive && has) {
      el.className = current
        .split(" sparkline-hit--active ").join(" ")
        .replace(/^\s+|\s+$/g, "");
    }
  }

  // D-13/UXA-11: roving tabindex. companion/pages/health_page.py's
  // battery_sparkline_svg() emits exactly one hit target with
  // tabindex="0" (the chronologically-latest point, rightmost in
  // `points`) and tabindex="-1" on every other one, so Tab visits the
  // chart exactly once instead of once per reading. moveFocusTo()
  // clamps to [0, points.length - 1] — it never wraps at either end —
  // sets every point's tabindex attribute via setAttribute() (never the
  // dataset/property form, matching this file's own getAttribute()-not-
  // dataset discipline), then calls .focus() on the newly-current
  // point. .focus() fires the "focus" listener registered below, which
  // already calls reveal(), so no duplicate reveal() call is needed
  // here.
  function moveFocusTo(index) {
    if (index < 0) {
      index = 0;
    } else if (index > points.length - 1) {
      index = points.length - 1;
    }
    for (var k = 0; k < points.length; k++) {
      points[k].setAttribute("tabindex", k === index ? "0" : "-1");
    }
    points[index].focus();
  }

  // Classic indexed for loop with a per-iteration closure (an inner IIFE),
  // so the ES5-safe subset holds and no let/const/arrow function is
  // required.
  for (var i = 0; i < points.length; i++) {
    (function (point) {
      point.addEventListener("click", function () {
        // The tap half of D-02: a tap synthesises a click in every mobile
        // browser this project targets, so no separate touch-start /
        // touch-end listeners are registered here (06.5-RESEARCH.md,
        // Anti-Patterns — they would duplicate this logic and risk
        // double-firing).
        reveal(point);
      });
      point.addEventListener("mouseenter", function () {
        // The desktop-hover half of D-02, giving mouse users the same
        // persistent readout a tap gives touch users.
        reveal(point);
      });
      point.addEventListener("focus", function () {
        // Keyboard traversal reveals the reading without needing a
        // separate key press.
        reveal(point);
      });
      point.addEventListener("keydown", function (evt) {
        if (evt.key === "Enter" || evt.key === " ") {
          evt.preventDefault();
          reveal(point);
        }
      });
      // D-13/UXA-11: a separate keydown listener (not merged into the
      // Enter/Space listener above) for roving-tabindex chart
      // navigation. Array.prototype.indexOf.call() is used rather than
      // an ES6 array-conversion helper (ES5-safe against a NodeList —
      // no conversion is needed, just an index lookup).
      point.addEventListener("keydown", function (evt) {
        var currentIndex = Array.prototype.indexOf.call(points, point);
        if (evt.key === "ArrowRight" || evt.key === "ArrowDown") {
          evt.preventDefault();
          moveFocusTo(currentIndex + 1);
        } else if (evt.key === "ArrowLeft" || evt.key === "ArrowUp") {
          evt.preventDefault();
          moveFocusTo(currentIndex - 1);
        } else if (evt.key === "Home") {
          evt.preventDefault();
          moveFocusTo(0);
        } else if (evt.key === "End") {
          evt.preventDefault();
          moveFocusTo(points.length - 1);
        }
      });
    })(points[i]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag plan 06.5-02
  // emits carries `defer`, so this file only ever runs after parsing.
  // Do not add one later.
})();
