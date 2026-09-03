/*
 * SkyPane companion service — flash-cleanup.js.
 *
 * UIR-19 (quick task 260903-peo): strips a consumed "?flash=" query
 * parameter from the address bar once its banner has actually rendered,
 * so reloading the page (or a user re-sharing/bookmarking the URL) never
 * replays a save/poll confirmation that has already been shown. Like
 * nav-dropdown.js/dirty-state.js/panel-lookup.js before it, this file has
 * no build step, no bundler, no framework and no dependency of any kind,
 * and must stay written to an ES5-safe subset (no let/const/arrow
 * functions/template literals/backticks) so no transpiler is ever needed
 * to ship it. It is served by companion/app.py's
 * FLASH_CLEANUP_SCRIPT_ROUTE, mirroring the existing /static/style.css
 * route.
 *
 * The server-side PRG (Post/Redirect/Get) redirect itself is NOT touched
 * by this file or by this task: POST /settings still redirects to
 * "%s?flash=%s" (companion/app.py), _resolve_flash_text() still resolves
 * it, FLASH_ROLES still maps it, and companion/layout.py's
 * flash_banner() still renders it. This script only runs client-side,
 * after the banner produced by that redirect has already reached the
 * DOM, and its only job is tidying the address bar behind it.
 *
 * Guarded on BOTH conditions, not one: a rendered ".banner--flash"
 * element (companion/layout.py's flash_banner() — the ONLY element in
 * the whole app carrying this class) must be present, AND
 * location.search must mention "flash". The first condition proves a
 * flash banner was genuinely produced by this exact page load, not just
 * that the URL happens to carry the substring; the second proves there
 * is actually something in the query string to remove. Two conditions,
 * not one, is deliberate: a future page could add a second, unrelated
 * query parameter, and this guard must not silently discard it under the
 * same rewrite.
 *
 * location.pathname is safe to hand to history.replaceState() unchanged
 * today, verified from source rather than assumed: companion/app.py
 * reads exactly ONE query parameter across the whole module —
 * params.get("flash", ...) — confirmed by grep to be the only
 * params.get( call in the file. The other query parameter this app ever
 * reads, "?next=", appears only on /login, which renders through
 * companion/layout.py's login_shell(), never page_shell(), so a login
 * page never carries a flash banner and this script's guard above
 * already excludes it. Replacing the WHOLE search string (rather than
 * surgically removing just the "flash" key) is therefore lossless
 * today — the two-condition guard above is what keeps that true if a
 * second query parameter is ever added to an authenticated page later,
 * rather than this file's own unchecked assumption.
 *
 * This file writes to browser navigation state only, via
 * history.replaceState() — never a raw-markup DOM sink of any kind,
 * never a network call, never a timer, and holds no persistent state of
 * its own. The replacement URL is always location.pathname, a
 * same-document value read from the browser itself, never a server- or
 * attacker-supplied string and never a URL assembled from DOM content.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page) — the flash banner is emitted
 * by page_shell() for every authenticated page (Settings, Health,
 * Airlines and History's own flash keys all reach it), so the cleanup
 * belongs in its own page-agnostic file that no-ops via the guard clause
 * above, matching the project's established convention
 * (nav-dropdown.js/dirty-state.js/panel-lookup.js's own early returns)
 * rather than being bolted onto one page-specific script.
 */
(function () {
  "use strict";

  if (!document.querySelector(".banner--flash")) {
    return;
  }
  if (location.search.indexOf("flash") === -1) {
    return;
  }

  history.replaceState(null, "", location.pathname);

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
