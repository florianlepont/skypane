/*
 * SkyPane companion service — freshness.js.
 *
 * D-12/UXA-13 (06.6.3-CONTEXT.md): reveals a "this view may be stale"
 * banner once the page's own [data-loaded-at] timestamp is older than a
 * fixed threshold. Like nav-dropdown.js/battery-trend.js before it,
 * this file has no build step, no bundler, no framework and no
 * dependency of any kind, and must stay written to an ES5-safe subset
 * (no let/const/arrow functions/template literals/backticks) so no
 * transpiler is ever needed to ship it. It is served by
 * companion/app.py's FRESHNESS_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route.
 *
 * Standing constraint this file must never violate: it never
 * recomputes Health's authoritative ok/warn/error severity client-side
 * — it only toggles a server-rendered banner's visibility based on
 * elapsed wall-clock time since the page loaded. The severity judgment
 * itself stays entirely server-side.
 *
 * Standing constraint, not just a description of this version: this
 * file must never poll — never setInterval, never a network call. At
 * most one deferred setTimeout, scheduled once, for the remaining time
 * until the threshold.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * [data-loaded-at] element at all — today only Health/Preview do — so
 * the guard below is load-bearing, not defensive noise, matching the
 * project's established convention.
 */
(function () {
  "use strict";

  // 10 minutes — a named constant, not a magic number
  // (06.6.3-UI-SPEC.md's New Component Contracts, D-12 Open Question 2).
  var STALE_VIEW_THRESHOLD_MS = 600000;

  var loadedAtEl = document.querySelector("[data-loaded-at]");
  var banner = document.querySelector("[data-stale-banner]");
  if (!loadedAtEl || !banner) {
    return;
  }

  var raw = loadedAtEl.getAttribute("data-loaded-at");
  if (!raw) {
    return;
  }

  // This file has no access to companion/layout.py's parse_iso() — it
  // must do its own defensive parse-or-noop rather than assuming the
  // attribute is always well-formed.
  var parsed = new Date(raw);
  if (isNaN(parsed.getTime())) {
    return;
  }

  function reveal() {
    banner.hidden = false;
  }

  var elapsed = Date.now() - parsed.getTime();
  var remaining = STALE_VIEW_THRESHOLD_MS - elapsed;
  if (remaining <= 0) {
    reveal();
  } else {
    window.setTimeout(reveal, remaining);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
