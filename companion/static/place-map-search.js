/*
 * SkyPane companion service - place-map-search.js.
 *
 * The search box, its airport and address suggestions and the "use my
 * position" button of the Location and detection page. place-start.js loads it
 * right after place-map.js, which hands over the helpers it shares with this
 * file as `window.skypanePlaceMapCore` once the map is up (no map, nothing to
 * wire: the search form stays the plain form). The only requests are one
 * address search per submit or typed pause, through the gate in
 * place-search.js. ES5-safe subset.
 */
(function () {
  "use strict";

  var core = window.skypanePlaceMapCore;
  if (!core) {
    return;
  }
  delete window.skypanePlaceMapCore;

  var MESSAGE_MS = core.MESSAGE_MS;
  var airportForQuery = core.airportForQuery;
  var airports = core.airports;
  var byId = core.byId;
  var chooseAirport = core.chooseAirport;
  var chooseAreaMode = core.chooseAreaMode;
  var fire = core.fire;
  var foldText = core.foldText;
  var format = core.format;
  var labelField = core.labelField;
  var mapEl = core.mapEl;
  var parseNumber = core.parseNumber;
  var placePin = core.placePin;
  var roundCoord = core.roundCoord;
  var setStatus = core.setStatus;
  var showMessage = core.showMessage;
  var text = core.text;

  // The one search endpoint; moving to another service means changing this line.
  var SEARCH_URL = "https://nominatim.openstreetmap.org/search";
  var SEARCH_RESULT_LIMIT = 5;
  var STREET_ZOOM = 15;
  var CITY_ZOOM = 12;
  var LOCATE_ZOOM = 14;
  var LOCATE_TIMEOUT_MS = 10000;
  var LOCATE_MAX_AGE_MS = 60000;
  // Result kinds a person means a street address by: zoom in close for these.
  var STREET_KINDS = [
    "house", "building", "road", "street", "residential", "pedestrian", "path",
    "footway", "service", "living_street", "unclassified", "tertiary", "secondary",
    "primary", "amenity", "shop", "tourism", "office"
  ];
  var SUGGEST_MAX = 6;
  var SUGGEST_MIN_CHARS = 2;
  var LOCATE_GUARD_MS = LOCATE_TIMEOUT_MS + 3000;

  var searchForm = document.querySelector("form.place-search");
  var searchInput = byId("place-search");
  var resultsEl = byId("place-results");

  // --- Search by city or address ------------------------------------------------

  var searchMin = parseInt(mapEl.getAttribute("data-search-min"), 10) || 3;
  var searchMax = parseInt(mapEl.getAttribute("data-search-max"), 10) || 120;
  var searchLockMs = parseInt(mapEl.getAttribute("data-search-lock-ms"), 10) || 1500;
  var searchBusy = false;
  var searchLocked = false;

  function setSearchDisabled(disabled) {
    var button = searchForm.querySelector("button[type='submit']");
    if (button) {
      button.disabled = disabled;
    }
  }

  var noteTimer = null;
  var activeOption = -1;

  function clearResults() {
    window.clearTimeout(noteTimer);
    while (resultsEl.firstChild) {
      resultsEl.removeChild(resultsEl.firstChild);
    }
    resultsEl.hidden = true;
    activeOption = -1;
    if (searchInput) {
      searchInput.setAttribute("aria-expanded", "false");
      searchInput.removeAttribute("aria-activedescendant");
    }
  }

  function showResultsNote(message) {
    clearResults();
    var note = document.createElement("p");
    note.className = "place-results__note text-label";
    note.textContent = message;
    resultsEl.appendChild(note);
    resultsEl.hidden = false;
    // A note is read once and goes: it never stays over the controls.
    noteTimer = window.setTimeout(clearResults, MESSAGE_MS);
  }

  // Reads one search answer row into a safe record, or null when it has no
  // usable position. Every field is treated as untrusted text.
  function readResult(item) {
    if (!item || typeof item !== "object") {
      return null;
    }
    var lat = parseNumber(item.lat);
    var lon = parseNumber(item.lon);
    if (lat === null || lon === null || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      return null;
    }
    var display = typeof item.display_name === "string" ? item.display_name : "";
    var parts = display.split(",").map(function (part) {
      return part.replace(/^\s+|\s+$/g, "");
    }).filter(function (part) {
      return part.length > 0;
    });
    var name = typeof item.name === "string" && item.name ? item.name : (parts[0] || "");
    if (!name) {
      return null;
    }
    if (parts.length && parts[parts.length - 1].toLowerCase() === "france") {
      parts.pop();
    }
    var rest = parts.slice(1).join(", ");
    var kind = String(item.addresstype || item.type || "").toLowerCase();
    return {
      name: name,
      rest: rest,
      lat: lat,
      lon: lon,
      zoom: STREET_KINDS.indexOf(kind) >= 0 ? STREET_ZOOM : CITY_ZOOM
    };
  }

  function fillLabel(name) {
    if (labelField && labelField.value.replace(/\s+/g, "") === "") {
      labelField.value = name.slice(0, 60);
      fire(labelField, "input");
    }
  }

  function chooseResult(result) {
    clearResults();
    chooseAreaMode();
    placePin(L.latLng(result.lat, result.lon), { zoom: result.zoom, animate: true });
    fillLabel(result.name);
  }

  // The one list under the search field, for typed airport suggestions and
  // for submitted address results alike: a listbox of option buttons, each
  // with a name and a smaller line. `rows` hold `name`, `rest` and `choose`.
  function showOptions(rows) {
    clearResults();
    var ul = document.createElement("ul");
    ul.className = "place-results__list";
    ul.setAttribute("role", "listbox");
    ul.setAttribute("aria-label", resultsEl.getAttribute("aria-label") || "");
    rows.forEach(function (row, at) {
      var li = document.createElement("li");
      li.setAttribute("role", "presentation");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "place-result";
      button.id = "place-option-" + at;
      button.tabIndex = -1;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", "false");
      var nameEl = document.createElement("span");
      nameEl.className = "place-result__name";
      nameEl.textContent = row.name;
      button.appendChild(nameEl);
      if (row.rest) {
        var restEl = document.createElement("span");
        restEl.className = "place-result__rest text-label";
        restEl.textContent = row.rest;
        button.appendChild(restEl);
      }
      button.title = row.rest ? row.name + " - " + row.rest : row.name;
      button.addEventListener("click", row.choose);
      li.appendChild(button);
      ul.appendChild(li);
    });
    resultsEl.appendChild(ul);
    resultsEl.hidden = false;
    searchInput.setAttribute("aria-expanded", "true");
  }

  function renderResults(list) {
    var rows = [];
    for (var n = 0; n < list.length && rows.length < SEARCH_RESULT_LIMIT; n++) {
      var row = readResult(list[n]);
      if (row) {
        rows.push(row);
      }
    }
    if (!rows.length) {
      showResultsNote(text("search-none"));
      return;
    }
    showOptions(rows.map(function (result) {
      return {
        name: result.name,
        rest: result.rest,
        choose: function () {
          chooseResult(result);
        }
      };
    }));
  }

  // Airports whose code, name or municipality starts with or contains what
  // was typed, best first: an exact code, a code prefix, a name or
  // municipality prefix, a word prefix, then any part. Answered from the
  // page's own catalogue; nothing leaves the browser while typing.
  function suggestAirports(query) {
    var wanted = foldText(query);
    if (wanted.length < SUGGEST_MIN_CHARS) {
      return [];
    }
    var found = [];
    airports.forEach(function (airport) {
      var f = airport.folded;
      var rank = 9;
      if (wanted === f[0] || wanted === f[1]) {
        rank = 0;
      } else if (f[0].indexOf(wanted) === 0 || f[1].indexOf(wanted) === 0) {
        rank = 1;
      } else if (f[2].indexOf(wanted) === 0 || f[3].indexOf(wanted) === 0) {
        rank = 2;
      } else if ((" " + f[2] + " " + f[3]).indexOf(" " + wanted) >= 0) {
        rank = 3;
      } else if (f[2].indexOf(wanted) >= 0 || f[3].indexOf(wanted) >= 0) {
        rank = 4;
      }
      if (rank < 9) {
        found.push({ airport: airport, rank: rank });
      }
    });
    found.sort(function (a, b) {
      return a.rank - b.rank || (a.airport.name < b.airport.name ? -1 : 1);
    });
    return found.slice(0, SUGGEST_MAX).map(function (entry) {
      return entry.airport;
    });
  }

  function showAirportSuggestions() {
    var matches = suggestAirports(searchInput.value);
    if (!matches.length) {
      clearResults();
      return;
    }
    showOptions(matches.map(function (airport) {
      var codes = [airport.iata, airport.icao].filter(Boolean).join(" · ");
      return {
        name: airport.name,
        rest: text("result-airport") + " · " + codes +
          (airport.city ? " · " + airport.city : ""),
        choose: function () {
          clearResults();
          chooseAirport(airport);
        }
      };
    }));
  }

  function optionButtons() {
    return resultsEl.querySelectorAll("button[role='option']");
  }

  function setActiveOption(at) {
    var options = optionButtons();
    for (var k = 0; k < options.length; k++) {
      var on = k === at;
      options[k].setAttribute("aria-selected", on ? "true" : "false");
      options[k].className = "place-result" + (on ? " is-active" : "");
      if (on) {
        searchInput.setAttribute("aria-activedescendant", options[k].id);
        if (typeof options[k].scrollIntoView === "function") {
          options[k].scrollIntoView({ block: "nearest" });
        }
      }
    }
    if (at < 0) {
      searchInput.removeAttribute("aria-activedescendant");
    }
    activeOption = at;
  }

  // Arrow keys move through the options (wrapping), Enter picks the active
  // one, Escape closes the list; with no active option Enter submits.
  function onSearchKey(event) {
    var options = optionButtons();
    if (event.key === "Escape") {
      // The first Escape closes the list and keeps the typed text (a search
      // field would clear itself); a second one is the field's own.
      if (!resultsEl.hidden) {
        event.preventDefault();
      }
      clearResults();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!options.length) {
        if (event.key === "ArrowDown") {
          showAirportSuggestions();
        }
        return;
      }
      event.preventDefault();
      var step = event.key === "ArrowDown" ? 1 : -1;
      var next = activeOption < 0 && step < 0 ? options.length - 1 : activeOption + step;
      setActiveOption((next + options.length) % options.length);
    } else if (event.key === "Enter" && activeOption >= 0 && options[activeOption]) {
      event.preventDefault();
      options[activeOption].click();
    }
  }

  function searchUrl(query) {
    var pairs = [
      ["format", "jsonv2"], ["q", query], ["countrycodes", "fr"],
      ["limit", String(SEARCH_RESULT_LIMIT)],
      ["accept-language", document.documentElement.lang === "fr" ? "fr" : "en"]
    ];
    return SEARCH_URL + "?" + pairs.map(function (pair) {
      return pair[0] + "=" + encodeURIComponent(pair[1]);
    }).join("&");
  }

  // A submitted query goes through the shared gate (place-search.js): one at
  // a time, spaced, answered from memory when it was asked before, and the
  // button stays off for the length the service's policy asks for.
  function runSearch(query) {
    searchBusy = true;
    setSearchDisabled(true);
    var done = function () {
      searchBusy = false;
      searchLocked = true;
      window.setTimeout(function () {
        searchLocked = false;
        setSearchDisabled(false);
      }, searchLockMs);
    };
    var failed = function () {
      showResultsNote(text("search-failed"));
    };
    var gate = window.skypaneSearchGate;
    if (!gate) {
      failed();
      done();
      return;
    }
    gate.search(query, searchUrl(query), "submit").then(function (list) {
      renderResults(list);
      done();
    }, function () {
      failed();
      done();
    });
  }

  function onSearchSubmit(event) {
    event.preventDefault();
    var query = searchInput.value.replace(/\s+/g, " ").replace(/^ | $/g, "");
    // An airport code or name is answered from the page's own list: the
    // airport's link opens the page for it, nothing leaves the browser.
    var airport = airportForQuery(query);
    if (airport) {
      clearResults();
      chooseAirport(airport);
      return;
    }
    if (searchBusy || searchLocked) {
      return;
    }
    if (query.length < searchMin) {
      showResultsNote(text("search-short"));
      return;
    }
    query = query.slice(0, searchMax);
    var remembered = window.skypaneSearchGate && window.skypaneSearchGate.cached(query);
    if (remembered) {
      renderResults(remembered);
      return;
    }
    // The typed suggestions give way to the answer, which replaces them.
    clearResults();
    runSearch(query);
  }

  // --- Use my position --------------------------------------------------------------

  var locateButton = byId("place-locate");
  var locating = false;

  function setLocateBusy(busy) {
    locating = busy;
    locateButton.disabled = busy;
    locateButton.setAttribute("aria-busy", busy ? "true" : "false");
    var label = locateButton.querySelector(".place-locate__label");
    if (label) {
      if (busy) {
        label.setAttribute("data-idle", label.textContent);
        label.textContent = text("locating");
      } else if (label.hasAttribute("data-idle")) {
        label.textContent = label.getAttribute("data-idle");
        label.removeAttribute("data-idle");
      }
    }
  }

  var locateGuard = null;

  function finishLocate() {
    window.clearTimeout(locateGuard);
    setLocateBusy(false);
  }

  // Reports in the status line (read aloud) and in the visible message.
  function report(message) {
    setStatus(message);
    showMessage(message);
  }

  // A found position follows the person: the mode becomes My position, the
  // pin sits on the spot and the map centres on it.
  function onPosition(position) {
    finishLocate();
    chooseAreaMode();
    var point = L.latLng(
      roundCoord(position.coords.latitude), roundCoord(position.coords.longitude));
    placePin(point, { zoom: LOCATE_ZOOM, animate: true });
    report(format(text("located"), position.coords.accuracy || 0));
  }

  function onPositionError(error) {
    finishLocate();
    var key = "locate-unavailable";
    if (error && error.code === 1) {
      key = "locate-denied";
    } else if (error && error.code === 3) {
      key = "locate-timeout";
    }
    report(text(key));
  }

  function onLocateClick() {
    if (locating) {
      return;
    }
    setLocateBusy(true);
    report(text("locating"));
    // Some browsers never answer a dismissed prompt: the button is freed
    // after the request's own timeout plus a margin.
    locateGuard = window.setTimeout(function () {
      onPositionError({ code: 3 });
    }, LOCATE_GUARD_MS);
    try {
      navigator.geolocation.getCurrentPosition(onPosition, onPositionError, {
        enableHighAccuracy: false,
        timeout: LOCATE_TIMEOUT_MS,
        maximumAge: LOCATE_MAX_AGE_MS
      });
    } catch (error) {
      onPositionError({ code: 2 });
    }
  }

  // What place-card.js needs to add typed address suggestions to the list.
  window.skypanePlaceSearch = { read: readResult, choose: chooseResult, url: searchUrl };

  function wireSearchAndLocate() {
    if (searchForm && searchInput && resultsEl) {
      searchForm.addEventListener("submit", onSearchSubmit);
      searchInput.setAttribute("role", "combobox");
      searchInput.setAttribute("aria-autocomplete", "list");
      searchInput.setAttribute("aria-controls", "place-results");
      searchInput.setAttribute("aria-expanded", "false");
      searchInput.addEventListener("keydown", onSearchKey);
      searchInput.addEventListener("input", showAirportSuggestions);
    }
    if (locateButton) {
      if (!navigator.geolocation) {
        locateButton.hidden = true;
      } else {
        locateButton.addEventListener("click", onLocateClick);
      }
    }
  }

  // The map's click handler clears the open suggestions through this hook.
  core.clearResults = clearResults;
  wireSearchAndLocate();
}());
