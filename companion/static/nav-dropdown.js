/*
 * SkyPane companion service — nav-dropdown.js.
 *
 * Shell script present on every page. It marks the document as script-capable
 * (the "js" class the stylesheet's .js-scoped rules wait for) and sets Home's
 * greeting wording for the local hour. No build step, ES5-safe subset. Served
 * by companion/app.py's NAV_SCRIPT_ROUTE. Never a network call, a timer or
 * persistent state.
 */
(function () {
  "use strict";

  // Runs unconditionally: style.css's .js-scoped rules must never be left
  // unresolved, whatever the page holds.
  document.documentElement.className += " js";

  var hour = new Date().getHours();

  // Home's title carries the four wordings (first name included); the one
  // for the local hour (morning 05-12, afternoon 12-17, evening 17-21, else
  // night) replaces the neutral server text. This script runs before the
  // first paint, so the swap does not move the page.
  var greeting = document.querySelector("[data-greeting]");
  var greetingText = greeting && greeting.querySelector("[data-greeting-text]");
  if (greetingText) {
    var band = "night";
    if (hour >= 5 && hour < 12) {
      band = "morning";
    } else if (hour >= 12 && hour < 17) {
      band = "afternoon";
    } else if (hour >= 17 && hour < 21) {
      band = "evening";
    }
    var wording = greeting.getAttribute("data-greeting-" + band);
    if (wording) {
      greetingText.textContent = wording;
    }
  }
})();
