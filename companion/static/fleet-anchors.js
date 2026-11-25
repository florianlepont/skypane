/*
 * SkyPane companion service — fleet-anchors.js.
 *
 * A frame's page is State, Settings and Access stacked; a phone shows three
 * anchor links above them (they stay at the top while the page scrolls). The
 * links work without this file: each is a plain in-page link. This file marks
 * the section in view as the current anchor and, when the server named a section
 * to bring into view (a save or a dialog returning to Settings or Access), scrolls
 * to it once the page has loaded. On a wide screen the list of frames scrolls
 * inside its own panel, so the selected frame's row is brought to the middle of
 * that panel when the page opens. No build step, ES5-safe subset. Served by
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

  // The list panel scrolls by itself; centre the selected row in it without
  // moving the page. Nothing happens when the panel is not shown (a phone
  // shows the list on its own page) or the row is already fully visible.
  function showSelectedRow() {
    var row = document.querySelector(".fleet-list__body .fleet-frame-row.is-selected");
    var panel = row ? row.parentNode : null;
    while (panel && panel.className.indexOf("fleet-list__body") === -1) {
      panel = panel.parentNode;
    }
    if (!panel || !panel.getClientRects().length) {
      return;
    }
    var box = row.getBoundingClientRect();
    var view = panel.getBoundingClientRect();
    if (box.top < view.top || box.bottom > view.bottom) {
      panel.scrollTop += (box.top - view.top) - (view.height - box.height) / 2;
    }
  }
  showSelectedRow();

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

  // The bar paints the page's own gradient (see style-admin.css) so it never
  // shows as a band: the gradient is laid out over the whole page, so the bar
  // needs the page height and its own distance from the top of the page. While
  // it sticks it covers the gap above it (a strip, shown only then, so the
  // content just above it is never covered while it rests in place).
  function paintBar() {
    var top = parseFloat(window.getComputedStyle(nav).top) || 0;
    var box = nav.getBoundingClientRect();
    nav.style.setProperty("--anchors-page-h", document.documentElement.offsetHeight + "px");
    nav.style.setProperty("--anchors-y", (box.top + window.pageYOffset) + "px");
    if (window.pageYOffset > 0 && box.top <= top + 0.5) {
      nav.setAttribute("data-stuck", "true");
    } else {
      nav.removeAttribute("data-stuck");
    }
  }

  function update() {
    paintBar();
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
