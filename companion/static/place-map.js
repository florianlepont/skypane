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
  var TILE_ERRORS_BEFORE_NOTICE = 4;
  var NEAREST_AIRPORT_KM = 3;
  var COORD_DECIMALS = 4;
  var RADIUS_MIN_KM = 2;
  var RADIUS_MAX_KM = 28;
  var READY_CLASS = "map-ready";
  // Set on the page element by the head script while scripts run: the loading
  // state shows instead of the plain form. A map that cannot start clears it.
  var EARLY_CLASS = "js-early";
  // Set on the page element in a Safari tab: the stylesheet puts a lead of
  // map above the page (its size is --place-lead), which the page scrolls past.
  var LEAD_CLASS = "place-lead";
  // How long after the last scroll the page settles back past the lead.
  var LEAD_SETTLE_MS = 250;
  // Set on the page element while the opening splash covers the page.
  var SPLASH_CLASS = "splash-on";
  // How long after the splash has gone the page waits for its last frames
  // under the splash to leave the screen before it nudges its scroll.
  var SPLASH_SETTLE_MS = 400;
  var MESSAGE_MS = 8000;

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
  var searchForm = document.querySelector("form.place-search");
  var searchInput = byId("place-search");
  var resultsEl = byId("place-results");
  // What place-map-search.js takes over once it loads: the same helpers and
  // state, and the one hook the map calls back.
  var core = {};

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
  // The runway group, the address and the map view the page opened with:
  // Cancel after an in-place pick puts them back.
  var openedRunways = [];
  var openedAddress = window.location.pathname + window.location.search;
  var pickedHere = false;

  var openedView = null;

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
    var point = fieldsPoint();
    if (point) {
      placePin(point, { fromFields: true });
    } else {
      removePin();
    }
    drawCircle();
    if (openedView) {
      map.setView(openedView.centre, openedView.zoom, { animate: true });
    }
    refreshDots();
    showCheckedRunway();
    setStatus("");
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
  var leadApplied = false;

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

  function reducedMotion() {
    return !!(window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches);
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
      // With reduced motion a tile shows at once instead of fading in.
      fadeAnimation: !reducedMotion(),
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

  // Takes the pin off the map and puts the readout back to "tap the map":
  // what a page without a saved place shows.
  function removePin() {
    if (pin) {
      map.removeLayer(pin);
      pin = null;
    }
    if (coordsEl) {
      coordsEl.hidden = true;
    }
    if (moveHintEl) {
      moveHintEl.hidden = true;
    }
    if (tapHintEl) {
      tapHintEl.hidden = false;
    }
    if (nearestEl) {
      nearestEl.hidden = true;
    }
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

  // Hands the search script the helpers it shares with the map. Set only
  // once the map is up, and taken (and removed) by that script when it loads.
  function exportCore() {
    core.MESSAGE_MS = MESSAGE_MS;
    core.airportForQuery = airportForQuery;
    core.airports = airports;
    core.byId = byId;
    core.chooseAirport = chooseAirport;
    core.chooseAreaMode = chooseAreaMode;
    core.fire = fire;
    core.foldText = foldText;
    core.format = format;
    core.labelField = labelField;
    core.mapEl = mapEl;
    core.parseNumber = parseNumber;
    core.placePin = placePin;
    core.roundCoord = roundCoord;
    core.setStatus = setStatus;
    core.showMessage = showMessage;
    core.text = text;
    core.getMap = function () {
      return map;
    };
    window.skypanePlaceMapCore = core;
  }

  // --- Status bar lead ----------------------------------------------------------

  // The lead in pixels while the stylesheet applies it (a phone layout with
  // the map running), else 0.
  function leadSize() {
    var value = window.getComputedStyle(document.documentElement).getPropertyValue("--place-lead");
    return parseFloat(value) || 0;
  }

  // In a Safari tab on an iPhone (navigator.standalone is false there, true
  // in a Home Screen web app and undefined in other browsers) the status bar
  // shows the part of the document above the window and the toolbar the part
  // below it. The page starts scrolled past the lead of map the stylesheet
  // adds, with its tail of map below the window, so both parts are map. A
  // scroll that ends anywhere else (a drag on the sheet, a rotation) settles
  // back, never during a touch or while a field is being typed in.
  function leadUnderStatusBar() {
    if (window.navigator.standalone !== false) {
      return;
    }
    leadApplied = true;
    document.documentElement.className += " " + LEAD_CLASS;
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual";
    }
    window.scrollTo(0, leadSize());
    var touches = 0;
    var timer = null;
    function settle(smooth) {
      var lead = leadSize();
      var active = document.activeElement;
      var typing = !!active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName) &&
        active.type !== "range" && active.type !== "radio" && active.type !== "checkbox";
      if (!lead || touches || typing || Math.abs(window.scrollY - lead) <= 1) {
        return;
      }
      window.scrollTo({ top: lead, behavior: smooth ? "smooth" : "auto" });
    }
    function later() {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        settle(true);
      }, LEAD_SETTLE_MS);
    }
    function onTouch(event) {
      touches = event.touches.length;
      if (!touches) {
        later();
      }
    }
    window.addEventListener("scroll", later, { passive: true });
    window.addEventListener("resize", function () {
      settle(false);
    });
    document.addEventListener("focusout", later);
    document.addEventListener("touchstart", onTouch, { passive: true });
    document.addEventListener("touchend", onTouch, { passive: true });
    document.addEventListener("touchcancel", onTouch, { passive: true });
    afterSplash(nudge);
  }

  // Safari's status bar keeps the look it took from what the page showed at
  // its last scroll. The scroll past the lead happens while the opening
  // splash may still cover the page (dark in the dark theme, which then
  // stays as a grey veil under the clock), and the page does not scroll
  // again; so once the splash has gone it moves by one pixel for a frame and
  // back, and the status bar takes the look of the map.
  function nudge() {
    var lead = leadSize();
    if (!lead || Math.abs(window.scrollY - lead) > 1) {
      return;
    }
    window.scrollTo(0, lead - 1);
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        window.scrollTo(0, lead);
      });
    });
  }

  // Runs `callback` once the opening splash has gone (and the screen has
  // caught up), if it covers the page now; nothing to wait for otherwise.
  function afterSplash(callback) {
    var root = document.documentElement;
    if (root.className.split(" ").indexOf(SPLASH_CLASS) < 0 ||
        typeof window.MutationObserver !== "function") {
      return;
    }
    var watch = new window.MutationObserver(function () {
      if (root.className.split(" ").indexOf(SPLASH_CLASS) < 0) {
        watch.disconnect();
        window.setTimeout(callback, SPLASH_SETTLE_MS);
      }
    });
    watch.observe(root, { attributes: true, attributeFilter: ["class"] });
  }

  // --- Start ------------------------------------------------------------------

  function start() {
    // The ready class comes first: the stylesheet lays the map out as the
    // page's backdrop, and the library measures it when it is built. A
    // failure below removes the class again. The lead is in place before
    // the library measures the map too.
    document.documentElement.className += " " + READY_CLASS;
    leadUnderStatusBar();
    buildMap();
    dotLayer = L.layerGroup().addTo(map);
    wireFranceButton();
    map.on("click", function (event) {
      if (resultsEl && core.clearResults) {
        core.clearResults();
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
        if (areaWanted()) {
          // The status line stops naming the airport that was being followed.
          setStatus("");
        }
        if (pin) {
          pinMoved(pin.getLatLng());
          // The panel changed height: keep the pin in the clear part.
          centreOn(pin.getLatLng(), map.getZoom(), true);
        }
      }
    });
    rememberOpened();
    wireCancel();
    showCheckedRunway();

    if (pin) {
      centreOn(pin.getLatLng(), map.getZoom(), false);
    }
    openedView = { centre: map.getCenter(), zoom: map.getZoom() };
    keepPinClear();
    exportCore();
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
    // Without the map there is no lead: the plain form starts at its top.
    if (leadApplied) {
      removeRootClass(LEAD_CLASS);
      window.scrollTo(0, 0);
    }
  }
}());
