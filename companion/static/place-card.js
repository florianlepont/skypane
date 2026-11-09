/*
 * SkyPane companion service - place-card.js.
 *
 * The small page furniture around the map on the Location and detection page:
 * the credits popover and the details card's heading. Loaded after
 * place-map.js on that one page only, and inert unless the map started (the
 * page element carries `map-ready`), so a page without the map keeps its plain
 * form. No build step, ES5-safe subset.
 */
(function () {
  "use strict";

  if (!document.getElementById("place-map") ||
      (" " + document.documentElement.className + " ").indexOf(" map-ready ") < 0) {
    return;
  }

  var infoButton = document.getElementById("place-info");
  var creditsEl = document.getElementById("place-credits");

  function setCreditsOpen(open) {
    creditsEl.hidden = !open;
    infoButton.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function wireCredits() {
    if (!infoButton || !creditsEl) {
      return;
    }
    infoButton.addEventListener("click", function () {
      setCreditsOpen(creditsEl.hidden);
    });
    document.addEventListener("click", function (event) {
      if (!creditsEl.hidden && !event.target.closest(".place-info")) {
        setCreditsOpen(false);
      }
    }, true);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !creditsEl.hidden) {
        setCreditsOpen(false);
        infoButton.focus();
      }
    });
  }

  wireCredits();

  // The radius field and its slider: a value past the limits is pulled back
  // to the nearest limit once the field is left, and the slider speaks the
  // value in kilometres.
  function wireRadius() {
    var field = document.getElementById("place-radius");
    var range = document.getElementById("place-radius-range");
    if (!field) {
      return;
    }
    function speak() {
      if (range && field.value !== "") {
        range.setAttribute("aria-valuetext", field.value + " km");
      }
    }
    field.addEventListener("input", speak);
    if (range) {
      range.addEventListener("input", speak);
    }
    field.addEventListener("change", function () {
      var km = parseFloat(field.value);
      var min = parseFloat(field.getAttribute("min"));
      var max = parseFloat(field.getAttribute("max"));
      if (isNaN(km) || isNaN(min) || isNaN(max)) {
        return;
      }
      var clamped = Math.round(Math.min(max, Math.max(min, km)));
      if (String(clamped) !== field.value) {
        field.value = String(clamped);
        field.dispatchEvent(new Event("input", { bubbles: true }));
      }
      speak();
    });
    speak();
  }

  wireRadius();

  // One search: while a place or an address is typed, the page's own airport
  // matches (listed by place-map.js at once) are joined, after a pause, by
  // the search service's place suggestions in the same list, each group under
  // its own heading. The submit button and Enter keep working as before.
  function wireUnifiedSearch() {
    var api = window.skypanePlaceSearch;
    var mapEl = document.getElementById("place-map");
    var input = document.getElementById("place-search");
    var results = document.getElementById("place-results");
    if (!api || !input || !results) {
      return;
    }
    var DEBOUNCE_MS = 700;
    var LIMIT = 5;
    var min = parseInt(mapEl.getAttribute("data-search-min"), 10) || 3;
    var max = parseInt(mapEl.getAttribute("data-search-max"), 10) || 120;
    var lockMs = parseInt(mapEl.getAttribute("data-search-lock-ms"), 10) || 1500;
    var timer = null;
    var lastStart = 0;
    var inFlight = false;
    var cache = {};

    function typed() {
      return input.value.replace(/\s+/g, " ").replace(/^ | $/g, "");
    }

    function heading(label, kind) {
      var li = document.createElement("li");
      li.className = "place-results__group text-label";
      li.setAttribute("role", "presentation");
      li.setAttribute("data-group", kind);
      li.textContent = label;
      return li;
    }

    function placeRow(result, at) {
      var li = document.createElement("li");
      li.setAttribute("role", "presentation");
      li.setAttribute("data-place", "");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "place-result";
      button.id = "place-option-place-" + at;
      button.tabIndex = -1;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", "false");
      var name = document.createElement("span");
      name.className = "place-result__name";
      name.textContent = result.name;
      button.appendChild(name);
      if (result.rest) {
        var rest = document.createElement("span");
        rest.className = "place-result__rest text-label";
        rest.textContent = result.rest;
        button.appendChild(rest);
      }
      button.title = result.rest ? result.name + " - " + result.rest : result.name;
      button.addEventListener("click", function () {
        api.choose(result);
      });
      li.appendChild(button);
      return li;
    }

    function show(list, query) {
      if (typed() !== query) {
        return;
      }
      var rows = [];
      for (var n = 0; n < list.length && rows.length < LIMIT; n++) {
        var row = api.read(list[n]);
        if (row) {
          rows.push(row);
        }
      }
      if (!rows.length) {
        return;
      }
      var ul = results.querySelector("ul.place-results__list");
      if (!ul) {
        while (results.firstChild) {
          results.removeChild(results.firstChild);
        }
        ul = document.createElement("ul");
        ul.className = "place-results__list";
        ul.setAttribute("role", "listbox");
        ul.setAttribute("aria-label", results.getAttribute("aria-label") || "");
        results.appendChild(ul);
      }
      var old = ul.querySelectorAll("[data-place], [data-group]");
      for (var k = 0; k < old.length; k++) {
        ul.removeChild(old[k]);
      }
      if (ul.firstChild) {
        ul.insertBefore(heading(mapEl.getAttribute("data-t-group-airports") || "", "airports"), ul.firstChild);
      }
      ul.appendChild(heading(mapEl.getAttribute("data-t-group-places") || "", "places"));
      rows.forEach(function (row, at) {
        ul.appendChild(placeRow(row, at));
      });
      results.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function run() {
      var query = typed();
      if (query.length < min || typeof window.fetch !== "function") {
        return;
      }
      query = query.slice(0, max);
      var key = query.toLowerCase();
      if (Object.prototype.hasOwnProperty.call(cache, key)) {
        show(cache[key], typed());
        return;
      }
      var wait = lastStart + lockMs - Date.now();
      if (inFlight || wait > 0) {
        timer = window.setTimeout(run, Math.max(wait, 300));
        return;
      }
      inFlight = true;
      lastStart = Date.now();
      window.fetch(api.url(query), {
        credentials: "omit",
        referrerPolicy: "origin"
      }).then(function (response) {
        if (!response.ok) {
          throw new Error("search failed");
        }
        return response.json();
      }).then(function (list) {
        if (Array.isArray(list)) {
          cache[key] = list;
          show(list, typed());
        }
      }).then(function () {
        inFlight = false;
      }, function () {
        inFlight = false;
      });
    }

    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(run, DEBOUNCE_MS);
    });
    // A submitted search runs on its own: the pending suggestion is dropped.
    input.form.addEventListener("submit", function () {
      window.clearTimeout(timer);
    });
  }

  wireUnifiedSearch();

  var detailsSummary = document.querySelector("#details > summary");
  if (detailsSummary) {
    // With the map the details are a card shown by the #details link: its
    // title is a heading, not a toggle.
    detailsSummary.addEventListener("click", function (event) {
      event.preventDefault();
    });
  }
}());
