/*
 * SkyPane companion service — place-start.js.
 *
 * The Location page is complete without its map: the form, the search box and
 * the saved place work as plain HTML. This script starts the map after the
 * first paint instead of blocking it: it loads the map library and the page's
 * map scripts, one after the other and in order, then, once the map is up,
 * fills the airport list. The addresses come from `data-*-src` attributes on
 * #place-map (the page names each script once, with its version). A failing
 * library leaves the plain form as it is (place-map.js sees it missing). ES5-safe subset.
 */
(function () {
  "use strict";

  var mapEl = document.getElementById("place-map");
  if (!mapEl) {
    return;
  }
  var MAP_SCRIPTS = [
    "data-leaflet-src", "data-search-src", "data-map-src", "data-map-search-src",
    "data-card-src"
  ];
  var IDLE_TIMEOUT_MS = 400;

  function load(attr, next) {
    var src = mapEl.getAttribute(attr);
    if (!src) {
      next();
      return;
    }
    var script = document.createElement("script");
    script.src = src;
    script.onload = next;
    // A script that fails to load does not stop the others: place-map.js
    // itself leaves the plain form in place when the library is missing.
    script.onerror = next;
    document.head.appendChild(script);
  }

  function chain(attrs, done) {
    var at = 0;
    function step() {
      if (at >= attrs.length) {
        done();
        return;
      }
      load(attrs[at++], step);
    }
    step();
  }

  // Runs `fn` once the browser has painted and is idle.
  function whenIdle(fn) {
    function idle() {
      if (typeof window.requestIdleCallback === "function") {
        window.requestIdleCallback(fn, { timeout: IDLE_TIMEOUT_MS });
      } else {
        window.setTimeout(fn, 0);
      }
    }
    if (typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(function () {
        window.setTimeout(idle, 0);
      });
    } else {
      idle();
    }
  }

  // The airport rows join the list late, once the map is up.
  function fillAirports() {
    whenIdle(function () {
      load("data-airports-src", function () {});
    });
  }

  whenIdle(function () {
    chain(MAP_SCRIPTS, fillAirports);
  });
}());
