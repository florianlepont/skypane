/* The opening splash's gate. A tiny synchronous script in the document head,
 * right after the stylesheet: it decides, before the first paint, whether the
 * splash shows, by putting `splash-on` on <html>. The overlay markup is
 * hidden by the stylesheet until then, so there is no flash of the page
 * under it and, without scripts, no splash at all.
 *
 * The splash shows once per browser session (the guard is written before
 * anything else, so a second page opened during the splash skips it), never
 * when the stylesheet came from the cache (a visitor who has been here
 * before), and never when session storage is unavailable (the once-only
 * promise could not be kept). The hard cap below removes the class again
 * even if the main splash script never runs.
 */
(function () {
  "use strict";

  var KEY = "skypane.splash";
  var HARD_CAP_MS = 3200;
  var root = document.documentElement;

  // A resource timing entry for the stylesheet whose bytes did not cross the
  // network (a memory-cache hit, or a revalidation that only moved headers).
  function stylesheetWasCached() {
    var entries;
    try {
      entries = window.performance.getEntriesByType("resource");
    } catch (error) {
      return false;
    }
    for (var i = 0; i < entries.length; i += 1) {
      var entry = entries[i];
      if (entry.name.indexOf("/static/style.css") === -1) {
        continue;
      }
      return entry.transferSize === 0 ||
        (entry.encodedBodySize > 0 && entry.transferSize < entry.encodedBodySize);
    }
    return false;
  }

  try {
    if (window.sessionStorage.getItem(KEY)) {
      return;
    }
    window.sessionStorage.setItem(KEY, "1");
  } catch (error) {
    return;
  }
  if (stylesheetWasCached()) {
    return;
  }
  root.classList.add("splash-on");
  window.setTimeout(function () {
    root.classList.remove("splash-on");
  }, HARD_CAP_MS);
}());
