/*
 * SkyPane companion service - place-map.js.
 *
 * First-party glue between the Location and detection page and the vendored
 * Leaflet library (loaded first, global `L`): the map, the draggable pin, the
 * area circle, the airport dots and the coordinate fields kept in step with
 * them. No build step, ES5-safe subset. Served by companion/static_files.py's
 * PLACE_MAP_SCRIPT_ROUTE and loaded on that one page only.
 *
 * Everything the script shows in words arrives as `data-t-*` attributes on
 * #place-map, so this file holds no language. The page is complete without
 * it: `map-ready` is added to the page element only once the map runs, and a
 * missing or failing library leaves the plain form as it is.
 *
 * The only requests are the tile pictures the library asks the tile host for
 * (one constant below, no subdomains, no prefetch) and, on a submitted place
 * search, one request to the search service. The position is read from the
 * browser only on a tap. Nothing is stored.
 */
(function () {
  "use strict";

  // The one tile source. Moving to another provider means changing this line.
  var TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  // The tile host's policy asks for a valid Referer; the page's own
  // Referrer-Policy is same-origin, so the layer overrides it per request.
  var TILE_REFERRER_POLICY = "origin";
  var COPYRIGHT_URL = "https://www.openstreetmap.org/copyright";
  // The one search endpoint; moving to another service means changing this line.
  var SEARCH_URL = "https://nominatim.openstreetmap.org/search";
  var SEARCH_REFERRER_POLICY = "origin";
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
  var MAX_ZOOM = 18;
  var FRANCE_CENTRE = [46.6, 2.5];
  var AIRPORT_ZOOM = 13;
  var DOT_MIN_ZOOM = 8;
  var TILE_ERRORS_BEFORE_NOTICE = 4;
  var NEAREST_AIRPORT_KM = 3;
  var COORD_DECIMALS = 4;
  var RADIUS_MIN_KM = 2;
  var RADIUS_MAX_KM = 28;
  var READY_CLASS = "map-ready";

  var mapEl = document.getElementById("place-map");
  if (!mapEl) {
    return;
  }

  // Without the library the map container has nothing to show: hide it and
  // leave the plain form (the fallback explanation stays visible).
  function giveUp() {
    mapEl.hidden = true;
  }

  if (typeof L === "undefined" || typeof L.map !== "function") {
    giveUp();
    return;
  }

  function byId(id) {
    return document.getElementById(id);
  }

  var latField = byId("place-lat");
  var lonField = byId("place-lon");
  var labelField = byId("place-label");
  var radiusField = byId("place-radius");
  var statusEl = byId("place-status");
  var noticeEl = byId("place-notice");
  var detailsEl = byId("details");

  function text(key) {
    return mapEl.getAttribute("data-t-" + key) || "";
  }

  // Replaces %s and %d in order, once each.
  function format(template) {
    var args = Array.prototype.slice.call(arguments, 1);
    var at = 0;
    return template.replace(/%[sd]/g, function (match) {
      var value = args[at];
      at += 1;
      return match === "%d" ? String(Math.round(value)) : String(value);
    });
  }

  function escapeText(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function parseNumber(value) {
    var n = parseFloat(value);
    return isFinite(n) ? n : null;
  }

  function clamp(value, low, high) {
    return Math.min(high, Math.max(low, value));
  }

  function roundCoord(value) {
    var f = Math.pow(10, COORD_DECIMALS);
    return Math.round(value * f) / f;
  }

  function fire(field, type) {
    var event = document.createEvent("Event");
    event.initEvent(type, true, false);
    field.dispatchEvent(event);
  }

  function setStatus(message) {
    if (statusEl) {
      statusEl.textContent = message;
    }
  }

  function showNotice(message) {
    if (noticeEl) {
      noticeEl.textContent = message;
      noticeEl.hidden = false;
    }
  }

  function hideNotice() {
    if (noticeEl) {
      noticeEl.hidden = true;
    }
  }

  // --- Server-rendered catalogue (never fetched) ---------------------------

  var airports = [];
  var anchors = document.querySelectorAll("a[data-icao][data-lat][data-lon]");
  for (var i = 0; i < anchors.length; i++) {
    var lat = parseNumber(anchors[i].getAttribute("data-lat"));
    var lon = parseNumber(anchors[i].getAttribute("data-lon"));
    if (lat !== null && lon !== null) {
      airports.push({
        icao: anchors[i].getAttribute("data-icao"),
        name: anchors[i].getAttribute("data-name") || "",
        lat: lat,
        lon: lon,
        anchor: anchors[i]
      });
    }
  }

  // Choosing an airport is the list's own navigation: the server renders the
  // runway cards, the pin and the label for it, so a dot follows its link.
  function chooseAirport(airport) {
    airport.anchor.click();
  }

  function distanceKm(lat1, lon1, lat2, lon2) {
    var rad = Math.PI / 180;
    var dLat = (lat2 - lat1) * rad;
    var dLon = (lon2 - lon1) * rad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  // --- The map --------------------------------------------------------------

  var startLat = parseNumber(mapEl.getAttribute("data-lat"));
  var startLon = parseNumber(mapEl.getAttribute("data-lon"));
  var startZoom = parseInt(mapEl.getAttribute("data-zoom"), 10) || 5;
  var hasStartPin = startLat !== null && startLon !== null;

  var map = null;
  var pin = null;
  var circle = null;
  var syncing = false;
  var dots = {};
  var dotLayer = null;

  var tilesLoaded = false;
  var tileErrors = 0;

  function buildMap() {
    map = L.map(mapEl, {
      zoomControl: false,
      attributionControl: true,
      maxZoom: MAX_ZOOM,
      center: hasStartPin ? [startLat, startLon] : FRANCE_CENTRE,
      zoom: hasStartPin ? startZoom : 5
    });
    L.control.zoom({
      zoomInTitle: text("zoom-in"),
      zoomOutTitle: text("zoom-out")
    }).addTo(map);
    map.attributionControl.setPrefix(false);
    var tiles = L.tileLayer(TILE_URL, {
      maxZoom: MAX_ZOOM,
      attribution: '<a href="' + COPYRIGHT_URL + '" target="_blank" ' +
        'rel="noopener noreferrer">' + escapeText(text("attribution")) + "</a>",
      referrerPolicy: TILE_REFERRER_POLICY
    });
    tiles.on("tileload", function () {
      tilesLoaded = true;
      hideNotice();
    });
    tiles.on("tileerror", function () {
      tileErrors += 1;
      if (!tilesLoaded && tileErrors >= TILE_ERRORS_BEFORE_NOTICE) {
        showNotice(text("tiles-failed"));
      }
    });
    tiles.addTo(map);
  }

  // --- Pin, circle, fields ---------------------------------------------------

  function pinIcon() {
    return L.divIcon({
      className: "place-pin",
      html: '<svg class="icon place-pin__glyph" width="36" height="36" ' +
        'aria-hidden="true" focusable="false"><use href="#icon-pin"></use></svg>',
      iconSize: [44, 44],
      iconAnchor: [22, 42]
    });
  }

  function areaWanted() {
    var radio = byId("place-mode-area");
    return !!(radio && radio.checked);
  }

  function radiusKm() {
    var km = radiusField ? parseNumber(radiusField.value) : null;
    if (km === null) {
      km = parseNumber(mapEl.getAttribute("data-radius-km"));
    }
    return km === null ? null : clamp(km, RADIUS_MIN_KM, RADIUS_MAX_KM);
  }

  function drawCircle() {
    var km = radiusKm();
    if (!pin || !areaWanted() || km === null) {
      if (circle) {
        map.removeLayer(circle);
        circle = null;
      }
      return;
    }
    if (!circle) {
      circle = L.circle(pin.getLatLng(), {
        radius: km * 1000,
        className: "place-circle",
        interactive: false
      }).addTo(map);
    } else {
      circle.setLatLng(pin.getLatLng());
      circle.setRadius(km * 1000);
    }
  }

  function writeFields(latlng) {
    if (!latField || !lonField) {
      return;
    }
    syncing = true;
    latField.value = roundCoord(latlng.lat).toFixed(COORD_DECIMALS);
    lonField.value = roundCoord(latlng.lng).toFixed(COORD_DECIMALS);
    fire(latField, "input");
    fire(lonField, "input");
    syncing = false;
  }

  function announce(latlng) {
    setStatus(format(
      text("pin-placed"), roundCoord(latlng.lat).toFixed(COORD_DECIMALS),
      roundCoord(latlng.lng).toFixed(COORD_DECIMALS)));
  }

  function afterPinMoved(latlng, fromFields) {
    drawCircle();
    if (!fromFields) {
      writeFields(latlng);
    }
    announce(latlng);
    pinMoved(latlng);
  }

  // Drops the pin, or moves it. Options: `zoom` to set one, `fromFields` when
  // the fields are the source (they are not rewritten), `pan` to centre.
  function placePin(latlng, options) {
    var opts = options || {};
    var point = L.latLng(
      clamp(latlng.lat, -90, 90), clamp(latlng.lng, -180, 180));
    if (!pin) {
      pin = L.marker(point, {
        icon: pinIcon(),
        draggable: true,
        keyboard: false,
        autoPan: true,
        zIndexOffset: 1000
      }).addTo(map);
      pin.on("drag", function () {
        drawCircle();
      });
      pin.on("dragend", function () {
        afterPinMoved(pin.getLatLng(), false);
      });
    } else {
      pin.setLatLng(point);
    }
    if (opts.zoom) {
      map.setView(point, opts.zoom, { animate: !!opts.animate });
    } else if (opts.pan) {
      map.panTo(point);
    }
    afterPinMoved(point, !!opts.fromFields);
  }

  // --- Nearest airport ----------------------------------------------------------

  var nearestEl = byId("place-nearest");

  function currentAirportCode() {
    var field = document.querySelector("input[name='airport'][form]");
    return field ? field.value : "";
  }

  function nearestAirport(latlng) {
    var best = null;
    var bestKm = Infinity;
    for (var k = 0; k < airports.length; k++) {
      var km = distanceKm(latlng.lat, latlng.lng, airports[k].lat, airports[k].lon);
      if (km < bestKm) {
        best = airports[k];
        bestKm = km;
      }
    }
    return best && bestKm <= NEAREST_AIRPORT_KM ? { airport: best, km: bestKm } : null;
  }

  // Offers the catalogue airport under the pin, unless it already is the one
  // the runway choice follows.
  function pinMoved(latlng) {
    if (!nearestEl) {
      return;
    }
    var found = nearestAirport(latlng);
    var runway = byId("place-mode-runway");
    var following = found && runway && runway.checked &&
      currentAirportCode() === found.airport.icao;
    if (!found || following) {
      nearestEl.hidden = true;
      return;
    }
    var line = nearestEl.querySelector(".place-nearest__text");
    var button = nearestEl.querySelector(".place-nearest__button");
    line.textContent = format(
      text("nearest"), found.airport.name, Math.max(1, Math.round(found.km)));
    button.textContent = format(text("follow"), found.airport.name);
    button.onclick = function () {
      chooseAirport(found.airport);
    };
    nearestEl.hidden = false;
  }

  function fieldsPoint() {
    if (!latField || !lonField) {
      return null;
    }
    var lat = parseNumber(latField.value);
    var lon = parseNumber(lonField.value);
    if (lat === null || lon === null || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      return null;
    }
    return L.latLng(lat, lon);
  }

  function onFieldEdited() {
    if (syncing) {
      return;
    }
    var point = fieldsPoint();
    if (point) {
      placePin(point, { fromFields: true, pan: true });
    }
  }

  // --- Airport dots ----------------------------------------------------------

  function dotIcon(airport) {
    return L.divIcon({
      className: "place-dot",
      html: '<span class="place-dot__mark" data-icao="' + escapeText(airport.icao) +
        '"></span>',
      iconSize: [44, 44],
      iconAnchor: [22, 22]
    });
  }

  function refreshDots() {
    if (!dotLayer) {
      return;
    }
    var wanted = {};
    if (map.getZoom() >= DOT_MIN_ZOOM) {
      var bounds = map.getBounds().pad(0.25);
      for (var k = 0; k < airports.length; k++) {
        if (bounds.contains([airports[k].lat, airports[k].lon])) {
          wanted[airports[k].icao] = airports[k];
        }
      }
    }
    var icao;
    for (icao in dots) {
      if (Object.prototype.hasOwnProperty.call(dots, icao) && !wanted[icao]) {
        dotLayer.removeLayer(dots[icao]);
        delete dots[icao];
      }
    }
    for (icao in wanted) {
      if (Object.prototype.hasOwnProperty.call(wanted, icao) && !dots[icao]) {
        dots[icao] = makeDot(wanted[icao]);
        dotLayer.addLayer(dots[icao]);
      }
    }
  }

  function makeDot(airport) {
    var marker = L.marker([airport.lat, airport.lon], {
      icon: dotIcon(airport),
      keyboard: false,
      riseOnHover: false
    });
    marker.on("click", function () {
      chooseAirport(airport);
    });
    return marker;
  }

  // --- Search by city or address ------------------------------------------------

  var searchForm = document.querySelector("form.place-search");
  var searchInput = byId("place-search");
  var resultsEl = byId("place-results");
  var searchMin = parseInt(mapEl.getAttribute("data-search-min"), 10) || 3;
  var searchMax = parseInt(mapEl.getAttribute("data-search-max"), 10) || 120;
  var searchLockMs = parseInt(mapEl.getAttribute("data-search-lock-ms"), 10) || 1500;
  var searchBusy = false;
  var searchLocked = false;
  var searchCache = {};

  function setSearchDisabled(disabled) {
    var button = searchForm.querySelector("button[type='submit']");
    if (button) {
      button.disabled = disabled;
    }
  }

  function clearResults() {
    while (resultsEl.firstChild) {
      resultsEl.removeChild(resultsEl.firstChild);
    }
    resultsEl.hidden = true;
  }

  function showResultsNote(message) {
    clearResults();
    var note = document.createElement("p");
    note.className = "place-results__note text-label";
    note.textContent = message;
    resultsEl.appendChild(note);
    resultsEl.hidden = false;
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
    placePin(L.latLng(result.lat, result.lon), { zoom: result.zoom, animate: true });
    fillLabel(result.name);
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
    clearResults();
    var ul = document.createElement("ul");
    ul.className = "place-results__list";
    rows.forEach(function (result) {
      var li = document.createElement("li");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "place-result";
      var nameEl = document.createElement("span");
      nameEl.className = "place-result__name";
      nameEl.textContent = result.name;
      button.appendChild(nameEl);
      if (result.rest) {
        var restEl = document.createElement("span");
        restEl.className = "place-result__rest text-label";
        restEl.textContent = result.rest;
        button.appendChild(restEl);
      }
      button.addEventListener("click", function () {
        chooseResult(result);
      });
      li.appendChild(button);
      ul.appendChild(li);
    });
    resultsEl.appendChild(ul);
    resultsEl.hidden = false;
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

  // The one place a request leaves for the search service: a submitted query,
  // one at a time, then a lock for the length the service's policy asks for.
  function runSearch(query, key) {
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
    if (typeof window.fetch !== "function") {
      failed();
      done();
      return;
    }
    window.fetch(searchUrl(query), {
      credentials: "omit",
      referrerPolicy: SEARCH_REFERRER_POLICY
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("search failed");
      }
      return response.json();
    }).then(function (list) {
      if (!Array.isArray(list)) {
        throw new Error("search failed");
      }
      searchCache[key] = list;
      renderResults(list);
    }).then(done, function () {
      failed();
      done();
    });
  }

  function onSearchSubmit(event) {
    event.preventDefault();
    if (searchBusy || searchLocked) {
      return;
    }
    var query = searchInput.value.replace(/\s+/g, " ").replace(/^ | $/g, "");
    if (query.length < searchMin) {
      showResultsNote(text("search-short"));
      return;
    }
    query = query.slice(0, searchMax);
    var key = query.toLowerCase();
    if (Object.prototype.hasOwnProperty.call(searchCache, key)) {
      renderResults(searchCache[key]);
      return;
    }
    runSearch(query, key);
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

  function onPosition(position) {
    setLocateBusy(false);
    var point = L.latLng(
      roundCoord(position.coords.latitude), roundCoord(position.coords.longitude));
    placePin(point, { zoom: LOCATE_ZOOM, animate: true });
    setStatus(format(text("located"), position.coords.accuracy || 0));
  }

  function onPositionError(error) {
    setLocateBusy(false);
    var key = "locate-unavailable";
    if (error && error.code === 1) {
      key = "locate-denied";
    } else if (error && error.code === 3) {
      key = "locate-timeout";
    }
    setStatus(text(key));
  }

  function onLocateClick() {
    if (locating) {
      return;
    }
    setLocateBusy(true);
    setStatus(text("locating"));
    navigator.geolocation.getCurrentPosition(onPosition, onPositionError, {
      enableHighAccuracy: false,
      timeout: LOCATE_TIMEOUT_MS,
      maximumAge: LOCATE_MAX_AGE_MS
    });
  }

  function wireSearchAndLocate() {
    if (searchForm && searchInput && resultsEl) {
      searchForm.addEventListener("submit", onSearchSubmit);
    }
    if (locateButton) {
      if (!navigator.geolocation) {
        locateButton.hidden = true;
      } else {
        locateButton.addEventListener("click", onLocateClick);
      }
    }
  }

  // --- Start ------------------------------------------------------------------

  function start() {
    buildMap();
    dotLayer = L.layerGroup().addTo(map);
    map.on("click", function (event) {
      placePin(event.latlng, {});
    });
    map.on("moveend zoomend", refreshDots);
    if (hasStartPin) {
      placePin(L.latLng(startLat, startLon), { fromFields: true });
      setStatus("");
    }
    refreshDots();

    if (latField) {
      latField.addEventListener("input", onFieldEdited);
      latField.addEventListener("change", onFieldEdited);
    }
    if (lonField) {
      lonField.addEventListener("input", onFieldEdited);
      lonField.addEventListener("change", onFieldEdited);
    }
    if (radiusField) {
      radiusField.addEventListener("input", drawCircle);
      radiusField.addEventListener("change", drawCircle);
    }
    document.addEventListener("change", function (event) {
      if (event.target && event.target.name === "mode") {
        drawCircle();
        if (pin) {
          pinMoved(pin.getLatLng());
        }
      }
    });
    wireSearchAndLocate();

    // Scripts and the library are up: the fields tuck away, the form stays
    // the way to type a place. A refused save keeps its card open.
    if (detailsEl && !detailsEl.querySelector("[aria-invalid='true']")) {
      detailsEl.open = false;
    }
    document.documentElement.className += " " + READY_CLASS;
  }

  try {
    start();
  } catch (error) {
    // A half-built map is worse than none: drop it and keep the plain form.
    if (map) {
      try {
        map.remove();
      } catch (ignored) {
        map = null;
      }
    }
    giveUp();
    var classes = document.documentElement.className.split(" ");
    document.documentElement.className = classes.filter(function (name) {
      return name !== READY_CLASS;
    }).join(" ");
  }
}());
