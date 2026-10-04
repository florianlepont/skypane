/*
 * SkyPane companion service — airline-types.js.
 *
 * Page-local enhancement for the Airlines gallery: an airline with several
 * known aircraft types renders one slide per type in a horizontal
 * scroll-snap strip that swipes and scrolls natively. With this script the
 * pagination dots (script-gated markup) scroll to a slide when pressed and
 * the current dot follows the strip's scroll position. No network call and
 * no persistent state. ES5-safe. Served by companion/app.py's
 * AIRLINE_TYPES_SCRIPT_ROUTE.
 */
(function () {
  "use strict";

  var READY_ATTR = "data-airline-types-ready";
  var TYPE_ATTR = "data-airline-type";
  var DOT_ATTR = "data-airline-type-dot";

  function prefersReducedMotion() {
    return !!(window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function wire(group) {
    var track = group.querySelector(".airline-card__track");
    var slides = group.querySelectorAll("[" + TYPE_ATTR + "]");
    var dots = group.querySelectorAll("[" + DOT_ATTR + "]");
    if (!track || !slides.length || !dots.length) {
      return;
    }

    function current() {
      var width = track.clientWidth || 1;
      var index = Math.round(track.scrollLeft / width);
      return Math.max(0, Math.min(slides.length - 1, index));
    }

    function paint() {
      var at = current();
      for (var i = 0; i < dots.length; i += 1) {
        if (i === at) {
          dots[i].setAttribute("aria-current", "true");
        } else {
          dots[i].removeAttribute("aria-current");
        }
      }
    }

    function goTo(index) {
      var left = slides[index].offsetLeft;
      if (track.scrollTo) {
        track.scrollTo({
          left: left,
          behavior: prefersReducedMotion() ? "auto" : "smooth"
        });
      } else {
        track.scrollLeft = left;
      }
    }

    for (var d = 0; d < dots.length; d += 1) {
      (function (index) {
        dots[index].addEventListener("click", function () {
          goTo(index);
        });
      })(d);
    }

    track.addEventListener("scroll", paint, { passive: true });
    group.setAttribute(READY_ATTR, "");
    paint();
  }

  var groups = document.querySelectorAll("[data-airline-types]");
  for (var index = 0; index < groups.length; index += 1) {
    wire(groups[index]);
  }
})();
