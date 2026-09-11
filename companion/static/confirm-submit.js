/*
 * SkyPane companion service — confirm-submit.js.
 *
 * D-08 (19-11-PLAN.md, A-26): provides the inline-free native confirm()
 * step for any form[data-confirm] on the site — today,
 * companion/pages/config_page.py's calendar_disconnect_section() is the
 * one such form. Like poll-cooldown.js/dirty-state.js before it, this
 * file has no build step, no bundler, no framework and no dependency of
 * any kind, and must stay written to an ES5-safe subset (no let/const/
 * arrow functions/template literals/backticks) so no transpiler is ever
 * needed to ship it. It is served by companion/app.py's
 * CONFIRM_SUBMIT_SCRIPT_ROUTE, mirroring the existing /static/style.css
 * route.
 *
 * Standing constraint this file must never violate: no HTML-writing
 * sink of any kind anywhere in this file — only attribute reads, one
 * native window.confirm() call, and setting one input's own .value.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * form[data-confirm] at all — today only the Device page does — so the
 * guard below is load-bearing, not defensive noise, matching the
 * project's established convention.
 *
 * IMPORTANT — read before "fixing" anything here: the native confirm()
 * dialog below is a misclick guard only, never a security/authorisation
 * control. It is trivially bypassable (a hand-crafted request, a
 * browser with JavaScript disabled, or this very script blocked by the
 * site's own Content-Security-Policy all skip it entirely). The actual
 * control is server-side: companion/app.py's disconnect route
 * independently requires an exact confirm field value and renders its
 * own two-step confirmation page for a no-JS/CSP-blocked client, and the
 * route sits behind require_session() like every other state-changing
 * route on this site. Do not add logic here that assumes this dialog is
 * the thing standing between a click and the destructive action.
 *
 * Interaction with dirty-state.js's beforeunload guard (19-10-PLAN.md,
 * D-10/A-28): the disconnect form is NOT the settings form
 * (form[data-dirty-form]), so dirty-state.js's own submit listener does
 * not fire for it. A user with unsaved Settings edits who then confirms
 * a disconnect gets BOTH this dialog's confirmation AND, immediately
 * after, the browser's beforeunload warning about the unsaved edits —
 * that is correct and intended (they really are about to navigate away
 * and lose those edits), not a bug to "fix" by suppressing either
 * dialog.
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

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
