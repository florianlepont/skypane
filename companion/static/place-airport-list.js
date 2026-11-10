/*
 * SkyPane companion service — place-airport-list.js.
 *
 * Fills the Location page's airport list from the catalogue the map already
 * carries (the data-airports attribute of #place-map), so the page ships each
 * airport once. The server renders the rows itself only when a search term
 * narrowed the list, and a short <noscript> list for a browser without
 * scripts. The rows are exactly the ones the server would render: the filter
 * (list-filter.js) reads their data-filter-text. Runs before list-filter.js.
 * No network call. ES5-safe subset.
 */
(function () {
  "use strict";

  var list = document.querySelector("[data-airport-fill]");
  var mapEl = document.getElementById("place-map");
  if (!list || !mapEl) {
    return;
  }

  // Lower case, accents removed, spaces collapsed: the fold list-filter.js
  // matches the typed text against.
  function foldText(value) {
    var folded = String(value).toLowerCase();
    if (typeof folded.normalize === "function") {
      folded = folded.normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    return folded.replace(/\s+/g, " ").replace(/^ | $/g, "");
  }

  var rows = [];
  try {
    rows = JSON.parse(mapEl.getAttribute("data-airports") || "[]");
  } catch (ignored) {
    rows = [];
  }
  var urlTemplate = mapEl.getAttribute("data-airport-url") || "";
  var currentIcao = list.getAttribute("data-current") || "";
  var currentLabel = list.getAttribute("data-current-label") || "";

  var fragment = document.createDocumentFragment();
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    if (!Array.isArray(row)) {
      continue;
    }
    var icao = String(row[0]);
    var iata = String(row[1] || "");
    var name = String(row[2] || "");
    var city = String(row[3] || "");

    var item = document.createElement("li");
    item.className = "place-airport";
    item.setAttribute("data-filter-text", foldText([name, city, icao, iata].join(" ")));

    var link = document.createElement("a");
    link.className = "place-airport__link";
    link.setAttribute(
      "href", urlTemplate.replace("__ICAO__", encodeURIComponent(icao)) + "#airport-runways");
    link.setAttribute("data-detection-nav", "");
    link.setAttribute("data-icao", icao);

    var nameEl = document.createElement("span");
    nameEl.className = "place-airport__name";
    nameEl.textContent = name;

    var meta = document.createElement("span");
    meta.className = "place-airport__meta text-label";
    meta.textContent = [icao, iata, city].filter(Boolean).join(" · ");
    if (currentIcao && icao === currentIcao) {
      meta.setAttribute("data-current-label", currentLabel);
    }

    link.appendChild(nameEl);
    link.appendChild(meta);
    item.appendChild(link);
    fragment.appendChild(item);
  }
  list.appendChild(fragment);

  var countEl = document.querySelector("[data-filter-count]");
  if (countEl && rows.length) {
    var template = countEl.getAttribute("data-filter-count-template") || "# of #";
    countEl.textContent = template.replace("#", String(rows.length)).replace("#", String(rows.length));
  }
}());
