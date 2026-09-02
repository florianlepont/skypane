/*
 * SkyPane companion service — copy-button.js.
 *
 * D-23 (06.6.3-CONTEXT.md): click handler on every [data-copy-value]
 * button, copying its value to the clipboard. Like nav-dropdown.js/
 * battery-trend.js before it, this file has no build step, no bundler,
 * no framework and no dependency of any kind beyond the Clipboard API,
 * and must stay written to an ES5-safe subset (no let/const/arrow
 * functions/template literals/backticks) so no transpiler is ever
 * needed to ship it. It is served by companion/app.py's
 * COPY_BUTTON_SCRIPT_ROUTE, mirroring the existing /static/style.css
 * route.
 *
 * Standing constraint this file must never violate: no innerHTML, no
 * other HTML-writing sink anywhere in this file — only textContent and
 * attribute reads. The values this file ever touches are already
 * server-escaped data-copy-value attributes; writing them back into the
 * DOM via anything other than textContent would reopen a markup
 * injection surface this file has no reason to carry.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * [data-copy-value] elements at all, so the guard below is
 * load-bearing, not defensive noise, matching the project's established
 * convention.
 */
(function () {
  "use strict";

  var buttons = document.querySelectorAll("[data-copy-value]");
  if (buttons.length === 0) {
    return;
  }

  var FEEDBACK_TEXT = "Copied";
  var FEEDBACK_RESET_MS = 2000;

  function fallbackCopy(value) {
    var textarea = document.createElement("textarea");
    // Off-screen, not display:none — some browsers refuse to select()
    // an element with no rendered box.
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    textarea.style.left = "-9999px";
    textarea.value = value;
    document.body.appendChild(textarea);
    try {
      textarea.select();
      document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }
  }

  function showFeedback(button) {
    var feedbackEl = button.nextElementSibling;
    if (!feedbackEl || !feedbackEl.hasAttribute("data-copy-feedback")) {
      return;
    }
    feedbackEl.textContent = FEEDBACK_TEXT;
    window.setTimeout(function () {
      feedbackEl.textContent = "";
    }, FEEDBACK_RESET_MS);
  }

  function handleClick(button) {
    var value = button.getAttribute("data-copy-value") || "";
    if (window.navigator && window.navigator.clipboard
        && window.navigator.clipboard.writeText) {
      window.navigator.clipboard.writeText(value).then(
        function () {
          showFeedback(button);
        },
        function () {
          fallbackCopy(value);
          showFeedback(button);
        }
      );
      return;
    }
    fallbackCopy(value);
    showFeedback(button);
  }

  for (var i = 0; i < buttons.length; i++) {
    (function (button) {
      button.addEventListener("click", function () {
        handleClick(button);
      });
    })(buttons[i]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
