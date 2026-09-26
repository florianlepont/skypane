/*
 * SkyPane companion service — flash-cleanup.js.
 *
 * Strips the consumed "flash"/"rule" query parameters from the address
 * bar once the flash banner they produced has rendered, so a reload or
 * re-shared URL never replays a confirmation. Keeps every other query
 * parameter and the fragment. No build step, ES5-safe subset. Served
 * by companion/app.py's FLASH_CLEANUP_SCRIPT_ROUTE. Writes only via
 * history.replaceState(), never DOM content or a server-supplied URL.
 */
(function () {
  "use strict";

  if (!document.querySelector(".banner--flash")) {
    return;
  }
  if (location.search.indexOf("flash=") === -1) {
    return;
  }

  // Keeps every parameter but flash/rule, so ?resolve= survives.
  var kept = [];
  var query = location.search.charAt(0) === "?" ? location.search.slice(1) : location.search;
  var pairs = query ? query.split("&") : [];
  for (var i = 0; i < pairs.length; i += 1) {
    var name = pairs[i].split("=")[0];
    if (name !== "flash" && name !== "rule" && pairs[i] !== "") {
      kept.push(pairs[i]);
    }
  }
  var cleaned = location.pathname + (kept.length ? "?" + kept.join("&") : "") + location.hash;
  history.replaceState(null, "", cleaned);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
