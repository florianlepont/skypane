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
 * (one constant below, no subdomains, no prefetch) and, on a submitted
 * address search, one request to the search service (a submitted airport code
 * or name is answered from the page's own list, no request). The position is
 * read from the browser only on a tap. Nothing is stored.
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
  var AIRPORT_ZOOM = 12;
  var FRANCE_ZOOM = 5;
  // Airports closer than one grid cell (in screen pixels) at a zoom below
  // CLUSTER_MAX_ZOOM + 1 are drawn as one numbered bubble.
  var CLUSTER_CELL_PX = 64;
  var CLUSTER_MAX_ZOOM = 11;
  // How far past the screen (as a share of its size) pins are kept.
  var PIN_MARGIN = 0.5;
  var LABEL_MIN_ZOOM = 6;
  var SUGGEST_MAX = 6;
  var SUGGEST_MIN_CHARS = 2;
  var TILE_ERRORS_BEFORE_NOTICE = 4;
  var NEAREST_AIRPORT_KM = 3;
  var COORD_DECIMALS = 4;
  var RADIUS_MIN_KM = 2;
  var RADIUS_MAX_KM = 28;
  var READY_CLASS = "map-ready";
  // Set on the page element by the head script while scripts run: the loading
  // state shows instead of the plain form. A map that cannot start clears it.
  var EARLY_CLASS = "js-early";
  var MESSAGE_MS = 8000;
  var LOCATE_GUARD_MS = LOCATE_TIMEOUT_MS + 3000;

  var mapEl = document.getElementById("place-map");
  if (!mapEl) {
    return;
  }

  // Without the library the map container has nothing to show: hide it and
  // leave the plain form (the fallback explanation stays visible).
  function giveUp() {
    mapEl.hidden = true;
    removeRootClass(EARLY_CLASS);
  }

  function removeRootClass(name) {
    var classes = document.documentElement.className.split(" ");
    document.documentElement.className = classes.filter(function (cls) {
      return cls !== name;
    }).join(" ");
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
  var loadingEl = byId("place-loading");
  var messageEl = byId("place-message");
  var rangeField = byId("place-radius-range");
  var cardEl = document.querySelector(".place-card");
  var sheetEl = document.querySelector(".place-sheet");
  var modesEl = document.querySelector(".place-modes");
  var DESKTOP_QUERY = "(min-width: 960px)";

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

  var messageTimer = null;

  // The visible message of the locate button; it fades after a few seconds.
  function showMessage(message) {
    if (!messageEl) {
      return;
    }
    messageEl.textContent = message;
    messageEl.hidden = !message;
    window.clearTimeout(messageTimer);
    if (message) {
      messageTimer = window.setTimeout(function () {
        messageEl.hidden = true;
      }, MESSAGE_MS);
    }
  }

  function showNotice(message) {
    if (noticeEl) {
      noticeEl.textContent = message;
      noticeEl.hidden = false;
    }
  }

  // The loading note shows from the moment the map is built until its first
  // pictures are in (or have failed, or the wait has run out), so the map is
  // never an unexplained blank.
  var LOADING_MAX_MS = 8000;
  var loadingTimer = 0;

  function setLoading(on) {
    if (!loadingEl) {
      return;
    }
    loadingEl.hidden = !on;
    window.clearTimeout(loadingTimer);
    if (on) {
      loadingTimer = window.setTimeout(function () {
        loadingEl.hidden = true;
      }, LOADING_MAX_MS);
    }
  }

  function hideNotice() {
    if (noticeEl) {
      noticeEl.hidden = true;
    }
  }

  // --- Server-rendered catalogue (never fetched) ---------------------------

  // Lower case, accents removed, spaces collapsed: how a typed word is
  // compared with an airport's code or name.
  function foldText(value) {
    var folded = String(value).toLowerCase();
    if (typeof folded.normalize === "function") {
      folded = folded.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }
    return folded.replace(/\s+/g, " ").replace(/^ | $/g, "");
  }

  // The whole catalogue arrives with the page as one attribute (rows of ICAO,
  // IATA, name, municipality, latitude, longitude), whatever the airport list
  // below is filtered to: every pin and every typed suggestion comes from it.
  var airports = [];
  (function readCatalogue() {
    var rows = [];
    try {
      rows = JSON.parse(mapEl.getAttribute("data-airports") || "[]");
    } catch (ignored) {
      rows = [];
    }
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var lat = Array.isArray(row) ? parseNumber(row[4]) : null;
      var lon = Array.isArray(row) ? parseNumber(row[5]) : null;
      if (lat !== null && lon !== null) {
        airports.push({
          icao: String(row[0]),
          iata: String(row[1] || ""),
          name: String(row[2] || ""),
          city: String(row[3] || ""),
          lat: lat,
          lon: lon,
          folded: [
            foldText(row[1] || ""), foldText(row[0]), foldText(row[2] || ""),
            foldText(row[3] || "")
          ]
        });
      }
    }
  }());

  var airportUrl = mapEl.getAttribute("data-airport-url") || "";

  // The fallback when the page cannot be updated in place: the page's own
  // navigation, carried through the form guard, which handles every
  // data-detection-nav click. The server renders everything for the airport.
  function navigateToAirport(airport) {
    var link = document.createElement("a");
    link.setAttribute("href", airportUrl.replace("__ICAO__", encodeURIComponent(airport.icao)));
    link.setAttribute("data-detection-nav", "");
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  var runwaysEl = byId("place-runways");
  var pickTicket = 0;
  // The runway group and the address the page opened with: Cancel
  // after an in-place pick puts them back.
  var openedRunways = [];
  var openedAddress = window.location.pathname + window.location.search;
  var pickedHere = false;

  function rememberOpened() {
    for (var k = 0; runwaysEl && k < runwaysEl.childNodes.length; k++) {
      openedRunways.push(runwaysEl.childNodes[k].cloneNode(true));
    }
  }

  // The form's Cancel (a native reset) restores the fields it holds; the
  // parts a pick swapped in place come back from what the page opened with.
  function restoreOpened() {
    if (!pickedHere) {
      return;
    }
    pickedHere = false;
    pickTicket += 1;
    while (runwaysEl.firstChild) {
      runwaysEl.removeChild(runwaysEl.firstChild);
    }
    openedRunways.forEach(function (node) {
      runwaysEl.appendChild(node.cloneNode(true));
    });
    if (dotLayer) {
      dotLayer.clearLayers();
      dots = {};
    }
    drawCircle();
    refreshDots();
    showCheckedRunway();
    var point = fieldsPoint();
    if (point) {
      placePin(point, { fromFields: true, pan: true });
    }
    if (window.history && typeof window.history.replaceState === "function") {
      try {
        window.history.replaceState(window.history.state, "", openedAddress);
      } catch (ignored) {
        return;
      }
    }
  }

  function wireCancel() {
    var form = document.querySelector("form[data-dirty-form]");
    if (form) {
      form.addEventListener("reset", function () {
        window.setTimeout(restoreOpened, 0);
      });
    }
  }

  // Moves the page to an airport without leaving it: the Airport mode is
  // chosen, the pin, the label and the coordinates follow the airport, the
  // map flies there, and the runway cards and the airport header are swapped
  // for the ones the server renders for that airport (fetched from the page's
  // own airport URL, so the data and the validation are the server's). The
  // address bar follows through history.replaceState. A failed fetch falls
  // back to the page's own navigation.
  function chooseAirport(airport) {
    if (!map || !runwaysEl || typeof window.fetch !== "function" ||
        typeof window.DOMParser !== "function") {
      navigateToAirport(airport);
      return;
    }
    pickTicket += 1;
    pickedHere = true;
    var ticket = pickTicket;
    if (searchInput) {
      searchInput.value = "";
    }
    var radio = byId("place-mode-runway");
    if (radio && !radio.checked) {
      radio.checked = true;
      fire(radio, "change");
    }
    if (labelField) {
      labelField.value = airport.name;
      fire(labelField, "input");
    }
    placePin(L.latLng(airport.lat, airport.lon), { zoom: AIRPORT_ZOOM, animate: true });
    var url = airportUrl.replace("__ICAO__", encodeURIComponent(airport.icao));
    window.fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "text/html" }
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("airport page " + response.status);
      }
      return response.text();
    }).then(function (html) {
      if (ticket !== pickTicket) {
        return;
      }
      var fresh = new window.DOMParser().parseFromString(html, "text/html")
        .getElementById("place-runways");
      if (!fresh) {
        throw new Error("no runway group");
      }
      showPickedAirport(airport, fresh);
    }).catch(function () {
      if (ticket === pickTicket) {
        navigateToAirport(airport);
      }
    });
  }

  function showPickedAirport(airport, fresh) {
    while (runwaysEl.firstChild) {
      runwaysEl.removeChild(runwaysEl.firstChild);
    }
    for (var k = 0; k < fresh.childNodes.length; k++) {
      runwaysEl.appendChild(document.importNode(fresh.childNodes[k], true));
    }
    if (dotLayer) {
      dotLayer.clearLayers();
      dots = {};
    }
    refreshDots();
    showCheckedRunway();
    if (pin) {
      pinMoved(pin.getLatLng());
    }
    var chosen = document.querySelector("input[name='airport'][form]");
    var runway = runwaysEl.querySelector("input[name='runway']:checked");
    // The form guard counts the differences from what the page opened with.
    fire(chosen || runway || runwaysEl, "change");
    if (runway) {
      fire(runway, "change");
    }
    setStatus(airport.name);
    keepAddressInStep(airport);
  }

  // The address now names the picked airport, the live mode and the radius,
  // exactly what the page's own navigation would have put there.
  function keepAddressInStep(airport) {
    if (!window.history || typeof window.history.replaceState !== "function") {
      return;
    }
    var pairs = ["airport=" + encodeURIComponent(airport.icao), "mode=runway"];
    if (radiusField && radiusField.value) {
      pairs.push("radius_km=" + encodeURIComponent(radiusField.value));
    }
    try {
      window.history.replaceState(
        window.history.state, "", window.location.pathname + "?" + pairs.join("&"));
    } catch (ignored) {
      return;
    }
  }

  // The airport whose ICAO or IATA code or whole name is what was typed.
  function airportForQuery(query) {
    var wanted = foldText(query);
    if (!wanted) {
      return null;
    }
    for (var k = 0; k < airports.length; k++) {
      var airport = airports[k];
      if (wanted === airport.folded[1] || wanted === airport.folded[2] ||
          (airport.iata && wanted === airport.folded[0])) {
        return airport;
      }
    }
    return null;
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

  function isDesktop() {
    return !!(window.matchMedia && window.matchMedia(DESKTOP_QUERY).matches);
  }

  // The parts of the map the card and the floating controls cover: on a wide
  // screen the card's width at the left, on a phone the sheet's height at the
  // bottom and the search field and the mode chips' height at the top.
  function coveredBy() {
    var none = { left: 0, top: 0, bottom: 0 };
    if (!sheetEl || !map) {
      return none;
    }
    var mapBox = mapEl.getBoundingClientRect();
    if (isDesktop()) {
      var card = (cardEl || sheetEl).getBoundingClientRect();
      return { left: Math.max(0, card.right - mapBox.left), top: 0, bottom: 0 };
    }
    var top = 0;
    var floating = [searchForm, modesEl];
    for (var k = 0; k < floating.length; k++) {
      if (floating[k]) {
        top = Math.max(top, floating[k].getBoundingClientRect().bottom - mapBox.top);
      }
    }
    var sheet = sheetEl.getBoundingClientRect();
    return { left: 0, top: top, bottom: Math.max(0, mapBox.bottom - sheet.top) };
  }

  // The map centre that puts `point` in the middle of the uncovered part.
  function visibleCentre(point, zoom) {
    var covered = coveredBy();
    var shift = L.point(covered.left / 2, (covered.top - covered.bottom) / 2);
    return map.unproject(map.project(point, zoom).subtract(shift), zoom);
  }

  function centreOn(point, zoom, animate) {
    var z = zoom || map.getZoom();
    map.setView(visibleCentre(point, z), z, { animate: !!animate });
  }

  function buildMap() {
    // Without a saved place the map opens on the airport the setting follows
    // (when there is one) rather than on the whole of France.
    var own = null;
    for (var k = 0; !hasStartPin && k < airports.length; k++) {
      if (airports[k].icao === mapEl.getAttribute("data-airport")) {
        own = airports[k];
      }
    }
    var start = hasStartPin ? [startLat, startLon] : own ? [own.lat, own.lon] : null;
    var zoom = hasStartPin ? startZoom : own ? AIRPORT_ZOOM : FRANCE_ZOOM;
    map = L.map(mapEl, {
      zoomControl: false,
      attributionControl: false,
      maxZoom: MAX_ZOOM,
      center: start || FRANCE_CENTRE,
      zoom: zoom
    });
    if (start) {
      centreOn(L.latLng(start[0], start[1]), zoom, false);
    }
    L.control.zoom({
      position: "topright",
      zoomInTitle: text("zoom-in"),
      zoomOutTitle: text("zoom-out")
    }).addTo(map);
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
        setLoading(false);
      }
    });
    // "load" fires once every tile in view has arrived or failed.
    tiles.on("load", function () {
      setLoading(false);
    });
    setLoading(true);
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

  function chooseAreaMode() {
    var radio = byId("place-mode-area");
    if (radio && !radio.checked) {
      radio.checked = true;
      fire(radio, "change");
    }
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

  function syncRange() {
    if (rangeField && radiusField) {
      var km = parseNumber(radiusField.value);
      if (km !== null) {
        rangeField.value = String(clamp(km, RADIUS_MIN_KM, RADIUS_MAX_KM));
      }
    }
  }

  function announce(latlng) {
    setStatus(format(
      text("pin-placed"), roundCoord(latlng.lat).toFixed(COORD_DECIMALS),
      roundCoord(latlng.lng).toFixed(COORD_DECIMALS)));
  }

  var tapHintEl = byId("place-tap-hint");
  var moveHintEl = byId("place-move-hint");
  var coordsEl = byId("place-coords");

  // The readout above the radius: "48.7262 N · 2.3652 E", with the decimal
  // comma on a French page, and the hint that a tap moves the pin.
  function showReadout(latlng) {
    var comma = (document.documentElement.getAttribute("lang") || "").slice(0, 2) === "fr";
    function number(value) {
      var out = Math.abs(roundCoord(value)).toFixed(COORD_DECIMALS);
      return comma ? out.replace(".", ",") : out;
    }
    if (coordsEl) {
      coordsEl.textContent = format(
        text("coords"), number(latlng.lat), latlng.lat >= 0 ? "N" : "S",
        number(latlng.lng), latlng.lng >= 0 ? "E" : "W");
      coordsEl.hidden = false;
    }
    if (moveHintEl) {
      moveHintEl.hidden = false;
    }
  }

  function afterPinMoved(latlng, fromFields) {
    if (tapHintEl) {
      tapHintEl.hidden = true;
    }
    showReadout(latlng);
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
      centreOn(point, opts.zoom, opts.animate);
    } else if (opts.pan) {
      centreOn(point, map.getZoom(), true);
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

  // --- Airport pins ----------------------------------------------------------

  function runwayWanted() {
    var radio = byId("place-mode-runway");
    return !!(radio && radio.checked);
  }

  // A small round mark in a 44 px invisible hit box, with the IATA code as a
  // label that the stylesheet shows from the label zoom, on hover, or always
  // for the airport the setting follows.
  function dotIcon(airport, selected) {
    return L.divIcon({
      className: "place-dot" + (selected ? " place-dot--selected" : ""),
      html: '<span class="place-dot__mark" data-icao="' + escapeText(airport.icao) +
        '"></span><span class="place-dot__label">' +
        escapeText(airport.iata || airport.icao) + "</span>",
      iconSize: [44, 44],
      iconAnchor: [22, 22]
    });
  }

  function syncLabelZoom() {
    var low = map.getZoom() < LABEL_MIN_ZOOM;
    var has = (" " + mapEl.className + " ").indexOf(" place-map--bare ") >= 0;
    if (low && !has) {
      mapEl.className += " place-map--bare";
    } else if (!low && has) {
      mapEl.className = mapEl.className.replace(/\s*place-map--bare\b/, "");
    }
  }

  // The page's own button zooms out to the whole of France, for the way back
  // from an airport's close-up view.
  function wireFranceButton() {
    var button = byId("place-france");
    if (button) {
      button.addEventListener("click", function () {
        centreOn(L.latLng(FRANCE_CENTRE[0], FRANCE_CENTRE[1]), FRANCE_ZOOM, true);
      });
    }
  }

  // A numbered bubble in a 44 px invisible hit box, an even size so the
  // anchor lands on whole pixels.
  function clusterIcon(count) {
    return L.divIcon({
      className: "place-cluster",
      html: '<span class="place-cluster__count">' + count + "</span>",
      iconSize: [44, 44],
      iconAnchor: [22, 22]
    });
  }

  // The drawn items for the current zoom: every airport is either an
  // individual pin or counted in exactly one bubble. The followed airport is
  // always a pin. The grid is in world pixels of the zoom, so it does not
  // move when the map pans.
  function drawnItems() {
    var zoom = map.getZoom();
    var wanted = {};
    var followed = currentAirportCode();
    var cells = {};
    // Zoomed in, only the pins near the screen are real elements; the
    // others are added when a pan or zoom brings them close.
    var near = map.getBounds().pad(PIN_MARGIN);
    var k;
    for (k = 0; k < airports.length; k++) {
      var airport = airports[k];
      if (airport.icao === followed) {
        wanted["p:" + airport.icao] = { airport: airport };
        continue;
      }
      if (zoom > CLUSTER_MAX_ZOOM) {
        if (near.contains([airport.lat, airport.lon])) {
          wanted["p:" + airport.icao] = { airport: airport };
        }
        continue;
      }
      var at = map.project(L.latLng(airport.lat, airport.lon), zoom);
      var key = Math.floor(at.x / CLUSTER_CELL_PX) + ":" + Math.floor(at.y / CLUSTER_CELL_PX);
      (cells[key] = cells[key] || []).push(airport);
    }
    for (var cell in cells) {
      if (!Object.prototype.hasOwnProperty.call(cells, cell)) {
        continue;
      }
      var members = cells[cell];
      if (members.length === 1) {
        wanted["p:" + members[0].icao] = { airport: members[0] };
      } else {
        wanted["c:" + cell + ":" + members.length + ":" + members[0].icao] = { members: members };
      }
    }
    return wanted;
  }

  // Every airport is drawn in Airport mode, clustered while zoomed out; My
  // position mode shows none, so a tap there always places the pin.
  function refreshDots() {
    if (!dotLayer) {
      return;
    }
    syncLabelZoom();
    var wanted = runwayWanted() ? drawnItems() : {};
    var key;
    for (key in dots) {
      if (Object.prototype.hasOwnProperty.call(dots, key) && !wanted[key]) {
        dotLayer.removeLayer(dots[key]);
        delete dots[key];
      }
    }
    for (key in wanted) {
      if (Object.prototype.hasOwnProperty.call(wanted, key) && !dots[key]) {
        dots[key] = wanted[key].airport ? makeDot(wanted[key].airport) : makeCluster(wanted[key].members);
        dotLayer.addLayer(dots[key]);
      }
    }
  }

  function makeCluster(members) {
    var lat = 0;
    var lon = 0;
    var bounds = L.latLngBounds([]);
    members.forEach(function (airport) {
      lat += airport.lat;
      lon += airport.lon;
      bounds.extend([airport.lat, airport.lon]);
    });
    var marker = L.marker([lat / members.length, lon / members.length], {
      icon: clusterIcon(members.length),
      title: format(text("cluster"), members.length),
      keyboard: false,
      riseOnHover: false
    });
    marker.on("click", function () {
      var zoom = Math.max(
        map.getZoom() + 1, Math.min(map.getBoundsZoom(bounds.pad(0.4)), CLUSTER_MAX_ZOOM + 1));
      centreOn(bounds.getCenter(), zoom, true);
    });
    return marker;
  }

  function makeDot(airport) {
    var selected = airport.icao === currentAirportCode();
    var marker = L.marker([airport.lat, airport.lon], {
      icon: dotIcon(airport, selected),
      title: airport.name,
      keyboard: false,
      riseOnHover: false,
      zIndexOffset: selected ? 1000 : 0
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

  // --- Start ------------------------------------------------------------------

  function start() {
    // The ready class comes first: the stylesheet lays the map out as the
    // page's backdrop, and the library measures it when it is built. A
    // failure below removes the class again.
    document.documentElement.className += " " + READY_CLASS;
    buildMap();
    dotLayer = L.layerGroup().addTo(map);
    wireFranceButton();
    map.on("click", function (event) {
      if (resultsEl) {
        clearResults();
      }
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
      radiusField.addEventListener("input", syncRange);
      radiusField.addEventListener("change", syncRange);
    }
    if (rangeField && radiusField) {
      syncRange();
      rangeField.addEventListener("input", function () {
        radiusField.value = rangeField.value;
        fire(radiusField, "input");
      });
    }
    document.addEventListener("change", function (event) {
      if (event.target && event.target.name === "mode") {
        drawCircle();
        refreshDots();
        if (pin) {
          pinMoved(pin.getLatLng());
          // The panel changed height: keep the pin in the clear part.
          centreOn(pin.getLatLng(), map.getZoom(), true);
        }
      }
    });
    wireSearchAndLocate();
    rememberOpened();
    wireCancel();
    showCheckedRunway();

    if (pin) {
      centreOn(pin.getLatLng(), map.getZoom(), false);
    }
    keepPinClear();
  }

  // On a phone the runway chips are one row that scrolls sideways when an
  // airport has more than three: the chosen one is brought into view.
  function showCheckedRunway() {
    var row = document.querySelector(".place-sheet .detection-runways");
    var checked = row && row.querySelector("input:checked");
    var card = checked && checked.parentNode;
    if (card && row.scrollWidth > row.clientWidth) {
      row.scrollLeft = Math.max(0, card.offsetLeft - row.offsetLeft - 4);
    }
  }

  // Whether the pin (its tip and the 42 px of glyph above it) lies in the
  // part of the map the card and the floating controls leave clear.
  function pinIsClear() {
    var covered = coveredBy();
    var size = map.getSize();
    var at = map.latLngToContainerPoint(pin.getLatLng());
    return at.x >= covered.left && at.y - 42 >= covered.top &&
      at.y <= size.y - covered.bottom;
  }

  // The sheet changes height when Save appears or the mode changes: a pin
  // that would end up under it is put back in the clear part. A pin the
  // person just dropped in the clear part stays where their finger put it.
  function keepPinClear() {
    if (typeof window.ResizeObserver !== "function" || !sheetEl) {
      return;
    }
    var seen = Math.round(sheetEl.getBoundingClientRect().height);
    new window.ResizeObserver(function () {
      var height = Math.round(sheetEl.getBoundingClientRect().height);
      if (height !== seen && pin) {
        seen = height;
        if (!pinIsClear()) {
          centreOn(pin.getLatLng(), map.getZoom(), false);
        }
      }
    }).observe(sheetEl);
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
    setLoading(false);
    giveUp();
    removeRootClass(READY_CLASS);
  }
}());
