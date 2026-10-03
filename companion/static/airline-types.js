/*
 * SkyPane companion service — airline-types.js.
 *
 * Page-local enhancement for the Airlines gallery: each airline with
 * several known aircraft types renders every type as its own section plus
 * a native <select>. With this script the select decides which one
 * section is visible; without it every section stays visible in source
 * order. No network call and no persistent state, only the `hidden`
 * attribute. ES5-safe. Served by companion/app.py's
 * AIRLINE_TYPES_SCRIPT_ROUTE.
 */
(function () {
  "use strict";

  var READY_ATTR = "data-airline-types-ready";
  var TYPE_ATTR = "data-airline-type";

  function wire(group) {
    var select = group.querySelector("[data-airline-type-select]");
    var sections = group.querySelectorAll("[" + TYPE_ATTR + "]");
    if (!select || !sections.length) {
      return;
    }

    function show() {
      var wanted = select.value;
      for (var i = 0; i < sections.length; i += 1) {
        sections[i].hidden = sections[i].getAttribute(TYPE_ATTR) !== wanted;
      }
    }

    select.addEventListener("change", show);
    group.setAttribute(READY_ATTR, "");
    show();
  }

  var groups = document.querySelectorAll("[data-airline-types]");
  for (var index = 0; index < groups.length; index += 1) {
    wire(groups[index]);
  }
})();
