/*
 * SkyPane companion service — nav-dropdown.js.
 *
 * Shell script present on every page. It marks the document as script-capable
 * (the "js" class the stylesheet's .js-scoped rules wait for) and remembers
 * whether the visitor collapsed the frame tile strip on a phone. No build
 * step, ES5-safe subset. Served by companion/app.py's NAV_SCRIPT_ROUTE. Never
 * a network call or a timer; the only persistent state is one localStorage
 * flag, read and written inside try/catch because storage can be blocked.
 */
(function () {
  "use strict";

  // Runs unconditionally: style.css's .js-scoped rules must never be left
  // unresolved, whatever the page holds.
  document.documentElement.className += " js";

  var fold = document.querySelector("details.frame-fold");
  if (!fold || !window.matchMedia) {
    return;
  }

  var STORAGE_KEY = "skypane.frameStrip";
  // The strip is only collapsible below this width (the summary row is
  // hidden above it); must equal the stylesheet's phone breakpoint.
  var phone = window.matchMedia("(max-width: 699.98px)");

  function stored() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function store(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (err) {
      // Storage blocked: the choice simply is not remembered.
    }
  }

  // Applies the remembered choice on a phone; a wider window always shows the
  // strip, since nothing there can reopen it.
  function apply() {
    fold.open = phone.matches ? stored() !== "closed" : true;
  }

  apply();

  fold.addEventListener("toggle", function () {
    if (phone.matches) {
      store(fold.open ? "open" : "closed");
    }
  });

  if (phone.addEventListener) {
    phone.addEventListener("change", apply);
  }
})();
