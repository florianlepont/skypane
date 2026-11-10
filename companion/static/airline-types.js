/*
 * SkyPane companion service — airline-types.js.
 *
 * The airline editor ships each airline's aircraft-type rows inside a
 * <template> in its table body and opens them with the airline's chevron, so
 * the page does not build and style hundreds of rows nobody has opened. The
 * rows are the ones the server rendered; nothing is fetched. Without a script
 * the page links to a view that holds every row (see airline_table.py).
 * ES5-safe subset.
 */
(function () {
  "use strict";

  function fill(group) {
    var template = group.querySelector("template.airlines-types");
    if (!template || !template.content) {
      return;
    }
    group.appendChild(template.content);
    group.removeChild(template);
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
