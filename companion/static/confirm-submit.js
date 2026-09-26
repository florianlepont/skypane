/*
 * SkyPane companion service — confirm-submit.js.
 *
 * A native confirm() step for any form[data-confirm] (today the Device
 * page's calendar disconnect form). No build step, ES5-safe subset.
 * Inert on a page with no such form. Served by companion/app.py's
 * CONFIRM_SUBMIT_SCRIPT_ROUTE. No HTML-writing sink: only attribute
 * reads, window.confirm(), and setting one input's .value.
 *
 * Security: this dialog is a misclick guard only, trivially bypassable
 * (no JS, a blocked script, a hand-crafted request). The actual control
 * is server-side: companion/app.py's disconnect route independently
 * requires an exact confirm field value and sits behind
 * require_session() like every other state-changing route.
 */
(function () {
  "use strict";

  var forms = document.querySelectorAll("form[data-confirm]");
  if (!forms.length) {
    return;
  }

  function attachConfirmHandler(form) {
    form.addEventListener("submit", function (evt) {
      var question = form.getAttribute("data-confirm");
      if (!window.confirm(question)) {
        evt.preventDefault();
        return;
      }
      var field = form.querySelector("[data-confirm-field]");
      var value = form.getAttribute("data-confirm-value");
      if (field && value !== null) {
        field.value = value;
      }
    });
  }

  var i;
  for (i = 0; i < forms.length; i++) {
    attachConfirmHandler(forms[i]);
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
