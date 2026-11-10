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
    var DEBOUNCE_MS = 500;
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

    function listbox() {
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
      return ul;
    }

    function clearStatus() {
      var old = results.querySelector("[data-status]");
      if (old) {
        old.parentNode.removeChild(old);
      }
    }

    // The last row of the list: a spinner and "Searching..." while the request
    // is pending, then "No place found" or a short error line. The results
    // replace it.
    function status(kind) {
      var ul = listbox();
      clearStatus();
      var li = document.createElement("li");
      li.className = "place-results__status text-label";
      li.setAttribute("role", "presentation");
      li.setAttribute("data-status", kind);
      if (kind === "searching") {
        var spinner = document.createElement("span");
        spinner.className = "place-loading__spinner";
        spinner.setAttribute("aria-hidden", "true");
        li.appendChild(spinner);
      }
      li.appendChild(document.createTextNode(mapEl.getAttribute("data-t-row-" + kind) || ""));
      ul.appendChild(li);
      results.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function show(list, query) {
      if (typed().slice(0, max) !== query) {
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
        status("none");
        return;
      }
      var ul = listbox();
      clearStatus();
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
        show(cache[key], query);
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
          show(list, query);
        }
      }).then(function () {
        inFlight = false;
      }, function () {
        inFlight = false;
        if (typed().slice(0, max) === query) {
          status("failed");
        }
      });
    }

    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(run, DEBOUNCE_MS);
      // place-map.js has just listed the airport matches (its own input
      // listener runs first): the pending search is shown under them at once.
      var query = typed().slice(0, max);
      if (query.length >= min && typeof window.fetch === "function" &&
          !Object.prototype.hasOwnProperty.call(cache, query.toLowerCase())) {
        status("searching");
      }
    });
    // A submitted search runs on its own: the pending suggestion is dropped.
    input.form.addEventListener("submit", function () {
      window.clearTimeout(timer);
      clearStatus();
    });
  }

  wireUnifiedSearch();

  // On a phone the nearest-airport offer is one line over the map, above the
  // bottom buttons, so it never lifts the sheet over the pin just dropped; a
  // wide screen keeps it as a card in the sheet.
  function wireNearestPlacement() {
    var offer = document.getElementById("place-nearest");
    var tools = document.querySelector(".place-tools");
    var sheet = offer && offer.parentNode;
    if (!offer || !tools || !sheet || typeof window.matchMedia !== "function") {
      return;
    }
    var anchor = offer.nextElementSibling;
    var phone = window.matchMedia("(max-width: 699.98px)");
    function place() {
      if (phone.matches) {
        tools.insertBefore(offer, tools.firstChild);
      } else {
        sheet.insertBefore(offer, anchor);
      }
    }
    if (typeof phone.addEventListener === "function") {
      phone.addEventListener("change", place);
    }
    place();
  }

  wireNearestPlacement();

  // An airport's code label that meets the details card, the sheet or a
  // control floating over the map is hidden while it does, so a label never
  // pokes out from under (or over) them.
  function wireLabelClearance() {
    var mapEl = document.getElementById("place-map");
    var overlays = [".place-card", ".place-sheet", ".place-float", ".place-modes",
      ".place-tools", ".place-info", ".place-pos"];
    var queued = false;

    function boxes() {
      var found = [];
      overlays.forEach(function (selector) {
        var list = document.querySelectorAll(selector);
        for (var n = 0; n < list.length; n++) {
          var box = list[n].getBoundingClientRect();
          if (box.width > 0 && box.height > 0) {
            found.push(box);
          }
        }
      });
      return found;
    }

    function meets(a, b) {
      return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    }

    function sweep() {
      queued = false;
      var covers = boxes();
      var frame = mapEl.getBoundingClientRect();
      var labels = mapEl.querySelectorAll(".place-dot__label");
      for (var n = 0; n < labels.length; n++) {
        var label = labels[n].getBoundingClientRect();
        var hide = label.left < frame.left || label.right > frame.right ||
          label.top < frame.top || label.bottom > frame.bottom;
        for (var k = 0; k < covers.length && !hide; k++) {
          hide = meets(label, covers[k]);
        }
        labels[n].classList.toggle("place-dot__label--covered", hide);
      }
      // A pan or zoom glides on a CSS transition without touching an
      // attribute: keep sweeping every frame until it has finished.
      if (typeof mapEl.getAnimations === "function" &&
          mapEl.getAnimations({ subtree: true }).length) {
        queue();
      }
    }

    function queue() {
      if (!queued) {
        queued = true;
        window.requestAnimationFrame(sweep);
      }
    }

    if (typeof window.MutationObserver === "function") {
      new window.MutationObserver(queue).observe(mapEl, {
        childList: true, subtree: true, attributes: true, attributeFilter: ["style", "class"]
      });
    }
    window.addEventListener("resize", queue);
    document.addEventListener("transitionrun", queue);
    document.addEventListener("transitionend", queue);
    queue();
  }

  wireLabelClearance();

  var detailsSummary = document.querySelector("#details > summary");
  if (detailsSummary) {
    // With the map the details are a card shown by the #details link: its
    // title is a heading, not a toggle.
    detailsSummary.addEventListener("click", function (event) {
      event.preventDefault();
    });
  }
}());
