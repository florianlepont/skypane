/*
 * SkyPane companion service — fleet-anchors.js.
 *
 * A frame's page is State, Settings and Access stacked; a phone shows three
 * anchor links above them (they stay at the top while the page scrolls). The
 * links work without this file: each is a plain in-page link. This file marks
 * the section in view as the current anchor and, when the server named a section
 * to bring into view (a save or a dialog returning to Settings or Access), scrolls
 * to it once the page has loaded. No build step, ES5-safe subset. Served by
 * companion/static_files.py's FLEET_ANCHORS_SCRIPT_ROUTE. No HTML-writing sink.
 */
(function () {
  "use strict";

  var NAV_ATTR = "data-fleet-anchors";
  var FOCUS_ATTR = "data-fleet-focus";
  var SECTION_PREFIX = "fleet-section-";
  // A section counts as in view once its top is within this share of the
  // window height from the top.
  var VIEW_SHARE = 0.4;

  var nav = document.querySelector("[" + NAV_ATTR + "]");
  if (!nav || !nav.getClientRects().length) {
    return;
  }
  var links = nav.querySelectorAll("a[href^='#" + SECTION_PREFIX + "']");
  var pairs = [];
  for (var i = 0; i < links.length; i++) {
    var target = document.getElementById(links[i].getAttribute("href").slice(1));
    if (target) {
      pairs.push({ link: links[i], section: target });
    }
  }
  if (!pairs.length) {
    return;
  }

  function mark(current) {
    for (var k = 0; k < pairs.length; k++) {
      if (pairs[k] === current) {
        pairs[k].link.setAttribute("aria-current", "true");
      } else {
        pairs[k].link.removeAttribute("aria-current");
      }
    }
  }

  function update() {
    var limit = window.innerHeight * VIEW_SHARE;
    var current = pairs[0];
    for (var k = 0; k < pairs.length; k++) {
      if (pairs[k].section.getBoundingClientRect().top <= limit) {
        current = pairs[k];
      }
    }
    // At the very bottom the last section is the one being read, even when it
    // is too short to reach the limit.
    if (window.innerHeight + window.pageYOffset >= document.documentElement.scrollHeight - 2) {
      current = pairs[pairs.length - 1];
    }
    mark(current);
  }

  var queued = false;
  function onScroll() {
    if (queued) {
      return;
    }
    queued = true;
    window.requestAnimationFrame(function () {
      queued = false;
      update();
    });
  }

  function bringIntoView() {
    var holder = document.querySelector("[" + FOCUS_ATTR + "]");
    var wanted = holder ? document.getElementById(SECTION_PREFIX + holder.getAttribute(FOCUS_ATTR)) : null;
    if (wanted && !window.location.hash) {
      var top = wanted.getBoundingClientRect().top + window.pageYOffset - nav.offsetHeight;
      window.scrollTo(0, Math.max(0, top));
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  bringIntoView();
  update();
})();
