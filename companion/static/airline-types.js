/*
 * SkyPane companion service — airline-types.js.
 *
 * The airline editor lists each airline closed; its aircraft-type rows are
 * fetched from the address on the airline's <tbody> (data-types-src) when its
 * chevron first opens, so the page does not carry, build and style hundreds
 * of rows nobody has opened. Without a script the page links to a view that
 * holds every row (see airline_table.py). ES5-safe subset.
 */
(function () {
  "use strict";

  var SRC_ATTR = "data-types-src";
  var LOADING_ATTR = "data-types-loading";

  function insert(group, html) {
    var template = document.createElement("template");
    template.innerHTML = html;
    group.appendChild(template.content);
    group.removeAttribute(SRC_ATTR);
  }

  function fill(group) {
    var src = group.getAttribute(SRC_ATTR);
    if (!src || group.hasAttribute(LOADING_ATTR) || !window.fetch) {
      return;
    }
    group.setAttribute(LOADING_ATTR, "");
    window.fetch(src, { credentials: "same-origin" }).then(function (response) {
      return response.ok ? response.text() : "";
    }).then(function (html) {
      if (html) {
        insert(group, html);
      }
      group.removeAttribute(LOADING_ATTR);
    }, function () {
      // A failed request leaves the group closed-looking; the next toggle retries.
      group.removeAttribute(LOADING_ATTR);
    });
  }

  function groupOf(details) {
    var node = details;
    while (node && node.tagName !== "TBODY") {
      node = node.parentNode;
    }
    return node;
  }

  // A toggle does not bubble, so it is caught on the way down.
  document.addEventListener("toggle", function (evt) {
    var details = evt.target;
    if (details && details.classList && details.classList.contains("airlines-expand")
        && details.open) {
      var group = groupOf(details);
      if (group) {
        fill(group);
      }
    }
  }, true);

  var opened = document.querySelectorAll("details.airlines-expand[open]");
  for (var i = 0; i < opened.length; i++) {
    var group = groupOf(opened[i]);
    if (group) {
      fill(group);
    }
  }
}());
