/*
 * SkyPane companion service — login-card.js.
 *
 * The login card's two script-gated affordances: the show-password
 * toggle and the live lockout countdown. No build step, ES5-safe
 * subset. Served by companion/app.py's LOGIN_CARD_SCRIPT_ROUTE, the
 * only script the pre-auth login_shell() loads. No HTML-writing DOM
 * sink; every value here was already server-escaped. No-JS floor: the
 * toggle ships hidden and this file is the only thing that removes it.
 * The countdown is presentational only, over server state that already
 * exists: companion/auth.py's LoginThrottle gates every POST /login
 * regardless of whether this script ran.
 */
(function () {
  "use strict";

  var form = document.querySelector(".login-form");
  if (!form) {
    return;
  }

  // Reserves the field's right-hand gutter. Appended here, never
  // server-rendered, so a scripts-blocked page has no empty gutter.
  var WITH_TOGGLE_CLASS = "login-form__field--with-toggle";

  var toggle = form.querySelector("[data-login-reveal]");
  var field = document.getElementById("password");
  var glyph = toggle ? toggle.querySelector("[data-login-reveal-glyph]") : null;

  // Both accessible names and both glyphs are server-rendered,
  // escaped and already translated; reading them off the element keeps
  // every English string in this feature on the Python side.
  var applyRevealState = function (shown) {
    field.setAttribute("type", shown ? "text" : "password");
    toggle.setAttribute("aria-pressed", shown ? "true" : "false");
    var label = toggle.getAttribute(
      shown ? "data-hide-label" : "data-show-label");
    if (label) {
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("title", label);
    }
    var mark = toggle.getAttribute(
      shown ? "data-hide-glyph" : "data-show-glyph");
    if (glyph && mark) {
      glyph.textContent = mark;
    }
  };

  if (toggle && field) {
    toggle.removeAttribute("hidden");
    if ((" " + toggle.parentNode.className + " ").indexOf(
        " " + WITH_TOGGLE_CLASS + " ") === -1) {
      toggle.parentNode.className += " " + WITH_TOGGLE_CLASS;
    }
    toggle.addEventListener("click", function () {
      applyRevealState(toggle.getAttribute("aria-pressed") !== "true");
    });
  }

  // --- the live lockout countdown --------------------------------------
  //
  // The remaining figure is the server's own seconds_remaining()
  // output, read off the form, never a client clock or duration
  // constant. parseInt()+isNaN(), not truthy, so a negative or
  // non-numeric value cannot leave the form natively disabled while
  // this script inertly no-ops.
  var rawRemaining = form.getAttribute("data-lockout-seconds");
  var remaining = parseInt(rawRemaining, 10);
  var message = document.getElementById("login-error");
  var template = form.getAttribute("data-lockout-template");
  var token = form.getAttribute("data-lockout-token");
  var submit = form.querySelector("button[type=\"submit\"]");

  if (rawRemaining !== null && !isNaN(remaining) && remaining > 0
      && message && template && token && field && submit) {
    // The message keeps its role="alert", which announces the lockout
    // on page load, but an alert is an assertive live region and
    // rewriting it once a second would interrupt a screen-reader user
    // for the whole window. An explicit aria-live overrides that
    // implicit politeness while leaving the role itself in place.
    message.setAttribute("aria-live", "off");
    var timer = window.setInterval(function () {
      remaining -= 1;
      if (remaining > 0) {
        message.textContent = template.replace(token, String(remaining));
        return;
      }
      window.clearInterval(timer);
      message.textContent = "";
      field.removeAttribute("disabled");
      submit.removeAttribute("disabled");
      // The message is gone, so the field must not still be described
      // by an empty paragraph.
      field.removeAttribute("aria-describedby");
    }, 1000);
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
