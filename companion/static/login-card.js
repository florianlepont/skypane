/*
 * SkyPane companion service — login-card.js.
 *
 * 22-13-PLAN.md (X3, 22-UI-SPEC.md §3.2): the login card's two
 * script-gated affordances — the show-password toggle and, from Task 3,
 * the live lockout countdown. Like theme-preview.js/flight-rows.js/
 * poll-cooldown.js before it, this file has no build step, no bundler,
 * no framework and no dependency of any kind, and must stay written to
 * an ES5-safe subset (var-only declarations, no arrow functions, no
 * template-literal syntax) so no transpiler is ever needed to ship it.
 * It is served by companion/app.py's LOGIN_CARD_SCRIPT_ROUTE, mirroring
 * the existing /static/style.css route.
 *
 * This is the first script this app has ever loaded on its PRE-AUTH
 * page. companion/layout.py's login_shell() emitted zero script tags
 * until this plan — its own docstring said so as a deliberate property
 * of the pre-session shell — which is why that function gained exactly
 * one script tag, and layout.py gained one LOGIN_CARD_SCRIPT_SRC
 * constant beside its eleven siblings, in the same plan. The
 * Content-Security-Policy is UNCHANGED: script-src 'self', no
 * unsafe-inline, no nonce, no CSP edit of any kind, because this is a
 * same-origin static file exactly like every other script here.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, any persistent state, or
 * any markup-writing DOM sink at all. The only DOM writes it ever makes
 * are attribute reads/writes/removals, one class append, and
 * textContent on two leaf elements — never a sink that parses a string
 * as HTML. Every value it writes back was escaped at render time by
 * companion/app.py's _login_body(), which is what keeps that true.
 *
 * No-JS floor (D-09, locked): the toggle is server-rendered WITH the
 * hidden attribute on every branch, and this file is the only thing
 * that ever removes it. A browser with JavaScript disabled, or one
 * where this file is blocked, simply never runs it — so it never shows
 * a control that would do nothing, which is this app's own recorded
 * precedent (references/settings-page-patterns.md). That same browser
 * still sees the server-computed lockout sentence and can still sign
 * in, unchanged from before this plan.
 *
 * This script is served to every page on the site as a single cached
 * static asset, but only login_shell() ever emits a tag for it, so
 * today the login page is its only requester. The guard below is
 * load-bearing anyway, matching the project's established convention.
 */
(function () {
  "use strict";

  var form = document.querySelector(".login-form");
  if (!form) {
    return;
  }

  // The class companion/static/style.css reserves the field's
  // right-hand gutter with. Appended here, never server-rendered, so a
  // scripts-blocked page has no empty gutter — the per-script
  // class-at-load idiom theme-preview.js and flight-rows.js established.
  var WITH_TOGGLE_CLASS = "login-form__field--with-toggle";

  var toggle = form.querySelector("[data-login-reveal]");
  var field = document.getElementById("password");
  var glyph = toggle ? toggle.querySelector("[data-login-reveal-glyph]") : null;

  // Both accessible names and both glyphs are server-rendered,
  // server-escaped and already translated (companion/app.py's
  // LOGIN_REVEAL_* constants). Reading them off the element is what
  // keeps every English string in this feature on the Python side,
  // where companion/test_i18n.py can see it.
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
  // Presentational ONLY, over server state that already exists. A
  // reviewer will reasonably ask whether re-enabling the form here is a
  // way past the lockout: it is not. companion/auth.py's LoginThrottle
  // is consulted on every POST /login before the submitted password is
  // even looked at, so an attempt made inside the window is rejected
  // whether this file ran or not, and a visitor who deletes the two
  // disabled attributes by hand gains exactly nothing. No throttling
  // constant is duplicated here either — the remaining figure is the
  // server's own seconds_remaining() output, read off the form, never
  // derived from a client clock or a duration constant.
  //
  // parseInt()+isNaN(), not truthy, so this file's own "greater than
  // zero" gate agrees with _login_body()'s: a negative or non-numeric
  // value must not leave the form natively disabled while this script
  // inertly no-ops, which would be the one state with no way back.
  var rawRemaining = form.getAttribute("data-lockout-seconds");
  var remaining = parseInt(rawRemaining, 10);
  var message = document.getElementById("login-error");
  var template = form.getAttribute("data-lockout-template");
  var token = form.getAttribute("data-lockout-token");
  var submit = form.querySelector("button[type=\"submit\"]");

  if (rawRemaining !== null && !isNaN(remaining) && remaining > 0
      && message && template && token && field && submit) {
    // The message keeps its role="alert" — that is the contract, and it
    // is what announces the lockout when the page loads. But an alert is
    // an assertive live region, and rewriting its text once a second
    // would interrupt a screen-reader user every second for the whole
    // window. An explicit aria-live overrides the role's implicit
    // politeness while leaving the role itself in the accessibility
    // tree, so the sentence is announced once and then ticks silently.
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
      // The message is gone, so nothing is left for the field to be
      // described by; leaving the association pointing at an empty
      // paragraph would announce the field as having a description it
      // no longer has.
      field.removeAttribute("aria-describedby");
    }, 1000);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's login_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
