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
 * Standing constraint this file must never violate: no inner-HTML
 * assignment, no other HTML-writing sink anywhere in this file — only
 * textContent and attribute reads. The values this file ever touches are already
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
  // D-20: was 2000 — 1.5s is the visible-confirmation window this
  // decision names for the new on-button "Copied" swap below.
  var FEEDBACK_RESET_MS = 1500;
  var COPIED_CLASS = "copy-btn--copied";

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
      // A-37's third half: this used to call document.execCommand("copy")
      // and discard its boolean return value, so handleClick() below
      // showed "Copied" even when the copy silently failed. Propagate
      // the real result instead.
      return document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }
  }

  function _toggleCopiedClass(button, isActive) {
    // Defensive classList fallback, matching battery-trend.js's own
    // _toggleActive() pattern for elements whose classList might be
    // unavailable.
    if (button.classList) {
      if (isActive) {
        button.classList.add(COPIED_CLASS);
      } else {
        button.classList.remove(COPIED_CLASS);
      }
      return;
    }
    var current = " " + (button.getAttribute("class") || "") + " ";
    var has = current.indexOf(" " + COPIED_CLASS + " ") !== -1;
    if (isActive && !has) {
      button.setAttribute("class", (current + COPIED_CLASS).replace(/^\s+|\s+$/g, ""));
    } else if (!isActive && has) {
      button.setAttribute("class", current.split(" " + COPIED_CLASS + " ").join(" ")
        .replace(/^\s+|\s+$/g, ""));
    }
  }

  function showFeedback(button) {
    var feedbackEl = button.nextElementSibling;
    if (!feedbackEl || !feedbackEl.hasAttribute("data-copy-feedback")) {
      return;
    }
    feedbackEl.textContent = FEEDBACK_TEXT;

    // D-20: swap a visible "Copied" label in beside the icon, on
    // success only. The button's own visible content is an SVG icon
    // (history_page._copy_button_html()'s .copy-btn__icon span) —
    // writing textContent onto the button itself would destroy that
    // SVG with no way to restore it, so this writes only into the leaf
    // .copy-btn__label span rendered alongside it, never the button
    // element (keeping the no-HTML-writing-sink rule intact: only
    // textContent on a leaf <span>, only a class toggle on the button).
    //
    // A double-click mid-animation must not overwrite the remembered
    // original label with "Copied" a second time — data-copy-pending
    // guards that: only the FIRST swap in a run records the label to
    // restore, and one shared setTimeout clears the visible label, the
    // announced feedback span and the class together, so the visible
    // and announced states can never disagree.
    var labelEl = button.querySelector(".copy-btn__label");
    if (!labelEl || button.getAttribute("data-copy-pending") === "1") {
      window.setTimeout(function () {
        feedbackEl.textContent = "";
      }, FEEDBACK_RESET_MS);
      return;
    }

    button.setAttribute("data-copy-pending", "1");
    var originalLabel = labelEl.textContent;
    labelEl.textContent = FEEDBACK_TEXT;
    _toggleCopiedClass(button, true);
    window.setTimeout(function () {
      feedbackEl.textContent = "";
      labelEl.textContent = originalLabel;
      _toggleCopiedClass(button, false);
      button.removeAttribute("data-copy-pending");
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
          // A-37: only report success when fallbackCopy() actually
          // succeeded. A failed copy must show nothing at all — never a
          // false "Copied".
          if (fallbackCopy(value)) {
            showFeedback(button);
          }
        }
      );
      return;
    }
    if (fallbackCopy(value)) {
      showFeedback(button);
    }
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
