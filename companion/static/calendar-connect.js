/*
 * SkyPane companion service — calendar-connect.js.
 *
 * Upgrades the calendar connection page's one form. No build step,
 * ES5-safe subset. Inert on a page with no [data-calendar-connect] form.
 * Served by companion/app.py's CALENDAR_CONNECT_SCRIPT_ROUTE. No network
 * call, no timer, no HTML-writing sink: only attribute reads and
 * textContent writes.
 *
 * The server reads the pasted link before saving it, which can take up to
 * ten seconds: while the form posts, the submit button says so. The label
 * is rendered by the server (already translated) on the button.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-calendar-connect]");
  if (!form) {
    return;
  }
  var buttons = document.querySelectorAll('button[type="submit"][data-pending-label]');

  form.addEventListener("submit", function () {
    for (var i = 0; i < buttons.length; i += 1) {
      buttons[i].textContent = buttons[i].getAttribute("data-pending-label");
    }
    form.setAttribute("aria-busy", "true");
  });
})();
