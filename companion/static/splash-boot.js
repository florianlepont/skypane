/* The opening splash's gate. A tiny synchronous script in the document head,
 * right after the stylesheet: it decides, before the first paint, whether the
 * splash shows, by putting `splash-on` on <html>. It also puts `js-early` on
 * <html> whenever scripts run, and `web-app` in an iPhone Home Screen web
 * app (see below). The overlay markup is
 * hidden by the stylesheet until then, so there is no flash of the page
 * under it and, without scripts, no splash at all.
 *
 * The splash shows at every opening of the site: once per browser session,
 * whatever the cache holds, so opening the app or a tab from a bookmark or the
 * home-screen icon plays it and moving between pages does not (the guard is
 * written before anything else, so a second page opened during the splash
 * skips it). It never shows when session storage is unavailable (the
 * once-only promise could not be kept). A page restored from the back/forward
 * cache keeps whatever it showed; the splash does not replay there. The hard
 * cap below removes the class again even if the main splash script never
 * runs.
 *
 * The main splash script is not linked from the page: this script loads it,
 * from the address named by its own `data-splash-src` attribute, only when
 * the splash is going to play, so every other page load skips the download.
 */
(function () {
  "use strict";

  var KEY = "skypane.splash";
  var HARD_CAP_MS = 3200;
  var EARLY_CLASS = "js-early";
  var WEB_APP_CLASS = "web-app";
  // How long the Location page's loading state may wait for the map before
  // the plain form shows instead.
  var EARLY_CAP_MS = 6000;
  var root = document.documentElement;
  var bootTag = document.currentScript;

  // Scripts run: the class is on <html> before the first paint, so a page
  // that swaps its plain form for a script-driven view can hide the form and
  // show a loading state from the start. The cap puts the plain form back if
  // the page's own script never reports ready.
  root.classList.add(EARLY_CLASS);
  window.setTimeout(function () {
    root.classList.remove(EARLY_CLASS);
  }, EARLY_CAP_MS);

  // An iPhone Home Screen web app: navigator.standalone is true there only
  // (false in a Safari tab, undefined in every other browser; no
  // display-mode media query matches it, as the site has no manifest). iOS
  // frosts the top of such a window, below the status bar, and the
  // stylesheet moves the phone app bar down out of that frost. Set before
  // the first paint so the bar never jumps.
  if (window.navigator.standalone === true) {
    root.classList.add(WEB_APP_CLASS);
  }

  // A page reached through a page change (a view transition) is already
  // arriving by the cross-fade. The mark lets the stylesheet skip the block
  // entrance, so one motion plays, not two. The event fires before the first
  // frame, which is why the listener lives in this early script.
  window.addEventListener("pagereveal", function (event) {
    if (event.viewTransition) {
      root.classList.add("page-crossfade");
    }
  });

  // The splash script reads the overlay markup, so it is added once the
  // document has been parsed (what `defer` did when the page linked it).
  function loadSplashScript() {
    var src = bootTag && bootTag.getAttribute("data-splash-src");
    if (!src) {
      return;
    }
    // Fetched now, while the document is still being parsed, so the script is
    // already here when the splash needs it.
    var hint = document.createElement("link");
    hint.rel = "preload";
    hint.as = "script";
    hint.href = src;
    document.head.appendChild(hint);
    function add() {
      var script = document.createElement("script");
      script.src = src;
      document.head.appendChild(script);
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", add);
    } else {
      add();
    }
  }

  try {
    if (window.sessionStorage.getItem(KEY)) {
      return;
    }
    window.sessionStorage.setItem(KEY, "1");
  } catch (error) {
    return;
  }
  root.classList.add("splash-on");
  loadSplashScript();
  window.setTimeout(function () {
    root.classList.remove("splash-on");
  }, HARD_CAP_MS);
}());
