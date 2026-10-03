/*
 * SkyPane companion service — battery-trend.js.
 *
 * Reveals a battery sparkline point's exact reading and timestamp on
 * hover, tap, or keyboard focus, and drives roving-tabindex navigation
 * across the chart. No build step, ES5-safe subset. Served by
 * companion/app.py's SCRIPT_ROUTE. Never a network call, a timer, or
 * persistent state: reads attributes already in the DOM and writes
 * text via textContent, never an HTML-writing sink.
 *
 * Also switches the chart between its server-rendered Percentage and
 * Voltage views: both are already in the DOM, the script only shows one
 * and hides the other, and never converts a unit itself.
 */
(function () {
  "use strict";

  // Most pages have no readout element at all.
  var readout = document.getElementById("battery-readout");
  if (!readout) {
    return;
  }

  // Both spans must be present for the two-span write path below; if
  // either is missing, reveal() falls through to a single-string write.
  var readoutValue = readout.querySelector(".battery-readout__value");
  var readoutDetail = readout.querySelector(".battery-readout__detail");

  var allPoints = document.querySelectorAll(".sparkline-hit");
  if (allPoints.length === 0) {
    return;
  }

  // The hit targets of the view currently shown; reassigned on a unit
  // switch. A hidden view's targets are never in the tab order.
  var points = allPoints;
  var views = document.querySelectorAll(".battery-chart__view");
  var activeIndex = -1;

  function viewPoints(view) {
    return view.querySelectorAll(".sparkline-hit");
  }

  if (views.length > 0) {
    for (var v = 0; v < views.length; v++) {
      if (!views[v].hasAttribute("hidden")) {
        points = viewPoints(views[v]);
      }
    }
  }

  function reveal(point) {
    // getAttribute(), not the dataset property: dataset on an
    // SVGElement has a narrower support floor than getAttribute(),
    // which is universal.
    var mv = point.getAttribute("data-mv");
    var ts = point.getAttribute("data-ts");
    var when = point.getAttribute("data-when");
    if (mv === null || ts === null) {
      return;
    }
    // The server humanises the detail once (health_page.py's
    // _battery_reading_parts()) and shares it through data-when; this
    // function reads it back rather than reformatting a timestamp
    // itself, so it needs no date-formatting logic of its own. `when`
    // is a full local timestamp, used for both the visible text and
    // `title`, so a user never sees the raw ISO ts.
    // data-reading carries the server-computed text for a non-voltage
    // view (the percentage estimate); voltage points have none.
    var reading = point.getAttribute("data-reading");
    var valueText = reading !== null ? reading : mv + " mV";
    if (when !== null && readoutValue && readoutDetail) {
      readoutValue.textContent = valueText;
      readoutDetail.textContent = " — " + when;
      readoutDetail.setAttribute("title", when);
    } else {
      // A missing data-when attribute or span (this script can ship one
      // wave ahead of the markup that references it) degrades to the
      // bare value with no time at all, never the raw ISO ts.
      readout.textContent = valueText;
    }

    // Mark exactly one point as active: the one just revealed, toggled on;
    // every other point, toggled off.
    for (var j = 0; j < points.length; j++) {
      _toggleActive(points[j], points[j] === point);
    }
    activeIndex = Array.prototype.indexOf.call(points, point);
  }

  function _toggleActive(el, isActive) {
    // These hit targets are SVG <circle> elements, whose className is a
    // read-only SVGAnimatedString; classList works on SVG elements in
    // every browser this app supports, with a setAttribute fallback.
    var cls = "sparkline-hit--active";
    if (el.classList) {
      if (isActive) {
        el.classList.add(cls);
      } else {
        el.classList.remove(cls);
      }
      return;
    }
    var current = " " + (el.getAttribute("class") || "") + " ";
    var has = current.indexOf(" " + cls + " ") !== -1;
    if (isActive && !has) {
      el.setAttribute("class", (current + cls).replace(/^\s+|\s+$/g, ""));
    } else if (!isActive && has) {
      el.setAttribute("class", current.split(" " + cls + " ").join(" ")
        .replace(/^\s+|\s+$/g, ""));
    }
  }

  // Roving tabindex: health_page.py's battery_sparkline_svg() emits one
  // hit target with tabindex="0" and tabindex="-1" on the rest, so Tab
  // visits the chart once. Clamps to the ends, never wraps, then calls
  // .focus(), which fires the "focus" listener below and reveals the
  // point without a duplicate call here.
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

  // Per-iteration closure (an inner IIFE), for the ES5-safe subset.
  // Listeners go on every view's targets; each handler works against
  // whichever view is shown when it fires.
  for (var i = 0; i < allPoints.length; i++) {
    (function (point) {
      point.addEventListener("click", function () {
        // A tap synthesises a click in every mobile browser this
        // project targets, so no separate touch listeners are needed.
        reveal(point);
      });
      point.addEventListener("mouseenter", function () {
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
      // A separate keydown listener for roving-tabindex navigation.
      // Array.prototype.indexOf.call() rather than an ES6 helper, since
      // no conversion is needed on a NodeList, only an index lookup.
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
    })(allPoints[i]);
  }

  // Percentage / Voltage control. Native buttons give Enter, Space,
  // pointer and touch operation and a visible focus ring; the selected
  // state is aria-pressed. The control ships `hidden` and is revealed
  // here, so without this script only the default view is offered.
  var unitGroup = document.querySelector(".battery-unit");
  if (unitGroup && views.length > 0) {
    var buttons = unitGroup.querySelectorAll(".battery-unit__option");

    var selectUnit = function (unit) {
      for (var b = 0; b < buttons.length; b++) {
        buttons[b].setAttribute(
          "aria-pressed", buttons[b].getAttribute("data-unit") === unit ? "true" : "false");
      }
      for (var w = 0; w < views.length; w++) {
        if (views[w].getAttribute("data-unit") === unit) {
          views[w].removeAttribute("hidden");
          points = viewPoints(views[w]);
        } else {
          views[w].setAttribute("hidden", "");
        }
      }
      // Carry the revealed reading across: the same position in the new
      // view, or its latest point when none had been revealed.
      for (var t = 0; t < points.length; t++) {
        _toggleActive(points[t], false);
      }
      reveal(points[activeIndex >= 0 && activeIndex < points.length
        ? activeIndex : points.length - 1]);
    };

    for (var k = 0; k < buttons.length; k++) {
      (function (button) {
        button.addEventListener("click", function () {
          selectUnit(button.getAttribute("data-unit"));
        });
      })(buttons[k]);
    }
    unitGroup.removeAttribute("hidden");
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
