/*
 * SkyPane companion service — place-search.js.
 *
 * The one gate every request to the address search service goes through, for
 * the typed suggestions (place-card.js) and the submitted search
 * (place-map.js) alike: at most one request in flight, at least
 * `data-search-lock-ms` between two starts, one answer cache shared by both.
 * A request for a query that is in flight, waiting or cached is not sent
 * again; a suggestion that a submit replaces is aborted, and a request that
 * a newer one replaces while it waits is dropped. Loaded before the two scripts above. ES5-safe subset.
 */
(function () {
  "use strict";

  var mapEl = document.getElementById("place-map");
  if (!mapEl || typeof window.fetch !== "function") {
    return;
  }
  var lockMs = parseInt(mapEl.getAttribute("data-search-lock-ms"), 10) || 1500;
  var cache = {};
  var active = null;
  var pending = null;
  var lastStart = 0;
  var timer = null;

  function hasKey(key) {
    return Object.prototype.hasOwnProperty.call(cache, key);
  }

  function replaced() {
    var error = new Error("search replaced");
    error.name = "AbortError";
    return error;
  }

  function settle(entry) {
    if (active === entry) {
      active = null;
    }
    pump();
  }

  function start(entry) {
    active = entry;
    lastStart = Date.now();
    var options = { credentials: "omit", referrerPolicy: "origin" };
    if (typeof window.AbortController === "function") {
      entry.controller = new window.AbortController();
      options.signal = entry.controller.signal;
    }
    window.fetch(entry.url, options).then(function (response) {
      if (!response.ok) {
        throw new Error("search failed");
      }
      return response.json();
    }).then(function (list) {
      if (!Array.isArray(list)) {
        throw new Error("search failed");
      }
      cache[entry.key] = list;
      settle(entry);
      entry.resolve(list);
    }, function (error) {
      settle(entry);
      entry.reject(error);
    });
  }

  // Starts the waiting request once nothing is in flight and the lock has run out.
  function pump() {
    window.clearTimeout(timer);
    if (active || !pending) {
      return;
    }
    var wait = lastStart + lockMs - Date.now();
    if (wait > 0) {
      timer = window.setTimeout(pump, wait);
      return;
    }
    var entry = pending;
    pending = null;
    start(entry);
  }

  function search(query, url, role) {
    var key = query.toLowerCase();
    if (hasKey(key)) {
      return Promise.resolve(cache[key]);
    }
    if (active && active.key === key) {
      return active.promise;
    }
    if (pending && pending.key === key) {
      return pending.promise;
    }
    if (pending && pending.role === "submit" && role === "suggest") {
      return Promise.reject(replaced());
    }
    var entry = { key: key, url: url, role: role, controller: null };
    entry.promise = new Promise(function (resolve, reject) {
      entry.resolve = resolve;
      entry.reject = reject;
    });
    if (pending) {
      pending.reject(replaced());
    }
    // A submit does not wait for a suggestion of another query: that one is
    // cancelled. A newer suggestion waits its turn instead.
    if (role === "submit" && active && active.role === "suggest" && active.controller) {
      active.controller.abort();
    }
    pending = entry;
    pump();
    return entry.promise;
  }

  window.skypaneSearchGate = {
    search: search,
    cached: function (query) {
      var key = query.toLowerCase();
      return hasKey(key) ? cache[key] : null;
    }
  };
}());
