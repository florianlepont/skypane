/*
 * SkyPane companion service — poll-cooldown.js.
 *
 * The poll trigger button's two affordances: a live cooldown countdown
 * and a disable-on-submit label swap. No build step, ES5-safe subset.
 * Inert on a page with no #poll-trigger-btn (today only Settings).
 * Served by companion/app.py's POLL_COOLDOWN_SCRIPT_ROUTE. No
 * HTML-writing sink: only textContent and attribute reads/removals on
 * values already escaped by config_page.py's poll_trigger_section().
 */
(function () {
  "use strict";

  var btn = document.getElementById("poll-trigger-btn");
  if (!btn) {
    return;
  }

  // The live countdown, present only on the disabled branch, via the
  // button's own server-computed data-cooldown figure. parseInt()+
  // isNaN(), not truthy, so a negative or non-numeric value cannot
  // leave the button natively disabled while this script inertly
  // no-ops.
  var rawRemaining = btn.getAttribute("data-cooldown");
  var remaining = parseInt(rawRemaining, 10);
  if (rawRemaining !== null && !isNaN(remaining) && remaining > 0) {
    var textId = btn.getAttribute("data-cooldown-text-id");
    var text = textId ? document.getElementById(textId) : null;
    var template = btn.getAttribute("data-cooldown-template");
    var token = btn.getAttribute("data-cooldown-token");
    if (text && template && token) {
      var timer = setInterval(function () {
        remaining -= 1;
        if (remaining <= 0) {
          clearInterval(timer);
          btn.removeAttribute("disabled");
          text.textContent = "";
          return;
        }
        text.textContent = template.replace(token, String(remaining));
      }, 1000);
    }
  }

  // The disable-on-submit affordance, present only on the enabled
  // (zero-cooldown) branch. Cosmetic only: companion/app.py's
  // _POLL_LOCK is the actual correctness boundary.
  var pendingText = btn.getAttribute("data-submit-pending");
  if (pendingText) {
    var form = btn.form;
    if (form) {
      form.addEventListener("submit", function () {
        btn.disabled = true;
        btn.textContent = pendingText;
      });
    }
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
