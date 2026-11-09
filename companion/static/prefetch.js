/*
 * SkyPane companion service — prefetch.js.
 *
 * Warms the page behind a navigation link so the tap that follows opens it
 * from the browser's private cache. Candidates are the plain links of the
 * tab bar, the sidebar and the hamburger menu; each is fetched with a GET
 * carrying `X-Requested-With: prefetch`, which is what makes the server
 * answer `private, max-age=10` with `Vary: Cookie` instead of its usual
 * `no-store` (companion/page_cache.py). Pages are warmed once the window is
 * idle after load, then again on touchstart, mouse hover and keyboard focus
 * of a link. The idle warm-up fetches only the two pages a visitor most likely
 * opens next. Never prefetched: a link to the current page, to another
 * origin, with a query or a fragment, to the sign-in or sign-out routes, to
 * the bare root (a redirect), to the airline editor or to a quick-switch
 * route; nothing here sends a POST. Skipped altogether under
 * Save-Data, on a 2G-class connection and in a hidden tab. At most two
 * requests run at once. Whenever the user changes something (a form post or a
 * quick switch) a marker cookie is rewritten, which changes the cache key of
 * every warmed page, so a page fetched before the change is never shown after
 * it. The cookie carries only a timestamp. ES5-safe subset.
 */
(function () {
  "use strict";

  var LINK_SELECTOR = ".tab-bar a[href], .sidebar-nav a[href], .mobile-nav a[href]";
  var HEADER_VALUE = "prefetch";
  // A little under the server's max-age, so a page is never asked for again
  // while the cached copy is still fresh.
  var REFRESH_AFTER_MS = 8000;
  var IDLE_DELAY_MS = 2500;
  var MAX_ACTIVE = 2;
  var MAX_QUEUED = 8;
  var MARKER_COOKIE = "sp_mut";
  // Routes that are not plain pages, the bare root (a redirect) and the
  // airline editor (a heavy page nobody opens on a whim).
  var EXCLUDED = /^\/(login|logout|quick|static)(\/|$)|^\/$|(^|\/devices\/d_[0-9a-f]{8})\/airlines\/manage$/;
  // When idle, only the next pages a visitor most likely opens are warmed
  // (two, by the page they are on); every other link is warmed on intent.
  var IDLE_LIKELY = {
    home: ["flights", "display"],
    flights: ["home", "display"],
    other: ["flights", "home"]
  };

  var lastFetched = {};
  var queue = [];
  var active = 0;

  function connectionAllows() {
    var connection = navigator.connection;
    if (!connection) {
      return true;
    }
    if (connection.saveData) {
      return false;
    }
    return !/(^|-)2g$/.test(connection.effectiveType || "");
  }

  // The absolute URL to warm for `anchor`, or "" when it must not be.
  function targetOf(anchor) {
    if (!anchor || anchor.hasAttribute("download")
        || (anchor.target && anchor.target !== "_self")) {
      return "";
    }
    var url;
    try {
      url = new URL(anchor.getAttribute("href"), window.location.href);
    } catch (error) {
      return "";
    }
    if (url.origin !== window.location.origin || url.search || url.hash
        || url.pathname === window.location.pathname
        || EXCLUDED.test(url.pathname)) {
      return "";
    }
    return url.href;
  }

  function isFresh(url) {
    return lastFetched[url] && Date.now() - lastFetched[url] < REFRESH_AFTER_MS;
  }

  function pump() {
    while (active < MAX_ACTIVE && queue.length) {
      var url = queue.shift();
      if (isFresh(url)) {
        continue;
      }
      lastFetched[url] = Date.now();
      active += 1;
      run(url);
    }
  }

  function run(url) {
    var done = function () {
      active -= 1;
      pump();
    };
    window.fetch(url, {
      method: "GET",
      credentials: "same-origin",
      redirect: "manual",
      priority: "low",
      headers: { "X-Requested-With": HEADER_VALUE }
    }).then(function (response) {
      if (!response.ok) {
        delete lastFetched[url];
      }
      // The body is read so the whole answer reaches the cache.
      return response.type === "opaqueredirect" ? null : response.text();
    }).then(done, function () {
      delete lastFetched[url];
      done();
    });
  }

  function enqueue(url, urgent) {
    if (!url || isFresh(url) || !window.fetch || document.hidden
        || !connectionAllows()) {
      return;
    }
    var at = queue.indexOf(url);
    if (at !== -1) {
      queue.splice(at, 1);
    }
    if (urgent) {
      queue.unshift(url);
    } else if (queue.length < MAX_QUEUED) {
      queue.push(url);
    }
    pump();
  }

  // "home", "flights", "display" or "other" for a path (a frame's own prefix
  // is ignored).
  function slugOf(pathname) {
    var path = pathname.replace(/^\/devices\/d_[0-9a-f]{8}/, "");
    if (path === "" || path === "/") {
      return "home";
    }
    return path === "/flights" || path === "/display" ? path.slice(1) : "other";
  }

  function warmAll() {
    var anchors = document.querySelectorAll(LINK_SELECTOR);
    var current = slugOf(window.location.pathname);
    var order = IDLE_LIKELY[current] || IDLE_LIKELY.other;
    var chosen = {};
    for (var i = 0; i < anchors.length; i++) {
      var url = targetOf(anchors[i]);
      if (url) {
        chosen[slugOf(new URL(url).pathname)] = url;
      }
    }
    for (var j = 0; j < order.length; j++) {
      if (chosen[order[j]]) {
        enqueue(chosen[order[j]], false);
      }
    }
  }

  function linkOf(evt) {
    var node = evt.target;
    if (!node || !node.closest) {
      return null;
    }
    var anchor = node.closest("a[href]");
    return anchor && anchor.matches(LINK_SELECTOR) ? anchor : null;
  }

  function onIntent(evt) {
    enqueue(targetOf(linkOf(evt)), true);
  }

  // Changes the cache key of every page warmed so far.
  function markChange() {
    lastFetched = {};
    queue = [];
    try {
      document.cookie = MARKER_COOKIE + "=" + Date.now()
        + "; path=/; SameSite=Strict"
        + (window.location.protocol === "https:" ? "; Secure" : "");
    } catch (error) {
      // Cookies blocked: the cached copies simply expire on their own.
    }
  }

  document.addEventListener("touchstart", onIntent, { passive: true });
  document.addEventListener("pointerover", function (evt) {
    if (evt.pointerType === "mouse") {
      onIntent(evt);
    }
  });
  document.addEventListener("focusin", onIntent);
  document.addEventListener("skypane-mutated", markChange);
  document.addEventListener("submit", function (evt) {
    var form = evt.target;
    if (form && form.method && form.method.toLowerCase() !== "get") {
      markChange();
    }
  }, true);

  function whenIdle() {
    window.setTimeout(function () {
      if (window.requestIdleCallback) {
        window.requestIdleCallback(warmAll, { timeout: 4000 });
      } else {
        warmAll();
      }
    }, IDLE_DELAY_MS);
  }

  if (document.readyState === "complete") {
    whenIdle();
  } else {
    window.addEventListener("load", whenIdle);
  }
  // A page restored from the back/forward cache starts its own idle warm-up.
  window.addEventListener("pageshow", function (evt) {
    if (evt.persisted) {
      lastFetched = {};
      whenIdle();
    }
  });
})();
